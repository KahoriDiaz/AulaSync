"""Automatizaciones de la revisión de solicitudes (§13.6, puntos 1 a 3).

Solo lectura: comprueba duplicados, calcula el grado con ``fn_grado_siguiente``,
consulta cupos con ``sp_cupos_seccion`` y revisa los JSON de la bandeja. Nunca
escribe en MySQL ni modifica la solicitud; la secretaria conserva la decisión.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app import db
from app.errores import ErrorApp
from app.servicios import matricula
from app.servicios import solicitudes as sol

VERDE, AMBAR, ROJO = "verde", "ámbar", "rojo"


def alumno_registrado(dni: str) -> bool:
    """Indica si el DNI ya existe en ESTUDIANTE (aviso de actualización)."""
    fila = db.query_uno("SELECT 1 AS existe FROM ESTUDIANTE WHERE DNI = %s", (str(dni),))
    return fila is not None


def matriculado_en_anio(dni: str, anio: int) -> bool:
    """Indica si ese alumno ya tiene matrícula en el año solicitado."""
    fila = db.query_uno(
        "SELECT 1 AS existe FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = %s",
        (str(dni), int(anio)),
    )
    return fila is not None


def sugerir_seccion(anio: int, nivel: str, grado: str) -> str | None:
    """Devuelve la sección con más vacantes para el destino solicitado."""
    cupos = matricula.verificar_cupos(int(anio), str(nivel), str(grado))
    if not cupos:
        return None
    return max(cupos, key=lambda fila: int(fila.get("Vacantes") or 0))["seccion"]


def _decisiones_por_dni(decisiones: Any) -> dict[str, dict[str, Any]]:
    """Acepta el mapa por DNI o una secuencia de decisiones con clave ``dni``."""
    if not decisiones:
        return {}
    if isinstance(decisiones, dict) and "alumnos" in decisiones:
        decisiones = decisiones["alumnos"]
    if isinstance(decisiones, dict):
        return {str(dni): dict(valores or {}) for dni, valores in decisiones.items()}
    resultado: dict[str, dict[str, Any]] = {}
    for valores in decisiones if isinstance(decisiones, (list, tuple)) else ():
        if isinstance(valores, dict) and valores.get("dni"):
            resultado[str(valores["dni"])] = dict(valores)
    return resultado


def _mayor_de_edad(fecha_nacimiento: Any) -> bool | None:
    try:
        nacimiento = date.fromisoformat(str(fecha_nacimiento)[:10])
    except (TypeError, ValueError):
        return None
    hoy = date.today()
    mayoria = nacimiento.replace(year=nacimiento.year + 18)
    return hoy >= mayoria


def documentos_faltantes(solicitud: dict[str, Any], alumno: dict[str, Any]) -> list[str]:
    """Lista los documentos que conviene revisar antes de aprobar."""
    faltan: list[str] = []
    documentos = alumno.get("docs", {})
    if not documentos.get("dni"):
        faltan.append("DNI del alumno")
    constancia = alumno.get("constancia", {})
    if not documentos.get("constancia") and not constancia.get("sin_constancia"):
        faltan.append("Constancia de logros")
    if not any(padre.get("docs", {}).get("dni") for padre in solicitud.get("padres", [])):
        faltan.append("DNI de un padre/apoderado")
    if not solicitud.get("contacto_emergencia", {}).get("celular"):
        faltan.append("Celular de emergencia")
    return faltan


def _agregar(
    chequeos: list[dict[str, str]], nivel: str, etiqueta: str, detalle: str
) -> None:
    chequeos.append({"nivel": nivel, "etiqueta": etiqueta, "detalle": detalle})


def _chequeo_seguro(funcion, *argumentos: Any) -> Any:
    """Un fallo de MySQL se muestra como advertencia, no rompe la bandeja."""
    try:
        return funcion(*argumentos)
    except ErrorApp as exc:
        return exc


def evaluar(
    solicitud: dict[str, Any], decisiones: Any = None, id_actual: str = ""
) -> dict[str, Any]:
    """Devuelve un semáforo por alumno y el estado global de la solicitud."""
    anio = int(solicitud.get("anio") or 0)
    por_dni = _decisiones_por_dni(decisiones)
    otras = [
        otra for otra in sol.listar_solicitudes("pendientes")
        if str(otra.get("id")) != str(id_actual) and int(otra.get("anio") or 0) == anio
    ]
    resultado: dict[str, Any] = {"por_alumno": {}, "estado": VERDE}
    for alumno in solicitud.get("alumnos", []):
        dni = str(alumno.get("ficha", {}).get("DNI", ""))
        decision = por_dni.get(dni, {})
        destino = alumno.get("destino", {})
        chequeos: list[dict[str, str]] = []

        if len(dni) == 8 and dni.isdigit():
            _agregar(chequeos, VERDE, "DNI", f"{dni} tiene 8 dígitos.")
        else:
            _agregar(chequeos, ROJO, "DNI", "El DNI debe tener 8 dígitos.")

        ya_matriculado = _chequeo_seguro(matriculado_en_anio, dni, anio)
        duplicado = False
        for otra in otras:
            for otro_alumno in otra.get("alumnos", []):
                if str(otro_alumno.get("ficha", {}).get("DNI", "")) == dni:
                    duplicado = True
        if isinstance(ya_matriculado, ErrorApp):
            _agregar(chequeos, AMBAR, "Duplicado", "No se pudo consultar la BD.")
        elif ya_matriculado:
            _agregar(chequeos, ROJO, "Duplicado", f"Ya tiene matrícula en {anio}.")
        elif duplicado:
            _agregar(chequeos, ROJO, "Duplicado", "Otra solicitud pendiente usa ese DNI.")
        else:
            _agregar(chequeos, VERDE, "Duplicado", "Sin matrícula ni solicitudes duplicadas.")

        existente = _chequeo_seguro(alumno_registrado, dni)
        if isinstance(existente, ErrorApp):
            _agregar(chequeos, AMBAR, "Registro previo", "No se pudo consultar la BD.")
        elif existente:
            _agregar(chequeos, AMBAR, "Registro previo", "Alumno ya registrado: se actualizarán sus datos.")
        else:
            _agregar(chequeos, VERDE, "Registro previo", "Alumno nuevo: se creará.")

        if decision.get("sin_constancia") or alumno.get("constancia", {}).get("sin_constancia"):
            _agregar(chequeos, AMBAR, "Grado", "Sin constancia: no se exige coincidencia.")
        else:
            nivel = str(decision.get("nivel_ultimo") or "")
            grado = str(decision.get("grado_ultimo") or "")
            situacion = str(decision.get("situacion") or "APROBADO")
            calculado = _chequeo_seguro(matricula.grado_siguiente, nivel, grado, situacion)
            if isinstance(calculado, ErrorApp):
                _agregar(chequeos, AMBAR, "Grado", "Complete los datos vistos en la plataforma.")
            elif not calculado:
                _agregar(chequeos, AMBAR, "Grado", "Ingrese el nivel y grado anteriores.")
            elif calculado == destino.get("grado"):
                _agregar(chequeos, VERDE, "Grado", f"Corresponde {calculado}.")
            else:
                _agregar(chequeos, AMBAR, "Grado", f"Se solicitó {destino.get('grado')}, corresponde {calculado}.")

        seccion = str(decision.get("seccion") or "")
        if seccion:
            cupos = _chequeo_seguro(
                matricula.cupos_seccion, anio, destino.get("nivel", ""),
                destino.get("grado", ""), seccion,
            )
            if isinstance(cupos, ErrorApp):
                _agregar(chequeos, AMBAR, "Cupo", "No se pudo consultar el cupo.")
            elif int(cupos.get("Vacantes") or 0) <= 0:
                _agregar(chequeos, ROJO, "Cupo", f"Sección {seccion} sin vacantes.")
            elif int(cupos.get("Vacantes") or 0) <= 3:
                _agregar(chequeos, AMBAR, "Cupo", f"Sección {seccion}: quedan pocas vacantes.")
            else:
                _agregar(chequeos, VERDE, "Cupo", f"Sección {seccion} con cupo.")

        faltan = documentos_faltantes(solicitud, alumno)
        if faltan:
            _agregar(chequeos, AMBAR, "Documentos", "Revisar: " + ", ".join(faltan))
        else:
            _agregar(chequeos, VERDE, "Documentos", "Documentos completos.")

        responsable = str(solicitud.get("dni_responsable") or "")
        padres = solicitud.get("padres", [])
        nacimiento = next(
            (padre.get("FechaNacimiento") for padre in padres
             if str(padre.get("DNI")) == responsable),
            None,
        )
        if nacimiento is None:
            _agregar(chequeos, AMBAR, "Responsable", "No se pudo comprobar la mayoría de edad.")
        else:
            mayor = _mayor_de_edad(nacimiento)
            if mayor is True:
                _agregar(chequeos, VERDE, "Responsable", "Responsable mayor de 18 años.")
            elif mayor is False:
                _agregar(chequeos, ROJO, "Responsable", "El responsable es menor de 18 años.")
            else:
                _agregar(chequeos, AMBAR, "Responsable", "Fecha de nacimiento no válida.")

        niveles = {chequeo["nivel"] for chequeo in chequeos}
        estado = ROJO if ROJO in niveles else AMBAR if AMBAR in niveles else VERDE
        resultado["por_alumno"][dni] = {"estado": estado, "chequeos": chequeos}

    estados = {valor["estado"] for valor in resultado["por_alumno"].values()}
    if ROJO in estados:
        resultado["estado"] = ROJO
    elif AMBAR in estados:
        resultado["estado"] = AMBAR
    resultado["resumen"] = {
        VERDE: "Sin bloqueos: puede aprobar.",
        AMBAR: "Hay advertencias: revise los avisos antes de aprobar.",
        ROJO: "Hay bloqueos: no se puede aprobar hasta corregirlos.",
    }[resultado["estado"]]
    return resultado
