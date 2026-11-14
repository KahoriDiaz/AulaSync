"""Pruebas de integración con la base de datos real (se omiten si no hay conexión)."""
import pytest

from core import seguridad
from core.db import conectar, consultar
from servicios import constancias, estudiantes, instituciones, matriculas, padres

CONTEOS_ESPERADOS = {
    "CONTACTO_EMERGENCIA": 6,
    "INSTITUCION_EDUCATIVA": 4,
    "PADRE_APODERADO": 10,
    "ESTUDIANTE": 10,
    "ESTUDIANTE_NEE": 9,
    "ESTUDIANTE_HERMANOS_IE": 7,
    "HERMANDAD": 4,
    "TIENE_PADRES": 13,
    "CONSTANCIA_LOGROS": 3,
    "LOGRO": 8,
    "MATRICULA": 13,
    "SECRETARIA": 1,
    "USUARIO": 1,
}


def _hay_bd() -> bool:
    try:
        cnx = conectar()
        cnx.close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _hay_bd(), reason="Sin conexión a la base de datos de pruebas")


@pytest.fixture(autouse=True)
def sesion_administrador():
    seguridad.iniciar_sesion(
        seguridad.Sesion(1, "pruebas", "Administrador", "00000000", "Cuenta", "Pruebas")
    )
    yield
    seguridad.cerrar_sesion()


def test_trece_tablas():
    filas = consultar(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
    )
    assert len(filas) == 13


def test_cinco_procedimientos():
    filas = consultar(
        "SELECT ROUTINE_NAME FROM information_schema.ROUTINES "
        "WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'PROCEDURE'"
    )
    assert len(filas) == 5


def test_conteos_de_datos_de_prueba():
    for tabla, esperado in CONTEOS_ESPERADOS.items():
        filas = consultar(f"SELECT COUNT(*) AS total FROM `{tabla}`")
        assert filas[0]["total"] == esperado, f"{tabla} no coincide"


def test_listados_principales():
    assert len(estudiantes.listar_estudiantes()) == 10
    assert len(padres.listar_padres()) == 10
    assert len(instituciones.listar_instituciones()) == 4
    assert len(constancias.listar_constancias()) == 3


def test_buscar_estudiante_procedimiento():
    filas = consultar("SELECT ApellidoPaterno FROM ESTUDIANTE LIMIT 1")
    apellido = filas[0]["ApellidoPaterno"]
    encontrados = matriculas.buscar_estudiantes(apellido, "", "")
    assert encontrados
    assert any(apellido in f["ApellidoPaterno"] for f in encontrados)


def test_verificar_grado():
    filas = consultar("SELECT DNI FROM ESTUDIANTE LIMIT 1")
    resultado = matriculas.verificar_grado(filas[0]["DNI"], 2026)
    assert resultado["estado"] in ("Correcto", "Advertencia", "Error")
    assert resultado["dni"] == filas[0]["DNI"]


def test_verificar_matriculados():
    resultado = matriculas.verificar_matriculados(2025, 2026)
    assert set(resultado["resumen"]) == {
        "Total", "Continúa", "Sin matrícula en el año actual", "Nuevo"
    }
    assert resultado["resumen"]["Total"] == len(resultado["filas"])


def test_listar_hermanos():
    filas = consultar("SELECT DNI_HermanoA FROM HERMANDAD LIMIT 1")
    hermanos = matriculas.listar_hermanos(filas[0]["DNI_HermanoA"])
    assert hermanos


def test_constancia_con_logros():
    codigos = consultar("SELECT CodigoVirtual FROM CONSTANCIA_LOGROS LIMIT 1")
    constancia = constancias.obtener_constancia(codigos[0]["CodigoVirtual"])
    assert constancia is not None
    assert len(constancia["logros"]) >= 1
