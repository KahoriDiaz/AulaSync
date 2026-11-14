"""Hermandad entre estudiantes (HERMANDAD)."""
from __future__ import annotations

from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar_filas, llamar_procedimiento
from core.errores import ErrorValidacion
from core.formatos import validar_dni


def _par(dni_a: str, dni_b: str) -> tuple[str, str]:
    a = validar_dni(dni_a, "DNI del primer hermano")
    b = validar_dni(dni_b, "DNI del segundo hermano")
    if a == b:
        raise ErrorValidacion("Un estudiante no puede ser hermano de sí mismo.")
    return a, b


def crear_hermandad(dni_a: str, dni_b: str) -> None:
    seguridad.requerir_secretaria()
    a, b = _par(dni_a, dni_b)
    for dni in (a, b):
        if not consultar_uno("SELECT 1 FROM ESTUDIANTE WHERE DNI = %s", (dni,)):
            raise ErrorValidacion(f"El estudiante con DNI {dni} no existe.")
    if consultar_uno(
        "SELECT 1 FROM HERMANDAD WHERE (DNI_HermanoA = %s AND DNI_HermanoB = %s) "
        "OR (DNI_HermanoA = %s AND DNI_HermanoB = %s)",
        (a, b, b, a),
    ):
        raise ErrorValidacion("La hermandad ya está registrada.")
    ejecutar_filas(
        "INSERT INTO HERMANDAD (DNI_HermanoA, DNI_HermanoB) VALUES (%s, %s)", (a, b)
    )


def eliminar_hermandad(dni_a: str, dni_b: str) -> None:
    seguridad.requerir_secretaria()
    a, b = _par(dni_a, dni_b)
    ejecutar_filas(
        "DELETE FROM HERMANDAD WHERE (DNI_HermanoA = %s AND DNI_HermanoB = %s) "
        "OR (DNI_HermanoA = %s AND DNI_HermanoB = %s)",
        (a, b, b, a),
    )


def listar_hermanos(dni: str) -> list[dict[str, Any]]:
    resultados = llamar_procedimiento("sp_listar_hermanos", (validar_dni(dni),))
    return resultados[0] if resultados else []


def listar_hermandades() -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    return consultar(
        "SELECT h.DNI_HermanoA, h.DNI_HermanoB, "
        "CONCAT(a.ApellidoPaterno, ' ', a.ApellidoMaterno, ', ', a.Nombres) AS HermanoA, "
        "CONCAT(b.ApellidoPaterno, ' ', b.ApellidoMaterno, ', ', b.Nombres) AS HermanoB "
        "FROM HERMANDAD h "
        "INNER JOIN ESTUDIANTE a ON a.DNI = h.DNI_HermanoA "
        "INNER JOIN ESTUDIANTE b ON b.DNI = h.DNI_HermanoB "
        "ORDER BY a.ApellidoPaterno, b.ApellidoPaterno"
    )


def insertar_en_transaccion(cursor, dni_a: str, dni_b: str) -> None:
    a, b = _par(dni_a, dni_b)
    cursor.execute(
        "SELECT 1 FROM HERMANDAD WHERE (DNI_HermanoA = %s AND DNI_HermanoB = %s) "
        "OR (DNI_HermanoA = %s AND DNI_HermanoB = %s)",
        (a, b, b, a),
    )
    if cursor.fetchone() is not None:
        return
    cursor.execute(
        "INSERT INTO HERMANDAD (DNI_HermanoA, DNI_HermanoB) VALUES (%s, %s)", (a, b)
    )
