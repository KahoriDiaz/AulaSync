"""Bandeja de solicitudes de la secretaria (§6.3 punto 1).

Solo lee los JSON de ``data/solicitudes``; ninguna solicitud pendiente ejecuta
un procedimiento de escritura en MySQL (§13.1).
"""
from __future__ import annotations

from datetime import date

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app import errores
from app.servicios import solicitudes
from app.ui.componentes import Tabla
from app.ui.tema import tarjeta
from app.ui.secretaria.revision import RevisionSolicitud
from app.ui.secretaria.revision_vacante import RevisionVacante

COLUMNAS = ("ID", "Año", "Etapa", "Estado", "Solicitante", "Fecha envío", "Alumnos")


class BandejaSolicitudes(ttk.Frame):
    """Lista de solicitudes enviadas con filtros y acciones de revisión."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._construir()
        self.recargar()

    def _construir(self) -> None:
        acciones = tarjeta(self)
        acciones.pack(fill="x", padx=8, pady=(8, 6))
        ttk.Label(acciones, text="Acciones", style="Card.Seccion.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        barra = ttk.Frame(acciones, style="SobreTarjeta.TFrame")
        barra.pack(fill="x")
        ttk.Button(barra, text="Revisar", style="Primary.TButton",
                   command=self.revisar).pack(side="left", padx=(0, 6))
        ttk.Button(barra, text="Observar", command=self.observar).pack(side="left", padx=3)
        ttk.Button(barra, text="Rechazar", style="Danger.TButton",
                   command=self.rechazar).pack(side="left", padx=3)
        ttk.Button(barra, text="Actualizar lista", command=self.recargar).pack(side="right", padx=3)

        filtros = tarjeta(self)
        filtros.pack(fill="x", padx=8, pady=6)
        ttk.Label(filtros, text="Año:", style="Card.TLabel").pack(side="left", padx=4)
        self.anio_var = tk.StringVar(value=str(date.today().year + 1))
        ttk.Entry(filtros, textvariable=self.anio_var, width=8).pack(side="left")
        ttk.Label(filtros, text="Estado:", style="Card.TLabel").pack(side="left", padx=8)
        self.estado_var = tk.StringVar(value="Todas")
        ttk.Combobox(
            filtros, textvariable=self.estado_var, state="readonly",
            values=("Todas",) + solicitudes.ESTADOS,
        ).pack(side="left")
        ttk.Label(filtros, text="Etapa:", style="Card.TLabel").pack(side="left", padx=8)
        self.etapa_var = tk.StringVar(value="Todas")
        ttk.Combobox(
            filtros, textvariable=self.etapa_var, state="readonly",
            values=("Todas", "Vacante", "Matrícula"),
        ).pack(side="left")
        self.contador_var = tk.StringVar(value="Pendientes: 0 | Vacantes por atender: 0")
        ttk.Label(filtros, textvariable=self.contador_var,
                  style="Card.Seccion.TLabel").pack(side="right", padx=8)

        self.tabla = Tabla(self, columnas=COLUMNAS, anchos={"ID": 160, "Solicitante": 130})
        self.tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def recargar(self) -> None:
        """Vuelve a leer la bandeja y aplica los filtros seleccionados."""
        try:
            datos = solicitudes.listar_solicitudes("pendientes")
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
            return
        pendientes = sum(1 for s in datos if s.get("estado") == "Enviada")
        vacantes = sum(
            1 for s in datos
            if s.get("estado") == "Enviada" and solicitudes.etapa_de(s) == "vacante"
        )
        atrasadas = sum(1 for s in datos if solicitudes.sin_respuesta(s))
        self.contador_var.set(
            f"Pendientes: {pendientes} | Vacantes por atender: {vacantes} "
            f"| Sin respuesta >7 días: {atrasadas}"
        )
        anio = self.anio_var.get().strip()
        estado = self.estado_var.get()
        etapa = self.etapa_var.get()
        filas = []
        for solicitud in datos:
            if anio and str(solicitud.get("anio", "")) != anio:
                continue
            if estado != "Todas" and solicitud.get("estado") != estado:
                continue
            etapa_actual = solicitudes.etapa_de(solicitud)
            if etapa == "Vacante" and etapa_actual != "vacante":
                continue
            if etapa == "Matrícula" and etapa_actual != "matricula":
                continue
            atrasada = solicitudes.sin_respuesta(solicitud)
            filas.append({
                "ID": solicitud.get("id", ""),
                "Año": solicitud.get("anio", ""),
                "Etapa": "Vacante" if etapa_actual == "vacante" else "Matrícula",
                "Estado": ("⚠ " if atrasada else "") + solicitudes.texto_estado(solicitud),
                "Solicitante": solicitud.get("dni_solicitante", ""),
                "Fecha envío": solicitud.get("fecha_envio") or "-",
                "Alumnos": len(solicitud.get("alumnos", [])),
                "_tag": "atencion" if atrasada else "",
            })
        self.tabla.cargar(filas)

    def _id_seleccionado(self) -> str | None:
        fila = self.tabla.seleccion()
        if not fila:
            messagebox.showwarning("Atención", "Seleccione una solicitud.")
            return None
        return str(fila.get("ID") or "")

    def revisar(self) -> None:
        id_solicitud = self._id_seleccionado()
        if not id_solicitud:
            return
        try:
            datos = solicitudes.obtener(id_solicitud)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
            return
        if solicitudes.etapa_de(datos) == "vacante":
            RevisionVacante(self, id_solicitud, al_cerrar=self.recargar)
        else:
            RevisionSolicitud(self, id_solicitud, al_cerrar=self.recargar)

    def observar(self) -> None:
        id_solicitud = self._id_seleccionado()
        if not id_solicitud:
            return
        texto = simpledialog.askstring(
            "Observar solicitud", "Escriba la observación para el padre:", parent=self
        )
        if not texto or not texto.strip():
            return
        try:
            solicitudes.observar(id_solicitud, texto.strip())
            messagebox.showinfo("Listo", "La solicitud quedó observada.")
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
        self.recargar()

    def rechazar(self) -> None:
        id_solicitud = self._id_seleccionado()
        if not id_solicitud:
            return
        motivo = simpledialog.askstring(
            "Rechazar solicitud", "Motivo del rechazo:", parent=self
        )
        if not motivo or not motivo.strip():
            return
        if not messagebox.askyesno("Confirmar", "¿Rechazar esta solicitud?"):
            return
        try:
            solicitudes.rechazar(id_solicitud, motivo.strip())
            messagebox.showinfo("Listo", "La solicitud fue rechazada.")
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc))
        self.recargar()
