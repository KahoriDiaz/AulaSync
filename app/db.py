"""Acceso a datos: conexion MySQL, consultas SELECT y llamadas CALL a procedimientos.

El codigo Python NO contiene sentencias INSERT / UPDATE / DELETE: solo se usa
CALL sp_... (a traves de call_proc) y SELECT (a traves de query).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import mysql.connector

from app.config import config
from app.errores import ErrorBaseDatos, traducir_error


def conectar(database: str | None = None) -> mysql.connector.MySQLConnection:
    kwargs = dict(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        charset="utf8mb4",
        use_unicode=True,
        use_pure=True,
        autocommit=False,
    )
    kwargs["database"] = database or config.database
    try:
        return mysql.connector.connect(**kwargs)
    except mysql.connector.Error as exc:
        raise ErrorBaseDatos(
            "No se pudo conectar a la base de datos. Verifique que MySQL esté encendido "
            "y que config.ini tenga los datos correctos."
        ) from exc


def _envolver(exc: Exception) -> ErrorBaseDatos:
    if isinstance(exc, ErrorBaseDatos):
        return exc
    return ErrorBaseDatos(traducir_error(exc))


def query(sql: str, parametros: Sequence[Any] = ()) -> list[dict[str, Any]]:
    """Ejecuta un SELECT parametrizado y devuelve las filas como diccionarios."""
    cnx = conectar()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(parametros))
        return list(cursor.fetchall())
    except Exception as exc:
        raise _envolver(exc) from exc
    finally:
        cursor.close()
        cnx.close()


def query_uno(sql: str, parametros: Sequence[Any] = ()) -> dict[str, Any] | None:
    filas = query(sql, parametros)
    return filas[0] if filas else None


def call_proc(nombre: str, parametros: Sequence[Any] = ()) -> list[list[dict[str, Any]]]:
    """Llama a un procedimiento almacenado y devuelve sus conjuntos de resultados."""
    cnx = conectar()
    cursor = cnx.cursor(dictionary=True)
    try:
        marcadores = ", ".join(["%s"] * len(parametros))
        cursor.execute(f"CALL `{nombre}`({marcadores})", tuple(parametros))
        resultados: list[list[dict[str, Any]]] = []
        while True:
            if cursor.with_rows:
                filas = cursor.fetchall()
                if filas and isinstance(filas[0], dict):
                    resultados.append(list(filas))
                else:
                    columnas = [d[0] for d in cursor.description or []]
                    resultados.append(
                        [dict(zip(columnas, fila)) for fila in filas]
                    )
            if not cursor.nextset():
                break
        cnx.commit()
        return resultados
    except Exception as exc:
        cnx.rollback()
        raise _envolver(exc) from exc
    finally:
        cursor.close()
        cnx.close()


@contextmanager
def transaccion() -> Iterator[mysql.connector.cursor.MySQLCursor]:
    """Contexto transaccional: commit al salir bien, rollback ante cualquier error."""
    cnx = conectar()
    cursor = cnx.cursor(dictionary=True)
    try:
        yield cursor
        cnx.commit()
    except Exception as exc:
        cnx.rollback()
        raise _envolver(exc) from exc
    finally:
        cursor.close()
        cnx.close()


def version() -> str:
    """Devuelve la version del gestor MySQL (para el asistente de conexion)."""
    cnx = conectar()
    try:
        cursor = cnx.cursor()
        cursor.execute("SELECT VERSION()")
        fila = cursor.fetchone()
        cursor.close()
        return str(fila[0]) if fila else "desconocida"
    finally:
        cnx.close()


def contar_estudiantes() -> int:
    """Devuelve el numero de estudiantes (para probar que la BD ya existe)."""
    fila = query_uno("SELECT COUNT(*) AS total FROM ESTUDIANTE")
    return int(fila["total"]) if fila else 0
