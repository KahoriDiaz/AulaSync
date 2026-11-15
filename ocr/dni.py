"""Extractor de datos de un DNI (estudiante o padre/apoderado)."""
from __future__ import annotations

import re

from ocr.normalizacion import (
    limpiar,
    mayuscula_inicial,
    normalizar_dni,
    normalizar_fecha,
    normalizar_sexo,
)

LineaOCR = tuple[str, int]
Campo = tuple[str, int, str]

_ETIQUETAS = (
    "APELLIDO PATERNO",
    "PRIMER APELLIDO",
    "APELLIDO MATERNO",
    "SEGUNDO APELLIDO",
    "PRE NOMBRES",
    "PRENOMBRES",
    "NOMBRES",
    "FECHA DE NACIMIENTO",
    "FECHA NACIMIENTO",
    "SEXO",
    "DOMICILIO",
    "DIRECCION",
    "DISTRITO DE NACIMIENTO",
    "PROVINCIA DE NACIMIENTO",
    "DEPARTAMENTO DE NACIMIENTO",
    "DISTRITO DE DOMICILIO",
    "DISTRITO",
    "PROVINCIA",
    "DEPARTAMENTO",
    "DNI",
    "DOCUMENTO NACIONAL DE IDENTIDAD",
)


def _patron(etiqueta: str) -> re.Pattern[str]:
    palabras = [re.escape(p) for p in etiqueta.split()]
    return re.compile(r"\b" + r"\s+".join(palabras) + r"\b\s*[:.\-]?\s*", re.IGNORECASE)


_PATRONES = {etiqueta: _patron(etiqueta) for etiqueta in _ETIQUETAS}


def _parece_etiqueta(texto: str) -> bool:
    norm = texto.upper().strip(" :.-")
    return any(norm == etiqueta or norm.startswith(etiqueta + " ") for etiqueta in _ETIQUETAS)


def _buscar(lineas: list[LineaOCR], etiquetas: tuple[str, ...]) -> tuple[str, int] | None:
    for indice, (texto, confianza) in enumerate(lineas):
        for etiqueta in etiquetas:
            patron = _PATRONES.get(etiqueta)
            if patron is None:
                patron = _patron(etiqueta)
                _PATRONES[etiqueta] = patron
            coincidencia = patron.search(texto)
            if not coincidencia:
                continue
            resto = texto[coincidencia.end():].strip(" :;.-")
            if (
                etiqueta in ("DISTRITO", "PROVINCIA", "DEPARTAMENTO")
                and resto.upper().startswith("DE ")
            ):
                continue
            if resto and not _parece_etiqueta(resto):
                return resto, confianza
            for siguiente in range(indice + 1, min(indice + 3, len(lineas))):
                candidato = lineas[siguiente][0].strip(" :;.-")
                if candidato and not _parece_etiqueta(candidato):
                    return limpiar(candidato), lineas[siguiente][1]
    return None


def _texto_completo(lineas: list[LineaOCR]) -> str:
    return "\n".join(texto for texto, _ in lineas)


def _limpiar_nombre(valor: str) -> str:
    limpio = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ' ]+", " ", valor)
    return mayuscula_inicial(limpiar(limpio))


_MRZ_CARACTERES = re.compile(r"^[A-Z0-9<]+$")


def _lineas_mrz(lineas: list[LineaOCR]) -> list[str]:
    """Devuelve candidatas a zona de lectura mecánica (MRZ) en orden de aparición."""
    candidatas: list[str] = []
    for texto, _ in lineas:
        limpio = re.sub(r"\s+", "", texto.upper())
        if 28 <= len(limpio) <= 44 and limpio.count("<") >= 3 and _MRZ_CARACTERES.match(limpio):
            candidatas.append(limpio)
    return candidatas


def _mrz(lineas: list[LineaOCR]) -> dict[str, Campo]:
    """Extrae DNI, fecha de nacimiento, sexo y nombres desde la MRZ del DNI (TD1)."""
    candidatas = _lineas_mrz(lineas)
    if not candidatas:
        return {}
    resultado: dict[str, Campo] = {}

    for linea in candidatas:
        coincidencia = re.search(r"PER([0-9<]{8,9})", linea)
        if not coincidencia:
            continue
        numero = re.sub(r"[^0-9]", "", coincidencia.group(1))
        if len(numero) == 8:
            resultado["DNI"] = (numero, 95, "OCR (MRZ)")
            break

    for linea in candidatas:
        coincidencia = re.match(r"(\d{2})(\d{2})(\d{2})\d*([MF])[A-Z<]?(\d{6})", linea)
        if not coincidencia:
            continue
        anio, mes, dia = (int(g) for g in coincidencia.groups()[:3])
        anio += 2000 if anio < 30 else 1900
        try:
            from datetime import date

            fecha = date(anio, mes, dia).isoformat()
        except ValueError:
            fecha = f"{anio:04d}-{mes:02d}-{dia:02d}"
        resultado["FechaNacimiento"] = (fecha, 90, "OCR (MRZ)")
        sexo = coincidencia.group(4)
        if sexo in ("M", "F"):
            resultado["Sexo"] = (sexo, 90, "OCR (MRZ)")
        break

    for linea in candidatas:
        if re.search(r"\d", linea) or "<" not in linea:
            continue
        partes = linea.split("<<")
        apellidos = partes[0].replace("<", " ").strip()
        nombres = partes[1].replace("<", " ").strip() if len(partes) > 1 else ""
        if apellidos:
            resultado["ApellidoPaterno"] = (_limpiar_nombre(apellidos), 85, "OCR (MRZ)")
        if nombres:
            resultado["Nombres"] = (_limpiar_nombre(nombres), 85, "OCR (MRZ)")
        break
    return resultado


