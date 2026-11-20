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


class DialogoCrearCuenta(tk.Toplevel):
    """Diálogo modal para registrar un padre/apoderado (fase A)."""

    def __init__(self, parent, al_crear):
        super().__init__(parent)
        self.title("AulaSync - Crear cuenta de padre/apoderado")
        self.resizable(False, False)
        self.al_crear = al_crear
        self.transient(parent)  # el login está visible
        self.grab_set()
        self._construir_ui()

    def _construir_ui(self) -> None:
        marco = ttk.Frame(self, padding=18)
        marco.pack(fill="both", expand=True)

        ttk.Label(
            marco, text="Datos del apoderado", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        self.campos: dict[str, ttk.Entry] = {}
        etiquetas = (
            ("dni", "DNI (8 dígitos)"),
            ("nombres", "Nombres y apellidos"),
            ("celular", "Celular (9 dígitos, empieza con 9)"),
            ("correo", "Correo electrónico"),
            ("usuario", "Usuario"),
        )
        for clave, texto in etiquetas:
            ttk.Label(marco, text=texto).pack(anchor="w")
            fabrica = entry_dni if clave == "dni" else ttk.Entry
            entry = fabrica(marco, width=34)
            entry.pack(fill="x", pady=(0, 8))
            self.campos[clave] = entry

        ttk.Label(marco, text="Clave (mín. 8, letra y número)").pack(anchor="w")
        self.ent_clave = ttk.Entry(marco, width=34, show="*")
        self.ent_clave.pack(fill="x", pady=(0, 8))

        ttk.Label(marco, text="Confirmar clave").pack(anchor="w")
        self.ent_confirmar = ttk.Entry(marco, width=34, show="*")
        self.ent_confirmar.pack(fill="x", pady=(0, 10))
        self.ent_confirmar.bind("<Return>", lambda _e: self.crear())

        self.lbl_msg = ttk.Label(marco, text="", foreground="#a31a1a", wraplength=320)
        self.lbl_msg.pack(fill="x", pady=(0, 8))

        botones = ttk.Frame(marco)
        botones.pack(fill="x")
        ttk.Button(botones, text="Crear cuenta", command=self.crear).pack(
            side="left", padx=(0, 6)
        )
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
        self.title("AulaSync")
        self.resizable(False, False)
        self.exito_callback = exito_callback
        self._construir_ui()
        self._refrescar_estado()

    def _construir_ui(self):
        marco = ttk.Frame(self, padding=25)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="AulaSync", font=("Segoe UI", 16, "bold")).pack(pady=(0, 10))

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

        enlace = ttk.Label(
            marco,
            text="Crear cuenta de padre/apoderado",
            foreground="#1256a0",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
        )
        enlace.pack(pady=(10, 0))
        enlace.bind("<Button-1>", lambda _e: self.crear_cuenta())

        self.lbl_msg = ttk.Label(marco, text="", foreground="#1a7a1a")
        self.lbl_msg.pack(pady=(10, 0))

        marco.columnconfigure(0, weight=1)

    def crear_cuenta(self) -> None:
        DialogoCrearCuenta(self, self._usuario_creado)

    def _usuario_creado(self, usuario: str) -> None:
        self.ent_usuario.delete(0, "end")
        self.ent_usuario.insert(0, usuario)
        self.lbl_msg.config(text="Cuenta creada. Ya puede iniciar sesión.", foreground="#1a7a1a")
        self.ent_clave.focus()

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
