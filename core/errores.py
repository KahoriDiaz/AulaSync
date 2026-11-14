"""Errores de la aplicación y traducción de errores de MySQL."""
from __future__ import annotations


class ErrorApp(Exception):
    """Error controlado que se muestra al usuario."""


class ErrorValidacion(ErrorApp):
    """Dato inválido ingresado por el usuario."""


class ErrorPermiso(ErrorApp):
    """El usuario no tiene permiso para la operación."""


class ErrorBaseDatos(ErrorApp):
    """Error de base de datos ya traducido a español."""


class ErrorConflicto(ErrorApp):
    """El archivo de la solicitud cambió desde que se leyó; vuelva a cargarlo."""


_MENSAJES_MYSQL = {
    1451: "No se puede eliminar el registro porque está siendo utilizado por otros datos.",
    1452: "El dato relacionado no existe. Verifique la información ingresada.",
    1062: "Ya existe un registro con esos datos (valor duplicado).",
    3819: "Los datos no cumplen el formato permitido. Revise lo ingresado.",
    4025: "Los datos no cumplen una restricción de validación. Revise lo ingresado.",
}


def traducir_error(exc: BaseException) -> str:
    """Convierte una excepción de MySQL en un mensaje claro en español."""
    errno = getattr(exc, "errno", None)
    if errno is None:
        args = getattr(exc, "args", ())
        if args and isinstance(args[0], int):
            errno = args[0]
    mensaje = getattr(exc, "msg", None)
    if mensaje is None and getattr(exc, "args", ()):
        mensaje = exc.args[-1] if isinstance(exc.args[-1], str) else None
    if errno == 1644:
        return str(mensaje or "La operación no cumple una regla del negocio.")
    if errno in _MENSAJES_MYSQL:
        return _MENSAJES_MYSQL[errno]
    if isinstance(mensaje, str) and mensaje:
        return mensaje
    return "Ocurrió un error al acceder a la base de datos."
