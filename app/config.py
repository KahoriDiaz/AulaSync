"""Lectura y escritura de configuracion en config.ini (junto al ejecutable).

La clave del administrador de MySQL nunca se guarda en disco: solo se pide
transitoriamente en el asistente de conexion para crear la BD y el usuario
matricula_app.
"""
from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.ini"


class Configuracion:
    def __init__(self) -> None:
        self.parser = configparser.ConfigParser()
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "3306"))
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
                self.port = sec.getint("port", self.port)
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
