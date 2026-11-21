"""Configuración del mantenimiento (CRUD) de las tablas del modelo.

Cada tabla declara su consulta de listado (SELECT), sus campos y los
procedimientos de insertar, actualizar y eliminar con el orden exacto de sus
parámetros (ver sql/03_procedimientos.sql). Python no escribe directo: solo
llama a ``CALL sp_...`` mediante ``db.call_proc``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from app import db
from app.errores import ErrorValidacion
from app.servicios.matricula import LUGAR_SUSCRIPCION, NIVELES, SECCIONES, SITUACIONES_FINALES

TODOS_LOS_GRADOS = tuple(sorted({g for grados in NIVELES.values() for g in grados}))
TODAS_LAS_SECCIONES = tuple(sorted({s for secciones in SECCIONES.values() for s in secciones}))


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    tipo: str = "texto"          # texto | dni | lista | fecha | numero
    valores: tuple[str, ...] = ()
    obligatorio: bool = True
    clave_primaria: bool = False  # no editable al modificar
    solo_lectura: bool = False    # se muestra, pero no se escribe (p. ej. Id autonumérico)


@dataclass(frozen=True)
class TablaCrud:
    titulo: str
    nombre: str                   # "contacto", "logro"... para los mensajes
    consulta: str
    columnas: tuple[str, ...]
    campos: tuple[Campo, ...]
    sp_insertar: str | None
    parametros_insertar: tuple[str, ...]
    sp_eliminar: str | None
    parametros_eliminar: tuple[str, ...]
    sp_actualizar: str | None = None
    parametros_actualizar: tuple[str, ...] = ()
    actualizar_especial: Callable[[dict[str, Any], dict[str, Any]], None] | None = field(default=None)
    campos_editables: tuple[str, ...] = ()   # si no está vacío, solo estos se editan

    @property
    def permite_editar(self) -> bool:
        return bool(self.sp_actualizar or self.actualizar_especial)


def _vacio_a_none(valor: Any) -> Any:
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _actualizar_matricula(anterior: dict[str, Any], nuevo: dict[str, Any]) -> None:
    """La matrícula solo cambia de estado o de sección (procedimientos propios)."""
    dni, anio = anterior["DNI_Estudiante"], int(anterior["AñoEscolar"])
    if nuevo.get("Estado") and nuevo["Estado"] != anterior.get("Estado"):
        db.call_proc("sp_actualizar_estado_matricula", (dni, anio, nuevo["Estado"]))
    if nuevo.get("Seccion") and nuevo["Seccion"] != anterior.get("Seccion"):
        db.call_proc("sp_cambiar_seccion", (dni, anio, nuevo["Seccion"]))


TABLAS: dict[str, TablaCrud] = {
    "contacto": TablaCrud(
        titulo="Contacto de emergencia", nombre="contacto de emergencia",
        consulta="SELECT IdContactoEmergencia, NombreContactoEmergencia, CelularEmergencia "
                 "FROM CONTACTO_EMERGENCIA ORDER BY IdContactoEmergencia",
        columnas=("IdContactoEmergencia", "NombreContactoEmergencia", "CelularEmergencia"),
        campos=(
            Campo("IdContactoEmergencia", "Id (automático)", clave_primaria=True, solo_lectura=True,
                  obligatorio=False),
            Campo("NombreContactoEmergencia", "Nombre del contacto"),
            Campo("CelularEmergencia", "Celular (9 dígitos)"),
        ),
        sp_insertar="sp_contacto_insertar",
        parametros_insertar=("NombreContactoEmergencia", "CelularEmergencia"),
        sp_actualizar="sp_contacto_actualizar",
        parametros_actualizar=("IdContactoEmergencia", "NombreContactoEmergencia", "CelularEmergencia"),
        sp_eliminar="sp_contacto_eliminar", parametros_eliminar=("IdContactoEmergencia",),
    ),
    "ie": TablaCrud(
        titulo="Institución educativa", nombre="institución educativa",
        consulta="SELECT CodigoModularIE, NombreIE, TipoIE FROM INSTITUCION_EDUCATIVA ORDER BY NombreIE",
        columnas=("CodigoModularIE", "NombreIE", "TipoIE"),
        campos=(
            Campo("CodigoModularIE", "Código modular", clave_primaria=True),
            Campo("NombreIE", "Nombre", obligatorio=False),
            Campo("TipoIE", "Tipo", "lista", ("", "Estatal", "Particular"), obligatorio=False),
        ),
        sp_insertar="sp_ie_insertar", parametros_insertar=("CodigoModularIE", "NombreIE", "TipoIE"),
        sp_actualizar="sp_ie_actualizar", parametros_actualizar=("CodigoModularIE", "NombreIE", "TipoIE"),
        sp_eliminar="sp_ie_eliminar", parametros_eliminar=("CodigoModularIE",),
    ),
    "constancia": TablaCrud(
        titulo="Constancia de logros", nombre="constancia",
        consulta="SELECT CodigoVirtual, DNI_Estudiante, NivelEducativo, FechaHoraEmision "
                 "FROM CONSTANCIA_LOGROS ORDER BY DNI_Estudiante",
        columnas=("CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision"),
        campos=(
            Campo("CodigoVirtual", "Código virtual (8 caracteres)", clave_primaria=True),
            Campo("DNI_Estudiante", "DNI del estudiante", "dni"),
            Campo("NivelEducativo", "Nivel educativo", "lista", tuple(NIVELES)),
            Campo("FechaHoraEmision", "Fecha de emisión", "fecha", obligatorio=False),
        ),
        sp_insertar="sp_constancia_insertar",
        parametros_insertar=("CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision"),
        sp_actualizar="sp_constancia_actualizar",
        parametros_actualizar=("CodigoVirtual", "DNI_Estudiante", "NivelEducativo", "FechaHoraEmision"),
        sp_eliminar="sp_constancia_eliminar", parametros_eliminar=("CodigoVirtual",),
    ),
    "logro": TablaCrud(
        titulo="Logro", nombre="logro",
        consulta="SELECT CodigoVirtual, `AñoEscolar`, GradoCursado, CodigoModularIE, SituacionFinal "
                 "FROM LOGRO ORDER BY CodigoVirtual, `AñoEscolar`",
        columnas=("CodigoVirtual", "AñoEscolar", "GradoCursado", "CodigoModularIE", "SituacionFinal"),
        campos=(
            Campo("CodigoVirtual", "Código virtual", clave_primaria=True),
            Campo("AñoEscolar", "Año escolar", "numero", clave_primaria=True),
            Campo("GradoCursado", "Grado cursado", "lista", TODOS_LOS_GRADOS),
            Campo("CodigoModularIE", "Código modular de la I.E."),
            Campo("SituacionFinal", "Situación final", "lista", SITUACIONES_FINALES),
        ),
        sp_insertar="sp_logro_insertar",
        parametros_insertar=("CodigoVirtual", "AñoEscolar", "GradoCursado", "CodigoModularIE", "SituacionFinal"),
        sp_actualizar="sp_logro_actualizar",
        parametros_actualizar=("CodigoVirtual", "AñoEscolar", "GradoCursado", "CodigoModularIE", "SituacionFinal"),
        sp_eliminar="sp_logro_eliminar", parametros_eliminar=("CodigoVirtual", "AñoEscolar"),
    ),
    "matricula": TablaCrud(
        titulo="Matrícula", nombre="matrícula",
        consulta="SELECT DNI_Estudiante, `AñoEscolar`, Nivel, Grado, Seccion, Estado, "
                 "LugarSuscripcion, FechaSuscripcion, DNI_Responsable, DNI_Secretaria "
                 "FROM MATRICULA ORDER BY `AñoEscolar` DESC, Nivel, Grado, Seccion",
        columnas=("DNI_Estudiante", "AñoEscolar", "Nivel", "Grado", "Seccion", "Estado",
                  "LugarSuscripcion", "FechaSuscripcion", "DNI_Responsable", "DNI_Secretaria"),
        campos=(
            Campo("DNI_Estudiante", "DNI del estudiante", "dni", clave_primaria=True),
            Campo("AñoEscolar", "Año escolar", "numero", clave_primaria=True),
            Campo("Nivel", "Nivel", "lista", tuple(NIVELES)),
            Campo("Grado", "Grado", "lista", TODOS_LOS_GRADOS),
            Campo("Seccion", "Sección", "lista", TODAS_LAS_SECCIONES),
            Campo("Estado", "Estado", "lista", ("Matriculado", "Retirado", "Trasladado")),
            Campo("LugarSuscripcion", "Lugar de suscripción (por defecto Virtual)", obligatorio=False),
            Campo("FechaSuscripcion", "Fecha de suscripción (por defecto hoy)", "fecha", obligatorio=False),
            Campo("DNI_Responsable", "DNI del responsable", "dni"),
        ),
        sp_insertar="sp_registrar_matricula",
        parametros_insertar=("DNI_Estudiante", "AñoEscolar", "Nivel", "Grado", "Seccion",
                             "DNI_Responsable", "DNI_Secretaria", "LugarSuscripcion", "FechaSuscripcion"),
        actualizar_especial=_actualizar_matricula,
        campos_editables=("Estado", "Seccion"),
        sp_eliminar="sp_eliminar_matricula", parametros_eliminar=("DNI_Estudiante", "AñoEscolar"),
    ),
    "tiene_padres": TablaCrud(
        titulo="Tiene padres", nombre="relación estudiante-padre",
        consulta="SELECT tp.DNI_Estudiante, tp.DNI_Padre, "
                 "CONCAT(p.ApellidoPaterno, ' ', p.ApellidoMaterno, ', ', p.Nombres) AS Padre "
                 "FROM TIENE_PADRES tp INNER JOIN PADRE_APODERADO p ON p.DNI = tp.DNI_Padre "
                 "ORDER BY tp.DNI_Estudiante",
        columnas=("DNI_Estudiante", "DNI_Padre", "Padre"),
        campos=(
            Campo("DNI_Estudiante", "DNI del estudiante", "dni", clave_primaria=True),
            Campo("DNI_Padre", "DNI del padre o madre", "dni", clave_primaria=True),
        ),
        sp_insertar="sp_tiene_padres_insertar", parametros_insertar=("DNI_Estudiante", "DNI_Padre"),
        sp_eliminar="sp_tiene_padres_eliminar", parametros_eliminar=("DNI_Estudiante", "DNI_Padre"),
    ),
    "hermandad": TablaCrud(
        titulo="Hermandad", nombre="relación de hermandad",
        consulta="SELECT DNI_HermanoA, DNI_HermanoB FROM HERMANDAD ORDER BY DNI_HermanoA",
        columnas=("DNI_HermanoA", "DNI_HermanoB"),
        campos=(
            Campo("DNI_HermanoA", "DNI del hermano A", "dni", clave_primaria=True),
            Campo("DNI_HermanoB", "DNI del hermano B", "dni", clave_primaria=True),
        ),
        sp_insertar="sp_hermandad_insertar", parametros_insertar=("DNI_HermanoA", "DNI_HermanoB"),
        sp_eliminar="sp_hermandad_eliminar", parametros_eliminar=("DNI_HermanoA", "DNI_HermanoB"),
    ),
    "nee": TablaCrud(
        titulo="Necesidades educativas especiales", nombre="necesidad educativa especial",
        consulta="SELECT DNI_Estudiante, NecesidadEducativaEspecial FROM ESTUDIANTE_NEE "
                 "ORDER BY DNI_Estudiante",
        columnas=("DNI_Estudiante", "NecesidadEducativaEspecial"),
        campos=(
            Campo("DNI_Estudiante", "DNI del estudiante", "dni", clave_primaria=True),
            Campo("NecesidadEducativaEspecial", "Necesidad educativa especial", clave_primaria=True),
        ),
        sp_insertar="sp_nee_insertar", parametros_insertar=("DNI_Estudiante", "NecesidadEducativaEspecial"),
        sp_eliminar="sp_nee_eliminar", parametros_eliminar=("DNI_Estudiante", "NecesidadEducativaEspecial"),
    ),
    "hermanos_ie": TablaCrud(
        titulo="Hermanos en la I.E.", nombre="registro de hermanos en la I.E.",
        consulta="SELECT DNI_Estudiante, NivelHermano FROM ESTUDIANTE_HERMANOS_IE ORDER BY DNI_Estudiante",
        columnas=("DNI_Estudiante", "NivelHermano"),
        campos=(
            Campo("DNI_Estudiante", "DNI del estudiante", "dni", clave_primaria=True),
            Campo("NivelHermano", "Nivel del hermano", "lista", tuple(NIVELES), clave_primaria=True),
        ),
        sp_insertar="sp_hermanos_ie_insertar", parametros_insertar=("DNI_Estudiante", "NivelHermano"),
        sp_eliminar="sp_hermanos_ie_eliminar", parametros_eliminar=("DNI_Estudiante", "NivelHermano"),
    ),
    "secretaria": TablaCrud(
        titulo="Secretaria", nombre="secretaria",
        consulta="SELECT DNI, Nombres, ApellidoPaterno, ApellidoMaterno FROM SECRETARIA "
                 "ORDER BY ApellidoPaterno, ApellidoMaterno",
        columnas=("DNI", "Nombres", "ApellidoPaterno", "ApellidoMaterno"),
        campos=(
            Campo("DNI", "DNI", "dni", clave_primaria=True),
            Campo("Nombres", "Nombres"),
            Campo("ApellidoPaterno", "Apellido paterno"),
            Campo("ApellidoMaterno", "Apellido materno"),
        ),
        sp_insertar="sp_secretaria_insertar",
        parametros_insertar=("DNI", "Nombres", "ApellidoPaterno", "ApellidoMaterno"),
        sp_actualizar="sp_secretaria_actualizar",
        parametros_actualizar=("DNI", "Nombres", "ApellidoPaterno", "ApellidoMaterno"),
        sp_eliminar="sp_secretaria_eliminar", parametros_eliminar=("DNI",),
    ),
}


def listar(clave: str) -> list[dict[str, Any]]:
    return db.query(TABLAS[clave].consulta)


def _validar(tabla: TablaCrud, valores: dict[str, Any], campos: tuple[str, ...]) -> None:
    errores = []
    for campo in tabla.campos:
        if campo.clave not in campos or campo.solo_lectura:
            continue
        valor = str(valores.get(campo.clave) or "").strip()
        if campo.obligatorio and not valor:
            errores.append(f"Falta: {campo.etiqueta}.")
        elif valor and campo.tipo == "dni" and not (valor.isdigit() and len(valor) == 8):
            errores.append(f"{campo.etiqueta}: debe tener 8 dígitos.")
        elif valor and campo.tipo == "numero" and not valor.isdigit():
            errores.append(f"{campo.etiqueta}: debe ser un número.")
    if errores:
        raise ErrorValidacion("\n".join(errores))


def _preparar(clave: str, valores: dict[str, Any]) -> dict[str, Any]:
    datos = {k: _vacio_a_none(v) for k, v in valores.items()}
    if clave == "constancia" and datos.get("FechaHoraEmision"):
        datos["FechaHoraEmision"] = str(datos["FechaHoraEmision"])[:10] + " 00:00:00"
    if clave in ("constancia", "logro") and datos.get("CodigoVirtual"):
        datos["CodigoVirtual"] = str(datos["CodigoVirtual"]).upper()
    return datos


def insertar(clave: str, valores: dict[str, Any], dni_secretaria: str | None = None) -> None:
    tabla = TABLAS[clave]
    _validar(tabla, valores, tabla.parametros_insertar)
    datos = _preparar(clave, valores)
    if clave == "matricula":
        datos["DNI_Secretaria"] = dni_secretaria
        datos["LugarSuscripcion"] = datos.get("LugarSuscripcion") or LUGAR_SUSCRIPCION
        datos["FechaSuscripcion"] = datos.get("FechaSuscripcion") or date.today().isoformat()
    db.call_proc(tabla.sp_insertar, tuple(datos.get(c) for c in tabla.parametros_insertar))


def actualizar(clave: str, anterior: dict[str, Any], valores: dict[str, Any]) -> None:
    tabla = TABLAS[clave]
    if not tabla.permite_editar:
        raise ErrorValidacion(f"La tabla {tabla.titulo} no se modifica: elimine y vuelva a crear el registro.")
    if tabla.actualizar_especial:
        tabla.actualizar_especial(anterior, _preparar(clave, valores))
        return
    _validar(tabla, valores, tabla.parametros_actualizar)
    datos = _preparar(clave, {**anterior, **valores})
    db.call_proc(tabla.sp_actualizar, tuple(datos.get(c) for c in tabla.parametros_actualizar))


def eliminar(clave: str, fila: dict[str, Any]) -> None:
    tabla = TABLAS[clave]
    db.call_proc(tabla.sp_eliminar, tuple(_vacio_a_none(fila.get(c)) for c in tabla.parametros_eliminar))
