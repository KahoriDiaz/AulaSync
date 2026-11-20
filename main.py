"""Punto de entrada del aplicativo de escritorio de Registro de Matrícula.

Flujo de arranque (§4):
1. Lee config.ini. Si no existe o la conexión falla → abre el asistente de conexión.
2. El asistente prueba la conexión y, opcionalmente, crea bd_matricula y carga
   los datos de prueba (guarda config.ini con matricula_app; la clave de root
   NO se guarda).
3. Luego muestra el login.
4. Tras el login, muestra la ventana principal según el rol.
"""
from __future__ import annotations

import tkinter as tk

from app.config import config
from app.db import conectar


def conexion_valida() -> bool:
    try:
        conectar()
        return True
    except Exception:
        return False


def lanzar_login() -> None:
    root = tk.Tk()
    root.withdraw()  # raíz oculta; el login es la ventana visible

    def al_exito():
        root.destroy()
        from app.ui.ventana_principal import abrir_ventana_principal

        abrir_ventana_principal()

    from app.ui.login import VentanaLogin

    dlg = VentanaLogin(root, al_exito)
    dlg.transient(root)
    dlg.grab_set()
    root.mainloop()


def main() -> None:
    if not config.database or not conexion_valida():
        from app.ui.asistente_conexion import AsistenteConexion

        AsistenteConexion().mainloop()
    lanzar_login()


if __name__ == "__main__":
    main()
