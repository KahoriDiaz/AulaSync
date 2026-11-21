
"""Punto de entrada del aplicativo AulaSync."""
from __future__ import annotations

import tkinter as tk

from app.config import config
from app.db import conectar
from app.ui.tema import aplicar_tema


def conexion_valida() -> bool:
    try:
        cnx = conectar()
        cnx.close()
        return True
    except Exception:
        return False


def base_datos_valida() -> bool:
    try:
        cnx = conectar()
        cursor = cnx.cursor()
        cursor.execute("SHOW TABLES LIKE 'USUARIO'")
        existe = cursor.fetchone() is not None
        cursor.close()
        cnx.close()
        return existe
    except Exception:
        return False


def lanzar_login() -> None:
    root = tk.Tk()
    aplicar_tema(root)
    root.withdraw()

    acceso = {"exito": False}

    from app.ui.login import VentanaLogin

    def al_exito():
        acceso["exito"] = True
        dlg.destroy()
        root.quit()

    dlg = VentanaLogin(root, al_exito)

    # Cerrar el login finaliza su ciclo de eventos.
    dlg.protocol("WM_DELETE_WINDOW", root.quit)

    root.mainloop()
    root.destroy()

    # Abrir la ventana principal después de finalizar el login.
    if acceso["exito"]:
        from app.ui.ventana_principal import abrir_ventana_principal
        abrir_ventana_principal()


def main() -> None:
    if not config.database or not conexion_valida() or not base_datos_valida():
        from app.ui.asistente_conexion import AsistenteConexion

        asistente = AsistenteConexion()
        asistente.mainloop()

        # Si el usuario cierra el asistente sin completar la instalación,
        # no continuar al login.
        if not conexion_valida() or not base_datos_valida():
            return

    lanzar_login()


if __name__ == "__main__":
    main()
