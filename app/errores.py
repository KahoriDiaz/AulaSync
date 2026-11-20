"""Errores de la aplicacion y traduccion de errores de MySQL."""
from __future__ import annotations


class ErrorApp(Exception):
    """Error controlado que se muestra al usuario."""


class ErrorValidacion(ErrorApp):
    """Dato invalido ingresado por el usuario."""


class ErrorPermiso(ErrorApp):
    """El usuario no tiene permiso para la operacion."""


class ErrorBaseDatos(ErrorApp):
    """Error de base de datos ya traducido a espanol."""


class ErrorConflicto(ErrorApp):
    """El archivo de la solicitud cambio desde que se leyo; vuelva a cargarlo."""


_MENSAJES_MYSQL = {
    1451: "No se puede eliminar el registro porque esta siendo utilizado por otros datos.",
    1452: "El dato relacionado no existe. Verifique la informacion ingresada.",
    1062: "Ya existe un registro con esos datos (valor duplicado).",
    3819: "Los datos no cumplen el formato permitido. Revise lo ingresado.",
    4025: "Los datos no cumplen una restriccion de validacion. Revise lo ingresado.",
}


def traducir_error(exc: BaseException) -> str:
    """Convierte una excepcion de MySQL en un mensaje claro en espanol."""
    errno = getattr(exc, "errno", None)
    if errno is None:
        args = getattr(exc, "args", ())
        if args and isinstance(args[0], int):
            errno = args[0]
    mensaje = getattr(exc, "msg", None)
    if mensaje is None and getattr(exc, "args", ()):
        mensaje = exc.args[-1] if isinstance(exc.args[-1], str) else None
    if errno == 1644:
        return str(mensaje or "La operacion no cumple una regla del negocio.")
    if errno in _MENSAJES_MYSQL:
        return _MENSAJES_MYSQL[errno]
    if isinstance(mensaje, str) and mensaje:
        return mensaje
    return "Ocurrio un error al acceder a la base de datos."
