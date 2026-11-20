"""Fases B/C: solicitud de vacante, respuesta de secretaría y disponibilidad."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app import db, sesion as sesion_mod
from app.errores import ErrorPermiso, ErrorValidacion
from app.servicios import auth, solicitudes as sol, vacantes

CONTACTO = {
    "nombres_apoderado": "María Elena Acosta",
    "celular": "987654321",
    "correo": "maria@example.com",
}


class TestFlujoVacante(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        sol.configurar_directorio(Path(self.temporal.name) / "solicitudes")
        self.sesion_original = sesion_mod.autenticacion.sesion_activa
        self._iniciar_padre()
        self.parches = [
            patch.object(sol, "_ya_matriculado", return_value=False),
            patch.object(auth, "leer_perfil", return_value=dict(CONTACTO)),
        ]
        for parche in self.parches:
            parche.start()

    def tearDown(self) -> None:
        for parche in reversed(self.parches):
            parche.stop()
        sesion_mod.autenticacion.cerrar_sesion()
        if self.sesion_original:
            sesion_mod.autenticacion.iniciar_sesion(self.sesion_original)
        sol.restaurar_directorio()
        self.temporal.cleanup()

    def _iniciar_padre(self) -> None:
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=7, nombre_usuario="padre_demo", rol="Padre",
            dni="29481029", nombres="María", apellidos="Acosta",
        ))

    def _iniciar_secretaria(self) -> None:
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=1, nombre_usuario="secretaria", rol="Secretaria",
            dni="87733221", nombres="Claudia", apellidos="Acosta",
        ))

    def _alumno(self, dni: str) -> dict:
        alumno = sol.nuevo_alumno_vacante()
        sol.sincronizar_ficha_vacante(alumno)
        alumno["ficha"]["DNI"] = dni
        alumno["ficha"]["dni"] = dni
        alumno["ficha"]["Nombres"] = "Ana"
        alumno["ficha"]["nombres"] = "Ana"
        alumno["ficha"]["ApellidoPaterno"] = "Quispe"
        alumno["ficha"]["apellido_paterno"] = "Quispe"
        alumno["ficha"]["ApellidoMaterno"] = "Pérez"
        alumno["ficha"]["apellido_materno"] = "Pérez"
        alumno["ficha"]["FechaNacimiento"] = "2015-05-10"
        alumno["ficha"]["fecha_nacimiento"] = "2015-05-10"
        alumno["destino"] = {"nivel": "Primaria", "grado": "1.°"}
        return alumno

    def _vacante(self) -> dict:
        datos = sol.crear_borrador()
        datos["alumnos"] = [self._alumno("91234567")]
        sol.guardar_solicitud(datos)
        return datos

    def test_etapa_vacante_por_defecto_y_json_antiguo(self) -> None:
        datos = sol.crear_borrador()
        self.assertEqual(datos["etapa"], "vacante")
        self.assertEqual(datos["contacto"], CONTACTO)
        antiguo = dict(datos)
        antiguo.pop("etapa")
        self.assertEqual(sol.etapa_de(antiguo), "matricula")

    def test_validar_vacante_y_limite_de_hermanos(self) -> None:
        datos = self._vacante()
        self.assertEqual(sol.validar_vacante(datos), [])
        for numero in range(1, 6):
            datos["alumnos"].append(self._alumno(f"9123456{numero}"))
        self.assertEqual(len(datos["alumnos"]), 6)
        self.assertEqual(sol.validar_vacante(datos), [])
        datos["alumnos"].append(self._alumno("91234569"))
        self.assertTrue(any("1 y 6" in error for error in sol.validar_vacante(datos)))

    def test_validar_vacante_exige_contacto_valido(self) -> None:
        datos = self._vacante()
        datos["contacto"] = {"nombres_apoderado": "", "celular": "876543210", "correo": "x"}
        errores = sol.validar_vacante(datos)
        self.assertEqual(len(errores), 3)

    def test_enviar_vacante_no_toca_la_base_de_datos(self) -> None:
        datos = self._vacante()
        with patch.object(db, "call_proc") as llamadas, patch.object(db, "query_uno") as consultas:
            enviada = sol.enviar(datos["id"])
        self.assertEqual(enviada["estado"], "Enviada")
        self.assertEqual(enviada["etapa"], "vacante")
        llamadas.assert_not_called()
        consultas.assert_not_called()

    def test_transiciones_invalidas(self) -> None:
        casos = (
            ("Borrador", "Aprobada", "vacante", "matricula"),
            ("Enviada", "Aprobada", "vacante", "matricula"),
            ("Aprobada", "Enviada", "matricula", "matricula"),
            ("Vacante aceptada", "Enviada", "matricula", "vacante"),
            ("Enviada", "Borrador", "vacante", "vacante"),
        )
        for actual, nuevo, etapa_actual, etapa_nueva in casos:
            with self.subTest(actual=actual, nuevo=nuevo):
                with self.assertRaises(ErrorValidacion):
                    sol.validar_transicion(actual, nuevo, etapa_actual, etapa_nueva)

    def test_el_padre_no_puede_aceptar_la_vacante(self) -> None:
        datos = self._vacante()
        sol.enviar(datos["id"])
        with self.assertRaises(ErrorPermiso):
            sol.aceptar_vacante(datos["id"])

    def test_aceptar_vacante_cambia_estado_y_no_reserva_cupo(self) -> None:
        datos = self._vacante()
        sol.enviar(datos["id"])
        self._iniciar_secretaria()
        with patch.object(db, "call_proc") as llamadas, patch.object(db, "query") as consultas:
            aceptada = sol.aceptar_vacante(datos["id"])
        self.assertEqual(aceptada["estado"], "Vacante aceptada")
        self.assertEqual(aceptada["etapa"], "matricula")
        observacion = aceptada["observaciones"][-1]["texto"]
        self.assertIn("Documentos a presentar", observacion)
        llamadas.assert_not_called()
        consultas.assert_not_called()
        # La carpeta sigue en pendientes: aceptar no mueve archivos ni escribe BD.
        self.assertTrue(sol.ruta_solicitud(datos["id"]).exists())

    def test_registrar_contacto_y_observar_mantienen_la_etapa(self) -> None:
        datos = self._vacante()
        sol.enviar(datos["id"])
        self._iniciar_secretaria()
        sol.registrar_contacto(datos["id"], "Llamada telefónica")
        observada = sol.observar(datos["id"], "Adjunte el DNI del hijo")
        self.assertEqual(observada["estado"], "Observada")
        self.assertEqual(sol.etapa_de(observada), "vacante")
        self._iniciar_padre()
        reenviada = sol.enviar(datos["id"])
        self.assertEqual(reenviada["estado"], "Enviada")
        self.assertEqual(sol.etapa_de(reenviada), "vacante")

    def test_rechazar_desde_cualquier_etapa_de_vacante(self) -> None:
        datos = self._vacante()
        sol.enviar(datos["id"])
        self._iniciar_secretaria()
        rechazada = sol.rechazar(datos["id"], "Sin vacantes")
        self.assertEqual(rechazada["estado"], "Rechazada")
        self.assertTrue(sol.ruta_solicitud(datos["id"], "rechazadas").exists())

    def test_matricula_solo_se_abre_tras_aceptar_vacante(self) -> None:
        datos = self._vacante()
        sol.enviar(datos["id"])
        self._iniciar_secretaria()
        sol.aceptar_vacante(datos["id"])
        self._iniciar_padre()
        aceptada = sol.obtener(datos["id"])
        self.assertEqual(aceptada["estado"], "Vacante aceptada")
        self.assertEqual(sol.etapa_de(aceptada), "matricula")
        with patch.object(sol, "validar_para_enviar", return_value=[]):
            enviada = sol.enviar(datos["id"])
        self.assertEqual(enviada["estado"], "Enviada")
        self.assertEqual(sol.etapa_de(enviada), "matricula")

    def test_contador_de_vacantes_por_atender(self) -> None:
        self._vacante()
        sol.enviar(next(iter(sol.listar_solicitudes()))["id"])
        self._iniciar_secretaria()
        self.assertEqual(sol.contar_vacantes_por_atender(), 1)
        self._iniciar_padre()
        with self.assertRaises(ErrorPermiso):
            sol.contar_vacantes_por_atender()


class TestDisponibilidadReferencial(unittest.TestCase):
    def test_vacantes_por_grado_usa_sp_y_calcula_30_menos_matriculados(self) -> None:
        conjuntos = [
            [[{"Matriculados": 28, "Vacantes": 2}]],
            [[{"Matriculados": 30, "Vacantes": 0}]],
            [[{"Matriculados": 29, "Vacantes": 1}]],
        ]
        with patch.object(vacantes.db, "call_proc", side_effect=conjuntos) as llamadas:
            total = vacantes.vacantes_por_grado(date.today().year + 1, "Primaria", "1.°")
        self.assertEqual(total, 3)
        self.assertEqual(llamadas.call_count, 3)
        self.assertTrue(all(c.args[0] == "sp_cupos_seccion" for c in llamadas.call_args_list))

    def test_sin_vacantes_no_bloquea_el_envio(self) -> None:
        with patch.object(vacantes, "vacantes_por_grado", return_value=0):
            self.assertEqual(vacantes.vacantes_por_grado(2027, "Primaria", "1.°"), 0)

    def test_historial_y_situacion_son_solo_lecturas(self) -> None:
        con_estudiante = {"Nombres": "Ana", "ApellidoPaterno": "Quispe", "ApellidoMaterno": "Pérez"}
        con_matricula = {"anio": 2025, "Nivel": "Primaria", "Grado": "5.°", "Seccion": "A", "Estado": "Matriculado"}
        con_logro = {"anio": 2025, "grado": "5.°", "situacion": "APROBADO"}
        with patch.object(vacantes.db, "query_uno", side_effect=[con_estudiante, con_matricula, con_logro]):
            historial = vacantes.historial_alumno("91234567")
            situacion = vacantes.situacion_final("91234567")
        self.assertTrue(historial["existe"])
        self.assertEqual(historial["ultima"]["grado"], "5.°")
        self.assertEqual(situacion["nivel"], "Primaria")
        self.assertEqual(situacion["situacion"], "APROBADO")


class TestAvisoSinRespuesta(unittest.TestCase):
    def test_solo_resalta_envios_con_mas_de_siete_dias(self) -> None:
        ahora = datetime.now()
        reciente = {"estado": "Enviada", "fecha_envio": (ahora - timedelta(days=3)).isoformat()}
        antigua = {"estado": "Enviada", "fecha_envio": (ahora - timedelta(days=8)).isoformat()}
        self.assertFalse(sol.sin_respuesta(reciente))
        self.assertTrue(sol.sin_respuesta(antigua))
        self.assertFalse(sol.sin_respuesta({"estado": "Observada", "fecha_envio": antigua["fecha_envio"]}))


if __name__ == "__main__":
    unittest.main()
