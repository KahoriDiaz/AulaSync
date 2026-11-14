import pytest

from core.almacen import Almacen
from core.config import config
from servicios import validaciones

PNG = b"\x89PNG\r\n\x1a\n" + b"contenido"


def _datos():
    return {
        "estudiante": {
            "DNI": "70000009", "Sexo": "F", "Nombres": "Ana Sofia",
            "ApellidoPaterno": "Quispe", "ApellidoMaterno": "Mamani",
            "FechaNacimiento": "2019-06-01", "DistritoNacimiento": "Cercado",
            "ProvinciaNacimiento": "Arequipa", "DepartamentoNacimiento": "Arequipa",
            "PaisNacimiento": "Perú", "DomicilioActual": "Av. Los Andes 123",
            "DistritoDomicilio": "Cercado", "LugarQueOcupa": 1,
            "ViveConPadre": True, "ViveConMadre": True,
            "ElPadreVive": True, "LaMadreVive": True,
        },
        "padre": {
            "DNI": "70000008", "Sexo": "M", "Nombres": "Luis",
            "ApellidoPaterno": "Quispe", "ApellidoMaterno": "Mamani",
            "FechaNacimiento": "1985-01-01", "GradoInstruccion": "Secundaria",
            "DomicilioActual": "Av. Los Andes 123", "DistritoDomicilio": "Cercado",
            "Celular": "987654321",
        },
        "contacto": {
            "NombreContactoEmergencia": "Rosa Mamani", "CelularEmergencia": "987654322",
        },
        "constancia": {
            "CodigoVirtual": "ABCD1234", "NivelEducativo": "Primaria",
            "logros": [{
                "AñoEscolar": 2025, "GradoCursado": "1.°",
                "CodigoModularIE": "1234567-8", "SituacionFinal": "APROBADO",
            }],
        },
    }


@pytest.fixture
def solicitud_valida(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "_data_dir", str(tmp_path))
    almacen = Almacen(tmp_path)
    id_solicitud = almacen.crear({
        "padre": {"id_usuario": 1}, "anio": 2026, "nivel": "Primaria",
        "grado": "2.°", "datos": _datos(),
    })
    solicitud = almacen.cargar(id_solicitud)
    solicitud["seccion"] = "A"
    for indice, tipo in enumerate(validaciones.DOCUMENTOS_OBLIGATORIOS, start=1):
        origen = tmp_path / f"documento_{indice}.png"
        origen.write_bytes(PNG + bytes([indice]))
        almacen.agregar_documento(id_solicitud, origen, tipo)
    solicitud = almacen.cargar(id_solicitud)
    solicitud["seccion"] = "A"
    return solicitud


def test_solicitud_completa(monkeypatch, solicitud_valida):
    monkeypatch.setattr(validaciones, "consultar_uno", lambda *a, **k: None)
    monkeypatch.setattr(validaciones, "consultar", lambda *a, **k: [])
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is True
    assert resultado["errores"] == 0
    assert any(item["mensaje"].startswith("Le corresponde") for item in resultado["items"])


def test_documentos_faltantes(monkeypatch, solicitud_valida):
    monkeypatch.setattr(validaciones, "consultar_uno", lambda *a, **k: None)
    solicitud_valida["documentos"] = []
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is False
    assert resultado["errores"] >= 3


def test_grado_incorrecto_es_advertencia(monkeypatch, solicitud_valida):
    monkeypatch.setattr(validaciones, "consultar_uno", lambda *a, **k: None)
    solicitud_valida["grado"] = "1.°"
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is True
    assert any(item["campo"] == "Grado" and item["estado"] == "Advertencia" for item in resultado["items"])


def test_edad_inicial(monkeypatch, solicitud_valida):
    monkeypatch.setattr(validaciones, "consultar_uno", lambda *a, **k: None)
    solicitud_valida["nivel"] = "Inicial"
    solicitud_valida["grado"] = "3 a."
    solicitud_valida["datos"]["estudiante"]["FechaNacimiento"] = "2023-01-01"
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is True
    assert any("Inicial 3 a." in item["mensaje"] for item in resultado["items"])


def test_confianza_baja(monkeypatch, solicitud_valida):
    monkeypatch.setattr(validaciones, "consultar_uno", lambda *a, **k: None)
    solicitud_valida["datos"]["ocr_confianzas"] = {"ApellidoMaterno": 55}
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is True
    assert any(item["seccion"] == "OCR" for item in resultado["items"])


def test_constancia_duplicada_es_error(monkeypatch, solicitud_valida):
    monkeypatch.setattr(
        validaciones, "consultar_uno",
        lambda sql, params=(): {"DNI_Estudiante": "70000077"} if "CONSTANCIA_LOGROS" in sql else None,
    )
    resultado = validaciones.validar_solicitud(solicitud_valida)
    assert resultado["puede_enviar"] is False