def _campo(valor: str | None, confianza: int, origen: str) -> Campo | None:
    if not valor:
        return None
    return (valor, max(0, min(100, int(confianza))), origen)


def extraer_dni(
    lineas: list[LineaOCR], tabla: str = "ESTUDIANTE", origen: str = "OCR"
) -> dict[str, Campo]:
    """Devuelve campos con clave 'TABLA.Columna'."""
    resultado: dict[str, Campo] = {}
    texto_completo = _texto_completo(lineas)

    dni = None
    encontrado = _buscar(lineas, ("DNI",))
    if encontrado:
        dni = normalizar_dni(encontrado[0])
        confianza_dni = encontrado[1]
    else:
        confianza_dni = 0
    if dni is None:
        coincidencia = re.search(r"\bDNI\b\s*[:.\-]?\s*(\d{8})", texto_completo, re.IGNORECASE)
        if coincidencia:
            dni = coincidencia.group(1)
            confianza_dni = 75
    if dni is None:
        numeros = re.findall(r"(?<!\d)\d{8}(?!\d)", texto_completo)
        for numero in numeros:
            if not re.search(rf"\b\d{{1,2}}[/.-]{numero[:2]}[/.-]\d{{4}}\b", texto_completo):
                dni = numero
                confianza_dni = 60
                break
    if dni:
        resultado[f"{tabla}.DNI"] = (dni, confianza_dni, origen)

    apellido_paterno = _buscar(lineas, ("APELLIDO PATERNO", "PRIMER APELLIDO"))
    if apellido_paterno:
        resultado[f"{tabla}.ApellidoPaterno"] = (
            _limpiar_nombre(apellido_paterno[0]),
            apellido_paterno[1],
            origen,
        )
    apellido_materno = _buscar(lineas, ("APELLIDO MATERNO", "SEGUNDO APELLIDO"))
    if apellido_materno:
        resultado[f"{tabla}.ApellidoMaterno"] = (
            _limpiar_nombre(apellido_materno[0]),
            apellido_materno[1],
            origen,
        )
    nombres = _buscar(lineas, ("PRE NOMBRES", "PRENOMBRES", "NOMBRES"))
    if nombres:
        resultado[f"{tabla}.Nombres"] = (
            _limpiar_nombre(nombres[0]),
            nombres[1],
            origen,
        )

    fecha = _buscar(lineas, ("FECHA DE NACIMIENTO", "FECHA NACIMIENTO"))
    crudo_fecha = fecha[0] if fecha else None
    if not crudo_fecha:
        coincidencia = re.search(
            r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\b", texto_completo
        )
        if coincidencia:
            crudo_fecha = coincidencia.group(1)
            fecha = (crudo_fecha, 70)
    if crudo_fecha and fecha:
        normalizada = normalizar_fecha(crudo_fecha)
        resultado[f"{tabla}.FechaNacimiento"] = (
            normalizada or crudo_fecha,
            fecha[1] if normalizada else 0,
            origen,
        )

    sexo = None
    encontrado_sexo = _buscar(lineas, ("SEXO",))
    if encontrado_sexo:
        sexo = normalizar_sexo(encontrado_sexo[0])
        confianza_sexo = encontrado_sexo[1]
    else:
        coincidencia = re.search(r"SEXO\s*[:.]?\s*([MF])\b", texto_completo, re.IGNORECASE)
        sexo = coincidencia.group(1).upper() if coincidencia else None
        confianza_sexo = 60
    if sexo:
        resultado[f"{tabla}.Sexo"] = (sexo, confianza_sexo, origen)

    domicilio = _buscar(lineas, ("DOMICILIO", "DIRECCION"))
    if domicilio:
        resultado[f"{tabla}.DomicilioActual"] = (limpiar(domicilio[0]), domicilio[1], origen)
    distrito = _buscar(lineas, ("DISTRITO DE DOMICILIO", "DISTRITO"))
    if distrito:
        resultado[f"{tabla}.DistritoDomicilio"] = (mayuscula_inicial(distrito[0]), distrito[1], origen)

    if tabla == "ESTUDIANTE":
        distrito_nac = _buscar(lineas, ("DISTRITO DE NACIMIENTO",))
        provincia_nac = _buscar(lineas, ("PROVINCIA DE NACIMIENTO",))
        departamento_nac = _buscar(lineas, ("DEPARTAMENTO DE NACIMIENTO",))
        if distrito_nac:
            resultado["ESTUDIANTE.DistritoNacimiento"] = (
                mayuscula_inicial(distrito_nac[0]), distrito_nac[1], origen
            )
        if provincia_nac:
            resultado["ESTUDIANTE.ProvinciaNacimiento"] = (
                mayuscula_inicial(provincia_nac[0]), provincia_nac[1], origen
            )
        if departamento_nac:
            resultado["ESTUDIANTE.DepartamentoNacimiento"] = (
                mayuscula_inicial(departamento_nac[0]), departamento_nac[1], origen
            )

    mrz = _mrz(lineas)
    for sufijo, valor in mrz.items():
        resultado.setdefault(f"{tabla}.{sufijo}", valor)
    if "DNI" in mrz:
        resultado[f"{tabla}.DNI"] = mrz["DNI"]

    return {clave: valor for clave, valor in resultado.items() if valor and valor[0]}
