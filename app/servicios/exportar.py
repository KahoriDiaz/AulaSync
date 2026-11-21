"""Exportación de listas y reportes a Excel, PDF y CSV (§6.3 punto 6).

Las librerías se importan dentro de cada función para que el resto de la
aplicación siga funcionando si no se instaló alguna de ellas; en ese caso se
muestra un mensaje claro al usuario.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.errores import ErrorValidacion

FORMATOS = ("xlsx", "pdf", "csv")
EXTENSIONES = {"xlsx": ".xlsx", "pdf": ".pdf", "csv": ".csv"}
_CARACTERES_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def nombre_archivo(titulo: str, formato: str) -> str:
    """Devuelve un nombre de archivo seguro para el título indicado."""
    if formato not in FORMATOS:
        raise ErrorValidacion(f"Formato de exportación desconocido: {formato}.")
    limpio = _CARACTERES_INVALIDOS.sub("_", str(titulo or "reporte")).strip(" .")
    limpio = re.sub(r"\s+", " ", limpio)[:80] or "reporte"
    return limpio + EXTENSIONES[formato]


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat(sep=" ") if isinstance(valor, datetime) else valor.isoformat()
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="replace")
    return str(valor)


def preparar(
    filas: Iterable[Mapping[str, Any]], columnas: Sequence[str] | None = None
) -> tuple[tuple[str, ...], list[list[str]]]:
    """Normaliza las filas a una matriz de texto con encabezados."""
    registros = [dict(fila) for fila in filas]
    if columnas is None:
        encabezados: tuple[str, ...] = tuple(registros[0].keys()) if registros else ()
    else:
        encabezados = tuple(str(columna) for columna in columnas)
    cuerpo = [[_texto(fila.get(columna)) for columna in encabezados] for fila in registros]
    return encabezados, cuerpo


def a_csv(
    filas: Iterable[Mapping[str, Any]], columnas: Sequence[str] | None = None
) -> str:
    """Devuelve el contenido CSV (con BOM al guardarse, para abrirlo en Excel)."""
    encabezados, cuerpo = preparar(filas, columnas)
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    if encabezados:
        escritor.writerow(encabezados)
    escritor.writerows(cuerpo)
    return salida.getvalue()


def guardar_csv(
    filas: Iterable[Mapping[str, Any]], ruta: str | Path,
    columnas: Sequence[str] | None = None,
) -> Path:
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(a_csv(filas, columnas), encoding="utf-8-sig")
    return destino


def guardar_excel(
    filas: Iterable[Mapping[str, Any]], ruta: str | Path, titulo: str = "Reporte",
    columnas: Sequence[str] | None = None,
) -> Path:
    """Genera un libro de una hoja con encabezados congelados y autofiltro."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        from app.errores import ErrorApp

        raise ErrorApp("Falta openpyxl; instale las dependencias para exportar a Excel.") from exc

    encabezados, cuerpo = preparar(filas, columnas)
    libro = Workbook()
    hoja = libro.active
    hoja.title = nombre_archivo(titulo, "csv").removesuffix(".csv")[:31] or "Reporte"
    if encabezados:
        hoja.append(list(encabezados))
        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="075985")
            celda.alignment = Alignment(vertical="center")
        hoja.freeze_panes = "A2"
    for fila in cuerpo:
        hoja.append(fila)
        # openpyxl interpreta como fórmula cualquier texto que empiece con "=";
        # los datos se guardan siempre como texto para evitar inyección de fórmulas.
        for celda in hoja[hoja.max_row]:
            if celda.data_type == "f":
                celda.data_type = "s"
    if encabezados and cuerpo:
        hoja.auto_filter.ref = f"A1:{get_column_letter(len(encabezados))}{len(cuerpo) + 1}"
    for indice, columna in enumerate(encabezados or (), 1):
        ancho = max([len(str(columna))] + [len(fila[indice - 1]) for fila in cuerpo] or [10])
        hoja.column_dimensions[get_column_letter(indice)].width = min(max(ancho + 2, 10), 48)
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)
    return destino


def guardar_pdf(
    filas: Iterable[Mapping[str, Any]], ruta: str | Path, titulo: str = "Reporte",
    columnas: Sequence[str] | None = None,
) -> Path:
    """Genera un PDF apaisado con la tabla de resultados."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape
    except ImportError as exc:
        from app.errores import ErrorApp

        raise ErrorApp("Falta reportlab; instale las dependencias para exportar a PDF.") from exc

    encabezados, cuerpo = preparar(filas, columnas)
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "titulo_pdf", parent=estilos["Title"], fontSize=14, spaceAfter=10
    )
    estilo_celda = ParagraphStyle("celda_pdf", parent=estilos["BodyText"], fontSize=7, leading=9)
    estilo_encabezado = ParagraphStyle(
        "encabezado_pdf", parent=estilo_celda, textColor=colors.white,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    )

    pagina = landscape(A4)
    ancho_util = pagina[0] - 2 * cm
    if encabezados and cuerpo:
        longitud = [
            max([len(str(encabezados[i]))] + [len(fila[i]) for fila in cuerpo])
            for i in range(len(encabezados))
        ]
        suma = sum(longitud) or 1
        anchos = [max(ancho_util * n / suma, 1.2 * cm) for n in longitud]
    else:
        anchos = [ancho_util]

    datos = [[Paragraph(escape(str(c)), estilo_encabezado) for c in encabezados]] if encabezados else []
    datos.extend(
        [Paragraph(escape(valor), estilo_celda) for valor in fila] for fila in cuerpo
    )
    if not datos:
        datos = [[Paragraph("Sin datos", estilo_celda)]]
    tabla = Table(datos, colWidths=anchos, repeatRows=1 if encabezados else 0)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#075985")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F7FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = SimpleDocTemplate(
        str(destino), pagesize=pagina, leftMargin=cm, rightMargin=cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, title=str(titulo),
    )
    documento.build([Paragraph(escape(str(titulo or "Reporte")), estilo_titulo), Spacer(1, 6), tabla])
    return destino


def exportar(
    filas: Iterable[Mapping[str, Any]], ruta: str | Path, formato: str,
    titulo: str = "Reporte", columnas: Sequence[str] | None = None,
) -> Path:
    """Guarda las filas en el formato solicitado y devuelve la ruta creada."""
    formato = str(formato).lower().lstrip(".")
    if formato not in FORMATOS:
        raise ErrorValidacion(f"Formato de exportación desconocido: {formato}.")
    if formato == "csv":
        return guardar_csv(filas, ruta, columnas)
    if formato == "xlsx":
        return guardar_excel(filas, ruta, titulo, columnas)
    return guardar_pdf(filas, ruta, titulo, columnas)
