from datetime import date

import pytest

from core.errores import ErrorValidacion
from core.formatos import (
    normalizar_grado,
    normalizar_situacion,
    validar_celular,
    validar_dni,
    validar_si_no,
)


def test_dni_valido():
    assert validar_dni("70000001") == "70000001"


@pytest.mark.parametrize("valor", ["1234567", "123456789", "abcdefgh", ""])
def test_dni_invalido(valor):
    with pytest.raises(ErrorValidacion):
        validar_dni(valor)


def test_celular_opcional():
    assert validar_celular("", opcional=True) is None
    assert validar_celular("987654321") == "987654321"


def test_celular_invalido():
    with pytest.raises(ErrorValidacion):
        validar_celular("123")


@pytest.mark.parametrize(
    "entrada,esperado",
    [("TERCERO", "3.°"), ("3ER GRADO", "3.°"), ("1", "1.°"), ("5.°", "5.°")],
)
def test_normalizar_grado(entrada, esperado):
    assert normalizar_grado(entrada) == esperado


def test_normalizar_situacion():
    assert normalizar_situacion("Aprobado") == "APROBADO"
    assert normalizar_situacion("Requiere recuperacion") == "REQUIERE RECUPERACIÓN"
    with pytest.raises(ErrorValidacion):
        normalizar_situacion("Otro")


@pytest.mark.parametrize("valor", [True, "SI", "1", 1])
def test_validar_si_no_verdadero(valor):
    assert validar_si_no(valor, "campo") is True


@pytest.mark.parametrize("valor", [False, "NO", "0", 0])
def test_validar_si_no_falso(valor):
    assert validar_si_no(valor, "campo") is False


def test_fecha_valida():
    from core.formatos import normalizar_fecha

    assert normalizar_fecha("15/03/2014") == "2014-03-15"
    assert normalizar_fecha(date(2014, 3, 15)) == "2014-03-15"
