"""Pruebas del módulo OCR: normalización y extractores (sin Tesseract)."""
from ocr import normalizacion as nz
from ocr.constancia import extraer_constancia
from ocr.dni import extraer_dni

LINEAS_DNI = [
    ("DOCUMENTO NACIONAL DE IDENTIDAD", 92),
    ("DNI 70000001", 94),
    ("APELLIDO PATERNO", 90),
    ("QUISPE", 93),
    ("APELLIDO MATERNO", 90),
    ("MAMANI", 92),
    ("PRENOMBRES", 90),
    ("ANA SOFIA", 91),
    ("FECHA DE NACIMIENTO", 90),
    ("15/03/2014", 89),
    ("SEXO", 90),
    ("F", 90),
    ("DOMICILIO", 88),
    ("AV. LOS ANDES 123", 88),
    ("DISTRITO", 85),
    ("CERCADO", 85),
    ("DISTRITO DE NACIMIENTO", 84),
    ("CERCADO", 84),
    ("PROVINCIA DE NACIMIENTO", 84),
    ("AREQUIPA", 84),
    ("DEPARTAMENTO DE NACIMIENTO", 84),
    ("AREQUIPA", 84),
]

LINEAS_CONSTANCIA = [
    ("CONSTANCIA DE LOGROS DE APRENDIZAJE", 90),
    ("CODIGO VIRTUAL", 90),
    ("D4E5F6A7", 92),
    ("DNI 70000001", 94),
    ("NIVEL PRIMARIA", 90),
    ("FECHA DE EMISION 15/12/2025 10:30:00", 90),
    ("CODIGO MODULAR 1137421-0", 90),
    ("INSTITUCION EDUCATIVA L.E. 40174 EJEMPLO", 88),
    ("TIPO ESTATAL", 86),
    ("2022 PRIMER GRADO APROBADO", 85),
    ("2023 SEGUNDO GRADO APROBADO", 85),
    ("2024 TERCER GRADO APROBADO", 85),
    ("2025 CUARTO GRADO REQUIERE RECUPERACION", 85),
]


def test_normalizar_dni():
    assert nz.normalizar_dni("70-000.001") == "70000001"
    assert nz.normalizar_dni("123") is None


def test_normalizar_fecha():
    assert nz.normalizar_fecha("15/03/2014") == "2014-03-15"
    assert nz.normalizar_fecha("2014-03-15") == "2014-03-15"
    assert nz.normalizar_fecha("no es fecha") is None


def test_normalizar_fecha_hora():
    assert nz.normalizar_fecha_hora("15/12/2025 10:30:00") == "2025-12-15 10:30:00"
    assert nz.normalizar_fecha_hora("15/12/2025") == "2025-12-15 00:00:00"


def test_normalizar_sexo():
    assert nz.normalizar_sexo("F") == "F"
    assert nz.normalizar_sexo("Masculino") == "M"
    assert nz.normalizar_sexo("x") is None


def test_normalizar_nivel_y_grado():
    assert nz.normalizar_nivel("NIVEL PRIMARIA") == "Primaria"
    assert nz.normalizar_grado("TERCER GRADO") == "3.°"
    assert nz.normalizar_grado("4") == "4.°"
    assert nz.normalizar_grado("sin grado") is None


def test_normalizar_situacion():
    assert nz.normalizar_situacion("APROBADO") == "APROBADO"
    assert nz.normalizar_situacion("REQUIERE RECUPERACIÓN") == "REQUIERE RECUPERACIÓN"


def test_normalizar_codigos():
    assert nz.normalizar_codigo_virtual("d4e5-f6a7") == "D4E5F6A7"
    assert nz.normalizar_codigo_virtual("123") is None
    assert nz.normalizar_codigo_modular("1137421-0") == "1137421-0"


