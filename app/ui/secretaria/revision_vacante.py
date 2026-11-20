"""Revisión de una solicitud de vacante por la secretaria (Fase B).

Toda la información se obtiene con SELECT y ``sp_cupos_seccion``. Aceptar,
observar o rechazar solo modifica el JSON y mueve archivos: no se reserva cupo
ni se escribe en MySQL (§13.1).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app import errores
from app.servicios import matricula, solicitudes as sol, vacantes


class RevisionVacante(tk.Toplevel):
    """Muestra antecedentes y cupos por hijo y permite responder la vacante."""

    def __init__(self, parent, id_solicitud: str, al_cerrar=None):
        super().__init__(parent)
        self.title(f"AulaSync - Revisión de vacante {id_solicitud}")
        self.geometry("950x650")
        self.transient(parent)
        self.al_cerrar = al_cerrar
        try:
            self.datos = sol.obtener(id_solicitud)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            self.destroy()
            return
        if sol.etapa_de(self.datos) != "vacante":
            messagebox.showwarning("Atención", "Esta solicitud no es de vacante.", parent=self)
            self.destroy()
            return
        self.id_solicitud = id_solicitud
        self._construir()
        self._cargar_alumno(0)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _construir(self) -> None:
        superior = ttk.Frame(self, padding=8)
        superior.pack(fill="x")
        ttk.Label(
            superior,
            text=f"Solicitud {self.id_solicitud} — año {self.datos.get('anio', '')} "
                 f"— estado {self.datos.get('estado', '')}",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left")

        contacto = ttk.LabelFrame(self, text="Datos de contacto del apoderado", padding=8)
        contacto.pack(fill="x", padx=8)
        self.contacto = self.datos.get("contacto", {})
        ttk.Label(
            contacto,
            text=str(self.contacto.get("nombres_apoderado", "")),
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w")
        fila = ttk.Frame(contacto)
        fila.pack(fill="x", pady=4)
        self.celular_var = tk.StringVar(value=str(self.contacto.get("celular", "")))
        self.correo_var = tk.StringVar(value=str(self.contacto.get("correo", "")))
        ttk.Label(fila, text="Celular:").pack(side="left")
        ttk.Entry(fila, textvariable=self.celular_var, width=16, state="readonly").pack(side="left", padx=4)
        ttk.Button(fila, text="Copiar celular", command=self.copiar_celular).pack(side="left", padx=4)
        ttk.Label(fila, text="Correo:").pack(side="left", padx=(16, 4))
        ttk.Entry(fila, textvariable=self.correo_var, width=30, state="readonly").pack(side="left", padx=4)
        ttk.Button(fila, text="Copiar correo", command=self.copiar_correo).pack(side="left", padx=4)

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True, padx=8, pady=6)
        lista = ttk.LabelFrame(cuerpo, text="Hijos")
        lista.pack(side="left", fill="y", padx=(0, 6))
        self.alumnos_list = tk.Listbox(lista, width=26, height=10, exportselection=False)
        self.alumnos_list.pack(fill="y", padx=6, pady=6)
        self.alumnos_list.bind("<<ListboxSelect>>", self._alumno_seleccionado)
        for indice, alumno in enumerate(self.datos.get("alumnos", []), 1):
            ficha = alumno["ficha"]
            self.alumnos_list.insert(
                "end",
                f"{indice}. {ficha.get('ApellidoPaterno', '')} {ficha.get('Nombres', '')}",
            )

        self.detalle = ttk.LabelFrame(cuerpo, text="Antecedentes y vacantes", padding=8)
        self.detalle.pack(side="left", fill="both", expand=True)
        self.antecedentes_var = tk.StringVar(value="")
        ttk.Label(
            self.detalle, textvariable=self.antecedentes_var, wraplength=560,
            justify="left", anchor="nw",
        ).pack(fill="x")
        self.grado_var = tk.StringVar(value="")
        ttk.Label(self.detalle, textvariable=self.grado_var, wraplength=560).pack(
            fill="x", pady=6
        )
        self.total_var = tk.StringVar(value="Vacantes totales del grado: —")
        ttk.Label(
            self.detalle, textvariable=self.total_var, font=("TkDefaultFont", 10, "bold")
        ).pack(fill="x")
        self.cupos_tree = ttk.Treeview(
            self.detalle, columns=("Seccion", "Matriculados", "Vacantes"),
            show="headings", height=5,
        )
        for columna, texto, ancho in (
            ("Seccion", "Sección", 100),
            ("Matriculados", "Matriculados", 130),
            ("Vacantes", "Vacantes disponibles", 170),
        ):
            self.cupos_tree.heading(columna, text=texto)
            self.cupos_tree.column(columna, width=ancho)
        self.cupos_tree.pack(fill="both", expand=True, pady=6)

        notas = ttk.LabelFrame(self, text="Indicaciones para el padre", padding=6)
        notas.pack(fill="x", padx=8)
        self.notas = tk.Text(notas, height=4)
        self.notas.pack(fill="x")

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ttk.Button(barra, text="Registrar contacto", command=self.registrar_contacto).pack(side="left", padx=3)
        ttk.Button(barra, text="Observar", command=self.observar).pack(side="left", padx=3)
        ttk.Button(barra, text="Rechazar", command=self.rechazar).pack(side="left", padx=3)
        ttk.Button(barra, text="Aceptar vacante", command=self.aceptar).pack(side="right", padx=3)
        ttk.Button(barra, text="Cerrar", command=self._cerrar).pack(side="right", padx=3)

    def _copiar(self, valor: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(valor)
        messagebox.showinfo("Copiado", "El dato quedó en el portapapeles.", parent=self)

    def copiar_celular(self) -> None:
        self._copiar(self.celular_var.get())

    def copiar_correo(self) -> None:
        self._copiar(self.correo_var.get())

    def _indice_alumno(self) -> int | None:
        seleccion = self.alumnos_list.curselection()
        return int(seleccion[0]) if seleccion else None

    def _alumno_seleccionado(self, _evento=None) -> None:
        indice = self._indice_alumno()
        if indice is not None:
            self._cargar_alumno(indice)

    def _cargar_alumno(self, indice: int) -> None:
        alumnos = self.datos.get("alumnos", [])
        if indice >= len(alumnos):
            return
        self.alumnos_list.selection_clear(0, "end")
        self.alumnos_list.selection_set(indice)
        alumno = alumnos[indice]
        valores = sol.sincronizar_ficha_vacante(alumno)
        dni = valores["dni"]
        destino = alumno.get("destino", {})
        anio = int(self.datos.get("anio", 0) or 0)
        nivel, grado = destino.get("nivel", ""), destino.get("grado", "")

        try:
            historial = vacantes.historial_alumno(dni)
        except errores.ErrorApp as exc:
            historial = {"existe": False, "ultima": None, "error": str(exc)}
        if historial.get("existe") and historial.get("ultima"):
            ultima = historial["ultima"]
            texto = (
                f"Alumno de años anteriores: última matrícula {ultima.get('anio', '')}, "
                f"{ultima.get('nivel', '')} {ultima.get('grado', '')}, "
                f"sección {ultima.get('seccion', '')}, estado {ultima.get('estado', '')}."
            )
        elif historial.get("existe"):
            texto = "Alumno registrado, sin matrículas anteriores."
        else:
            texto = "Alumno nuevo (no registrado)."
        self.antecedentes_var.set(
            f"{valores['nombres']} {valores['apellido_paterno']} "
            f"{valores['apellido_materno']} — DNI {dni}\n"
            f"Condición declarada: {alumno.get('condicion_declarada', '')}\n"
            f"Destino solicitado: {nivel} {grado}\n{texto}"
        )

        self.grado_var.set("")
        if historial.get("existe"):
            try:
                situacion = vacantes.situacion_final(dni)
                if situacion:
                    nivel_anterior = situacion.get("nivel") or nivel
                    calculado = matricula.grado_siguiente(
                        nivel_anterior, situacion.get("grado", ""),
                        situacion.get("situacion", ""),
                    )
                    nivel_calculado = matricula.nivel_de_grado_siguiente(
                        nivel_anterior, situacion.get("grado", ""), calculado
                    )
                    coincide = calculado == grado and nivel_calculado == nivel
                    self.grado_var.set(
                        f"Grado sugerido: {nivel_calculado} {calculado}. "
                        + ("Coincide con lo solicitado."
                           if coincide else "ADVERTENCIA: no coincide con lo solicitado.")
                    )
                else:
                    self.grado_var.set(
                        "Sin situación final registrada: no se puede sugerir grado."
                    )
            except errores.ErrorApp as exc:
                self.grado_var.set(f"No se pudo calcular el grado sugerido: {exc}")

        self.cupos_tree.delete(*self.cupos_tree.get_children())
        try:
            filas = vacantes.cupos_por_seccion(anio, nivel, grado)
        except errores.ErrorApp as exc:
            self.grado_var.set(str(exc))
            filas = []
        for fila in filas:
            self.cupos_tree.insert("", "end", values=(
                fila["Seccion"], fila["Matriculados"], fila["Vacantes"],
            ))
        self.total_var.set(
            "Vacantes totales del grado: " + str(sum(fila["Vacantes"] for fila in filas))
        )
        if not filas:
            self.cupos_tree.insert("", "end", values=("—", "—", "Sin vacantes"))

    def registrar_contacto(self) -> None:
        texto = simpledialog.askstring(
            "Registrar contacto", "Cómo se realizó el contacto (teléfono/correo):",
            parent=self,
        )
        if not texto or not texto.strip():
            return
        try:
            sol.registrar_contacto(self.id_solicitud, texto.strip())
            messagebox.showinfo("Listo", "El contacto quedó registrado.", parent=self)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def observar(self) -> None:
        texto = simpledialog.askstring(
            "Observar vacante", "Qué debe corregir el apoderado:", parent=self
        )
        if not texto or not texto.strip():
            return
        try:
            sol.observar(self.id_solicitud, texto.strip())
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def rechazar(self) -> None:
        motivo = simpledialog.askstring(
            "Rechazar vacante", "Motivo del rechazo (por ejemplo: sin vacantes):",
            parent=self,
        )
        if not motivo or not motivo.strip():
            messagebox.showwarning("Atención", "El motivo es obligatorio.", parent=self)
            return
        try:
            sol.rechazar(self.id_solicitud, motivo.strip())
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def aceptar(self) -> None:
        indicaciones = self.notas.get("1.0", "end").strip() or (
            "Presentar DNI de los hijos y del apoderado, y la constancia de logros "
            "cuando corresponda."
        )
        if not messagebox.askyesno(
            "Confirmar",
            "¿Aceptar la vacante? No se reserva cupo ni se escribe en la base de datos.",
            parent=self,
        ):
            return
        try:
            sol.aceptar_vacante(self.id_solicitud, indicaciones)
            messagebox.showinfo(
                "Listo",
                "Vacante aceptada. El apoderado ya puede completar la matrícula.",
                parent=self,
            )
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def _cerrar(self) -> None:
        if self.al_cerrar:
            self.al_cerrar()
        self.destroy()
