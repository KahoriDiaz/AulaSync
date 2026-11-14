"""Crea una cuenta adicional de secretaria o administrador.

Uso:  python crear_usuario.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.errores import ErrorApp
from servicios import usuarios


def main() -> None:
    print("=== Crear cuenta de secretaria o administrador ===")
    usuario = input("Nombre de usuario: ").strip()
    rol = input("Rol (Secretaria/Administrador): ").strip().capitalize()
    dni = input("DNI: ").strip()
    nombres = input("Nombres: ").strip()
    apellidos = input("Apellidos: ").strip()
    clave = getpass.getpass("Contraseña: ")
    confirmacion = getpass.getpass("Confirme la contraseña: ")
    if clave != confirmacion:
        print("Las contraseñas no coinciden.")
        return
    try:
        creado = usuarios.actualizar_hash_si_existe(usuario, dni, rol, nombres, apellidos, clave)
        if creado:
            print(f"Se actualizó la contraseña de la cuenta '{usuario}'.")
        else:
            usuarios.crear_usuario_rol(usuario, rol, dni, nombres, apellidos, clave, confirmacion)
            print(f"Cuenta '{usuario}' creada con rol {rol}.")
    except ErrorApp as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
