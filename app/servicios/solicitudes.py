"""Gestión de solicitudes de matrícula como bandeja de archivos JSON (§5).

No hay tabla nueva: la solicitud del padre vive bajo ``data/solicitudes`` y
solo se escribe en MySQL cuando la secretaria aprueba el flujo completo.
Esta capa valida los datos, aplica los permisos por rol y escribe el JSON de
forma atómica; la interfaz nunca accede directamente a los archivos.

La rama de directorios se puede redirigir en las pruebas con
:func:`configurar_directorio`.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.errores import ErrorApp, ErrorConflicto, ErrorPermiso, ErrorValidacion
from app.sesion import autenticacion

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SOLICITUDES_DIR = BASE_DIR / "data" / "solicitudes"

EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".pdf"}
TAMANIO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB
MAXIMO_ALUMNOS = 6
MAXIMO_PADRES = 2

NIVELES = {
    "Inicial": ("3 a.", "4 a.", "5 a."),
    "Primaria": ("1.°", "2.°", "3.°", "4.°", "5.°", "6.°"),
    "Secundaria": ("1.°", "2.°", "3.°", "4.°", "5.°"),
}
SEXOS = ("M", "F")
TIPOS_ATENCION = ("ESSALUD", "SIS", "Otros")
GRADOS_INSTRUCCION = ("Primaria", "Secundaria", "Superior", "Otros")
CAMPOS_ALUMNO_OBLIGATORIOS = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno",
    "FechaNacimiento", "DistritoNacimiento", "ProvinciaNacimiento",
    "DepartamentoNacimiento", "PaisNacimiento", "DomicilioActual",
    "DistritoDomicilio", "LugarQueOcupa", "ViveConPadre", "ViveConMadre",
    "ElPadreVive", "LaMadreVive",
)
CAMPOS_PADRE_OBLIGATORIOS = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno",
    "FechaNacimiento", "GradoInstruccion", "DomicilioActual",
    "DistritoDomicilio", "Celular",
)
ESTADOS = ("Borrador", "Enviada", "Observada", "Aprobada", "Rechazada")
CARPETAS = {
    "pendientes": "pendientes",
    "aprobadas": "aprobadas",
    "rechazadas": "rechazadas",
}


# --------------------------------------------------------------------- rutas
def configurar_directorio(ruta: Path | str) -> None:
    """Redirige la bandeja de solicitudes (útil para pruebas)."""
    global SOLICITUDES_DIR
    SOLICITUDES_DIR = Path(ruta)


def restaurar_directorio() -> None:
    """Vuelve a la bandeja ubicada junto al código fuente."""
    configurar_directorio(BASE_DIR / "data" / "solicitudes")


def _asegurar_directorios() -> None:
    for nombre in CARPETAS.values():
        (SOLICITUDES_DIR / nombre).mkdir(parents=True, exist_ok=True)


def _base(estado: str = "pendientes") -> Path:
    if estado not in CARPETAS:
        raise ErrorValidacion(f"Estado de bandeja desconocido: {estado}.")
    _asegurar_directorios()
    return SOLICITUDES_DIR / CARPETAS[estado]


def carpeta_solicitud(id_solicitud: str, estado: str = "pendientes") -> Path:
    """Devuelve la carpeta de una solicitud dentro de la bandeja indicada."""
    return _base(estado) / id_solicitud


def ruta_solicitud(id_solicitud: str, estado: str = "pendientes") -> Path:
    """Devuelve la ruta al archivo ``solicitud.json``."""
    return carpeta_solicitud(id_solicitud, estado) / "solicitud.json"


# ------------------------------------------------------------------- plantilla
def nuevo_alumno() -> dict[str, Any]:
    """Devuelve la estructura vacía de un alumno de la solicitud (§5)."""
    return {
        "ficha": {
            "DNI": "", "Sexo": "", "Nombres": "", "ApellidoPaterno": "",
            "ApellidoMaterno": "", "FechaNacimiento": "", "DistritoNacimiento": "",
            "ProvinciaNacimiento": "", "DepartamentoNacimiento": "", "PaisNacimiento": "",
            "DomicilioActual": "", "DistritoDomicilio": "", "Celular": "",
            "CorreoElectronico": "", "Religion": "", "LugarQueOcupa": 1,
            "TipoAtencion": "", "EnfermedadCronica": "", "ViveConPadre": True,
            "ViveConMadre": True, "ElPadreVive": True, "LaMadreVive": True,
        },
        "nee": [],
        "hermanos_ie": [],
        "ie_procedencia": {"codigo_modular": "", "nombre": "", "tipo": ""},
        "destino": {"nivel": "", "grado": ""},
        "constancia": {"codigo_virtual": "", "logros": []},
        "docs": {"dni": "", "constancia": ""},
        "verificacion": {"estado": "Pendiente", "verificado_por": None},
    }


def nuevo_padre(vinculo: str = "Padre") -> dict[str, Any]:
    """Devuelve la estructura vacía de un padre, madre o apoderado."""
    padre = {
        "vinculo": vinculo,
        "DNI": "", "Sexo": "", "Nombres": "", "ApellidoPaterno": "",
        "ApellidoMaterno": "", "FechaNacimiento": "", "OcupacionActual": "",
        "GradoInstruccion": "", "DomicilioActual": "", "DistritoDomicilio": "",
        "TelefonoFijo": "", "Celular": "", "CorreoElectronico": "",
    }
    return padre


def plantilla_solicitud(anio: int, dni_solicitante: str) -> dict[str, Any]:
    """Crea la estructura inicial de una solicitud en estado Borrador."""
    return {
        "id": "",
        "anio": int(anio),
        "estado": "Borrador",
        "dni_solicitante": str(dni_solicitante),
        "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
        "fecha_envio": None,
        "padres": [],
        "dni_responsable": None,
        "dni_apoderado": None,
        "contacto_emergencia": {"nombre": "", "celular": ""},
        "alumnos": [],
        "observaciones": [],
        "historial": [{
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "accion": "Creación de la solicitud",
            "usuario": str(dni_solicitante),
        }],
    }


# -------------------------------------------------------------------- permisos
def _sesion():
    sesion = autenticacion.sesion_activa
    if sesion is None:
        raise ErrorPermiso("Inicie sesión para trabajar con solicitudes.")
    return sesion


def _exigir_padre() -> Any:
    sesion = _sesion()
    if sesion.rol != "Padre":
        raise ErrorPermiso("Solo el padre o apoderado puede crear y enviar solicitudes.")
    return sesion


def _exigir_secretaria() -> Any:
    sesion = _sesion()
    if sesion.rol != "Secretaria":
        raise ErrorPermiso("Solo la secretaria puede revisar solicitudes.")
    return sesion


def _verificar_propietario(solicitud: dict[str, Any], sesion: Any) -> None:
    if str(solicitud.get("dni_solicitante", "")) != str(sesion.dni):
        raise ErrorPermiso("No puede acceder a una solicitud de otro padre/apoderado.")


# ------------------------------------------------------------------ lectura/escritura
def _leer_json(ruta: Path) -> dict[str, Any]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorApp(f"No existe la solicitud en {ruta.parent.name}.") from exc
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise ErrorApp(
            f"La solicitud {ruta.parent.name} está ilegible; avise a la secretaria."
        ) from exc
    if not isinstance(datos, dict):
        raise ErrorApp(f"La solicitud {ruta.parent.name} tiene un formato inválido.")
    return datos


def json_atomico(ruta: Path, datos: dict[str, Any]) -> None:
    """Escribe el JSON en un archivo temporal y lo reemplaza (§13.2 punto 12)."""
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)


def guardar_solicitud(solicitud: dict[str, Any], estado: str = "pendientes") -> str:
    """Guarda una solicitud en su carpeta y devuelve su identificador."""
    id_solicitud = str(solicitud["id"])
    carpeta = carpeta_solicitud(id_solicitud, estado)
    carpeta.mkdir(parents=True, exist_ok=True)
    json_atomico(ruta_solicitud(id_solicitud, estado), solicitud)
    return id_solicitud


def obtener(id_solicitud: str, estado: str = "pendientes") -> dict[str, Any]:
    """Carga una solicitud, comprobando el permiso del usuario activo."""
    sesion = _sesion()
    datos = _leer_json(ruta_solicitud(id_solicitud, estado))
    if sesion.rol == "Padre":
        _verificar_propietario(datos, sesion)
    elif sesion.rol != "Secretaria":
        raise ErrorPermiso("Rol no autorizado para leer solicitudes.")
    return datos


def listar_solicitudes(
    estado: str = "pendientes", dni_solicitante: str | None = None
) -> list[dict[str, Any]]:
    """Lista solicitudes de una bandeja; un padre solo ve las suyas (§13.1)."""
    sesion = _sesion()
    if sesion.rol == "Padre":
        dni_solicitante = str(sesion.dni)
    elif sesion.rol != "Secretaria":
        raise ErrorPermiso("Rol no autorizado para listar solicitudes.")

    resultado: list[dict[str, Any]] = []
    for carpeta in sorted(_base(estado).iterdir()):
        if not carpeta.is_dir():
            continue
        ruta = carpeta / "solicitud.json"
        if not ruta.exists():
            continue
        try:
            datos = _leer_json(ruta)
        except ErrorApp:
            # Un JSON dañado se muestra como ilegible sin romper la bandeja.
            datos = {"id": carpeta.name, "estado": "ilegible", "error": "JSON dañado"}
        if dni_solicitante is None or str(datos.get("dni_solicitante")) == str(dni_solicitante):
            resultado.append(datos)
    return resultado


# -------------------------------------------------------------------- identificadores
def _siguiente_numero(anio: int) -> int:
    """Devuelve el siguiente número disponible para SOL-AAAA-NNNN."""
    _asegurar_directorios()
    prefijo = f"SOL-{anio}-"
    existente = 0
    for base in _base().iterdir():
        if not base.is_dir():
            continue
        nombre = base.name.split(".")[0]
        if nombre.startswith(prefijo):
            try:
                existente = max(existente, int(nombre[len(prefijo):]))
            except ValueError:
                continue
    return existente + 1


def generar_id(anio: int) -> str:
    """Genera SOL-AAAA-NNNN creando la carpeta de forma atómica (§13.2 punto 13)."""
    _asegurar_directorios()
    numero = _siguiente_numero(anio)
    while True:
        identificador = f"SOL-{anio}-{numero:04d}"
        try:
            (_base() / identificador).mkdir(exist_ok=False)
            return identificador
        except FileExistsError:
            numero += 1


# ---------------------------------------------------------------------- cambios
def crear_borrador(anio: int | None = None) -> dict[str, Any]:
    """Crea una solicitud nueva en Borrador para el padre con sesión activa."""
    sesion = _exigir_padre()
    anio = int(anio or (date.today().year + 1))
    datos = plantilla_solicitud(anio, sesion.dni)
    datos["id"] = generar_id(anio)
    guardar_solicitud(datos)
    return datos


def _fusionar(destino: dict[str, Any], cambios: dict[str, Any]) -> None:
    """Fusiona cambios respetando los diccionarios anidados de la ficha."""
    for clave, valor in cambios.items():
        if clave in ("id", "dni_solicitante", "estado", "fecha_envio", "historial"):
            continue
        if isinstance(valor, dict) and isinstance(destino.get(clave), dict):
            _fusionar(destino[clave], valor)
        else:
            destino[clave] = valor


def actualizar(id_solicitud: str, cambios: dict[str, Any]) -> dict[str, Any]:
    """Actualiza un borrador o una solicitud observada devuelta por la secretaria."""
    sesion = _exigir_padre()
    datos = obtener(id_solicitud)
    if datos["estado"] not in ("Borrador", "Observada"):
        raise ErrorValidacion(
            f"La solicitud {datos['estado']} ya no puede modificarse."
        )
    _verificar_propietario(datos, sesion)
    _fusionar(datos, cambios)
    datos["historial"].append({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "accion": "Actualización de datos por el padre",
        "usuario": str(sesion.dni),
    })
    guardar_solicitud(datos)
    return datos


def _fecha(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor.strip()[:10])
        except ValueError:
            return None
    return None


def _es_verdadero(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("sí", "si", "true", "1", "s")


def _dni_valido(valor: Any) -> bool:
    return bool(re.fullmatch(r"\d{8}", str(valor or "")))


def _celular_valido(valor: Any) -> bool:
    return bool(re.fullmatch(r"\d{9}", str(valor or "")))


def validar_paso(paso: int, solicitud: dict[str, Any]) -> list[str]:
    """Valida uno de los cinco pasos del asistente del padre (§6.2, §14.8)."""
    errores: list[str] = []
    alumnos = solicitud.get("alumnos", [])
    padres = solicitud.get("padres", [])

    if paso == 1:
        anio = solicitud.get("anio")
        permitidos = (date.today().year, date.today().year + 1)
        if anio not in permitidos:
            errores.append(f"El año escolar debe ser {permitidos[0]} o {permitidos[1]}.")
        if not 1 <= len(alumnos) <= MAXIMO_ALUMNOS:
            errores.append(f"Agregue entre 1 y {MAXIMO_ALUMNOS} alumnos.")
        vistos: set[str] = set()
        for indice, alumno in enumerate(alumnos, 1):
            ficha = alumno.get("ficha", {})
            dni = str(ficha.get("DNI", ""))
            if not _dni_valido(dni):
                errores.append(f"Alumno {indice}: el DNI debe tener 8 dígitos.")
            elif dni in vistos:
                errores.append(f"Alumno {indice}: el DNI {dni} está repetido en la solicitud.")
            vistos.add(dni)
            destino = alumno.get("destino", {})
            nivel, grado = destino.get("nivel"), destino.get("grado")
            if nivel not in NIVELES:
                errores.append(f"Alumno {indice}: nivel no válido.")
            elif grado not in NIVELES[nivel]:
                errores.append(f"Alumno {indice}: grado no válido para {nivel}.")
        return errores

    if paso == 2:
        contacto = solicitud.get("contacto_emergencia", {})
        if not str(contacto.get("nombre", "")).strip():
            errores.append("Ingrese el nombre del contacto de emergencia.")
        if not _celular_valido(contacto.get("celular")):
            errores.append("El celular de emergencia debe tener 9 dígitos.")
        for indice, alumno in enumerate(alumnos, 1):
            ficha = alumno.get("ficha", {})
            for campo in CAMPOS_ALUMNO_OBLIGATORIOS:
                valor = ficha.get(campo)
                if campo.endswith("Vive") or campo in ("ViveConPadre", "ViveConMadre"):
                    continue
                if valor is None or str(valor).strip() == "" or str(valor).strip() == "0":
                    errores.append(f"Alumno {indice}: falta {campo}.")
            nacimiento = _fecha(ficha.get("FechaNacimiento"))
            if nacimiento is None or nacimiento > date.today():
                errores.append(f"Alumno {indice}: la fecha de nacimiento no es válida.")
            sexo = str(ficha.get("Sexo") or "").strip()
            if sexo and sexo not in SEXOS:
                errores.append(f"Alumno {indice}: el sexo debe ser M o F.")
            tipo = str(ficha.get("TipoAtencion") or "").strip()
            if tipo and tipo not in TIPOS_ATENCION:
                errores.append(f"Alumno {indice}: tipo de atención no válido.")
            celular = ficha.get("Celular")
            if celular and str(celular).strip() and not _celular_valido(celular):
                errores.append(f"Alumno {indice}: el celular debe tener 9 dígitos.")
            if any(len(str(n)) > 50 for n in alumno.get("nee", [])):
                errores.append(f"Alumno {indice}: una NEE supera los 50 caracteres.")
            if any(n not in NIVELES for n in alumno.get("hermanos_ie", [])):
                errores.append(f"Alumno {indice}: nivel de hermano en la I.E. no válido.")
        return errores

    if paso == 3:
        if not padres:
            errores.append("Ingrese al menos un padre, madre o apoderado.")
        vinculos = [
            str(p.get("vinculo", "Padre")) for p in padres
        ]
        if vinculos.count("Padre") + vinculos.count("Madre") > MAXIMO_PADRES:
            errores.append("No se pueden registrar más de dos padres por alumno.")
        dni_padres: set[str] = set()
        for indice, padre in enumerate(padres, 1):
            for campo in CAMPOS_PADRE_OBLIGATORIOS:
                valor = padre.get(campo)
                if valor is None or str(valor).strip() == "":
                    errores.append(f"Padre/apoderado {indice}: falta {campo}.")
            dni = str(padre.get("DNI", ""))
            if not _dni_valido(dni):
                errores.append(f"Padre/apoderado {indice}: el DNI debe tener 8 dígitos.")
            dni_padres.add(dni)
            sexo = str(padre.get("Sexo") or "").strip()
            if sexo and sexo not in SEXOS:
                errores.append(f"Padre/apoderado {indice}: el sexo debe ser M o F.")
            instruccion = str(padre.get("GradoInstruccion") or "").strip()
            if instruccion and instruccion not in GRADOS_INSTRUCCION:
                errores.append(f"Padre/apoderado {indice}: grado de instrucción no válido.")
            nacimiento = _fecha(padre.get("FechaNacimiento"))
            if nacimiento is None:
                errores.append(f"Padre/apoderado {indice}: fecha de nacimiento no válida.")
            else:
                hoy = date.today()
                edad = hoy.year - nacimiento.year - (
                    (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
                )
                if edad < 18:
                    errores.append(f"Padre/apoderado {indice}: debe ser mayor de 18 años.")
            if padre.get("Celular") and not _celular_valido(padre.get("Celular")):
                errores.append(f"Padre/apoderado {indice}: el celular debe tener 9 dígitos.")
            fijo = str(padre.get("TelefonoFijo") or "").strip()
            if fijo and not _celular_valido(fijo):
                errores.append(f"Padre/apoderado {indice}: el teléfono fijo debe tener 9 dígitos.")
        for indice, alumno in enumerate(alumnos, 1):
            dni_alumno = str(alumno.get("ficha", {}).get("DNI", ""))
            if dni_alumno in dni_padres:
                errores.append(f"Alumno {indice}: el DNI no puede ser el de un padre/apoderado.")
        responsable = str(solicitud.get("dni_responsable") or "")
        if responsable not in dni_padres:
            errores.append("El responsable de la matrícula debe ser uno de los padres/apoderados.")
        apoderado = str(solicitud.get("dni_apoderado") or "")
        if apoderado and apoderado not in dni_padres:
            errores.append("El apoderado debe estar registrado en la solicitud.")
        return errores

    # Los pasos 4 y 5 (documentos, OCR y resumen) se completan en la fase 5.
    return errores


def _ya_matriculado(dni: str, anio: int) -> bool:
    """Consulta en la BD si el alumno ya tiene matrícula en ese año (§13.2 punto 9)."""
    from app import db  # importación diferida: la bandeja no exige BD para borradores

    fila = db.query_uno(
        "SELECT 1 AS existe FROM MATRICULA WHERE DNI_Estudiante = %s "
        "AND `AñoEscolar` = %s",
        (str(dni), anio),
    )
    return fila is not None


def _solicitudes_guardadas(id_actual: str, anio: int) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    for carpeta in sorted(_base().iterdir()):
        if not carpeta.is_dir() or carpeta.name == id_actual:
            continue
        ruta = carpeta / "solicitud.json"
        if ruta.exists():
            try:
                datos = _leer_json(ruta)
            except ErrorApp:
                continue
            if datos.get("anio") == anio:
                resultados.append(datos)
    return resultados


def validar_para_enviar(solicitud: dict[str, Any]) -> list[str]:
    """Valida todos los pasos y las reglas de integridad antes del envío."""
    errores: list[str] = []
    for paso in (1, 2, 3):
        errores.extend(validar_paso(paso, solicitud))

    anio = solicitud.get("anio")
    dnis = [
        str(alumno.get("ficha", {}).get("DNI", ""))
        for alumno in solicitud.get("alumnos", [])
    ]
    if dnis:
        guardadas = _solicitudes_guardadas(str(solicitud.get("id", "")), anio)
        pendientes = [
            s for s in guardadas
            if s.get("estado") in ("Borrador", "Enviada", "Observada")
        ]
        for solicitud_guardada in pendientes:
            otros = [
                str(a.get("ficha", {}).get("DNI", ""))
                for a in solicitud_guardada.get("alumnos", [])
            ]
            repetidos = sorted(set(dnis) & set(otros))
            if repetidos:
                errores.append(
                    f"Ya existe una solicitud pendiente para el alumno {repetidos[0]}."
                )

    for dni in dnis:
        if _dni_valido(dni) and _ya_matriculado(dni, anio):
            errores.append(f"El alumno {dni} ya tiene matrícula en {anio}.")
    return errores


def enviar(id_solicitud: str) -> dict[str, Any]:
    """Pasa una solicitud de Borrador/Observada a Enviada tras validarla."""
    sesion = _exigir_padre()
    datos = obtener(id_solicitud)
    _verificar_propietario(datos, sesion)
    if datos["estado"] not in ("Borrador", "Observada"):
        raise ErrorValidacion(
            f"Una solicitud {datos['estado']} no puede enviarse nuevamente."
        )
    errores = validar_para_enviar(datos)
    if errores:
        raise ErrorValidacion("No se puede enviar la solicitud:\n- " + "\n- ".join(errores))
    datos["estado"] = "Enviada"
    datos["fecha_envio"] = datetime.now().isoformat(timespec="seconds")
    datos["historial"].append({
        "fecha": datos["fecha_envio"],
        "accion": "Envío de la solicitud",
        "usuario": str(sesion.dni),
    })
    guardar_solicitud(datos)
    return datos


# ------------------------------------------------------- acciones de secretaría
def observar(id_solicitud: str, texto: str, usuario: str | None = None) -> dict[str, Any]:
    """Agrega una observación y deja la solicitud en estado Observada (§6.3)."""
    sesion = _exigir_secretaria()
    datos = obtener(id_solicitud)
    if datos["estado"] != "Enviada":
        raise ErrorValidacion("Solo se puede observar una solicitud Enviada.")
    datos.setdefault("observaciones", []).append({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "de": usuario or sesion.nombre_usuario,
        "texto": texto,
    })
    datos["estado"] = "Observada"
    guardar_solicitud(datos)
    return datos


def _mover_carpeta(id_solicitud: str, origen: str, destino: str) -> None:
    """Mueve la carpeta de bandeja; falla si otra persona la está procesando."""
    src = carpeta_solicitud(id_solicitud, origen)
    dst = carpeta_solicitud(id_solicitud, destino)
    if not src.exists():
        raise ErrorConflicto(f"No existe la carpeta de la solicitud {id_solicitud}.")
    if dst.exists():
        raise ErrorConflicto(
            f"La solicitud {id_solicitud} ya fue procesada en {destino}."
        )
    os.rename(src, dst)


def rechazar(
    id_solicitud: str, motivo: str, usuario: str | None = None
) -> dict[str, Any]:
    """Rechaza una solicitud y la mueve a la bandeja de rechazadas."""
    sesion = _exigir_secretaria()
    if carpeta_solicitud(id_solicitud, "rechazadas").exists():
        raise ErrorConflicto(f"La solicitud {id_solicitud} ya fue rechazada.")
    datos = obtener(id_solicitud)
    if datos["estado"] not in ("Enviada", "Observada"):
        raise ErrorValidacion("Solo se puede rechazar una solicitud Enviada u Observada.")
    datos["estado"] = "Rechazada"
    datos.setdefault("observaciones", []).append({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "de": usuario or sesion.nombre_usuario,
        "texto": f"Rechazada: {motivo}",
    })
    _mover_carpeta(id_solicitud, "pendientes", "rechazadas")
    guardar_solicitud(datos, "rechazadas")
    return datos


def aprobar(id_solicitud: str, usuario_dni: str | None = None) -> dict[str, Any]:
    """Marca la solicitud como Aprobada y la mueve a aprobadas/ (§6.3)."""
    sesion = _exigir_secretaria()
    if carpeta_solicitud(id_solicitud, "aprobadas").exists():
        raise ErrorConflicto(f"La solicitud {id_solicitud} ya fue aprobada.")
    datos = obtener(id_solicitud)
    if datos["estado"] != "Enviada":
        raise ErrorValidacion("Solo se puede aprobar una solicitud Enviada.")
    datos["estado"] = "Aprobada"
    datos["aprobado_por"] = usuario_dni or sesion.dni
    datos["fecha_aprobacion"] = datetime.now().isoformat(timespec="seconds")
    _mover_carpeta(id_solicitud, "pendientes", "aprobadas")
    guardar_solicitud(datos, "aprobadas")
    return datos


# ------------------------------------------------------------------ documentos
def copiar_documento(
    origen: Path | str, id_solicitud: str, nombre_generado: str | None = None
) -> str:
    """Copia un documento a la carpeta de la solicitud con nombre generado."""
    origen = Path(origen)
    extension = origen.suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ErrorValidacion(
            f"Extensión no permitida: {extension}. Use {sorted(EXTENSIONES_PERMITIDAS)}."
        )
    if not origen.is_file() or origen.stat().st_size > TAMANIO_MAXIMO_BYTES:
        raise ErrorValidacion("El documento no existe o supera los 5 MB permitidos.")
    nombre = nombre_generado or (uuid.uuid4().hex + extension)
    destino = carpeta_solicitud(id_solicitud) / "docs" / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(origen.read_bytes())
    return str(destino.relative_to(SOLICITUDES_DIR.parent.parent))


def adjuntar_documento(
    id_solicitud: str, origen: Path | str, indice_alumno: int = 0, tipo: str = "dni"
) -> str:
    """Guarda un adjunto y lo registra en el JSON de la solicitud."""
    datos = obtener(id_solicitud)
    if datos["estado"] not in ("Borrador", "Observada"):
        raise ErrorValidacion("Solo se pueden adjuntar documentos a una solicitud editable.")
    ruta = copiar_documento(origen, id_solicitud)
    if tipo == "dni":
        datos["alumnos"][indice_alumno]["docs"]["dni"] = ruta
    elif tipo == "constancia":
        datos["alumnos"][indice_alumno]["docs"]["constancia"] = ruta
    else:
        raise ErrorValidacion(f"Tipo de documento desconocido: {tipo}.")
    guardar_solicitud(datos)
    return ruta


def agregar_alumno(datos: dict[str, Any]) -> dict[str, Any]:
    """Agrega un hermano a la solicitud, respetando el máximo de seis."""
    if len(datos.get("alumnos", [])) >= MAXIMO_ALUMNOS:
        raise ErrorValidacion(f"Una solicitud admite como máximo {MAXIMO_ALUMNOS} alumnos.")
    alumno = nuevo_alumno()
    alumno["ficha"]["LugarQueOcupa"] = len(datos.get("alumnos", [])) + 1
    datos.setdefault("alumnos", []).append(alumno)
    return alumno


def quitar_alumno(datos: dict[str, Any], indice: int) -> None:
    """Quita un alumno de la solicitud por su índice (basado en cero)."""
    alumnos = datos.get("alumnos", [])
    if not 0 <= indice < len(alumnos):
        raise ErrorValidacion("No existe ese alumno en la solicitud.")
    alumnos.pop(indice)
    for posicion, alumno in enumerate(alumnos, 1):
        alumno["ficha"]["LugarQueOcupa"] = posicion


def resumen(datos: dict[str, Any]) -> list[tuple[str, str]]:
    """Devuelve un resumen legible de la solicitud para el último paso."""
    filas: list[tuple[str, str]] = [
        ("Identificador", str(datos.get("id", ""))),
        ("Año escolar", str(datos.get("anio", ""))),
        ("Alumnos", str(len(datos.get("alumnos", [])))),
        ("Responsable", str(datos.get("dni_responsable") or "-")),
    ]
    for indice, alumno in enumerate(datos.get("alumnos", []), 1):
        ficha = alumno.get("ficha", {})
        destino = alumno.get("destino", {})
        filas.append((
            f"Alumno {indice}",
            f"{ficha.get('Nombres', '')} {ficha.get('ApellidoPaterno', '')} "
            f"({ficha.get('DNI', '')}) → {destino.get('nivel', '')} "
            f"{destino.get('grado', '')}",
        ))
    return filas
