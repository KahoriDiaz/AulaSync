import pytest

from core.almacen import Almacen
from core.errores import ErrorValidacion

PNG = b"\x89PNG\r\n\x1a\n" + b"datos"


def _archivo(tmp_path, nombre, contenido=PNG):
    ruta = tmp_path / nombre
    ruta.write_bytes(contenido)
    return ruta


def test_crear_y_cargar_solicitud(tmp_path):
    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({"padre": {"id_usuario": 1}, "anio": 2026})
    assert id_solicitud.startswith("SOL-")
    solicitud = almacen.cargar(id_solicitud)
    assert solicitud["estado"] == "Borrador"
    assert solicitud["version"] == 1
    assert solicitud["historial"][0]["accion"] == "Creación de la solicitud"


def test_ids_correlativos(tmp_path):
    almacen = Almacen(tmp_path)
    primero = almacen.crear({})
    segundo = almacen.crear({})
    assert int(segundo[-4:]) == int(primero[-4:]) + 1


def test_control_de_version(tmp_path):
    from core.errores import ErrorConflicto

    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({})
    solicitud = almacen.cargar(id_solicitud)
    almacen.guardar(solicitud, version_esperada=1)
    with pytest.raises(ErrorConflicto):
        almacen.guardar(solicitud, version_esperada=1)


def test_agregar_documento(tmp_path):
    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({})
    origen = _archivo(tmp_path, "dni.png")
    registro, solicitud = almacen.agregar_documento(id_solicitud, origen, "DNI estudiante")
    assert registro["mime"] == "image/png"
    assert solicitud["documentos"][0]["tipo"] == "DNI estudiante"
    assert almacen.ruta_documento(id_solicitud, registro).is_file()


def test_rechaza_documento_repetido(tmp_path):
    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({})
    origen = _archivo(tmp_path, "dni.png")
    almacen.agregar_documento(id_solicitud, origen, "DNI estudiante")
    with pytest.raises(ErrorValidacion):
        almacen.agregar_documento(id_solicitud, origen, "Otro")


def test_rechaza_pdf_falso(tmp_path):
    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({})
    falso = _archivo(tmp_path, "falso.pdf", b"no es un pdf")
    with pytest.raises(ErrorValidacion):
        almacen.agregar_documento(id_solicitud, falso, "Constancia de logros")


def test_id_invalido(tmp_path):
    almacen = Almacen(tmp_path)
    with pytest.raises(ErrorValidacion):
        almacen.ruta("../../etc")
