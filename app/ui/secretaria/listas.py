"""Pantalla de listas: padrón, comparación de años e importación de DNIs (§6.3.6)."""
from __future__ import annotations

from datetime import date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import errores
from app.servicios import distribucion, listas
from app.ui.componentes import BarraExportacion, Tabla


class Listas(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        anio_actual = str(date.today().year + 1)
        self.anio_var = tk.StringVar(value=anio_actual)
        self.nivel_var = tk.StringVar(value="Todos")
        self.grado_var = tk.StringVar(value="Todos")
        self.seccion_var = tk.StringVar(value="Todas")
        self.anio_anterior_var = tk.StringVar(value=str(date.today().year))
        self.anio_actual_var = tk.StringVar(value=anio_actual)
        self.resumen_var = tk.StringVar(value="Continúan: 0 | Nuevos: 0 | No continúan: 0")
        self.externa_var = tk.StringVar(value="Lista externa: sin importar")
        self.dnis_externos: list[str] = []
        self._construir()
        self._recargar_padron()

    def _construir(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        self._pestana_padron()
        self._pestana_comparacion()

    def _pestana_padron(self) -> None:
        pagina = ttk.Frame(self.notebook)
        self.notebook.add(pagina, text="Padrón de matriculados")
        filtros = ttk.Frame(pagina)
        filtros.pack(fill="x", padx=4, pady=6)
        ttk.Label(filtros, text="Año:").pack(side="left", padx=4)
        ttk.Entry(filtros, textvariable=self.anio_var, width=8).pack(side="left")
        ttk.Label(filtros, text="Nivel:").pack(side="left", padx=8)
        self.nivel_combo = ttk.Combobox(
            filtros, textvariable=self.nivel_var, width=14, state="readonly",
            values=("Todos",) + distribucion.niveles(),
        )
        self.nivel_combo.pack(side="left")
        self.nivel_combo.bind("<<ComboboxSelected>>", self._nivel_cambiado)
        ttk.Label(filtros, text="Grado:").pack(side="left", padx=8)
        self.grado_combo = ttk.Combobox(
            filtros, textvariable=self.grado_var, width=10, state="readonly",
            values=("Todos",),
        )
        self.grado_combo.pack(side="left")
        ttk.Label(filtros, text="Sección:").pack(side="left", padx=8)
        self.seccion_combo = ttk.Combobox(
            filtros, textvariable=self.seccion_var, width=10, state="readonly",
            values=("Todas",),
        )
        self.seccion_combo.pack(side="left")
        ttk.Button(filtros, text="Buscar", style="Primary.TButton",
                   command=self._recargar_padron).pack(side="left", padx=8)

        self.tabla_padron = Tabla(
            pagina, columnas=listas.COLUMNAS_PADRON,
            anchos={"DNI": 110, "Nivel": 105, "Grado": 75, "Seccion": 85, "Estado": 105},
        )
        self.tabla_padron.pack(fill="both", expand=True, padx=4, pady=4)
        BarraExportacion(
            pagina, self.tabla_padron.filas,
            lambda: f"Padrón {self.anio_var.get()}",
            columnas=listas.COLUMNAS_PADRON,
        ).pack(fill="x", padx=4, pady=4)

    def recargar(self) -> None:
        """Vuelve a leer el padrón con los filtros actuales."""
        self._recargar_padron()

    def _nivel_cambiado(self, _evento=None) -> None:
        nivel = self.nivel_var.get()
        grados = distribucion.grados(nivel) if nivel != "Todos" else ()
        secciones = distribucion.secciones(nivel) if nivel != "Todos" else ()
        self.grado_combo["values"] = ("Todos",) + tuple(grados)
        self.seccion_combo["values"] = ("Todas",) + tuple(secciones)
        self.grado_var.set("Todos")
        self.seccion_var.set("Todas")

    def _recargar_padron(self) -> None:
        try:
            anio = int(self.anio_var.get().strip())
        except ValueError:
            messagebox.showwarning("Atención", "Ingrese un año válido.", parent=self)
            return
        nivel = None if self.nivel_var.get() in ("", "Todos") else self.nivel_var.get()
        grado = None if self.grado_var.get() in ("", "Todos") else self.grado_var.get()
        seccion = None if self.seccion_var.get() in ("", "Todas") else self.seccion_var.get()
        try:
            filas = listas.padron(anio, nivel, grado, seccion)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.tabla_padron.cargar(filas)

    def _pestana_comparacion(self) -> None:
        pagina = ttk.Frame(self.notebook)
        self.notebook.add(pagina, text="Comparación de listas")
        filtros = ttk.Frame(pagina)
        filtros.pack(fill="x", padx=4, pady=6)
        ttk.Label(filtros, text="Año anterior:").pack(side="left", padx=4)
        ttk.Entry(filtros, textvariable=self.anio_anterior_var, width=8).pack(side="left")
        ttk.Label(filtros, text="Año actual:").pack(side="left", padx=8)
        ttk.Entry(filtros, textvariable=self.anio_actual_var, width=8).pack(side="left")
        ttk.Button(filtros, text="Comparar años", style="Primary.TButton",
                   command=self._comparar).pack(side="left", padx=8)
        ttk.Button(
            filtros, text="Importar lista externa (CSV/Excel)",
            command=self._importar,
        ).pack(side="right", padx=4)
        ttk.Label(pagina, textvariable=self.resumen_var, font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", padx=6
        )

        self.tabla_comparacion = Tabla(
            pagina, columnas=listas.COLUMNAS_COMPARACION,
            anchos={"DNI": 105, "NivelAnterior": 110, "GradoAnterior": 110,
                    "NivelActual": 100, "GradoActual": 100, "Situacion": 150},
        )
        self.tabla_comparacion.pack(fill="both", expand=True, padx=4, pady=4)
        BarraExportacion(
            pagina, self.tabla_comparacion.filas,
            lambda: (f"Comparación {self.anio_anterior_var.get()}-"
                     f"{self.anio_actual_var.get()}"),
            columnas=listas.COLUMNAS_COMPARACION,
        ).pack(fill="x", padx=4, pady=4)

        externa = ttk.LabelFrame(pagina, text="Comparación con lista externa")
        externa.pack(fill="both", expand=True, padx=4, pady=6)
        ttk.Label(externa, textvariable=self.externa_var).pack(anchor="w", padx=6, pady=4)
        self.tabla_externa = Tabla(
            externa, columnas=listas.COLUMNAS_EXTERNA,
            anchos={"DNI": 120, "Situacion": 180, "Nombres": 320, "Seccion": 90},
        )
        self.tabla_externa.pack(fill="both", expand=True, padx=4, pady=4)
        BarraExportacion(
            externa, self.tabla_externa.filas,
            lambda: f"Lista externa {self.anio_actual_var.get()}",
            columnas=listas.COLUMNAS_EXTERNA,
        ).pack(fill="x", padx=4, pady=4)

    def _anios(self) -> tuple[int, int] | None:
        try:
            return int(self.anio_anterior_var.get()), int(self.anio_actual_var.get())
        except ValueError:
            messagebox.showwarning("Atención", "Ingrese años válidos.", parent=self)
            return None

    def _comparar(self) -> None:
        anios = self._anios()
        if anios is None:
            return
        try:
            filas = listas.comparar(*anios)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.tabla_comparacion.cargar(filas)
        conteo = listas.resumen(filas)
        self.resumen_var.set(
            f"Continúan: {conteo['Continúa']} | Nuevos: {conteo['Nuevo']} | "
            f"No continúan: {conteo[listas.NO_CONTINUA]}"
        )

    def _importar(self) -> None:
        origen = filedialog.askopenfilename(
            title="Lista externa de DNIs",
            filetypes=(
                ("CSV y Excel", "*.csv *.txt *.xlsx *.xlsm"),
                ("CSV", "*.csv"), ("Excel", "*.xlsx"), ("Todos", "*.*"),
            ),
            parent=self,
        )
        if not origen:
            return
        try:
            self.dnis_externos = listas.importar_dnis(origen)
            anios = self._anios()
            if anios is None:
                return
            filas = listas.comparar_con_lista_externa(
                self.dnis_externos, anios[1]
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("No se pudo importar", str(exc), parent=self)
            return
        self.tabla_externa.cargar(filas)
        self.externa_var.set(
            f"Lista externa: {len(filas)} DNI(s) comparados con {anios[1]}"
        )
