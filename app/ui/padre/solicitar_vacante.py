"""Etapa 1: solicitud de vacante del padre/apoderado (Fase B).

Formulario corto (un solo diálogo): contacto, hijos y destino solicitado.
La disponibilidad que se muestra es referencial y se calcula con
``sp_cupos_seccion``; no reserva cupo ni escribe en MySQL.
"""
from __future__ import annotations

from datetime import date

import tkinter as tk
from tkinter import messagebox, ttk

from app import errores
from app.servicios import solicitudes as sol, vacantes
from app.ui.componentes import entry_dni
from app.ui.tema import ALERTA, aplicar_tema, cabecera

COLUMNAS = ("DNI", "Nombres", "Apellidos", "Nacimiento", "Nivel", "Grado", "Condición")
AVISO = (
    "Disponibilidad referencial. La vacante se confirma cuando la secretaria "
    "acepte su solicitud."
)


class DialogoHijo(tk.Toplevel):
    """Diálogo modal para agregar o editar un hijo de la solicitud."""

    def __init__(self, parent, hijo: dict | None = None):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Datos del hijo")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.resultado: dict | None = None
        self.hijo = hijo or sol.nuevo_alumno_vacante()
        self.vars: dict[str, tk.StringVar] = {}
        self._construir()
        self._cargar()

    def _construir(self) -> None:
        marco = ttk.Frame(self, padding=14)
        marco.pack(fill="both", expand=True)
        campos = (
            ("dni", "DNI (8 dígitos)"),
            ("nombres", "Nombres"),
            ("apellido_paterno", "Apellido paterno"),
            ("apellido_materno", "Apellido materno"),
            ("fecha_nacimiento", "Fecha de nacimiento (AAAA-MM-DD)"),
        )
        for fila, (clave, texto) in enumerate(campos):
            ttk.Label(marco, text=texto).grid(row=fila, column=0, sticky="w", pady=3)
            variable = tk.StringVar()
            fabrica = entry_dni if clave == "dni" else ttk.Entry
            fabrica(marco, textvariable=variable, width=26).grid(row=fila, column=1)
            self.vars[clave] = variable

        ttk.Label(marco, text="Nivel").grid(row=5, column=0, sticky="w", pady=3)
        self.nivel_var = tk.StringVar()
        ttk.Combobox(
            marco, textvariable=self.nivel_var, values=tuple(sol.NIVELES),
            state="readonly", width=23,
        ).grid(row=5, column=1)
        self.nivel_var.trace_add("write", lambda *_: self._nivel_cambiado())

        ttk.Label(marco, text="Grado al que postula").grid(row=6, column=0, sticky="w", pady=3)
        self.grado_var = tk.StringVar()
        self.grado_combo = ttk.Combobox(marco, textvariable=self.grado_var, state="readonly", width=23)
        self.grado_combo.grid(row=6, column=1)
        self.grado_var.trace_add("write", lambda *_: self._actualizar_vacantes())

        ttk.Label(marco, text="Condición declarada").grid(row=7, column=0, sticky="w", pady=3)
        self.condicion_var = tk.StringVar()
        ttk.Combobox(
            marco, textvariable=self.condicion_var, values=("Nuevo", "Continuador"),
            state="readonly", width=23,
        ).grid(row=7, column=1)

        self.vacantes_var = tk.StringVar(value="Vacantes disponibles: —")
        ttk.Label(marco, textvariable=self.vacantes_var, foreground="#1256a0").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Label(marco, text=AVISO, wraplength=330, foreground="#6a5d00").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(4, 8)
        )

        botones = ttk.Frame(marco)
        botones.grid(row=10, column=0, columnspan=2, pady=6)
        ttk.Button(botones, text="Aceptar", command=self.aceptar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="left", padx=4)

    def _cargar(self) -> None:
        valores = sol.sincronizar_ficha_vacante(self.hijo)
        for clave, variable in self.vars.items():
            variable.set(valores[clave])
        destino = self.hijo.get("destino", {})
        self.nivel_var.set(destino.get("nivel", "Primaria"))
        self._nivel_cambiado()
        self.grado_var.set(destino.get("grado", sol.NIVELES["Primaria"][0]))
        self.condicion_var.set(self.hijo.get("condicion_declarada", "Nuevo"))
        self._actualizar_vacantes()

    def _nivel_cambiado(self) -> None:
        nivel = self.nivel_var.get()
        grados = sol.NIVELES.get(nivel, ())
        self.grado_combo["values"] = grados
        if self.grado_var.get() not in grados:
            self.grado_var.set(grados[0] if grados else "")
        self._actualizar_vacantes()

    def _actualizar_vacantes(self) -> None:
        nivel, grado = self.nivel_var.get(), self.grado_var.get()
        if not nivel or not grado:
            self.vacantes_var.set("Vacantes disponibles: —")
            return
        try:
            # El año se ajusta al guardar; aquí se usa el vigente como referencia.
            total = vacantes.vacantes_por_grado(date.today().year + 1, nivel, grado)
            self.vacantes_var.set(
                f"Vacantes disponibles: {total}" if total else "Sin vacantes"
            )
        except errores.ErrorApp:
            self.vacantes_var.set("Disponibilidad no disponible en este momento")

    def aceptar(self) -> None:
        self.resultado = {
            "ficha": {
                clave: variable.get().strip() for clave, variable in self.vars.items()
            },
            "destino": {
                "nivel": self.nivel_var.get(), "grado": self.grado_var.get(),
            },
            "condicion_declarada": self.condicion_var.get(),
        }
        sol.sincronizar_ficha_vacante(self.resultado)
        self.destroy()


