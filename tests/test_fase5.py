"""Pruebas de la fase 5: documentos, OCR, revisión y matrícula (§6.3)."""
from __future__ import annotations

import re
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import db, sesion as sesion_mod
from app.errores import ErrorConflicto, ErrorValidacion
from app.servicios import matricula, solicitudes as sol
from ocr import extraer_constancia, extraer_dni

RAIZ = Path(__file__).resolve().parent.parent
LINEAS_DNI = [
    ("DOCUMENTO NACIONAL DE IDENTIDAD", 92), ("DNI 70000001", 94),
    ("APELLIDO PATERNO", 90), ("QUISPE", 93), ("APELLIDO MATERNO", 90),
    ("MAMANI", 92), ("PRENOMBRES", 90), ("ANA SOFIA", 91),
    ("FECHA DE NACIMIENTO", 90), ("15/03/2014", 89), ("SEXO", 90), ("F", 90),
]
LINEAS_CONSTANCIA = [
    ("CODIGO VIRTUAL", 90), ("D4E5F6A7", 92), ("NIVEL PRIMARIA", 90),
    ("FECHA DE EMISION 15/12/2025 10:30:00", 90),
    ("CODIGO MODULAR 1137421-0", 90), ("TIPO ESTATAL", 86),
    ("2024 TERCER GRADO APROBADO", 85),
]


class CursorFalso:
    """Cursor que registra los CALL y devuelve filas de existencia prefijadas."""

    def __init__(self, existencia: dict[str, dict] | None = None, fallar_en: str = ""):
        self.llamadas: list[tuple[str, tuple]] = []
        self.existencia = existencia or {}
        self.fallar_en = fallar_en
        self.with_rows = False
        self._fila: dict | None = None

    @staticmethod
    def _tabla(sql: str) -> str:
        superior = sql.upper()
        for tabla in (
            "INSTITUCION_EDUCATIVA", "PADRE_APODERADO", "ESTUDIANTE_NEE",
            "ESTUDIANTE_HERMANOS_IE", "ESTUDIANTE", "CONSTANCIA_LOGROS",
            "TIENE_PADRES", "HERMANDAD", "LOGRO",
        ):
            if tabla in superior:
                return tabla
        return "OTRO"

    def execute(self, sql: str, parametros=()) -> None:
        if sql.lstrip().upper().startswith("CALL"):
            nombre = sql.split("`")[1]
            self.llamadas.append((nombre, tuple(parametros)))
            self.with_rows = False
            self._fila = None
            if nombre == self.fallar_en:
                raise RuntimeError("Cupo lleno")
            return
        fila = self.existencia.get(self._tabla(sql))
        self.with_rows = fila is not None
        self._fila = dict(fila) if fila else None

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return []

    def nextset(self):
        return False


