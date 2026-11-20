"""Servicio de padres/apoderados para la secretaria (§6.3 punto 4).

Todas las escrituras usan CALL sp_padre_* ; las lecturas usan SELECT.
Nunca INSERT / UPDATE / DELETE en Python.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from app import db


def listar_padres() -> list[dict[str, Any]]:
    return db.query(
        "SELECT DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento, "
        "OcupacionActual, GradoInstruccion, DomicilioActual, DistritoDomicilio, "
        "TelefonoFijo, Celular, CorreoElectronico "
        "FROM PADRE_APODERADO ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres"
    )


def obtener_padre(dni: str) -> Optional[dict[str, Any]]:
    return db.query_uno("SELECT * FROM PADRE_APODERADO WHERE DNI = %s", (dni,))


def insertar_padre(parametros: Sequence[Any]) -> None:
    db.call_proc("sp_padre_insertar", tuple(parametros))


def actualizar_padre(parametros: Sequence[Any]) -> None:
    db.call_proc("sp_padre_actualizar", tuple(parametros))


def eliminar_padre(dni: str) -> None:
    db.call_proc("sp_padre_eliminar", (dni,))
