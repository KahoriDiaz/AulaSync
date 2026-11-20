"""Normalización de los textos devueltos por OCR (§6.2 punto 3)."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

GRADOS_TEXTO = {
    "PRIMER": "1.°", "PRIMERO": "1.°", "PRIMERA": "1.°",
    "SEGUNDO": "2.°", "SEGUNDA": "2.°",
    "TERCER": "3.°", "TERCERO": "3.°", "TERCERA": "3.°",
    "CUARTO": "4.°", "CUARTA": "4.°",
    "QUINTO": "5.°", "QUINTA": "5.°",
    "SEXTO": "6.°", "SEXTA": "6.°",
}


def sin_tildes(texto: str) -> str:
    """Devuelve el texto sin acentos, en mayúsculas y con espacios simples."""
    descompuesto = unicodedata.normalize("NFD", str(texto or ""))
    plano = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", plano).strip().upper()


def limpiar_texto(texto: str) -> str:
    """Texto legible para el usuario, con espacios normalizados."""
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def normalizar_nombre_persona(texto: str) -> str:
    """Convierte 'ANA SOFIA' en 'Ana Sofia' y quita ruido de OCR."""
    limpio = limpiar_texto(texto).replace("<", " ").replace("_", " ")
    limpio = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ'’\- ]", " ", limpio)
    return re.sub(r"\s+", " ", limpio).strip().title()


def normalizar_dni(valor: Any) -> str | None:
    """Acepta 70000001, 70-000.001 o 'DNI 70000001'; solo 8 dígitos."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos if len(digitos) == 8 else None


def normalizar_fecha(valor: Any) -> str | None:
    """Devuelve AAAA-MM-DD desde DD/MM/AAAA o AAAA-MM-DD."""
    texto = limpiar_texto(valor)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        try:
            return date.fromisoformat(texto).isoformat()
        except ValueError:
            return None
    coincidencia = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", texto)
    if coincidencia:
        dia, mes, anio = map(int, coincidencia.groups())
        try:
            return date(anio, mes, dia).isoformat()
        except ValueError:
            return None
    return None


def normalizar_fecha_hora(valor: Any) -> str | None:
    """Devuelve 'AAAA-MM-DD HH:MM:SS' desde formatos usuales de constancia."""
    texto = limpiar_texto(valor)
    coincidencia = re.search(
        r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?", texto
    )
    if coincidencia:
        dia, mes, anio, hora, minuto, segundo = coincidencia.groups()
        try:
            return datetime(
                int(anio), int(mes), int(dia), int(hora or 0), int(minuto or 0),
                int(segundo or 0),
            ).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    fecha = normalizar_fecha(texto)
    return f"{fecha} 00:00:00" if fecha else None


def normalizar_sexo(valor: Any) -> str | None:
    plano = sin_tildes(valor)
    if plano in ("M", "MASCULINO"):
        return "M"
    if plano in ("F", "FEMENINO"):
        return "F"
    return None


def normalizar_nivel(valor: Any) -> str | None:
    plano = sin_tildes(valor)
    for nivel in ("INICIAL", "PRIMARIA", "SECUNDARIA"):
        if nivel in plano:
            return nivel.title()
    return None


def normalizar_grado(valor: Any) -> str | None:
    """Convierte 'TERCER GRADO', '4' o '4.°' en el grado oficial '3.°'."""
    texto = limpiar_texto(valor)
    plano = sin_tildes(texto)
    inicial = re.search(r"\b([3-5])\s*A\.?\s*(?:AÑOS?)?\b", plano)
    if inicial:
        return f"{inicial.group(1)} a."
    for palabra, grado in GRADOS_TEXTO.items():
        if re.search(rf"\b{palabra}\b", plano):
            return grado
    coincidencia = re.search(r"\b([1-6])\b", texto)
    if coincidencia:
        return f"{coincidencia.group(1)}.°"
    return None


def normalizar_situacion(valor: Any) -> str | None:
    plano = sin_tildes(valor)
    if "RECUPERACION" in plano:
        return "REQUIERE RECUPERACIÓN"
    if "APROBADO" in plano:
        return "APROBADO"
    return None


def normalizar_codigo_virtual(valor: Any) -> str | None:
    """Código virtual: exactamente 8 caracteres alfanuméricos."""
    plano = re.sub(r"[^A-Za-z0-9]", "", str(valor or "")).upper()
    return plano if len(plano) == 8 else None


def normalizar_codigo_modular(valor: Any) -> str | None:
    plano = sin_tildes(valor).replace(" ", "")
    coincidencia = re.search(r"(\d{6,7}-?\d?)", plano)
    return coincidencia.group(1) if coincidencia else None


def normalizar_tipo_ie(valor: Any) -> str | None:
    plano = sin_tildes(valor)
    if "ESTATAL" in plano:
        return "Estatal"
    if "PARTICULAR" in plano or "PRIVADA" in plano:
        return "Particular"
    return None
