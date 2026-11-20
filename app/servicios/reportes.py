"""Las 10 consultas representativas de la Entrega 4 (§14.4).

El texto SQL se conserva **idéntico** al de ``sql/06_consultas.sql`` (mismo
orden, mismas aliases, mismos JOIN); únicamente los valores fijos del script se
reemplazan por marcadores ``%s``. Cada pantalla arranca con esos valores
predeterminados para que el resultado inicial coincida con las figuras 22–31.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app import db
from app.errores import ErrorValidacion

SQL_CONSULTAS = "sql/06_consultas.sql"


@dataclass(frozen=True)
class Reporte:
    """Definición ejecutable de una de las 10 consultas."""

    numero: int
    titulo: str
    sql: str
    parametros: tuple[str, ...]
    defaults: tuple[Any, ...]
    literales: tuple[str, ...]
    repeticiones: tuple[int, ...]
    columnas: tuple[str, ...]
    joins: int


CONSULTAS: tuple[Reporte, ...] = (
    Reporte(
        numero=1,
        titulo="Lista de estudiantes matriculados en un año, nivel, grado y sección específicos",
        sql="""
SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
       m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, m.Estado
FROM MATRICULA m
INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
WHERE m.`AñoEscolar` = %s
  AND m.Nivel = %s
  AND m.Grado = %s
  AND m.Seccion = %s
  AND m.Estado = %s
ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres
""",
        parametros=("Año", "Nivel", "Grado", "Sección", "Estado"),
        defaults=(2026, "Secundaria", "3.°", "B", "Matriculado"),
        literales=("2026", "'Secundaria'", "'3.°'", "'B'", "'Matriculado'"),
        repeticiones=(1, 1, 1, 1, 1),
        columnas=("DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres",
                  "AñoEscolar", "Nivel", "Grado", "Seccion", "Estado"),
        joins=1,
    ),
    Reporte(
        numero=2,
        titulo="Buscar estudiante por apellidos y nombres",
        sql="""
SELECT DNI, ApellidoPaterno, ApellidoMaterno, Nombres, FechaNacimiento
FROM ESTUDIANTE
WHERE ApellidoPaterno = %s
  AND ApellidoMaterno = %s
ORDER BY Nombres
""",
        parametros=("Apellido paterno", "Apellido materno"),
        defaults=("Diaz", "Acosta"),
        literales=("'Diaz'", "'Acosta'"),
        repeticiones=(1, 1),
        columnas=("DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "FechaNacimiento"),
        joins=0,
    ),
    Reporte(
        numero=3,
        titulo="Constancias de un estudiante filtradas por nivel",
        sql="""
SELECT c.CodigoVirtual, c.DNI_Estudiante, c.NivelEducativo,
       c.FechaHoraEmision,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante
FROM CONSTANCIA_LOGROS c
INNER JOIN ESTUDIANTE e ON c.DNI_Estudiante = e.DNI
WHERE c.DNI_Estudiante = %s
  AND c.NivelEducativo = %s
""",
        parametros=("DNI", "Nivel"),
        defaults=("74922482", "Secundaria"),
        literales=("'74922482'", "'Secundaria'"),
        repeticiones=(1, 1),
        columnas=("CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision", "Estudiante"),
        joins=1,
    ),
    Reporte(
        numero=4,
        titulo="Listar hermanos de un estudiante",
        sql="""
SELECT h.DNI_HermanoB AS DNI_Hermano,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Hermano
FROM HERMANDAD h
INNER JOIN ESTUDIANTE e ON h.DNI_HermanoB = e.DNI
WHERE h.DNI_HermanoA = %s
UNION
SELECT h.DNI_HermanoA AS DNI_Hermano,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Hermano
FROM HERMANDAD h
INNER JOIN ESTUDIANTE e ON h.DNI_HermanoA = e.DNI
WHERE h.DNI_HermanoB = %s
""",
        parametros=("DNI",),
        defaults=("56743478",),
        literales=("'56743478'", "'56743478'"),
        repeticiones=(2,),
        columnas=("DNI_Hermano", "Hermano"),
        joins=2,
    ),
    Reporte(
        numero=5,
        titulo="Reporte de matriculados por año, nivel y grado",
        sql="""
SELECT m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion,
       COUNT(*) AS Total_Matriculados,
       SUM(CASE WHEN m.Estado = 'Matriculado' THEN 1 ELSE 0 END) AS Activos,
       SUM(CASE WHEN m.Estado = 'Retirado' THEN 1 ELSE 0 END) AS Retirados,
       SUM(CASE WHEN m.Estado = 'Trasladado' THEN 1 ELSE 0 END) AS Trasladados
FROM MATRICULA m
GROUP BY m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion
ORDER BY m.`AñoEscolar` DESC, m.Nivel, m.Grado
""",
        parametros=(),
        defaults=(),
        literales=(),
        repeticiones=(),
        columnas=("AñoEscolar", "Nivel", "Grado", "Seccion", "Total_Matriculados",
                  "Activos", "Retirados", "Trasladados"),
        joins=0,
    ),
    Reporte(
        numero=6,
        titulo="Estudiantes de un apoderado específico",
        sql="""
SELECT e.DNI, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante,
       e.FechaNacimiento, e.DistritoDomicilio
