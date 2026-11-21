"""Pestaña de mantenimiento genérica, configurada con una ``TablaCrud``.

Muestra el listado con buscador y los botones Nuevo / Editar / Eliminar; el
formulario se arma con los campos de la tabla. Los errores de procedimientos y
triggers se muestran tal cual llegan (ya traducidos por app.errores).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.errores import ErrorApp
from app.servicios import auth, mantenimiento
from app.ui.componentes import CampoBusqueda, Tabla, entry_dni
from app.ui.selector_fecha import SelectorFecha
from app.ui.tema import aplicar_tema


class FormularioGenerico(tk.Toplevel):
    def __init__(self, parent, tabla: mantenimiento.TablaCrud, al_guardar, datos=None):
        super().__init__(parent)
        aplicar_tema(self)
        self.tabla = tabla
        self.al_guardar = al_guardar
        self.datos = datos
        self.editando = datos is not None
        self.title(("Editar " if self.editando else "Nuevo: ") + tabla.nombre)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.variables: dict[str, tk.StringVar] = {}
        self.fechas: dict[str, SelectorFecha] = {}

        marco = ttk.Frame(self, padding=16)
        marco.pack(fill="both", expand=True)
        fila = 0
        for campo in tabla.campos:
            if campo.solo_lectura and not self.editando:
                continue
            ttk.Label(marco, text=campo.etiqueta).grid(row=fila, column=0, sticky="w", pady=4, padx=(0, 10))
            bloqueado = self.editando and (
                campo.clave_primaria or campo.solo_lectura
                or (tabla.campos_editables and campo.clave not in tabla.campos_editables)
            )
            control = self._control(marco, campo, bloqueado)
            control.grid(row=fila, column=1, sticky="ew", pady=4)
            fila += 1
        botones = ttk.Frame(marco)
        botones.grid(row=fila, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(botones, text="Guardar", style="Primary.TButton", command=self._guardar).pack(side="right")
        marco.columnconfigure(1, weight=1)

    def _control(self, parent, campo: mantenimiento.Campo, bloqueado: bool) -> tk.Widget:
        valor = (self.datos or {}).get(campo.clave)
        if campo.tipo == "fecha":
            selector = SelectorFecha(parent, anio_min=2000, anio_max=2100, permitir_futuro=True)
            if valor:
                selector.establecer(valor)
            if bloqueado:
                selector.configure_estado("disabled")
            self.fechas[campo.clave] = selector
            return selector
        variable = tk.StringVar(value="" if valor is None else str(valor))
        self.variables[campo.clave] = variable
        if campo.tipo == "lista":
            control = ttk.Combobox(parent, textvariable=variable, values=list(campo.valores),
                                   state="disabled" if bloqueado else "readonly", width=34)
        elif campo.tipo == "dni":
            control = entry_dni(parent, textvariable=variable, width=36)
            if bloqueado:
                control.configure(state="readonly")
        else:
            control = ttk.Entry(parent, textvariable=variable, width=36,
                                state="readonly" if bloqueado else "normal")
        return control

    def valores(self) -> dict[str, str]:
        datos = {clave: variable.get().strip() for clave, variable in self.variables.items()}
        for clave, selector in self.fechas.items():
            datos[clave] = selector.obtener()
        return datos

    def _guardar(self) -> None:
        for clave, selector in self.fechas.items():
            campo = next(c for c in self.tabla.campos if c.clave == clave)
            if (campo.obligatorio or selector.obtener()) and not selector.validar():
                messagebox.showwarning("Fecha", f"{campo.etiqueta}: {selector.mensaje_error}", parent=self)
                return
        try:
            self.al_guardar(self.valores())
        except ErrorApp as exc:
            messagebox.showerror("No se guardó", str(exc), parent=self)
            return
        messagebox.showinfo("Listo", "Registro guardado.", parent=self)
        self.destroy()


class PestanaCrud(ttk.Frame):
    def __init__(self, parent, clave: str):
        super().__init__(parent)
        self.clave = clave
        self.tabla_crud = mantenimiento.TABLAS[clave]
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=5, pady=4)
        ttk.Button(barra, text="Nuevo", style="Primary.TButton", command=self.nuevo).pack(side="left", padx=3)
        self.btn_editar = ttk.Button(barra, text="Editar", command=self.editar)
        self.btn_editar.pack(side="left", padx=3)
        if not self.tabla_crud.permite_editar:
            self.btn_editar.configure(state="disabled")
        ttk.Button(barra, text="Eliminar", style="Danger.TButton", command=self.eliminar).pack(side="left", padx=3)
        ttk.Button(barra, text="Actualizar lista", command=self.recargar).pack(side="left", padx=3)
        CampoBusqueda(barra, etiqueta="Buscar:", comando=lambda t: self.tabla.filtrar(t)).pack(side="right", padx=5)
        columnas = list(self.tabla_crud.columnas)
        self.tabla = Tabla(self, columnas=columnas, anchos={c: 150 for c in columnas})
        self.tabla.pack(fill="both", expand=True, padx=5, pady=4)

    def recargar(self) -> None:
        try:
            self.tabla.cargar(mantenimiento.listar(self.clave))
        except ErrorApp as exc:
            messagebox.showerror("Error al cargar los datos", str(exc), parent=self)

    def _seleccion(self):
        fila = self.tabla.seleccion()
        if not fila:
            messagebox.showwarning("Atención", f"Seleccione un registro de {self.tabla_crud.titulo}.", parent=self)
        return fila

    def nuevo(self) -> None:
        sesion = auth.sesion_actual()

        def guardar(valores):
            mantenimiento.insertar(self.clave, valores, sesion.dni if sesion else None)
            self.recargar()

        FormularioGenerico(self.winfo_toplevel(), self.tabla_crud, guardar)

    def editar(self) -> None:
        fila = self._seleccion()
        if not fila:
            return

        def guardar(valores):
            mantenimiento.actualizar(self.clave, fila, valores)
            self.recargar()

        FormularioGenerico(self.winfo_toplevel(), self.tabla_crud, guardar, datos=fila)

    def eliminar(self) -> None:
        fila = self._seleccion()
        if not fila:
            return
        clave = ", ".join(str(fila.get(c, "")) for c in self.tabla_crud.parametros_eliminar)
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {self.tabla_crud.nombre} ({clave})?", parent=self):
            return
        try:
            mantenimiento.eliminar(self.clave, fila)
        except ErrorApp as exc:
            messagebox.showerror("No se pudo eliminar", str(exc), parent=self)
            return
        self.recargar()
        messagebox.showinfo("Listo", "Registro eliminado.", parent=self)
