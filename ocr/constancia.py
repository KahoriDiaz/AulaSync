"""Extractor de datos de una constancia de logros de aprendizaje."""
from __future__ import annotations

import re

from ocr.dni import Campo, LineaOCR, _buscar, _texto_completo
from ocr.normalizacion import (
    limpiar,
    normalizar_codigo_modular,
    normalizar_codigo_virtual,
    normalizar_dni,
    normalizar_fecha_hora,
    normalizar_grado,
    normalizar_nivel,
    normalizar_situacion,
    normalizar_tipo_ie,
)

_MESES = (
    "ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|"
    "NOVIEMBRE|DICIEMBRE"
)


def _fecha_hora(texto: str) -> str | None:
    fecha = normalizar_fecha_hora(texto)
    if fecha:
        return fecha
    coincidencia = re.search(
        rf"\b(\d{{1,2}})\s+DE\s+({_MESES})\s+DE\s+(\d{{4}})\b", texto.upper()
    )
    if not coincidencia:
        return None
    meses = {
        "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
        "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10,
        "NOVIEMBRE": 11, "DICIEMBRE": 12,
    }
    dia, mes, anio = coincidencia.groups()
    hora = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b", texto)
    hh, mm, ss = hora.groups() if hora else ("0", "0", "0")
    return f"{anio}-{meses[mes]:02d}-{int(dia):02d} {int(hh):02d}:{int(mm):02d}:{int(ss):02d}"


def _codigo_modular(texto: str) -> str | None:
    coincidencia = re.search(r"\b\d{7}(?:-\d)?\b", texto)
    if coincidencia:
        return normalizar_codigo_modular(coincidencia.group(0))
    return None


def extraer_constancia(
    lineas: list[LineaOCR], origen: str = "OCR"
) -> tuple[dict[str, Campo], list[dict[str, Campo]]]:
    campos: dict[str, Campo] = {}
    texto_completo = _texto_completo(lineas)

    codigo = _buscar(lineas, ("CODIGO VIRTUAL", "CÓDIGO VIRTUAL", "CODIGO DE CONSTANCIA"))
    codigo_virtual = None
    if codigo:
        codigo_virtual = normalizar_codigo_virtual(codigo[0]) or normalizar_codigo_virtual(
            codigo[0].split()[0] if codigo[0].split() else ""
        )
    if codigo_virtual is None:
        for token in re.findall(r"\b[A-Z0-9]{8}\b", texto_completo.upper()):
            if re.search(r"\d", token) and re.search(r"[A-Z]", token):
                codigo_virtual = token
                break
    if codigo_virtual:
        campos["CONSTANCIA_LOGROS.CodigoVirtual"] = (
            codigo_virtual,
            codigo[1] if codigo else 60,
            origen,
        )

    dni = _buscar(lineas, ("DNI",))
    dni_normalizado = normalizar_dni(dni[0]) if dni else None
    if dni_normalizado is None:
        coincidencia = re.search(r"(?<!\d)\d{8}(?!\d)", texto_completo)
        if coincidencia:
            dni_normalizado = coincidencia.group(0)
    if dni_normalizado:
        campos["CONSTANCIA_LOGROS.DNI_Estudiante"] = (
            dni_normalizado,
            dni[1] if dni else 60,
            origen,
        )

    nivel = normalizar_nivel(texto_completo)
    if nivel:
        confianza_nivel = 90
        for texto, confianza in lineas:
            if normalizar_nivel(texto):
                confianza_nivel = confianza
                break
        campos["CONSTANCIA_LOGROS.NivelEducativo"] = (nivel, confianza_nivel, origen)

    fecha = _buscar(lineas, ("FECHA DE EMISION", "FECHA EMISION", "FECHA DE EMISIÓN", "EMITIDA"))
    crudo = fecha[0] if fecha else texto_completo
    fecha_hora = _fecha_hora(crudo)
    if fecha_hora:
        campos["CONSTANCIA_LOGROS.FechaHoraEmision"] = (
            fecha_hora,
            fecha[1] if fecha else 65,
            origen,
        )

    codigo_ie = _buscar(lineas, ("CODIGO MODULAR", "CÓDIGO MODULAR"))
    modular = None
    if codigo_ie:
        modular = normalizar_codigo_modular(codigo_ie[0])
    if modular is None:
        modular = _codigo_modular(texto_completo)
    if modular:
        campos["INSTITUCION_EDUCATIVA.CodigoModularIE"] = (
            modular,
            codigo_ie[1] if codigo_ie else 65,
            origen,
        )

    nombre_ie = _buscar(lineas, ("INSTITUCION EDUCATIVA", "INSTITUCIÓN EDUCATIVA", "I.E.", "IE"))
    if nombre_ie:
        nombre = re.sub(r"CODIGO MODULAR.*$", "", nombre_ie[0], flags=re.IGNORECASE)
        nombre = limpiar(nombre)
        if nombre:
            campos["INSTITUCION_EDUCATIVA.NombreIE"] = (nombre[:50], nombre_ie[1], origen)

    tipo_ie = normalizar_tipo_ie(texto_completo)
    if tipo_ie:
        campos["INSTITUCION_EDUCATIVA.TipoIE"] = (tipo_ie, 80, origen)

    logros = _extraer_logros(lineas, modular, origen)
    return campos, logros


def _extraer_logros(
    lineas: list[LineaOCR], modular: str | None, origen: str
) -> list[dict[str, Campo]]:
    inicios: list[tuple[int, str, int]] = []
    for indice, (texto, confianza) in enumerate(lineas):
        if re.search(r"(EMISION|EMISIÓN|EMITIDA|NACIMIENTO|CONSTANCIA)", texto.upper()):
            continue
        coincidencia = re.search(r"\b(19|20)\d{2}\b", texto)
        if not coincidencia:
            continue
        if normalizar_grado(texto) or normalizar_situacion(texto) or texto.count(" ") >= 2:
            inicios.append((indice, coincidencia.group(0), confianza))

    logros: list[dict[str, Campo]] = []
    for posicion, (indice, anio, confianza) in enumerate(inicios):
        fin = inicios[posicion + 1][0] if posicion + 1 < len(inicios) else len(lineas)
        seccion = lineas[indice:fin]
        texto_seccion = " ".join(texto for texto, _ in seccion)
        grado = normalizar_grado(texto_seccion)
        situacion = normalizar_situacion(texto_seccion)
        if grado is None and situacion is None:
            continue
        logro: dict[str, Campo] = {
            "LOGRO.AñoEscolar": (anio, confianza, origen),
        }
        if grado:
            logro["LOGRO.GradoCursado"] = (grado, confianza, origen)
        if situacion:
            logro["LOGRO.SituacionFinal"] = (situacion, confianza, origen)
        codigo = _codigo_modular(texto_seccion) or modular
        if codigo:
            logro["LOGRO.CodigoModularIE"] = (codigo, confianza, origen)
        if len(logro) >= 3:
            logros.append(logro)
    return logros
