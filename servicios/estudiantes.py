"""Estudiantes (ESTUDIANTE), contacto de emergencia y vínculo con padres."""
from __future__ import annotations

from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar, ejecutar_filas, transaccion
from core.errores import ErrorValidacion
from core.formatos import (
    TIPOS_ATENCION,
    normalizar_nivel,
    normalizar_nombre,
    normalizar_sexo,
    validar_celular,
    validar_correo,
    validar_dni,
    validar_fecha_no_futura,
    validar_opcion,
    validar_si_no,
)

COLUMNAS = (
    "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno", "FechaNacimiento",
    "DistritoNacimiento", "ProvinciaNacimiento", "DepartamentoNacimiento", "PaisNacimiento",
    "DomicilioActual", "DistritoDomicilio", "Celular", "CorreoElectronico", "Religion",
    "LugarQueOcupa", "TipoAtencion", "EnfermedadCronica", "ViveConPadre", "ViveConMadre",
    "ElPadreVive", "LaMadreVive", "IdContactoEmergencia", "CodigoModularIE", "DNI_Apoderado",
)


def _texto(datos: dict[str, Any], campo: str, obligatorio: bool = True, maximo: int = 100) -> str | None:
    valor = str(datos.get(campo) or "").strip()
    if not valor:
        if obligatorio:
            raise ErrorValidacion(f"El campo {campo} es obligatorio.")
        return None
    if len(valor) > maximo:
        raise ErrorValidacion(f"El campo {campo} no puede superar {maximo} caracteres.")
    return valor


def _normalizar(datos: dict[str, Any]) -> dict[str, Any]:
    dni = validar_dni(datos.get("DNI"))
    try:
        lugar = int(datos.get("LugarQueOcupa") or 1)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion("El lugar que ocupa debe ser un número entero.") from exc
    if lugar < 1:
        raise ErrorValidacion("El lugar que ocupa debe ser mayor o igual a 1.")
    tipo_atencion = str(datos.get("TipoAtencion") or "").strip() or None
    if tipo_atencion:
        tipo_atencion = validar_opcion(tipo_atencion, TIPOS_ATENCION, "tipo de atención")
    contacto = datos.get("IdContactoEmergencia")
    if contacto is None or str(contacto).strip() == "":
        raise ErrorValidacion("Debe indicar un contacto de emergencia.")
    try:
        contacto_id = int(contacto)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion("El contacto de emergencia no es válido.") from exc
    codigo_ie = _texto(datos, "CodigoModularIE", obligatorio=False, maximo=10)
    apoderado = str(datos.get("DNI_Apoderado") or "").strip() or None
    if apoderado:
        apoderado = validar_dni(apoderado, "DNI del apoderado")
    return {
        "DNI": dni,
        "Sexo": normalizar_sexo(datos.get("Sexo")),
        "Nombres": normalizar_nombre(_texto(datos, "Nombres", maximo=50)),
        "ApellidoPaterno": normalizar_nombre(_texto(datos, "ApellidoPaterno", maximo=30)),
        "ApellidoMaterno": normalizar_nombre(_texto(datos, "ApellidoMaterno", maximo=30)),
        "FechaNacimiento": validar_fecha_no_futura(datos.get("FechaNacimiento")),
        "DistritoNacimiento": _texto(datos, "DistritoNacimiento", maximo=30),
        "ProvinciaNacimiento": _texto(datos, "ProvinciaNacimiento", maximo=30),
        "DepartamentoNacimiento": _texto(datos, "DepartamentoNacimiento", maximo=30),
        "PaisNacimiento": _texto(datos, "PaisNacimiento", maximo=30) or "Perú",
        "DomicilioActual": _texto(datos, "DomicilioActual", maximo=100),
        "DistritoDomicilio": _texto(datos, "DistritoDomicilio", maximo=30),
        "Celular": validar_celular(datos.get("Celular"), "celular", opcional=True),
        "CorreoElectronico": validar_correo(datos.get("CorreoElectronico"), "correo", opcional=True),
        "Religion": _texto(datos, "Religion", obligatorio=False, maximo=20),
        "LugarQueOcupa": lugar,
        "TipoAtencion": tipo_atencion,
        "EnfermedadCronica": _texto(datos, "EnfermedadCronica", obligatorio=False, maximo=50),
        "ViveConPadre": validar_si_no(datos.get("ViveConPadre", False), "vive con padre"),
        "ViveConMadre": validar_si_no(datos.get("ViveConMadre", False), "vive con madre"),
        "ElPadreVive": validar_si_no(datos.get("ElPadreVive", False), "el padre vive"),
        "LaMadreVive": validar_si_no(datos.get("LaMadreVive", False), "la madre vive"),
        "IdContactoEmergencia": contacto_id,
        "CodigoModularIE": codigo_ie,
        "DNI_Apoderado": apoderado,
    }


