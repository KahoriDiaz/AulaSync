"""Pruebas de normalización y validación de los servicios de datos (sin BD)."""
import pytest

from core.errores import ErrorValidacion
from servicios import constancias, estudiantes, padres


def _padre_valido():
    return {
        "DNI": "70000008", "Sexo": "M", "Nombres": "luis alberto",
        "ApellidoPaterno": "quispe", "ApellidoMaterno": "mamani",
        "FechaNacimiento": "1985-01-01", "OcupacionActual": "Comerciante",
        "GradoInstruccion": "Secundaria", "DomicilioActual": "Av. Los Andes 123",
        "DistritoDomicilio": "Cercado", "TelefonoFijo": "054234567",
        "Celular": "987654321", "CorreoElectronico": "luis@correo.com",
    }


def _estudiante_valido():
    return {
        "DNI": "70000009", "Sexo": "F", "Nombres": "ana sofia",
        "ApellidoPaterno": "quispe", "ApellidoMaterno": "mamani",
        "FechaNacimiento": "2019-06-01", "DistritoNacimiento": "Cercado",
        "ProvinciaNacimiento": "Arequipa", "DepartamentoNacimiento": "Arequipa",
        "PaisNacimiento": "Perú", "DomicilioActual": "Av. Los Andes 123",
        "DistritoDomicilio": "Cercado", "Celular": "987654322",
        "CorreoElectronico": "ana@correo.com", "Religion": "Católica",
        "LugarQueOcupa": 1, "TipoAtencion": "SIS",
        "EnfermedadCronica": "Asma", "ViveConPadre": True, "ViveConMadre": True,
        "ElPadreVive": True, "LaMadreVive": True, "IdContactoEmergencia": 3,
        "CodigoModularIE": "1137421-0", "DNI_Apoderado": "70000008",
    }


# --------------------------------------------------------------- padres
def test_padres_normaliza_campos():
    valores = padres.normalizar(_padre_valido())
    assert valores["DNI"] == "70000008"
    assert valores["Nombres"] == "Luis Alberto"
    assert valores["ApellidoPaterno"] == "Quispe"
    assert valores["Sexo"] == "M"
    assert valores["FechaNacimiento"] == "1985-01-01"
    assert valores["Celular"] == "987654321"


def test_padres_celular_invalido():
    datos = _padre_valido()
    datos["Celular"] = "123"
    with pytest.raises(ErrorValidacion):
        padres.normalizar(datos)


def test_padres_grado_instruccion_invalido():
    datos = _padre_valido()
    datos["GradoInstruccion"] = "Doctorado"
    with pytest.raises(ErrorValidacion):
        padres.normalizar(datos)


# ----------------------------------------------------------- estudiantes
def test_estudiantes_normaliza_campos():
    valores = estudiantes.normalizar(_estudiante_valido())
    assert valores["Nombres"] == "Ana Sofia"
    assert valores["Sexo"] == "F"
    assert valores["IdContactoEmergencia"] == 3
    assert valores["TipoAtencion"] == "SIS"
    assert valores["ViveConPadre"] is True
    assert valores["PaisNacimiento"] == "Perú"


def test_estudiantes_sin_contacto():
    datos = _estudiante_valido()
    datos["IdContactoEmergencia"] = None
    with pytest.raises(ErrorValidacion):
        estudiantes.normalizar(datos)


def test_estudiantes_lugar_ocupacion_no_numerico():
    datos = _estudiante_valido()
    datos["LugarQueOcupa"] = "abc"
    with pytest.raises(ErrorValidacion):
        estudiantes.normalizar(datos)


def test_estudiantes_lugar_ocupacion_vacio_usa_uno():
    datos = _estudiante_valido()
    datos["LugarQueOcupa"] = 0
    assert estudiantes.normalizar(datos)["LugarQueOcupa"] == 1


def test_estudiantes_fecha_futura():
    datos = _estudiante_valido()
    datos["FechaNacimiento"] = "2999-01-01"
    with pytest.raises(ErrorValidacion):
        estudiantes.normalizar(datos)


# ------------------------------------------------------------ constancias
def _logros_validos():
    return [
        {"AñoEscolar": 2024, "GradoCursado": "TERCER GRADO",
         "CodigoModularIE": "1137421-0", "SituacionFinal": "APROBADO"},
        {"AñoEscolar": 2025, "GradoCursado": "4",
         "CodigoModularIE": "1137421-0", "SituacionFinal": "REQUIERE RECUPERACIÓN"},
    ]


def test_constancia_normaliza():
    valores = constancias.normalizar_constancia(
        {"CodigoVirtual": "d4e5f6a7", "DNI_Estudiante": "70000009",
         "NivelEducativo": "primaria", "FechaHoraEmision": "15/12/2025 10:30:00"}
    )
    assert valores["CodigoVirtual"] == "D4E5F6A7"
    assert valores["NivelEducativo"] == "Primaria"
    assert valores["FechaHoraEmision"] == "2025-12-15 10:30:00"


def test_constancia_codigo_invalido():
    with pytest.raises(ErrorValidacion):
        constancias.normalizar_constancia(
            {"CodigoVirtual": "ABC", "DNI_Estudiante": "70000009",
             "NivelEducativo": "Primaria"}
        )


def test_logros_normaliza_grado_y_situacion():
    logros = constancias.normalizar_logros("Primaria", _logros_validos())
    assert logros[0]["GradoCursado"] == "3.°"
    assert logros[1]["GradoCursado"] == "4.°"
    assert logros[1]["SituacionFinal"] == "REQUIERE RECUPERACIÓN"


def test_logros_anio_duplicado():
    logros = _logros_validos()
    logros[1]["AñoEscolar"] = 2024
    with pytest.raises(ErrorValidacion):
        constancias.normalizar_logros("Primaria", logros)


def test_logros_sin_institucion():
    logros = _logros_validos()
    logros[0]["CodigoModularIE"] = ""
    with pytest.raises(ErrorValidacion):
        constancias.normalizar_logros("Primaria", logros)


def test_logros_vacios():
    with pytest.raises(ErrorValidacion):
        constancias.normalizar_logros("Primaria", [])
