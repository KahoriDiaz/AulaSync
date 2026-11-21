"""Aprobación y matrícula de una solicitud (§6.3.3 y §13.2).

Todas las escrituras se hacen con ``CALL sp_...`` dentro de **una sola**
transacción. Python no contiene sentencias de escritura: solo llama a los
procedimientos en el orden exigido por las claves foráneas. La carpeta JSON se
bloquea con un renombrado atómico y solo se mueve a ``aprobadas/`` tras el
``COMMIT``.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Sequence

from app import db
from app.errores import ErrorValidacion
from app.servicios import solicitudes as sol

SECCIONES = {
    "Inicial": ("A", "B"),
    "Primaria": ("A", "B", "C"),
    "Secundaria": ("A", "B", "C", "D"),
}
LUGAR_SUSCRIPCION = "Virtual"
SIN_CONSTANCIA = "Sin constancia (ingresante)"


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


def grado_siguiente(nivel: str, grado: str, situacion: str) -> str:
    """Calcula el grado que corresponde usando ``fn_grado_siguiente``."""
    fila = db.query_uno(
        "SELECT fn_grado_siguiente(%s, %s, %s) AS grado", (nivel, grado, situacion)
    )
    return str(fila["grado"]) if fila else ""


def cupos_seccion(anio: int, nivel: str, grado: str, seccion: str) -> dict[str, Any]:
    """Devuelve matriculados y vacantes de una sección (30 por sección)."""
    conjuntos = db.call_proc("sp_cupos_seccion", (anio, nivel, grado, seccion))
    fila = conjuntos[0][0] if conjuntos and conjuntos[0] else {}
    matriculados = int(fila.get("Matriculados") or 0)
    vacantes = fila.get("Vacantes")
    return {
        "Matriculados": matriculados,
        # Una sección llena tiene 0 vacantes: no usar "or", que lo cambiaría a 30.
        "Vacantes": int(vacantes) if vacantes is not None else max(0, 30 - matriculados),
    }


def verificar_cupos(anio: int, nivel: str, grado: str) -> list[dict[str, Any]]:
    """Cupos de todas las secciones posibles para el nivel indicado."""
    return [
        {"seccion": seccion, **cupos_seccion(anio, nivel, grado, seccion)}
        for seccion in SECCIONES.get(nivel, ())
    ]


# --------------------------------------------------------- decisiones / grado
def _decisiones_por_dni(decisiones: Any) -> dict[str, dict[str, Any]]:
    if not decisiones:
        return {}
    if isinstance(decisiones, dict) and "alumnos" in decisiones:
        alumnos = decisiones["alumnos"]
    else:
        alumnos = decisiones
    if isinstance(alumnos, dict):
        return {str(dni): dict(valores or {}) for dni, valores in alumnos.items()}
    if isinstance(alumnos, (list, tuple)):
        resultado: dict[str, dict[str, Any]] = {}
        for valores in alumnos:
            if isinstance(valores, dict) and valores.get("dni"):
                resultado[str(valores["dni"])] = dict(valores)
        return resultado
    return {}


def nivel_de_grado_siguiente(nivel: str, grado: str, siguiente: str) -> str:
    """Infiere el nivel del grado calculado (``fn_grado_siguiente`` da solo el grado)."""
    if siguiente == "EGRESADO":
        return ""
    if nivel == "Inicial" and grado == "5 a.":
        return "Primaria"
    if nivel == "Primaria" and grado == "6.°":
        return "Secundaria"
    return nivel


def aplicar_verificaciones(
    solicitud: dict[str, Any], decisiones: Any, usuario_dni: str
) -> list[str]:
    """Registra lo visto por la secretaria y advierte si el grado no coincide."""
    por_dni = _decisiones_por_dni(decisiones)
    advertencias: list[str] = []
    ahora = date.today().isoformat()
    for alumno in solicitud.get("alumnos", []):
        ficha = alumno["ficha"]
        dni = str(ficha.get("DNI", ""))
        decision = por_dni.get(dni, {})
        constancia = alumno.setdefault("constancia", {})
        sin_constancia = bool(decision.get("sin_constancia", constancia.get("sin_constancia")))
        situacion = str(decision.get("situacion") or "APROBADO").strip().upper()
        nivel_ultimo = str(decision.get("nivel_ultimo") or constancia.get("nivel_educativo") or "")
        grado_ultimo = str(decision.get("grado_ultimo") or "")
        if not grado_ultimo and constancia.get("logros"):
            ultimo = max(constancia["logros"], key=lambda fila: int(fila.get("anio", 0)))
            grado_ultimo = str(ultimo.get("grado", ""))
        ultimo_anio = decision.get("ultimo_anio")
        if ultimo_anio is None and constancia.get("logros"):
            ultimo_anio = max(int(fila.get("anio", 0)) for fila in constancia["logros"])

        calculado = ""
        if sin_constancia:
            constancia["sin_constancia"] = True
            estado = SIN_CONSTANCIA
        else:
            calculado = grado_siguiente(nivel_ultimo, grado_ultimo, situacion)
            estado = "Verificado"
        destino = alumno.get("destino", {})
        nivel_calculado = (
            nivel_de_grado_siguiente(nivel_ultimo, grado_ultimo, calculado)
            if calculado else ""
        )
        coincide = None
        if calculado:
            coincide = (
                calculado == destino.get("grado") and nivel_calculado == destino.get("nivel")
            )
            if not coincide:
                advertencias.append(
                    f"{dni}: corresponde {nivel_calculado} {calculado} pero se solicitó "
                    f"{destino.get('nivel', '')} {destino.get('grado', '')}."
                )
        seccion = str(decision.get("seccion") or "A").strip().upper()
        if seccion not in SECCIONES.get(str(destino.get("nivel", "")), ()):
            raise ErrorValidacion(f"{dni}: sección {seccion} no válida para el nivel.")
        alumno["verificacion"] = {
            "estado": estado,
            "verificado_por": usuario_dni,
            "fecha": ahora,
            "ultimo_anio": ultimo_anio,
            "situacion": situacion,
            "nivel_ultimo": nivel_ultimo,
            "grado_ultimo": grado_ultimo,
            "grado_calculado": calculado,
            "nivel_calculado": nivel_calculado,
            "grado_solicitado": destino.get("grado", ""),
            "coincide": coincide,
            "seccion": seccion,
        }
    return advertencias


def verificar_antes_de_aprobar(solicitud: dict[str, Any]) -> list[str]:
    """Revalida los datos y comprueba matrículas previas (solo SELECT)."""
    errores: list[str] = []
    for paso in (1, 2, 3, 4, 5):
        errores.extend(sol.validar_paso(paso, solicitud))
    if solicitud.get("estado") != "Enviada":
        errores.append("Solo se puede matricular una solicitud Enviada.")
    if sol.etapa_de(solicitud) != "matricula":
        errores.append(
            "La solicitud está en la etapa Vacante: primero acepte la vacante y "
            "complete los datos de matrícula."
        )
    anio = solicitud.get("anio")
    for alumno in solicitud.get("alumnos", []):
        dni = str(alumno.get("ficha", {}).get("DNI", ""))
        fila = db.query_uno(
            "SELECT 1 AS existe FROM MATRICULA WHERE DNI_Estudiante = %s "
            "AND `AñoEscolar` = %s",
            (dni, anio),
        )
        if fila:
            errores.append(f"El alumno {dni} ya tiene matrícula en {anio}.")
    return errores


# ------------------------------------------------------------ helpers de datos
def _sin_vacios(existente: dict[str, Any], nuevos: dict[str, Any]) -> dict[str, Any]:
    """Conserva los existentes cuando el JSON trae el campo vacío.

    Siempre devuelve todas las claves de ``nuevos`` (con valor vacío si hace
    falta), porque los procedimientos exigen la firma completa.
    """
    resultado: dict[str, Any] = {}
    for clave, valor in nuevos.items():
        resultado[clave] = valor if valor not in (None, "") else existente.get(clave, valor)
    return resultado


def _padre_parametros(padre: dict[str, Any], existente: dict[str, Any] | None) -> tuple:
    campos = {
        "DNI": "DNI", "Sexo": "Sexo", "Nombres": "Nombres",
        "ApellidoPaterno": "ApellidoPaterno", "ApellidoMaterno": "ApellidoMaterno",
        "FechaNacimiento": "FechaNacimiento", "OcupacionActual": "OcupacionActual",
        "GradoInstruccion": "GradoInstruccion", "DomicilioActual": "DomicilioActual",
        "DistritoDomicilio": "DistritoDomicilio", "TelefonoFijo": "TelefonoFijo",
        "Celular": "Celular", "CorreoElectronico": "CorreoElectronico",
    }
    valores = {campo: padre.get(origen, "") for origen, campo in campos.items()}
    if existente:
        valores = _sin_vacios(existente, valores)
    return tuple(valores[campo] for campo in campos.values())


def _ie_de_alumno(alumno: dict[str, Any]) -> dict[str, str]:
    constancia = alumno.get("constancia", {})
    procedencia = alumno.get("ie_procedencia", {})
    return {
        "CodigoModularIE": str(
            procedencia.get("codigo_modular") or constancia.get("codigo_modular_ie") or ""
        ).strip(),
        "NombreIE": str(
            procedencia.get("nombre") or constancia.get("nombre_ie") or ""
        ).strip(),
        "TipoIE": str(procedencia.get("tipo") or constancia.get("tipo_ie") or "").strip(),
    }


def _estudiante_base(alumno: dict[str, Any]) -> tuple:
    """Los 22 primeros argumentos, comunes a insertar y actualizar."""
    ficha = alumno["ficha"]
    return (
        ficha.get("DNI", ""), ficha.get("Sexo", ""), ficha.get("Nombres", ""),
        ficha.get("ApellidoPaterno", ""), ficha.get("ApellidoMaterno", ""),
        ficha.get("FechaNacimiento", ""), ficha.get("DistritoNacimiento", ""),
        ficha.get("ProvinciaNacimiento", ""), ficha.get("DepartamentoNacimiento", ""),
        ficha.get("PaisNacimiento", ""), ficha.get("DomicilioActual", ""),
        ficha.get("DistritoDomicilio", ""), ficha.get("Celular", ""),
        ficha.get("CorreoElectronico", ""), ficha.get("Religion", ""),
        ficha.get("LugarQueOcupa", 1), ficha.get("TipoAtencion", ""),
        ficha.get("EnfermedadCronica", ""), bool(ficha.get("ViveConPadre", False)),
        bool(ficha.get("ViveConMadre", False)), bool(ficha.get("ElPadreVive", False)),
        bool(ficha.get("LaMadreVive", False)),
    )


def _pares_hermandad(dnis: Iterable[str]) -> list[tuple[str, str]]:
    ordenados = sorted(set(dnis))
    return [
        (ordenados[i], ordenados[j])
        for i in range(len(ordenados))
        for j in range(i + 1, len(ordenados))
    ]


# ------------------------------------------------------------- transacción
def _matricular(
    cursor, solicitud: dict[str, Any], decisiones: Any, usuario_dni: str
) -> None:
    contacto: dict[str, Any] = solicitud.get("contacto_emergencia", {})
    id_contacto: int | None = None

    # 1. Padres/apoderados (antes que ESTUDIANTE por la FK de apoderado).
    for padre in solicitud.get("padres", []):
        dni = str(padre.get("DNI", ""))
        existente = _uno(cursor, "SELECT * FROM PADRE_APODERADO WHERE DNI = %s", (dni,))
        parametros = _padre_parametros(padre, existente)
        proc = "sp_padre_actualizar" if existente else "sp_padre_insertar"
        _llamar(cursor, proc, parametros)

    for alumno in solicitud.get("alumnos", []):
        dni = str(alumno["ficha"].get("DNI", ""))
        ie = _ie_de_alumno(alumno)

        # 2. Institución de procedencia.
        if ie["CodigoModularIE"]:
            existe_ie = _uno(
                cursor,
                "SELECT CodigoModularIE, NombreIE, TipoIE FROM INSTITUCION_EDUCATIVA "
                "WHERE CodigoModularIE = %s",
                (ie["CodigoModularIE"],),
            )
            valores_ie = (
                _sin_vacios(existe_ie, ie) if existe_ie else ie
            )
            parametros_ie = (
                ie["CodigoModularIE"], valores_ie["NombreIE"], valores_ie["TipoIE"]
            )
            _llamar(
                cursor,
                "sp_ie_actualizar" if existe_ie else "sp_ie_insertar",
                parametros_ie,
            )
            codigo_ie = ie["CodigoModularIE"]
        else:
            codigo_ie = ""

        # 3. Estudiante; el primer hermano crea el contacto compartido.
        existente = _uno(cursor, "SELECT * FROM ESTUDIANTE WHERE DNI = %s", (dni,))
        apoderado = str(solicitud.get("dni_apoderado") or solicitud.get("dni_responsable") or "")
        if existente:
            fila_contacto = _uno(
                cursor,
                "SELECT IdContactoEmergencia FROM ESTUDIANTE WHERE DNI = %s", (dni,),
            )
            contacto_actual = fila_contacto.get("IdContactoEmergencia") if fila_contacto else None
            parametros = _estudiante_base(alumno) + (
                contacto_actual,
                codigo_ie or existente.get("CodigoModularIE", ""),
                apoderado,
            )
            _llamar(cursor, "sp_estudiante_actualizar", parametros)
            id_contacto = id_contacto or contacto_actual
        else:
            parametros = _estudiante_base(alumno) + (
                id_contacto,
                str(contacto.get("nombre", "")),
                str(contacto.get("celular", "")),
                codigo_ie,
                apoderado,
            )
            _llamar(cursor, "sp_estudiante_insertar", parametros)
            fila_contacto = _uno(
                cursor,
                "SELECT IdContactoEmergencia FROM ESTUDIANTE WHERE DNI = %s", (dni,),
            )
            id_contacto = id_contacto or (
                fila_contacto.get("IdContactoEmergencia") if fila_contacto else None
            )

        # 4. Relación con padres/apoderados.
        for padre in solicitud.get("padres", []):
            dni_padre = str(padre.get("DNI", ""))
            relacion = _uno(
                cursor,
                "SELECT 1 AS existe FROM TIENE_PADRES WHERE DNI_Estudiante = %s "
                "AND DNI_Padre = %s",
                (dni, dni_padre),
            )
            if not relacion:
                _llamar(cursor, "sp_tiene_padres_insertar", (dni, dni_padre))

        # 5. NEE y hermanos en la I.E.
        for necesidad in alumno.get("nee", []):
            existe = _uno(
                cursor,
                "SELECT 1 AS existe FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = %s "
                "AND NecesidadEducativaEspecial = %s",
                (dni, necesidad),
            )
            if not existe:
                _llamar(cursor, "sp_nee_insertar", (dni, necesidad))
        for nivel in alumno.get("hermanos_ie", []):
            existe = _uno(
                cursor,
                "SELECT 1 AS existe FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = %s "
                "AND NivelHermano = %s",
                (dni, nivel),
            )
            if not existe:
                _llamar(cursor, "sp_hermanos_ie_insertar", (dni, nivel))

        # 6. Constancia y logros (opcional para ingresantes).
        constancia = alumno.get("constancia", {})
        codigo_virtual = str(constancia.get("codigo_virtual") or "").strip().upper()
        if codigo_virtual and not constancia.get("sin_constancia"):
            existe = _uno(
                cursor,
                "SELECT CodigoVirtual, DNI_Estudiante, NivelEducativo, FechaHoraEmision "
                "FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s",
                (codigo_virtual,),
            )
            datos_constancia = {
                "CodigoVirtual": codigo_virtual,
                "DNI_Estudiante": dni,
                "NivelEducativo": str(constancia.get("nivel_educativo") or ""),
                "FechaHoraEmision": str(constancia.get("fecha_hora_emision") or "") or None,
            }
            if existe:
                datos_constancia = _sin_vacios(existe, datos_constancia)
                _llamar(cursor, "sp_constancia_actualizar", tuple(
                    datos_constancia[c] for c in (
                        "CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision"
                    )
                ))
            else:
                _llamar(cursor, "sp_constancia_insertar", tuple(
                    datos_constancia[c] for c in (
                        "CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision"
                    )
                ))
            for logro in constancia.get("logros", []):
                anio = int(logro.get("anio", 0))
                existe_logro = _uno(
                    cursor,
                    "SELECT 1 AS existe FROM LOGRO WHERE CodigoVirtual = %s "
                    "AND `AñoEscolar` = %s",
                    (codigo_virtual, anio),
                )
                parametros_logro = (
                    codigo_virtual, anio, str(logro.get("grado", "")),
                    str(logro.get("codigo_modular_ie") or codigo_ie or ""),
                    str(logro.get("situacion", "")),
                )
                _llamar(
                    cursor,
                    "sp_logro_actualizar" if existe_logro else "sp_logro_insertar",
                    parametros_logro,
                )

    # 7. Hermandad: un par por orden de DNI y solo si todavía no existe.
    dnis = [str(a["ficha"].get("DNI", "")) for a in solicitud.get("alumnos", [])]
    for primero, segundo in _pares_hermandad(dnis):
        existe = _uno(
            cursor,
            "SELECT 1 AS existe FROM HERMANDAD WHERE DNI_HermanoA = %s "
            "AND DNI_HermanoB = %s",
            (primero, segundo),
        )
        if not existe:
            _llamar(cursor, "sp_hermandad_insertar", (primero, segundo))

    # 8. Matrícula: el procedimiento bloquea el cupo y valida duplicados.
    for alumno in solicitud.get("alumnos", []):
        dni = str(alumno["ficha"].get("DNI", ""))
        verificacion = alumno.get("verificacion", {})
        destino = alumno.get("destino", {})
        _llamar(cursor, "sp_registrar_matricula", (
            dni,
            int(solicitud["anio"]),
            str(destino.get("nivel", "")),
            str(destino.get("grado", "")),
            str(verificacion.get("seccion") or "A"),
            str(solicitud.get("dni_responsable") or ""),
            usuario_dni,
            LUGAR_SUSCRIPCION,
            date.today(),
        ))


def aprobar_y_matricular(
    id_solicitud: str, decisiones: Any = None, usuario_dni: str | None = None
) -> dict[str, Any]:
    """Ejecuta el flujo completo de aprobación (§6.3.3, §13.2)."""
    sesion = sol._exigir_secretaria()
    usuario_dni = str(usuario_dni or sesion.dni)
    id_procesando = sol.iniciar_procesamiento(id_solicitud)
    try:
        datos = sol.obtener(id_procesando)
        errores = verificar_antes_de_aprobar(datos)
        if errores:
            raise ErrorValidacion(
                "No se puede matricular la solicitud:\n- " + "\n- ".join(errores)
            )
        advertencias = aplicar_verificaciones(datos, decisiones, usuario_dni)
        with db.transaccion() as cursor:
            _matricular(cursor, datos, decisiones, usuario_dni)

        datos["estado"] = "Aprobada"
        datos["aprobado_por"] = usuario_dni
        datos["fecha_aprobacion"] = date.today().isoformat()
        datos["advertencias_grado"] = advertencias
        datos.setdefault("historial", []).append({
            "fecha": datos["fecha_aprobacion"],
            "accion": "Aprobación y matrícula",
            "usuario": usuario_dni,
        })
        datos["id"] = id_solicitud
        sol.finalizar_procesamiento(id_procesando, datos)
        return datos
    except Exception:
        sol.cancelar_procesamiento(id_procesando)
        raise
