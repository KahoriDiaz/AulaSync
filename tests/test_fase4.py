"""Pruebas de la fase 4: asistente del padre y bandeja de solicitudes (§6.2)."""
from __future__ import annotations

import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import sesion as sesion_mod
from app.errores import ErrorConflicto, ErrorPermiso, ErrorValidacion
from app.servicios import solicitudes

RAIZ = Path(__file__).resolve().parent.parent


class TestFase4Solicitudes(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        solicitudes.configurar_directorio(Path(self.temporal.name) / "solicitudes")
        self.sesion_original = sesion_mod.autenticacion.sesion_activa
        self._iniciar_padre()
        self._parche_matricula = patch.object(
            solicitudes, "_ya_matriculado", return_value=False
        )
        self._mock_matricula = self._parche_matricula.start()

    def tearDown(self) -> None:
        self._parche_matricula.stop()
        sesion_mod.autenticacion.cerrar_sesion()
        if self.sesion_original:
            sesion_mod.autenticacion.iniciar_sesion(self.sesion_original)
        solicitudes.restaurar_directorio()
        self.temporal.cleanup()

    # --------------------------------------------------------------- ayuda
    def _iniciar_padre(self, dni: str = "29481029") -> None:
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=7, nombre_usuario="padre_demo", rol="Padre",
            dni=dni, nombres="María Elena", apellidos="Acosta Porras",
        ))

    def _iniciar_secretaria(self) -> None:
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=1, nombre_usuario="secretaria", rol="Secretaria",
            dni="87733221", nombres="Claudia", apellidos="Acosta Neira",
        ))

    def _solicitud_lista(self, dni_alumno: str = "91234567", anio: int | None = None):
        datos = solicitudes.crear_borrador(anio or date.today().year + 1)
        alumno = solicitudes.nuevo_alumno()
        alumno["ficha"].update({
            "DNI": dni_alumno,
            "Sexo": "F",
            "Nombres": "Ana Sofía",
            "ApellidoPaterno": "Quispe",
            "ApellidoMaterno": "Pérez",
            "FechaNacimiento": "2015-05-10",
            "DistritoNacimiento": "Cercado",
            "ProvinciaNacimiento": "Arequipa",
            "DepartamentoNacimiento": "Arequipa",
            "PaisNacimiento": "Perú",
            "DomicilioActual": "Calle Lima 123",
            "DistritoDomicilio": "Cercado",
            "Celular": "987654321",
            "LugarQueOcupa": 1,
            "ViveConPadre": True,
            "ViveConMadre": True,
            "ElPadreVive": True,
            "LaMadreVive": True,
        })
        alumno["destino"] = {"nivel": "Secundaria", "grado": "4.°"}
        padre = solicitudes.nuevo_padre("Padre")
        padre.update({
            "DNI": "29481029", "Sexo": "F", "Nombres": "María Elena",
            "ApellidoPaterno": "Acosta", "ApellidoMaterno": "Porras",
            "FechaNacimiento": "1990-03-15", "GradoInstruccion": "Superior",
            "DomicilioActual": "Calle Lima 123", "DistritoDomicilio": "Cercado",
            "Celular": "987654321",
        })
        datos["alumnos"] = [alumno]
        datos["padres"] = [padre]
        datos["dni_responsable"] = "29481029"
        datos["contacto_emergencia"] = {"nombre": "Rosa Pérez", "celular": "987654321"}
        solicitudes.guardar_solicitud(datos)
        return datos

    # ------------------------------------------------------------- pruebas
    def test_crear_borrador_y_filtro_por_padre(self):
        datos = solicitudes.crear_borrador()
        self.assertRegex(datos["id"], r"^SOL-\d{4}-\d{4}$")
        self.assertEqual(datos["estado"], "Borrador")
        self.assertEqual(datos["dni_solicitante"], "29481029")
        self.assertTrue(solicitudes.ruta_solicitud(datos["id"]).exists())
        self.assertEqual(len(solicitudes.listar_solicitudes()), 1)

        self._iniciar_padre("70000003")
        self.assertEqual(solicitudes.listar_solicitudes(), [])
        with self.assertRaises(ErrorPermiso):
            solicitudes.obtener(datos["id"])

        self._iniciar_secretaria()
        self.assertEqual(len(solicitudes.listar_solicitudes()), 1)

    def test_actualizar_fusiona_y_protege_identidad(self):
        datos = solicitudes.crear_borrador()
        actualizado = solicitudes.actualizar(datos["id"], {
            "contacto_emergencia": {"nombre": "Rosa"},
            "estado": "Aprobada",
            "id": "OTRO-ID",
            "dni_solicitante": "00000000",
        })
        self.assertEqual(actualizado["contacto_emergencia"]["nombre"], "Rosa")
        self.assertEqual(actualizado["contacto_emergencia"]["celular"], "")
        self.assertEqual(actualizado["estado"], "Borrador")
        self.assertEqual(actualizado["id"], datos["id"])
        self.assertEqual(actualizado["dni_solicitante"], "29481029")
        self.assertEqual(len(actualizado["historial"]), 2)

    def test_validacion_paso1_destino_y_hermanos(self):
        datos = self._solicitud_lista()
        self.assertEqual(solicitudes.validar_paso(1, datos), [])
        datos["anio"] = date.today().year + 5
        self.assertTrue(solicitudes.validar_paso(1, datos))
        datos["anio"] = date.today().year + 1
        datos["alumnos"][0]["destino"]["grado"] = "7.°"
        self.assertTrue(solicitudes.validar_paso(1, datos))
        datos["alumnos"][0]["destino"]["grado"] = "4.°"
        planta = datos["alumnos"][0]
        for posicion in range(5):
            hermano = solicitudes.agregar_alumno(datos)
            hermano["ficha"] = dict(planta["ficha"])
            hermano["ficha"]["DNI"] = str(91234568 + posicion)
            hermano["ficha"]["LugarQueOcupa"] = posicion + 2
            hermano["destino"] = dict(planta["destino"])
        self.assertEqual(len(datos["alumnos"]), 6)
        self.assertEqual(solicitudes.validar_paso(1, datos), [])
        with self.assertRaises(ErrorValidacion):
            solicitudes.agregar_alumno(datos)

    def test_validacion_paso2_alumnos_y_contacto(self):
        datos = self._solicitud_lista()
        self.assertEqual(solicitudes.validar_paso(2, datos), [])
        datos["alumnos"][0]["ficha"]["FechaNacimiento"] = "2099-01-01"
        self.assertTrue(solicitudes.validar_paso(2, datos))
        datos["alumnos"][0]["ficha"]["FechaNacimiento"] = "2015-05-10"
        datos["alumnos"][0]["nee"] = ["X" * 51]
        self.assertTrue(solicitudes.validar_paso(2, datos))
        datos["alumnos"][0]["nee"] = ["Ninguna"]
        datos["contacto_emergencia"]["celular"] = "123"
        self.assertTrue(solicitudes.validar_paso(2, datos))
        datos["contacto_emergencia"]["celular"] = "987654321"
        datos["alumnos"][0]["ficha"]["Sexo"] = "X"
        self.assertTrue(solicitudes.validar_paso(2, datos))
        datos["alumnos"][0]["ficha"]["Sexo"] = "F"
        datos["alumnos"][0]["ficha"]["TipoAtencion"] = "OTRO"
        self.assertTrue(solicitudes.validar_paso(2, datos))

    def test_validacion_paso3_padres_y_responsable(self):
        datos = self._solicitud_lista()
        self.assertEqual(solicitudes.validar_paso(3, datos), [])
        datos["padres"][0]["FechaNacimiento"] = str(date.today().year - 10) + "-01-01"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["padres"][0]["FechaNacimiento"] = "1990-03-15"
        datos["alumnos"][0]["ficha"]["DNI"] = "29481029"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["alumnos"][0]["ficha"]["DNI"] = "91234567"
        datos["dni_responsable"] = "00000000"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["dni_responsable"] = "29481029"
        datos["padres"][0]["Sexo"] = "X"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["padres"][0]["Sexo"] = "F"
        datos["padres"][0]["GradoInstruccion"] = "Doctorado"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["padres"][0]["GradoInstruccion"] = "Superior"
        datos["padres"][0]["TelefonoFijo"] = "123"
        self.assertTrue(solicitudes.validar_paso(3, datos))
        datos["padres"][0]["TelefonoFijo"] = ""
        datos["padres"].append(solicitudes.nuevo_padre("Madre"))
        datos["padres"].append(solicitudes.nuevo_padre("Madre"))
        self.assertTrue(solicitudes.validar_paso(3, datos))

    def test_enviar_cambia_estado_y_bloquea_edicion(self):
        datos = self._solicitud_lista()
        enviada = solicitudes.enviar(datos["id"])
        self.assertEqual(enviada["estado"], "Enviada")
        self.assertTrue(enviada["fecha_envio"])
        self.assertEqual(enviada["historial"][-1]["accion"], "Envío de la solicitud")
        with self.assertRaises(ErrorValidacion):
            solicitudes.actualizar(datos["id"], {"anio": 2027})
        with self.assertRaises(ErrorValidacion):
            solicitudes.enviar(datos["id"])

    def test_duplicado_y_ya_matriculado_bloquean_envio(self):
        primera = self._solicitud_lista(dni_alumno="91234567")
        solicitudes.enviar(primera["id"])
        segunda = self._solicitud_lista(dni_alumno="91234567")
        mensajes = solicitudes.validar_para_enviar(segunda)
        self.assertTrue(any("pendiente" in m for m in mensajes))

        self._mock_matricula.return_value = True
        tercera = self._solicitud_lista(dni_alumno="92234567")
        mensajes = solicitudes.validar_para_enviar(tercera)
        self.assertTrue(any("ya tiene matrícula" in m for m in mensajes))

    def test_observada_puede_editarse_y_reenviarse(self):
        datos = self._solicitud_lista()
        solicitudes.enviar(datos["id"])
        self._iniciar_secretaria()
        solicitudes.observar(datos["id"], "Falta el DNI del padre", "secretaria")
        self._iniciar_padre()
        observada = solicitudes.obtener(datos["id"])
        self.assertEqual(observada["estado"], "Observada")
        self.assertEqual(len(observada["observaciones"]), 1)
        reenviada = solicitudes.enviar(datos["id"])
        self.assertEqual(reenviada["estado"], "Enviada")

    def test_json_danado_no_rompe_la_bandeja(self):
        self._solicitud_lista()
        carpeta = solicitudes.SOLICITUDES_DIR / "pendientes" / "SOL-2027-9999"
        carpeta.mkdir(parents=True)
        (carpeta / "solicitud.json").write_text("{json roto", encoding="utf-8")
        # El padre sigue viendo solo la suya; la secretaria ve la ilegible.
        self.assertEqual(len(solicitudes.listar_solicitudes()), 1)
        self._iniciar_secretaria()
        lista = solicitudes.listar_solicitudes()
        self.assertEqual(len(lista), 2)
        self.assertTrue(any(s.get("estado") == "ilegible" for s in lista))

    def test_rechazar_y_aprobar_mueven_carpetas(self):
        datos = self._solicitud_lista(dni_alumno="91234567")
        solicitudes.enviar(datos["id"])
        self._iniciar_secretaria()
        rechazada = solicitudes.rechazar(datos["id"], "Documento ilegible")
        self.assertEqual(rechazada["estado"], "Rechazada")
        self.assertTrue(solicitudes.ruta_solicitud(datos["id"], "rechazadas").exists())

        self._iniciar_padre()
        otro = self._solicitud_lista(dni_alumno="92234567")
        solicitudes.enviar(otro["id"])
        self._iniciar_secretaria()
        aprobada = solicitudes.aprobar(otro["id"])
        self.assertEqual(aprobada["estado"], "Aprobada")
        self.assertTrue(solicitudes.ruta_solicitud(otro["id"], "aprobadas").exists())
        with self.assertRaises(ErrorConflicto):
            solicitudes.aprobar(otro["id"])

    def test_documentos_con_nombre_generado_y_validaciones(self):
        datos = self._solicitud_lista()
        origen = Path(self.temporal.name) / "dni_original.jpg"
        origen.write_bytes(b"imagen de prueba")
        ruta = solicitudes.adjuntar_documento(
            datos["id"], origen, indice_alumno=0, tipo="dni"
        )
        self.assertTrue(ruta.endswith(".jpg"))
        self.assertNotIn("dni_original", ruta)
        actualizada = solicitudes.obtener(datos["id"])
        self.assertEqual(actualizada["alumnos"][0]["docs"]["dni"], ruta)

        copiada = solicitudes.copiar_documento(origen, datos["id"])
        self.assertTrue(copiada.endswith(".jpg"))
        self.assertNotIn("dni_original", copiada)
        self.assertTrue((solicitudes.carpeta_solicitud(datos["id"]) / "docs").exists())

        invalido = Path(self.temporal.name) / "dni.txt"
        invalido.write_text("x", encoding="utf-8")
        with self.assertRaises(ErrorValidacion):
            solicitudes.copiar_documento(invalido, datos["id"])
        grande = Path(self.temporal.name) / "grande.png"
        grande.write_bytes(b"0" * (solicitudes.TAMANIO_MAXIMO_BYTES + 1))
        with self.assertRaises(ErrorValidacion):
            solicitudes.copiar_documento(grande, datos["id"])

    def test_no_hay_dml_en_el_codigo_de_la_fase4(self):
        patrones = (
            re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
            re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
            re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
        )
        archivos = [RAIZ / "app" / "servicios" / "solicitudes.py"]
        archivos += sorted((RAIZ / "app" / "ui" / "padre").glob("*.py"))
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8")
            for patron in patrones:
                self.assertIsNone(patron.search(texto), f"{archivo}: {patron.pattern}")


if __name__ == "__main__":
    unittest.main()
