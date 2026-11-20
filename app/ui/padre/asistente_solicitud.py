"""Asistente del padre para crear la solicitud de matrícula (§6.2 y §14.8).

Cinco pasos con botones Anterior/Siguiente y validación por paso. El paso 4
permite adjuntar documentos, registrar la constancia y sus logros, y usar OCR
como ayuda opcional; el 5 muestra el resumen y permite guardar o enviar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from app import errores
from app.servicios import solicitudes
from app.ui.componentes import entry_dni, normalizar_dni
from ocr import extraer_constancia, extraer_dni, extraer_lineas, tesseract_disponible

CAMPOS_ALUMNO = (
    ("DNI", "DNI", "texto"),
    ("Sexo", "Sexo (M/F)", "sexo"),
    ("Nombres", "Nombres", "texto"),
    ("ApellidoPaterno", "Apellido paterno", "texto"),
    ("ApellidoMaterno", "Apellido materno", "texto"),
    ("FechaNacimiento", "Fecha de nacimiento (AAAA-MM-DD)", "texto"),
    ("DistritoNacimiento", "Distrito de nacimiento", "texto"),
    ("ProvinciaNacimiento", "Provincia de nacimiento", "texto"),
    ("DepartamentoNacimiento", "Departamento de nacimiento", "texto"),
    ("PaisNacimiento", "País de nacimiento", "texto"),
    ("DomicilioActual", "Domicilio actual", "texto"),
    ("DistritoDomicilio", "Distrito del domicilio", "texto"),
    ("Celular", "Celular (9 dígitos)", "texto"),
    ("CorreoElectronico", "Correo electrónico", "texto"),
    ("Religion", "Religión", "texto"),
    ("LugarQueOcupa", "Lugar que ocupa entre los hermanos", "numero"),
    ("TipoAtencion", "Tipo de atención", "atencion"),
    ("EnfermedadCronica", "Enfermedad crónica", "texto"),
    ("ViveConPadre", "Vive con el padre", "booleano"),
    ("ViveConMadre", "Vive con la madre", "booleano"),
    ("ElPadreVive", "El padre vive", "booleano"),
    ("LaMadreVive", "La madre vive", "booleano"),
)
CAMPOS_PADRE = (
    ("DNI", "DNI", "texto"),
    ("Sexo", "Sexo (M/F)", "sexo"),
    ("Nombres", "Nombres", "texto"),
    ("ApellidoPaterno", "Apellido paterno", "texto"),
    ("ApellidoMaterno", "Apellido materno", "texto"),
    ("FechaNacimiento", "Fecha de nacimiento (AAAA-MM-DD)", "texto"),
    ("OcupacionActual", "Ocupación actual", "texto"),
    ("GradoInstruccion", "Grado de instrucción", "instruccion"),
    ("DomicilioActual", "Domicilio actual", "texto"),
    ("DistritoDomicilio", "Distrito del domicilio", "texto"),
    ("TelefonoFijo", "Teléfono fijo (9 dígitos)", "texto"),
    ("Celular", "Celular (9 dígitos)", "texto"),
    ("CorreoElectronico", "Correo electrónico", "texto"),
)
OPCIONES = {
    "sexo": solicitudes.SEXOS,
    "booleano": ("Sí", "No"),
    "atencion": ("",) + solicitudes.TIPOS_ATENCION,
    "instruccion": ("",) + solicitudes.GRADOS_INSTRUCCION,
    "nivel_doc": ("",) + tuple(solicitudes.NIVELES),
    "situacion": ("",) + solicitudes.SITUACIONES_FINALES,
    "tipo_ie": ("", "Estatal", "Particular"),
}
GRADOS_DOC = tuple(grado for grados in solicitudes.NIVELES.values() for grado in grados)
ARCHIVOS = (
    ("Imágenes y PDF", "*.jpg *.jpeg *.png *.pdf"),
    ("Imágenes", "*.jpg *.jpeg *.png"),
    ("PDF", "*.pdf"),
)


class AsistenteSolicitud(tk.Toplevel):
    """Ventana de cinco pasos para capturar y guardar una solicitud."""

    def __init__(self, parent, id_solicitud: str | None = None, al_cerrar=None):
        super().__init__(parent)
        self.title("Nueva solicitud de matrícula")
        self.geometry("980x680")
        self.transient(parent)
        self.grab_set()
        self.al_cerrar = al_cerrar
        try:
            self.datos = (
                solicitudes.obtener(id_solicitud)
                if id_solicitud else solicitudes.crear_borrador(etapa="matricula")
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            self.destroy()
            return
        if solicitudes.etapa_de(self.datos) == "vacante":
            messagebox.showwarning(
                "Atención",
                "Primero debe solicitar una vacante y esperar a que la secretaria la acepte.",
                parent=self,
            )
            self.destroy()
            return

        self.anio_var = tk.StringVar()
        self.nivel_var = tk.StringVar()
        self.grado_var = tk.StringVar()
        self.contacto_vars: dict[str, tk.StringVar] = {}
        self.alumno_vars: list[dict[str, tk.StringVar]] = []
        self.padre_vars: list[dict[str, tk.StringVar]] = []
        self.constancia_vars: dict[str, tk.StringVar] = {}
        self.sin_constancia_var = tk.BooleanVar(value=False)
        self.docs_labels: dict[str, tk.StringVar] = {}
        self.dni_padre_labels: list[tk.StringVar] = []
        self.logros_tree: ttk.Treeview | None = None
        self.ocr_button: ttk.Button | None = None
        # Tras aceptar la vacante, el nivel y grado vienen de la etapa anterior.
        self.destino_bloqueado = (
            solicitudes.etapa_de(self.datos) == "matricula"
            and self.datos.get("estado") == "Vacante aceptada"
        )
        self._construir()
        self._cargar_datos()

    # ------------------------------------------------------------ estructura
    def _construir(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)
        titulos = (
            "1. Año y alumnos", "2. Datos del alumno", "3. Padres y apoderado",
            "4. Documentos", "5. Resumen y envío",
        )
        self.pasos = []
        for titulo in titulos:
            pagina = ttk.Frame(self.notebook)
            self.notebook.add(pagina, text=titulo)
            self.pasos.append(pagina)

        self._construir_paso1()
        self._construir_paso2()
        self._construir_paso3()
        self._construir_paso4()
        self._construir_paso5()

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ttk.Button(barra, text="Anterior", command=self.anterior).pack(side="left", padx=3)
        ttk.Button(barra, text="Siguiente", command=self.siguiente).pack(side="left", padx=3)
        ttk.Button(barra, text="Guardar borrador", command=self.guardar).pack(side="right", padx=3)
        ttk.Button(barra, text="Enviar solicitud", command=self.enviar).pack(side="right", padx=3)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    @staticmethod
    def _campo(parent, etiqueta: str, valor, tipo: str = "texto") -> tk.StringVar:
        """Crea un par etiqueta/control y devuelve su variable asociada."""
        fila = ttk.Frame(parent)
        fila.pack(fill="x", pady=2)
        ttk.Label(fila, text=etiqueta, width=36, anchor="w").pack(side="left")
        if tipo == "booleano":
            valor = "Sí" if solicitudes._es_verdadero(valor) else "No"
        variable = tk.StringVar(value="" if valor is None else str(valor))
        if tipo in OPCIONES or tipo == "grado":
            control = ttk.Combobox(fila, textvariable=variable, values=OPCIONES.get(tipo, ()), state="readonly")
        elif etiqueta == "DNI":
            control = entry_dni(fila, textvariable=variable)
        else:
            control = ttk.Entry(fila, textvariable=variable)
        control.pack(side="left", fill="x", expand=True)
        return variable

    # ---------------------------------------------------------------- paso 1
    def _construir_paso1(self) -> None:
        pagina = self.pasos[0]
        superior = ttk.Frame(pagina)
        superior.pack(fill="x", padx=8, pady=8)
        ttk.Label(superior, text="Año escolar:").pack(side="left")
        ttk.Entry(superior, textvariable=self.anio_var, width=10).pack(side="left", padx=6)

        marco = ttk.LabelFrame(pagina, text="Alumnos (hermanos, máximo 6)")
        marco.pack(fill="both", expand=True, padx=8, pady=4)
        self.alumnos_tree = ttk.Treeview(
            marco, columns=("DNI", "Nombres", "Nivel", "Grado"), show="headings", height=8
        )
        for col, ancho in (("DNI", 120), ("Nombres", 220), ("Nivel", 130), ("Grado", 90)):
            self.alumnos_tree.heading(col, text=col)
            self.alumnos_tree.column(col, width=ancho)
        self.alumnos_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.alumnos_tree.bind("<<TreeviewSelect>>", self._alumno_seleccionado)

        botones = ttk.Frame(marco)
        botones.pack(fill="x", padx=6, pady=6)
        self.boton_agregar = ttk.Button(botones, text="Agregar hermano", command=self.agregar_alumno)
        self.boton_agregar.pack(side="left", padx=3)
        self.boton_quitar = ttk.Button(botones, text="Quitar seleccionado", command=self.quitar_alumno)
        self.boton_quitar.pack(side="left", padx=3)
        if self.destino_bloqueado:
            self.boton_agregar["state"] = "disabled"
            self.boton_quitar["state"] = "disabled"
            ttk.Label(
                pagina,
                text="Nivel y grado definidos al solicitar la vacante; no se pueden cambiar.",
                foreground="#1256a0",
            ).pack(fill="x", padx=8)

        destino = ttk.LabelFrame(pagina, text="Destino del alumno seleccionado")
        destino.pack(fill="x", padx=8, pady=8)
        ttk.Label(destino, text="Nivel:").pack(side="left", padx=4)
        self.nivel_combo = ttk.Combobox(
            destino, textvariable=self.nivel_var, values=tuple(solicitudes.NIVELES), state="readonly"
        )
        self.nivel_combo.pack(side="left", padx=4)
        self.nivel_combo.bind("<<ComboboxSelected>>", self._nivel_cambiado)
        ttk.Label(destino, text="Grado:").pack(side="left", padx=4)
        estado_destino = "disabled" if self.destino_bloqueado else "readonly"
        self.nivel_combo["state"] = estado_destino
        self.grado_combo = ttk.Combobox(destino, textvariable=self.grado_var, state=estado_destino)
        self.grado_combo.pack(side="left", padx=4)
        self.grado_combo.bind("<<ComboboxSelected>>", self._grado_cambiado)

    def _indice_alumno(self) -> int | None:
        item = self.alumnos_tree.focus()
        if not item:
            return None
        valores = self.alumnos_tree.item(item, "values")
        return int(valores[0]) if valores else None

    def _refrescar_alumnos(self) -> None:
        for item in self.alumnos_tree.get_children():
            self.alumnos_tree.delete(item)
        for indice, alumno in enumerate(self.datos.get("alumnos", [])):
            ficha, destino = alumno["ficha"], alumno["destino"]
            self.alumnos_tree.insert(
                "", "end", iid=str(indice),
                values=(indice, ficha.get("DNI", ""), ficha.get("Nombres", ""),
                        destino.get("nivel", ""), destino.get("grado", "")),
            )

    def _alumno_seleccionado(self, _evento=None) -> None:
        indice = self._indice_alumno()
        if indice is None:
            return
        destino = self.datos["alumnos"][indice]["destino"]
        self.nivel_var.set(destino.get("nivel", ""))
        self._nivel_cambiado()
        self.grado_var.set(destino.get("grado", ""))

    def _nivel_cambiado(self, _evento=None) -> None:
        nivel = self.nivel_var.get()
        self.grado_combo["values"] = solicitudes.NIVELES.get(nivel, ())
        if self.grado_var.get() not in solicitudes.NIVELES.get(nivel, ()):
            self.grado_var.set("")
        indice = self._indice_alumno()
        if indice is not None:
            self.datos["alumnos"][indice]["destino"]["nivel"] = nivel

    def _grado_cambiado(self, _evento=None) -> None:
        indice = self._indice_alumno()
        if indice is not None:
            self.datos["alumnos"][indice]["destino"]["grado"] = self.grado_var.get()

    def agregar_alumno(self) -> None:
        """Agrega un hermano pidiendo el DNI y los datos mínimos de destino."""
        dni = normalizar_dni(
            simpledialog.askstring("Nuevo alumno", "DNI del alumno (8 dígitos):", parent=self)
        )
        if not dni:
            return
        if len(dni) != 8:
            messagebox.showwarning("DNI inválido", "El DNI debe tener 8 dígitos.", parent=self)
            return
        try:
            alumno = solicitudes.agregar_alumno(self.datos)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        alumno["ficha"]["DNI"] = dni
        self._refrescar_alumnos()
        self._refrescar_fichas_alumnos()

    def quitar_alumno(self) -> None:
        """Quita el alumno seleccionado y reordena el lugar entre hermanos."""
        indice = self._indice_alumno()
        if indice is None:
            messagebox.showwarning("Atención", "Seleccione un alumno.", parent=self)
            return
        try:
            solicitudes.quitar_alumno(self.datos, indice)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._refrescar_alumnos()
        self._refrescar_fichas_alumnos()

    # ---------------------------------------------------------------- paso 2
    def _construir_paso2(self) -> None:
        pagina = self.pasos[1]
        contacto = ttk.LabelFrame(pagina, text="Contacto de emergencia (compartido por los hermanos)")
        contacto.pack(fill="x", padx=8, pady=6)
        self.contacto_vars["nombre"] = self._campo(contacto, "Nombre del contacto", "")
        self.contacto_vars["celular"] = self._campo(contacto, "Celular (9 dígitos)", "")
        self.alumnos_notebook = ttk.Notebook(pagina)
        self.alumnos_notebook.pack(fill="both", expand=True, padx=8, pady=6)

    def _refrescar_fichas_alumnos(self) -> None:
        for item in self.alumnos_notebook.tabs():
            self.alumnos_notebook.forget(item)
        self.alumno_vars.clear()
        for indice, alumno in enumerate(self.datos.get("alumnos", [])):
            pagina = ttk.Frame(self.alumnos_notebook)
            self.alumnos_notebook.add(pagina, text=f"Alumno {indice + 1}")
            lienzo = ttk.Frame(pagina)
            lienzo.pack(fill="both", expand=True)
            variables: dict[str, tk.StringVar] = {}
            for clave, etiqueta, tipo in CAMPOS_ALUMNO:
                variables[clave] = self._campo(
                    lienzo, etiqueta, alumno["ficha"].get(clave, ""), tipo
                )
            variables["nee"] = self._campo(
                lienzo, "NEE (separadas por coma)", ", ".join(alumno.get("nee", []))
            )
            variables["hermanos_ie"] = self._campo(
                lienzo, "Hermanos en la I.E. (Inicial/Primaria/Secundaria, separados por coma)",
                ", ".join(alumno.get("hermanos_ie", [])),
            )
            self.alumno_vars.append(variables)

    # ---------------------------------------------------------------- paso 3
    def _construir_paso3(self) -> None:
        pagina = self.pasos[2]
        botones = ttk.Frame(pagina)
        botones.pack(fill="x", padx=8, pady=6)
        ttk.Button(botones, text="Agregar padre/madre", command=lambda: self.agregar_padre("Padre")).pack(side="left", padx=3)
        ttk.Button(botones, text="Agregar madre", command=lambda: self.agregar_padre("Madre")).pack(side="left", padx=3)
        ttk.Button(botones, text="Agregar apoderado", command=lambda: self.agregar_padre("Apoderado")).pack(side="left", padx=3)
        ttk.Button(botones, text="Quitar seleccionado", command=self.quitar_padre).pack(side="left", padx=3)

        self.padres_notebook = ttk.Notebook(pagina)
        self.padres_notebook.pack(fill="both", expand=True, padx=8, pady=4)
        responsable = ttk.LabelFrame(pagina, text="Responsable de la matrícula")
        responsable.pack(fill="x", padx=8, pady=6)
        ttk.Label(responsable, text="Responsable:").pack(side="left", padx=4)
        self.responsable_combo = ttk.Combobox(responsable, textvariable=tk.StringVar(), state="readonly")
        self.responsable_combo.pack(side="left", padx=4)
        ttk.Label(responsable, text="Apoderado:").pack(side="left", padx=4)
        self.apoderado_combo = ttk.Combobox(responsable, textvariable=tk.StringVar(), state="readonly")
        self.apoderado_combo.pack(side="left", padx=4)

    def _refrescar_padres(self) -> None:
        for item in self.padres_notebook.tabs():
            self.padres_notebook.forget(item)
        self.padre_vars.clear()
        for indice, padre in enumerate(self.datos.get("padres", [])):
            pagina = ttk.Frame(self.padres_notebook)
            self.padres_notebook.add(pagina, text=f"{padre.get('vinculo', 'Padre')} {indice + 1}")
            variables: dict[str, tk.StringVar] = {}
            for clave, etiqueta, tipo in CAMPOS_PADRE:
                variables[clave] = self._campo(
                    pagina, etiqueta, padre.get(clave, ""), tipo
                )
            self.padre_vars.append(variables)

        dnis = [str(p.get("DNI") or "") for p in self.datos.get("padres", []) if p.get("DNI")]
        opciones = ("",) + tuple(dnis)
        self.responsable_combo["values"] = opciones
        self.apoderado_combo["values"] = opciones
        self.responsable_combo.set(str(self.datos.get("dni_responsable") or ""))
        self.apoderado_combo.set(str(self.datos.get("dni_apoderado") or ""))

    def agregar_padre(self, vinculo: str) -> None:
        """Agrega una ficha de padre, madre o apoderado a la solicitud."""
        if vinculo == "Apoderado":
            if any(p.get("vinculo") == "Apoderado" for p in self.datos.get("padres", [])):
                messagebox.showwarning("Atención", "Ya hay un apoderado registrado.", parent=self)
                return
        elif sum(p.get("vinculo") in ("Padre", "Madre") for p in self.datos.get("padres", [])) >= 2:
            messagebox.showwarning("Atención", "Ya se registraron el padre y la madre.", parent=self)
            return
        self.datos.setdefault("padres", []).append(solicitudes.nuevo_padre(vinculo))
        self._refrescar_padres()

    def quitar_padre(self) -> None:
        """Quita la ficha de padre/apoderado seleccionada."""
        seleccion = self.padres_notebook.select()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione una ficha.", parent=self)
            return
        indice = self.padres_notebook.index(seleccion)
        self.datos["padres"].pop(indice)
        self._refrescar_padres()

    # ---------------------------------------------------------------- paso 4
    def _construir_paso4(self) -> None:
        pagina = self.pasos[3]
        seleccion = ttk.LabelFrame(pagina, text="Documentos del alumno")
        seleccion.pack(fill="x", padx=8, pady=6)
        ttk.Label(seleccion, text="Alumno:").pack(side="left", padx=4)
        self.doc_alumno_combo = ttk.Combobox(seleccion, state="readonly", width=34)
        self.doc_alumno_combo.pack(side="left", padx=4)
        self.doc_alumno_combo.bind("<<ComboboxSelected>>", self._documento_alumno_cambiado)
        ttk.Button(seleccion, text="Adjuntar DNI", command=self.adjuntar_dni_alumno).pack(side="left", padx=3)
        ttk.Button(seleccion, text="Adjuntar constancia", command=self.adjuntar_constancia).pack(side="left", padx=3)
        self.ocr_button = ttk.Button(
            seleccion, text="Autocompletar con OCR", command=self.autocompletar_ocr
        )
        self.ocr_button.pack(side="left", padx=3)
        if not tesseract_disponible():
            self.ocr_button["state"] = "disabled"
            ttk.Label(
                seleccion,
                text="OCR no disponible: llene los campos manualmente.",
                foreground="#8a5a00",
            ).pack(side="left", padx=6)

        estados = ttk.Frame(pagina)
        estados.pack(fill="x", padx=8)
        self.docs_labels["dni"] = tk.StringVar(value="DNI del alumno: sin adjuntar")
        self.docs_labels["constancia"] = tk.StringVar(value="Constancia: sin adjuntar")
        ttk.Label(estados, textvariable=self.docs_labels["dni"]).pack(side="left", padx=12)
        ttk.Label(estados, textvariable=self.docs_labels["constancia"]).pack(side="left", padx=12)

        constancia = ttk.LabelFrame(pagina, text="Constancia de logros")
        constancia.pack(fill="x", padx=8, pady=6)
        self.constancia_controles: dict[str, ttk.Entry | ttk.Combobox] = {}
        campos = (
            ("codigo_virtual", "Código virtual (8 caracteres)"),
            ("nivel_educativo", "Nivel educativo"),
            ("fecha_hora_emision", "Fecha de emisión (AAAA-MM-DD HH:MM:SS)"),
            ("codigo_modular_ie", "Código modular de la I.E."),
            ("nombre_ie", "Nombre de la I.E."),
        )
        for clave, etiqueta in campos:
            fila = ttk.Frame(constancia)
            fila.pack(fill="x", pady=2)
            ttk.Label(fila, text=etiqueta, width=38, anchor="w").pack(side="left")
            variable = tk.StringVar()
            if clave == "nivel_educativo":
                control = ttk.Combobox(
                    fila, textvariable=variable, values=tuple(solicitudes.NIVELES),
                    state="readonly",
                )
            else:
                control = ttk.Entry(fila, textvariable=variable)
            control.pack(side="left", fill="x", expand=True)
            self.constancia_vars[clave] = variable
            self.constancia_controles[clave] = control
        ttk.Label(constancia, text="Tipo de I.E.:").pack(side="left", padx=4)
        self.constancia_vars["tipo_ie"] = tk.StringVar()
        ttk.Combobox(
            constancia, textvariable=self.constancia_vars["tipo_ie"],
            values=("Estatal", "Particular"), state="readonly", width=14,
        ).pack(side="left", padx=4)
        ttk.Checkbutton(
            constancia, text="Sin constancia (ingresante)",
            variable=self.sin_constancia_var, command=self._sin_constancia_cambiado,
        ).pack(side="left", padx=12)

        logros = ttk.LabelFrame(pagina, text="Logros de aprendizaje")
        logros.pack(fill="both", expand=True, padx=8, pady=6)
        self.logros_tree = ttk.Treeview(
            logros, columns=("Anio", "Grado", "IE", "Situacion"), show="headings", height=6
        )
        for columna, texto, ancho in (
            ("Anio", "Año", 80), ("Grado", "Grado", 100),
            ("IE", "I.E. (código modular)", 220), ("Situacion", "Situación", 230),
        ):
            self.logros_tree.heading(columna, text=texto)
            self.logros_tree.column(columna, width=ancho)
        self.logros_tree.pack(fill="both", expand=True, padx=6, pady=6)
        botones = ttk.Frame(logros)
        botones.pack(fill="x", padx=6, pady=6)
        self.logro_vars: dict[str, tk.StringVar] = {
            "anio": tk.StringVar(), "grado": tk.StringVar(),
            "ie": tk.StringVar(), "situacion": tk.StringVar(),
        }
        for clave, ancho in (("anio", 8), ("grado", 10), ("ie", 18), ("situacion", 24)):
            ttk.Entry(botones, textvariable=self.logro_vars[clave], width=ancho).pack(
                side="left", padx=2
            )
        ttk.Button(botones, text="Agregar logro", command=self.agregar_logro).pack(side="left", padx=3)
        ttk.Button(botones, text="Quitar seleccionado", command=self.quitar_logro).pack(side="left", padx=3)

        padres = ttk.LabelFrame(pagina, text="DNI de padres y apoderados")
        padres.pack(fill="x", padx=8, pady=6)
        self.padres_docs_frame = ttk.Frame(padres)
        self.padres_docs_frame.pack(fill="x", padx=6, pady=6)

    def _indice_documento_alumno(self) -> int | None:
        if self.doc_alumno_combo is None:
            return None
        texto = self.doc_alumno_combo.get()
        if not texto.isdigit():
            return None
        return int(texto) - 1

    def _refrescar_documentos(self) -> None:
        alumnos = self.datos.get("alumnos", [])
        opciones = tuple(str(i + 1) for i in range(len(alumnos)))
        self.doc_alumno_combo["values"] = opciones
        if opciones:
            actual = self.doc_alumno_combo.get()
            self.doc_alumno_combo.set(actual if actual in opciones else opciones[0])
        else:
            self.doc_alumno_combo.set("")
        for item in self.padres_docs_frame.winfo_children():
            item.destroy()
        self.dni_padre_labels.clear()
        for indice, padre in enumerate(self.datos.get("padres", [])):
            fila = ttk.Frame(self.padres_docs_frame)
            fila.pack(fill="x", pady=2)
            ttk.Label(fila, text=f"{padre.get('vinculo', 'Padre')} {indice + 1}:", width=20).pack(side="left")
            variable = tk.StringVar(value="sin adjuntar")
            if padre.get("docs", {}).get("dni"):
                variable.set(padre["docs"]["dni"].split("/")[-1])
            ttk.Label(fila, textvariable=variable, width=38).pack(side="left")
            ttk.Button(
                fila, text="Adjuntar DNI",
                command=lambda i=indice: self.adjuntar_dni_padre(i),
            ).pack(side="left", padx=3)
            self.dni_padre_labels.append(variable)
        self._cargar_documentos_alumno()

    def _documento_alumno_cambiado(self, _evento=None) -> None:
        self._sincronizar_documentos()
        self._cargar_documentos_alumno()

    def _sin_constancia_cambiado(self) -> None:
        """Desactiva los campos de constancia cuando es un alumno ingresante."""
        self._sincronizar_documentos()
        sin = self.sin_constancia_var.get()
        estado = "disabled" if sin else "normal"
        for control in self.constancia_controles.values():
            if isinstance(control, ttk.Combobox):
                control.configure(state="disabled" if sin else "readonly")
            else:
                control.configure(state=estado)

    def _cargar_documentos_alumno(self) -> None:
        indice = self._indice_documento_alumno()
        if indice is None or indice >= len(self.datos.get("alumnos", [])):
            for variable in self.constancia_vars.values():
                variable.set("")
            self.sin_constancia_var.set(False)
            self.logros_tree.delete(*self.logros_tree.get_children())
            return
        alumno = self.datos["alumnos"][indice]
        constancia = alumno.get("constancia", {})
        for clave, variable in self.constancia_vars.items():
            variable.set(constancia.get(clave, "") or "")
        self.sin_constancia_var.set(bool(constancia.get("sin_constancia")))
        self._sin_constancia_cambiado()
        for tipo in ("dni", "constancia"):
            ruta = alumno.get("docs", {}).get(tipo, "")
            self.docs_labels[tipo].set(
                f"{'DNI del alumno' if tipo == 'dni' else 'Constancia'}: "
                f"{ruta.split('/')[-1] if ruta else 'sin adjuntar'}"
            )
        self._refrescar_logros()

    def _refrescar_logros(self) -> None:
        self.logros_tree.delete(*self.logros_tree.get_children())
        indice = self._indice_documento_alumno()
        if indice is None or indice >= len(self.datos.get("alumnos", [])):
            return
        for fila in self.datos["alumnos"][indice].get("constancia", {}).get("logros", []):
            self.logros_tree.insert("", "end", values=(
                fila.get("anio", ""), fila.get("grado", ""),
                fila.get("codigo_modular_ie", ""), fila.get("situacion", ""),
            ))

    def _sincronizar_documentos(self) -> None:
        indice = self._indice_documento_alumno()
        if indice is None or indice >= len(self.datos.get("alumnos", [])):
            return
        constancia = self.datos["alumnos"][indice].setdefault("constancia", {})
        for clave, variable in self.constancia_vars.items():
            constancia[clave] = variable.get()
        constancia["sin_constancia"] = self.sin_constancia_var.get()

    def adjuntar_dni_alumno(self) -> None:
        self._sincronizar_documentos()
        indice = self._indice_documento_alumno()
        if indice is None:
            messagebox.showwarning("Atención", "Agregue un alumno primero.", parent=self)
            return
        origen = filedialog.askopenfilename(title="DNI del alumno", filetypes=ARCHIVOS, parent=self)
        if not origen:
            return
        try:
            ruta = solicitudes.copiar_documento(origen, self.datos["id"])
        except errores.ErrorApp as exc:
            messagebox.showerror("Documento no válido", str(exc), parent=self)
            return
        self.datos["alumnos"][indice].setdefault("docs", {})["dni"] = ruta
        self.docs_labels["dni"].set(f"DNI del alumno: {ruta.split('/')[-1]}")

    def adjuntar_constancia(self) -> None:
        self._sincronizar_documentos()
        indice = self._indice_documento_alumno()
        if indice is None:
            messagebox.showwarning("Atención", "Agregue un alumno primero.", parent=self)
            return
        origen = filedialog.askopenfilename(title="Constancia de logros", filetypes=ARCHIVOS, parent=self)
        if not origen:
            return
        try:
            ruta = solicitudes.copiar_documento(origen, self.datos["id"])
        except errores.ErrorApp as exc:
            messagebox.showerror("Documento no válido", str(exc), parent=self)
            return
        self.datos["alumnos"][indice].setdefault("docs", {})["constancia"] = ruta
        self.docs_labels["constancia"].set(f"Constancia: {ruta.split('/')[-1]}")

    def adjuntar_dni_padre(self, indice: int) -> None:
        origen = filedialog.askopenfilename(title="DNI del padre/apoderado", filetypes=ARCHIVOS, parent=self)
        if not origen:
            return
        try:
            ruta = solicitudes.copiar_documento(origen, self.datos["id"])
        except errores.ErrorApp as exc:
            messagebox.showerror("Documento no válido", str(exc), parent=self)
            return
        self.datos["padres"][indice].setdefault("docs", {})["dni"] = ruta
        self.dni_padre_labels[indice].set(ruta.split("/")[-1])

    def agregar_logro(self) -> None:
        self._sincronizar_documentos()
        anio = self.logro_vars["anio"].get().strip()
        grado = self.logro_vars["grado"].get().strip()
        situacion = self.logro_vars["situacion"].get().strip()
        if not (anio.isdigit() and len(anio) == 4 and grado and situacion):
            messagebox.showwarning(
                "Logro incompleto", "Ingrese año (4 dígitos), grado y situación.", parent=self
            )
            return
        indice = self._indice_documento_alumno()
        if indice is None:
            return
        constancia = self.datos["alumnos"][indice].setdefault("constancia", {})
        constancia.setdefault("logros", []).append({
            "anio": anio, "grado": grado, "situacion": situacion,
            "codigo_modular_ie": self.logro_vars["ie"].get().strip(),
        })
        self._refrescar_logros()

    def quitar_logro(self) -> None:
        seleccion = self.logros_tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un logro.", parent=self)
            return
        indice_alumno = self._indice_documento_alumno()
        if indice_alumno is None:
            return
        logros = self.datos["alumnos"][indice_alumno]["constancia"].setdefault("logros", [])
        for item in seleccion:
            posicion = self.logros_tree.index(item)
            if 0 <= posicion < len(logros):
                logros.pop(posicion)
        self._refrescar_logros()

    def autocompletar_ocr(self) -> None:
        """Extrae datos con OCR y pide confirmación antes de aplicarlos (§6.2.3)."""
        self._sincronizar_documentos()
        indice = self._indice_documento_alumno()
        if indice is None:
            messagebox.showwarning("Atención", "Agregue un alumno primero.", parent=self)
            return
        origen = filedialog.askopenfilename(title="Imagen para OCR", filetypes=ARCHIVOS, parent=self)
        if not origen:
            return
        try:
            lineas = extraer_lineas(origen)
        except errores.ErrorApp as exc:
            messagebox.showwarning("OCR no disponible", str(exc), parent=self)
            return
        campos_dni = extraer_dni(lineas, tabla="ESTUDIANTE")
        campos_const, logros = extraer_constancia(lineas)
        if not campos_dni and not campos_const:
            messagebox.showinfo(
                "Sin resultados", "No se reconocieron campos. Complete el formulario a mano.",
                parent=self,
            )
            return
        detalle = "\n".join(
            f"- {clave.split('.')[-1]}: {valor} ({conf}%)"
            for clave, (valor, conf) in list(campos_dni.items()) + list(campos_const.items())
        )
        if logros:
            detalle += f"\n- Logros detectados: {len(logros)}"
        if not messagebox.askyesno(
            "Confirmar OCR",
            "Revise los datos reconocidos antes de aplicarlos:\n\n" + detalle
            + "\n\n¿Desea aplicarlos al formulario?",
            parent=self,
        ):
            return
        alumno = self.datos["alumnos"][indice]
        aplicados = solicitudes.aplicar_ocr_dni(campos_dni, alumno["ficha"])
        aplicados += solicitudes.aplicar_ocr_constancia(
            campos_const, logros, alumno.setdefault("constancia", {})
        )
        self._cargar_ficha_alumno(indice)
        self._cargar_documentos_alumno()
        messagebox.showinfo(
            "OCR aplicado", f"Se actualizaron {len(aplicados)} campos. Revíselos antes de enviar.",
            parent=self,
        )

    def _cargar_ficha_alumno(self, indice: int) -> None:
        if indice >= len(self.alumno_vars):
            return
        alumno = self.datos["alumnos"][indice]
        for clave, variable in self.alumno_vars[indice].items():
            if clave in ("nee", "hermanos_ie"):
                variable.set(", ".join(alumno.get(clave, [])))
            else:
                variable.set(str(alumno["ficha"].get(clave, "")))

    def _construir_paso5(self) -> None:
        pagina = self.pasos[4]
        self.resumen_tree = ttk.Treeview(
            pagina, columns=("Campo", "Valor"), show="headings", height=12
        )
        self.resumen_tree.heading("Campo", text="Campo")
        self.resumen_tree.heading("Valor", text="Valor")
        self.resumen_tree.column("Campo", width=180)
        self.resumen_tree.column("Valor", width=700)
        self.resumen_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _refrescar_resumen(self) -> None:
        for item in self.resumen_tree.get_children():
            self.resumen_tree.delete(item)
        for campo, valor in solicitudes.resumen(self.datos):
            self.resumen_tree.insert("", "end", values=(campo, valor))

    # ------------------------------------------------------- sincronización
    def _cargar_datos(self) -> None:
        self.anio_var.set(str(self.datos.get("anio", "")))
        self.contacto_vars["nombre"].set(self.datos.get("contacto_emergencia", {}).get("nombre", ""))
        self.contacto_vars["celular"].set(self.datos.get("contacto_emergencia", {}).get("celular", ""))
        self._refrescar_alumnos()
        self._refrescar_fichas_alumnos()
        self._refrescar_padres()
        self._refrescar_documentos()
        self._refrescar_resumen()

    def _sincronizar(self) -> None:
        try:
            self.datos["anio"] = int(self.anio_var.get())
        except ValueError:
            pass
        self.datos["contacto_emergencia"] = {
            "nombre": self.contacto_vars["nombre"].get(),
            "celular": self.contacto_vars["celular"].get(),
        }
        for indice, variables in enumerate(self.alumno_vars):
            if indice >= len(self.datos.get("alumnos", [])):
                break
            ficha = self.datos["alumnos"][indice]["ficha"]
            for clave, variable in variables.items():
                if clave in ("nee", "hermanos_ie"):
                    self.datos["alumnos"][indice][clave] = [
                        t.strip() for t in variable.get().split(",") if t.strip()
                    ]
                elif clave == "LugarQueOcupa":
                    texto = variable.get().strip()
                    ficha[clave] = int(texto) if texto.isdigit() else ""
                else:
                    ficha[clave] = variable.get()
        for indice, variables in enumerate(self.padre_vars):
            if indice >= len(self.datos.get("padres", [])):
                break
            for clave, variable in variables.items():
                self.datos["padres"][indice][clave] = variable.get()
        self.datos["dni_responsable"] = self.responsable_combo.get() or None
        self.datos["dni_apoderado"] = self.apoderado_combo.get() or None
        self._sincronizar_documentos()

    def _guardar_datos(self) -> bool:
        if self.datos.get("estado") not in ("Borrador", "Observada", "Vacante aceptada"):
            return True
        try:
            solicitudes.actualizar(self.datos["id"], self.datos)
            return True
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return False

    # ------------------------------------------------------------- acciones
    def _validar(self, pasos: tuple[int, ...]) -> bool:
        mensajes: list[str] = []
        for paso in pasos:
            mensajes.extend(solicitudes.validar_paso(paso, self.datos))
        if mensajes:
            messagebox.showerror(
                "Datos incompletos", "\n".join("- " + m for m in mensajes), parent=self
            )
            return False
        return True

    def siguiente(self) -> None:
        """Sincroniza, valida el paso actual y avanza al siguiente."""
        self._sincronizar()
        paso = self.notebook.index(self.notebook.select()) + 1
        if paso <= 4 and not self._validar((paso,)):
            return
        if paso == 5:
            self._refrescar_resumen()
        elif paso < 5:
            self.notebook.select(paso)

    def anterior(self) -> None:
        """Retrocede un paso sin validar."""
        indice = self.notebook.index(self.notebook.select())
        if indice > 0:
            self._sincronizar()
            self.notebook.select(indice - 1)

    def guardar(self) -> None:
        """Guarda el contenido actual como borrador."""
        self._sincronizar()
        if self._guardar_datos():
            mensaje = (
                "La matrícula quedó guardada; puede continuar después."
                if self.destino_bloqueado else "El borrador quedó guardado."
            )
            messagebox.showinfo("Solicitud guardada", mensaje, parent=self)

    def enviar(self) -> None:
        """Valida la solicitud completa y la envía a la bandeja de la secretaria."""
        self._sincronizar()
        if not self._validar((1, 2, 3, 4, 5)):
            return
        try:
            errores_envio = solicitudes.validar_para_enviar(self.datos)
            if errores_envio:
                messagebox.showerror(
                    "No se puede enviar",
                    "\n".join("- " + m for m in errores_envio), parent=self,
                )
                return
            self.datos = solicitudes.enviar(self.datos["id"])
            messagebox.showinfo("Solicitud enviada", "La solicitud fue enviada correctamente.", parent=self)
            self._cerrar()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def _cerrar(self) -> None:
        if self.datos.get("estado") in ("Borrador", "Observada", "Vacante aceptada"):
            self._sincronizar()
            self._guardar_datos()
        if self.al_cerrar:
            self.al_cerrar()
        self.destroy()
