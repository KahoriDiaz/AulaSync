"""Servicio de instituciones educativas para la secretaria (§6.3 punto 4).

Todas las escrituras usan CALL sp_ie_* ; las lecturas usan SELECT.
Nunca INSERT / UPDATE / DELETE en Python.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from app import db


def listar_instituciones() -> list[dict[str, Any]]:
    return db.query(
        "SELECT CodigoModularIE, NombreIE, TipoIE "
        "FROM INSTITUCION_EDUCATIVA ORDER BY NombreIE"
    )


def obtener_institucion(codigo_modular_ie: str) -> Optional[dict[str, Any]]:
    return db.query_uno(
        "SELECT * FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s",
        (codigo_modular_ie,),
    )


def insertar_institucion(parametros: Sequence[Any]) -> None:
    db.call_proc("sp_ie_insertar", tuple(parametros))


def actualizar_institucion(parametros: Sequence[Any]) -> None:
    db.call_proc("sp_ie_actualizar", tuple(parametros))


def eliminar_institucion(codigo_modular_ie: str) -> None:
    db.call_proc("sp_ie_eliminar", (codigo_modular_ie,))
