"""Realizar matrícula: guardado de datos y registro de la matrícula (§6.3.3).

Todas las escrituras se hacen con ``CALL sp_...``; Python solo ejecuta
``SELECT`` para decidir si llama al procedimiento de insertar o de actualizar.
``guardar_datos`` ejecuta, en **una sola** transacción y en el orden que exigen
las claves foráneas:

    padre / madre -> instituciones educativas -> estudiante (crea su contacto)
    -> tiene_padres -> constancia de logros -> logros

``registrar_matricula`` llama a ``sp_registrar_matricula``, que valida el cupo
(30 por sección), la matrícula duplicada y el responsable.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from app import db
from app.errores import ErrorValidacion

NIVELES: dict[str, tuple[str, ...]] = {
    "Inicial": ("3 a.", "4 a.", "5 a."),
    "Primaria": ("1.°", "2.°", "3.°", "4.°", "5.°", "6.°"),
    "Secundaria": ("1.°", "2.°", "3.°", "4.°", "5.°"),
}
SECCIONES: dict[str, tuple[str, ...]] = {
    "Inicial": ("A", "B"),
    "Primaria": ("A", "B", "C"),
    "Secundaria": ("A", "B", "C", "D"),
}
SITUACIONES_FINALES = ("APROBADO", "REQUIERE RECUPERACIÓN")
CAPACIDAD = 30
LUGAR_SUSCRIPCION = "Virtual"

CAMPOS_PADRE = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno",
    "FechaNacimiento", "OcupacionActual", "GradoInstruccion", "DomicilioActual",
    "DistritoDomicilio", "TelefonoFijo", "Celular", "CorreoElectronico",
)
CAMPOS_ESTUDIANTE = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno",
    "FechaNacimiento", "DistritoNacimiento", "ProvinciaNacimiento",
    "DepartamentoNacimiento", "PaisNacimiento", "DomicilioActual",
    "DistritoDomicilio", "Celular", "CorreoElectronico", "Religion",
    "LugarQueOcupa", "TipoAtencion", "EnfermedadCronica", "ViveConPadre",
    "ViveConMadre", "ElPadreVive", "LaMadreVive",
)
BOOLEANOS = ("ViveConPadre", "ViveConMadre", "ElPadreVive", "LaMadreVive")


# ------------------------------------------------------------ lecturas / BD
def _uno(cursor, sql: str, parametros: Sequence[Any] = ()) -> dict[str, Any] | None:
    cursor.execute(sql, tuple(parametros))
    fila = cursor.fetchone()
    cursor.fetchall()  # consume cualquier fila restante antes del siguiente execute
    return dict(fila) if fila else None


def _llamar(cursor, nombre: str, parametros: Sequence[Any] = ()) -> None:
    """Ejecuta un procedimiento dentro de la transacción y consume sus filas."""
    marcadores = ", ".join(["%s"] * len(parametros))
    cursor.execute(f"CALL `{nombre}`({marcadores})", tuple(parametros))
    while True:
        if cursor.with_rows:
            cursor.fetchall()
        if not cursor.nextset():
            break


def _vacio_a_none(valor: Any) -> Any:
    """Los campos opcionales vacíos se envían como NULL a los procedimientos."""
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _booleano(valor: Any) -> int:
    return 1 if valor in (True, 1, "1", "Sí", "Si", "sí", "si") else 0


def grado_siguiente(nivel: str, grado: str, situacion: str) -> str:
    """Calcula el grado que corresponde usando ``fn_grado_siguiente``."""
    fila = db.query_uno(
        "SELECT fn_grado_siguiente(%s, %s, %s) AS grado", (nivel, grado, situacion)
    )
    return str(fila["grado"]) if fila else ""


def nivel_de_grado_siguiente(nivel: str, grado: str, siguiente: str) -> str:
    """Infiere el nivel del grado calculado (``fn_grado_siguiente`` da solo el grado)."""
    if siguiente == "EGRESADO":
        return ""
    if nivel == "Inicial" and grado == "5 a.":
        return "Primaria"
    if nivel == "Primaria" and grado == "6.°":
        return "Secundaria"
    return nivel


def grado_que_corresponde(
    nivel_ultimo: str, grado_ultimo: str, situacion: str
) -> tuple[str, str]:
    """Devuelve ``(nivel, grado)`` que corresponde según el último logro."""
    siguiente = grado_siguiente(nivel_ultimo, grado_ultimo, situacion)
    return nivel_de_grado_siguiente(nivel_ultimo, grado_ultimo, siguiente), siguiente


def cupos_seccion(anio: int, nivel: str, grado: str, seccion: str) -> dict[str, Any]:
    """Devuelve matriculados y vacantes de una sección (30 por sección)."""
    conjuntos = db.call_proc("sp_cupos_seccion", (anio, nivel, grado, seccion))
    fila = conjuntos[0][0] if conjuntos and conjuntos[0] else {}
    matriculados = int(fila.get("Matriculados") or 0)
    vacantes = fila.get("Vacantes")
    return {
        "Matriculados": matriculados,
        # Una sección llena tiene 0 vacantes: no usar "or", que lo cambiaría a 30.
        "Vacantes": int(vacantes) if vacantes is not None else max(0, CAPACIDAD - matriculados),
    }


def verificar_cupos(anio: int, nivel: str, grado: str) -> list[dict[str, Any]]:
    """Cupos de todas las secciones posibles para el nivel indicado."""
    return [
        {"seccion": seccion, **cupos_seccion(anio, nivel, grado, seccion)}
        for seccion in SECCIONES.get(nivel, ())
    ]


# ------------------------------------------------------------ guardar datos
def _parametros_padre(padre: dict[str, Any]) -> tuple:
    return tuple(_vacio_a_none(padre.get(campo)) for campo in CAMPOS_PADRE)


def _parametros_estudiante(estudiante: dict[str, Any]) -> tuple:
    valores: list[Any] = []
    for campo in CAMPOS_ESTUDIANTE:
        valor = estudiante.get(campo)
        if campo in BOOLEANOS:
            valores.append(_booleano(valor))
        elif campo == "LugarQueOcupa":
            valores.append(int(valor or 1))
        else:
            valores.append(_vacio_a_none(valor))
    return tuple(valores)


def _guardar_padre(cursor, padre: dict[str, Any]) -> str:
    dni = str(padre.get("DNI") or "").strip()
    existe = _uno(cursor, "SELECT DNI FROM PADRE_APODERADO WHERE DNI = %s", (dni,))
    _llamar(
        cursor, "sp_padre_actualizar" if existe else "sp_padre_insertar",
        _parametros_padre(padre),
    )
    return dni


def _guardar_ie(cursor, codigo: Any, nombre: Any = "", tipo: Any = "") -> None:
    """Inserta la I.E. si no existe; si existe, solo completa datos nuevos."""
    codigo = str(codigo or "").strip()
    if not codigo:
        return
    existe = _uno(
        cursor,
        "SELECT CodigoModularIE, NombreIE, TipoIE FROM INSTITUCION_EDUCATIVA "
        "WHERE CodigoModularIE = %s",
        (codigo,),
    )
    nombre = _vacio_a_none(nombre)
    tipo = _vacio_a_none(tipo)
    if existe is None:
        _llamar(cursor, "sp_ie_insertar", (codigo, nombre, tipo))
    elif (nombre and nombre != existe.get("NombreIE")) or (tipo and tipo != existe.get("TipoIE")):
        _llamar(cursor, "sp_ie_actualizar", (
            codigo, nombre or existe.get("NombreIE"), tipo or existe.get("TipoIE"),
        ))


def _guardar_estudiante(
    cursor, estudiante: dict[str, Any], codigo_ie: str | None, dni_apoderado: str | None
) -> None:
    dni = str(estudiante.get("DNI") or "").strip()
    existe = _uno(
        cursor, "SELECT IdContactoEmergencia FROM ESTUDIANTE WHERE DNI = %s", (dni,)
    )
    nombre_contacto = _vacio_a_none(estudiante.get("NombreContactoEmergencia"))
    celular_contacto = _vacio_a_none(estudiante.get("CelularEmergencia"))
    base = _parametros_estudiante(estudiante)
    if existe is None:
        _llamar(cursor, "sp_estudiante_insertar", base + (
            None, nombre_contacto, celular_contacto, codigo_ie, dni_apoderado,
        ))
        return
    id_contacto = existe["IdContactoEmergencia"]
    if nombre_contacto and celular_contacto:
        _llamar(cursor, "sp_contacto_actualizar", (id_contacto, nombre_contacto, celular_contacto))
    _llamar(cursor, "sp_estudiante_actualizar", base + (id_contacto, codigo_ie, dni_apoderado))


def _guardar_constancia(
    cursor, dni: str, constancia: dict[str, Any], logros: list[dict[str, Any]]
) -> None:
    codigo = str(constancia.get("CodigoVirtual") or "").strip().upper()
    if not codigo:
        return
    parametros = (
        codigo, dni, constancia.get("NivelEducativo"),
        _vacio_a_none(constancia.get("FechaHoraEmision")),
    )
    existe = _uno(
        cursor, "SELECT CodigoVirtual FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s",
        (codigo,),
    )
    _llamar(
        cursor, "sp_constancia_actualizar" if existe else "sp_constancia_insertar",
        parametros,
    )
    for logro in logros:
        anio = int(logro["AñoEscolar"])
        existe_logro = _uno(
            cursor,
            "SELECT 1 AS existe FROM LOGRO WHERE CodigoVirtual = %s AND `AñoEscolar` = %s",
            (codigo, anio),
        )
        _llamar(
            cursor, "sp_logro_actualizar" if existe_logro else "sp_logro_insertar",
            (codigo, anio, logro.get("GradoCursado"),
             str(logro.get("CodigoModularIE") or "").strip(), logro.get("SituacionFinal")),
        )


def _digitos(valor: Any, cantidad: int) -> bool:
    texto = str(valor or "")
    return texto.isdigit() and len(texto) == cantidad


def _fecha(valor: Any) -> date | None:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor or "")[:10])
    except ValueError:
        return None


def edad(nacimiento: date, hoy: date | None = None) -> int:
    hoy = hoy or date.today()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def validar_estudiante(estudiante: dict[str, Any], nuevo: bool = True) -> list[str]:
    """Mismas reglas que el formulario de estudiante."""
    errores: list[str] = []
    obligatorios = [
        ("DNI", "DNI"), ("Sexo", "sexo"), ("Nombres", "nombres"),
        ("ApellidoPaterno", "apellido paterno"), ("ApellidoMaterno", "apellido materno"),
        ("FechaNacimiento", "fecha de nacimiento"), ("DistritoNacimiento", "distrito de nacimiento"),
        ("ProvinciaNacimiento", "provincia de nacimiento"),
        ("DepartamentoNacimiento", "departamento de nacimiento"),
        ("PaisNacimiento", "país de nacimiento"), ("DomicilioActual", "domicilio actual"),
        ("DistritoDomicilio", "distrito de domicilio"),
    ]
    if nuevo:
        obligatorios += [
            ("NombreContactoEmergencia", "nombre del contacto de emergencia"),
            ("CelularEmergencia", "celular del contacto de emergencia"),
        ]
    for campo, texto in obligatorios:
        if not str(estudiante.get(campo) or "").strip():
            errores.append(f"Estudiante: falta el {texto}.")
    if estudiante.get("DNI") and not _digitos(estudiante["DNI"], 8):
        errores.append("Estudiante: el DNI debe tener 8 dígitos.")
    if estudiante.get("Sexo") and estudiante["Sexo"] not in ("M", "F"):
        errores.append("Estudiante: el sexo debe ser M o F.")
    nacimiento = _fecha(estudiante.get("FechaNacimiento"))
    if estudiante.get("FechaNacimiento") and (nacimiento is None or nacimiento > date.today()):
        errores.append("Estudiante: la fecha de nacimiento no es válida.")
    for campo, texto in (("Celular", "celular"), ("CelularEmergencia", "celular de emergencia")):
        if estudiante.get(campo) and not _digitos(estudiante[campo], 9):
            errores.append(f"Estudiante: el {texto} debe tener 9 dígitos.")
    try:
        lugar = int(estudiante.get("LugarQueOcupa") or 1)
        if not 1 <= lugar <= 255:
            raise ValueError
    except (TypeError, ValueError):
        errores.append("Estudiante: el lugar que ocupa debe ser un número entre 1 y 255.")
    tipo = estudiante.get("TipoAtencion")
    if tipo and tipo not in ("ESSALUD", "SIS", "Otros"):
        errores.append("Estudiante: tipo de atención no válido.")
    return errores


def validar_padre(padre: dict[str, Any], nombre: str = "Padre") -> list[str]:
    """Mismas reglas que el formulario de padre/apoderado (mayor de 18 años)."""
    errores: list[str] = []
    for campo, texto in (
        ("DNI", "DNI"), ("Sexo", "sexo"), ("Nombres", "nombres"),
        ("ApellidoPaterno", "apellido paterno"), ("ApellidoMaterno", "apellido materno"),
        ("FechaNacimiento", "fecha de nacimiento"), ("GradoInstruccion", "grado de instrucción"),
        ("DomicilioActual", "domicilio actual"), ("DistritoDomicilio", "distrito de domicilio"),
        ("Celular", "celular"),
    ):
        if not str(padre.get(campo) or "").strip():
            errores.append(f"{nombre}: falta el {texto}.")
    if padre.get("DNI") and not _digitos(padre["DNI"], 8):
        errores.append(f"{nombre}: el DNI debe tener 8 dígitos.")
    if padre.get("Celular") and not _digitos(padre["Celular"], 9):
        errores.append(f"{nombre}: el celular debe tener 9 dígitos.")
    if padre.get("TelefonoFijo") and not _digitos(padre["TelefonoFijo"], 9):
        errores.append(f"{nombre}: el teléfono fijo debe tener 9 dígitos.")
    if padre.get("GradoInstruccion") and padre["GradoInstruccion"] not in (
        "Primaria", "Secundaria", "Superior", "Otros"
    ):
        errores.append(f"{nombre}: grado de instrucción no válido.")
    nacimiento = _fecha(padre.get("FechaNacimiento"))
    if padre.get("FechaNacimiento"):
        if nacimiento is None:
            errores.append(f"{nombre}: la fecha de nacimiento no es válida.")
        elif edad(nacimiento) < 18:
            errores.append(f"{nombre}: debe tener 18 años o más.")
    correo = str(padre.get("CorreoElectronico") or "").strip()
    if correo and "@" not in correo:
        errores.append(f"{nombre}: el correo electrónico no es válido.")
    return errores


def validar_datos(datos: dict[str, Any]) -> list[str]:
    """Reglas antes de llamar a los procedimientos (los triggers validan el resto)."""
    estudiante = datos.get("estudiante") or {}
    errores: list[str] = validar_estudiante(estudiante, nuevo=not datos.get("estudiante_existe"))
    dni = str(estudiante.get("DNI") or "")
    for clave, nombre in (("padre", "Padre"), ("madre", "Madre")):
        if datos.get(clave):
            errores.extend(validar_padre(datos[clave], nombre))
    padres = [p for p in (datos.get("padre"), datos.get("madre")) if p]
    if not padres:
        errores.append("Registre al menos al padre o a la madre.")
    dnis_padres = {str(p.get("DNI") or "") for p in padres}
    if str(datos.get("responsable") or "") not in dnis_padres:
        errores.append("El responsable de la matrícula debe ser el padre o la madre registrados.")
    if dni and dni in dnis_padres:
        errores.append("El DNI del estudiante no puede ser el de su padre o madre.")
    constancia = datos.get("constancia") or {}
    if constancia.get("CodigoVirtual"):
        for logro in datos.get("logros") or []:
            if not str(logro.get("CodigoModularIE") or "").strip():
                errores.append(
                    f"El logro {logro.get('AñoEscolar')} necesita el código modular de la I.E."
                )
            if logro.get("SituacionFinal") not in SITUACIONES_FINALES:
                errores.append(
                    f"El logro {logro.get('AñoEscolar')} tiene una situación final no válida."
                )
    return errores


def guardar_datos(datos: dict[str, Any]) -> None:
    """Inserta o actualiza todos los datos del estudiante en una sola transacción.

    ``datos`` contiene: ``estudiante`` (columnas de ESTUDIANTE más
    NombreContactoEmergencia y CelularEmergencia), ``padre`` y ``madre``
    (columnas de PADRE_APODERADO o None), ``responsable`` (DNI), ``ie``
    (procedencia: CodigoModularIE, NombreIE, TipoIE), ``constancia``
    (CodigoVirtual, NivelEducativo, FechaHoraEmision) y ``logros`` (lista con
    AñoEscolar, GradoCursado, CodigoModularIE, NombreIE, SituacionFinal).
    Ante cualquier error del procedimiento o trigger se hace ROLLBACK.
    """
    errores = validar_datos(datos)
    if errores:
        raise ErrorValidacion("Revise los datos:\n- " + "\n- ".join(errores))
    estudiante = datos["estudiante"]
    dni = str(estudiante["DNI"]).strip()
    ie = datos.get("ie") or {}
    logros = list(datos.get("logros") or [])
    responsable = str(datos.get("responsable") or "").strip() or None

    with db.transaccion() as cursor:
        # 1. Padre y madre (antes que ESTUDIANTE por la FK del apoderado).
        dnis_padres = [
            _guardar_padre(cursor, padre)
            for padre in (datos.get("padre"), datos.get("madre")) if padre
        ]
        # 2. Instituciones: la de procedencia y las de cada logro (FK de LOGRO).
        _guardar_ie(cursor, ie.get("CodigoModularIE"), ie.get("NombreIE"), ie.get("TipoIE"))
        for logro in logros:
            _guardar_ie(cursor, logro.get("CodigoModularIE"), logro.get("NombreIE"))
        codigo_ie = str(ie.get("CodigoModularIE") or "").strip() or None
        # 3. Estudiante (el procedimiento crea el contacto de emergencia).
        _guardar_estudiante(cursor, estudiante, codigo_ie, responsable)
        # 4. Relación con sus padres.
        for dni_padre in dnis_padres:
            relacion = _uno(
                cursor,
                "SELECT 1 AS existe FROM TIENE_PADRES WHERE DNI_Estudiante = %s AND DNI_Padre = %s",
                (dni, dni_padre),
            )
            if not relacion:
                _llamar(cursor, "sp_tiene_padres_insertar", (dni, dni_padre))
        # 5 y 6. Constancia de logros y sus logros.
        _guardar_constancia(cursor, dni, datos.get("constancia") or {}, logros)


# ------------------------------------------------------------ matrícula
def registrar_matricula(
    dni_estudiante: str, anio: int, nivel: str, grado: str, seccion: str,
    dni_responsable: str, dni_secretaria: str, fecha: date | None = None,
) -> None:
    """Registra la matrícula con ``sp_registrar_matricula``.

    El procedimiento rechaza (con SIGNAL) la matrícula duplicada, la sección
    llena y un responsable que no sea padre ni apoderado del estudiante.
    """
    if nivel not in NIVELES or grado not in NIVELES[nivel]:
        raise ErrorValidacion("Seleccione un nivel y un grado válidos.")
    if seccion not in SECCIONES[nivel]:
        raise ErrorValidacion(f"La sección {seccion} no existe para el nivel {nivel}.")
    db.call_proc("sp_registrar_matricula", (
        dni_estudiante, int(anio), nivel, grado, seccion,
        dni_responsable, dni_secretaria, LUGAR_SUSCRIPCION, fecha or date.today(),
    ))
