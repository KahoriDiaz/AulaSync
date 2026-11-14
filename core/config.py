"""Configuración central de la aplicación (lee .env)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


class Configuracion:
    def __init__(self) -> None:
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.db_user = os.getenv("DB_USER", "matricula_app")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_name = os.getenv("DB_NAME", "bd_matricula_paola_frassinetti")
        self._data_dir = os.getenv("DATA_DIR", "almacen/solicitudes")

    @property
    def data_dir(self) -> Path:
        ruta = Path(self._data_dir)
        if not ruta.is_absolute():
            ruta = BASE_DIR / ruta
        return ruta

    @property
    def tessdata_dir(self) -> Path:
        return BASE_DIR / "tesseract" / "tessdata"

    @property
    def tesseract_dir(self) -> Path:
        return BASE_DIR / "tesseract"


config = Configuracion()
