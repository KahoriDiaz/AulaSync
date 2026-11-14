"""Registro, inicio de sesión y administración de cuentas de usuario."""
from __future__ import annotations

import time
from typing import Any

from core import seguridad
from core.db import consultar, consultar_uno, ejecutar
from core.errores import ErrorBaseDatos, ErrorValidacion
from core.formatos import (
    normalizar_nombre,
    validar_dni,
)

_MAX_INTENTOS = 5
_BLOQUEO_SEGUNDOS = 5 * 60
_fallos: dict[str, list[float]] = {}


def _validar_clave(clave: str, confirmacion: str) -> None:
    if not clave or len(clave) < 8:
        raise ErrorValidacion("La contraseña debe tener al menos 8 caracteres.")
    if clave != confirmacion:
        raise ErrorValidacion("Las contraseñas no coinciden.")


def _validar_usuario(nombre_usuario: str) -> str:
    texto = (nombre_usuario or "").strip()
    if len(texto) < 3:
        raise ErrorValidacion("El nombre de usuario debe tener al menos 3 caracteres.")
    if len(texto) > 30:
        raise ErrorValidacion("El nombre de usuario no puede superar los 30 caracteres.")
    if not all(c.isalnum() or c in "._-" for c in texto):
        raise ErrorValidacion(
            "El nombre de usuario solo puede contener letras, números, punto, guion y guion bajo."
        )
    return texto


def _existe(nombre_usuario: str, dni: str) -> None:
    if consultar_uno("SELECT IdUsuario FROM USUARIO WHERE NombreUsuario = %s", (nombre_usuario,)):
        raise ErrorValidacion("Ese nombre de usuario ya está en uso.")
    if consultar_uno("SELECT IdUsuario FROM USUARIO WHERE DNI = %s", (dni,)):
        raise ErrorValidacion("Ya existe una cuenta registrada con ese DNI.")


def registrar_padre(
    dni: str,
    nombres: str,
    apellidos: str,
    nombre_usuario: str,
    clave: str,
    confirmacion: str,
) -> int:
    """Registro autónomo de una cuenta de padre/madre/apoderado."""
    dni = validar_dni(dni)
    nombres = normalizar_nombre(nombres)
    apellidos = normalizar_nombre(apellidos)
    if not nombres or not apellidos:
        raise ErrorValidacion("Los nombres y apellidos son obligatorios.")
    usuario = _validar_usuario(nombre_usuario)
    _validar_clave(clave, confirmacion)
    _existe(usuario, dni)
    return ejecutar(
        "INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI, Nombres, Apellidos) "
        "VALUES (%s, %s, 'Padre', 'Activo', %s, %s, %s)",
        (usuario, seguridad.generar_hash(clave), dni, nombres, apellidos),
    )


def crear_usuario_rol(
    nombre_usuario: str,
    rol: str,
    dni: str,
    nombres: str,
    apellidos: str,
    clave: str,
    confirmacion: str,
) -> int:
    """Crea una cuenta de Secretaria o Administrador (para crear_usuario.py)."""
    if rol not in ("Secretaria", "Administrador"):
        raise ErrorValidacion("El rol debe ser Secretaria o Administrador.")
    dni = validar_dni(dni)
    nombres = normalizar_nombre(nombres)
    apellidos = normalizar_nombre(apellidos)
    usuario = _validar_usuario(nombre_usuario)
    _validar_clave(clave, confirmacion)
    _existe(usuario, dni)
    return ejecutar(
        "INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI, Nombres, Apellidos) "
        "VALUES (%s, %s, %s, 'Activo', %s, %s, %s)",
        (usuario, seguridad.generar_hash(clave), rol, dni, nombres, apellidos),
    )


