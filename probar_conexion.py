"""Comprueba la conexión con la base de datos configurada en .env."""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.db import consultar_uno, conectar
from core.errores import ErrorApp

try:
    cnx = conectar()
except ErrorApp as exc:
    print(f"ERROR: {exc}")
    raise SystemExit(1)

try:
    cursor = cnx.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    total = consultar_uno("SELECT COUNT(*) AS total FROM ESTUDIANTE")
    print("Conexión exitosa")
    print(f"Versión de MySQL: {version}")
    print(f"Filas en ESTUDIANTE: {total['total']}")
finally:
    cnx.close()
