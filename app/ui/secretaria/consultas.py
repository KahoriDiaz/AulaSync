"""Consultas: los 10 reportes, la distribución por secciones y las listas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.secretaria.distribucion import Distribucion
from app.ui.secretaria.listas import Listas
from app.ui.secretaria.reportes import Reportes


class Consultas(ttk.Frame):
    """Contenedor con una sub-pestaña por tipo de consulta."""

    def __init__(self, parent):
        super().__init__(parent)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.pestanas: list[tk.Widget] = []
        for titulo, clase in (
            ("Reportes (10 consultas)", Reportes),
            ("Distribución por secciones", Distribucion),
            ("Listas y comparación", Listas),
        ):
            pestana = clase(self.notebook)
            self.notebook.add(pestana, text=titulo)
            self.pestanas.append(pestana)
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.recargar())

    def recargar(self):
        seleccionada = self.notebook.select()
        for pestana in self.pestanas:
            if str(pestana) == seleccionada:
                pestana.recargar()
                return
