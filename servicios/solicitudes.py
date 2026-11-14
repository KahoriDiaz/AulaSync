"""Solicitudes de matrícula en trámite (almacén de archivos JSON)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core import seguridad
from core.almacen import Almacen
from core.errores import ErrorPermiso, ErrorValidacion
from core.formatos import normalizar_nivel, validar_dni, validar_grado

TIPOS_SOLICITUD = ("Nueva matrícula", "Actualización de datos")
ESTADOS_SOLICITUD = ("Borrador", "Enviada", "En revisión", "Subsanación", "Aprobada", "Rechazada")
ESTADOS_EDITABLES = ("Borrador", "Subsanación")
ESTADOS_RESOLUCION = ("Enviada", "En revisión", "Subsanación")


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _almacen() -> Almacen:
    return Almacen()


def _padre(sesion: seguridad.Sesion) -> dict[str, Any]:
    return {
        "id_usuario": sesion.id_usuario,
        "dni": sesion.dni,
        "nombre": sesion.nombre_completo,
    }


def _verificar_propietario(solicitud: dict[str, Any], sesion: seguridad.Sesion) -> None:
    if not sesion.es_padre:
        return
    if str(solicitud.get("padre", {}).get("id_usuario")) != str(sesion.id_usuario):
        raise ErrorPermiso("La solicitud pertenece a otro usuario.")


def _merge(destino: dict[str, Any], cambios: dict[str, Any]) -> dict[str, Any]:
    for clave, valor in cambios.items():
        if isinstance(valor, dict) and isinstance(destino.get(clave), dict):
            destino[clave] = _merge(dict(destino[clave]), valor)
        else:
            destino[clave] = valor
    return destino


def _guardar(solicitud: dict[str, Any], usuario: Any = None, accion: str | None = None) -> int:
    if accion:
        Almacen.registrar_historial(
            solicitud, usuario, accion, solicitud.get("estado"), ""
        )
    return _almacen().guardar(solicitud, version_esperada=solicitud.get("version"))


def crear_borrador(
    tipo: str,
    estudiante_dni: str,
    anio: int,
    nivel: str,
    grado: str,
    seccion: str = "",
    datos: dict[str, Any] | None = None,
) -> str:
    sesion = seguridad.requerir_roles("Padre")
    if tipo not in TIPOS_SOLICITUD:
        raise ErrorValidacion(f"El tipo de solicitud debe ser: {', '.join(TIPOS_SOLICITUD)}.")
    dni = validar_dni(estudiante_dni, "DNI del estudiante")
    try:
        anio = int(anio)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion("El año escolar no es válido.") from exc
    if anio < 2000 or anio > 2100:
        raise ErrorValidacion("El año escolar no es válido.")
    nivel = normalizar_nivel(nivel)
    grado = validar_grado(nivel, grado)
    seccion = str(seccion or "").strip().upper()
    if len(seccion) > 5:
        raise ErrorValidacion("La sección debe tener hasta 5 caracteres.")
    almacen = _almacen()
    id_solicitud = almacen.crear(
        {
            "padre": _padre(sesion),
            "estudiante_dni": dni,
            "anio": anio,
            "nivel": nivel,
            "grado": grado,
            "datos": datos or {},
        }
    )
    solicitud = almacen.cargar(id_solicitud)
    solicitud["tipo"] = tipo
    solicitud["seccion"] = seccion
    solicitud["validaciones"] = None
    solicitud["datos"].setdefault("estudiante", {})
    solicitud["datos"]["estudiante"].setdefault("DNI", dni)
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return id_solicitud


def obtener(id_solicitud: str) -> dict[str, Any]:
    sesion = seguridad.sesion_requerida()
    solicitud = _almacen().cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    return solicitud


def actualizar(
    id_solicitud: str,
    cambios: dict[str, Any],
    seccion: str | None = None,
    anio: int | None = None,
    nivel: str | None = None,
    grado: str | None = None,
) -> dict[str, Any]:
    sesion = seguridad.sesion_requerida()
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    if solicitud.get("estado") not in ESTADOS_EDITABLES:
        raise ErrorValidacion("La solicitud ya fue enviada y no se puede editar.")
    if anio is not None:
        solicitud["anio"] = int(anio)
    if nivel is not None:
        solicitud["nivel"] = normalizar_nivel(nivel)
    if grado is not None:
        solicitud["grado"] = validar_grado(solicitud["nivel"], grado)
    if seccion is not None:
        solicitud["seccion"] = str(seccion).strip().upper()[:5]
    if cambios:
        solicitud["datos"] = _merge(solicitud.get("datos") or {}, cambios)
    solicitud["validaciones"] = None
    _guardar(solicitud, sesion.nombre_usuario, "Edición de la solicitud")
    return solicitud


def agregar_documento(id_solicitud: str, ruta: str, tipo: str) -> dict[str, Any]:
    sesion = seguridad.sesion_requerida()
    solicitud = _almacen().cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    if solicitud.get("estado") not in ESTADOS_EDITABLES:
        raise ErrorValidacion("Solo se pueden cargar documentos antes de enviar la solicitud.")
    _, solicitud = _almacen().agregar_documento(id_solicitud, ruta, tipo)
    return solicitud


def eliminar_documento(id_solicitud: str, sha256: str) -> dict[str, Any]:
    sesion = seguridad.sesion_requerida()
    solicitud = _almacen().cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    if solicitud.get("estado") not in ESTADOS_EDITABLES:
        raise ErrorValidacion("Solo se pueden quitar documentos antes de enviar la solicitud.")
    return _almacen().eliminar_documento(id_solicitud, sha256)


def validar(id_solicitud: str) -> dict[str, Any]:
    from servicios.validaciones import validar_solicitud

    sesion = seguridad.sesion_requerida()
    solicitud = _almacen().cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    resultado = validar_solicitud(solicitud)
    solicitud["validaciones"] = resultado
    _guardar(solicitud)
    return resultado


def enviar(id_solicitud: str) -> dict[str, Any]:
    from servicios.validaciones import validar_solicitud

    sesion = seguridad.requerir_roles("Padre")
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    _verificar_propietario(solicitud, sesion)
    if solicitud.get("estado") not in ESTADOS_EDITABLES:
        raise ErrorValidacion("La solicitud ya fue enviada.")
    resultado = validar_solicitud(solicitud)
    solicitud["validaciones"] = resultado
    if not resultado["puede_enviar"]:
        almacen.guardar(solicitud, version_esperada=solicitud["version"])
        pendientes = [
            item["mensaje"] for item in resultado["items"] if item["estado"] == "Error"
        ]
        raise ErrorValidacion(
            "No se puede enviar la solicitud. Corrija:\n- " + "\n- ".join(pendientes[:8])
        )
    solicitud["estado"] = "Enviada"
    solicitud["fecha_envio"] = _ahora()
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Envío de la solicitud", "Enviada",
        f"{resultado['advertencias']} advertencia(s).",
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return solicitud


def marcar_en_revision(id_solicitud: str) -> dict[str, Any]:
    sesion = seguridad.requerir_secretaria()
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    if solicitud.get("estado") not in ("Enviada", "En revisión"):
        raise ErrorValidacion("Solo se pueden revisar solicitudes enviadas.")
    if solicitud.get("estado") == "Enviada":
        solicitud["estado"] = "En revisión"
        solicitud["revisor"] = sesion.nombre_completo
        Almacen.registrar_historial(
            solicitud, sesion.nombre_usuario, "Inicio de revisión", "En revisión"
        )
        almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return solicitud


def solicitar_subsanacion(id_solicitud: str, observacion: str) -> dict[str, Any]:
    sesion = seguridad.requerir_secretaria()
    texto = str(observacion or "").strip()
    if not texto:
        raise ErrorValidacion("Indique qué debe corregir el padre o apoderado.")
    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    if solicitud.get("estado") not in ESTADOS_RESOLUCION:
        raise ErrorValidacion("La solicitud no está en un estado que admita subsanación.")
    solicitud["estado"] = "Subsanación"
    solicitud["revisor"] = sesion.nombre_completo
    solicitud["observacion"] = texto
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Solicitud de subsanación", "Subsanación", texto
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return solicitud


def guardar_validaciones(id_solicitud: str) -> dict[str, Any]:
    sesion = seguridad.requerir_secretaria()
    from servicios.validaciones import validar_solicitud

    almacen = _almacen()
    solicitud = almacen.cargar(id_solicitud)
    resultado = validar_solicitud(solicitud)
    solicitud["validaciones"] = resultado
    solicitud["revisor"] = sesion.nombre_completo
    Almacen.registrar_historial(
        solicitud, sesion.nombre_usuario, "Validación de la solicitud",
        solicitud.get("estado"),
        f"{resultado['errores']} error(es), {resultado['advertencias']} advertencia(s).",
    )
    almacen.guardar(solicitud, version_esperada=solicitud["version"])
    return resultado


def listar(
    estado: str | None = None, filtro: str = "", solo_propias: bool = False
) -> list[dict[str, Any]]:
    sesion = seguridad.sesion_requerida()
    if estado and estado not in ESTADOS_SOLICITUD:
        raise ErrorValidacion("El estado indicado no es válido.")
    propias = solo_propias or sesion.es_padre
    resultados: list[dict[str, Any]] = []
    for id_solicitud in _almacen().listar_ids():
        try:
            solicitud = _almacen().cargar(id_solicitud)
        except ErrorValidacion:
            continue
        if propias and str(solicitud.get("padre", {}).get("id_usuario")) != str(sesion.id_usuario):
            continue
        if estado and solicitud.get("estado") != estado:
            continue
        if filtro.strip():
            texto = filtro.strip().lower()
            campos = (
                id_solicitud,
                str(solicitud.get("estudiante_dni", "")),
                str(solicitud.get("padre", {}).get("nombre", "")),
                str((solicitud.get("datos", {}).get("estudiante") or {}).get("Nombres", "")),
                str((solicitud.get("datos", {}).get("estudiante") or {}).get("ApellidoPaterno", "")),
                str((solicitud.get("datos", {}).get("estudiante") or {}).get("ApellidoMaterno", "")),
            )
            if not any(texto in campo.lower() for campo in campos):
                continue
        resultados.append(solicitud)
    resultados.sort(key=lambda s: s.get("fecha_creacion", ""), reverse=True)
    return resultados


def resumen_por_estado(resultados: list[dict[str, Any]] | None = None) -> dict[str, int]:
    if resultados is None:
        resultados = listar()
    resumen = {estado: 0 for estado in ESTADOS_SOLICITUD}
    for solicitud in resultados:
        estado = solicitud.get("estado")
        if estado in resumen:
            resumen[estado] += 1
    return resumen
