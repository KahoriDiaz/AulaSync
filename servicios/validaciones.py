"""Validaciones de una solicitud antes de enviarla y antes de aprobarla."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.almacen import Almacen
from core.db import consultar, consultar_uno
from core.errores import ErrorValidacion
from core.formatos import (
    ESTADOS_MATRICULA,
    SITUACIONES,
    grados_de_nivel,
    normalizar_grado,
    normalizar_nivel,
    normalizar_sexo,
    normalizar_situacion,
    validar_celular,
    normalizar_fecha,
    validar_correo,
    validar_dni,
)

DOCUMENTOS_OBLIGATORIOS = ("DNI estudiante", "DNI padre/apoderado", "Constancia de logros")
CAPACIDAD_MAXIMA = 30
CONFIANZA_MINIMA = 80


def _item(items: list[dict[str, Any]], seccion: str, campo: str, mensaje: str, estado: str) -> None:
    items.append(
        {"seccion": seccion, "campo": campo, "mensaje": mensaje, "estado": estado}
    )


def _valor(datos: dict[str, Any], grupo: str, campo: str) -> Any:
    bloque = datos.get(grupo) or {}
    return bloque.get(campo)


def _texto(valor: Any) -> str:
    return " ".join(str(valor or "").split())


def _validar_documentos(solicitud: dict[str, Any], items: list[dict[str, Any]]) -> None:
    almacen = Almacen()
    presentes = {d.get("tipo") for d in solicitud.get("documentos", [])}
    for tipo in DOCUMENTOS_OBLIGATORIOS:
        if tipo not in presentes:
            _item(items, "Documentos", tipo, f"Falta cargar: {tipo}.", "Error")
    for documento in solicitud.get("documentos", []):
        tipo = documento.get("tipo", "Documento")
        try:
            ruta: Path = almacen.ruta_documento(solicitud["id"], documento)
        except ErrorValidacion as exc:
            _item(items, "Documentos", tipo, str(exc), "Error")
            continue
        if not ruta.is_file():
            _item(items, "Documentos", tipo, f"El archivo de {tipo} no está disponible.", "Error")
            continue
        if ruta.stat().st_size != int(documento.get("bytes") or 0):
            _item(items, "Documentos", tipo, f"El archivo de {tipo} cambió de tamaño.", "Error")


def _validar_estudiante(datos: dict[str, Any], items: list[dict[str, Any]]) -> None:
    est = datos.get("estudiante") or {}
    try:
        validar_dni(est.get("DNI"), "DNI del estudiante")
    except ErrorValidacion as exc:
        _item(items, "Estudiante", "DNI", str(exc), "Error")
    try:
        normalizar_sexo(est.get("Sexo"))
    except ErrorValidacion as exc:
        _item(items, "Estudiante", "Sexo", str(exc), "Error")
    for campo, etiqueta in (
        ("Nombres", "nombres"), ("ApellidoPaterno", "apellido paterno"),
        ("ApellidoMaterno", "apellido materno"),
        ("DistritoNacimiento", "distrito de nacimiento"),
        ("ProvinciaNacimiento", "provincia de nacimiento"),
        ("DepartamentoNacimiento", "departamento de nacimiento"),
        ("DomicilioActual", "domicilio actual"),
        ("DistritoDomicilio", "distrito de domicilio"),
    ):
        if not _texto(est.get(campo)):
            _item(items, "Estudiante", campo, f"Falta el {etiqueta}.", "Error")
    fecha_nacimiento = None
    try:
        fecha_nacimiento = datetime.strptime(
            normalizar_fecha(est.get("FechaNacimiento")), "%Y-%m-%d"
        ).date()
        if fecha_nacimiento > date.today():
            _item(items, "Estudiante", "FechaNacimiento", "La fecha de nacimiento es futura.", "Error")
    except ErrorValidacion as exc:
        _item(items, "Estudiante", "FechaNacimiento", str(exc), "Error")
    try:
        lugar = int(est.get("LugarQueOcupa") or 0)
        if lugar < 1:
            raise ValueError
    except (TypeError, ValueError):
        _item(items, "Estudiante", "LugarQueOcupa", "El lugar que ocupa debe ser 1 o mayor.", "Error")
    for campo, etiqueta in (("Celular", "celular"), ("CorreoElectronico", "correo")):
        valor = est.get(campo)
        try:
            if campo == "Celular":
                validar_celular(valor, etiqueta, opcional=True)
            else:
                validar_correo(valor, etiqueta, opcional=True)
        except ErrorValidacion as exc:
            _item(items, "Estudiante", campo, str(exc), "Error")
    datos["_fecha_nacimiento_calculada"] = fecha_nacimiento


def _validar_padre(datos: dict[str, Any], items: list[dict[str, Any]]) -> None:
    padre = datos.get("padre") or {}
    try:
        validar_dni(padre.get("DNI"), "DNI del padre/apoderado")
    except ErrorValidacion as exc:
        _item(items, "Padre/apoderado", "DNI", str(exc), "Error")
    try:
        normalizar_sexo(padre.get("Sexo"))
    except ErrorValidacion as exc:
        _item(items, "Padre/apoderado", "Sexo", str(exc), "Error")
    if not _texto(padre.get("FechaNacimiento")):
        _item(items, "Padre/apoderado", "FechaNacimiento", "Falta la fecha de nacimiento.", "Error")
    if not _texto(padre.get("GradoInstruccion")):
        _item(items, "Padre/apoderado", "GradoInstruccion", "Falta el grado de instrucci?n.", "Error")
    for campo, etiqueta in (
        ("Nombres", "nombres"), ("ApellidoPaterno", "apellido paterno"),
        ("ApellidoMaterno", "apellido materno"),
        ("DomicilioActual", "domicilio"), ("DistritoDomicilio", "distrito"),
    ):
        if not _texto(padre.get(campo)):
            _item(items, "Padre/apoderado", campo, f"Falta el {etiqueta}.", "Error")
    try:
        validar_celular(padre.get("Celular"), "celular del padre/apoderado")
    except ErrorValidacion as exc:
        _item(items, "Padre/apoderado", "Celular", str(exc), "Error")


def _validar_contacto(datos: dict[str, Any], items: list[dict[str, Any]]) -> None:
    contacto = datos.get("contacto") or {}
    if not _texto(contacto.get("NombreContactoEmergencia")):
        _item(items, "Contacto de emergencia", "Nombre", "Falta el nombre del contacto.", "Error")
    try:
        validar_celular(contacto.get("CelularEmergencia"), "celular de emergencia")
    except ErrorValidacion as exc:
        _item(items, "Contacto de emergencia", "Celular", str(exc), "Error")


def _siguiente_grado(nivel: str, grado: str) -> tuple[str, str] | None:
    if grado not in grados_de_nivel(nivel):
        return None
    grados = grados_de_nivel(nivel)
    posicion = grados.index(grado)
    if posicion + 1 < len(grados):
        return nivel, grados[posicion + 1]
    if nivel == "Inicial":
        return "Primaria", "1.°"
    if nivel == "Primaria":
        return "Secundaria", "1.°"
    return None


def _logro_mas_reciente(datos: dict[str, Any]) -> dict[str, Any] | None:
    constancia = datos.get("constancia") or {}
    logros = constancia.get("logros") or []
    if not logros:
        return None
    validos = []
    for logro in logros:
        try:
            anio = int(logro.get("AñoEscolar"))
        except (TypeError, ValueError):
            continue
        validos.append((anio, logro))
    if not validos:
        return None
    return max(validos, key=lambda par: par[0])[1]


def _validar_grado(
    solicitud: dict[str, Any], datos: dict[str, Any], items: list[dict[str, Any]]
) -> None:
    fecha_nacimiento = datos.get("_fecha_nacimiento_calculada")
    anio = solicitud.get("anio")
    if not fecha_nacimiento or not anio:
        return
    try:
        anio = int(anio)
        nivel = normalizar_nivel(solicitud.get("nivel"))
        grado = _texto(solicitud.get("grado"))
    except ErrorValidacion:
        return
    if not grado:
        _item(items, "Grado", "Grado", "Falta el grado solicitado.", "Error")
        return
    edad = anio - fecha_nacimiento.year
    if (fecha_nacimiento.month, fecha_nacimiento.day) > (3, 31):
        edad -= 1

    if 3 <= edad <= 5:
        esperado = f"{edad} a."
        if nivel != "Inicial" or grado != esperado:
            _item(
                items, "Grado", "Grado",
                f"Con {edad} años al 31 de marzo corresponde Inicial {esperado}.",
                "Advertencia",
            )
        else:
            _item(items, "Grado", "Grado", f"Corresponde Inicial {esperado}.", "Correcto")
        return

    logro = _logro_mas_reciente(datos)
    if not logro:
        try:
            existe = consultar_uno(
                "SELECT DNI FROM ESTUDIANTE WHERE DNI = %s",
                (validar_dni((datos.get("estudiante") or {}).get("DNI")),),
            )
        except ErrorValidacion:
            existe = None
        if existe:
            fila = consultar_uno(
                "SELECT c.NivelEducativo, l.GradoCursado, l.SituacionFinal "
                "FROM CONSTANCIA_LOGROS c INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual "
                "WHERE c.DNI_Estudiante = %s ORDER BY l.AñoEscolar DESC LIMIT 1",
                ((datos.get("estudiante") or {}).get("DNI"),),
            )
            logro = fila
        if not logro:
            _item(
                items, "Grado", "Grado",
                "No hay constancia de logros para verificar el grado que corresponde.",
                "Advertencia",
            )
            return
        nivel_logro = logro.get("NivelEducativo")
        grado_logro = logro.get("GradoCursado")
        situacion = logro.get("SituacionFinal")
    else:
        constancia = datos.get("constancia") or {}
        try:
            nivel_logro = normalizar_nivel(constancia.get("NivelEducativo"))
        except ErrorValidacion:
            nivel_logro = None
        try:
            grado_logro = normalizar_grado(logro.get("GradoCursado"))
            if grado_logro not in grados_de_nivel(nivel_logro or ""):
                grado_logro = _texto(logro.get("GradoCursado"))
        except (ErrorValidacion, KeyError):
            grado_logro = _texto(logro.get("GradoCursado"))
        try:
            situacion = normalizar_situacion(logro.get("SituacionFinal"))
        except ErrorValidacion:
            situacion = None

    if not nivel_logro or not grado_logro:
        _item(items, "Grado", "Grado", "Los datos de la constancia no permiten verificar el grado.", "Advertencia")
        return
    if situacion == "REQUIERE RECUPERACIÓN":
        esperado_nivel, esperado_grado = nivel_logro, grado_logro
        nota = f"Pendiente de recuperación: corresponde repetir {nivel_logro} {grado_logro}."
    else:
        siguiente = _siguiente_grado(nivel_logro, grado_logro)
        if siguiente is None:
            _item(
                items, "Grado", "Grado",
                "El estudiante egresó de Secundaria; no corresponde matrícula.", "Error",
            )
            return
        esperado_nivel, esperado_grado = siguiente
        nota = f"Le corresponde {esperado_nivel} {esperado_grado}."
    if (nivel, grado) != (esperado_nivel, esperado_grado):
        _item(
            items, "Grado", "Grado",
            f"{nota} La solicitud indica {nivel} {grado}.", "Advertencia",
        )
    else:
        _item(items, "Grado", "Grado", nota, "Correcto")


def _validar_matricula(
    solicitud: dict[str, Any], datos: dict[str, Any], items: list[dict[str, Any]]
) -> None:
    dni = (datos.get("estudiante") or {}).get("DNI")
    try:
        dni = validar_dni(dni, "DNI del estudiante")
    except ErrorValidacion:
        return
    anio = solicitud.get("anio")
    try:
        anio = int(anio)
    except (TypeError, ValueError):
        return
    if consultar_uno(
        "SELECT 1 FROM MATRICULA WHERE DNI_Estudiante = %s AND AñoEscolar = %s", (dni, anio)
    ):
        _item(
            items, "Matrícula", "Año escolar",
            f"El estudiante ya tiene matrícula registrada en {anio}.", "Error",
        )
    nivel = solicitud.get("nivel")
    grado = solicitud.get("grado")
    seccion = solicitud.get("seccion")
    if nivel and grado and seccion:
        try:
            total = consultar_uno(
                "SELECT COUNT(*) AS total FROM MATRICULA WHERE AñoEscolar = %s AND Nivel = %s "
                "AND Grado = %s AND Seccion = %s AND Estado = 'Matriculado'",
                (anio, nivel, grado, seccion),
            )
            total = int(total["total"]) if total else 0
            if total >= CAPACIDAD_MAXIMA:
                _item(
                    items, "Matrícula", "Sección",
                    f"La sección {nivel} {grado} {seccion} alcanzó el máximo de "
                    f"{CAPACIDAD_MAXIMA} estudiantes.", "Error",
                )
        except Exception:
            pass
    existe = consultar_uno("SELECT DNI FROM ESTUDIANTE WHERE DNI = %s", (dni,))
    anterior = consultar_uno(
        "SELECT 1 FROM MATRICULA WHERE DNI_Estudiante = %s AND AñoEscolar = %s", (dni, anio - 1)
    )
    if existe and anterior:
        _item(items, "Matrícula", "Continuidad", "El estudiante continúa del año anterior.", "Correcto")
    elif existe:
        _item(items, "Matrícula", "Continuidad", "El estudiante no tiene matrícula el año anterior; se considera nuevo.", "Correcto")


def _validar_constancia(
    solicitud: dict[str, Any], datos: dict[str, Any], items: list[dict[str, Any]]
) -> None:
    constancia = datos.get("constancia") or {}
    codigo = _texto(constancia.get("CodigoVirtual")).upper()
    if len(codigo) != 8 or not codigo.isalnum():
        _item(items, "Constancia", "Código", "El código virtual debe tener 8 letras o números.", "Error")
    try:
        nivel = normalizar_nivel(constancia.get("NivelEducativo"))
    except ErrorValidacion:
        _item(items, "Constancia", "Nivel", "El nivel educativo de la constancia no es válido.", "Error")
        nivel = None
    logros = constancia.get("logros") or []
    if not logros:
        _item(items, "Constancia", "Logros", "La constancia no tiene logros.", "Error")
        return
    anios: list[int] = []
    grados: list[str] = []
    for logro in logros:
        try:
            anio = int(logro.get("AñoEscolar"))
        except (TypeError, ValueError):
            _item(items, "Constancia", "Año escolar", "Hay un año escolar inválido.", "Error")
            continue
        anios.append(anio)
        grado = _texto(logro.get("GradoCursado"))
        if nivel:
            try:
                grado = normalizar_grado(grado)
                if grado not in grados_de_nivel(nivel):
                    raise ErrorValidacion("")
            except ErrorValidacion:
                _item(
                    items, "Constancia", "Grado",
                    f"El grado '{grado}' no corresponde a {nivel}.", "Error",
                )
        grados.append(grado)
        codigo_ie = _texto(logro.get("CodigoModularIE"))
        if codigo_ie and not consultar_uno(
            "SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", (codigo_ie,)
        ):
            _item(
                items, "Constancia", "Institución",
                f"La institución {codigo_ie} no está registrada; se dará de alta al aprobar.",
                "Advertencia",
            )
        try:
            normalizar_situacion(logro.get("SituacionFinal"))
        except ErrorValidacion as exc:
            _item(items, "Constancia", "Situación", str(exc), "Error")
    if len(set(anios)) != len(anios):
        _item(items, "Constancia", "Año escolar", "Hay años escolares repetidos.", "Error")
    ordenados = sorted(set(anios))
    for previo, siguiente in zip(ordenados, ordenados[1:]):
        if siguiente != previo + 1:
            _item(
                items, "Constancia", "Año escolar",
                f"Falta el año {previo + 1} entre los logros.", "Advertencia",
            )
            break
    orden_grados = [g for g in grados if g in grados_de_nivel(nivel or "")]
    if len(orden_grados) > 1 and orden_grados != sorted(
        orden_grados, key=lambda g: grados_de_nivel(nivel).index(g)
    ):
        _item(items, "Constancia", "Grado", "Los grados de los logros no están en orden.", "Advertencia")
    if codigo:
        existente = consultar_uno(
            "SELECT DNI_Estudiante FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s", (codigo,)
        )
        dni = (datos.get("estudiante") or {}).get("DNI")
        if existente and existente["DNI_Estudiante"] != dni:
            _item(
                items, "Constancia", "Código",
                "Ese código virtual ya pertenece a otro estudiante.", "Error",
            )


def _validar_confianza(datos: dict[str, Any], items: list[dict[str, Any]]) -> None:
    confianzas = datos.get("ocr_confianzas") or {}
    for campo, confianza in confianzas.items():
        try:
            valor = int(confianza)
        except (TypeError, ValueError):
            continue
        if valor < CONFIANZA_MINIMA:
            _item(
                items, "OCR", campo,
                f"Confianza baja ({valor}%). Verifique el dato transcrito.", "Advertencia",
            )


def validar_solicitud(solicitud: dict[str, Any]) -> dict[str, Any]:
    datos = solicitud.get("datos") or {}
    items: list[dict[str, Any]] = []
    _validar_documentos(solicitud, items)
    _validar_estudiante(datos, items)
    _validar_padre(datos, items)
    _validar_contacto(datos, items)
    _validar_grado(solicitud, datos, items)
    _validar_matricula(solicitud, datos, items)
    _validar_constancia(solicitud, datos, items)
    _validar_confianza(datos, items)
    errores = sum(1 for item in items if item["estado"] == "Error")
    advertencias = sum(1 for item in items if item["estado"] == "Advertencia")
    return {
        "items": items,
        "errores": errores,
        "advertencias": advertencias,
        "puede_enviar": errores == 0,
        "puede_aprobar": errores == 0,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
