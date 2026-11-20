"""Revisión de una solicitud y «Aprobar y matricular» (§6.3 puntos 2 y 3).

El OCR y la bandeja son auxiliares: la secretaria confirma lo visto en la
plataforma externa antes de ejecutar la transacción en MySQL.
"""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app import errores
from app.config import config
from app.servicios import matricula, solicitudes


class RevisionSolicitud(tk.Toplevel):
    """Ventana de revisión por alumno de una solicitud enviada."""

    def __init__(self, parent, id_solicitud: str, al_cerrar=None):
        super().__init__(parent)
        self.title(f"AulaSync - Revisión de {id_solicitud}")
        self.geometry("1050x700")
        self.transient(parent)
        self.al_cerrar = al_cerrar
        try:
            self.datos = solicitudes.obtener(id_solicitud)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            self.destroy()
            return
        self.id_solicitud = id_solicitud
        self.decisiones = self._decisiones_iniciales()
        self._construir()
        self._cargar_alumno(0)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _decisiones_iniciales(self) -> dict[str, dict]:
        resultado: dict[str, dict] = {}
        for alumno in self.datos.get("alumnos", []):
            dni = str(alumno["ficha"].get("DNI", ""))
            verificacion = alumno.get("verificacion", {})
            constancia = alumno.get("constancia", {})
            logros = constancia.get("logros", [])
            ultimo = max(logros, key=lambda f: int(f.get("anio", 0))) if logros else {}
            resultado[dni] = {
                "dni": dni,
                "seccion": verificacion.get("seccion", "A"),
                "sin_constancia": bool(constancia.get("sin_constancia")),
                "situacion": verificacion.get("situacion") or ultimo.get("situacion", "APROBADO"),
                "nivel_ultimo": verificacion.get("nivel_ultimo")
                or constancia.get("nivel_educativo") or "",
                "grado_ultimo": verificacion.get("grado_ultimo") or ultimo.get("grado", ""),
                "ultimo_anio": verificacion.get("ultimo_anio") or ultimo.get("anio", ""),
            }
        return resultado

    # ------------------------------------------------------------ estructura
    def _construir(self) -> None:
        superior = ttk.Frame(self)
        superior.pack(fill="x", padx=8, pady=6)
        ttk.Label(
            superior,
            text=f"Solicitud {self.id_solicitud} — año {self.datos.get('anio', '')} "
                 f"— estado {self.datos.get('estado', '')}",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left")

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True, padx=8, pady=4)
        lista = ttk.LabelFrame(cuerpo, text="Alumnos (hermanos)")
        lista.pack(side="left", fill="y", padx=(0, 6))
        self.alumnos_list = tk.Listbox(lista, width=26, height=12, exportselection=False)
        self.alumnos_list.pack(fill="y", padx=6, pady=6)
        self.alumnos_list.bind("<<ListboxSelect>>", self._alumno_seleccionado)
        for indice, alumno in enumerate(self.datos.get("alumnos", []), 1):
            ficha = alumno["ficha"]
            self.alumnos_list.insert(
                "end",
                f"{indice}. {ficha.get('ApellidoPaterno', '')} {ficha.get('Nombres', '')}",
            )

        self.detalle = ttk.Notebook(cuerpo)
        self.detalle.pack(side="left", fill="both", expand=True)
        self._pestana_datos()
        self._pestana_documentos()
        self._pestana_verificacion()

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ttk.Button(barra, text="Observar", command=self.observar).pack(side="left", padx=3)
        ttk.Button(barra, text="Rechazar", command=self.rechazar).pack(side="left", padx=3)
        ttk.Button(barra, text="Aprobar y matricular", command=self.aprobar).pack(side="right", padx=3)
        ttk.Button(barra, text="Cerrar", command=self._cerrar).pack(side="right", padx=3)

    def _pestana_datos(self) -> None:
        pagina = ttk.Frame(self.detalle)
        self.detalle.add(pagina, text="Datos de la solicitud")
        self.datos_tree = ttk.Treeview(
            pagina, columns=("Campo", "Valor"), show="headings"
        )
        self.datos_tree.heading("Campo", text="Campo")
        self.datos_tree.heading("Valor", text="Valor")
        self.datos_tree.column("Campo", width=260)
        self.datos_tree.column("Valor", width=620)
        self.datos_tree.pack(fill="both", expand=True, padx=6, pady=6)

    def _pestana_documentos(self) -> None:
        pagina = ttk.Frame(self.detalle)
        self.detalle.add(pagina, text="Documentos adjuntos")
        marco = ttk.LabelFrame(pagina, text="Archivos del alumno seleccionado")
        marco.pack(fill="both", expand=True, padx=8, pady=8)
        self.documentos_tree = ttk.Treeview(
            marco, columns=("Tipo", "Archivo"), show="headings", height=6
        )
        self.documentos_tree.heading("Tipo", text="Tipo")
        self.documentos_tree.heading("Archivo", text="Archivo")
        self.documentos_tree.column("Tipo", width=160)
        self.documentos_tree.column("Archivo", width=500)
        self.documentos_tree.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Button(marco, text="Abrir con el visor del sistema", command=self.abrir_documento).pack(
            side="left", padx=6, pady=6
        )
        self.logros_tree = ttk.Treeview(
            pagina, columns=("Anio", "Grado", "IE", "Situacion"), show="headings", height=6
        )
        for columna, texto, ancho in (
            ("Anio", "Año", 90), ("Grado", "Grado", 110),
            ("IE", "I.E.", 240), ("Situacion", "Situación", 240),
        ):
            self.logros_tree.heading(columna, text=texto)
            self.logros_tree.column(columna, width=ancho)
        ttk.Label(pagina, text="Logros registrados en la constancia:").pack(anchor="w", padx=10)
        self.logros_tree.pack(fill="both", expand=True, padx=8, pady=6)

    def _pestana_verificacion(self) -> None:
        pagina = ttk.Frame(self.detalle)
        self.detalle.add(pagina, text="Verificación y matrícula")
        consulta = ttk.LabelFrame(pagina, text="Consulta externa (MINEDU)")
        consulta.pack(fill="x", padx=8, pady=6)
        self.codigo_var = tk.StringVar()
        ttk.Label(consulta, text="Código virtual:").pack(side="left", padx=4)
        ttk.Entry(consulta, textvariable=self.codigo_var, width=16).pack(side="left")
        ttk.Button(consulta, text="Consultar constancia en MINEDU", command=self.consultar_minedu).pack(
            side="left", padx=6
        )

        datos = ttk.LabelFrame(pagina, text="Lo que se ve en la plataforma")
        datos.pack(fill="x", padx=8, pady=6)
        self.decision_vars: dict[str, tk.StringVar] = {
            "ultimo_anio": tk.StringVar(), "nivel_ultimo": tk.StringVar(),
            "grado_ultimo": tk.StringVar(), "situacion": tk.StringVar(value="APROBADO"),
            "seccion": tk.StringVar(value="A"),
        }
        ttk.Label(datos, text="Último año:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(datos, textvariable=self.decision_vars["ultimo_anio"], width=10).grid(row=0, column=1)
        ttk.Label(datos, text="Nivel:").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Combobox(
            datos, textvariable=self.decision_vars["nivel_ultimo"], width=12,
            values=tuple(solicitudes.NIVELES), state="readonly",
        ).grid(row=0, column=3)
        ttk.Label(datos, text="Grado cursado:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(datos, textvariable=self.decision_vars["grado_ultimo"], width=10).grid(row=1, column=1)
        ttk.Label(datos, text="Situación final:").grid(row=1, column=2, sticky="w", padx=4)
        ttk.Combobox(
            datos, textvariable=self.decision_vars["situacion"], width=22,
            values=solicitudes.SITUACIONES_FINALES, state="readonly",
        ).grid(row=1, column=3)
        ttk.Label(datos, text="Sección:").grid(row=2, column=0, sticky="w", padx=4, pady=3)
        self.seccion_combo = ttk.Combobox(
            datos, textvariable=self.decision_vars["seccion"], width=8, state="readonly"
        )
        self.seccion_combo.grid(row=2, column=1)
        self.sin_constancia_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            datos, text="Sin constancia (ingresante)", variable=self.sin_constancia_var,
            command=self._sin_constancia_cambiado,
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=4)

        resultado = ttk.LabelFrame(pagina, text="Resultado del cálculo")
        resultado.pack(fill="x", padx=8, pady=6)
        self.grado_calculado_var = tk.StringVar(value="—")
        self.coincide_var = tk.StringVar(value="—")
        ttk.Label(resultado, text="Grado que corresponde:").pack(side="left", padx=4)
        ttk.Label(resultado, textvariable=self.grado_calculado_var, font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Label(resultado, textvariable=self.coincide_var, foreground="#8a1c1c").pack(side="left", padx=12)
        ttk.Button(resultado, text="Calcular grado", command=self.calcular_grado).pack(side="right", padx=3)
        ttk.Button(resultado, text="Ver cupos de sección", command=self.ver_cupos).pack(side="right", padx=3)

    # ------------------------------------------------------------ navegación
    def _indice_alumno(self) -> int | None:
        seleccion = self.alumnos_list.curselection()
        return int(seleccion[0]) if seleccion else None

    def _alumno_seleccionado(self, _evento=None) -> None:
        self._sincronizar_decision()
        indice = self._indice_alumno()
        if indice is not None:
            self._cargar_alumno(indice)

    def _sincronizar_decision(self) -> None:
        indice = self._indice_alumno()
        if indice is None or not hasattr(self, "decision_vars"):
            return
        alumnos = self.datos.get("alumnos", [])
        if indice >= len(alumnos):
            return
        dni = str(alumnos[indice]["ficha"].get("DNI", ""))
        decision = self.decisiones.setdefault(dni, {"dni": dni})
        for clave, variable in self.decision_vars.items():
            decision[clave] = variable.get()
        decision["sin_constancia"] = self.sin_constancia_var.get()
        decision["codigo_virtual"] = self.codigo_var.get()

    def _cargar_alumno(self, indice: int) -> None:
        alumnos = self.datos.get("alumnos", [])
        if indice >= len(alumnos):
            return
        self.alumnos_list.selection_clear(0, "end")
        self.alumnos_list.selection_set(indice)
        alumno = alumnos[indice]
        dni = str(alumno["ficha"].get("DNI", ""))
        decision = self.decisiones.setdefault(dni, {"dni": dni})

        self.datos_tree.delete(*self.datos_tree.get_children())
        for clave, valor in alumno["ficha"].items():
            self.datos_tree.insert("", "end", values=(f"Alumno.{clave}", valor))
        for clave, valor in alumno.get("destino", {}).items():
            self.datos_tree.insert("", "end", values=(f"Destino.{clave}", valor))
        contacto = self.datos.get("contacto_emergencia", {})
        self.datos_tree.insert(
            "", "end", values=(
                "Contacto de emergencia",
                f"{contacto.get('nombre', '')} — {contacto.get('celular', '')}",
            )
        )
        for numero, padre in enumerate(self.datos.get("padres", []), 1):
            self.datos_tree.insert(
                "", "end",
                values=(f"Padre {numero} ({padre.get('vinculo', '')})",
                        f"{padre.get('Nombres', '')} {padre.get('ApellidoPaterno', '')} "
                        f"DNI {padre.get('DNI', '')}"),
            )
        self.datos_tree.insert(
            "", "end", values=("Responsable", self.datos.get("dni_responsable") or "-")
        )

        self.documentos_tree.delete(*self.documentos_tree.get_children())
        for tipo, ruta in alumno.get("docs", {}).items():
            if ruta:
                self.documentos_tree.insert("", "end", values=(tipo, ruta))
        for numero, padre in enumerate(self.datos.get("padres", []), 1):
            ruta = padre.get("docs", {}).get("dni")
            if ruta:
                self.documentos_tree.insert("", "end", values=(f"DNI padre {numero}", ruta))

        self.logros_tree.delete(*self.logros_tree.get_children())
        for fila in alumno.get("constancia", {}).get("logros", []):
            self.logros_tree.insert("", "end", values=(
                fila.get("anio", ""), fila.get("grado", ""),
                fila.get("codigo_modular_ie", ""), fila.get("situacion", ""),
            ))

        constancia = alumno.get("constancia", {})
        self.codigo_var.set(decision.get("codigo_virtual") or constancia.get("codigo_virtual") or "")
        self.sin_constancia_var.set(bool(decision.get("sin_constancia", constancia.get("sin_constancia"))))
        for clave, variable in self.decision_vars.items():
            variable.set(str(decision.get(clave, "")))
        destino = alumno.get("destino", {})
        self.seccion_combo["values"] = matricula.SECCIONES.get(destino.get("nivel", ""), ())
        if self.decision_vars["seccion"].get() not in self.seccion_combo["values"]:
            self.decision_vars["seccion"].set(
                self.seccion_combo["values"][0] if self.seccion_combo["values"] else "A"
            )
        self.grado_calculado_var.set("—")
        self.coincide_var.set("—")
        self._sin_constancia_cambiado()

    def _sin_constancia_cambiado(self) -> None:
        self._sincronizar_decision()
        sin = self.sin_constancia_var.get()
        self.codigo_var.set("" if sin else self.codigo_var.get())
        if sin:
            self.grado_calculado_var.set(matricula.SIN_CONSTANCIA)
            self.coincide_var.set("Sin constancia: no se exige coincidencia de grado.")

    # -------------------------------------------------------------- acciones
    def consultar_minedu(self) -> None:
        self._sincronizar_decision()
        codigo = self.codigo_var.get().strip()
        if not codigo:
            messagebox.showwarning("Atención", "Ingrese el código virtual de la constancia.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(codigo)
        url = str(config.url_consulta_constancia or "").strip()
        if not url:
            messagebox.showinfo(
                "Código copiado",
                f"El código {codigo} quedó en el portapapeles.\n"
                "Configure url_consulta_constancia en config.ini para abrir la plataforma.",
                parent=self,
            )
            return
        webbrowser.open(url)
        messagebox.showinfo(
            "Consulta externa", f"Se copió el código {codigo} y se abrió la URL configurada.",
            parent=self,
        )

    def abrir_documento(self) -> None:
        seleccion = self.documentos_tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un documento.", parent=self)
            return
        ruta_relativa = str(self.documentos_tree.item(seleccion[0], "values")[1])
        archivo = solicitudes.ruta_documento(ruta_relativa)
        if not archivo.is_file():
            messagebox.showerror("Error", f"No se encontró el archivo: {archivo}", parent=self)
            return
        try:
            os.startfile(str(archivo))  # visor del sistema en Windows
        except AttributeError:
            webbrowser.open(Path(archivo).as_uri())
        except OSError as exc:
            messagebox.showerror("Error", f"No se pudo abrir el documento: {exc}", parent=self)

    def calcular_grado(self) -> None:
        self._sincronizar_decision()
        if self.sin_constancia_var.get():
            messagebox.showinfo(
                "Sin constancia", "Marque 'Sin constancia (ingresante)': no se calcula grado.",
                parent=self,
            )
            return
        indice = self._indice_alumno()
        if indice is None:
            return
        alumno = self.datos["alumnos"][indice]
        nivel = self.decision_vars["nivel_ultimo"].get()
        grado = self.decision_vars["grado_ultimo"].get()
        situacion = self.decision_vars["situacion"].get()
        if not nivel or not grado:
            messagebox.showwarning(
                "Atención", "Ingrese el nivel y el grado vistos en la plataforma.", parent=self
            )
            return
        try:
            calculado = matricula.grado_siguiente(nivel, grado, situacion)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        nivel_calculado = matricula.nivel_de_grado_siguiente(nivel, grado, calculado)
        destino = alumno.get("destino", {})
        coincide = calculado == destino.get("grado") and nivel_calculado == destino.get("nivel")
        self.grado_calculado_var.set(f"{nivel_calculado} {calculado}".strip())
        self.coincide_var.set(
            "Coincide con lo solicitado." if coincide
            else f"ADVERTENCIA: se solicitó {destino.get('nivel', '')} {destino.get('grado', '')}."
        )

    def ver_cupos(self) -> None:
        indice = self._indice_alumno()
        if indice is None:
            return
        destino = self.datos["alumnos"][indice].get("destino", {})
        try:
            cupos = matricula.verificar_cupos(
                int(self.datos.get("anio", 0)), destino.get("nivel", ""),
                destino.get("grado", ""),
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        texto = "\n".join(
            f"Sección {c['seccion']}: {c['Matriculados']} matriculados, "
            f"{c['Vacantes']} vacantes"
            for c in cupos
        )
        messagebox.showinfo("Cupos por sección", texto or "No hay secciones para ese nivel.", parent=self)

    def observar(self) -> None:
        texto = simpledialog.askstring(
            "Observar solicitud", "Observación para el padre:", parent=self
        )
        if not texto or not texto.strip():
            return
        try:
            solicitudes.observar(self.id_solicitud, texto.strip())
            messagebox.showinfo("Listo", "La solicitud quedó observada.", parent=self)
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def rechazar(self) -> None:
        motivo = simpledialog.askstring("Rechazar solicitud", "Motivo:", parent=self)
        if not motivo or not motivo.strip():
            return
        if not messagebox.askyesno("Confirmar", "¿Rechazar la solicitud?", parent=self):
            return
        try:
            solicitudes.rechazar(self.id_solicitud, motivo.strip())
            messagebox.showinfo("Listo", "La solicitud fue rechazada.", parent=self)
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def aprobar(self) -> None:
        self._sincronizar_decision()
        if not messagebox.askyesno(
            "Confirmar", "¿Aprobar y matricular a todos los hermanos de esta solicitud?",
            parent=self,
        ):
            return
        try:
            resultado = matricula.aprobar_y_matricular(
                self.id_solicitud, decisiones=self.decisiones
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("No se pudo matricular", str(exc), parent=self)
            return
        advertencias = resultado.get("advertencias_grado", [])
        if advertencias:
            messagebox.showwarning(
                "Matriculado con advertencias",
                "La matrícula se registró, pero hubo diferencias de grado:\n\n"
                + "\n".join("- " + a for a in advertencias),
                parent=self,
            )
        else:
            messagebox.showinfo("Listo", "La solicitud fue aprobada y matriculada.", parent=self)
        self._cerrar()

    def _cerrar(self) -> None:
        if self.al_cerrar:
            self.al_cerrar()
        self.destroy()
