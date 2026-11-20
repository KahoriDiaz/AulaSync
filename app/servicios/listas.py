"""Padrón, comparación de listas de dos años e importación de DNIs (§6.3.6).

La importación de un archivo externo **solo compara**: nunca modifica la base
de datos. La comparación de años usa `sp_verificar_matriculados` y muestra
"No continúa" donde el procedimiento devuelve "Sin matrícula en el año actual".
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Iterable

from app import db
from app.errores import ErrorApp, ErrorValidacion
from app.servicios import distribucion

COLUMNAS_PADRON = distribucion.COLUMNAS_PADRON
COLUMNAS_COMPARACION = (
    "DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres",
    "NivelAnterior", "GradoAnterior", "NivelActual", "GradoActual", "Situacion",
)
COLUMNAS_EXTERNA = ("DNI", "Situacion", "Nombres", "Seccion")
SIN_MATRICULA = "Sin matrícula en el año actual"
NO_CONTINUA = "No continúa"
DNI_RE = re.compile(r"^\d{8}$")


def padron(
    anio: int, nivel: str | None = None, grado: str | None = None,
    seccion: str | None = None,
) -> list[dict[str, Any]]:
    return distribucion.padron(anio, nivel, grado, seccion)


def etiqueta_situacion(situacion: str) -> str:
    """Texto que se muestra en pantalla para cada situación de la comparación."""
    return NO_CONTINUA if str(situacion) == SIN_MATRICULA else str(situacion)


def comparar(anio_anterior: int, anio_actual: int) -> list[dict[str, Any]]:
    """Compara dos años lectivos: continúan, nuevos y no continúan."""
    conjuntos = db.call_proc(
        "sp_verificar_matriculados", (anio_anterior, anio_actual)
    )
    filas = list(conjuntos[0]) if conjuntos and conjuntos[0] else []
    # Se conservan las 9 columnas del procedimiento; solo cambia la etiqueta
    # que se muestra al usuario para el caso "Sin matrícula en el año actual".
    return [
        {
            **dict(fila),
            "Situacion": etiqueta_situacion(fila.get("Situacion", "")),
        }
        for fila in filas
    ]


def resumen(filas: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Cantidades por categoría de la comparación."""
    conteo = {"Continúa": 0, "Nuevo": 0, NO_CONTINUA: 0}
    for fila in filas:
        categoria = etiqueta_situacion(fila.get("Situacion", ""))
        if categoria in conteo:
            conteo[categoria] += 1
    return conteo


def _dni_desde_celda(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip().replace(" ", "").replace("-", "")


def importar_dnis(ruta: str | Path) -> list[str]:
    """Lee DNIs desde CSV/TXT o Excel, usando la primera columna.

    Se ignoran encabezados y filas vacías; solo se aceptan DNIs de 8 dígitos.
    """
    archivo = Path(ruta)
    if not archivo.is_file():
        raise ErrorValidacion(f"No se encontró el archivo {archivo}.")
    extension = archivo.suffix.lower()
    valores: list[Any] = []
    if extension in (".csv", ".txt"):
        with archivo.open("r", encoding="utf-8-sig", newline="") as manejador:
            for fila in csv.reader(manejador):
                if fila:
                    valores.append(fila[0])
    elif extension in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise ErrorApp(
                "Falta openpyxl; instale las dependencias para leer archivos Excel."
            ) from exc
        libro = load_workbook(archivo, read_only=True, data_only=True)
        try:
            hoja = libro.active
            for fila in hoja.iter_rows(min_col=1, max_col=1, values_only=True):
                valores.append(fila[0])
        finally:
            libro.close()
    else:
        raise ErrorValidacion("Use un archivo CSV, TXT o Excel (.xlsx).")

    dni_validos: list[str] = []
    vistos: set[str] = set()
    for valor in valores:
        dni = _dni_desde_celda(valor)
        if DNI_RE.fullmatch(dni) and dni not in vistos:
            vistos.add(dni)
            dni_validos.append(dni)
    if not dni_validos:
        raise ErrorValidacion("El archivo no contiene DNIs válidos de 8 dígitos.")
    return dni_validos


def comparar_con_lista_externa(
    dnis: Iterable[str], anio: int, nivel: str | None = None,
    grado: str | None = None, seccion: str | None = None,
) -> list[dict[str, Any]]:
    """Contrasta una lista de DNIs con el padrón, sin escribir en la BD."""
    padron_actual = padron(anio, nivel, grado, seccion)
    por_dni = {str(fila.get("DNI", "")): fila for fila in padron_actual}
    resultado: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for dni in dnis:
        dni = _dni_desde_celda(dni)
        if not DNI_RE.fullmatch(dni) or dni in vistos:
            continue
        vistos.add(dni)
        fila = por_dni.get(dni)
        resultado.append({
            "DNI": dni,
            "Situacion": "En el sistema" if fila else "No está en el sistema",
            "Nombres": (
                f"{fila.get('ApellidoPaterno', '')} {fila.get('ApellidoMaterno', '')}, "
                f"{fila.get('Nombres', '')}".strip(", ")
                if fila else ""
            ),
            "Seccion": fila.get("Seccion", "") if fila else "",
        })
    return resultado
