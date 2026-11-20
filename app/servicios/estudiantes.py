"""Servicio de estudiantes para la secretaria (§6.3 punto 4).

Todas las escrituras usan CALL sp_estudiante_* ; las lecturas usan SELECT.
Nunca INSERT / UPDATE / DELETE en Python.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from app import db


def listar_estudiantes() -> list[dict[str, Any]]:
    return db.query(
        "SELECT DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento, "
        "DistritoNacimiento, ProvinciaNacimiento, DepartamentoNacimiento, PaisNacimiento, "
        "DomicilioActual, DistritoDomicilio, Celular, CorreoElectronico, Religion, "
        "LugarQueOcupa, TipoAtencion, EnfermedadCronica, ViveConPadre, ViveConMadre, "
        "ElPadreVive, LaMadreVive, IdContactoEmergencia, CodigoModularIE, DNI_Apoderado "
        "FROM ESTUDIANTE ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres"
    )


def obtener_estudiante(dni: str) -> Optional[dict[str, Any]]:
    return db.query_uno("SELECT * FROM ESTUDIANTE WHERE DNI = %s", (dni,))


def insertar_estudiante(parametros: Sequence[Any]) -> None:
    """parametros en el orden de sp_estudiante_insertar (sin el OUT id_contacto)."""
    db.call_proc("sp_estudiante_insertar", tuple(parametros))


def actualizar_estudiante(parametros: Sequence[Any]) -> None:
    db.call_proc("sp_estudiante_actualizar", tuple(parametros))


def eliminar_estudiante(dni: str) -> None:
    db.call_proc("sp_estudiante_eliminar", (dni,))


def buscar_estudiantes(
    apellido_paterno: str = "", apellido_materno: str = "", nombres: str = ""
) -> list[dict[str, Any]]:
    return db.call_proc(
        "sp_buscar_estudiante", (apellido_paterno, apellido_materno, nombres)
    )[0]
