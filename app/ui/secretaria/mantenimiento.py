"""Mantenimiento: una sub-pestaña por tabla con listado, buscador y CRUD.

Estudiante y Padre/Apoderado usan sus formularios completos; todas las
altas, modificaciones y bajas llaman a procedimientos (CALL sp_...).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.servicios import estudiantes, padres
from app.ui.componentes import CampoBusqueda, Tabla
from app.ui.secretaria.crud_generico import PestanaCrud
from app.ui.secretaria.formulario_estudiante import FormularioEstudiante
from app.ui.secretaria.formulario_padre import FormularioPadre


class PestanaConFormulario(ttk.Frame):
    """Listado + Nuevo / Editar / Eliminar usando un formulario Toplevel."""

    def __init__(self, parent, *, columnas, listar, obtener, insertar, actualizar,
                 eliminar, formulario, nombre):
        super().__init__(parent)
        self.listar = listar
        self.obtener = obtener
        self.insertar = insertar
        self.actualizar = actualizar
        self.eliminar_registro = eliminar
        self.formulario = formulario
        self.nombre = nombre

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=5, pady=4)
        ttk.Button(barra, text="Nuevo", style="Primary.TButton", command=self.nuevo).pack(side="left", padx=3)
        ttk.Button(barra, text="Editar", command=self.editar).pack(side="left", padx=3)
        ttk.Button(barra, text="Eliminar", style="Danger.TButton", command=self.eliminar).pack(side="left", padx=3)
        ttk.Button(barra, text="Actualizar lista", command=self.recargar).pack(side="left", padx=3)
        CampoBusqueda(barra, etiqueta="Buscar:", comando=lambda t: self.tabla.filtrar(t)).pack(side="right", padx=5)

        self.tabla = Tabla(self, columnas=columnas, anchos={c: 130 for c in columnas})
        self.tabla.pack(fill="both", expand=True, padx=5, pady=4)

    def recargar(self):
        try:
            self.tabla.cargar(self.listar())
        except Exception as exc:
            messagebox.showerror("Error al cargar los datos", str(exc), parent=self)

    def _seleccion(self):
        seleccionado = self.tabla.seleccion()
        if not seleccionado:
            messagebox.showwarning("Atención", f"Seleccione un {self.nombre}.", parent=self)
        return seleccionado

    def nuevo(self):
        def guardar(parametros):
            self.insertar(parametros)
            self.recargar()

        self.formulario(self.winfo_toplevel(), modo="nuevo", al_guardar=guardar)

    def editar(self):
        seleccionado = self._seleccion()
        if not seleccionado:
            return
        try:
            datos = self.obtener(seleccionado["DNI"])
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        if not datos:
            messagebox.showerror("Error", f"No se encontró el {self.nombre} seleccionado.", parent=self)
            return

        def guardar(parametros):
            self.actualizar(parametros)
            self.recargar()

        self.formulario(self.winfo_toplevel(), modo="editar", datos=datos, al_guardar=guardar)

    def eliminar(self):
        seleccionado = self._seleccion()
        if not seleccionado:
            return
        dni = seleccionado["DNI"]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el {self.nombre} con DNI {dni}?", parent=self):
            return
        try:
            self.eliminar_registro(dni)
        except Exception as exc:
            messagebox.showerror("No se pudo eliminar", str(exc), parent=self)
            return
        self.recargar()
        messagebox.showinfo("Éxito", "Registro eliminado.", parent=self)


class Mantenimiento(ttk.Frame):
    """Contenedor con una sub-pestaña por tabla, elegida desde una lista vertical."""

    def __init__(self, parent):
        super().__init__(parent)
        lista = ttk.Frame(self, width=230)
        lista.pack(side="left", fill="y", padx=(0, 14))
        lista.pack_propagate(False)
        ttk.Label(lista, text="TABLAS", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(2, 6))
        self.lista = lista
        self.botones: dict[str, ttk.Button] = {}
        self.notebook = ttk.Notebook(self, style="SinPestanas.TNotebook")
        self.notebook.pack(side="left", fill="both", expand=True)
        self.pestanas: dict[str, tk.Widget] = {}

        self._agregar("Estudiante", PestanaConFormulario(
            self.notebook,
            columnas=["DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "FechaNacimiento", "Celular"],
            listar=estudiantes.listar_estudiantes, obtener=estudiantes.obtener_estudiante,
            insertar=estudiantes.insertar_estudiante, actualizar=estudiantes.actualizar_estudiante,
            eliminar=estudiantes.eliminar_estudiante, formulario=FormularioEstudiante,
            nombre="estudiante",
        ))
        self._agregar("Padre / Apoderado", PestanaConFormulario(
            self.notebook,
            columnas=["DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "Celular", "CorreoElectronico"],
            listar=padres.listar_padres, obtener=padres.obtener_padre,
            insertar=padres.insertar_padre, actualizar=padres.actualizar_padre,
            eliminar=padres.eliminar_padre, formulario=FormularioPadre,
            nombre="padre o apoderado",
        ))
        for clave, titulo in (
            ("contacto", "Contacto de emergencia"),
            ("ie", "Institución educativa"),
            ("constancia", "Constancia de logros"),
            ("logro", "Logro"),
            ("matricula", "Matrícula"),
            ("tiene_padres", "Tiene padres"),
            ("hermandad", "Hermandad"),
            ("nee", "Necesidades educativas especiales"),
            ("hermanos_ie", "Hermanos en la I.E."),
            ("secretaria", "Secretaria"),
        ):
            self._agregar(titulo, PestanaCrud(self.notebook, clave))
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.recargar())

    def _agregar(self, titulo: str, pestana: tk.Widget) -> None:
        self.notebook.add(pestana, text=titulo)
        self.pestanas[titulo] = pestana
        boton = ttk.Button(self.lista, text=titulo, style="SubNav.TButton",
                           command=lambda: self.notebook.select(pestana))
        boton.pack(fill="x", pady=1)
        self.botones[titulo] = boton

    def recargar(self):
        """Recarga solo la sub-pestaña visible y la resalta en la lista."""
        seleccionada = self.notebook.select()
        for titulo, pestana in self.pestanas.items():
            activa = str(pestana) == seleccionada
            self.botones[titulo].configure(style="SubNavActivo.TButton" if activa else "SubNav.TButton")
            if activa:
                pestana.recargar()
