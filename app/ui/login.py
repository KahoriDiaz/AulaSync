"""Pantalla de login (§6.1) para secretaria.

- DNI y clave; mensaje genérico si falla (no decir cuál dato falló).
- Bloqueo temporal tras 5 intentos fallidos (30 s).
- Usuarios Inactivos no pueden entrar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.errores import ErrorApp
from app.servicios import auth
from app.ui.componentes import entry_dni
from app.ui.tema import EXITO, PELIGRO, aplicar_tema, separador, tarjeta


class VentanaLogin(tk.Toplevel):
    def __init__(self, parent, exito_callback):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Ingreso de secretaria")
        self.resizable(False, False)
        self.exito_callback = exito_callback
        self._construir_ui()
        self._refrescar_estado()

    def _construir_ui(self):
        marco = ttk.Frame(self, padding=22)
        marco.pack(fill="both", expand=True)

        tarjeta_marca = tarjeta(marco)
        tarjeta_marca.pack(fill="x", pady=(0, 12))
        ttk.Label(tarjeta_marca, text="AulaSync", style="Card.Titulo.TLabel").pack(anchor="w")
        separador(tarjeta_marca).pack(fill="x", pady=(10, 0))

        tarjeta_formulario = tarjeta(marco)
        tarjeta_formulario.pack(fill="both", expand=True)
        tarjeta_formulario.columnconfigure(0, weight=1)

        ttk.Label(tarjeta_formulario, text="DNI (8 dígitos)", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.ent_dni = entry_dni(tarjeta_formulario, width=32)
        self.ent_dni.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(tarjeta_formulario, text="Clave", style="Card.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        self.ent_clave = ttk.Entry(tarjeta_formulario, width=32, show="*")
        self.ent_clave.grid(row=3, column=0, sticky="ew", pady=(2, 8))
        self.ent_clave.bind("<Return>", lambda _e: self.ingresar())

        self.lbl_bloqueo = ttk.Label(
            tarjeta_formulario, text="", foreground=PELIGRO, style="Card.Muted.TLabel"
        )
        self.lbl_bloqueo.grid(row=4, column=0, sticky="w", pady=(0, 6))

        self.btn_ingresar = ttk.Button(
            tarjeta_formulario, text="Ingresar", style="Primary.TButton",
            command=self.ingresar,
        )
        self.btn_ingresar.grid(row=5, column=0, sticky="ew")

        self.lbl_msg = ttk.Label(
            tarjeta_formulario, text="", foreground=EXITO, style="Card.Muted.TLabel"
        )
        self.lbl_msg.grid(row=7, column=0, sticky="w", pady=(10, 0))

    def _refrescar_estado(self):
        if auth.autenticacion.esta_bloqueado():
            segs = auth.autenticacion.segundos_restantes_bloqueo()
            self.lbl_bloqueo.config(
                text=f"Demasiados intentos fallidos. Bloqueado {segs}s más.",
                foreground=PELIGRO,
            )
            self.ent_dni.config(state="disabled")
            self.ent_clave.config(state="disabled")
            self.btn_ingresar.config(state="disabled")
        else:
            self.lbl_bloqueo.config(text="")
            self.ent_dni.config(state="normal")
            self.ent_clave.config(state="normal")
            self.btn_ingresar.config(state="normal")
        self.after(1000, self._refrescar_estado)

    def ingresar(self):
        dni = self.ent_dni.get().strip()
        clave = self.ent_clave.get()
        if not dni or not clave:
            self.lbl_msg.config(text="Ingrese DNI y clave.", foreground=PELIGRO)
            return

        try:
            resultado = auth.login(dni, clave)
        except ErrorApp as exc:
            # Error de conexión o de consulta: se informa sin cerrar el login.
            self.lbl_msg.config(text=str(exc), foreground=PELIGRO)
            return
        if resultado.exito:
            self.lbl_msg.config(text=resultado.mensaje, foreground=EXITO)
            self.after(600, lambda: self.exito_callback())
        else:
            self.lbl_msg.config(text=resultado.mensaje, foreground=PELIGRO)
            self.ent_clave.delete(0, "end")
            self.ent_clave.focus()
