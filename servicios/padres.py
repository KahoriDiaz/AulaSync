"""Padres y apoderados (PADRE_APODERADO)."""
from __future__ import annotations

from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar, ejecutar_filas
from core.errores import ErrorValidacion
from core.formatos import (
    GRADOS_INSTRUCCION,
    normalizar_nombre,
    normalizar_sexo,
    validar_celular,
    validar_correo,
    validar_dni,
    validar_fecha_no_futura,
    validar_opcion,
)

COLUMNAS = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno",
    "FechaNacimiento", "OcupacionActual", "GradoInstruccion", "DomicilioActual",
    "DistritoDomicilio", "TelefonoFijo", "Celular", "CorreoElectronico",
)


def _texto(datos: dict[str, Any], campo: str, obligatorio: bool = True, maximo: int = 100) -> str | None:
    valor = str(datos.get(campo) or "").strip()
    if not valor:
        if obligatorio:
            raise ErrorValidacion(f"El campo {campo} es obligatorio.")
        return None
    if len(valor) > maximo:
        raise ErrorValidacion(f"El campo {campo} no puede superar {maximo} caracteres.")
    return valor


def _normalizar(datos: dict[str, Any]) -> dict[str, Any]:
    return {
        "DNI": validar_dni(datos.get("DNI")),
        "Sexo": normalizar_sexo(datos.get("Sexo")),
        "Nombres": normalizar_nombre(_texto(datos, "Nombres", maximo=50)),
        "ApellidoPaterno": normalizar_nombre(_texto(datos, "ApellidoPaterno", maximo=30)),
        "ApellidoMaterno": normalizar_nombre(_texto(datos, "ApellidoMaterno", maximo=30)),
        "FechaNacimiento": validar_fecha_no_futura(datos.get("FechaNacimiento")),
        "OcupacionActual": _texto(datos, "OcupacionActual", obligatorio=False, maximo=50),
        "GradoInstruccion": validar_opcion(
            datos.get("GradoInstruccion"), GRADOS_INSTRUCCION, "grado de instrucción"
        ),
        "DomicilioActual": _texto(datos, "DomicilioActual", maximo=100),
        "DistritoDomicilio": _texto(datos, "DistritoDomicilio", maximo=30),
        "TelefonoFijo": validar_celular(
            datos.get("TelefonoFijo"), "teléfono fijo", opcional=True
        ),
        "Celular": validar_celular(datos.get("Celular"), "celular"),
        "CorreoElectronico": validar_correo(datos.get("CorreoElectronico"), "correo", opcional=True),
    }


def crear_padre(datos: dict[str, Any]) -> str:
    seguridad.requerir_secretaria()
    valores = _normalizar(datos)
    ejecutar(
        "INSERT INTO PADRE_APODERADO (DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, "
        "FechaNacimiento, OcupacionActual, GradoInstruccion, DomicilioActual, DistritoDomicilio, "
        "TelefonoFijo, Celular, CorreoElectronico) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        tuple(valores[c] for c in COLUMNAS),
    )
    return valores["DNI"]


def obtener_padre(dni: str) -> dict[str, Any] | None:
    return consultar_uno("SELECT * FROM PADRE_APODERADO WHERE DNI = %s", (validar_dni(dni),))


def listar_padres(filtro: str = "") -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    texto = f"%{filtro.strip()}%"
    return consultar(
        "SELECT * FROM PADRE_APODERADO WHERE DNI LIKE %s OR Nombres LIKE %s "
        "OR ApellidoPaterno LIKE %s OR ApellidoMaterno LIKE %s "
        "ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres",
        (texto, texto, texto, texto),
    )


def actualizar_padre(dni: str, datos: dict[str, Any]) -> None:
    seguridad.requerir_secretaria()
    actual = obtener_padre(dni)
    if not actual:
        raise ErrorValidacion("El padre o apoderado no existe.")
    combinado = {**actual, **datos, "DNI": actual["DNI"]}
    valores = _normalizar(combinado)
    ejecutar(
        "UPDATE PADRE_APODERADO SET Sexo=%s, Nombres=%s, ApellidoPaterno=%s, ApellidoMaterno=%s, "
        "FechaNacimiento=%s, OcupacionActual=%s, GradoInstruccion=%s, DomicilioActual=%s, "
        "DistritoDomicilio=%s, TelefonoFijo=%s, Celular=%s, CorreoElectronico=%s WHERE DNI=%s",
        (
            valores["Sexo"], valores["Nombres"], valores["ApellidoPaterno"],
            valores["ApellidoMaterno"], valores["FechaNacimiento"], valores["OcupacionActual"],
            valores["GradoInstruccion"], valores["DomicilioActual"], valores["DistritoDomicilio"],
            valores["TelefonoFijo"], valores["Celular"], valores["CorreoElectronico"],
            valores["DNI"],
        ),
    )


def eliminar_padre(dni: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas("DELETE FROM PADRE_APODERADO WHERE DNI = %s", (validar_dni(dni),))


def insertar_en_transaccion(cursor, valores: dict[str, Any]) -> None:
    cursor.execute(
        "INSERT INTO PADRE_APODERADO (DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, "
        "FechaNacimiento, OcupacionActual, GradoInstruccion, DomicilioActual, DistritoDomicilio, "
        "TelefonoFijo, Celular, CorreoElectronico) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        tuple(valores[c] for c in COLUMNAS),
    )


def actualizar_en_transaccion(cursor, valores: dict[str, Any]) -> None:
    cursor.execute(
        "UPDATE PADRE_APODERADO SET Sexo=%s, Nombres=%s, ApellidoPaterno=%s, ApellidoMaterno=%s, "
        "FechaNacimiento=%s, OcupacionActual=%s, GradoInstruccion=%s, DomicilioActual=%s, "
        "DistritoDomicilio=%s, TelefonoFijo=%s, Celular=%s, CorreoElectronico=%s WHERE DNI=%s",
        (
            valores["Sexo"], valores["Nombres"], valores["ApellidoPaterno"],
            valores["ApellidoMaterno"], valores["FechaNacimiento"], valores["OcupacionActual"],
            valores["GradoInstruccion"], valores["DomicilioActual"], valores["DistritoDomicilio"],
            valores["TelefonoFijo"], valores["Celular"], valores["CorreoElectronico"],
            valores["DNI"],
        ),
    )


def normalizar(datos: dict[str, Any]) -> dict[str, Any]:
    return _normalizar(datos)