def _validar_referencias(valores: dict[str, Any], cursor=None) -> None:
    consulta = cursor.execute if cursor is not None else None

    def existe(sql: str, parametro: Any) -> bool:
        if cursor is not None:
            cursor.execute(sql, (parametro,))
            return cursor.fetchone() is not None
        return consultar_uno(sql, (parametro,)) is not None

    if not existe(
        "SELECT 1 FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = %s",
        valores["IdContactoEmergencia"],
    ):
        raise ErrorValidacion("El contacto de emergencia seleccionado no existe.")
    if valores["CodigoModularIE"] and not existe(
        "SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s",
        valores["CodigoModularIE"],
    ):
        raise ErrorValidacion("La institución educativa de procedencia no existe.")
    if valores["DNI_Apoderado"] and not existe(
        "SELECT 1 FROM PADRE_APODERADO WHERE DNI = %s", valores["DNI_Apoderado"]
    ):
        raise ErrorValidacion("El apoderado indicado no existe.")


def _insertar(cursor, valores: dict[str, Any]) -> None:
    cursor.execute(
        f"INSERT INTO ESTUDIANTE ({', '.join(COLUMNAS)}) VALUES ({', '.join(['%s'] * len(COLUMNAS))})",
        tuple(valores[c] for c in COLUMNAS),
    )


def _actualizar(cursor, valores: dict[str, Any]) -> None:
    asignaciones = ", ".join(f"{c}=%s" for c in COLUMNAS if c != "DNI")
    cursor.execute(
        f"UPDATE ESTUDIANTE SET {asignaciones} WHERE DNI=%s",
        tuple(valores[c] for c in COLUMNAS if c != "DNI") + (valores["DNI"],),
    )


def crear_estudiante(
    datos: dict[str, Any],
    contacto_nuevo: dict[str, Any] | None = None,
    padres: list[str] | None = None,
) -> str:
    seguridad.requerir_secretaria()
    if contacto_nuevo:
        nombre = _texto(contacto_nuevo, "NombreContactoEmergencia", maximo=110)
        celular = validar_celular(contacto_nuevo.get("CelularEmergencia"), "celular de emergencia")
        datos = dict(datos)
        datos.pop("IdContactoEmergencia", None)
    else:
        nombre = celular = None
    with transaccion() as cursor:
        if contacto_nuevo:
            cursor.execute(
                "INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia) "
                "VALUES (%s, %s)",
                (nombre, celular),
            )
            datos["IdContactoEmergencia"] = cursor.lastrowid
        valores = _normalizar(datos)
        _validar_referencias(valores, cursor)
        _insertar(cursor, valores)
        for dni_padre in padres or []:
            dni_padre = validar_dni(dni_padre, "DNI del padre")
            cursor.execute(
                "SELECT 1 FROM PADRE_APODERADO WHERE DNI = %s", (dni_padre,)
            )
            if cursor.fetchone() is None:
                raise ErrorValidacion(f"El padre con DNI {dni_padre} no existe.")
            cursor.execute(
                "INSERT INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES (%s, %s)",
                (valores["DNI"], dni_padre),
            )
    return valores["DNI"]


def obtener_estudiante(dni: str) -> dict[str, Any] | None:
    return consultar_uno(
        "SELECT e.*, c.NombreContactoEmergencia, c.CelularEmergencia "
        "FROM ESTUDIANTE e INNER JOIN CONTACTO_EMERGENCIA c "
        "ON c.IdContactoEmergencia = e.IdContactoEmergencia WHERE e.DNI = %s",
        (validar_dni(dni),),
    )


def listar_estudiantes(filtro: str = "") -> list[dict[str, Any]]:
    seguridad.requerir_secretaria()
    texto = f"%{filtro.strip()}%"
    return consultar(
        "SELECT e.*, c.NombreContactoEmergencia, c.CelularEmergencia "
        "FROM ESTUDIANTE e INNER JOIN CONTACTO_EMERGENCIA c "
        "ON c.IdContactoEmergencia = e.IdContactoEmergencia "
        "WHERE e.DNI LIKE %s OR e.Nombres LIKE %s OR e.ApellidoPaterno LIKE %s "
        "OR e.ApellidoMaterno LIKE %s ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres",
        (texto, texto, texto, texto),
    )


