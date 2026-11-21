"""Pantalla de distribución por secciones (§6.3 punto 5).

Muestra nivel / grado / sección con matriculados y vacantes, permite consultar
el padrón de cada sección y mover un alumno con `sp_cambiar_seccion`.
"""
from __future__ import annotations

from datetime import date

import tkinter as tk
from tkinter import messagebox, ttk

from app import errores
from app.servicios import distribucion
from app.ui.componentes import BarraExportacion, Tabla


class Distribucion(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.anio_var = tk.StringVar(value=str(date.today().year + 1))
        self.nivel_var = tk.StringVar(value="Todos")
        self.filtro_var = tk.StringVar(value="Todas las secciones")
        self.seccion_var = tk.StringVar(value="A")
        self._construir()
        # Los datos se cargan al abrir la pestaña (recargar), no al construirla.

    def _construir(self) -> None:
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=6, pady=6)
        ttk.Label(filtros, text="Año:").pack(side="left", padx=4)
        ttk.Combobox(
            filtros, textvariable=self.anio_var, width=8,
            values=tuple(str(a) for a in distribucion.anios()),
        ).pack(side="left")
        ttk.Label(filtros, text="Nivel:").pack(side="left", padx=8)
        self.nivel_combo = ttk.Combobox(
            filtros, textvariable=self.nivel_var, width=14, state="readonly",
            values=("Todos",) + distribucion.niveles(),
        )
        self.nivel_combo.pack(side="left")
        ttk.Button(filtros, text="Buscar", style="Primary.TButton",
                   command=self.recargar).pack(side="left", padx=6)

        cupos = ttk.LabelFrame(self, text="Cupos por sección (máximo 30)")
        cupos.pack(fill="both", expand=True, padx=6, pady=4)
        self.tabla_cupos = Tabla(
            cupos, columnas=distribucion.COLUMNAS_CUPOS,
            anchos={"AñoEscolar": 110, "Nivel": 110, "Grado": 80,
                    "Seccion": 90, "Matriculados": 120, "Vacantes": 100},
        )
        self.tabla_cupos.pack(fill="both", expand=True, padx=4, pady=4)
        self.tabla_cupos.tree.bind("<<TreeviewSelect>>", self._cupo_seleccionado)
        BarraExportacion(
            cupos, self.tabla_cupos.filas,
            lambda: f"Distribución {self.anio_var.get()}",
            columnas=distribucion.COLUMNAS_CUPOS,
        ).pack(fill="x", padx=4, pady=4)

        matriculados = ttk.LabelFrame(self, text="Matriculados")
        matriculados.pack(fill="both", expand=True, padx=6, pady=4)
        cabecera = ttk.Frame(matriculados)
        cabecera.pack(fill="x", padx=4, pady=4)
        ttk.Label(cabecera, textvariable=self.filtro_var).pack(side="left")
        ttk.Label(cabecera, text="Mover a sección:").pack(side="left", padx=8)
        self.secciones_combo = ttk.Combobox(
            cabecera, textvariable=self.seccion_var, width=8, state="readonly"
        )
        self.secciones_combo.pack(side="left")
        ttk.Button(cabecera, text="Mover alumno", style="Primary.TButton",
                   command=self.mover).pack(side="left", padx=6)
        self.tabla_padron = Tabla(
            matriculados, columnas=distribucion.COLUMNAS_PADRON,
            anchos={"DNI": 105, "Nivel": 100, "Grado": 75, "Seccion": 85, "Estado": 100},
        )
        self.tabla_padron.pack(fill="both", expand=True, padx=4, pady=4)
        BarraExportacion(
            matriculados, self.tabla_padron.filas,
            lambda: f"Padrón {self.anio_var.get()} - {self.filtro_var.get()}",
            columnas=distribucion.COLUMNAS_PADRON,
        ).pack(fill="x", padx=4, pady=4)

    def recargar(self) -> None:
        try:
            anio = int(self.anio_var.get().strip())
        except ValueError:
            messagebox.showwarning("Atención", "Ingrese un año válido.", parent=self)
            return
        nivel = self.nivel_var.get()
        try:
            filas = distribucion.resumen(
                anio, None if nivel in ("", "Todos") else nivel
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.tabla_cupos.cargar(filas)
        self._cargar_padron()

    def _cupo_seleccionado(self, _evento=None) -> None:
        fila = self.tabla_cupos.seleccion()
        if not fila:
            return
        self.seccion_var.set(str(fila.get("Seccion") or "A"))
        self.secciones_combo["values"] = distribucion.secciones(str(fila.get("Nivel", "")))
        if self.seccion_var.get() not in self.secciones_combo["values"]:
            self.seccion_var.set(
                self.secciones_combo["values"][0] if self.secciones_combo["values"] else ""
            )
        self.filtro_var.set(
            f"{fila.get('Nivel', '')} {fila.get('Grado', '')} - sección {fila.get('Seccion', '')}"
        )
        self._cargar_padron()

    def _cargar_padron(self) -> None:
        try:
            anio = int(self.anio_var.get().strip())
        except ValueError:
            return
        fila = self.tabla_cupos.seleccion()
        if fila:
            nivel, grado, seccion = fila.get("Nivel"), fila.get("Grado"), fila.get("Seccion")
        else:
            nivel = None if self.nivel_var.get() == "Todos" else self.nivel_var.get()
            grado = seccion = None
            self.filtro_var.set("Todas las secciones")
        try:
            filas = distribucion.padron(anio, nivel, grado, seccion)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.tabla_padron.cargar(filas)

    def mover(self) -> None:
        fila = self.tabla_padron.seleccion()
        if not fila:
            messagebox.showwarning("Atención", "Seleccione un alumno.", parent=self)
            return
        dni = str(fila.get("DNI", ""))
        seccion = self.seccion_var.get().strip().upper()
        if not seccion or seccion == fila.get("Seccion"):
            messagebox.showwarning(
                "Atención", "Elija una sección distinta a la actual.", parent=self
            )
            return
        if not messagebox.askyesno(
            "Confirmar", f"¿Mover al alumno {dni} a la sección {seccion}?", parent=self
        ):
            return
        try:
            distribucion.mover_seccion(dni, int(self.anio_var.get()), seccion)
        except errores.ErrorApp as exc:
            messagebox.showerror("No se pudo mover", str(exc), parent=self)
            return
        messagebox.showinfo("Listo", "El alumno cambió de sección.", parent=self)
        self.recargar()
