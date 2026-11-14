"""Matrículas y verificación de grado (procedimientos almacenados)."""
from __future__ import annotations

from datetime import date
from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, llamar_procedimiento
from core.errores import ErrorValidacion
from core.formatos import (
    ESTADOS_MATRICULA,
    NIVELES,
    grados_de_nivel,
    validar_dni,
    validar_grado,
    normalizar_nivel,
    validar_opcion,
)


def _anio(valor: Any, campo: str = "año escolar") -> int:
    try:
        anio = int(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion(f"El {campo} debe ser un número de 4 dígitos.") from exc
    if anio < 2000 or anio > 2100:
        raise ErrorValidacion("El año escolar no es válido.")
    return anio


def listar_matriculas(
    anio: int | None = None,
    nivel: str | None = None,
    grado: str | None = None,
    seccion: str | None = None,
    estado: str | None = None,
    filtro: str = "",
) -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    condiciones: list[str] = []
    parametros: list[Any] = []
    if anio:
        condiciones.append("m.AñoEscolar = %s")
        parametros.append(_anio(anio))
    if nivel:
        condiciones.append("m.Nivel = %s")
        parametros.append(normalizar_nivel(nivel))
    if grado:
        condiciones.append("m.Grado = %s")
        parametros.append(grado)
    if seccion:
        condiciones.append("m.Seccion = %s")
        parametros.append(seccion)
    if estado:
        condiciones.append("m.Estado = %s")
        parametros.append(validar_opcion(estado, ESTADOS_MATRICULA, "estado"))
    if filtro.strip():
        texto = f"%{filtro.strip()}%"
        condiciones.append(
            "(e.DNI LIKE %s OR e.Nombres LIKE %s OR e.ApellidoPaterno LIKE %s "
            "OR e.ApellidoMaterno LIKE %s)"
        )
        parametros.extend([texto, texto, texto, texto])
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return consultar(
        "SELECT m.*, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres "
        "FROM MATRICULA m INNER JOIN ESTUDIANTE e ON e.DNI = m.DNI_Estudiante "
        f"{where} ORDER BY m.AñoEscolar DESC, m.Nivel, m.Grado, m.Seccion, e.ApellidoPaterno",
        tuple(parametros),
    )


def obtener_matricula(dni: str, anio: int) -> dict[str, Any] | None:
    return consultar_uno(
        "SELECT * FROM MATRICULA WHERE DNI_Estudiante = %s AND AñoEscolar = %s",
        (validar_dni(dni), _anio(anio)),
    )


def contar_matriculados(anio: int, nivel: str, grado: str, seccion: str) -> int:
    fila = consultar_uno(
        "SELECT COUNT(*) AS total FROM MATRICULA WHERE AñoEscolar = %s AND Nivel = %s "
        "AND Grado = %s AND Seccion = %s AND Estado = 'Matriculado'",
        (_anio(anio), normalizar_nivel(nivel), grado, seccion),
    )
    return int(fila["total"]) if fila else 0


def registrar_matricula(
    dni_estudiante: str,
    anio: int,
    nivel: str,
    grado: str,
    seccion: str,
    dni_responsable: str,
    lugar: str,
    fecha: date | str | None = None,
) -> None:
    sesion = seguridad.requerir_secretaria()
    dni_estudiante = validar_dni(dni_estudiante, "DNI del estudiante")
    dni_responsable = validar_dni(dni_responsable, "DNI del responsable")
    nivel = normalizar_nivel(nivel)
    grado = validar_grado(nivel, grado)
    seccion = str(seccion or "").strip().upper()
    if not seccion or len(seccion) > 5:
        raise ErrorValidacion("La sección es obligatoria y debe tener hasta 5 caracteres.")
    lugar = str(lugar or "").strip()
    if not lugar:
        raise ErrorValidacion("El lugar de suscripción es obligatorio.")
    if isinstance(fecha, date):
        fecha_texto = fecha.isoformat()
    else:
        fecha_texto = str(fecha or date.today().isoformat())
    llamar_procedimiento(
        "sp_registrar_matricula",
        (
            dni_estudiante,
            _anio(anio),
            nivel,
            grado,
            seccion,
            dni_responsable,
            sesion.dni,
            lugar[:30],
            fecha_texto,
        ),
    )


def cambiar_estado(dni_estudiante: str, anio: int, estado: str) -> None:
    seguridad.requerir_secretaria()
    estado = validar_opcion(estado, ESTADOS_MATRICULA, "estado")
    llamar_procedimiento(
        "sp_actualizar_estado_matricula",
        (validar_dni(dni_estudiante), _anio(anio), estado),
    )


def buscar_estudiantes(
    apellido_paterno: str = "", apellido_materno: str = "", nombres: str = ""
) -> list[dict[str, Any]]:
    resultados = llamar_procedimiento(
        "sp_buscar_estudiante", (apellido_paterno, apellido_materno, nombres)
    )
    return resultados[0] if resultados else []


def listar_hermanos(dni: str) -> list[dict[str, Any]]:
    resultados = llamar_procedimiento("sp_listar_hermanos", (validar_dni(dni),))
    return resultados[0] if resultados else []


def verificar_matriculados(anio_anterior: int, anio_actual: int) -> dict[str, Any]:
    anterior = _anio(anio_anterior, "año anterior")
    actual = _anio(anio_actual, "año actual")
    resultados = llamar_procedimiento("sp_verificar_matriculados", (anterior, actual))
    filas = resultados[0] if resultados else []
    resumen = {"Total": len(filas), "Continúa": 0, "Sin matrícula en el año actual": 0, "Nuevo": 0}
    for fila in filas:
        situacion = fila.get("Situacion")
        if situacion in resumen:
            resumen[situacion] += 1
    return {"filas": filas, "resumen": resumen, "anio_anterior": anterior, "anio_actual": actual}


def _siguiente_grado(nivel: str, grado: str) -> tuple[str, str] | None:
    grados = grados_de_nivel(nivel)
    if grado not in grados:
        return None
    indice = grados.index(grado)
    if indice + 1 < len(grados):
        return nivel, grados[indice + 1]
    if nivel == "Inicial":
        return "Primaria", "1.°"
    if nivel == "Primaria":
        return "Secundaria", "1.°"
    return None


def verificar_grado(dni: str, anio: int) -> dict[str, Any]:
    """Calcula la edad al 31 de marzo y el grado que corresponde."""
    dni = validar_dni(dni, "DNI del estudiante")
    anio = _anio(anio)
    fila = consultar_uno(
        "SELECT DNI, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento "
        "FROM ESTUDIANTE WHERE DNI = %s",
        (dni,),
    )
    if not fila:
        return {
            "dni": dni, "fecha_nacimiento": None, "edad": None, "nivel": None,
            "grado": None, "situacion": None, "estado": "Error",
            "mensaje": "El estudiante no está registrado.",
        }
    nacimiento = fila["FechaNacimiento"]
    if isinstance(nacimiento, str):
        nacimiento = date.fromisoformat(nacimiento)
    edad = anio - nacimiento.year
    if (nacimiento.month, nacimiento.day) > (3, 31):
        edad -= 1

    if 3 <= edad <= 5:
        return {
            "dni": dni, "fecha_nacimiento": nacimiento.isoformat(), "edad": edad,
            "nivel": "Inicial", "grado": f"{edad} a.", "situacion": None,
            "estado": "Correcto",
            "mensaje": f"Le corresponde Inicial {edad} a. (edad cumplida al 31 de marzo: {edad}).",
        }

    logro = consultar_uno(
        "SELECT c.NivelEducativo, l.AñoEscolar, l.GradoCursado, l.SituacionFinal "
        "FROM CONSTANCIA_LOGROS c INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual "
        "WHERE c.DNI_Estudiante = %s ORDER BY l.AñoEscolar DESC, l.GradoCursado DESC LIMIT 1",
        (dni,),
    )
    base = {
        "dni": dni, "fecha_nacimiento": nacimiento.isoformat(), "edad": edad,
        "situacion": logro["SituacionFinal"] if logro else None,
    }
    if not logro:
        return {
            **base, "nivel": None, "grado": None, "estado": "Advertencia",
            "mensaje": "Sin constancia de logros registrada.",
        }
    nivel = logro["NivelEducativo"]
    grado = logro["GradoCursado"]
    if logro["SituacionFinal"] == "REQUIERE RECUPERACIÓN":
        return {
            **base, "nivel": nivel, "grado": grado, "estado": "Advertencia",
            "mensaje": f"Pendiente de recuperación: corresponde repetir {nivel} {grado}.",
        }
    siguiente = _siguiente_grado(nivel, grado)
    if siguiente is None:
        return {
            **base, "nivel": nivel, "grado": None, "estado": "Error",
            "mensaje": "El estudiante egresó de Secundaria; no corresponde matrícula.",
        }
    nivel_siguiente, grado_siguiente = siguiente
    return {
        **base, "nivel": nivel_siguiente, "grado": grado_siguiente, "estado": "Correcto",
        "mensaje": f"Le corresponde {nivel_siguiente} {grado_siguiente}.",
    }
