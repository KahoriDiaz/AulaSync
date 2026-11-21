"""Reglas del proyecto y estructura de la entrega (sin MySQL)."""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from app.servicios import reportes

RAIZ = Path(__file__).resolve().parent.parent
DIRS_IGNORADAS = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache", "tesseract"}
DML = re.compile(r"\b(?:INSERT\s+INTO|UPDATE\s+`?\w+`?\s+SET|DELETE\s+FROM)\b", re.IGNORECASE)
SCRIPTS = ("01_esquema", "02_usuario", "03_procedimientos", "04_triggers",
           "05_datos_prueba", "06_consultas")


def _leer(relativo: str) -> str:
    return (RAIZ / relativo).read_text(encoding="utf-8")


def _py_de_la_app() -> list[Path]:
    rutas = list((RAIZ / "app").rglob("*.py")) + list((RAIZ / "ocr").rglob("*.py"))
    return rutas + [RAIZ / "main.py"]


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
    def test_python_sin_insert_update_delete(self) -> None:
        """Python solo usa CALL sp_... y SELECT: falla si aparece DML en un .py."""
        for ruta in _py_de_la_app():
            texto = ruta.read_text(encoding="utf-8")
            with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                self.assertIsNone(DML.search(texto), f"DML directo en {ruta.relative_to(RAIZ)}")

    def test_detector_de_dml_funciona(self) -> None:
        for sentencia in ("INSERT INTO ESTUDIANTE VALUES (1)", "update MATRICULA set Estado='x'",
                          "DELETE FROM LOGRO"):
            self.assertIsNotNone(DML.search(sentencia))
        self.assertIsNone(DML.search("SELECT * FROM ESTUDIANTE"))

    def test_sin_otros_toolkits_graficos(self) -> None:
        for ruta in RAIZ.rglob("*.py"):
            if DIRS_IGNORADAS.intersection(ruta.relative_to(RAIZ).parts):
                continue
            for modulo in _modulos_importados(ruta):
                self.assertFalse(modulo.startswith(("PySide", "PyQt")), ruta)
                self.assertNotEqual(modulo, "wx", ruta)

    def test_sin_codigo_comentado(self) -> None:
        patron = re.compile(r"^\s*#\s*(def |class |import |from \w+ import|return\b|self\.\w+\(|\w+ = )")
        for ruta in _py_de_la_app():
            for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ)), linea=numero):
                    self.assertIsNone(patron.match(linea), linea)

    def test_no_quedan_modulos_de_solicitudes(self) -> None:
        for relativo in (
            "app/servicios/solicitudes.py", "app/servicios/vacantes.py",
            "app/servicios/automatizacion.py", "app/ui/secretaria/bandeja.py",
            "app/ui/secretaria/revision.py", "app/ui/secretaria/revision_vacante.py",
            "app/ui/secretaria/subir_ficha.py", "app/ui/secretaria/subir_constancia.py",
            "datos_demo", "data/solicitudes", "data/perfiles",
        ):
            with self.subTest(relativo=relativo):
                self.assertFalse((RAIZ / relativo).exists())


class TestScriptsSQL(unittest.TestCase):
    def test_sql_y_script_bd_son_identicos(self) -> None:
        for nombre in SCRIPTS:
            with self.subTest(script=nombre):
                self.assertEqual(_leer(f"sql/{nombre}.sql"), _leer(f"script_bd/{nombre}.sql"))

    def test_situacion_final_con_tilde(self) -> None:
        self.assertIn("'REQUIERE RECUPERACIÓN'", _leer("script_bd/01_esquema.sql"))

    def test_sin_alter_table_y_solo_usuario_es_adicional(self) -> None:
        sql = "\n".join(_leer(f"script_bd/{nombre}.sql") for nombre in SCRIPTS)
        self.assertNotIn("ALTER TABLE", sql.upper())
        self.assertEqual(len(re.findall(r"CREATE\s+TABLE\b", sql, re.IGNORECASE)), 13)

    def test_hay_procedimientos_de_mantenimiento_para_todas_las_tablas(self) -> None:
        sql = _leer("sql/03_procedimientos.sql")
        for nombre in (
            "sp_estudiante_insertar", "sp_estudiante_actualizar", "sp_estudiante_eliminar",
            "sp_padre_insertar", "sp_padre_actualizar", "sp_padre_eliminar",
            "sp_contacto_insertar", "sp_contacto_actualizar", "sp_contacto_eliminar",
            "sp_ie_insertar", "sp_ie_actualizar", "sp_ie_eliminar",
            "sp_constancia_insertar", "sp_constancia_actualizar", "sp_constancia_eliminar",
            "sp_logro_insertar", "sp_logro_actualizar", "sp_logro_eliminar",
            "sp_registrar_matricula", "sp_actualizar_estado_matricula", "sp_cambiar_seccion",
            "sp_eliminar_matricula", "sp_tiene_padres_insertar", "sp_tiene_padres_eliminar",
            "sp_hermandad_insertar", "sp_hermandad_eliminar", "sp_nee_insertar", "sp_nee_eliminar",
            "sp_hermanos_ie_insertar", "sp_hermanos_ie_eliminar",
            "sp_secretaria_insertar", "sp_secretaria_actualizar", "sp_secretaria_eliminar",
        ):
            with self.subTest(procedimiento=nombre):
                self.assertRegex(sql, rf"CREATE\s+PROCEDURE\s+{nombre}\s*\(")

    def test_sp_cupos_seccion_cuenta_solo_matriculados(self) -> None:
        sql = _leer("sql/03_procedimientos.sql")
        inicio = sql.index("CREATE PROCEDURE sp_cupos_seccion")
        self.assertIn("ESTADO = 'MATRICULADO'", sql[inicio:inicio + 1200].upper())

    def test_seis_consultas_con_join(self) -> None:
        con_join = [r.numero for r in reportes.todos() if " JOIN " in r.sql.upper()]
        self.assertEqual(con_join, [1, 3, 4, 8, 9, 10])
        self.assertEqual(len(reportes.todos()), 10)


