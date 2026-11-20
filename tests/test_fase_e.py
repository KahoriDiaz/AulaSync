"""Fase E: integridad de la entrega, datos demo y restricciones de diseño."""
from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

from app.servicios import solicitudes as sol

RAIZ = Path(__file__).resolve().parent.parent
DIRS_IGNORADAS = {
    ".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache", "tesseract"
}
DML = re.compile(r"\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.IGNORECASE)


def _leer(relativo: str) -> str:
    return (RAIZ / relativo).read_text(encoding="utf-8")


def _py_de_la_app() -> list[Path]:
    rutas = list((RAIZ / "app").rglob("*.py"))
    rutas += list((RAIZ / "ocr").rglob("*.py"))
    if (RAIZ / "main.py").is_file():
        rutas.append(RAIZ / "main.py")
    return rutas


def _todos_los_py() -> list[Path]:
    return [
        ruta for ruta in RAIZ.rglob("*.py")
        if not DIRS_IGNORADAS.intersection(ruta.relative_to(RAIZ).parts)
    ]


def _modulos_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])
    return modulos


class TestRestriccionesCodigo(unittest.TestCase):
    def test_aplicacion_sin_dml_directo(self) -> None:
        for ruta in _py_de_la_app():
            arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                    self.assertIsNone(
                        DML.search(nodo.value),
                        f"DML directo en {ruta.relative_to(RAIZ)}",
                    )

    def test_sin_importaciones_de_otros_toolkits(self) -> None:
        for ruta in _todos_los_py():
            for modulo in _modulos_importados(ruta):
                self.assertFalse(modulo.startswith(("PySide", "PyQt")))
                self.assertNotEqual(modulo, "wx")

    def test_no_hay_rol_administrador_en_app_ni_sql(self) -> None:
        rutas = _py_de_la_app() + list((RAIZ / "script_bd").glob("*.sql"))
        for ruta in rutas:
            texto = ruta.read_text(encoding="utf-8")
            self.assertNotIn("Administrador", texto, ruta.relative_to(RAIZ))
            self.assertNotIn("ADMINISTRADOR", texto, ruta.relative_to(RAIZ))

    def test_sin_logo_ni_nombre_de_institucion_en_pantallas(self) -> None:
        for relativo in ("main.py", "app/ui/login.py", "app/ui/ventana_principal.py"):
            texto = _leer(relativo).lower()
            self.assertIsNone(re.search(r"\blogo\b", texto, re.IGNORECASE), relativo)
            self.assertNotIn("photoimage", texto, relativo)
            self.assertNotIn("bitmapimage", texto, relativo)


class TestEsquemaSinCambios(unittest.TestCase):
    def test_no_hay_alter_table_y_solo_usuario_es_adicional(self) -> None:
        sql = "\n".join(
            ruta.read_text(encoding="utf-8") for ruta in sorted((RAIZ / "script_bd").glob("*.sql"))
        )
        self.assertNotIn("ALTER TABLE", sql.upper())
        self.assertEqual(len(re.findall(r"CREATE\s+TABLE\b", sql, re.IGNORECASE)), 13)
        self.assertIn("CREATE TABLE USUARIO", sql)

    def test_sp_cupos_seccion_cuenta_solo_matriculados(self) -> None:
        sql = _leer("script_bd/03_procedimientos.sql")
        coincidencia = re.search(r"CREATE\s+PROCEDURE\s+sp_cupos_seccion", sql, re.IGNORECASE)
        self.assertIsNotNone(coincidencia)
        bloque = sql[coincidencia.start():coincidencia.start() + 1200].upper()
        self.assertIn("ESTADO = 'MATRICULADO'", bloque)


