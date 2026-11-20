"""Extracción de campos de un DNI escaneado (§6.2 punto 3).

Entrada: lista de ``(texto, confianza)``. Salida: diccionario
``"TABLA.Campo": (valor, confianza)`` para que la UI pueda mostrar qué campos
vienen del OCR y dejar que el usuario los confirme.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable

from ocr import normalizacion as nz

Linea = tuple[str, int]
Campo = tuple[str, str, Callable[[Any], Any]]

ETIQUETAS_ESTUDIANTE: tuple[Campo, ...] = (
    ("DNI", "DNI", nz.normalizar_dni),
    ("APELLIDO PATERNO", "ApellidoPaterno", nz.normalizar_nombre_persona),
    ("APELLIDO MATERNO", "ApellidoMaterno", nz.normalizar_nombre_persona),
    ("PRENOMBRES", "Nombres", nz.normalizar_nombre_persona),
    ("NOMBRES", "Nombres", nz.normalizar_nombre_persona),
    ("FECHA DE NACIMIENTO", "FechaNacimiento", nz.normalizar_fecha),
    ("SEXO", "Sexo", nz.normalizar_sexo),
    ("DOMICILIO", "DomicilioActual", nz.limpiar_texto),
    ("DISTRITO DE NACIMIENTO", "DistritoNacimiento", nz.normalizar_nombre_persona),
    ("PROVINCIA DE NACIMIENTO", "ProvinciaNacimiento", nz.normalizar_nombre_persona),
    ("DEPARTAMENTO DE NACIMIENTO", "DepartamentoNacimiento", nz.normalizar_nombre_persona),
    ("DISTRITO", "DistritoDomicilio", nz.normalizar_nombre_persona),
    ("CELULAR", "Celular", nz.normalizar_dni),
)

CAMPOS_PADRE = {
    "DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "FechaNacimiento",
    "Sexo", "DomicilioActual", "DistritoDomicilio", "Celular", "TelefonoFijo",
    "CorreoElectronico", "DomicilioActual", "GradoInstruccion", "OcupacionActual",
}


def _anio_mrz(dos_digitos: str) -> int:
    anio = int(dos_digitos)
    return 2000 + anio if anio <= 50 else 1900 + anio


def _fecha_mrz(texto: str) -> str | None:
    coincidencia = (
        re.search(r"(\d{2})(\d{2})(\d{2})\d[FM]", texto)
        or re.search(r"(\d{2})(\d{2})(\d{2})[FM]", texto)
    )
    if not coincidencia:
        return None
    anio, mes, dia = map(int, coincidencia.groups())
    try:
        return date(_anio_mrz(f"{anio:02d}"), mes, dia).isoformat()
    except ValueError:
        return None


def _extraer_mrz(lineas: list[Linea], tabla: str, resultado: dict[str, tuple[Any, int]]) -> None:
    """Parsea la zona legible por máquina que traen algunos DNI peruanos."""
    for texto, confianza in lineas:
        plano = nz.sin_tildes(texto)
        if "<" not in plano:
            continue

        dni = re.search(r"I<[A-Z]{3}(\d{8})", plano) or re.search(r"\b(\d{8})\b", plano)
        if dni:
            resultado[f"{tabla}.DNI"] = (dni.group(1), confianza)

        fecha = _fecha_mrz(plano)
        if fecha:
            resultado[f"{tabla}.FechaNacimiento"] = (fecha, confianza)
        sexo = re.search(r"\d{6,7}([FM])", plano)
        if sexo:
            resultado[f"{tabla}.Sexo"] = (sexo.group(1), confianza)

        if "<<<" in plano or "<<ANA" in plano or "<<<" in plano:
            partes = [p for p in re.split(r"<{2,}", plano.strip("<")) if p]
            if len(partes) >= 2:
                apellidos = nz.normalizar_nombre_persona(partes[0].replace("<", " "))
                nombres = nz.normalizar_nombre_persona(partes[1].replace("<", " "))
                if apellidos:
                    resultado[f"{tabla}.ApellidoPaterno"] = (apellidos, confianza)
                if nombres:
                    resultado[f"{tabla}.Nombres"] = (nombres, confianza)


def extraer_dni(lineas: list[Linea], tabla: str = "ESTUDIANTE") -> dict[str, tuple[Any, int]]:
    """Extrae campos del DNI. ``tabla`` decide qué columnas se devuelven."""
    resultado: dict[str, tuple[Any, int]] = {}
    permitidos = CAMPOS_PADRE if tabla == "PADRE_APODERADO" else {
        campo for _, campo, _ in ETIQUETAS_ESTUDIANTE
    }
    etiquetas = sorted(ETIQUETAS_ESTUDIANTE, key=lambda item: len(item[0]), reverse=True)
    normalizadas: list[Linea] = [(nz.sin_tildes(texto), conf) for texto, conf in lineas]

    for indice, (plano, confianza) in enumerate(normalizadas):
        for etiqueta, campo, normalizador in etiquetas:
            if campo not in permitidos:
                continue
            posicion = plano.find(etiqueta)
            if posicion < 0:
                continue
            resto = plano[posicion + len(etiqueta):].strip(" :.-")
            destino = f"{tabla}.{campo}"
            if resto:
                valor = normalizador(resto)
                if valor:
                    resultado[destino] = (valor, confianza)
            elif indice + 1 < len(normalizadas):
                candidato, conf_siguiente = normalizadas[indice + 1]
                es_etiqueta = any(et in candidato for et, _, _ in etiquetas)
                valor = normalizador(candidato)
                if valor and not es_etiqueta:
                    resultado[destino] = (valor, conf_siguiente)
            break

    if f"{tabla}.DNI" not in resultado:
        for plano, confianza in normalizadas:
            valor = nz.normalizar_dni(plano)
            if valor:
                resultado[f"{tabla}.DNI"] = (valor, confianza)
                break

    _extraer_mrz(lineas, tabla, resultado)
    return resultado
