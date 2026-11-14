"""Normalización tolerante de valores leídos por OCR."""
from __future__ import annotations

import re
from datetime import datetime

from core.formatos import sin_tildes


def limpiar(valor: object) -> str:
    texto = " ".join(str(valor or "").split())
    return texto.strip(" :;,.-\t")


def mayuscula_inicial(texto: str) -> str:
    limpio = limpiar(texto)
    if not limpio:
        return ""
    return limpio.title()


def normalizar_dni(texto: str) -> str | None:
    digitos = re.sub(r"\D", "", str(texto or ""))
    if len(digitos) == 8:
        return digitos
    return None


def normalizar_fecha(texto: str) -> str | None:
    limpio = limpiar(texto)
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(limpio, formato).date().isoformat()
        except ValueError:
            continue
    coincidencia = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", limpio)
    if coincidencia:
        dia, mes, anio = coincidencia.groups()
        try:
            return datetime(int(anio), int(mes), int(dia)).date().isoformat()
        except ValueError:
            return None
    return None


def normalizar_fecha_hora(texto: str) -> str | None:
    limpio = limpiar(texto)
    fecha = normalizar_fecha(limpio)
    if not fecha:
        return None
    hora = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b", limpio)
    if not hora:
        return f"{fecha} 00:00:00"
    hh, mm, ss = hora.groups()
    return f"{fecha} {int(hh):02d}:{int(mm):02d}:{int(ss or 0):02d}"


def normalizar_sexo(texto: str) -> str | None:
    limpio = sin_tildes(str(texto or "")).upper()
    if re.search(r"\b(M|MASCULINO|HOMBRE|VARON)\b", limpio):
        return "M"
    if re.search(r"\b(F|FEMENINO|MUJER)\b", limpio):
        return "F"
    return None


def normalizar_nivel(texto: str) -> str | None:
    limpio = sin_tildes(str(texto or "")).upper()
    for nivel in ("INICIAL", "PRIMARIA", "SECUNDARIA"):
        if nivel in limpio:
            return nivel.capitalize()
    return None


def normalizar_grado(texto: str) -> str | None:
    limpio = sin_tildes(str(texto or "")).upper()
    limpio = re.sub(r"\b(GRADO|AÑO|ANIO|DE|DEL|EL)\b", " ", limpio)
    limpio = limpio.replace("°", " ").replace("º", " ").replace(".", " ")
    ordinales = {
        "PRIMER": "1", "PRIMERO": "1", "PRIMERA": "1",
        "SEGUNDO": "2", "SEGUNDA": "2",
        "TERCER": "3", "TERCERO": "3", "TERCERA": "3",
        "CUARTO": "4", "CUARTA": "4",
        "QUINTO": "5", "QUINTA": "5",
        "SEXTO": "6", "SEXTA": "6",
    }
    for palabra in re.split(r"\s+", limpio):
        if palabra in ordinales:
            return f"{ordinales[palabra]}.°"
        coincidencia = re.fullmatch(r"([1-6])(?:RO|DO|TO|ER|ERO)?", palabra)
        if coincidencia:
            return f"{coincidencia.group(1)}.°"
    return None


def normalizar_situacion(texto: str) -> str | None:
    limpio = sin_tildes(str(texto or "")).upper()
    if "RECUPER" in limpio:
        return "REQUIERE RECUPERACIÓN"
    if "APROB" in limpio:
        return "APROBADO"
    return None


def normalizar_codigo_virtual(texto: str) -> str | None:
    limpio = re.sub(r"[^A-Za-z0-9]", "", str(texto or "")).upper()
    if len(limpio) == 8:
        return limpio
    return None


def normalizar_codigo_modular(texto: str) -> str | None:
    limpio = re.sub(r"[^0-9-]", "", str(texto or ""))
    if 6 <= len(limpio.replace("-", "")) <= 10:
        return limpio
    return None


def normalizar_tipo_ie(texto: str) -> str | None:
    limpio = sin_tildes(str(texto or "")).upper()
    if "PARTICULAR" in limpio or "PRIVAD" in limpio:
        return "Particular"
    if "ESTATAL" in limpio or "PUBLIC" in limpio:
        return "Estatal"
    return None
