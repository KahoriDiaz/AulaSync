"""Distribución por secciones y padrón de matriculados (§6.3 punto 5).

Solo se consumen procedimientos (`sp_cupos_seccion`, `sp_padron`,
`sp_cambiar_seccion`) y consultas de lectura. Una solicitud pendiente nunca
reserva cupo: los procedimientos cuentan únicamente matrículas `Matriculado`.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app import db
from app.errores import ErrorValidacion
from app.servicios import matricula, solicitudes

COLUMNAS_CUPOS = ("AñoEscolar", "Nivel", "Grado", "Seccion", "Matriculados", "Vacantes")
COLUMNAS_PADRON = ("DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres",
                   "Nivel", "Grado", "Seccion", "Estado")
CAPACIDAD = 30


def anios() -> list[int]:
    """Años con matrículas, de más reciente a más antiguo."""
    filas = db.query(
        "SELECT DISTINCT `AñoEscolar` AS anio FROM MATRICULA ORDER BY anio DESC"
    )
    encontrados = [int(fila["anio"]) for fila in filas if fila.get("anio")]
    actual = date.today().year
    return sorted(set(encontrados) | {actual, actual + 1}, reverse=True)


def niveles() -> tuple[str, ...]:
    return tuple(solicitudes.NIVELES)


def grados(nivel: str) -> tuple[str, ...]:
    return solicitudes.NIVELES.get(nivel, ())


def secciones(nivel: str) -> tuple[str, ...]:
    return matricula.SECCIONES.get(nivel, ())


def cupos_seccion(anio: int, nivel: str, grado: str, seccion: str) -> dict[str, Any]:
    """Cupo de una sección; si no hay matriculados, devuelve 0 y 30 vacantes."""
    conjuntos = db.call_proc("sp_cupos_seccion", (anio, nivel, grado, seccion))
    fila = conjuntos[0][0] if conjuntos and conjuntos[0] else {}
    return {
        "AñoEscolar": fila.get("AñoEscolar", anio),
        "Nivel": fila.get("Nivel", nivel),
        "Grado": fila.get("Grado", grado),
        "Seccion": fila.get("Seccion", seccion),
        "Matriculados": int(fila.get("Matriculados") or 0),
        "Vacantes": int(fila.get("Vacantes") or 0) if fila else CAPACIDAD,
    }


def resumen(anio: int, nivel: str | None = None) -> list[dict[str, Any]]:
    """Todas las combinaciones nivel/grado/sección con sus vacantes."""
    niveles_a_mostrar = (nivel,) if nivel else niveles()
    resultado: list[dict[str, Any]] = []
    for nivel_actual in niveles_a_mostrar:
        for grado in grados(nivel_actual):
            for seccion in secciones(nivel_actual):
                resultado.append(cupos_seccion(anio, nivel_actual, grado, seccion))
    return resultado


def sugerir_seccion(anio: int, nivel: str, grado: str) -> str:
    """Sección con más vacantes para el nivel y grado indicados."""
    opciones = [
        cupos_seccion(anio, nivel, grado, seccion) for seccion in secciones(nivel)
    ]
    if not opciones:
        return ""
    return max(opciones, key=lambda fila: fila["Vacantes"])["Seccion"]


def padron(
    anio: int, nivel: str | None = None, grado: str | None = None,
    seccion: str | None = None,
) -> list[dict[str, Any]]:
    """Lista de matriculados; los filtros vacíos significan 'todos'."""
    conjuntos = db.call_proc("sp_padron", (
        anio, nivel or None, grado or None, seccion or None
    ))
    return list(conjuntos[0]) if conjuntos and conjuntos[0] else []


def nivel_matriculado(dni: str, anio: int) -> str:
    fila = db.query_uno(
        "SELECT Nivel FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = %s",
        (dni, anio),
    )
    return str(fila["Nivel"]) if fila and fila.get("Nivel") else ""


def mover_seccion(dni: str, anio: int, nueva_seccion: str) -> None:
    """Cambia de sección validando que exista para el nivel del alumno."""
    seccion = str(nueva_seccion).strip().upper()
    nivel = nivel_matriculado(dni, anio)
    if nivel and seccion not in secciones(nivel):
        raise ErrorValidacion(
            f"La sección {seccion} no existe para el nivel {nivel}."
        )
    db.call_proc("sp_cambiar_seccion", (dni, anio, seccion))
