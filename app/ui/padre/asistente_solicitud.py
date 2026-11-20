"""Asistente del padre para crear la solicitud de matrícula (§6.2 y §14.8).

Cinco pasos con botones Anterior/Siguiente y validación por paso. Los pasos 1 a
3 (destino, datos de los alumnos y de los padres) están implementados en esta
fase; el paso 4 queda reservado para documentos/OCR y el 5 muestra el resumen y
permite guardar o enviar la solicitud.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app import errores
from app.servicios import solicitudes

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
}


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
                if id_solicitud else solicitudes.crear_borrador()
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            self.destroy()
            return

        self.anio_var = tk.StringVar()
        self.nivel_var = tk.StringVar()
        self.grado_var = tk.StringVar()
        self.contacto_vars: dict[str, tk.StringVar] = {}
        self.alumno_vars: list[dict[str, tk.StringVar]] = []
        self.padre_vars: list[dict[str, tk.StringVar]] = []
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
        ttk.Button(botones, text="Agregar hermano", command=self.agregar_alumno).pack(side="left", padx=3)
        ttk.Button(botones, text="Quitar seleccionado", command=self.quitar_alumno).pack(side="left", padx=3)

        destino = ttk.LabelFrame(pagina, text="Destino del alumno seleccionado")
        destino.pack(fill="x", padx=8, pady=8)
        ttk.Label(destino, text="Nivel:").pack(side="left", padx=4)
        self.nivel_combo = ttk.Combobox(
            destino, textvariable=self.nivel_var, values=tuple(solicitudes.NIVELES), state="readonly"
        )
        self.nivel_combo.pack(side="left", padx=4)
        self.nivel_combo.bind("<<ComboboxSelected>>", self._nivel_cambiado)
        ttk.Label(destino, text="Grado:").pack(side="left", padx=4)
        self.grado_combo = ttk.Combobox(destino, textvariable=self.grado_var, state="readonly")
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
        self.nivel_cambiado()
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
        dni = simpledialog.askstring("Nuevo alumno", "DNI del alumno (8 dígitos):", parent=self)
        if not dni:
            return
        try:
            alumno = solicitudes.agregar_alumno(self.datos)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        alumno["ficha"]["DNI"] = dni.strip()
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

    # ------------------------------------------------------------- pasos 4/5
    def _construir_paso4(self) -> None:
        ttk.Label(
            self.pasos[3],
            text="Los documentos (DNI, constancia) y el autocompletado con OCR\n"
                 "se incorporan en la siguiente fase del aplicativo.\n\n"
                 "Puede guardar un borrador o continuar con el resumen y el envío.",
            justify="center",
        ).pack(expand=True)

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

    def _guardar_datos(self) -> bool:
        if self.datos.get("estado") not in ("Borrador", "Observada"):
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
        if paso <= 3 and not self._validar((paso,)):
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
            messagebox.showinfo("Solicitud guardada", "El borrador quedó guardado.", parent=self)

    def enviar(self) -> None:
        """Valida la solicitud completa y la envía a la bandeja de la secretaria."""
        self._sincronizar()
        if not self._validar((1, 2, 3)):
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
        if self.datos.get("estado") in ("Borrador", "Observada"):
            self._sincronizar()
            self._guardar_datos()
        if self.al_cerrar:
            self.al_cerrar()
        self.destroy()
