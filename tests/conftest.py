"""Configuración común de pruebas de la Entrega 5.

La interfaz usa tkinter y no depende de otros toolkits. Las pruebas estáticas
de interfaz ya están migradas; se excluyen solo los módulos heredados que
aún importan paquetes que no forman parte de esta entrega.
"""
from __future__ import annotations

collect_ignore = [
    "test_almacen.py",
    "test_formatos.py",
    "test_servicios.py",
    "test_solicitudes.py",
    "test_validaciones.py",
]

try:
    import mysql.connector  # noqa: F401
except ImportError:
    collect_ignore += ["test_integracion_db.py", "test_sql.py"]
