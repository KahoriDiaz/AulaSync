"""Extracción de campos y logros de una constancia de logros (§6.2 punto 3).

Entrada: lista de ``(texto, confianza)``. Devuelve ``(campos, logros)`` con el
mismo formato ``"TABLA.Campo": (valor, confianza)`` que :mod:`ocr.dni`.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from ocr import normalizacion as nz

Linea = tuple[str, int]
Valor = tuple[Any, int]


def _buscar(
    lineas: list[Linea], etiqueta: str, normalizador: Callable[[Any], Any]
) -> Valor | None:
    etiqueta_plana = nz.sin_tildes(etiqueta)
    planas: list[Linea] = [(nz.sin_tildes(texto), conf) for texto, conf in lineas]
    for indice, (plano, confianza) in enumerate(planas):
        posicion = plano.find(etiqueta_plana)
        if posicion < 0:
            continue
        resto = plano[posicion + len(etiqueta_plana):].strip(" :.-")
        if not resto and indice + 1 < len(planas):
            resto, confianza = planas[indice + 1]
        if resto:
            valor = normalizador(resto)
            if valor:
                return valor, confianza
    return None


def extraer_constancia(lineas: list[Linea]) -> tuple[dict[str, Valor], list[dict[str, Valor]]]:
    """Devuelve los campos de la constancia y la tabla de logros detectados."""
    campos: dict[str, Valor] = {}
    definiciones = (
        ("CONSTANCIA_LOGROS.CodigoVirtual", "CODIGO VIRTUAL", nz.normalizar_codigo_virtual),
        ("CONSTANCIA_LOGROS.DNI_Estudiante", "DNI", nz.normalizar_dni),
        ("CONSTANCIA_LOGROS.NivelEducativo", "NIVEL", nz.normalizar_nivel),
        ("CONSTANCIA_LOGROS.FechaHoraEmision", "FECHA DE EMISION", nz.normalizar_fecha_hora),
        ("INSTITUCION_EDUCATIVA.CodigoModularIE", "CODIGO MODULAR", nz.normalizar_codigo_modular),
        ("INSTITUCION_EDUCATIVA.NombreIE", "INSTITUCION EDUCATIVA", nz.limpiar_texto),
        ("INSTITUCION_EDUCATIVA.TipoIE", "TIPO", nz.normalizar_tipo_ie),
    )
    for clave, etiqueta, normalizador in definiciones:
        encontrado = _buscar(lineas, etiqueta, normalizador)
        if encontrado:
            campos[clave] = encontrado

    codigo_ie = campos.get("INSTITUCION_EDUCATIVA.CodigoModularIE", ("", 0))[0]
    logros: list[dict[str, Valor]] = []
    patron = re.compile(
        r"^(\d{4})\s+(.+?)\s+(APROBADO|REQUIERE RECUPERACION)\b", re.IGNORECASE
    )
    for texto, confianza in lineas:
        plano = nz.sin_tildes(texto)
        coincidencia = patron.match(plano)
        if not coincidencia:
            continue
        anio, grado_texto, situacion_texto = coincidencia.groups()
        grado = nz.normalizar_grado(grado_texto)
        situacion = nz.normalizar_situacion(situacion_texto)
        if not grado or not situacion:
            continue
        logro: dict[str, Valor] = {
            "LOGRO.AñoEscolar": (anio, confianza),
            "LOGRO.GradoCursado": (grado, confianza),
            "LOGRO.SituacionFinal": (situacion, confianza),
        }
        if codigo_ie:
            logro["LOGRO.CodigoModularIE"] = (codigo_ie, confianza)
        logros.append(logro)
    return campos, logros
