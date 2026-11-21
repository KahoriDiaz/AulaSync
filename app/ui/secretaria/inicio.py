"""Pantalla Inicio: indicadores del año actual y accesos rápidos."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

from app.errores import ErrorApp
from app.servicios import panel
from app.ui.componentes import Tabla
from app.ui.tema import (
    ACENTO, BORDE, EXITO, INFO, PELIGRO, PRIMARIO, PRIMARIO_OSCURO, SUPERFICIE,
    TEXTO_SUAVE, tarjeta,
)

# Color de la franja de cada tarjeta, en el orden de panel.tarjetas_inicio().
COLORES = (PRIMARIO, INFO, ACENTO, "#7A6BAE", EXITO)


class Inicio(ttk.Frame):
    def __init__(self, parent, navegar=None):
        super().__init__(parent)
        self.navegar = navegar or (lambda _clave: None)

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 12))
        ttk.Label(barra, text=f"Año escolar {date.today().year}",
                  style="Seccion.TLabel").pack(side="left")
        ttk.Button(barra, text="Actualizar", command=self.recargar).pack(side="right")
        ttk.Button(barra, text="Mantenimiento",
                   command=lambda: self.navegar("mantenimiento")).pack(side="right", padx=8)
        ttk.Button(barra, text="Realizar matrícula", style="Primary.TButton",
                   command=lambda: self.navegar("matricula")).pack(side="right")

        zona = ttk.Frame(self)
        zona.pack(fill="x", pady=(0, 18))
        self.valores: list[tk.StringVar] = []
        self.titulos: list[tk.StringVar] = []
        for columna, color in enumerate(COLORES):
            zona.columnconfigure(columna, weight=1, uniform="tarjetas")
            caja = tk.Frame(zona, bg=SUPERFICIE, highlightbackground=BORDE,
                            highlightthickness=1)
            caja.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 6, 0))
            tk.Frame(caja, bg=color, width=5).pack(side="left", fill="y")
            cuerpo = tk.Frame(caja, bg=SUPERFICIE, padx=16, pady=14)
            cuerpo.pack(side="left", fill="both", expand=True)
            titulo = tk.StringVar(value="-")
            valor = tk.StringVar(value="-")
            tk.Label(cuerpo, textvariable=titulo, bg=SUPERFICIE, fg=TEXTO_SUAVE,
                     font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=170).pack(fill="x")
            tk.Label(cuerpo, textvariable=valor, bg=SUPERFICIE, fg=PRIMARIO_OSCURO,
                     font=("Segoe UI", 26, "bold"), anchor="w").pack(fill="x", pady=(4, 0))
            self.titulos.append(titulo)
            self.valores.append(valor)

        contenedor = tarjeta(self, padding=16)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text="Matriculados por nivel y grado",
                  style="Card.Seccion.TLabel").pack(anchor="w", pady=(0, 8))
        self.tabla = Tabla(contenedor, columnas=("Nivel", "Grado", "Matriculados"),
                           anchos={"Nivel": 200, "Grado": 140, "Matriculados": 140})
        self.tabla.pack(fill="both", expand=True)
        self.lbl_error = ttk.Label(self, text="", foreground=PELIGRO)
        self.lbl_error.pack(anchor="w", pady=(6, 0))

    def recargar(self) -> None:
        try:
            tarjetas = panel.tarjetas_inicio()
            filas = panel.matriculados_por_grado()
        except ErrorApp as exc:
            self.lbl_error.config(text=f"No se pudieron cargar los indicadores: {exc}")
            return
        self.lbl_error.config(text="")
        for (titulo, valor), var_titulo, var_valor in zip(tarjetas, self.titulos, self.valores):
            var_titulo.set(titulo)
            var_valor.set(f"{valor:,}".replace(",", " "))
        self.tabla.cargar(filas)