class TestFase5(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        sol.configurar_directorio(Path(self.temporal.name) / "solicitudes")
        self.sesion_original = sesion_mod.autenticacion.sesion_activa
        self._iniciar_secretaria()
        self.parches = [
            patch.object(sol, "_ya_matriculado", return_value=False),
            patch.object(db, "query_uno", return_value=None),
            patch.object(matricula, "grado_siguiente", return_value="5.°"),
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

    def _iniciar_secretaria(self) -> None:
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=1, nombre_usuario="secretaria", rol="Secretaria",
            dni="87733221", nombres="Claudia", apellidos="Acosta Neira",
        ))

    def _solicitud_lista(self, con_dos_hermanos: bool = False):
        sesion_anterior = sesion_mod.autenticacion.sesion_activa
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=7, nombre_usuario="padre_demo", rol="Padre",
            dni="29481029", nombres="María", apellidos="Acosta",
        ))
        datos = sol.crear_borrador(date.today().year + 1, etapa="matricula")
        for dni in (["91234567", "91234568"] if con_dos_hermanos else ["91234567"]):
            alumno = sol.nuevo_alumno()
            alumno["ficha"].update({
                "DNI": dni, "Sexo": "F", "Nombres": "Ana", "ApellidoPaterno": "Quispe",
                "ApellidoMaterno": "Pérez", "FechaNacimiento": "2015-05-10",
                "DistritoNacimiento": "Cercado", "ProvinciaNacimiento": "Arequipa",
                "DepartamentoNacimiento": "Arequipa", "PaisNacimiento": "Perú",
                "DomicilioActual": "Calle Lima 123", "DistritoDomicilio": "Cercado",
                "Celular": "987654321", "LugarQueOcupa": len(datos["alumnos"]) + 1,
            })
            alumno["destino"] = {"nivel": "Secundaria", "grado": "5.°"}
            alumno["ie_procedencia"] = {
                "codigo_modular": "1137421-0", "nombre": "IE Ejemplo", "tipo": "Estatal",
            }
            datos["alumnos"].append(alumno)
        padre = sol.nuevo_padre("Padre")
        padre.update({
            "DNI": "29481029", "Sexo": "F", "Nombres": "María",
            "ApellidoPaterno": "Acosta", "ApellidoMaterno": "Porras",
            "FechaNacimiento": "1990-03-15", "GradoInstruccion": "Superior",
            "DomicilioActual": "Calle Lima 123", "DistritoDomicilio": "Cercado",
            "Celular": "987654321",
        })
        datos["padres"] = [padre]
        datos["dni_responsable"] = "29481029"
        datos["contacto_emergencia"] = {"nombre": "Rosa Pérez", "celular": "987654321"}
        sol.guardar_solicitud(datos)
        sesion_mod.autenticacion.cerrar_sesion()
        sesion_mod.autenticacion.iniciar_sesion(sesion_anterior)
        return datos

    def _enviar(self, datos):
        sesion_padre = sesion_mod.autenticacion.sesion_activa
        sesion_mod.autenticacion.iniciar_sesion(sesion_mod.Sesion(
            id_usuario=7, nombre_usuario="padre_demo", rol="Padre",
            dni="29481029", nombres="María", apellidos="Acosta",
        ))
        try:
            sol.enviar(datos["id"])
        finally:
            sesion_mod.autenticacion.cerrar_sesion()
            sesion_mod.autenticacion.iniciar_sesion(sesion_padre)

    def _transaccion_falsa(self, cursor):
        @contextmanager
        def contexto():
            try:
                yield cursor
            except Exception:
                raise
        return contexto()

    # ------------------------------------------------------------- pruebas
    def test_validacion_paso4_documentos_y_constancia(self):
        datos = self._solicitud_lista()
        alumno = datos["alumnos"][0]
        alumno["docs"]["dni"] = "data/solicitudes/no_existe.jpg"
        errores = sol.validar_paso(4, datos)
        self.assertTrue(any("falta el archivo" in e for e in errores))

        archivo = Path(self.temporal.name) / "dni.jpg"
        archivo.write_bytes(b"x")
        alumno["docs"]["dni"] = str(archivo)
        self.assertEqual(sol.validar_paso(4, datos), [])

        alumno["constancia"]["codigo_virtual"] = "MALO"
        self.assertTrue(any("código virtual" in e for e in sol.validar_paso(4, datos)))
        alumno["constancia"]["codigo_virtual"] = "D4E5F6A7"
        alumno["constancia"]["sin_constancia"] = True
        alumno["constancia"]["logros"] = [{"anio": "2024", "grado": "3.°", "situacion": "APROBADO"}]
        self.assertTrue(any("no ambos" in e for e in sol.validar_paso(4, datos)))

    def test_ocr_extrae_y_aplica_campos(self):
        campos = extraer_dni(LINEAS_DNI)
        ficha = {}
        aplicados = sol.aplicar_ocr_dni(campos, ficha)
        self.assertIn("DNI", aplicados)
        self.assertEqual(ficha["DNI"], "70000001")
        self.assertEqual(ficha["Nombres"], "Ana Sofia")
        constancia_campos, logros = extraer_constancia(LINEAS_CONSTANCIA)
        constancia = {}
        sol.aplicar_ocr_constancia(constancia_campos, logros, constancia)
        self.assertEqual(constancia["codigo_virtual"], "D4E5F6A7")
        self.assertEqual(len(constancia["logros"]), 1)
        self.assertEqual(constancia["logros"][0]["situacion"], "APROBADO")

    def test_verificacion_detecta_grado_no_coincidente(self):
        datos = self._solicitud_lista()
        avisos = matricula.aplicar_verificaciones(
            datos, {"91234567": {"seccion": "A", "nivel_ultimo": "Primaria",
                                 "grado_ultimo": "4.°", "situacion": "APROBADO"}},
            "87733221",
        )
        self.assertEqual(len(avisos), 1)
        self.assertIn("5.°", datos["alumnos"][0]["verificacion"]["grado_calculado"])
        avisos = matricula.aplicar_verificaciones(
            datos, {"91234567": {"seccion": "A", "nivel_ultimo": "Secundaria",
                                 "grado_ultimo": "4.°", "situacion": "APROBADO"}},
            "87733221",
        )
        self.assertEqual(avisos, [])

    def test_aprobacion_llama_procedimientos_en_orden(self):
        datos = self._solicitud_lista(con_dos_hermanos=True)
        self._enviar(datos)
        cursor = CursorFalso()
        with patch.object(db, "transaccion", side_effect=lambda: self._transaccion_falsa(cursor)):
            resultado = matricula.aprobar_y_matricular(datos["id"])
        nombres = [nombre for nombre, _ in cursor.llamadas]
        self.assertEqual(nombres[0], "sp_padre_insertar")
        self.assertIn("sp_ie_insertar", nombres)
        self.assertEqual(nombres.count("sp_estudiante_insertar"), 2)
        self.assertEqual(nombres.count("sp_tiene_padres_insertar"), 2)
        self.assertEqual(nombres.count("sp_hermandad_insertar"), 1)
        self.assertEqual(nombres.count("sp_registrar_matricula"), 2)
        self.assertEqual(nombres[-1], "sp_registrar_matricula")
        self.assertEqual(resultado["estado"], "Aprobada")
        self.assertTrue(sol.ruta_solicitud(datos["id"], "aprobadas").exists())
        self.assertFalse(sol.carpeta_solicitud(datos["id"] + ".procesando").exists())

    def test_aprobacion_con_existentes_usa_actualizar(self):
        datos = self._solicitud_lista()
        self._enviar(datos)
        existencia = {
            "PADRE_APODERADO": {"DNI": "29481029", "Nombres": "María"},
            "INSTITUCION_EDUCATIVA": {
                "CodigoModularIE": "1137421-0", "NombreIE": "IE Ejemplo", "TipoIE": "Estatal",
            },
            "ESTUDIANTE": {"DNI": "91234567", "IdContactoEmergencia": 12,
                           "CodigoModularIE": "1137421-0"},
        }
        cursor = CursorFalso(existencia)
        with patch.object(db, "transaccion", side_effect=lambda: self._transaccion_falsa(cursor)):
            matricula.aprobar_y_matricular(datos["id"])
        nombres = [nombre for nombre, _ in cursor.llamadas]
        self.assertIn("sp_padre_actualizar", nombres)
        self.assertIn("sp_ie_actualizar", nombres)
        self.assertIn("sp_estudiante_actualizar", nombres)
        self.assertNotIn("sp_padre_insertar", nombres)

    def test_fallo_en_bd_restaura_la_carpeta(self):
        datos = self._solicitud_lista()
        self._enviar(datos)
        cursor = CursorFalso(fallar_en="sp_registrar_matricula")
        with patch.object(db, "transaccion", side_effect=lambda: self._transaccion_falsa(cursor)):
            with self.assertRaises(Exception):
                matricula.aprobar_y_matricular(datos["id"])
        self.assertTrue(sol.ruta_solicitud(datos["id"]).exists())
        self.assertFalse(sol.carpeta_solicitud(datos["id"] + ".procesando").exists())
        self.assertEqual(sol.obtener(datos["id"])["estado"], "Enviada")

    def test_segunda_aprobacion_queda_bloqueada(self):
        datos = self._solicitud_lista()
        sol.carpeta_solicitud(datos["id"] + ".procesando").mkdir(parents=True)
        with self.assertRaises(ErrorConflicto):
            sol.iniciar_procesamiento(datos["id"])

    def test_sin_constancia_omite_constancia_y_logros(self):
        datos = self._solicitud_lista()
        self._enviar(datos)
        datos = sol.obtener(datos["id"])
        alumno = datos["alumnos"][0]
        alumno["constancia"]["sin_constancia"] = True
        sol.guardar_solicitud(datos)
        cursor = CursorFalso()
        with patch.object(db, "transaccion", side_effect=lambda: self._transaccion_falsa(cursor)):
            matricula.aprobar_y_matricular(
                datos["id"], decisiones={"91234567": {"seccion": "A", "sin_constancia": True}}
            )
        nombres = [nombre for nombre, _ in cursor.llamadas]
        self.assertNotIn("sp_constancia_insertar", nombres)
        self.assertNotIn("sp_logro_insertar", nombres)
        self.assertEqual(
            sol.obtener(datos["id"], "aprobadas")["alumnos"][0]["verificacion"]["estado"],
            matricula.SIN_CONSTANCIA,
        )

    def test_pares_de_hermandad_unicos_y_cupos(self):
        pares = matricula._pares_hermandad(["22222222", "11111111", "33333333"])
        self.assertEqual(pares, [("11111111", "22222222"), ("11111111", "33333333"),
                                 ("22222222", "33333333")])
        with patch.object(db, "call_proc", return_value=[]):
            self.assertEqual(matricula.cupos_seccion(2027, "Inicial", "3 a.", "A"),
                             {"Matriculados": 0, "Vacantes": 30})
        with patch.object(db, "call_proc", return_value=[[{"Matriculados": 7, "Vacantes": 23}]]):
            self.assertEqual(matricula.cupos_seccion(2027, "Inicial", "3 a.", "A")["Vacantes"], 23)

    def test_no_hay_dml_en_el_codigo_de_la_fase5(self):
        patron = re.compile(
            r"\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b", re.IGNORECASE
        )
        archivos = list((RAIZ / "app").rglob("*.py")) + list((RAIZ / "ocr").rglob("*.py"))
        encontrados = []
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8")
            if patron.search(texto):
                encontrados.append(str(archivo.relative_to(RAIZ)))
        self.assertEqual(encontrados, [])
