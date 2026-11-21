"""OCR auxiliar para DNI y constancias de logros (§6.2 punto 3).

El OCR es una ayuda: nunca reemplaza la validación manual. Las funciones de
extracción trabajan sobre una lista de ``(texto, confianza)`` para poder usar
tanto Tesseract como texto pegado por el usuario.
"""
from __future__ import annotations

from ocr.constancia import extraer_constancia
from ocr.dni import extraer_dni
from ocr.lector import (
    TesseractNoDisponible,
    diagnostico_ocr,
    extraer_lineas,
    lineas_desde_texto,
    probar_ocr,
    tesseract_disponible,
)

__all__ = [
    "extraer_dni",
    "extraer_constancia",
    "extraer_lineas",
    "lineas_desde_texto",
    "diagnostico_ocr",
    "probar_ocr",
    "tesseract_disponible",
    "TesseractNoDisponible",
]
