"""Contactos de emergencia (CONTACTO_EMERGENCIA)."""
from __future__ import annotations

from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar, ejecutar_filas
from core.errores import ErrorValidacion
from core.formatos import validar_celular


def _normalizar(datos: dict[str, Any]) -> tuple[str, str]:
    nombre = " ".join(str(datos.get("NombreContactoEmergencia") or "").split())
    if not nombre:
        raise ErrorValidacion("El nombre del contacto de emergencia es obligatorio.")
    if len(nombre) > 110:
        raise ErrorValidacion("El nombre del contacto no puede superar 110 caracteres.")
    celular = validar_celular(datos.get("CelularEmergencia"), "celular de emergencia")
    return nombre, celular


def crear_contacto(datos: dict[str, Any]) -> int:
    seguridad.requerir_secretaria()
    nombre, celular = _normalizar(datos)
    return ejecutar(
        "INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia) "
        "VALUES (%s, %s)",
        (nombre, celular),
    )


def obtener_contacto(id_contacto: int) -> dict[str, Any] | None:
    return consultar_uno(
        "SELECT * FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = %s", (id_contacto,)
    )


def listar_contactos() -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    return consultar(
        "SELECT * FROM CONTACTO_EMERGENCIA ORDER BY NombreContactoEmergencia"
    )


def actualizar_contacto(id_contacto: int, datos: dict[str, Any]) -> None:
    seguridad.requerir_secretaria()
    if not obtener_contacto(id_contacto):
        raise ErrorValidacion("El contacto de emergencia no existe.")
    nombre, celular = _normalizar(datos)
    ejecutar(
        "UPDATE CONTACTO_EMERGENCIA SET NombreContactoEmergencia = %s, CelularEmergencia = %s "
        "WHERE IdContactoEmergencia = %s",
        (nombre, celular, id_contacto),
    )


def eliminar_contacto(id_contacto: int) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas(
        "DELETE FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = %s", (id_contacto,)
    )


def buscar_o_crear_en_transaccion(cursor, nombre: str, celular: str) -> int:
    nombre, celular = _normalizar(
        {"NombreContactoEmergencia": nombre, "CelularEmergencia": celular}
    )
    cursor.execute(
        "SELECT IdContactoEmergencia FROM CONTACTO_EMERGENCIA "
        "WHERE NombreContactoEmergencia = %s AND CelularEmergencia = %s LIMIT 1",
        (nombre, celular),
    )
    fila = cursor.fetchone()
    if fila:
        return int(fila["IdContactoEmergencia"])
    cursor.execute(
        "INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia) "
        "VALUES (%s, %s)",
        (nombre, celular),
    )
    return int(cursor.lastrowid)
