"""Preprocesamiento de imágenes y lectura de texto de PDF con PyMuPDF."""
from __future__ import annotations

from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

ANCHO_OBJETIVO = 2480
DPI_PDF = 300


def preprocesar_imagen(ruta: Path | str) -> Image.Image:
    """Escala de grises, autocontraste, enderezado EXIF y escalado a ~300 dpi."""
    with Image.open(ruta) as original:
        imagen = ImageOps.exif_transpose(original).convert("L")
    imagen = ImageOps.autocontrast(imagen)
    ancho, alto = imagen.size
    if ancho < ANCHO_OBJETIVO:
        factor = ANCHO_OBJETIVO / float(ancho)
        imagen = imagen.resize(
            (ANCHO_OBJETIVO, max(1, int(alto * factor))), Image.Resampling.LANCZOS
        )
    return imagen


def extraer_texto_pdf(ruta: Path | str) -> str:
    with pymupdf.open(str(ruta)) as documento:
        return "\n".join(pagina.get_text("text") for pagina in documento)


def renderizar_pdf(ruta: Path | str, dpi: int = DPI_PDF) -> list[Image.Image]:
    paginas: list[Image.Image] = []
    with pymupdf.open(str(ruta)) as documento:
        for pagina in documento:
            pixmap = pagina.get_pixmap(dpi=dpi)
            modo = "RGB" if pixmap.n > 3 else "L"
            imagen = Image.frombytes(modo, (pixmap.width, pixmap.height), pixmap.samples)
            paginas.append(imagen.convert("L"))
    return paginas
