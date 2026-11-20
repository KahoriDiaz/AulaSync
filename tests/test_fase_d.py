"""Fase D: la matrícula se completa después de aceptar la vacante."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import db, sesion as sesion_mod
from app.errores import ErrorValidacion
from app.servicios import auth, solicitudes as sol

RAIZ = Path(__file__).resolve().parent.parent


class TestMatriculaTrasVacante(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        sol.configurar_directorio(Path(self.temporal.name) / "solicitudes")
        self.sesion_original = sesion_mod.autenticacion.sesion_activa
        self.parches = [
            patch.object(sol, "_ya_matriculado", return_value=False),
            patch.object(auth, "leer_perfil", return_value={
                "nombres_apoderado": "María Acosta", "celular": "987654321",
                "correo": "maria@example.com",
            }),
        ]
        for parche in self.parches:
            parche.start()
        self._iniciar_padre()

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

    def test_vacante_aceptada_se_envia_como_matricula(self) -> None:
        datos = sol.crear_borrador()
        alumno = sol.nuevo_alumno_vacante()
        alumno["ficha"].update({
            "dni": "91234567", "DNI": "91234567",
            "nombres": "Ana", "Nombres": "Ana",
            "apellido_paterno": "Quispe", "ApellidoPaterno": "Quispe",
            "apellido_materno": "Pérez", "ApellidoMaterno": "Pérez",
            "fecha_nacimiento": "2015-05-10", "FechaNacimiento": "2015-05-10",
        })
        datos["alumnos"] = [alumno]
        sol.guardar_solicitud(datos)
        sol.enviar(datos["id"])
        self._iniciar_secretaria()
        sol.aceptar_vacante(datos["id"])
        self._iniciar_padre()
        with patch.object(sol, "validar_para_enviar", return_value=[]):
            matricula = sol.enviar(datos["id"])
        self.assertEqual(matricula["estado"], "Enviada")
        self.assertEqual(matricula["etapa"], "matricula")

        # Con la matrícula Enviada, la aprobación sigue siendo válida.
        self._iniciar_secretaria()
        with patch.object(db, "query_uno") as consultas:
            consultas.return_value = None
            aprobada = sol.aprobar(datos["id"])
        self.assertEqual(aprobada["estado"], "Aprobada")
        self.assertTrue(sol.ruta_solicitud(datos["id"], "aprobadas").exists())

    def test_no_se_puede_aprobar_una_vacante_aceptada(self) -> None:
        datos = sol.crear_borrador()
        sol.guardar_solicitud(datos)
        self._iniciar_secretaria()
        with self.assertRaises(ErrorValidacion):
            sol.aprobar(datos["id"])

    def test_no_se_puede_aprobar_una_solicitud_de_vacante(self) -> None:
        datos = sol.crear_borrador(etapa="vacante")
        datos["estado"] = "Enviada"
        sol.guardar_solicitud(datos)
        self._iniciar_secretaria()
        with self.assertRaises(ErrorValidacion):
            sol.aprobar(datos["id"])


class TestAsistenteReutilizado(unittest.TestCase):
    """Comprobación estática: el módulo tkinter no está disponible en el agente."""

    def test_asistente_bloquea_nivel_y_grado_tras_aceptar_vacante(self) -> None:
        fuente = (RAIZ / "app/ui/padre/asistente_solicitud.py").read_text(encoding="utf-8")
        self.assertIn('crear_borrador(etapa="matricula")', fuente)
        self.assertIn('if solicitudes.etapa_de(self.datos) == "vacante":', fuente)
        self.assertIn("self.destino_bloqueado = (", fuente)
        self.assertIn('estado_destino = "disabled" if self.destino_bloqueado else "readonly"', fuente)
        self.assertIn('"Vacante aceptada")', fuente)
        self.assertIn("Nivel y grado definidos al solicitar la vacante", fuente)

    def test_bandeja_padre_abre_matricula_solo_tras_vacante_aceptada(self) -> None:
        fuente = (RAIZ / "app/ui/padre/mis_solicitudes.py").read_text(encoding="utf-8")
        self.assertIn("def completar_matricula", fuente)
        self.assertIn('datos["estado"] != "Vacante aceptada"', fuente)
        self.assertIn("Solicitar vacante", fuente)


if __name__ == "__main__":
    unittest.main()
