"""Configuración común de pruebas de la Entrega 5.

La interfaz es tkinter (sin PySide6) y las pruebas de la arquitectura anterior
se migran durante la fase 7; mientras tanto se excluyen de la recolección.
"""
from __future__ import annotations

collect_ignore = [
    "test_almacen.py",
    "test_formatos.py",
    "test_interfaz.py",
    "test_servicios.py",
    "test_solicitudes.py",
    "test_validaciones.py",
]

try:
    import mysql.connector  # noqa: F401
except ImportError:
    collect_ignore += ["test_integracion_db.py", "test_sql.py"]
