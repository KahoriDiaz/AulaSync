"""Autenticación de usuarios (§6.1, §13.4).

- Login con usuario y clave; mensaje genérico si falla (no decir cuál dato falló).
- Comparación de hash con hmac.compare_digest (sin timing attack).
- Registro de acceso (sp_usuario_registrar_acceso).
- Usuarios Inactivos no pueden entrar.
- Bloqueo temporal en memoria tras 5 intentos fallidos (30 s).
Todo el acceso a datos usa SELECT y CALL sp_... (sin INSERT/UPDATE/DELETE en Python).
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
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

USUARIO_RE = re.compile(r"^[A-Za-z0-9._]{4,30}$")
CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


@dataclass
class Intento:
    exito: bool
    mensaje: str
    segundos_bloqueo: int = 0


class ErrorAuth(Exception):
    pass


def login(nombre_usuario: str, clave_texto: str) -> Intento:
    """Intenta iniciar sesión. Devuelve un Intento con el resultado."""
    if autenticacion.esta_bloqueado():
        return Intento(
            False,
            "Demasiados intentos fallidos. Intente de nuevo en "
            f"{autenticacion.segundos_restantes_bloqueo()} segundos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    fila = db.query_uno(
        "SELECT IdUsuario, NombreUsuario, ClaveHash, Rol, Estado, DNI "
        "FROM USUARIO WHERE NombreUsuario = %s",
        (nombre_usuario,),
    )

    # Mensaje genérico tanto si no existe el usuario como si la clave es wrong.
    if fila is None:
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "Usuario o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    if fila["Estado"] != "Activo":
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "Usuario o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    if not verificar_clave(clave_texto, fila["ClaveHash"]):
        autenticacion.registrar_intento_fallido()
        return Intento(
            False,
            "Usuario o clave incorrectos.",
            autenticacion.segundos_restantes_bloqueo(),
        )

    # Éxito: registrar acceso y crear sesión.
    try:
        db.call_proc("sp_usuario_registrar_acceso", (fila["IdUsuario"],))
    except Exception:
        # No fallar el login por un error al registrar el acceso.
        pass

    sesion = Sesion(
        id_usuario=int(fila["IdUsuario"]),
        nombre_usuario=str(fila["NombreUsuario"]),
        rol=str(fila["Rol"]),
        dni=str(fila["DNI"]),
        nombres="",
        apellidos="",
    )
    autenticacion.iniciar_sesion(sesion)
    return Intento(True, "Bienvenido, " + nombre_usuario + ".")


def logout() -> None:
    autenticacion.cerrar_sesion()


def sesion_actual() -> Optional[Sesion]:
    return autenticacion.sesion_activa


# ------------------------------------------------------- alta de padre (fase A)
def validar_datos_registro(
    dni: str,
    nombres: str,
    celular: str,
    correo: str,
    usuario: str,
    clave: str,
    confirmar_clave: str | None = None,
) -> list[str]:
    """Valida el formulario de creación de cuenta. Devuelve una lista de errores."""
    errores: list[str] = []
    dni = str(dni or "").strip()
    nombres = str(nombres or "").strip()
    celular = str(celular or "").strip()
    correo = str(correo or "").strip()
    usuario = str(usuario or "").strip()
    clave = clave or ""

    if not re.fullmatch(r"\d{8}", dni):
        errores.append("El DNI debe tener 8 dígitos.")
    if not nombres:
        errores.append("Ingrese los nombres y apellidos del apoderado.")
    if not re.fullmatch(r"9\d{8}", celular):
        errores.append("El celular debe tener 9 dígitos y empezar con 9.")
    if not CORREO_RE.fullmatch(correo):
        errores.append("Ingrese un correo electrónico válido.")
    if not USUARIO_RE.fullmatch(usuario):
        errores.append(
            "El usuario debe tener de 4 a 30 caracteres: letras, números, punto o guion bajo."
        )
    if len(clave) < 8 or not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
        errores.append(
            "La clave debe tener al menos 8 caracteres, una letra y un número."
        )
    if confirmar_clave is not None and clave != confirmar_clave:
        errores.append("La clave y la confirmación deben ser iguales.")
    return errores


def ruta_perfil(dni: str) -> Path:
    """Ruta del archivo de contacto del apoderado, junto a la aplicación."""
    return config.USER_DIR / "data" / "perfiles" / f"{str(dni).strip()}.json"


def guardar_perfil(
    dni: str, nombres: str, celular: str, correo: str
) -> Path:
    """Guarda los datos de contacto en un JSON atómico de uso exclusivo."""
    ruta = ruta_perfil(dni)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(
        json.dumps(
            {
                "dni": str(dni).strip(),
                "nombres_apoderado": str(nombres).strip(),
                "celular": str(celular).strip(),
                "correo": str(correo).strip(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        os.chmod(temporal, 0o600)  # mejor esfuerzo; en Windows no es vinculante
    except OSError:
        pass
    os.replace(temporal, ruta)
    return ruta


def leer_perfil(dni: str) -> dict[str, str]:
    """Lee el perfil guardado; devuelve un dict vacío si no existe o está dañado."""
    ruta = ruta_perfil(dni)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _traducir_registro(mensaje: str) -> str:
    texto = str(mensaje).lower()
    if "nombre de usuario ya existe" in texto:
        return "Ese nombre de usuario ya existe. Elija otro."
    if "dni ya tiene una cuenta" in texto:
        return "Ese DNI ya tiene una cuenta de usuario."
    if "dni de un padre no puede" in texto or "registrado en secretar" in texto:
        return "Ese DNI pertenece a una secretaria; no se puede registrar como padre."
    return str(mensaje)


def registrar_padre(
    dni: str,
    usuario: str,
    clave: str,
    confirmar_clave: str | None = None,
    nombres: str = "",
    celular: str = "",
    correo: str = "",
) -> None:
    """Crea una cuenta de Padre usando solo ``CALL sp_usuario_registrar``.

    El Rol lo fuerza el procedimiento; esta capa no recibe ni envía un rol.
    La clave se guarda únicamente como hash PBKDF2. El perfil de contacto se
    guarda aparte, en data/perfiles/, porque USUARIO no tiene esas columnas.
    """
    dni = str(dni or "").strip()
    usuario = str(usuario or "").strip()
    nombres = str(nombres or "").strip()
    celular = str(celular or "").strip()
    correo = str(correo or "").strip()

    errores = validar_datos_registro(
        dni, nombres, celular, correo, usuario, clave, confirmar_clave
    )
    if errores:
        raise ErrorValidacion("No se pudo crear la cuenta:\n- " + "\n- ".join(errores))

    try:
        # call_proc hace commit() si todo va bien y rollback() ante cualquier error.
        db.call_proc("sp_usuario_registrar", (usuario, hash_clave(clave), dni))
    except ErrorBaseDatos as exc:
        raise ErrorValidacion(_traducir_registro(str(exc))) from exc

    try:
        guardar_perfil(dni, nombres, celular, correo)
    except OSError:
        # El perfil es opcional: si no se puede grabar, la cuenta ya fue creada.
        pass