def test_normalizar_tipo_ie():
    assert nz.normalizar_tipo_ie("TIPO ESTATAL") == "Estatal"
    assert nz.normalizar_tipo_ie("Institución privada") == "Particular"


def test_extraer_dni():
    campos = extraer_dni(LINEAS_DNI, tabla="ESTUDIANTE")
    assert campos["ESTUDIANTE.DNI"][0] == "70000001"
    assert campos["ESTUDIANTE.DNI"][1] == 94
    assert campos["ESTUDIANTE.ApellidoPaterno"][0] == "Quispe"
    assert campos["ESTUDIANTE.ApellidoMaterno"][0] == "Mamani"
    assert campos["ESTUDIANTE.Nombres"][0] == "Ana Sofia"
    assert campos["ESTUDIANTE.FechaNacimiento"][0] == "2014-03-15"
    assert campos["ESTUDIANTE.Sexo"][0] == "F"
    assert campos["ESTUDIANTE.DistritoDomicilio"][0] == "Cercado"
    assert campos["ESTUDIANTE.DistritoNacimiento"][0] == "Cercado"
    assert campos["ESTUDIANTE.ProvinciaNacimiento"][0] == "Arequipa"


def test_extraer_dni_tabla_padre():
    campos = extraer_dni(LINEAS_DNI, tabla="PADRE_APODERADO")
    assert "PADRE_APODERADO.DNI" in campos
    assert "ESTUDIANTE.DistritoNacimiento" not in campos


def test_extraer_dni_sin_etiqueta_usa_regex():
    campos = extraer_dni([("El documento 70000042 pertenece al titular", 80)])
    assert campos["ESTUDIANTE.DNI"][0] == "70000042"


LINEAS_DNI_MRZ = [
    ("I<PER71347545<2<<<<<CCECLL<<<", 21),
    ("0602149FF1404177PER<<<<<<<<<<<2", 53),
    ("BUSTAMANTE<<ANA<PAULA<<<<<<<<<", 83),
]


def test_extraer_dni_mrz():
    campos = extraer_dni(LINEAS_DNI_MRZ, tabla="ESTUDIANTE")
    assert campos["ESTUDIANTE.DNI"][0] == "71347545"
    assert campos["ESTUDIANTE.ApellidoPaterno"][0] == "Bustamante"
    assert campos["ESTUDIANTE.Nombres"][0] == "Ana Paula"
    assert campos["ESTUDIANTE.FechaNacimiento"][0] == "2006-02-14"
    assert campos["ESTUDIANTE.Sexo"][0] == "F"


def test_extraer_constancia_campos():
    campos, _ = extraer_constancia(LINEAS_CONSTANCIA)
    assert campos["CONSTANCIA_LOGROS.CodigoVirtual"][0] == "D4E5F6A7"
    assert campos["CONSTANCIA_LOGROS.DNI_Estudiante"][0] == "70000001"
    assert campos["CONSTANCIA_LOGROS.NivelEducativo"][0] == "Primaria"
    assert campos["CONSTANCIA_LOGROS.FechaHoraEmision"][0] == "2025-12-15 10:30:00"
    assert campos["INSTITUCION_EDUCATIVA.CodigoModularIE"][0] == "1137421-0"
    assert campos["INSTITUCION_EDUCATIVA.TipoIE"][0] == "Estatal"


def test_extraer_constancia_logros():
    _, logros = extraer_constancia(LINEAS_CONSTANCIA)
    anios = [logro["LOGRO.AñoEscolar"][0] for logro in logros]
    assert anios == ["2022", "2023", "2024", "2025"]
    assert logros[0]["LOGRO.GradoCursado"][0] == "1.°"
    assert logros[0]["LOGRO.SituacionFinal"][0] == "APROBADO"
    assert logros[3]["LOGRO.SituacionFinal"][0] == "REQUIERE RECUPERACIÓN"
    assert all(logro["LOGRO.CodigoModularIE"][0] == "1137421-0" for logro in logros)
