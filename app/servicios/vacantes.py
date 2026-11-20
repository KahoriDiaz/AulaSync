"""Disponibilidad referencial de vacantes y consulta de antecedentes (Fase B).

Solo se usan ``CALL sp_cupos_seccion`` y consultas SELECT: una solicitud,
incluso con la vacante aceptada, no reserva cupo ni escribe en la BD.
Los resultados de :func:`vacantes_por_grado` son únicamente números.
"""
from __future__ import annotations

from typing import Any

from app import db
from app.servicios import matricula, solicitudes

CAPACIDAD = matricula.CAPACIDAD if hasattr(matricula, "CAPACIDAD") else 30
SECCIONES = matricula.SECCIONES


def cupos_por_seccion(anio: int, nivel: str, grado: str) -> list[dict[str, Any]]:
    """Vacantes por sección para el nivel/grado solicitado."""
    filas: list[dict[str, Any]] = []
    for seccion in SECCIONES.get(nivel, ()):
        conjuntos = db.call_proc("sp_cupos_seccion", (anio, nivel, grado, seccion))
        fila = conjuntos[0][0] if conjuntos and conjuntos[0] else {}
        filas.append({
            "Seccion": seccion,
            "Matriculados": int(fila.get("Matriculados") or 0),
            "Vacantes": int(fila.get("Vacantes") or 0) if fila else CAPACIDAD,
        })
    return filas


def vacantes_por_grado(anio: int, nivel: str, grado: str) -> int:
    """Total de vacantes del grado; solo devuelve un número."""
    return sum(fila["Vacantes"] for fila in cupos_por_seccion(anio, nivel, grado))


def historial_alumno(dni: str) -> dict[str, Any]:
    """Devuelve si el alumno existe y su última matrícula, sin exponer otros DNIs."""
    estudiante = db.query_uno(
        "SELECT Nombres, ApellidoPaterno, ApellidoMaterno FROM ESTUDIANTE "
        "WHERE DNI = %s",
        (str(dni),),
    )
    fila = db.query_uno(
        "SELECT `AñoEscolar` AS anio, Nivel, Grado, Seccion, Estado "
        "FROM MATRICULA WHERE DNI_Estudiante = %s "
        "ORDER BY `AñoEscolar` DESC LIMIT 1",
        (str(dni),),
    )
    if estudiante is None and fila is None:
        return {"existe": False, "ultima": None}
    nombres = " ".join(str(estudiante.get(campo) or "") for campo in (
        "Nombres", "ApellidoPaterno", "ApellidoMaterno"
    )).strip() if estudiante else ""
    if fila is None:
        return {"existe": True, "ultima": None, "nombres": nombres}
    return {
        "existe": True,
        "ultima": {
            "anio": fila.get("anio", ""),
            "nivel": fila.get("Nivel", ""),
            "grado": fila.get("Grado", ""),
            "seccion": fila.get("Seccion", ""),
            "estado": fila.get("Estado", ""),
            "nombres": nombres,
        },
    }


def _nivel_de_grado(grado: str) -> str:
    """Infiere el nivel al que pertenece un grado cursado."""
    texto = str(grado or "")
    if "a." in texto:
        return "Inicial"
    return "Primaria" if texto in solicitudes.NIVELES["Primaria"] else "Secundaria"


def situacion_final(dni: str) -> dict[str, str]:
    """Última situación final registrada en LOGRO para el alumno indicado."""
    fila = db.query_uno(
        "SELECT l.`AñoEscolar` AS anio, l.GradoCursado AS grado, "
        "l.SituacionFinal AS situacion "
        "FROM LOGRO l JOIN CONSTANCIA_LOGROS c ON c.CodigoVirtual = l.CodigoVirtual "
        "WHERE c.DNI_Estudiante = %s ORDER BY l.`AñoEscolar` DESC LIMIT 1",
        (str(dni),),
    )
    if fila is None:
        return {}
    grado = str(fila.get("grado", ""))
    return {
        "anio": str(fila.get("anio", "")),
        "grado": grado,
        "nivel": _nivel_de_grado(grado),
        "situacion": str(fila.get("situacion", "")),
    }
