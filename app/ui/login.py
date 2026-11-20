"""Pantalla de login (§6.1).

- Usuario y clave; mensaje genérico si falla (no decir cuál dato falló).
- Bloqueo temporal tras 5 intentos fallidos (30 s).
- Usuarios Inactivos no pueden entrar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.servicios import auth


class VentanaLogin(tk.Toplevel):
    def __init__(self, parent, exito_callback):
        super().__init__(parent)
        self.title("Registro de Matrícula - Inicio de sesión")
        self.resizable(False, False)
        self.exito_callback = exito_callback
        self._construir_ui()
        self._refrescar_estado()

    def _construir_ui(self):
        marco = ttk.Frame(self, padding=25)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="Registro de Matrícula", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        ttk.Label(marco, text="Usuario").pack(anchor="w")
        self.ent_usuario = ttk.Entry(marco, width=30)
        self.ent_usuario.pack(fill="x", pady=(0, 10))

        ttk.Label(marco, text="Clave").pack(anchor="w")
        self.ent_clave = ttk.Entry(marco, width=30, show="*")
        self.ent_clave.pack(fill="x", pady=(0, 10))
        self.ent_clave.bind("<Return>", lambda _e: self.ingresar())

        self.lbl_bloqueo = ttk.Label(marco, text="", foreground="#a31a1a")
        self.lbl_bloqueo.pack(pady=(0, 8))

        self.btn_ingresar = ttk.Button(marco, text="Ingresar", command=self.ingresar)
        self.btn_ingresar.pack(fill="x")

        self.lbl_msg = ttk.Label(marco, text="", foreground="#1a7a1a")
        self.lbl_msg.pack(pady=(10, 0))

        marco.columnconfigure(0, weight=1)

    def _refrescar_estado(self):
        if auth.autenticacion.esta_bloqueado():
            segs = auth.autenticacion.segundos_restantes_bloqueo()
            self.lbl_bloqueo.config(
                text=f"Demasiados intentos fallidos. Bloqueado {segs}s más.",
                foreground="#a31a1a",
            )
            self.ent_usuario.config(state="disabled")
            self.ent_clave.config(state="disabled")
            self.btn_ingresar.config(state="disabled")
        else:
            self.lbl_bloqueo.config(text="")
            self.ent_usuario.config(state="normal")
            self.ent_clave.config(state="normal")
            self.btn_ingresar.config(state="normal")
        self.after(1000, self._refrescar_estado)

    def ingresar(self):
        usuario = self.ent_usuario.get().strip()
        clave = self.ent_clave.get()
        if not usuario or not clave:
            self.lbl_msg.config(text="Ingrese usuario y clave.", foreground="#a31a1a")
            return

        resultado = auth.login(usuario, clave)
        if resultado.exito:
            self.lbl_msg.config(text=resultado.mensaje, foreground="#1a7a1a")
            self.after(600, lambda: self.exito_callback())
        else:
            self.lbl_msg.config(text=resultado.mensaje, foreground="#a31a1a")
            self.ent_clave.delete(0, "end")
            self.ent_clave.focus()


def abrir_login(parent, exito_callback):
    dlg = VentanaLogin(parent, exito_callback)
    dlg.transient(parent)
    dlg.grab_set()
    parent.wait_window(dlg)
