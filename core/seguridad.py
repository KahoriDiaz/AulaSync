"""Hash de contraseñas, sesión del usuario y control de roles."""
from __future__ import annotations

from dataclasses import dataclass

from werkzeug.security import check_password_hash, generate_password_hash

from core.errores import ErrorPermiso

ROLES = ("Padre", "Secretaria", "Administrador")


@dataclass(frozen=True)
class Sesion:
    id_usuario: int
    nombre_usuario: str
    rol: str
    dni: str
    nombres: str
    apellidos: str

    @property
    def es_padre(self) -> bool:
        return self.rol == "Padre"

    @property
    def es_secretaria(self) -> bool:
        return self.rol == "Secretaria"

    @property
    def es_administrador(self) -> bool:
        return self.rol == "Administrador"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()


_sesion_actual: Sesion | None = None


def generar_hash(clave: str) -> str:
    return generate_password_hash(clave)


def verificar_hash(clave: str, hash_guardado: str) -> bool:
    return check_password_hash(hash_guardado, clave)


def iniciar_sesion(sesion: Sesion) -> None:
    global _sesion_actual
    _sesion_actual = sesion


def cerrar_sesion() -> None:
    global _sesion_actual
    _sesion_actual = None


def sesion_actual() -> Sesion | None:
    return _sesion_actual


def sesion_requerida() -> Sesion:
    if _sesion_actual is None:
        raise ErrorPermiso("Debe iniciar sesión para realizar esta operación.")
    return _sesion_actual


def requerir_roles(*roles: str) -> Sesion:
    sesion = sesion_requerida()
    if sesion.rol not in roles:
        raise ErrorPermiso("No tiene permiso para realizar esta operación.")
    return sesion


def requerir_secretaria() -> Sesion:
    return requerir_roles("Secretaria", "Administrador")
