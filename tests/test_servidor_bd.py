"""MySQL portátil: arranque sin instalar nada (el servidor se simula)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app import servidor_bd as s

RAIZ = Path(__file__).resolve().parent.parent


class TestServidorPortatil(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        base = Path(self.temporal.name)
        self.parches = [
            patch.object(s, "MYSQL_DIR", base / "mysql"),
            patch.object(s, "PLANTILLA_DIR", base / "mysql_plantilla"),
            patch.object(s, "DATOS_DIR", base / "mysql_data"),
            patch.object(s.config, "guardar"),
        ]
        for parche in self.parches:
            parche.start()
        self.base = base

    def tearDown(self):
        for parche in reversed(self.parches):
            parche.stop()
        s._proceso = None
        self.temporal.cleanup()

    def _plantilla(self):
        (self.base / "mysql_plantilla" / "mysql").mkdir(parents=True)
        (self.base / "mysql_plantilla" / s.MARCA).write_text("ok", encoding="utf-8")

    def test_disponible_solo_con_mysqld(self):
        self.assertFalse(s.disponible())
        (self.base / "mysql" / "bin").mkdir(parents=True)
        (self.base / "mysql" / "bin" / "mysqld.exe").touch()
        self.assertTrue(s.disponible())

    def test_primera_vez_copia_la_plantilla_y_no_recarga_scripts(self):
        self._plantilla()
        proceso = MagicMock()
        with patch.object(s, "_puerto_abierto", return_value=False), \
             patch.object(s, "_encender", return_value=proceso) as encender, \
             patch.object(s, "_inicializar") as inicializar, \
             patch.object(s, "_preparar_base") as preparar:
            s.iniciar()
        self.assertTrue((self.base / "mysql_data" / s.MARCA).is_file())
        inicializar.assert_not_called()
        preparar.assert_not_called()
        encender.assert_called_once()
        datos = s.config.guardar.call_args.args[0]
        self.assertEqual((datos["host"], datos["port"], datos["user"]),
                         ("127.0.0.1", 3307, "matricula_app"))

    def test_sin_plantilla_inicializa_y_carga_los_scripts(self):
        with patch.object(s, "_puerto_abierto", return_value=False), \
             patch.object(s, "_encender", return_value=MagicMock()), \
             patch.object(s, "_inicializar") as inicializar, \
             patch.object(s, "_preparar_base") as preparar:
            s.iniciar()
        inicializar.assert_called_once()
        preparar.assert_called_once()

    def test_detener_solo_si_lo_encendio_esta_ejecucion(self):
        with patch.object(s, "_apagar") as apagar:
            s.detener()
            apagar.assert_not_called()
            s._proceso = MagicMock(poll=MagicMock(return_value=None))
            s.detener()
            apagar.assert_called_once()
        self.assertIsNone(s._proceso)

    def test_servidor_solo_local_en_puerto_propio(self):
        fuente = (RAIZ / "app" / "servidor_bd.py").read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', fuente)
        self.assertIn("PUERTO = 3307", fuente)
        self.assertIn("--bind-address", fuente)

    def test_build_copia_mysql_y_genera_la_plantilla(self):
        build = (RAIZ / "build.bat").read_text(encoding="utf-8")
        self.assertIn("copiar_mysql.ps1", build)
        self.assertIn("--plantilla", build)
        empaquetar = (RAIZ / "empaquetar.ps1").read_text(encoding="utf-8")
        self.assertIn("'mysql_data'", empaquetar)


if __name__ == "__main__":
    unittest.main()
