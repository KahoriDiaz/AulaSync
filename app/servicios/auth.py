"""Autenticación de usuarios de secretaria (§6.1, §13.4).

- Login con DNI y clave; mensaje genérico si falla (no decir cuál dato falló).
- Comparación de hash con hmac.compare_digest (sin timing attack).
- Registro de acceso (sp_usuario_registrar_acceso).
- Usuarios Inactivos no pueden entrar.
- Bloqueo temporal en memoria tras 5 intentos fallidos (30 s).
Todo el acceso a datos usa SELECT y CALL sp_... (sin escrituras directas en Python).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from app import db
from app.config import config
from app.errores import ErrorBaseDatos, ErrorValidacion
from app.sesion import (
    INTENTOS_MAXIMOS,
    TIEMPO_BLOQUEO_SEGUNDOS,
    Sesion,
    autenticacion,
)
from app.seguridad import hash_clave, verificar_clave

DNI_RE = re.compile(r"^[0-9]{8}$")


@dataclass
class Intento:
    exito: bool
    mensaje: str
    segundos_bloqueo: int = 0


class ErrorAuth(Exception):
    pass


def login(dni: str, clave_texto: str) -> Intento:
    """Intenta iniciar sesión con DNI y clave. Devuelve un Intento con el resultado."""
    if autenticacion.esta_bloqueado():
        return Intento(
            False,
            "Demasiados intentos fallidos. Intente de nuevo en "
            f"{autenticacion.segundos_restantes_bloqueo()} segundos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    if not DNI_RE.fullmatch(dni or ""):
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "DNI o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    fila = db.query_uno(
        "SELECT u.IdUsuario, u.NombreUsuario, u.ClaveHash, u.Rol, u.Estado, u.DNI, "
        "s.Nombres, s.ApellidoPaterno, s.ApellidoMaterno "
        "FROM USUARIO u "
        "INNER JOIN SECRETARIA s ON u.DNI = s.DNI "
        "WHERE u.DNI = %s",
        (dni,),
    )

    # Mensaje genérico tanto si no existe el usuario como si la clave es wrong.
    if fila is None:
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "DNI o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    if fila["Estado"] != "Activo":
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "DNI o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    if not verificar_clave(clave_texto, fila["ClaveHash"]):
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "DNI o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    # Éxito: registrar acceso y crear sesión.
    try:
        db.call_proc("sp_usuario_registrar_acceso", (fila["IdUsuario"],))
    except Exception:
        # No fallar el login por un error al registrar el acceso.
        pass

    apellidos = str(fila.get("ApellidoPaterno", "") or "") + " " + str(fila.get("ApellidoMaterno", "") or "")
    sesion = Sesion(
        id_usuario=int(fila["IdUsuario"]),
        nombre_usuario=str(fila["NombreUsuario"]),
        rol=str(fila["Rol"]),
        dni=str(fila["DNI"]),
        nombres=str(fila.get("Nombres", "") or ""),
        apellidos=apellidos.strip(),
    )
    autenticacion.iniciar_sesion(sesion)
    return Intento(True, "Bienvenido, " + fila["Nombres"] + ".")


def logout() -> None:
    autenticacion.cerrar_sesion()


def sesion_actual() -> Optional[Sesion]:
    return autenticacion.sesion_activa
