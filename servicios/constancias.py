"""Constancias de logros y sus logros (CONSTANCIA_LOGROS / LOGRO)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar, ejecutar_filas, transaccion
from core.errores import ErrorValidacion
from core.formatos import (
    SITUACIONES,
    grados_de_nivel,
    normalizar_grado,
    normalizar_nivel,
    normalizar_situacion,
    validar_dni,
    validar_opcion,
)

CODIGO_RE = re.compile(r"^[A-Z0-9]{8}$")


def _codigo(valor: Any) -> str:
    codigo = str(valor or "").strip().upper()
    if not CODIGO_RE.match(codigo):
        raise ErrorValidacion("El código virtual debe tener 8 letras o números.")
    return codigo


def _fecha_hora(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    raise ErrorValidacion("La fecha y hora de emisión no tiene un formato válido.")


def _anio(valor: Any) -> int:
    try:
        anio = int(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion("El año escolar del logro no es válido.") from exc
    if anio < 2000 or anio > 2100:
        raise ErrorValidacion("El año escolar del logro no es válido.")
    return anio


def _grado(nivel: str, valor: Any) -> str:
    texto = str(valor or "").strip()
    if texto in grados_de_nivel(nivel):
        return texto
    try:
        return normalizar_grado(texto)
    except ErrorValidacion as exc:
        raise ErrorValidacion(
            f"El grado cursado no es válido para {nivel}. Use: "
            f"{', '.join(grados_de_nivel(nivel))}."
        ) from exc


def _normalizar_constancia(datos: dict[str, Any]) -> dict[str, Any]:
    dni = validar_dni(datos.get("DNI_Estudiante"), "DNI del estudiante")
    return {
        "CodigoVirtual": _codigo(datos.get("CodigoVirtual")),
        "DNI_Estudiante": dni,
        "NivelEducativo": normalizar_nivel(datos.get("NivelEducativo")),
        "FechaHoraEmision": _fecha_hora(datos.get("FechaHoraEmision")),
    }


def _normalizar_logros(nivel: str, logros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not logros:
        raise ErrorValidacion("La constancia debe tener al menos un logro.")
    salida: list[dict[str, Any]] = []
    anios: set[int] = set()
    for logro in logros:
        anio = _anio(logro.get("AñoEscolar"))
        if anio in anios:
            raise ErrorValidacion(f"El año {anio} está repetido en los logros.")
        anios.add(anio)
        codigo_ie = str(logro.get("CodigoModularIE") or "").strip().upper()
        if not codigo_ie:
            raise ErrorValidacion("Cada logro debe indicar la institución educativa.")
        salida.append(
            {
                "AñoEscolar": anio,
                "GradoCursado": _grado(nivel, logro.get("GradoCursado")),
                "CodigoModularIE": codigo_ie[:10],
                "SituacionFinal": validar_opcion(
                    normalizar_situacion(logro.get("SituacionFinal")), SITUACIONES, "situación"
                ),
            }
        )
    return salida


def _validar_ie(logros: list[dict[str, Any]], cursor=None) -> None:
    for logro in logros:
        if cursor is not None:
            cursor.execute(
                "SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s",
                (logro["CodigoModularIE"],),
            )
            existe = cursor.fetchone() is not None
        else:
            existe = consultar_uno(
                "SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s",
                (logro["CodigoModularIE"],),
            ) is not None
        if not existe:
            raise ErrorValidacion(
                f"La institución educativa {logro['CodigoModularIE']} no existe."
            )


def _insertar_logros(cursor, codigo: str, logros: list[dict[str, Any]]) -> None:
    for logro in logros:
        cursor.execute(
            "INSERT INTO LOGRO (CodigoVirtual, AñoEscolar, GradoCursado, CodigoModularIE, "
            "SituacionFinal) VALUES (%s, %s, %s, %s, %s)",
            (
                codigo, logro["AñoEscolar"], logro["GradoCursado"],
                logro["CodigoModularIE"], logro["SituacionFinal"],
            ),
        )


def crear_constancia(datos: dict[str, Any], logros: list[dict[str, Any]]) -> str:
    seguridad.requerir_secretaria()
    valores = _normalizar_constancia(datos)
    logros_normalizados = _normalizar_logros(valores["NivelEducativo"], logros)
    if not consultar_uno(
        "SELECT 1 FROM ESTUDIANTE WHERE DNI = %s", (valores["DNI_Estudiante"],)
    ):
        raise ErrorValidacion("El estudiante no existe.")
    _validar_ie(logros_normalizados)
    with transaccion() as cursor:
        cursor.execute(
            "INSERT INTO CONSTANCIA_LOGROS (CodigoVirtual, DNI_Estudiante, NivelEducativo, "
            "FechaHoraEmision) VALUES (%s, %s, %s, %s)",
            (
                valores["CodigoVirtual"], valores["DNI_Estudiante"],
                valores["NivelEducativo"], valores["FechaHoraEmision"],
            ),
        )
        _insertar_logros(cursor, valores["CodigoVirtual"], logros_normalizados)
    return valores["CodigoVirtual"]


def obtener_constancia(codigo: str) -> dict[str, Any] | None:
    constancia = consultar_uno(
        "SELECT c.*, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres "
        "FROM CONSTANCIA_LOGROS c INNER JOIN ESTUDIANTE e ON e.DNI = c.DNI_Estudiante "
        "WHERE c.CodigoVirtual = %s",
        (_codigo(codigo),),
    )
    if constancia:
        constancia["logros"] = consultar(
            "SELECT * FROM LOGRO WHERE CodigoVirtual = %s ORDER BY AñoEscolar",
            (constancia["CodigoVirtual"],),
        )
    return constancia


def listar_constancias(filtro: str = "") -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    texto = f"%{filtro.strip()}%"
    return consultar(
        "SELECT c.*, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres, "
        "(SELECT COUNT(*) FROM LOGRO l WHERE l.CodigoVirtual = c.CodigoVirtual) AS TotalLogros "
        "FROM CONSTANCIA_LOGROS c INNER JOIN ESTUDIANTE e ON e.DNI = c.DNI_Estudiante "
        "WHERE c.CodigoVirtual LIKE %s OR c.DNI_Estudiante LIKE %s OR e.Nombres LIKE %s "
        "OR e.ApellidoPaterno LIKE %s OR e.ApellidoMaterno LIKE %s "
        "ORDER BY c.FechaHoraEmision DESC, c.CodigoVirtual",
        (texto, texto, texto, texto, texto),
    )


def actualizar_constancia(
    codigo: str, datos: dict[str, Any], logros: list[dict[str, Any]] | None = None
) -> None:
    seguridad.requerir_secretaria()
    actual = obtener_constancia(codigo)
    if not actual:
        raise ErrorValidacion("La constancia no existe.")
    valores = _normalizar_constancia({**actual, **datos, "CodigoVirtual": actual["CodigoVirtual"]})
    nivel = valores["NivelEducativo"]
    logros_normalizados = (
        _normalizar_logros(nivel, logros) if logros is not None else None
    )
    if logros_normalizados is not None:
        _validar_ie(logros_normalizados)
    with transaccion() as cursor:
        cursor.execute(
            "UPDATE CONSTANCIA_LOGROS SET DNI_Estudiante = %s, NivelEducativo = %s, "
            "FechaHoraEmision = %s WHERE CodigoVirtual = %s",
            (
                valores["DNI_Estudiante"], nivel,
                valores["FechaHoraEmision"], valores["CodigoVirtual"],
            ),
        )
        if logros_normalizados is not None:
            cursor.execute(
                "DELETE FROM LOGRO WHERE CodigoVirtual = %s", (valores["CodigoVirtual"],)
            )
            _insertar_logros(cursor, valores["CodigoVirtual"], logros_normalizados)


def eliminar_constancia(codigo: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas("DELETE FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s", (_codigo(codigo),))


def agregar_logro(codigo: str, logro: dict[str, Any]) -> None:
    seguridad.requerir_secretaria()
    constancia = obtener_constancia(codigo)
    if not constancia:
        raise ErrorValidacion("La constancia no existe.")
    normalizado = _normalizar_logros(constancia["NivelEducativo"], [logro])[0]
    _validar_ie([normalizado])
    ejecutar(
        "INSERT INTO LOGRO (CodigoVirtual, AñoEscolar, GradoCursado, CodigoModularIE, "
        "SituacionFinal) VALUES (%s, %s, %s, %s, %s)",
        (
            constancia["CodigoVirtual"], normalizado["AñoEscolar"], normalizado["GradoCursado"],
            normalizado["CodigoModularIE"], normalizado["SituacionFinal"],
        ),
    )


def actualizar_logro(codigo: str, anio: int, datos: dict[str, Any]) -> None:
    seguridad.requerir_secretaria()
    constancia = obtener_constancia(codigo)
    if not constancia:
        raise ErrorValidacion("La constancia no existe.")
    anio = _anio(anio)
    actual = consultar_uno(
        "SELECT * FROM LOGRO WHERE CodigoVirtual = %s AND AñoEscolar = %s",
        (constancia["CodigoVirtual"], anio),
    )
    if not actual:
        raise ErrorValidacion("El logro no existe.")
    normalizado = _normalizar_logros(
        constancia["NivelEducativo"], [{**actual, **datos, "AñoEscolar": anio}]
    )[0]
    _validar_ie([normalizado])
    ejecutar(
        "UPDATE LOGRO SET GradoCursado = %s, CodigoModularIE = %s, SituacionFinal = %s "
        "WHERE CodigoVirtual = %s AND AñoEscolar = %s",
        (
            normalizado["GradoCursado"], normalizado["CodigoModularIE"],
            normalizado["SituacionFinal"], constancia["CodigoVirtual"], anio,
        ),
    )


def eliminar_logro(codigo: str, anio: int) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas(
        "DELETE FROM LOGRO WHERE CodigoVirtual = %s AND AñoEscolar = %s",
        (_codigo(codigo), _anio(anio)),
    )


def logros_de_estudiante(dni: str) -> list[dict[str, Any]]:
    return consultar(
        "SELECT l.*, c.NivelEducativo, c.FechaHoraEmision FROM LOGRO l "
        "INNER JOIN CONSTANCIA_LOGROS c ON c.CodigoVirtual = l.CodigoVirtual "
        "WHERE c.DNI_Estudiante = %s ORDER BY l.AñoEscolar",
        (validar_dni(dni),),
    )


def insertar_en_transaccion(cursor, valores: dict[str, Any]) -> None:
    cursor.execute(
        "INSERT INTO CONSTANCIA_LOGROS (CodigoVirtual, DNI_Estudiante, NivelEducativo, "
        "FechaHoraEmision) VALUES (%s, %s, %s, %s)",
        (
            valores["CodigoVirtual"], valores["DNI_Estudiante"],
            valores["NivelEducativo"], valores["FechaHoraEmision"],
        ),
    )


def reemplazar_logros_en_transaccion(cursor, codigo: str, logros: list[dict[str, Any]]) -> None:
    cursor.execute("DELETE FROM LOGRO WHERE CodigoVirtual = %s", (codigo,))
    _insertar_logros(cursor, codigo, logros)


def normalizar_constancia(datos: dict[str, Any]) -> dict[str, Any]:
    return _normalizar_constancia(datos)


def normalizar_logros(nivel: str, logros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _normalizar_logros(nivel, logros)


def validar_ie(logros: list[dict[str, Any]], cursor=None) -> None:
    _validar_ie(logros, cursor)


def fecha_actual() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hoy() -> date:
    return date.today()
