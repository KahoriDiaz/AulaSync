"""Bandeja «Mis solicitudes» del padre/apoderado (§6.2 punto 1).

Muestra únicamente las solicitudes del usuario con sesión activa; el filtro se
aplica también en la capa de servicios, no solo en esta pantalla.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import errores
from app.servicios import solicitudes
from app.ui.componentes import Tabla
from app.ui.padre.asistente_solicitud import AsistenteSolicitud

COLUMNAS = ("ID", "Año", "Estado", "Fecha envío", "Alumnos")


class MisSolicitudes(ttk.Frame):
    """Lista de solicitudes propias con acceso al asistente y observaciones."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._construir()
        self.recargar()

    def _construir(self) -> None:
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=6, pady=6)
        ttk.Button(barra, text="Nueva solicitud", command=self.nueva_solicitud).pack(side="left", padx=3)
        ttk.Button(barra, text="Editar / continuar", command=self.editar_solicitud).pack(side="left", padx=3)
        ttk.Button(barra, text="Ver observaciones", command=self.ver_observaciones).pack(side="left", padx=3)
        ttk.Button(barra, text="Actualizar lista", command=self.recargar).pack(side="right", padx=3)

        self.tabla = Tabla(self, columnas=COLUMNAS, anchos={"ID": 150, "Año": 80, "Estado": 110})
        self.tabla.pack(fill="both", expand=True, padx=6, pady=6)

    def recargar(self) -> None:
        """Vuelve a leer la bandeja del padre."""
        try:
            datos = solicitudes.listar_solicitudes("pendientes")
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
            return
        filas = [
            {
                "ID": s.get("id", ""),
                "Año": s.get("anio", ""),
                "Estado": s.get("estado", ""),
                "Fecha envío": s.get("fecha_envio") or "-",
                "Alumnos": len(s.get("alumnos", [])),
            }
            for s in datos
        ]
        self.tabla.cargar(filas)

    def _id_seleccionado(self) -> str | None:
        fila = self.tabla.seleccion()
        if not fila:
            messagebox.showwarning("Atención", "Seleccione una solicitud.")
            return None
        return str(fila.get("ID") or "")

    def nueva_solicitud(self) -> None:
        """Abre el asistente para crear una solicitud nueva."""
        AsistenteSolicitud(self, al_cerrar=self.recargar)

    def editar_solicitud(self) -> None:
        """Abre el asistente con una solicitud en Borrador u Observada."""
        id_solicitud = self._id_seleccionado()
        if not id_solicitud:
            return
        try:
            datos = solicitudes.obtener(id_solicitud)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
            return
        if datos["estado"] not in ("Borrador", "Observada"):
            messagebox.showwarning("Atención", "Esa solicitud ya no puede modificarse.")
            return
        AsistenteSolicitud(self, id_solicitud=id_solicitud, al_cerrar=self.recargar)

    def ver_observaciones(self) -> None:
        """Muestra las observaciones escritas por la secretaria."""
        id_solicitud = self._id_seleccionado()
        if not id_solicitud:
            return
        try:
            datos = solicitudes.obtener(id_solicitud)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
            return
        observaciones = datos.get("observaciones", [])
        if not observaciones:
            messagebox.showinfo("Observaciones", "La solicitud no tiene observaciones.")
            return
        texto = "\n\n".join(
            f"{o.get('fecha', '')} — {o.get('de', '')}:\n{o.get('texto', '')}"
            for o in observaciones
        )
        messagebox.showinfo("Observaciones de la secretaria", texto)