class SolicitarVacante(tk.Toplevel):
    """Formulario de solicitud de vacante para uno o varios hermanos."""

    def __init__(self, parent, id_solicitud: str | None = None, al_cerrar=None):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Solicitar vacante")
        self.geometry("900x520")
        self.transient(parent)
        self.grab_set()
        self.al_cerrar = al_cerrar
        try:
            self.datos = (
                sol.obtener(id_solicitud) if id_solicitud
                else sol.crear_borrador(date.today().year + 1, etapa="vacante")
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            self.destroy()
            return
        if sol.etapa_de(self.datos) != "vacante":
            messagebox.showwarning(
                "Atención", "Esta solicitud ya pasó a la etapa de matrícula.", parent=self
            )
            self.destroy()
            return
        self.id_solicitud = str(self.datos["id"])
        self.hijos = [dict(hijo) for hijo in self.datos.get("alumnos", [])]
        self._construir()
        self._cargar()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _construir(self) -> None:
        cabecera(self, "AulaSync", "Solicitud de vacante").pack(fill="x")
        superior = ttk.Frame(self, padding=8)
        superior.pack(fill="x")
        ttk.Label(superior, text="Año escolar:").pack(side="left")
        self.anio_var = tk.StringVar()
        anios = (date.today().year, date.today().year + 1)
        ttk.Combobox(
            superior, textvariable=self.anio_var, values=tuple(map(str, anios)),
            state="readonly", width=10,
        ).pack(side="left", padx=6)

        contacto = ttk.LabelFrame(self, text="Datos de contacto del apoderado", padding=8)
        contacto.pack(fill="x", padx=8)
        self.contacto_vars: dict[str, tk.StringVar] = {}
        for indice, (clave, texto) in enumerate((
            ("nombres_apoderado", "Nombres y apellidos"),
            ("celular", "Celular"),
            ("correo", "Correo electrónico"),
        )):
            ttk.Label(contacto, text=texto).grid(row=0, column=indice * 2, sticky="w", padx=4)
            variable = tk.StringVar()
            ttk.Entry(contacto, textvariable=variable, width=26).grid(
                row=0, column=indice * 2 + 1, padx=4
            )
            self.contacto_vars[clave] = variable

        hijos = ttk.LabelFrame(self, text="Hijos (máximo 6)", padding=6)
        hijos.pack(fill="both", expand=True, padx=8, pady=6)
        botonera = ttk.Frame(hijos)
        botonera.pack(fill="x")
        ttk.Button(botonera, text="Agregar hijo", command=self.agregar_hijo).pack(side="left", padx=3)
        ttk.Button(botonera, text="Editar", command=self.editar_hijo).pack(side="left", padx=3)
        ttk.Button(botonera, text="Quitar", command=self.quitar_hijo).pack(side="left", padx=3)

        self.tabla = ttk.Treeview(hijos, columns=COLUMNAS, show="headings", height=8)
        for columna, texto, ancho in zip(
            COLUMNAS,
            ("DNI", "Nombres", "Apellidos", "Nacimiento", "Nivel", "Grado", "Condición"),
            (100, 120, 170, 110, 90, 70, 100),
        ):
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho)
        self.tabla.pack(fill="both", expand=True, pady=6)

        ttk.Label(self, text=AVISO, foreground=ALERTA, wraplength=780).pack(pady=(0, 4))
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=8, pady=8)
        ttk.Button(acciones, text="Guardar borrador",
                   command=lambda: self.guardar(False)).pack(side="left", padx=4)
        ttk.Button(acciones, text="Enviar solicitud de vacante", style="Accent.TButton",
                   command=lambda: self.guardar(True)).pack(side="left", padx=4)
        ttk.Button(acciones, text="Cancelar", command=self._cerrar).pack(side="right", padx=4)

    def _cargar(self) -> None:
        self.anio_var.set(str(self.datos.get("anio", date.today().year + 1)))
        contacto = self.datos.get("contacto", {})
        for clave, variable in self.contacto_vars.items():
            variable.set(str(contacto.get(clave, "")))
        self._recargar_tabla()

    def _recargar_tabla(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for hijo in self.hijos:
            valores = sol.sincronizar_ficha_vacante(hijo)
            destino = hijo.get("destino", {})
            self.tabla.insert("", "end", values=(
                valores["dni"], valores["nombres"],
                f"{valores['apellido_paterno']} {valores['apellido_materno']}".strip(),
                valores["fecha_nacimiento"], destino.get("nivel", ""),
                destino.get("grado", ""), hijo.get("condicion_declarada", ""),
            ))

    def _hijo_seleccionado(self) -> int | None:
        seleccion = self.tabla.selection()
        return int(seleccion[0]) if seleccion else None

    def agregar_hijo(self) -> None:
        if len(self.hijos) >= sol.MAXIMO_ALUMNOS:
            messagebox.showwarning("Atención", f"Máximo {sol.MAXIMO_ALUMNOS} hijos.", parent=self)
            return
        dialogo = DialogoHijo(self)
        self.wait_window(dialogo)
        if dialogo.resultado:
            self.hijos.append(dialogo.resultado)
            self._recargar_tabla()

    def editar_hijo(self) -> None:
        indice = self._hijo_seleccionado()
        if indice is None:
            messagebox.showwarning("Atención", "Seleccione un hijo.", parent=self)
            return
        dialogo = DialogoHijo(self, self.hijos[indice])
        self.wait_window(dialogo)
        if dialogo.resultado:
            self.hijos[indice] = dialogo.resultado
            self._recargar_tabla()

    def quitar_hijo(self) -> None:
        indice = self._hijo_seleccionado()
        if indice is None:
            messagebox.showwarning("Atención", "Seleccione un hijo.", parent=self)
            return
        self.hijos.pop(indice)
        self._recargar_tabla()

    def guardar(self, enviar: bool) -> None:
        cambios = {
            "anio": int(self.anio_var.get()),
            "contacto": {
                clave: variable.get().strip()
                for clave, variable in self.contacto_vars.items()
            },
            "alumnos": self.hijos,
        }
        try:
            sol.actualizar(self.id_solicitud, cambios)
            if enviar:
                sol.enviar(self.id_solicitud)
        except (errores.ErrorApp, ValueError) as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)
            return
        mensaje = (
            "Solicitud de vacante enviada. La secretaria revisará su pedido."
            if enviar else "Borrador guardado."
        )
        messagebox.showinfo("Listo", mensaje, parent=self)
        self._cerrar()

    def _cerrar(self) -> None:
        if self.al_cerrar:
            self.al_cerrar()
        self.destroy()
