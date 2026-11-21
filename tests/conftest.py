"""Configuración común de pruebas.

Las pruebas de base de datos (test_sql, test_integracion_db) solo se ejecutan
si mysql-connector está instalado y hay conexión con los datos de config.ini;
sin MySQL se omiten, para que ``pytest`` corra sin fallos en cualquier equipo.
"""
from __future__ import annotations

collect_ignore: list[str] = []

_PRUEBAS_BD = ["test_integracion_db.py", "test_sql.py"]


def _hay_base_de_datos() -> bool:
    try:
        from app.db import conectar

        conectar().close()
        return True
    except Exception:
        return False


if not _hay_base_de_datos():
    collect_ignore += _PRUEBAS_BD
