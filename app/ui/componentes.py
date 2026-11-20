"""Componentes de UI reutilizables (tkinter + ttk).

Tabla: Treeview con encabezados clickeables para ordenar y un campo de búsqueda.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Tabla(ttk.Frame):
    """Treeview con scrollbar, orden por columna y filtro de texto."""

    def __init__(self, parent, columnas, anchos=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnas = list(columnas)
        self._orden_asc = {c: True for c in self.columnas}

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(marco, columns=self.columnas, show="headings")
        for col in self.columnas:
            texto = col.replace("_", " ").title()
            ancho = (anchos or {}).get(col, 100)
            self.tree.heading(col, text=texto, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=ancho, anchor="w")

        scroll = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._filas = []

    def cargar(self, filas):
        """Carga una lista de diccionarios (claves = columnas)."""
        self._filas = list(filas)
        self._mostrar(self._filas)

    def _mostrar(self, filas):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for fila in filas:
            valores = [fila.get(col, "") for col in self.columnas]
            self.tree.insert("", "end", values=valores)

    def _ordenar(self, col):
        asc = self._orden_asc[col]
        self._filas.sort(key=lambda f: str(f.get(col, "")), reverse=not asc)
        self._orden_asc[col] = not asc
        self._mostrar(self._filas)

    def filtrar(self, texto):
        texto = texto.lower()
        filtradas = [
            f for f in self._filas
            if any(texto in str(f.get(c, "")).lower() for c in self.columnas)
        ]
        self._mostrar(filtradas)

    def seleccion(self):
        item = self.tree.focus()
        if not item:
            return None
        valores = self.tree.item(item, "values")
        return dict(zip(self.columnas, valores))


class CampoBusqueda(ttk.Frame):
    def __init__(self, parent, etiqueta="Buscar:", comando=None, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text=etiqueta).pack(side="left", padx=(0, 5))
        self.entrada = ttk.Entry(self)
        self.entrada.pack(side="left", fill="x", expand=True)
        if comando:
            self.entrada.bind("<KeyRelease>", lambda _e: comando(self.entrada.get()))
