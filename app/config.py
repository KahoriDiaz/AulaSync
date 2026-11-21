"""Lectura y escritura de configuracion en config.ini (junto al ejecutable).

La clave del administrador de MySQL nunca se guarda en disco: solo se pide
transitoriamente en el asistente de conexion para crear la BD y el usuario
matricula_app.
"""
from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path
from typing import Any


def _rutas() -> tuple[Path, Path]:
    """Separa archivos editables del usuario de recursos empaquetados.

    Con PyInstaller ``--onedir`` los recursos (``sql``) quedan en ``_MEIPASS``,
    pero ``config.ini`` y ``data/`` deben estar junto al .exe para que el
    revisor pueda editarlos sin permisos de administrador.
    """
    if getattr(sys, "frozen", False):
        usuario = Path(sys.executable).resolve().parent
        recursos = Path(getattr(sys, "_MEIPASS", usuario))
        return usuario, recursos
    directorio = Path(__file__).resolve().parent.parent
    return directorio, directorio


USER_DIR, RECURSOS_DIR = _rutas()
BASE_DIR = RECURSOS_DIR  # alias de compatibilidad con código anterior
CONFIG_FILE = USER_DIR / "config.ini"
DATOS_DIR = USER_DIR / "data"
SOLICITUDES_DIR = DATOS_DIR / "solicitudes"


def _puerto(valor: str | None, por_defecto: int) -> int:
    """Convierte el puerto a entero; un valor vacío o inválido usa el predeterminado."""
    try:
        puerto = int(str(valor).strip())
    except (TypeError, ValueError):
        return por_defecto
    return puerto if 0 < puerto < 65536 else por_defecto


class Configuracion:
    def __init__(self) -> None:
        # Rutas expuestas también en la instancia para servicios y OCR.
        self.USER_DIR = USER_DIR
        self.RECURSOS_DIR = RECURSOS_DIR
        self.DATOS_DIR = DATOS_DIR
        self.SOLICITUDES_DIR = SOLICITUDES_DIR
        self.CONFIG_FILE = CONFIG_FILE
        self.parser = configparser.ConfigParser()
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = _puerto(os.getenv("DB_PORT"), 3306)
        self.user = os.getenv("DB_USER", "matricula_app")
        self.password = os.getenv("DB_PASSWORD", "matricula_app")
        self.database = os.getenv("DB_NAME", "bd_matricula")
        self.url_consulta_constancia = os.getenv("URL_CONSULTA_CONSTANCIA", "")
        self.tesseract_cmd = os.getenv("TESSERACT_CMD", "")
        self._cargar()

    def _cargar(self) -> None:
        if CONFIG_FILE.exists():
            self.parser.read(CONFIG_FILE, encoding="utf-8")
            if self.parser.has_section("bd"):
                sec = self.parser["bd"]
                self.host = sec.get("host", self.host)
                self.port = _puerto(sec.get("port"), self.port)
                self.user = sec.get("user", self.user)
                self.password = sec.get("password", self.password)
                self.database = sec.get("database", self.database)
            if self.parser.has_section("app"):
                self.url_consulta_constancia = self.parser["app"].get(
                    "url_consulta_constancia", self.url_consulta_constancia
                )
                self.tesseract_cmd = self.parser["app"].get(
                    "tesseract_cmd", self.tesseract_cmd
                )

    def guardar(self, datos: dict[str, Any]) -> None:
        """Guarda valores en config.ini (sin la clave del administrador MySQL)."""
        if not self.parser.has_section("bd"):
            self.parser.add_section("bd")
        bd = self.parser["bd"]
        bd["host"] = str(datos.get("host", self.host))
        bd["port"] = str(datos.get("port", self.port))
        bd["user"] = str(datos.get("user", self.user))
        bd["password"] = str(datos.get("password", self.password))
        bd["database"] = str(datos.get("database", self.database))
        if not self.parser.has_section("app"):
            self.parser.add_section("app")
        self.parser["app"]["url_consulta_constancia"] = str(
            datos.get("url_consulta_constancia", self.url_consulta_constancia)
        )
        self.parser["app"]["tesseract_cmd"] = str(
            datos.get("tesseract_cmd", self.tesseract_cmd)
        )
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            self.parser.write(f)
        # Mantener la instancia en memoria igual que el archivo recién escrito,
        # para que las conexiones siguientes usen los datos nuevos.
        self.host = bd["host"]
        self.port = int(bd["port"])
        self.user = bd["user"]
        self.password = bd["password"]
        self.database = bd["database"]
        self.url_consulta_constancia = self.parser["app"]["url_consulta_constancia"]
        self.tesseract_cmd = self.parser["app"]["tesseract_cmd"]

    @property
    def kwargs(self) -> dict[str, Any]:
        return dict(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
        )


config = Configuracion()
