"""Punto de entrada del aplicativo AulaSync.

Con el MySQL portátil de la entrega (carpeta mysql/) la base se enciende y se
prepara sola y se abre directo el login. Sin él, se usa un MySQL instalado y,
si hace falta, el asistente de conexión.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from app import servidor_bd
from app.config import config
from app.db import conectar
from app.ui.tema import PantallaCarga, aplicar_tema


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


def lanzar_login() -> bool:
    """Muestra el login; devuelve True si la secretaria ingresó correctamente."""
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
    return acceso["exito"]


def ejecutar_sesiones() -> None:
    """Alterna login y ventana principal hasta que el usuario salga.

    "Cerrar sesión" vuelve al login; cerrar la ventana o "Salir" termina.
    """
    from app.ui.ventana_principal import abrir_ventana_principal

    while lanzar_login():
        if not abrir_ventana_principal():
            break


def iniciar_base_portatil() -> bool:
    """Enciende el MySQL portátil mostrando una pantalla de carga; False si falla."""
    raiz = tk.Tk()
    aplicar_tema(raiz)
    raiz.withdraw()
    carga = PantallaCarga(raiz, "Iniciando la base de datos...")
    resultado: dict[str, object] = {}

    def trabajar():
        try:
            servidor_bd.iniciar(lambda texto: raiz.after(0, carga.var_mensaje.set, texto))
        except Exception as exc:  # se muestra al usuario
            resultado["error"] = exc
        raiz.after(0, raiz.quit)

    threading.Thread(target=trabajar, daemon=True).start()
    raiz.mainloop()
    carga.destroy()
    error = resultado.get("error")
    if error:
        messagebox.showerror("AulaSync", f"No se pudo iniciar la base de datos:\n{error}",
                             parent=raiz)
    raiz.destroy()
    return error is None


def main() -> None:
    if servidor_bd.disponible():
        try:
            if iniciar_base_portatil():
                ejecutar_sesiones()
        finally:
            servidor_bd.detener()
        return

    if not config.database or not conexion_valida() or not base_datos_valida():
        from app.ui.asistente_conexion import AsistenteConexion

        asistente = AsistenteConexion()
        asistente.mainloop()

        # Si el usuario cierra el asistente sin completar la instalación,
        # no continuar al login.
        if not conexion_valida() or not base_datos_valida():
            return

    ejecutar_sesiones()


if __name__ == "__main__":
    main()