class TestEntrega(unittest.TestCase):
    def test_archivos_de_entrega(self) -> None:
        for relativo in ("build.bat", "empaquetar.bat", "empaquetar.ps1", "LEEME.txt",
                         "config.ini.example", "app/ui/selector_fecha.py"):
            with self.subTest(relativo=relativo):
                self.assertTrue((RAIZ / relativo).is_file())

    def test_build_y_empaquetado_sin_solicitudes(self) -> None:
        for relativo in ("build.bat", "empaquetar.ps1"):
            texto = _leer(relativo)
            with self.subTest(relativo=relativo):
                self.assertNotIn("solicitudes", texto)
                self.assertNotIn("perfiles", texto)
                self.assertNotIn("datos_demo", texto)
        self.assertIn("--name AulaSync", _leer("build.bat"))

    def test_zip_excluye_entornos_cache_y_especificaciones(self) -> None:
        texto = _leer("empaquetar.ps1")
        for fragmento in ("'.venv'", "'.git'", "'__pycache__'", "'.pytest_cache'",
                          "'config.ini'", "'*.md'", "AulaSync.lnk", "Compress-Archive"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, texto)

    def test_leeme_con_usuarios_demo_por_dni(self) -> None:
        texto = _leer("LEEME.txt")
        for fragmento in ("MySQL 8.0", "secretaria123", "87733221", "87733222", "DNI",
                          "asistente de conexión"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, texto)
        for fragmento in ("padre123", "solicitud", "vacante"):
            self.assertNotIn(fragmento, texto.lower())

    def test_url_del_minedu_por_defecto(self) -> None:
        from app.config import config

        self.assertEqual(config.url_consulta_constancia or "https://constancia.minedu.gob.pe/",
                         "https://constancia.minedu.gob.pe/")
        self.assertIn("https://constancia.minedu.gob.pe/", _leer("config.ini.example"))


class TestMarcaYTema(unittest.TestCase):
    def test_todas_las_ventanas_llevan_la_marca(self) -> None:
        fuentes = "\n".join(r.read_text(encoding="utf-8") for r in (RAIZ / "app" / "ui").rglob("*.py"))
        titulos = re.findall(r'self\.title\(\s*\(?\s*f?"([^"]+)"', fuentes)
        titulos += re.findall(r'^\s+"(AulaSync - [^"]+)"', fuentes, re.MULTILINE)
        self.assertGreaterEqual(len(titulos), 5)
        for titulo in titulos:
            with self.subTest(titulo=titulo):
                self.assertTrue(titulo.startswith("AulaSync"), titulo)

    def test_ventanas_principales_aplican_el_tema(self) -> None:
        for relativo in ("main.py", "app/ui/asistente_conexion.py", "app/ui/login.py",
                         "app/ui/ventana_principal.py", "app/ui/secretaria/crud_generico.py"):
            with self.subTest(relativo=relativo):
                self.assertIn("aplicar_tema(", _leer(relativo))

    def test_sin_imagenes_de_marca(self) -> None:
        for ruta in (RAIZ / "app" / "ui").rglob("*.py"):
            texto = ruta.read_text(encoding="utf-8")
            with self.subTest(archivo=ruta.name):
                self.assertIsNone(re.search(r"\blogo\b", texto, re.IGNORECASE))
                self.assertNotIn("PhotoImage", texto)

    def test_formularios_con_dni_usan_el_componente(self) -> None:
        for relativo in ("app/ui/login.py", "app/ui/secretaria/realizar_matricula.py",
                         "app/ui/secretaria/crud_generico.py"):
            with self.subTest(relativo=relativo):
                self.assertIn("entry_dni", _leer(relativo))

    def test_fechas_con_selector_y_sin_strptime(self) -> None:
        for relativo in ("app/ui/secretaria/formulario_estudiante.py",
                         "app/ui/secretaria/formulario_padre.py",
                         "app/ui/secretaria/realizar_matricula.py",
                         "app/ui/secretaria/crud_generico.py"):
            texto = _leer(relativo)
            with self.subTest(relativo=relativo):
                self.assertIn("SelectorFecha", texto)
                self.assertNotIn("strptime", texto)
                self.assertNotIn("AAAA-MM-DD", texto)


if __name__ == "__main__":
    unittest.main()
