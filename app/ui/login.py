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
from app.ui.componentes import entry_dni, poner_iconos
from app.ui.iconos import icono
from app.ui.tema import (
    ACENTO, BLANCO, EXITO, PRIMARIO, FUENTE, FUENTE_SUAVE, LATERAL, LATERAL_TEXTO, PELIGRO,
    SUPERFICIE, TEXTO_SUAVE, aplicar_tema, centrar,
)


class VentanaLogin(tk.Toplevel):
    def __init__(self, parent, exito_callback):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Ingreso de secretaria")
        self.resizable(False, False)
        self.exito_callback = exito_callback
        self._ingreso_exitoso = False
        self._tarea_refresco = None
        self._construir_ui()
        self._refrescar_estado()
        self.bind("<Destroy>", self._al_destruir, add="+")

    def _al_destruir(self, evento):
        if evento.widget is self and self._tarea_refresco:
            self.after_cancel(self._tarea_refresco)
            self._tarea_refresco = None

    def _construir_ui(self):
        contenedor = tk.Frame(self, bg=SUPERFICIE)
        contenedor.pack(fill="both", expand=True)

        # Panel de presentación (solo texto: sin imágenes ni logos).
        lateral = tk.Frame(contenedor, bg=LATERAL, width=330, padx=34, pady=40)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        tk.Label(lateral, text="AulaSync", bg=LATERAL, fg=BLANCO,
                 font=("Segoe UI", 28, "bold")).pack(anchor="w")
        tk.Label(lateral, text="Sistema de matrícula escolar", bg=LATERAL,
                 fg=LATERAL_TEXTO, font=("Segoe UI", 11)).pack(anchor="w", pady=(2, 0))
        tk.Frame(lateral, bg=ACENTO, height=3, width=56).pack(anchor="w", pady=(18, 18))
        for linea in ("Registro de estudiantes y familias",
                      "Matrícula con verificación de constancias",
                      "Consultas y reportes exportables"):
            tk.Label(lateral, text=linea, bg=LATERAL, fg=LATERAL_TEXTO,
                     font=FUENTE, anchor="w").pack(anchor="w", pady=3)
        tk.Label(lateral, text="Acceso exclusivo para secretarías", bg=LATERAL,
                 fg="#7FA9CB", font=FUENTE_SUAVE).pack(side="bottom", anchor="w")

        # Formulario.
        formulario = ttk.Frame(contenedor, style="SobreTarjeta.TFrame", padding=(44, 44, 44, 30))
        formulario.pack(side="left", fill="both", expand=True)
        formulario.columnconfigure(0, weight=1)

        ttk.Label(formulario, text="Iniciar sesión", style="Card.Titulo.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(formulario, text="Ingrese su DNI y su clave para continuar.",
                  style="Card.Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 22))

        ttk.Label(formulario, text="  DNI", style="Card.Seccion.TLabel",
                  image=icono(formulario, "id-card", 18, PRIMARIO), compound="left").grid(
            row=2, column=0, sticky="w")
        self.ent_dni = entry_dni(formulario, width=32, font=("Segoe UI", 11))
        self.ent_dni.grid(row=3, column=0, sticky="ew", pady=(4, 14))
        self.ent_dni.bind("<Return>", lambda _e: self.ent_clave.focus())

        ttk.Label(formulario, text="  Clave", style="Card.Seccion.TLabel",
                  image=icono(formulario, "lock", 18, PRIMARIO), compound="left").grid(
            row=4, column=0, sticky="w")
        self.ent_clave = ttk.Entry(formulario, width=32, show="*", font=("Segoe UI", 11))
        self.ent_clave.grid(row=5, column=0, sticky="ew", pady=(4, 6))
        self.ent_clave.bind("<Return>", lambda _e: self.ingresar())

        self.lbl_bloqueo = ttk.Label(
            formulario, text="", foreground=PELIGRO, style="Card.Muted.TLabel"
        )
        self.lbl_bloqueo.grid(row=6, column=0, sticky="w", pady=(0, 8))

        self.btn_ingresar = ttk.Button(
            formulario, text="Ingresar", style="Primary.TButton",
            command=self.ingresar,
        )
        self.btn_ingresar.grid(row=7, column=0, sticky="ew", ipady=3)

        self.lbl_msg = ttk.Label(
            formulario, text="", foreground=EXITO, style="Card.Muted.TLabel", wraplength=330
        )
        self.lbl_msg.grid(row=8, column=0, sticky="w", pady=(12, 0))

        poner_iconos(self)
        centrar(self, 820, 480)
        self.ent_dni.focus_set()

    def _refrescar_estado(self):
        if self._ingreso_exitoso:
            return
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
        self._tarea_refresco = self.after(1000, self._refrescar_estado)

    def ingresar(self):
        if self._ingreso_exitoso:
            return
        dni = self.ent_dni.get().strip()
        clave = self.ent_clave.get()
        if not dni or not clave:
            self.lbl_msg.config(text="Ingrese DNI y clave.", foreground=PELIGRO)
            return

        self.lbl_msg.config(text="Verificando...", foreground=TEXTO_SUAVE)
        self.update_idletasks()
        try:
            resultado = auth.login(dni, clave)
        except ErrorApp as exc:
            # Error de conexión o de consulta: se informa sin cerrar el login.
            self.lbl_msg.config(text=str(exc), foreground=PELIGRO)
            return
        if resultado.exito:
            # Evita un segundo ingreso (Enter repetido) mientras se abre la ventana.
            self._ingreso_exitoso = True
            self.btn_ingresar.config(state="disabled")
            self.ent_clave.unbind("<Return>")
            self.lbl_msg.config(text=resultado.mensaje + " Abriendo AulaSync...", foreground=EXITO)
            self.after(400, lambda: self.exito_callback())
        else:
            self.lbl_msg.config(text=resultado.mensaje, foreground=PELIGRO)
            self.ent_clave.delete(0, "end")
            self.ent_clave.focus()
