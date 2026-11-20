"""Puente opcional con Tesseract (§6.2 punto 3 y §9).

Si Tesseract, Pillow o pytesseract no están instalados, el módulo sigue siendo
importable y la interfaz desactiva el botón de OC con un aviso.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.config import config
from app.errores import ErrorApp

Linea = tuple[str, int]


class TesseractNoDisponible(ErrorApp):
    """El OCR no puede ejecutarse en esta instalación."""


def ruta_tesseract() -> str | None:
    """Devuelve el ejecutable configurado, el incluido en el ZIP o el del PATH."""
    configurada = getattr(config, "tesseract_cmd", "")
    if configurada and Path(configurada).exists():
        return configurada
    for base in (config.USER_DIR, config.RECURSOS_DIR):
        empaquetado = base / "tesseract" / "tesseract.exe"
        if empaquetado.exists():
            tessdata = empaquetado.parent / "tessdata"
            if tessdata.is_dir():
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return str(empaquetado)
    return shutil.which("tesseract")


def tesseract_disponible() -> bool:
    """Indica si se puede intentar OCR sin instalar nada adicional."""
    if not ruta_tesseract():
        return False
    try:
        import PIL  # noqa: F401
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def extraer_lineas(ruta_imagen: str | Path) -> list[Linea]:
    """Devuelve ``[(texto, confianza), ...]`` de una imagen usando Tesseract."""
    ejecutable = ruta_tesseract()
    if not ejecutable:
        raise TesseractNoDisponible(
            "Tesseract no está disponible. Puede llenar los campos manualmente."
        )
    try:
        from PIL import Image
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise TesseractNoDisponible(
            "Falta Pillow o pytesseract. Puede llenar los campos manualmente."
        ) from exc

    pytesseract.tesseract_cmd = ejecutable
    imagen = Image.open(str(ruta_imagen))
    datos = pytesseract.image_to_data(
        imagen, lang="spa", output_type=Output.DICT
    )
    if not any(str(texto).strip() for texto in datos.get("text", [])):
        datos = pytesseract.image_to_data(
            imagen, lang="eng", output_type=Output.DICT
        )
    lineas: list[Linea] = []
    for texto, confianza in zip(datos.get("text", []), datos.get("conf", [])):
        limpio = str(texto).strip()
        if not limpio:
            continue
        try:
            conf = int(float(confianza))
        except (TypeError, ValueError):
            conf = 0
        if conf > 0:
            lineas.append((limpio, conf))
    return lineas
