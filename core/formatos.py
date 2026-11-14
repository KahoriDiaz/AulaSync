"""Validación y normalización de formatos permitidos por el modelo."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from core.errores import ErrorValidacion

DNI_RE = re.compile(r"^\d{8}$")
CELULAR_RE = re.compile(r"^\d{9}$")
CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NIVELES = ("Inicial", "Primaria", "Secundaria")
GRADOS = {
    "Inicial": ("3 a.", "4 a.", "5 a."),
    "Primaria": ("1.°", "2.°", "3.°", "4.°", "5.°", "6.°"),
    "Secundaria": ("1.°", "2.°", "3.°", "4.°", "5.°"),
}
TIPOS_ATENCION = ("ESSALUD", "SIS", "Otros")
TIPOS_IE = ("Estatal", "Particular")
GRADOS_INSTRUCCION = ("Primaria", "Secundaria", "Superior", "Otros")
SITUACIONES = ("APROBADO", "REQUIERE RECUPERACIÓN")
ESTADOS_MATRICULA = ("Matriculado", "Retirado", "Trasladado")

_ORDINALES = {
    "PRIMER": "1", "PRIMERO": "1", "PRIMERA": "1",
    "SEGUNDO": "2", "SEGUNDA": "2",
    "TERCER": "3", "TERCERO": "3", "TERCERA": "3",
    "CUARTO": "4", "CUARTA": "4",
    "QUINTO": "5", "QUINTA": "5",
    "SEXTO": "6", "SEXTA": "6",
    "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6",
    "1RO": "1", "2DO": "2", "3RO": "3", "4TO": "4", "5TO": "5", "6TO": "6",
}


def sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def texto_limpio(valor: object) -> str:
    return str(valor or "").strip()


def validar_dni(valor: object, campo: str = "DNI") -> str:
    texto = texto_limpio(valor)
    if not DNI_RE.match(texto):
        raise ErrorValidacion(f"El {campo} debe tener exactamente 8 dígitos.")
    return texto


def validar_celular(valor: object, campo: str = "celular", opcional: bool = False) -> str | None:
    texto = texto_limpio(valor)
    if not texto and opcional:
        return None
    if not CELULAR_RE.match(texto):
        raise ErrorValidacion(f"El {campo} debe tener exactamente 9 dígitos.")
    return texto


def validar_correo(valor: object, campo: str = "correo", opcional: bool = True) -> str | None:
    texto = texto_limpio(valor)
    if not texto and opcional:
        return None
    if not CORREO_RE.match(texto):
        raise ErrorValidacion(f"El {campo} no tiene un formato válido.")
    return texto


def normalizar_nombre(valor: object) -> str:
    texto = " ".join(texto_limpio(valor).split())
    return texto.title()


def normalizar_sexo(valor: object) -> str:
    texto = sin_tildes(texto_limpio(valor)).upper()
    if texto in ("M", "MASCULINO", "HOMBRE", "VARON"):
        return "M"
    if texto in ("F", "FEMENINO", "MUJER"):
        return "F"
    raise ErrorValidacion("El sexo debe ser M o F.")


def normalizar_fecha(valor: object) -> str:
    """Devuelve AAAA-MM-DD. Acepta AAAA-MM-DD, DD/MM/AAAA y DD-MM-AAAA."""
    texto = texto_limpio(valor)
    if not texto:
        raise ErrorValidacion("La fecha es obligatoria.")
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ErrorValidacion("La fecha debe tener el formato AAAA-MM-DD.")


def validar_fecha_no_futura(valor: object, campo: str = "fecha de nacimiento") -> str:
    texto = normalizar_fecha(valor)
    if datetime.strptime(texto, "%Y-%m-%d").date() > date.today():
        raise ErrorValidacion(f"La {campo} no puede ser una fecha futura.")
    return texto


def normalizar_nivel(valor: object) -> str:
    texto = sin_tildes(texto_limpio(valor)).upper()
    for nivel in NIVELES:
        if texto == sin_tildes(nivel).upper():
            return nivel
    raise ErrorValidacion("El nivel debe ser Inicial, Primaria o Secundaria.")


def grados_de_nivel(nivel: str) -> tuple[str, ...]:
    try:
        return GRADOS[nivel]
    except KeyError as exc:
        raise ErrorValidacion("El nivel debe ser Inicial, Primaria o Secundaria.") from exc


def validar_grado(nivel: str, grado: object) -> str:
    texto = texto_limpio(grado)
    if texto not in grados_de_nivel(nivel):
        raise ErrorValidacion(
            f"El grado no corresponde al nivel {nivel}. Use: {', '.join(GRADOS[nivel])}."
        )
    return texto


def normalizar_grado(valor: object) -> str:
    """Convierte 'TERCERO', '3ER GRADO', '3' o '3.°' a '3.°'."""
    texto = sin_tildes(texto_limpio(valor)).upper()
    texto = re.sub(r"\b(GRADO|AÑO|ANIO|DE|DEL)\b", " ", texto)
    texto = re.sub(r"[.°º]", " ", texto)
    for palabra in re.split(r"\s+", texto):
        if palabra in _ORDINALES:
            return f"{_ORDINALES[palabra]}.°"
        coincidencia = re.fullmatch(r"([1-6])(?:RO|DO|TO|ERO|ER)?", palabra)
        if coincidencia:
            return f"{coincidencia.group(1)}.°"
    raise ErrorValidacion("No se pudo reconocer el grado cursado.")


def normalizar_situacion(valor: object) -> str:
    texto = " ".join(sin_tildes(texto_limpio(valor)).upper().split())
    if "RECUPER" in texto:
        return "REQUIERE RECUPERACIÓN"
    if "APROB" in texto:
        return "APROBADO"
    raise ErrorValidacion("La situación final debe ser APROBADO o REQUIERE RECUPERACIÓN.")


def validar_si_no(valor: object, campo: str) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return bool(valor)
    texto = sin_tildes(texto_limpio(valor)).upper()
    if texto in ("SI", "SÍ", "S", "TRUE", "1", "VERDADERO"):
        return True
    if texto in ("NO", "N", "FALSE", "0", "FALSO"):
        return False
    raise ErrorValidacion(f"El campo {campo} debe ser Sí o No.")


def validar_opcion(valor: object, opciones: tuple[str, ...], campo: str) -> str:
    texto = texto_limpio(valor)
    if texto not in opciones:
        raise ErrorValidacion(f"El {campo} debe ser uno de: {', '.join(opciones)}.")
    return texto
