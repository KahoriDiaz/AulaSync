"""Panel de relaciones de la base de datos (solo ``SELECT``).

Hace visible el modelo entity-relacional entre MATRICULA, ESTUDIANTE,
PADRE_APODERADO, SECRETARIA, INSTITUCION_EDUCATIVA, CONSTANCIA_LOGROS y las
tablas de relación (TIENE_PADRES, HERMANDAD, ESTUDIANTE_NEE, LOGRO).
"""
from __future__ import annotations

from typing import Any

from app import db

INDICADORES: tuple[tuple[str, str], ...] = (
    ("Estudiantes", "SELECT COUNT(*) AS total FROM ESTUDIANTE"),
    ("Matrículas activas", "SELECT COUNT(*) AS total FROM MATRICULA WHERE Estado = 'Matriculado'"),
    ("Padres / apoderados", "SELECT COUNT(*) AS total FROM PADRE_APODERADO"),
    ("Instituciones educativas", "SELECT COUNT(*) AS total FROM INSTITUCION_EDUCATIVA"),
    ("Constancias de logros", "SELECT COUNT(*) AS total FROM CONSTANCIA_LOGROS"),
    ("Logros registrados", "SELECT COUNT(*) AS total FROM LOGRO"),
    ("Relaciones padre-estudiante", "SELECT COUNT(*) AS total FROM TIENE_PADRES"),
    ("Relaciones de hermandad", "SELECT COUNT(*) AS total FROM HERMANDAD"),
    ("Necesidades educativas", "SELECT COUNT(*) AS total FROM ESTUDIANTE_NEE"),
    ("Hermanos en la I.E.", "SELECT COUNT(*) AS total FROM ESTUDIANTE_HERMANOS_IE"),
)

SQL_DETALLE = """
SELECT e.DNI,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante,
       m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, m.Estado,
       CONCAT(p.ApellidoPaterno, ' ', p.ApellidoMaterno, ', ', p.Nombres) AS Responsable,
       CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria,
       i.NombreIE,
       (SELECT COUNT(*) FROM TIENE_PADRES tp WHERE tp.DNI_Estudiante = e.DNI) AS Padres,
       (SELECT COUNT(*) FROM HERMANDAD h
         WHERE h.DNI_HermanoA = e.DNI OR h.DNI_HermanoB = e.DNI) AS Hermanos,
       (SELECT COUNT(*) FROM LOGRO l WHERE l.CodigoModularIE = i.CodigoModularIE) AS LogrosIE
FROM MATRICULA m
INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
INNER JOIN PADRE_APODERADO p ON m.DNI_Responsable = p.DNI
INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI
LEFT JOIN INSTITUCION_EDUCATIVA i ON e.CodigoModularIE = i.CodigoModularIE
ORDER BY m.`AñoEscolar` DESC, e.ApellidoPaterno, e.ApellidoMaterno
"""


def indicadores() -> list[dict[str, Any]]:
    """Devuelve los conteos de cada tabla y relación del modelo."""
    filas: list[dict[str, Any]] = []
    for nombre, sql in INDICADORES:
        fila = db.query_uno(sql)
        filas.append({"Indicador": nombre, "Valor": int((fila or {}).get("total") or 0)})
    return filas


def detalle() -> list[dict[str, Any]]:
    """Devuelve matrículas con el detalle de las entidades relacionadas."""
    return db.query(SQL_DETALLE)


def columnas_detalle() -> tuple[str, ...]:
    """Encabezados de la tabla de detalle."""
    return (
        "DNI", "Estudiante", "AñoEscolar", "Nivel", "Grado", "Seccion", "Estado",
        "Responsable", "Secretaria", "NombreIE", "Padres", "Hermanos", "LogrosIE",
    )
