"""Panel que muestra las relaciones entre las tablas de la base (tkinter).

Dos áreas: indicadores por tabla y un detalle de matrículas que cruza
ESTUDIANTE, PADRE_APODERADO, SECRETARIA, I.E., LOGRO y HERMANDAD.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import errores
from app.servicios import panel as servicio
from app.ui.componentes import BarraExportacion, Tabla
from app.ui.tema import tarjeta


class PanelRelaciones(ttk.Frame):
    """Vista de solo lectura del modelo entity-relacional."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.contador_var = tk.StringVar(value="Presione 'Actualizar panel'.")
        self._construir()

    def _construir(self) -> None:
        indicadores = tarjeta(self)
        indicadores.pack(fill="x", padx=8, pady=(8, 6))
        cabecera = ttk.Frame(indicadores, style="SobreTarjeta.TFrame")
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="Indicadores del modelo", style="Seccion.TLabel").pack(side="left")
        ttk.Button(cabecera, text="Actualizar panel", style="Primary.TButton",
                   command=self.recargar).pack(side="right")

        self.indicadores_tree = ttk.Treeview(
            indicadores, columns=("Indicador", "Valor"), show="headings", height=5
        )
        self.indicadores_tree.heading("Indicador", text="Tabla o relación")
        self.indicadores_tree.heading("Valor", text="Registros")
        self.indicadores_tree.column("Indicador", width=280)
        self.indicadores_tree.column("Valor", width=110)
        self.indicadores_tree.pack(fill="x", pady=(6, 2))

        detalle = ttk.LabelFrame(self, text="Matrículas y sus relaciones", padding=6)
        detalle.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        columnas = servicio.columnas_detalle()
        anchos = {"NombreIE": 220, "Responsable": 220, "Secretaria": 200}
        self.tabla = Tabla(detalle, columnas=columnas, anchos=anchos)
        self.tabla.pack(fill="both", expand=True)
        BarraExportacion(
            detalle, self.tabla.filas,
            lambda: "Panel de relaciones", columnas=lambda: columnas,
        ).pack(fill="x", pady=(4, 0))
        ttk.Label(self, textvariable=self.contador_var).pack(anchor="w", padx=10, pady=(0, 6))

    def recargar(self) -> None:
        """Ejecuta las consultas de solo lectura y llena ambas tablas."""
        try:
            indicadores = servicio.indicadores()
            filas = servicio.detalle()
        except errores.ErrorApp as exc:
            messagebox.showerror("Panel de relaciones", str(exc), parent=self)
            return
        for item in self.indicadores_tree.get_children():
            self.indicadores_tree.delete(item)
        for fila in indicadores:
            self.indicadores_tree.insert(
                "", "end", values=(fila["Indicador"], fila["Valor"])
            )
        self.tabla.cargar(filas)
        self.contador_var.set(
            f"{len(filas)} matrícula(s) con su estudiante, responsable, secretaría e I.E."
        )
