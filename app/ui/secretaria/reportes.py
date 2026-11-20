"""Pantalla de las 10 consultas representativas (§6.3 punto 7).

Cada consulta se elige por número, arranca con los parámetros del script
`06_consultas.sql` y muestra sus resultados en una tabla exportable.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import errores
from app.servicios import reportes
from app.ui.componentes import BarraExportacion, Tabla

SUGERENCIAS = {
    "Nivel": ("Inicial", "Primaria", "Secundaria"),
    "Estado": ("Matriculado", "Retirado", "Trasladado"),
    "Sección": ("A", "B", "C", "D"),
}


class Reportes(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.reporte_actual: reportes.Reporte | None = None
        self.vars_parametros: list[tk.StringVar] = []
        self.controles: list[tk.Entry | ttk.Combobox] = []
        self.contador_var = tk.StringVar(value="Seleccione una consulta.")
        self._construir()
        self._seleccionar(1)

    def _construir(self) -> None:
        superior = ttk.Frame(self)
        superior.pack(fill="x", padx=6, pady=6)
        ttk.Label(superior, text="Consulta:", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.lista = tk.Listbox(superior, height=6, exportselection=False)
        self.lista.pack(side="left", fill="x", expand=True, padx=6)
        self.lista.bind("<<ListboxSelect>>", self._al_seleccionar)
        for consulta in reportes.todos():
            self.lista.insert("end", f"{consulta.numero}. {consulta.titulo}")
        self.lista.selection_set(0)

        self.titulo_var = tk.StringVar()
        ttk.Label(self, textvariable=self.titulo_var, wraplength=900).pack(anchor="w", padx=8)

        self.parametros_frame = ttk.LabelFrame(self, text="Parámetros (valores del script)")
        self.parametros_frame.pack(fill="x", padx=6, pady=6)
        self.botones = ttk.Frame(self)
        self.botones.pack(fill="x", padx=6)
        ttk.Button(self.botones, text="Ejecutar consulta", command=self.ejecutar).pack(side="left")

        resultado = ttk.LabelFrame(self, text="Resultados")
        resultado.pack(fill="both", expand=True, padx=6, pady=4)
        self.tabla = Tabla(resultado, columnas=(), anchos={})
        self.tabla.pack(fill="both", expand=True, padx=4, pady=4)
        BarraExportacion(
            resultado, self.tabla.filas,
            lambda: (f"Consulta {self.reporte_actual.numero} - "
                     f"{self.reporte_actual.titulo}" if self.reporte_actual else "Reporte"),
            columnas=lambda: self.tabla.columnas,
        ).pack(fill="x", padx=4, pady=4)
        ttk.Label(self, textvariable=self.contador_var).pack(anchor="w", padx=8, pady=4)

    def recargar(self) -> None:
        """No vuelve a consultar la BD hasta que el usuario ejecute una consulta."""

    def _al_seleccionar(self, _evento=None) -> None:
        seleccion = self.lista.curselection()
        if seleccion:
            self._seleccionar(int(seleccion[0]) + 1)

    def _seleccionar(self, numero: int) -> None:
        try:
            consulta = reportes.obtener(numero)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.reporte_actual = consulta
        self.tabla.reconfigurar(consulta.columnas)
        self.titulo_var.set(
            f"{consulta.numero}. {consulta.titulo}    "
            f"(JOIN: {consulta.joins}; parámetros: {len(consulta.parametros)})"
        )
        for hijo in self.parametros_frame.winfo_children():
            hijo.destroy()
        self.vars_parametros.clear()
        self.controles.clear()
        for fila, (nombre, valor) in enumerate(zip(consulta.parametros, consulta.defaults)):
            variable = tk.StringVar(value=str(valor))
            ttk.Label(self.parametros_frame, text=nombre, width=18, anchor="w").grid(
                row=fila, column=0, sticky="w", padx=6, pady=3
            )
            sugerencias = SUGERENCIAS.get(nombre)
            if sugerencias:
                control = ttk.Combobox(
                    self.parametros_frame, textvariable=variable,
                    values=sugerencias, width=24,
                )
            else:
                control = ttk.Entry(self.parametros_frame, textvariable=variable, width=26)
            control.grid(row=fila, column=1, sticky="w", padx=6, pady=3)
            self.vars_parametros.append(variable)
            self.controles.append(control)
        self.contador_var.set(
            "Parámetros listos. Presione 'Ejecutar consulta'."
            if consulta.parametros else "Sin parámetros. Presione 'Ejecutar consulta'."
        )

    def ejecutar(self) -> None:
        consulta = self.reporte_actual
        if consulta is None:
            return
        valores = tuple(variable.get() for variable in self.vars_parametros)
        # Los años se enhilan como número para conservar el tipo del script.
        valores = tuple(
            int(valor) if nombre == "Año" and str(valor).strip().isdigit() else valor
            for nombre, valor in zip(consulta.parametros, valores)
        )
        try:
            filas = reportes.ejecutar(consulta.numero, valores)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error en la consulta", str(exc), parent=self)
            return
        anchos = {
            columna: max(90, min(220, len(columna) * 9 + 20))
            for columna in consulta.columnas
        }
        self.tabla.reconfigurar(consulta.columnas, anchos)
        self.tabla.cargar(filas)
        self.contador_var.set(f"{len(filas)} fila(s) para la consulta {consulta.numero}.")
