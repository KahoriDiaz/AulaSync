"""Pruebas de la fase 7: empaquetado, rutas del ejecutable y documentación."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import config as config_mod
from app import setup_bd
from ocr import lector

RAIZ = Path(__file__).resolve().parent.parent


def _leer(relativo: str) -> str:
    return (RAIZ / relativo).read_text(encoding="utf-8")


class TestEstructuraEntrega(unittest.TestCase):
    def test_archivos_de_entrega_existen(self):
        for relativo in (
            "build.bat",
            "empaquetar.bat",
            "empaquetar.ps1",
            "LEEME.txt",
            "config.ini.example",
            "documentos/MANUAL_USUARIO.md",
            "data/solicitudes/pendientes/.gitkeep",
            "data/solicitudes/aprobadas/.gitkeep",
            "data/solicitudes/rechazadas/.gitkeep",
        ):
            with self.subTest(relativo=relativo):
                self.assertTrue((RAIZ / relativo).is_file(), relativo)

    def test_no_se_versiona_config_ini_real(self):
        gitignore = _leer(".gitignore")
        for patron in ("config.ini", "dist/", "build/", "*.spec", "*.zip"):
            self.assertIn(patron, gitignore)
        self.assertFalse((RAIZ / "config.ini").exists())


class TestBuild(unittest.TestCase):
    def test_build_bat_incluye_opciones_y_archivos_fuera_del_exe(self):
        contenido = _leer("build.bat")
        for fragmento in (
            "--noconfirm --onedir --windowed --name MatriculaApp",
            "python -m PyInstaller --version",
            "python -m PyInstaller %OPTS% %TESS% main.py",
            '--add-data "sql;sql"',
            "--collect-submodules mysql.connector",
            "--hidden-import mysql.connector.plugins.caching_sha2_password",
            "--hidden-import mysql.connector.plugins.mysql_native_password",
            "--hidden-import mysql.connector.locales.eng",
            'if exist "tesseract\\tessdata\\spa.traineddata"',
            'copy /y "config.ini.example"',
            "data\\solicitudes",
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, contenido)

    def test_empaquetar_genera_la_estructura_del_zip(self):
        contenido = _leer("empaquetar.ps1")
        for fragmento in (
            "Entrega5_GrupoXX.zip",
            "MatriculaApp",
            "codigo_fuente",
            "script_bd",
            "documentos",
            "LEEME.txt",
            "config.ini",
            "Compress-Archive",
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, contenido)
        self.assertIn("powershell", _leer("empaquetar.bat").lower())


class TestRutasEmpaquetadas(unittest.TestCase):
    def test_rutas_de_desarrollo_y_scripts_sql(self):
        self.assertEqual(config_mod.USER_DIR, RAIZ)
        self.assertEqual(config_mod.RECURSOS_DIR, RAIZ)
        self.assertEqual(config_mod.CONFIG_FILE, RAIZ / "config.ini")
        self.assertEqual(config_mod.SOLICITUDES_DIR, RAIZ / "data" / "solicitudes")
        self.assertTrue(config_mod.CONFIG_FILE.name.endswith("config.ini"))
        self.assertEqual(len(setup_bd.SCRIPTS), 6)
        for relativo in setup_bd.SCRIPTS:
            with self.subTest(relativo=relativo):
                self.assertTrue((config_mod.RECURSOS_DIR / relativo).is_file())

    def test_rutas_congeladas_separan_exe_y_recursos(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            exe = base / "MatriculaApp" / "MatriculaApp.exe"
            exe.parent.mkdir(parents=True)
            exe.touch()
            internal = base / "MatriculaApp" / "_internal"
            internal.mkdir()
            with patch.object(config_mod.sys, "frozen", True, create=True), patch.object(
                config_mod.sys, "executable", str(exe)
            ), patch.object(config_mod.sys, "_MEIPASS", str(internal), create=True):
                usuario, recursos = config_mod._rutas()
            self.assertEqual(usuario, exe.parent)
            self.assertEqual(recursos, internal)
            self.assertEqual(usuario / "config.ini", exe.parent / "config.ini")

    def test_tesseract_empaquetado_y_tessdata(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            ejecutable = base / "tesseract" / "tesseract.exe"
            ejecutable.parent.mkdir(parents=True)
            ejecutable.touch()
            tessdata = ejecutable.parent / "tessdata"
            tessdata.mkdir()
            with patch.dict(os.environ, {}, clear=False), patch.object(
                config_mod.config, "tesseract_cmd", ""
            ), patch.object(config_mod.config, "USER_DIR", base), patch.object(
                config_mod.config, "RECURSOS_DIR", base
            ):
                self.assertEqual(lector.ruta_tesseract(), str(ejecutable))
                self.assertEqual(os.environ["TESSDATA_PREFIX"], str(tessdata))


class TestLEEME(unittest.TestCase):
    def test_instrucciones_y_credenciales(self):
        contenido = _leer("LEEME.txt")
        for fragmento in (
            "MySQL 8.0 instalado y en ejecución",
            "MatriculaApp.exe",
            "asistente de conexión",
            "secretaria123",
            "padre123",
            "Windows Defender",
            "config.ini",
            "Entrega5_GrupoXX.zip",
            "codigo_fuente/",
            "script_bd/",
            "documentos/",
        ):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, contenido)


if __name__ == "__main__":
    unittest.main()
