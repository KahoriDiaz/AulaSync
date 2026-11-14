from datetime import date

import pytest

from core import seguridad
from core.config import config
from core.errores import ErrorPermiso, ErrorValidacion
from servicios import solicitudes


@pytest.fixture
def sesion_padre(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "_data_dir", str(tmp_path))
    seguridad.iniciar_sesion(
        seguridad.Sesion(
            id_usuario=7, nombre_usuario="padre1", rol="Padre",
            dni="70000002", nombres="Luis", apellidos="Quispe",
        )
    )
    yield
    seguridad.cerrar_sesion()


@pytest.fixture
def sesion_otro(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "_data_dir", str(tmp_path))
    seguridad.iniciar_sesion(
        seguridad.Sesion(
            id_usuario=8, nombre_usuario="padre2", rol="Padre",
            dni="70000003", nombres="Otro", apellidos="Padre",
        )
    )
    yield
    seguridad.cerrar_sesion()


def _datos_basicos():
    return {
        "estudiante": {"DNI": "70000001", "Nombres": "Ana Sofia"},
        "padre": {"DNI": "70000002", "Nombres": "Luis"},
        "contacto": {"NombreContactoEmergencia": "Rosa", "CelularEmergencia": "987654321"},
    }


def test_crear_borrador(sesion_padre):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°",
        "A", _datos_basicos(),
    )
    solicitud = solicitudes.obtener(id_solicitud)
    assert solicitud["estado"] == "Borrador"
    assert solicitud["tipo"] == "Nueva matrícula"
    assert solicitud["anio"] == 2026
    assert solicitud["datos"]["estudiante"]["Nombres"] == "Ana Sofia"
    assert solicitud["padre"]["id_usuario"] == 7


def test_actualizar_fusiona_datos(sesion_padre):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°", "A", _datos_basicos()
    )
    solicitud = solicitudes.actualizar(
        id_solicitud,
        {"estudiante": {"Nombres": "Ana Sofía"}, "lugar": "Cercado"},
        seccion="B",
    )
    assert solicitud["seccion"] == "B"
    assert solicitud["datos"]["estudiante"]["Nombres"] == "Ana Sofía"
    assert solicitud["datos"]["estudiante"]["DNI"] == "70000001"
    assert solicitud["datos"]["lugar"] == "Cercado"


def test_no_puede_ver_solicitud_ajena(sesion_padre, monkeypatch):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°", "A", _datos_basicos()
    )
    seguridad.iniciar_sesion(
        seguridad.Sesion(
            id_usuario=99, nombre_usuario="otro", rol="Padre",
            dni="70000099", nombres="Otro", apellidos="Usuario",
        )
    )
    with pytest.raises(ErrorPermiso):
        solicitudes.obtener(id_solicitud)


def test_validacion_bloquea_envio(sesion_padre, monkeypatch):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°", "A", _datos_basicos()
    )
    monkeypatch.setattr(
        "servicios.validaciones.validar_solicitud",
        lambda solicitud: {
            "items": [{"mensaje": "Falta DNI", "estado": "Error"}],
            "errores": 1, "advertencias": 0, "puede_enviar": False,
            "puede_aprobar": False, "fecha": "2026-01-01T00:00:00",
        },
    )
    with pytest.raises(ErrorValidacion):
        solicitudes.enviar(id_solicitud)
    assert solicitudes.obtener(id_solicitud)["estado"] == "Borrador"


def test_envio_correcto(sesion_padre, monkeypatch):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°", "A", _datos_basicos()
    )
    monkeypatch.setattr(
        "servicios.validaciones.validar_solicitud",
        lambda solicitud: {
            "items": [], "errores": 0, "advertencias": 0,
            "puede_enviar": True, "puede_aprobar": True,
            "fecha": "2026-01-01T00:00:00",
        },
    )
    solicitud = solicitudes.enviar(id_solicitud)
    assert solicitud["estado"] == "Enviada"
    assert solicitud["fecha_envio"]
    assert solicitud["historial"][-1]["accion"] == "Envío de la solicitud"


def test_no_editar_enviada(sesion_padre, monkeypatch):
    id_solicitud = solicitudes.crear_borrador(
        "Nueva matrícula", "70000001", 2026, "Primaria", "1.°", "A", _datos_basicos()
    )
    monkeypatch.setattr(
        "servicios.validaciones.validar_solicitud",
        lambda solicitud: {
            "items": [], "errores": 0, "advertencias": 0,
            "puede_enviar": True, "puede_aprobar": True,
            "fecha": "2026-01-01T00:00:00",
        },
    )
    solicitudes.enviar(id_solicitud)
    with pytest.raises(ErrorValidacion):
        solicitudes.actualizar(id_solicitud, {"lugar": "Arequipa"})
