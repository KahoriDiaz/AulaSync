"""Puente opcional con Tesseract (§6.2 punto 3 y §9).

El paquete incluye un ``tesseract.exe`` portable, pero el módulo sigue siendo
importable si falta: la interfaz muestra entonces un diagnóstico y permite pegar
el texto leído en otra herramienta. Así el formulario nunca queda bloqueado.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from app.config import config
from app.errores import ErrorApp

Linea = tuple[str, int]


class TesseractNoDisponible(ErrorApp):
    """El OCR no puede ejecutarse en esta instalación."""


def rutas_tesseract() -> list[Path]:
    """Candidatos a ejecutable: configurado, incluido en el ZIP y PATH."""
    candidatos: list[Path] = []
    configurada = str(getattr(config, "tesseract_cmd", "") or "").strip()
    if configurada:
        candidatos.append(Path(configurada))
    for base in (config.USER_DIR, config.RECURSOS_DIR):
        candidatos.append(base / "tesseract" / "tesseract.exe")
    return candidatos


def ruta_tesseract() -> str | None:
    """Devuelve el ejecutable configurado, el incluido en el ZIP o el del PATH."""
    for candidato in rutas_tesseract():
        if candidato.is_file():
            tessdata = candidato.parent / "tessdata"
            if tessdata.is_dir():
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return str(candidato)
    return shutil.which("tesseract")


def ruta_tessdata(ejecutable: str | None = None) -> Path | None:
    """Localiza la carpeta con los modelos de idioma del ejecutable."""
    prefijo = os.environ.get("TESSDATA_PREFIX", "")
    if prefijo and Path(prefijo).is_dir():
        return Path(prefijo)
    base = Path(ejecutable or ruta_tesseract() or "")
    for candidata in (base / "tessdata", base.parent / "tessdata"):
        if candidata.is_dir():
            return candidata
    return None


def _modulos_disponibles() -> tuple[bool, bool]:
    try:
        import PIL  # noqa: F401
        pillow = True
    except ImportError:
        pillow = False
    try:
        import pytesseract  # noqa: F401
        envoltorio = True
    except ImportError:
        envoltorio = False
    return pillow, envoltorio


def diagnostico_ocr() -> dict[str, Any]:
    """Explica qué componente falta, para mostrar un aviso útil al usuario."""
    ejecutable = ruta_tesseract()
    tessdata = ruta_tessdata(ejecutable)
    spa = bool(tessdata and (tessdata / "spa.traineddata").is_file())
    pillow, envoltorio = _modulos_disponibles()
    disponible = bool(ejecutable and spa and pillow and envoltorio)
    if not ejecutable:
        mensaje = (
            "No se encontró tesseract.exe. Debe estar en la carpeta tesseract/ "
            "junto a AulaSync.exe o indicarse en config.ini (tesseract_cmd)."
        )
    elif not spa:
        mensaje = (
            "Se encontró Tesseract pero falta tessdata/spa.traineddata en la "
            "misma carpeta."
        )
    elif not (pillow and envoltorio):
        mensaje = (
            "Se encontró Tesseract pero faltan las librerías Pillow o pytesseract "
            "en la instalación de Python."
        )
    else:
        mensaje = "OCR listo para usar."
    return {
        "disponible": disponible,
        "ejecutable": ejecutable or "",
        "tessdata": str(tessdata) if tessdata else "",
        "idioma_spa": spa,
        "pillow": pillow,
        "pytesseract": envoltorio,
        "mensaje": mensaje,
    }


def tesseract_disponible() -> bool:
    """Indica si se puede intentar OCR sin instalar nada adicional."""
    return diagnostico_ocr()["disponible"]


def lineas_desde_texto(texto: str) -> list[Linea]:
    """Convierte texto pegado en la misma entrada que usa el extractor de OCR."""
    return [(linea.strip(), 100) for linea in texto.splitlines() if linea.strip()]


def extraer_lineas(ruta_imagen: str | Path) -> list[Linea]:
    """Devuelve ``[(texto, confianza), ...]`` de una imagen usando Tesseract."""
    diagnostico = diagnostico_ocr()
    if not diagnostico["ejecutable"]:
        raise TesseractNoDisponible(diagnostico["mensaje"])
    if not diagnostico["pillow"] or not diagnostico["pytesseract"]:
        raise TesseractNoDisponible(diagnostico["mensaje"])

    from PIL import Image, ImageOps
    import pytesseract
    from pytesseract import Output
    from pytesseract import pytesseract as modulo_pytesseract

    modulo_pytesseract.tesseract_cmd = diagnostico["ejecutable"]
    imagen = Image.open(str(ruta_imagen)).convert("L")
    imagen = ImageOps.autocontrast(imagen)
    if max(imagen.size) < 1400:
        escala = 2
        imagen = imagen.resize((imagen.width * escala, imagen.height * escala))

    idiomas = "spa" if diagnostico["idioma_spa"] else "eng"
    datos = pytesseract.image_to_data(imagen, lang=idiomas, output_type=Output.DICT)
    sin_texto = not any(str(texto).strip() for texto in datos.get("text", []))
    tessdata = diagnostico["tessdata"]
    if sin_texto and tessdata and (Path(tessdata) / "eng.traineddata").is_file():
        datos = pytesseract.image_to_data(imagen, lang="eng", output_type=Output.DICT)
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


def probar_ocr() -> tuple[bool, str]:
    """Genera una imagen pequeña y comprueba que Tesseract responda."""
    diagnostico = diagnostico_ocr()
    if not diagnostico["disponible"]:
        return False, diagnostico["mensaje"]
    try:
        from PIL import Image, ImageDraw

        imagen = Image.new("RGB", (420, 90), "white")
        ImageDraw.Draw(imagen).text((12, 32), "PRUEBA OCR 12345678", fill="black")
        ruta = config.DATOS_DIR / "ocr_prueba.png"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            imagen.save(ruta)
            lineas = extraer_lineas(ruta)
        finally:
            ruta.unlink(missing_ok=True)
    except Exception as exc:  # Tesseract puede fallar por permisos o DLLs
        return False, f"Tesseract está instalado pero no respondió: {exc}"
    if lineas:
        return True, "OCR funcionando: " + " ".join(texto for texto, _ in lineas[:6])
    return False, "Tesseract respondió pero no reconoció la imagen de prueba."
