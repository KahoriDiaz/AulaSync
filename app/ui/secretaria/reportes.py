"""Pantalla de las 10 consultas representativas (§6.3 punto 7).

Cada consulta tiene su propio botón. Al presionarlo se muestran sus parámetros
y un botón para ejecutarla, con resultados en tabla exportable.
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

    def _construir(self) -> None:
        # Barra de botones (una por consulta)
        botones_frame = ttk.LabelFrame(self, text="Consultas representativas")
        botones_frame.pack(fill="x", padx=6, pady=6)

        consultas = reportes.todos()
        for idx, consulta in enumerate(consultas):
            fila = idx // 2
            col = idx % 2
            btn = ttk.Button(
                botones_frame,
                text=f"{consulta.numero}. {consulta.titulo}",
                command=lambda c=consulta: self._seleccionar(c),
            )
            btn.grid(row=fila, column=col, padx=4, pady=4, sticky="ew")
        botones_frame.columnconfigure(0, weight=1)
        botones_frame.columnconfigure(1, weight=1)

        # Título y parámetros
        self.titulo_var = tk.StringVar()
        ttk.Label(self, textvariable=self.titulo_var, wraplength=900).pack(
            anchor="w", padx=8, pady=(8, 0)
        )

        self.parametros_frame = ttk.LabelFrame(self, text="Parámetros (valores del script)")
        self.parametros_frame.pack(fill="x", padx=6, pady=6)
        ttk.Label(self.parametros_frame, text="Elija una de las 10 consultas para ver sus parámetros.",
                  style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=6, pady=3)

        self.botones_ejec = ttk.Frame(self)
        self.botones_ejec.pack(fill="x", padx=6)
        self.btn_ejecutar = ttk.Button(
            self.botones_ejec, text="Ejecutar consulta", command=self.ejecutar, state="disabled"
        )
        self.btn_ejecutar.pack(side="left")

        # Resultado
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
        pass

    def _seleccionar(self, consulta: reportes.Reporte) -> None:
        self.reporte_actual = consulta
        self.titulo_var.set(
            f"{consulta.numero}. {consulta.titulo}    "
            f"(JOIN: {consulta.joins}; parámetros: {len(consulta.parametros)})"
        )
        self.btn_ejecutar.config(state="normal")

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