class TestDatosDemo(unittest.TestCase):
    def test_cubre_todas_las_combinaciones_validas(self) -> None:
        rutas = sorted((RAIZ / "datos_demo" / "solicitudes").rglob("solicitud.json"))
        self.assertEqual(len(rutas), 9)
        combinaciones: set[tuple[str, str]] = set()
        for ruta in rutas:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            combinaciones.add((sol.etapa_de(datos), datos["estado"]))
            self.assertTrue(datos["contacto"]["celular"], ruta)
            self.assertTrue(datos["alumnos"], ruta)
        esperado = {
            ("vacante", "Borrador"), ("vacante", "Enviada"),
            ("vacante", "Observada"), ("vacante", "Rechazada"),
            ("matricula", "Vacante aceptada"), ("matricula", "Enviada"),
            ("matricula", "Observada"), ("matricula", "Aprobada"),
            ("matricula", "Rechazada"),
        }
        self.assertEqual(combinaciones, esperado)

    def test_hay_una_solicitud_antigua_para_el_aviso_de_siete_dias(self) -> None:
        datos = json.loads((RAIZ / "datos_demo/solicitudes/pendientes/SOL-2027-0002/solicitud.json").read_text(encoding="utf-8"))
        self.assertTrue(sol.sin_respuesta(datos))

    def test_build_copia_los_ejemplos_fuera_de_la_bandeja_real(self) -> None:
        build = _leer("build.bat")
        self.assertIn("datos_demo\\solicitudes", build)
        self.assertIn("xcopy", build)
        fuente = _leer("empaquetar.ps1")
        self.assertIn("'data'", fuente)
        self.assertIn("datos_demo\\solicitudes", fuente)
        self.assertIn("config.ini", fuente)
        self.assertIn("'*.json'", fuente)
        self.assertNotIn("'datos_demo'", fuente)


class TestEntradaDni(unittest.TestCase):
    def test_componente_solo_acepta_hasta_8_digitos(self) -> None:
        fuente = _leer("app/ui/componentes.py")
        for fragmento in (
            r"[0-9]{0,8}", 'validate="key"', '"%P"', "def normalizar_dni",
            "def entry_dni",
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, fuente)

    def test_formularios_de_dni_usan_el_componente(self) -> None:
        for relativo in (
            "app/ui/login.py",
            "app/ui/padre/solicitar_vacante.py",
            "app/ui/padre/asistente_solicitud.py",
        ):
            with self.subTest(relativo=relativo):
                self.assertIn("entry_dni", _leer(relativo))

    def test_dialogos_de_texto_tambien_recortan_el_dni(self) -> None:
        principal = _leer("app/ui/ventana_principal.py")
        asistente = _leer("app/ui/padre/asistente_solicitud.py")
        self.assertIn("_limitar_dnis", principal)
        self.assertIn("normalizar_dni", principal)
        self.assertIn("normalizar_dni(", asistente)
        self.assertIn("El DNI debe tener 8 dígitos", asistente)


class TestDocumentacionEntrega(unittest.TestCase):
    def test_documentos_del_nuevo_flujo_existen(self) -> None:
        for relativo in (
            "documentos/DISENO_FLUJO.md", "documentos/CAPTURAS.md",
            "documentos/MANUAL_USUARIO.md", "LEEME.txt",
        ):
            with self.subTest(relativo=relativo):
                self.assertTrue((RAIZ / relativo).is_file(), relativo)

    def test_documentacion_explica_etapas_y_decisiones(self) -> None:
        diseno = _leer("documentos/DISENO_FLUJO.md")
        manual = _leer("documentos/MANUAL_USUARIO.md")
        leeme = _leer("LEEME.txt")
        for fragmento in (
            "Vacante aceptada", "no reserva cupo", "No se agrega el rol",
            "30 alumnos por sección", "USUARIO", "fn_grado_siguiente",
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, diseno)
        for fragmento in ("Solicitar vacante", "Completar matrícula", "Vacantes por atender"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, manual)
        for fragmento in ("Flujo en dos etapas", "Datos demo incluidos", "Capturas pendientes"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, leeme)

    def test_capturas_quedan_registradas_como_pendientes(self) -> None:
        capturas = _leer("documentos/CAPTURAS.md")
        self.assertIn("pendientes de capturar", capturas)
        for fragmento in ("01_login_crear_cuenta.png", "07_matricula_paso1_bloqueado.png"):
            self.assertIn(fragmento, capturas)


if __name__ == "__main__":
    unittest.main()
