"""Instituciones educativas (INSTITUCION_EDUCATIVA)."""
from __future__ import annotations

import re
from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar, ejecutar_filas
from core.errores import ErrorValidacion
from core.formatos import TIPOS_IE, validar_opcion


def _normalizar(datos: dict[str, Any]) -> tuple[str, str | None, str | None]:
    codigo = str(datos.get("CodigoModularIE") or "").strip().upper()
    if not re.fullmatch(r"[0-9A-Z-]{1,10}", codigo):
        raise ErrorValidacion("El código modular debe tener hasta 10 caracteres alfanuméricos.")
    nombre = str(datos.get("NombreIE") or "").strip() or None
    if nombre and len(nombre) > 50:
        raise ErrorValidacion("El nombre de la institución no puede superar 50 caracteres.")
    tipo = str(datos.get("TipoIE") or "").strip() or None
    if tipo:
        tipo = validar_opcion(tipo, TIPOS_IE, "tipo de institución")
    return codigo, nombre, tipo


def crear_institucion(datos: dict[str, Any]) -> str:
    seguridad.requerir_secretaria()
    codigo, nombre, tipo = _normalizar(datos)
    ejecutar(
        "INSERT INTO INSTITUCION_EDUCATIVA (CodigoModularIE, NombreIE, TipoIE) "
        "VALUES (%s, %s, %s)",
        (codigo, nombre, tipo),
    )
    return codigo


def obtener_institucion(codigo: str) -> dict[str, Any] | None:
    return consultar_uno(
        "SELECT * FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", (codigo,)
    )


def listar_instituciones(filtro: str = "") -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    texto = f"%{filtro.strip()}%"
    return consultar(
        "SELECT * FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE LIKE %s OR NombreIE LIKE %s "
        "ORDER BY NombreIE, CodigoModularIE",
        (texto, texto),
    )


def actualizar_institucion(codigo: str, datos: dict[str, Any]) -> None:
    seguridad.requerir_secretaria()
    if not obtener_institucion(codigo):
        raise ErrorValidacion("La institución educativa no existe.")
    codigo_nuevo, nombre, tipo = _normalizar({**datos, "CodigoModularIE": codigo})
    ejecutar(
        "UPDATE INSTITUCION_EDUCATIVA SET NombreIE = %s, TipoIE = %s "
        "WHERE CodigoModularIE = %s",
        (nombre, tipo, codigo_nuevo),
    )


def eliminar_institucion(codigo: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas(
        "DELETE FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", (codigo,)
    )


def buscar_o_crear_en_transaccion(
    cursor, codigo: str, nombre: str | None = None, tipo: str | None = None
) -> str | None:
    if not str(codigo or "").strip():
        return None
    codigo, nombre, tipo = _normalizar(
        {"CodigoModularIE": codigo, "NombreIE": nombre, "TipoIE": tipo}
    )
    cursor.execute(
        "SELECT CodigoModularIE FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s",
        (codigo,),
    )
    fila = cursor.fetchone()
    if fila:
        return fila["CodigoModularIE"]
    cursor.execute(
        "INSERT INTO INSTITUCION_EDUCATIVA (CodigoModularIE, NombreIE, TipoIE) "
        "VALUES (%s, %s, %s)",
        (codigo, (nombre or "").strip()[:50] or None, tipo or None),
    )
    return codigo