def actualizar_estudiante(
    dni: str,
    datos: dict[str, Any],
    contacto_nuevo: dict[str, Any] | None = None,
    padres: list[str] | None = None,
) -> None:
    seguridad.requerir_secretaria()
    actual = obtener_estudiante(dni)
    if not actual:
        raise ErrorValidacion("El estudiante no existe.")
    combinado = {**actual, **datos, "DNI": actual["DNI"]}
    with transaccion() as cursor:
        if contacto_nuevo:
            nombre = _texto(contacto_nuevo, "NombreContactoEmergencia", maximo=110)
            celular = validar_celular(
                contacto_nuevo.get("CelularEmergencia"), "celular de emergencia"
            )
            cursor.execute(
                "INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia) "
                "VALUES (%s, %s)",
                (nombre, celular),
            )
            combinado["IdContactoEmergencia"] = cursor.lastrowid
        valores = _normalizar(combinado)
        _validar_referencias(valores, cursor)
        _actualizar(cursor, valores)
        if padres is not None:
            cursor.execute("DELETE FROM TIENE_PADRES WHERE DNI_Estudiante = %s", (dni,))
            for dni_padre in padres:
                dni_padre = validar_dni(dni_padre, "DNI del padre")
                cursor.execute("SELECT 1 FROM PADRE_APODERADO WHERE DNI = %s", (dni_padre,))
                if cursor.fetchone() is None:
                    raise ErrorValidacion(f"El padre con DNI {dni_padre} no existe.")
                cursor.execute(
                    "INSERT INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES (%s, %s)",
                    (dni, dni_padre),
                )


def eliminar_estudiante(dni: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas("DELETE FROM ESTUDIANTE WHERE DNI = %s", (validar_dni(dni),))


def padres_de_estudiante(dni: str) -> list[dict[str, Any]]:
    return consultar(
        "SELECT p.* FROM TIENE_PADRES tp INNER JOIN PADRE_APODERADO p "
        "ON p.DNI = tp.DNI_Padre WHERE tp.DNI_Estudiante = %s "
        "ORDER BY p.ApellidoPaterno, p.ApellidoMaterno, p.Nombres",
        (validar_dni(dni),),
    )


def asignar_apoderado(dni: str, dni_apoderado: str | None) -> None:
    seguridad.requerir_secretaria()
    if dni_apoderado:
        validar_dni(dni_apoderado, "DNI del apoderado")
        if not consultar_uno("SELECT 1 FROM PADRE_APODERADO WHERE DNI = %s", (dni_apoderado,)):
            raise ErrorValidacion("El apoderado indicado no existe.")
    ejecutar(
        "UPDATE ESTUDIANTE SET DNI_Apoderado = %s WHERE DNI = %s",
        (dni_apoderado or None, validar_dni(dni)),
    )


def insertar_en_transaccion(cursor, valores: dict[str, Any]) -> None:
    _insertar(cursor, valores)


def actualizar_en_transaccion(cursor, valores: dict[str, Any]) -> None:
    _actualizar(cursor, valores)


def normalizar(datos: dict[str, Any]) -> dict[str, Any]:
    return _normalizar(datos)


def validar_referencias(valores: dict[str, Any], cursor=None) -> None:
    _validar_referencias(valores, cursor)


def listar_nee(dni: str) -> list[str]:
    filas = consultar(
        "SELECT NecesidadEducativaEspecial FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = %s "
        "ORDER BY NecesidadEducativaEspecial",
        (validar_dni(dni),),
    )
    return [fila["NecesidadEducativaEspecial"] for fila in filas]


def agregar_nee(dni: str, necesidad: str) -> None:
    seguridad.requerir_secretaria()
    texto = " ".join(str(necesidad or "").split())
    if not texto or len(texto) > 50:
        raise ErrorValidacion("La necesidad educativa debe tener entre 1 y 50 caracteres.")
    if not consultar_uno("SELECT 1 FROM ESTUDIANTE WHERE DNI = %s", (validar_dni(dni),)):
        raise ErrorValidacion("El estudiante no existe.")
    ejecutar(
        "INSERT INTO ESTUDIANTE_NEE (DNI_Estudiante, NecesidadEducativaEspecial) "
        "VALUES (%s, %s)",
        (validar_dni(dni), texto),
    )


def quitar_nee(dni: str, necesidad: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas(
        "DELETE FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = %s AND NecesidadEducativaEspecial = %s",
        (validar_dni(dni), necesidad),
    )


def listar_hermanos_ie(dni: str) -> list[str]:
    filas = consultar(
        "SELECT NivelHermano FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = %s "
        "ORDER BY NivelHermano",
        (validar_dni(dni),),
    )
    return [fila["NivelHermano"] for fila in filas]


def agregar_nivel_hermano(dni: str, nivel: str) -> None:
    seguridad.requerir_secretaria()
    nivel = normalizar_nivel(nivel)
    if not consultar_uno("SELECT 1 FROM ESTUDIANTE WHERE DNI = %s", (validar_dni(dni),)):
        raise ErrorValidacion("El estudiante no existe.")
    ejecutar(
        "INSERT INTO ESTUDIANTE_HERMANOS_IE (DNI_Estudiante, NivelHermano) VALUES (%s, %s)",
        (validar_dni(dni), nivel),
    )


def quitar_nivel_hermano(dni: str, nivel: str) -> None:
    seguridad.requerir_secretaria()
    ejecutar_filas(
        "DELETE FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = %s AND NivelHermano = %s",
        (validar_dni(dni), normalizar_nivel(nivel)),
    )
