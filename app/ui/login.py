"""Pantalla de login (§6.1) y alta de cuenta de padre/apoderado (fase A).

- Usuario y clave; mensaje genérico si falla (no decir cuál dato falló).
- Bloqueo temporal tras 5 intentos fallidos (30 s).
- Usuarios Inactivos no pueden entrar.
- El enlace "Crear cuenta..." abre un diálogo modal sobre el login, que sí
  es visible; por eso ``transient(self)`` es seguro aquí (no así con la raíz
  oculta de main.py).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.errores import ErrorApp
from app.servicios import auth
from app.ui.componentes import entry_dni
from app.ui.tema import EXITO, INFO, PELIGRO, aplicar_tema, separador, tarjeta


class DialogoCrearCuenta(tk.Toplevel):
    """Diálogo modal para registrar un padre/apoderado (fase A)."""

    def __init__(self, parent, al_crear):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Crear cuenta de padre/apoderado")
        self.resizable(False, False)
        self.al_crear = al_crear
        self.transient(parent)  # el login está visible
        self.grab_set()
        self._construir_ui()

    def _construir_ui(self) -> None:
        marco = ttk.Frame(self, padding=18)
        marco.pack(fill="both", expand=True)

        tarjeta_formulario = tarjeta(marco)
        tarjeta_formulario.pack(fill="both", expand=True)
        ttk.Label(
            tarjeta_formulario, text="Datos del apoderado", style="Card.Seccion.TLabel"
        ).pack(anchor="w", pady=(0, 6))
        separador(tarjeta_formulario).pack(fill="x", pady=(0, 12))

        self.campos: dict[str, ttk.Entry] = {}
        etiquetas = (
            ("dni", "DNI (8 dígitos)"),
            ("nombres", "Nombres y apellidos"),
            ("celular", "Celular (9 dígitos, empieza con 9)"),
            ("correo", "Correo electrónico"),
            ("usuario", "Usuario"),
        )
        for clave, texto in etiquetas:
            ttk.Label(tarjeta_formulario, text=texto, style="Card.TLabel").pack(anchor="w")
            fabrica = entry_dni if clave == "dni" else ttk.Entry
            entry = fabrica(tarjeta_formulario, width=34)
            entry.pack(fill="x", pady=(2, 8))
            self.campos[clave] = entry

        ttk.Label(
            tarjeta_formulario, text="Clave (mín. 8, letra y número)", style="Card.TLabel"
        ).pack(anchor="w")
        self.ent_clave = ttk.Entry(tarjeta_formulario, width=34, show="*")
        self.ent_clave.pack(fill="x", pady=(2, 8))

        ttk.Label(tarjeta_formulario, text="Confirmar clave", style="Card.TLabel").pack(anchor="w")
        self.ent_confirmar = ttk.Entry(tarjeta_formulario, width=34, show="*")
        self.ent_confirmar.pack(fill="x", pady=(2, 10))
        self.ent_confirmar.bind("<Return>", lambda _e: self.crear())

        self.lbl_msg = ttk.Label(
            tarjeta_formulario, text="", foreground=PELIGRO,
            style="Card.Muted.TLabel", wraplength=320,
        )
        self.lbl_msg.pack(fill="x", pady=(0, 8))

        botones = ttk.Frame(tarjeta_formulario, style="SobreTarjeta.TFrame")
        botones.pack(fill="x")
        ttk.Button(botones, text="Crear cuenta", style="Primary.TButton",
                   command=self.crear).pack(side="left", padx=(0, 6))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="left")
        self.campos["dni"].focus()

    def crear(self) -> None:
        valores = {clave: entry.get().strip() for clave, entry in self.campos.items()}
        clave = self.ent_clave.get()
        confirmar = self.ent_confirmar.get()
        errores = auth.validar_datos_registro(
            valores["dni"],
            valores["nombres"],
            valores["celular"],
            valores["correo"],
            valores["usuario"],
            clave,
            confirmar,
        )
        if errores:
            self.lbl_msg.config(text="\n".join(errores))
            return
        try:
            auth.registrar_padre(
                valores["dni"],
                valores["usuario"],
                clave,
                confirmar,
                valores["nombres"],
                valores["celular"],
                valores["correo"],
            )
        except ErrorApp as exc:
            self.lbl_msg.config(text=str(exc))
            return
        messagebox.showinfo(
            "Cuenta creada", "Cuenta creada. Ya puede iniciar sesión", parent=self
        )
        usuario = valores["usuario"]
        self.destroy()
        self.al_crear(usuario)


class VentanaLogin(tk.Toplevel):
    def __init__(self, parent, exito_callback):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync")
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

        ttk.Label(tarjeta_formulario, text="Usuario", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.ent_usuario = ttk.Entry(tarjeta_formulario, width=32)
        self.ent_usuario.grid(row=1, column=0, sticky="ew", pady=(2, 10))

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

        enlace = ttk.Label(
            tarjeta_formulario,
            text="Crear cuenta de padre/apoderado",
            foreground=INFO,
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
            background="#FFFFFF",
        )
        enlace.grid(row=6, column=0, pady=(12, 0))
        enlace.bind("<Button-1>", lambda _e: self.crear_cuenta())

        self.lbl_msg = ttk.Label(
            tarjeta_formulario, text="", foreground=EXITO, style="Card.Muted.TLabel"
        )
        self.lbl_msg.grid(row=7, column=0, sticky="w", pady=(10, 0))

    def crear_cuenta(self) -> None:
        DialogoCrearCuenta(self, self._usuario_creado)

    def _usuario_creado(self, usuario: str) -> None:
        self.ent_usuario.delete(0, "end")
        self.ent_usuario.insert(0, usuario)
        self.lbl_msg.config(text="Cuenta creada. Ya puede iniciar sesión.", foreground=EXITO)
        self.ent_clave.focus()

    def _refrescar_estado(self):
        if auth.autenticacion.esta_bloqueado():
            segs = auth.autenticacion.segundos_restantes_bloqueo()
            self.lbl_bloqueo.config(
                text=f"Demasiados intentos fallidos. Bloqueado {segs}s más.",
                foreground=PELIGRO,
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
            self.lbl_msg.config(text="Ingrese usuario y clave.", foreground=PELIGRO)
            return

        resultado = auth.login(usuario, clave)
        if resultado.exito:
            self.lbl_msg.config(text=resultado.mensaje, foreground=EXITO)
            self.after(600, lambda: self.exito_callback())
        else:
            self.lbl_msg.config(text=resultado.mensaje, foreground=PELIGRO)
            self.ent_clave.delete(0, "end")
            self.ent_clave.focus()