def actualizar_hash_si_existe(
    nombre_usuario: str, dni: str, rol: str, nombres: str, apellidos: str, clave: str
) -> bool:
    """Actualiza el hash de una cuenta existente si coincide con el DNI indicado."""
    dni = validar_dni(dni)
    fila = consultar_uno(
        "SELECT IdUsuario, DNI FROM USUARIO WHERE NombreUsuario = %s", (nombre_usuario,)
    )
    if not fila:
        return False
    if fila["DNI"] != dni:
        raise ErrorValidacion("El usuario ya existe, pero su DNI no coincide con el indicado.")
    ejecutar(
        "UPDATE USUARIO SET ClaveHash = %s, Rol = %s, Nombres = %s, Apellidos = %s "
        "WHERE IdUsuario = %s",
        (
            seguridad.generar_hash(clave),
            rol,
            normalizar_nombre(nombres),
            normalizar_nombre(apellidos),
            fila["IdUsuario"],
        ),
    )
    return True


def _bloqueado(nombre_usuario: str) -> float:
    registros = _fallos.get(nombre_usuario, [])
    ahora = time.monotonic()
    registros = [instante for instante in registros if ahora - instante < _BLOQUEO_SEGUNDOS]
    _fallos[nombre_usuario] = registros
    if len(registros) >= _MAX_INTENTOS:
        return _BLOQUEO_SEGUNDOS - (ahora - registros[-1])
    return 0.0


def _registrar_fallo(nombre_usuario: str) -> None:
    _fallos.setdefault(nombre_usuario, []).append(time.monotonic())


def iniciar_sesion(nombre_usuario: str, clave: str) -> seguridad.Sesion:
    usuario = (nombre_usuario or "").strip()
    espera = _bloqueado(usuario)
    if espera > 0:
        minutos = max(1, int(espera // 60) + 1)
        raise ErrorValidacion(
            f"Demasiados intentos fallidos. Espere {minutos} minuto(s) e intente de nuevo."
        )
    fila = consultar_uno(
        "SELECT IdUsuario, NombreUsuario, ClaveHash, Rol, Estado, DNI, Nombres, Apellidos "
        "FROM USUARIO WHERE NombreUsuario = %s",
        (usuario,),
    )
    if not fila or not seguridad.verificar_hash(clave or "", fila["ClaveHash"]):
        _registrar_fallo(usuario)
        raise ErrorValidacion("Usuario o contraseña incorrectos.")
    if fila["Estado"] != "Activo":
        raise ErrorValidacion("La cuenta está inactiva. Contacte al administrador.")
    ejecutar("UPDATE USUARIO SET UltimoAcceso = NOW() WHERE IdUsuario = %s", (fila["IdUsuario"],))
    _fallos.pop(usuario, None)
    sesion = seguridad.Sesion(
        id_usuario=int(fila["IdUsuario"]),
        nombre_usuario=fila["NombreUsuario"],
        rol=fila["Rol"],
        dni=fila["DNI"],
        nombres=fila["Nombres"],
        apellidos=fila["Apellidos"],
    )
    seguridad.iniciar_sesion(sesion)
    return sesion


def cerrar_sesion() -> None:
    seguridad.cerrar_sesion()


def listar_usuarios() -> list[dict[str, Any]]:
    seguridad.requerir_roles("Administrador")
    return consultar(
        "SELECT IdUsuario, NombreUsuario, Rol, Estado, DNI, Nombres, Apellidos, "
        "FechaRegistro, UltimoAcceso FROM USUARIO ORDER BY Apellidos, Nombres"
    )


def cambiar_estado(id_usuario: int, estado: str) -> None:
    seguridad.requerir_roles("Administrador")
    if estado not in ("Activo", "Inactivo"):
        raise ErrorValidacion("El estado debe ser Activo o Inactivo.")
    sesion = seguridad.sesion_requerida()
    if sesion.id_usuario == id_usuario and estado == "Inactivo":
        raise ErrorValidacion("No puede desactivar su propia cuenta.")
    try:
        ejecutar("UPDATE USUARIO SET Estado = %s WHERE IdUsuario = %s", (estado, id_usuario))
    except ErrorBaseDatos as exc:
        raise ErrorBaseDatos(str(exc)) from exc
