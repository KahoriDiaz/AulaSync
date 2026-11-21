"""OCR para fichas de alumno y constancias de logros (§6.2, §13.6 punto 5).

Usa Tesseract (opcional). Si no está disponible, la secretaria puede llenar
los campos a mano. Nunca bloquea el flujo: el OCR es solo asistencia.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

try:
    import pytesseract
except ImportError:  # pragma: no cover - depende del entorno
    pytesseract = None


@dataclass
class OCRResultado:
    texto_completo: str = ""
    aplicados: list[str] = field(default_factory=list)
    disponible: bool = False
    error: str | None = None


def esta_disponible() -> bool:
    """Indica si Tesseract y pytesseract están instalados."""
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extraer_texto(ruta_imagen: str | Path) -> OCRResultado:
    """Ejecuta OCR sobre una imagen y devuelve el texto reconocido."""
    resultado = OCRResultado()
    if not esta_disponible():
        resultado.error = "Tesseract no está instalado o no se encontró el ejecutable."
        return resultado
    try:
        imagen = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(imagen, lang="spa")
        resultado.texto_completo = texto
        resultado.disponible = True
    except Exception as exc:  # noqa: BLE001
        resultado.error = str(exc)
    return resultado


# ---------------------------------------------------------------- ficha alumno
DNI_RE = re.compile(r"\b(\d{8})\b")
FECHA_RE = re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b")
NOMBRE_RE = re.compile(r"(Nombres?|Apellidos?|Nombre[s]?)\s*[:]\s*(.+)", re.IGNORECASE)


def procesar_ficha_alumno(texto: str) -> dict[str, Any]:
    """Extrae campos de una ficha de alumno desde el texto OCR."""
    datos: dict[str, Any] = {}

    dni = DNI_RE.search(texto)
    if dni:
        datos["DNI"] = dni.group(1)

    fecha = FECHA_RE.search(texto)
    if fecha:
        datos["FechaNacimiento"] = f"{fecha.group(3)}-{fecha.group(2).zfill(2)}-{fecha.group(1).zfill(2)}"

    # Buscar nombres y apellidos por etiquetas comunes
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        m = re.match(r"(?i)nombres?\s*[:]\s*(.+)", linea)
        if m:
            datos["Nombres"] = m.group(1).strip()
            continue
        m = re.match(r"(?i)apellido\s*paterno\s*[:]\s*(.+)", linea)
        if m:
            datos["ApellidoPaterno"] = m.group(1).strip()
            continue
        m = re.match(r"(?i)apellido\s*materno\s*[:]\s*(.+)", linea)
        if m:
            datos["ApellidoMaterno"] = m.group(1).strip()
            continue

    return datos


# ------------------------------------------------------------ constancia logros
CODIGO_VIRTUAL_RE = re.compile(r"\b([A-Z0-9]{8})\b")
LOGRO_RE = re.compile(
    r"(?i)(\d{4})\s*[-–]\s*([^\d\n]{1,20}?)\s*[-–]\s*(APROBADO|REQUIERE\s+RECUPERACIÓN)",
    re.IGNORECASE,
)


def procesar_constancia(texto: str) -> dict[str, Any]:
    """Extrae código virtual y logros de una constancia desde el texto OCR."""
    datos: dict[str, Any] = {"logros": []}

    codigo = CODIGO_VIRTUAL_RE.search(texto)
    if codigo:
        datos["codigo_virtual"] = codigo.group(1)

    for m in LOGRO_RE.finditer(texto):
        datos["logros"].append({
            "anio": int(m.group(1)),
            "grado": m.group(2).strip(),
            "situacion": m.group(3).upper(),
        })

    return datos