FROM ESTUDIANTE e
WHERE e.DNI_Apoderado = %s
ORDER BY e.ApellidoPaterno
""",
        parametros=("DNI apoderado",),
        defaults=("56345876",),
        literales=("'56345876'",),
        repeticiones=(1,),
        columnas=("DNI", "Estudiante", "FechaNacimiento", "DistritoDomicilio"),
        joins=0,
    ),
    Reporte(
        numero=7,
        titulo="Matrículas declaradas por un responsable",
        sql="""
SELECT m.DNI_Estudiante, m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion,
       m.FechaSuscripcion, m.LugarSuscripcion
FROM MATRICULA m
WHERE m.DNI_Responsable = %s
ORDER BY m.`AñoEscolar` DESC
""",
        parametros=("DNI responsable",),
        defaults=("29481029",),
        literales=("'29481029'",),
        repeticiones=(1,),
        columnas=("DNI_Estudiante", "AñoEscolar", "Nivel", "Grado", "Seccion",
                  "FechaSuscripcion", "LugarSuscripcion"),
        joins=0,
    ),
    Reporte(
        numero=8,
        titulo="Detalle completo de la última matrícula de un estudiante",
        sql="""
SELECT e.DNI,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante,
       m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, m.Estado,
       m.LugarSuscripcion, m.FechaSuscripcion,
       CONCAT(p.ApellidoPaterno, ' ', p.ApellidoMaterno, ', ', p.Nombres) AS Responsable,
       CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria
FROM MATRICULA m
INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
INNER JOIN PADRE_APODERADO p ON m.DNI_Responsable = p.DNI
INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI
WHERE m.DNI_Estudiante = %s
ORDER BY m.`AñoEscolar` DESC
LIMIT 1
""",
        parametros=("DNI",),
        defaults=("56743478",),
        literales=("'56743478'",),
        repeticiones=(1,),
        columnas=("DNI", "Estudiante", "AñoEscolar", "Nivel", "Grado", "Seccion", "Estado",
                  "LugarSuscripcion", "FechaSuscripcion", "Responsable", "Secretaria"),
        joins=3,
    ),
    Reporte(
        numero=9,
        titulo="Logros académicos de un estudiante y su I.E. de procedencia",
        sql="""
SELECT c.CodigoVirtual, l.`AñoEscolar`, l.GradoCursado,
       i.NombreIE, i.TipoIE, l.SituacionFinal
FROM CONSTANCIA_LOGROS c
INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual
INNER JOIN INSTITUCION_EDUCATIVA i ON l.CodigoModularIE = i.CodigoModularIE
WHERE c.DNI_Estudiante = %s
ORDER BY l.`AñoEscolar`
""",
        parametros=("DNI",),
        defaults=("74922482",),
        literales=("'74922482'",),
        repeticiones=(1,),
        columnas=("CodigoVirtual", "AñoEscolar", "GradoCursado", "NombreIE", "TipoIE", "SituacionFinal"),
        joins=2,
    ),
    Reporte(
        numero=10,
        titulo="Matrículas registradas por la secretaria en un año, por nivel",
        sql="""
SELECT s.DNI, CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria,
       m.Nivel, COUNT(*) AS TotalMatriculas
FROM MATRICULA m
INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI
WHERE m.`AñoEscolar` = %s
GROUP BY s.DNI, s.ApellidoPaterno, s.ApellidoMaterno, s.Nombres, m.Nivel
ORDER BY m.Nivel
""",
        parametros=("Año",),
        defaults=(2026,),
        literales=("2026",),
        repeticiones=(1,),
        columnas=("DNI", "Secretaria", "Nivel", "TotalMatriculas"),
        joins=1,
    ),
)

POR_NUMERO = {reporte.numero: reporte for reporte in CONSULTAS}


def todos() -> tuple[Reporte, ...]:
    """Devuelve las 10 consultas en el orden de las figuras 22 a 31."""
    return CONSULTAS


def obtener(numero: int) -> Reporte:
    reporte = POR_NUMERO.get(int(numero))
    if reporte is None:
        raise ErrorValidacion(f"No existe la consulta {numero}.")
    return reporte


def parametros_sql(reporte: Reporte, valores: Sequence[Any]) -> tuple[Any, ...]:
    """Repite un valor tantas veces como marcadores tenga en el SQL (consulta 4)."""
    if len(valores) != len(reporte.parametros):
        raise ErrorValidacion(
            f"La consulta {reporte.numero} espera {len(reporte.parametros)} parámetro(s)."
        )
    return tuple(
        valor
        for valor, veces in zip(valores, reporte.repeticiones)
        for _ in range(veces)
    )


def ejecutar(numero: int, valores: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Ejecuta una consulta con los valores dados o con los predeterminados."""
    reporte = obtener(numero)
    usados = reporte.defaults if valores is None else tuple(valores)
    return db.query(reporte.sql, parametros_sql(reporte, usados))


def sql_con_valores_por_defecto(reporte: Reporte) -> str:
    """Reconstruye el SQL original del script sustituyendo los marcadores.

    Se usa en las pruebas para comprobar que no se reescribió ninguna consulta.
    """
    sql = reporte.sql.strip()
    for literal in reporte.literales:
        sql = sql.replace("%s", literal, 1)
    return sql
