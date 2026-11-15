"""Acceso a MySQL: conexión, consultas parametrizadas, transacciones y procedimientos."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Sequence

import mysql.connector

from core.config import config
from core.errores import ErrorBaseDatos, traducir_error


def conectar() -> mysql.connector.MySQLConnection:
    try:
        return mysql.connector.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=False,
        )
    except mysql.connector.Error as exc:
        raise ErrorBaseDatos(
            "No se pudo conectar a la base de datos. Verifique que MySQL esté encendido "
            "y que el archivo .env tenga los datos correctos."
        ) from exc


def _envolver(exc: Exception) -> ErrorBaseDatos:
    if isinstance(exc, ErrorBaseDatos):
        return exc
    return ErrorBaseDatos(traducir_error(exc))


def consultar(sql: str, parametros: Sequence[Any] = ()) -> list[dict[str, Any]]:
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


def consultar_uno(sql: str, parametros: Sequence[Any] = ()) -> dict[str, Any] | None:
    filas = consultar(sql, parametros)
    return filas[0] if filas else None


def ejecutar(sql: str, parametros: Sequence[Any] = ()) -> int:
    """Ejecuta un INSERT/UPDATE/DELETE y confirma. Devuelve lastrowid."""
    cnx = conectar()
    cursor = cnx.cursor()
    try:
        cursor.execute(sql, tuple(parametros))
        cnx.commit()
        return int(cursor.lastrowid or 0)
    except Exception as exc:
        cnx.rollback()
        raise _envolver(exc) from exc
    finally:
        cursor.close()
        cnx.close()


def ejecutar_filas(sql: str, parametros: Sequence[Any] = ()) -> int:
    """Ejecuta una modificación y devuelve la cantidad de filas afectadas."""
    cnx = conectar()
    cursor = cnx.cursor()
    try:
        cursor.execute(sql, tuple(parametros))
        cnx.commit()
        return int(cursor.rowcount or 0)
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


def _llamar(cursor: Any, nombre: str, parametros: Sequence[Any]) -> None:
    """Ejecuta un procedimiento con parámetros vinculados (sin callproc obsoleto)."""
    marcadores = ", ".join(["%s"] * len(parametros))
    cursor.execute(f"CALL `{nombre}`({marcadores})", tuple(parametros))


def _resultados(cursor: Any, nombre: str, parametros: Iterable[Any]) -> list[list[dict[str, Any]]]:
    _llamar(cursor, nombre, tuple(parametros))
    resultados: list[list[dict[str, Any]]] = []
    while True:
        if cursor.with_rows:
            filas = cursor.fetchall()
            if filas and isinstance(filas[0], dict):
                resultados.append(list(filas))
            else:
                columnas = [d[0] for d in cursor.description or []]
                resultados.append([dict(zip(columnas, fila)) for fila in filas])
        if not cursor.nextset():
            break
    return resultados


def llamar_procedimiento(
    nombre: str, parametros: Sequence[Any] = ()
) -> list[list[dict[str, Any]]]:
    """Llama a un procedimiento almacenado y devuelve sus conjuntos de resultados."""
    cnx = conectar()
    cursor = cnx.cursor(dictionary=True)
    try:
        resultados = _resultados(cursor, nombre, parametros)
        cnx.commit()
        return resultados
    except Exception as exc:
        cnx.rollback()
        raise _envolver(exc) from exc
    finally:
        cursor.close()
        cnx.close()


def llamar_procedimiento_en(
    cursor: mysql.connector.cursor.MySQLCursor,
    nombre: str,
    parametros: Sequence[Any] = (),
) -> list[list[dict[str, Any]]]:
    """Llama a un procedimiento usando un cursor de una transacción existente."""
    try:
        return _resultados(cursor, nombre, parametros)
    except Exception as exc:
        raise _envolver(exc) from exc


def ejecutar_procedimiento_en(
    cursor: mysql.connector.cursor.MySQLCursor,
    nombre: str,
    parametros: Sequence[Any] = (),
) -> None:
    """Ejecuta un procedimiento en una transacción y descarta sus resultados."""
    try:
        _llamar(cursor, nombre, tuple(parametros))
        while True:
            if cursor.with_rows:
                cursor.fetchall()
            if not cursor.nextset():
                break
    except Exception as exc:
        raise _envolver(exc) from exc
