"""Aprobación y rechazo de solicitudes: traslado transaccional a las 12 tablas."""
from __future__ import annotations

from datetime import date
from typing import Any

from core import seguridad
from core.almacen import Almacen
from core.db import transaccion
from core.errores import ErrorValidacion
from core.formatos import normalizar_nivel, validar_fecha_no_futura, validar_grado

from servicios import constancias, contactos, estudiantes, hermandad, instituciones, padres


def _almacen() -> Almacen:
    return Almacen()


def _absorber(cursor: Any) -> None:
    for resultado in cursor.stored_results():
        resultado.fetchall()
    while cursor.nextset():
        pass


def _padres_solicitud(datos: dict[str, Any]) -> list[str]:
    propios = datos.get("padres") or []
    salida: list[str] = []
    for item in propios:
        if isinstance(item, dict):
            dni = item.get("DNI") or item.get("dni")
        else:
            dni = item
        if dni:
            salida.append(str(dni).strip())
    return salida


def _asegurar_instituciones(cursor, datos: dict[str, Any]) -> None:
    for institucion in datos.get("instituciones") or []:
        if not isinstance(institucion, dict):
            continue
        instituciones.buscar_o_crear_en_transaccion(
            cursor,
            institucion.get("CodigoModularIE") or institucion.get("codigo") or "",
            institucion.get("NombreIE") or institucion.get("nombre"),
            institucion.get("TipoIE") or institucion.get("tipo"),
        )
    constancia = datos.get("constancia") or {}
    for logro in constancia.get("logros") or []:
        codigo = logro.get("CodigoModularIE") or ""
        instituciones.buscar_o_crear_en_transaccion(cursor, codigo)
    estudiante = datos.get("estudiante") or {}
    if estudiante.get("CodigoModularIE"):
        instituciones.buscar_o_crear_en_transaccion(cursor, estudiante["CodigoModularIE"])


def _guardar_padre(cursor, datos: dict[str, Any], sesion: seguridad.Sesion) -> str:
    padre_datos = datos.get("padre") or {}
    dni = str(padre_datos.get("DNI") or sesion.dni).strip()
    cursor.execute("SELECT * FROM PADRE_APODERADO WHERE DNI = %s", (dni,))
    actual = cursor.fetchone()
    combinado = {**padre_datos, "DNI": dni}
    if actual:
        combinado = {**actual, **combinado}
        valores = padres.normalizar(combinado)
        padres.actualizar_en_transaccion(cursor, valores)
    else:
        valores = padres.normalizar(combinado)
        padres.insertar_en_transaccion(cursor, valores)
    return dni


def _guardar_estudiante(
    cursor, datos: dict[str, Any], contacto_id: int, padre_dni: str
) -> str:
    est = dict(datos.get("estudiante") or {})
    dni = str(est.get("DNI") or "").strip()
    cursor.execute("SELECT * FROM ESTUDIANTE WHERE DNI = %s", (dni,))
    actual = cursor.fetchone()
    if actual:
        est = {**actual, **est}
    est["IdContactoEmergencia"] = contacto_id
    est["DNI"] = dni
    if not est.get("DNI_Apoderado"):
        est["DNI_Apoderado"] = padre_dni
    valores = estudiantes.normalizar(est)
    estudiantes.validar_referencias(valores, cursor)
    if actual:
        estudiantes.actualizar_en_transaccion(cursor, valores)
    else:
        estudiantes.insertar_en_transaccion(cursor, valores)
    return dni


def _guardar_constancia(
    cursor, datos: dict[str, Any], dni_estudiante: str, actualizar: bool
) -> None:
    constancia = datos.get("constancia") or {}
    codigo = str(constancia.get("CodigoVirtual") or "").strip().upper()
    if not codigo:
        return
    cursor.execute(
        "SELECT DNI_Estudiante FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s", (codigo,)
    )
    existente = cursor.fetchone()
    logros = constancias.normalizar_logros(
        normalizar_nivel(constancia.get("NivelEducativo")), constancia.get("logros") or []
    )
    constancias.validar_ie(logros, cursor)
    if existente:
        if actualizar and existente["DNI_Estudiante"] == dni_estudiante:
            constancias.reemplazar_logros_en_transaccion(cursor, codigo, logros)
        return
    valores = constancias.normalizar_constancia({**constancia, "DNI_Estudiante": dni_estudiante})
    constancias.insertar_en_transaccion(cursor, valores)
    constancias.reemplazar_logros_en_transaccion(cursor, codigo, logros)


