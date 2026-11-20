"""Punto de entrada del aplicativo de escritorio de Registro de Matricula.

Flujo de arranque (§4):
1. Lee config.ini. Si no existe o la conexion falla -> abre el asistente de conexion.
2. Si la conexion es exitosa -> muestra la ventana principal (login en fases siguientes).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from app.config import config
from app.db import conectar, version
from app.ui.asistente_conexion import AsistenteConexion


def conexion_ok() -> bool:
    try:
        conectar()
        return True
    except Exception:
        return False


def iniciar_aplicacion() -> None:
    root = tk.Tk()
    root.title("Registro de Matricula")
    root.geometry("600x400")

    marco = tk.Frame(root, padx=40, pady=40)
    marco.pack(expand=True, fill="both")

    tk.Label(marco, text="Registro de Matricula", font=("Segoe UI", 16, "bold")).pack(pady=10)
    tk.Label(marco, text="Aplicativo de escritorio sin frameworks.").pack(pady=5)

    try:
        ver = version()
        tk.Label(marco, text=f"MySQL: {ver}").pack(pady=5)
        tk.Label(marco, text=f"Base de datos: {config.database}").pack(pady=5)
        tk.Label(marco, text="Estado: conectado").pack(pady=5, fg="green")
    except Exception as exc:
        tk.Label(marco, text=f"Error de conexion: {exc}").pack(pady=5, fg="red")

    def salir():
        root.destroy()

    tk.Button(marco, text="Salir", command=salir).pack(pady=20)
    root.mainloop()


def main() -> None:
    if not config.__dict__.get("database") or not conexion_ok():
        AsistenteConexion().mainloop()
    else:
        iniciar_aplicacion()


if __name__ == "__main__":
    main()
