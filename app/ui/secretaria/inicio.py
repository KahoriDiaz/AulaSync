"""Pantalla Inicio: indicadores del año actual y accesos rápidos."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

from app.errores import ErrorApp
from app.servicios import panel
from app.ui.componentes import Tabla
from app.ui.tema import PELIGRO, tarjeta


class Inicio(ttk.Frame):
    def __init__(self, parent, navegar=None):
        super().__init__(parent, padding=12)
        self.navegar = navegar or (lambda _clave: None)

        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text=f"Resumen del año escolar {date.today().year}",
                  style="Titulo.TLabel").pack(side="left")
        ttk.Button(cabecera, text="Actualizar", command=self.recargar).pack(side="right")

        self.zona_tarjetas = ttk.Frame(self)
        self.zona_tarjetas.pack(fill="x", pady=12)
        self.valores: list[tk.StringVar] = []
        self.titulos: list[tk.StringVar] = []
        for columna in range(5):
            caja = tarjeta(self.zona_tarjetas, padding=12)
            caja.grid(row=0, column=columna, sticky="nsew", padx=4)
            self.zona_tarjetas.columnconfigure(columna, weight=1)
            titulo = tk.StringVar()
            valor = tk.StringVar(value="-")
            ttk.Label(caja, textvariable=titulo, style="Card.Muted.TLabel", wraplength=160).pack(anchor="w")
            ttk.Label(caja, textvariable=valor, style="Card.Titulo.TLabel").pack(anchor="w", pady=(4, 0))
            self.titulos.append(titulo)
            self.valores.append(valor)

        accesos = ttk.Frame(self)
        accesos.pack(fill="x", pady=(0, 12))
        ttk.Button(accesos, text="Realizar matrícula", style="Primary.TButton",
                   command=lambda: self.navegar("matricula")).pack(side="left", padx=(0, 8))
        ttk.Button(accesos, text="Mantenimiento",
                   command=lambda: self.navegar("mantenimiento")).pack(side="left")

        ttk.Label(self, text="Matriculados por nivel y grado", style="Seccion.TLabel").pack(anchor="w")
        self.tabla = Tabla(self, columnas=("Nivel", "Grado", "Matriculados"),
                           anchos={"Nivel": 160, "Grado": 100, "Matriculados": 120})
        self.tabla.pack(fill="both", expand=True, pady=(4, 0))
        self.lbl_error = ttk.Label(self, text="", foreground=PELIGRO)
        self.lbl_error.pack(anchor="w")

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
            var_valor.set(str(valor))
        self.tabla.cargar(filas)