def aprobar(id_solicitud: str, observacion: str = "") -> dict[str, Any]:
    sesion = seguridad.requerir_secretaria()
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    if solicitud.get("estado") in ("Aprobada", "Rechazada"):
        raise ErrorValidacion("La solicitud ya fue resuelta.")
    if solicitud.get("estado") not in ("Enviada", "En revisión"):
        raise ErrorValidacion("La solicitud debe estar enviada o en revisión para aprobarse.")
    from servicios.validaciones import validar_solicitud

    resultado = validar_solicitud(solicitud)
    solicitud["validaciones"] = resultado
    if not resultado["puede_aprobar"]:
        almacen.guardar(solicitud, version_esperada=solicitud["version"])
        pendientes = [item["mensaje"] for item in resultado["items"] if item["estado"] == "Error"]
        raise ErrorValidacion(
            "No se puede aprobar la solicitud. Corrija:\n- " + "\n- ".join(pendientes[:8])
        )

    datos = solicitud.get("datos") or {}
    anio = int(solicitud["anio"])
    nivel = normalizar_nivel(solicitud["nivel"])
    grado = validar_grado(nivel, solicitud["grado"])
    seccion = str(solicitud.get("seccion") or "").strip().upper()
    if not seccion:
        raise ErrorValidacion("La solicitud no tiene sección asignada.")
    fecha_matricula = validar_fecha_no_futura(
        datos.get("fecha_matricula") or date.today().isoformat(), "fecha de matrícula"
    )
    lugar = str(datos.get("lugar") or "Cercado").strip()[:30]

    with transaccion() as cursor:
        _asegurar_instituciones(cursor, datos)
        padre_dni = _guardar_padre(cursor, datos, sesion)
        contacto_id = contactos.buscar_o_crear_en_transaccion(
            cursor,
            (datos.get("contacto") or {}).get("NombreContactoEmergencia"),
            (datos.get("contacto") or {}).get("CelularEmergencia"),
        )
        dni_estudiante = _guardar_estudiante(cursor, datos, contacto_id, padre_dni)
        for otro in _padres_solicitud(datos):
            cursor.execute("SELECT 1 FROM PADRE_APODERADO WHERE DNI = %s", (otro,))
            if cursor.fetchone() is None:
                raise ErrorValidacion(f"El padre o apoderado con DNI {otro} no existe.")
            cursor.execute(
                "INSERT IGNORE INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES (%s, %s)",
                (dni_estudiante, otro),
            )
        cursor.execute(
            "INSERT IGNORE INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES (%s, %s)",
            (dni_estudiante, padre_dni),
        )
        _guardar_constancia(
            cursor, datos, dni_estudiante, solicitud.get("tipo") == "Actualización de datos"
        )
        for dni_hermano in datos.get("hermanos_dni") or []:
            try:
                hermandad.insertar_en_transaccion(cursor, dni_estudiante, str(dni_hermano))
            except ErrorValidacion:
                continue
        for necesidad in datos.get("nee") or []:
            texto = str(necesidad).strip()
            if texto:
                cursor.execute(
                    "INSERT IGNORE INTO ESTUDIANTE_NEE (DNI_Estudiante, NecesidadEducativaEspecial) "
                    "VALUES (%s, %s)",
                    (dni_estudiante, texto[:50]),
                )
        for nivel_hermano in datos.get("hermanos_ie") or []:
            try:
                nivel_hermano = normalizar_nivel(nivel_hermano)
            except ErrorValidacion:
                continue
            cursor.execute(
                "INSERT IGNORE INTO ESTUDIANTE_HERMANOS_IE (DNI_Estudiante, NivelHermano) "
                "VALUES (%s, %s)",
                (dni_estudiante, nivel_hermano),
            )
        cursor.callproc(
            "sp_registrar_matricula",
            (
                dni_estudiante, anio, nivel, grado, seccion, padre_dni,
                sesion.dni, lugar, fecha_matricula,
            ),
        )
        _absorber(cursor)

    solicitud["estado"] = "Aprobada"
    solicitud["fecha_resolucion"] = date.today().isoformat()
    solicitud["revisor"] = sesion.nombre_completo
    solicitud["observacion"] = str(observacion or "").strip()
    solicitud["matricula"] = {
        "anio": anio, "nivel": nivel, "grado": grado, "seccion": seccion,
        "fecha": fecha_matricula, "lugar": lugar,
    }
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Aprobación de la solicitud", "Aprobada",
        solicitud["observacion"],
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    almacen.eliminar_documentos(id_solicitud)
    solicitud = almacen.cargar(id_solicitud)
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Eliminación de documentos", "Aprobada",
        "Los archivos se eliminaron después de la aprobación.",
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return solicitud


def rechazar(id_solicitud: str, motivo: str) -> dict[str, Any]:
    sesion = seguridad.requerir_secretaria()
    texto = str(motivo or "").strip()
    if not texto:
        raise ErrorValidacion("Indique el motivo del rechazo.")
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    if solicitud.get("estado") not in ("Enviada", "En revisión", "Subsanación"):
        raise ErrorValidacion("La solicitud no está en un estado que admita rechazo.")
    solicitud["estado"] = "Rechazada"
    solicitud["fecha_resolucion"] = date.today().isoformat()
    solicitud["revisor"] = sesion.nombre_completo
    solicitud["observacion"] = texto
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Rechazo de la solicitud", "Rechazada", texto
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    almacen.eliminar_documentos(id_solicitud)
    solicitud = almacen.cargar(id_solicitud)
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Eliminación de documentos", "Rechazada", ""
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return solicitud
