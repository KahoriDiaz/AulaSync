"""Realizar matrícula: pantalla por pasos (§6.3.3).

1. Documentos: imágenes del DNI del estudiante, del padre, de la madre y de la
   constancia de logros. El OCR solo prellena; todo es editable.
2. Datos: estudiante (con contacto de emergencia), padre, madre, responsable
   y constancia con su tabla de logros.
3. Verificación manual del código virtual en la página del MINEDU.
4. Guardar datos (una transacción con procedimientos).
5. Matrícula: grado que corresponde, vacantes y registro.

La lógica de base de datos está en ``app.servicios.matricula``.
"""
from __future__ import annotations

import tkinter as tk
import webbrowser
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

from app.config import config
from app.errores import ErrorApp
from app.servicios import auth, estudiantes, matricula, padres
from app.ui.componentes import entry_dni
from app.ui.selector_fecha import SelectorFecha
from app.ui.tema import EXITO, PELIGRO, TEXTO_SUAVE, tarjeta

AVISO_MINEDU = (
    "El código virtual no se puede verificar automáticamente. Ingrese a "
    "https://constancia.minedu.gob.pe/, elija 'Verificar constancia' e ingrese el "
    "código virtual y el DNI del estudiante."
)
SI_NO = ("Sí", "No")
TIPOS_ATENCION = ("", "ESSALUD", "SIS", "Otros")
GRADOS_INSTRUCCION = ("Primaria", "Secundaria", "Superior", "Otros")
TODOS_LOS_GRADOS = sorted({g for grados in matricula.NIVELES.values() for g in grados})


class Campos:
    """Grupo de campos de texto/lista/fecha de un formulario, con lectura y escritura."""

    def __init__(self, parent: ttk.Frame, columnas: int = 2):
        self.parent = parent
        self.columnas = columnas
        self.variables: dict[str, tk.StringVar] = {}
        self.fechas: dict[str, SelectorFecha] = {}
        self.controles: dict[str, tk.Widget] = {}
        self._posicion = 0
        for columna in range(columnas):
            parent.columnconfigure(columna, weight=1)

    def _celda(self, etiqueta: str) -> ttk.Frame:
        fila, columna = divmod(self._posicion, self.columnas)
        self._posicion += 1
        celda = ttk.Frame(self.parent)
        celda.grid(row=fila, column=columna, sticky="ew", padx=8, pady=4)
        ttk.Label(celda, text=etiqueta).pack(anchor="w")
        return celda

    def texto(self, clave: str, etiqueta: str, dni: bool = False) -> None:
        celda = self._celda(etiqueta)
        variable = tk.StringVar()
        control = entry_dni(celda, textvariable=variable) if dni else ttk.Entry(celda, textvariable=variable)
        control.pack(fill="x")
        self.variables[clave] = variable
        self.controles[clave] = control

    def lista(self, clave: str, etiqueta: str, valores, inicial: str = "") -> None:
        celda = self._celda(etiqueta)
        variable = tk.StringVar(value=inicial)
        control = ttk.Combobox(celda, textvariable=variable, values=list(valores), state="readonly")
        control.pack(fill="x")
        self.variables[clave] = variable
        self.controles[clave] = control

    def fecha(self, clave: str, etiqueta: str, **opciones) -> None:
        celda = self._celda(etiqueta)
        selector = SelectorFecha(celda, **opciones)
        selector.pack(anchor="w")
        self.fechas[clave] = selector
        self.controles[clave] = selector

    def valores(self) -> dict[str, str]:
        datos = {clave: variable.get().strip() for clave, variable in self.variables.items()}
        datos.update({clave: selector.obtener() for clave, selector in self.fechas.items()})
        return datos

    def establecer(self, datos: dict) -> None:
        for clave, valor in datos.items():
            if valor is None:
                continue
            if clave in self.fechas:
                self.fechas[clave].establecer(valor)
            elif clave in self.variables:
                if clave in matricula.BOOLEANOS:
                    valor = "Sí" if valor in (True, 1, "1", "Sí") else "No"
                self.variables[clave].set(str(valor))

    def limpiar(self) -> None:
        for variable in self.variables.values():
            variable.set("")
        for selector in self.fechas.values():
            selector.limpiar()


class RealizarMatricula(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.guardado = False
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self._paso_documentos()
        self._paso_datos()
        self._paso_verificacion()
        self._paso_guardar()
        self._paso_matricula()
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._al_cambiar_paso())
        self.reiniciar()

    # ------------------------------------------------------------ utilidades
    def _nuevo_paso(self, titulo: str) -> ttk.Frame:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text=titulo)
        return marco

    def _desplazable(self, parent) -> ttk.Frame:
        """Frame con barra de desplazamiento vertical para formularios largos."""
        lienzo = tk.Canvas(parent, highlightthickness=0, background="#F7F6F2")
        barra = ttk.Scrollbar(parent, orient="vertical", command=lienzo.yview)
        interior = ttk.Frame(lienzo)
        interior.bind("<Configure>", lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        ventana = lienzo.create_window((0, 0), window=interior, anchor="nw")
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana, width=e.width))
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return interior

    def recargar(self) -> None:
        """Al entrar a la sección no se pierde lo que se está escribiendo."""
        self._al_cambiar_paso()

    def reiniciar(self) -> None:
        self.guardado = False
        for campos in (self.est, self.padre, self.madre, self.cons):
            campos.limpiar()
        self.est.establecer({"LugarQueOcupa": "1", "PaisNacimiento": "Perú",
                             "ViveConPadre": "Sí", "ViveConMadre": "Sí",
                             "ElPadreVive": "Sí", "LaMadreVive": "Sí"})
        self.padre.establecer({"Sexo": "M"})
        self.madre.establecer({"Sexo": "F"})
        self.var_registrar_padre.set(True)
        self.var_registrar_madre.set(True)
        self.var_responsable.set("Madre")
        self.var_sin_constancia.set(False)
        self.tabla_logros.delete(*self.tabla_logros.get_children())
        for etiqueta in self.estado_documentos.values():
            etiqueta.config(text="Sin archivo", foreground=TEXTO_SUAVE)
        self.var_verificado.set(False)
        self.var_situacion_vista.set("APROBADO")
        self.lbl_guardado.config(text="Los datos aún no se han guardado.", foreground=TEXTO_SUAVE)
        self.lbl_resultado.config(text="")
        self.notebook.select(0)

    # ------------------------------------------------------------ paso 1
    def _paso_documentos(self) -> None:
        marco = self._nuevo_paso("1. Documentos")
        ttk.Label(
            marco, wraplength=760,
            text="Suba la imagen de cada documento para prellenar el formulario con OCR. "
                 "El OCR es solo una ayuda: en el paso 2 puede corregir o escribir todo a mano.",
        ).pack(anchor="w", pady=(0, 10))
        caja = tarjeta(marco)
        caja.pack(fill="x")
        self.estado_documentos: dict[str, ttk.Label] = {}
        documentos = (
            ("estudiante", "DNI del estudiante"),
            ("padre", "DNI del padre"),
            ("madre", "DNI de la madre"),
            ("constancia", "Consolidado de notas (constancia de logros)"),
        )
        for fila, (clave, texto) in enumerate(documentos):
            ttk.Button(caja, text=f"Subir {texto}", width=46,
                       command=lambda c=clave: self._subir_documento(c)).grid(
                row=fila, column=0, sticky="w", pady=4)
            etiqueta = ttk.Label(caja, text="Sin archivo", style="Card.Muted.TLabel")
            etiqueta.grid(row=fila, column=1, sticky="w", padx=12)
            self.estado_documentos[clave] = etiqueta
        ttk.Button(marco, text="Continuar al paso 2", style="Primary.TButton",
                   command=lambda: self.notebook.select(1)).pack(anchor="e", pady=12)

    def _subir_documento(self, clave: str) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Seleccione la imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        etiqueta = self.estado_documentos[clave]
        try:
            import ocr

            lineas = ocr.extraer_lineas(ruta)
            if clave == "constancia":
                aplicados = self._aplicar_constancia(*ocr.extraer_constancia(lineas))
            else:
                tabla = "ESTUDIANTE" if clave == "estudiante" else "PADRE_APODERADO"
                aplicados = self._aplicar_dni(clave, ocr.extraer_dni(lineas, tabla))
        except Exception as exc:  # OCR no disponible o imagen ilegible
            etiqueta.config(text=f"No se pudo leer: {exc}. Complete los datos a mano.",
                            foreground=PELIGRO)
            return
        if aplicados:
            etiqueta.config(text=f"Prellenado: {', '.join(aplicados)}. Revise en el paso 2.",
                            foreground=EXITO)
        else:
            etiqueta.config(text="No se reconocieron datos. Complete los datos a mano.",
                            foreground=PELIGRO)

    def _aplicar_dni(self, clave: str, campos: dict) -> list[str]:
        destino = {"estudiante": self.est, "padre": self.padre, "madre": self.madre}[clave]
        valores = {}
        for nombre, (valor, _confianza) in campos.items():
            campo = nombre.split(".", 1)[1]
            if campo in ("Celular", "OcupacionActual") and clave != "estudiante":
                continue  # se escriben a mano
            if valor not in (None, "") and (campo in destino.variables or campo in destino.fechas):
                valores[campo] = valor
        destino.establecer(valores)
        return sorted(valores)

    def _aplicar_constancia(self, campos: dict, logros: list) -> list[str]:
        equivalencias = {
            "CONSTANCIA_LOGROS.CodigoVirtual": "CodigoVirtual",
            "CONSTANCIA_LOGROS.NivelEducativo": "NivelEducativo",
            "CONSTANCIA_LOGROS.FechaHoraEmision": "FechaHoraEmision",
            "INSTITUCION_EDUCATIVA.CodigoModularIE": "CodigoModularIE",
            "INSTITUCION_EDUCATIVA.NombreIE": "NombreIE",
            "INSTITUCION_EDUCATIVA.TipoIE": "TipoIE",
        }
        valores = {equivalencias[c]: v for c, (v, _) in campos.items() if c in equivalencias and v}
        self.cons.establecer(valores)
        aplicados = sorted(valores)
        for logro in logros:
            fila = {c.split(".", 1)[1]: v for c, (v, _) in logro.items()}
            self.tabla_logros.insert("", "end", values=(
                fila.get("AñoEscolar", ""), fila.get("GradoCursado", ""),
                fila.get("CodigoModularIE", valores.get("CodigoModularIE", "")),
                valores.get("NombreIE", ""), fila.get("SituacionFinal", ""),
            ))
        if logros:
            aplicados.append(f"{len(logros)} logro(s)")
        return aplicados

    # ------------------------------------------------------------ paso 2
    def _paso_datos(self) -> None:
        marco = self._nuevo_paso("2. Datos")
        interno = ttk.Notebook(marco)
        interno.pack(fill="both", expand=True)

        # Estudiante
        pagina = ttk.Frame(interno, padding=8)
        interno.add(pagina, text="Estudiante")
        barra = ttk.Frame(pagina)
        barra.pack(fill="x")
        ttk.Button(barra, text="Cargar datos registrados del estudiante (por DNI)",
                   command=self._cargar_estudiante).pack(side="left")
        cuerpo = self._desplazable(pagina)
        self.est = Campos(cuerpo)
        self.est.texto("DNI", "DNI", dni=True)
        self.est.lista("Sexo", "Sexo", ("M", "F"))
        self.est.texto("Nombres", "Nombres")
        self.est.texto("ApellidoPaterno", "Apellido paterno")
        self.est.texto("ApellidoMaterno", "Apellido materno")
        self.est.fecha("FechaNacimiento", "Fecha de nacimiento", anio_min=1990)
        self.est.texto("DistritoNacimiento", "Distrito de nacimiento")
        self.est.texto("ProvinciaNacimiento", "Provincia de nacimiento")
        self.est.texto("DepartamentoNacimiento", "Departamento de nacimiento")
        self.est.texto("PaisNacimiento", "País de nacimiento")
        self.est.texto("DomicilioActual", "Domicilio actual")
        self.est.texto("DistritoDomicilio", "Distrito de domicilio")
        self.est.texto("Celular", "Celular del estudiante (opcional)")
        self.est.texto("CorreoElectronico", "Correo electrónico (opcional)")
        self.est.texto("Religion", "Religión (opcional)")
        self.est.texto("LugarQueOcupa", "Lugar que ocupa entre sus hermanos")
        self.est.lista("TipoAtencion", "Tipo de atención", TIPOS_ATENCION)
        self.est.texto("EnfermedadCronica", "Enfermedad crónica (opcional)")
        self.est.lista("ViveConPadre", "¿Vive con su padre?", SI_NO)
        self.est.lista("ViveConMadre", "¿Vive con su madre?", SI_NO)
        self.est.lista("ElPadreVive", "¿El padre vive?", SI_NO)
        self.est.lista("LaMadreVive", "¿La madre vive?", SI_NO)
        self.est.texto("NombreContactoEmergencia", "Nombre del contacto de emergencia")
        self.est.texto("CelularEmergencia", "Celular del contacto de emergencia")

        # Padre y madre
        self.var_registrar_padre = tk.BooleanVar(value=True)
        self.var_registrar_madre = tk.BooleanVar(value=True)
        self.padre = self._pagina_padre(interno, "Padre", self.var_registrar_padre, "M")
        self.madre = self._pagina_padre(interno, "Madre", self.var_registrar_madre, "F")

        # Responsable
        pagina = ttk.Frame(interno, padding=12)
        interno.add(pagina, text="Responsable")
        ttk.Label(pagina, text="Responsable de la matrícula (también queda como apoderado):").pack(anchor="w")
        self.var_responsable = tk.StringVar(value="Madre")
        for opcion in ("Padre", "Madre"):
            ttk.Radiobutton(pagina, text=opcion, value=opcion, variable=self.var_responsable).pack(anchor="w", pady=2)

        # Constancia y logros
        pagina = ttk.Frame(interno, padding=8)
        interno.add(pagina, text="Constancia y logros")
        self.var_sin_constancia = tk.BooleanVar(value=False)
        ttk.Checkbutton(pagina, text="Sin constancia (ingresante que no tiene logros previos)",
                        variable=self.var_sin_constancia).pack(anchor="w")
        datos = ttk.Frame(pagina)
        datos.pack(fill="x", pady=6)
        self.cons = Campos(datos, columnas=3)
        self.cons.texto("CodigoVirtual", "Código virtual (8 caracteres)")
        self.cons.lista("NivelEducativo", "Nivel educativo de la constancia", tuple(matricula.NIVELES))
        self.cons.fecha("FechaHoraEmision", "Fecha de emisión (opcional)", anio_min=2000)
        self.cons.texto("CodigoModularIE", "Código modular de la I.E. de procedencia")
        self.cons.texto("NombreIE", "Nombre de la I.E. de procedencia")
        self.cons.lista("TipoIE", "Tipo de I.E.", ("", "Estatal", "Particular"))

        ttk.Label(pagina, text="Logros (uno por año escolar):", style="Seccion.TLabel").pack(anchor="w", pady=(6, 2))
        columnas = ("Año", "Grado", "Código modular", "Nombre de la I.E.", "Situación final")
        self.tabla_logros = ttk.Treeview(pagina, columns=columnas, show="headings", height=5)
        for columna, ancho in zip(columnas, (70, 70, 120, 260, 180)):
            self.tabla_logros.heading(columna, text=columna)
            self.tabla_logros.column(columna, width=ancho, anchor="w")
        self.tabla_logros.pack(fill="x")
        self.tabla_logros.bind("<<TreeviewSelect>>", lambda _e: self._logro_seleccionado())

        edicion = ttk.Frame(pagina)
        edicion.pack(fill="x", pady=6)
        self.logro = Campos(edicion, columnas=5)
        self.logro.texto("AñoEscolar", "Año")
        self.logro.lista("GradoCursado", "Grado", TODOS_LOS_GRADOS)
        self.logro.texto("CodigoModularIE", "Código modular")
        self.logro.texto("NombreIE", "Nombre de la I.E.")
        self.logro.lista("SituacionFinal", "Situación final", matricula.SITUACIONES_FINALES)
        botones = ttk.Frame(pagina)
        botones.pack(fill="x")
        ttk.Button(botones, text="Agregar logro", command=self._agregar_logro).pack(side="left", padx=2)
        ttk.Button(botones, text="Reemplazar seleccionado", command=self._reemplazar_logro).pack(side="left", padx=2)
        ttk.Button(botones, text="Quitar seleccionado", command=self._quitar_logro).pack(side="left", padx=2)

        ttk.Button(marco, text="Continuar al paso 3", style="Primary.TButton",
                   command=lambda: self.notebook.select(2)).pack(anchor="e", pady=8)

    def _pagina_padre(self, interno, titulo: str, variable: tk.BooleanVar, sexo: str) -> Campos:
        pagina = ttk.Frame(interno, padding=8)
        interno.add(pagina, text=titulo)
        barra = ttk.Frame(pagina)
        barra.pack(fill="x")
        ttk.Checkbutton(barra, text=f"Registrar a la {titulo.lower()}" if sexo == "F"
                        else f"Registrar al {titulo.lower()}", variable=variable).pack(side="left")
        campos_holder: dict[str, Campos] = {}
        ttk.Button(barra, text="Cargar datos registrados (por DNI)",
                   command=lambda: self._cargar_padre(campos_holder["c"])).pack(side="left", padx=10)
        cuerpo = self._desplazable(pagina)
        campos = Campos(cuerpo)
        campos_holder["c"] = campos
        campos.texto("DNI", "DNI", dni=True)
        campos.lista("Sexo", "Sexo", ("M", "F"), inicial=sexo)
        campos.texto("Nombres", "Nombres")
        campos.texto("ApellidoPaterno", "Apellido paterno")
        campos.texto("ApellidoMaterno", "Apellido materno")
        campos.fecha("FechaNacimiento", "Fecha de nacimiento", anio_min=1940,
                     anio_max=date.today().year - 18)
        campos.texto("OcupacionActual", "Ocupación actual")
        campos.lista("GradoInstruccion", "Grado de instrucción", GRADOS_INSTRUCCION)
        campos.texto("DomicilioActual", "Domicilio actual")
        campos.texto("DistritoDomicilio", "Distrito de domicilio")
        campos.texto("TelefonoFijo", "Teléfono fijo (opcional, 9 dígitos)")
        campos.texto("Celular", "Celular (9 dígitos)")
        campos.texto("CorreoElectronico", "Correo electrónico (opcional)")
        return campos

    def _cargar_estudiante(self) -> None:
        dni = self.est.valores()["DNI"]
        try:
            datos = estudiantes.obtener_estudiante(dni) if len(dni) == 8 else None
        except ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        if not datos:
            messagebox.showinfo("Estudiante", "No hay un estudiante registrado con ese DNI.", parent=self)
            return
        self.est.establecer(datos)
        if datos.get("CodigoModularIE"):
            self.cons.establecer({"CodigoModularIE": datos["CodigoModularIE"]})

    def _cargar_padre(self, campos: Campos) -> None:
        dni = campos.valores()["DNI"]
        try:
            datos = padres.obtener_padre(dni) if len(dni) == 8 else None
        except ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        if not datos:
            messagebox.showinfo("Padre / madre", "No hay un registro con ese DNI.", parent=self)
            return
        campos.establecer(datos)

    # -------- logros
    def _logro_actual(self) -> tuple | None:
        valores = self.logro.valores()
        if not (valores["AñoEscolar"].isdigit() and len(valores["AñoEscolar"]) == 4):
            messagebox.showwarning("Logro", "El año debe tener 4 dígitos.", parent=self)
            return None
        if not valores["GradoCursado"] or not valores["SituacionFinal"]:
            messagebox.showwarning("Logro", "Seleccione el grado y la situación final.", parent=self)
            return None
        if not valores["CodigoModularIE"]:
            messagebox.showwarning("Logro", "Ingrese el código modular de la I.E.", parent=self)
            return None
        return (valores["AñoEscolar"], valores["GradoCursado"], valores["CodigoModularIE"],
                valores["NombreIE"], valores["SituacionFinal"])

    def _agregar_logro(self) -> None:
        fila = self._logro_actual()
        if fila:
            self.tabla_logros.insert("", "end", values=fila)

    def _reemplazar_logro(self) -> None:
        item = self.tabla_logros.focus()
        fila = self._logro_actual() if item else None
        if item and fila:
            self.tabla_logros.item(item, values=fila)

    def _quitar_logro(self) -> None:
        item = self.tabla_logros.focus()
        if item:
            self.tabla_logros.delete(item)

    def _logro_seleccionado(self) -> None:
        item = self.tabla_logros.focus()
        if not item:
            return
        anio, grado, codigo, nombre, situacion = self.tabla_logros.item(item, "values")
        self.logro.establecer({"AñoEscolar": anio, "GradoCursado": grado, "CodigoModularIE": codigo,
                               "NombreIE": nombre, "SituacionFinal": situacion})

    def _logros(self) -> list[dict]:
        logros = []
        for item in self.tabla_logros.get_children():
            anio, grado, codigo, nombre, situacion = self.tabla_logros.item(item, "values")
            logros.append({"AñoEscolar": int(anio), "GradoCursado": grado, "CodigoModularIE": codigo,
                           "NombreIE": nombre, "SituacionFinal": situacion})
        return sorted(logros, key=lambda fila: fila["AñoEscolar"])

    # ------------------------------------------------------------ paso 3
    def _paso_verificacion(self) -> None:
        marco = self._nuevo_paso("3. Verificación")
        caja = tarjeta(marco)
        caja.pack(fill="x")
        ttk.Label(caja, text=AVISO_MINEDU, wraplength=760, style="Card.TLabel").pack(anchor="w")
        botones = ttk.Frame(caja, style="Card.TFrame")
        botones.pack(anchor="w", pady=10)
        ttk.Button(botones, text="Abrir página del MINEDU", style="Primary.TButton",
                   command=self._abrir_minedu).pack(side="left", padx=(0, 6))
        ttk.Button(botones, text="Copiar código virtual", command=self._copiar_codigo).pack(side="left")
        self.lbl_codigo = ttk.Label(caja, text="", style="Card.Muted.TLabel")
        self.lbl_codigo.pack(anchor="w")

        self.var_verificado = tk.BooleanVar(value=False)
        ttk.Checkbutton(marco, text="Verifiqué el código virtual en el MINEDU",
                        variable=self.var_verificado).pack(anchor="w", pady=(14, 4))
        fila = ttk.Frame(marco)
        fila.pack(anchor="w")
        ttk.Label(fila, text="Situación final que se ve en la página del MINEDU:").pack(side="left")
        self.var_situacion_vista = tk.StringVar(value="APROBADO")
        ttk.Combobox(fila, textvariable=self.var_situacion_vista, state="readonly", width=26,
                     values=matricula.SITUACIONES_FINALES).pack(side="left", padx=6)
        ttk.Label(marco, foreground=TEXTO_SUAVE, wraplength=760,
                  text="Si el estudiante no tiene constancia (marcado en el paso 2), este paso no aplica.").pack(anchor="w", pady=8)
        ttk.Button(marco, text="Continuar al paso 4", style="Primary.TButton",
                   command=lambda: self.notebook.select(3)).pack(anchor="e", pady=8)

    def _abrir_minedu(self) -> None:
        webbrowser.open(config.url_consulta_constancia or "https://constancia.minedu.gob.pe/")

    def _copiar_codigo(self) -> None:
        codigo = self.cons.valores()["CodigoVirtual"].upper()
        if not codigo:
            messagebox.showwarning("Código virtual", "Ingrese el código virtual en el paso 2.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(codigo)
        self.lbl_codigo.config(text=f"Copiado: {codigo}  |  DNI del estudiante: {self.est.valores()['DNI']}")

    def verificacion_confirmada(self) -> bool:
        return bool(self.var_sin_constancia.get() or self.var_verificado.get())

    # ------------------------------------------------------------ paso 4
    def _paso_guardar(self) -> None:
        marco = self._nuevo_paso("4. Guardar datos")
        ttk.Label(
            marco, wraplength=760,
            text="Se guardan en una sola transacción el padre, la madre, la institución "
                 "educativa, el estudiante, la relación con sus padres, la constancia y los "
                 "logros. Si un DNI ya existe, sus datos se actualizan.",
        ).pack(anchor="w")
        ttk.Button(marco, text="Guardar datos", style="Primary.TButton",
                   command=self.guardar).pack(anchor="w", pady=12)
        self.lbl_guardado = ttk.Label(marco, text="", wraplength=760)
        self.lbl_guardado.pack(anchor="w")

    def datos_formulario(self) -> dict:
        estudiante = self.est.valores()
        padre = self.padre.valores() if self.var_registrar_padre.get() else None
        madre = self.madre.valores() if self.var_registrar_madre.get() else None
        elegido = padre if self.var_responsable.get() == "Padre" else madre
        constancia = self.cons.valores()
        sin_constancia = self.var_sin_constancia.get()
        if constancia.get("FechaHoraEmision"):
            constancia["FechaHoraEmision"] += " 00:00:00"
        try:
            existe = bool(estudiantes.obtener_estudiante(estudiante["DNI"])) if len(estudiante["DNI"]) == 8 else False
        except ErrorApp:
            existe = False
        return {
            "estudiante": estudiante,
            "estudiante_existe": existe,
            "padre": padre,
            "madre": madre,
            "responsable": (elegido or {}).get("DNI", ""),
            "ie": {campo: constancia.get(campo) for campo in ("CodigoModularIE", "NombreIE", "TipoIE")},
            "constancia": {} if sin_constancia else {
                "CodigoVirtual": constancia.get("CodigoVirtual", "").upper(),
                "NivelEducativo": constancia.get("NivelEducativo"),
                "FechaHoraEmision": constancia.get("FechaHoraEmision"),
            },
            "logros": [] if sin_constancia else self._logros(),
        }

    def guardar(self) -> None:
        datos = self.datos_formulario()
        if not self.var_sin_constancia.get():
            codigo = datos["constancia"]["CodigoVirtual"]
            if len(codigo) != 8 or not codigo.isalnum():
                messagebox.showwarning("Constancia", "El código virtual debe tener 8 caracteres "
                                       "alfanuméricos, o marque 'Sin constancia'.", parent=self)
                return
            if not datos["constancia"]["NivelEducativo"]:
                messagebox.showwarning("Constancia", "Seleccione el nivel educativo de la constancia.",
                                       parent=self)
                return
        try:
            matricula.guardar_datos(datos)
        except ErrorApp as exc:
            self.guardado = False
            self.lbl_guardado.config(text=str(exc), foreground=PELIGRO)
            messagebox.showerror("No se guardaron los datos", str(exc), parent=self)
            return
        self.guardado = True
        hora = datetime.now().strftime("%H:%M")
        self.lbl_guardado.config(text=f"Datos guardados correctamente ({hora}). Continúe con el paso 5.",
                                 foreground=EXITO)
        messagebox.showinfo("Listo", "Datos guardados correctamente.", parent=self)

    # ------------------------------------------------------------ paso 5
    def _paso_matricula(self) -> None:
        marco = self._nuevo_paso("5. Matrícula")
        self.lbl_requisitos = ttk.Label(marco, text="", wraplength=760)
        self.lbl_requisitos.pack(anchor="w")
        self.lbl_corresponde = ttk.Label(marco, text="", wraplength=760, style="Seccion.TLabel")
        self.lbl_corresponde.pack(anchor="w", pady=(6, 10))

        fila = ttk.Frame(marco)
        fila.pack(anchor="w")
        anio_actual = date.today().year
        self.var_anio = tk.StringVar(value=str(anio_actual))
        self.var_nivel = tk.StringVar()
        self.var_grado = tk.StringVar()
        self.var_seccion = tk.StringVar()
        for texto, variable, valores, ancho in (
            ("Año escolar", self.var_anio, [str(anio_actual), str(anio_actual + 1)], 8),
            ("Nivel", self.var_nivel, list(matricula.NIVELES), 12),
            ("Grado", self.var_grado, [], 8),
            ("Sección", self.var_seccion, [], 6),
        ):
            ttk.Label(fila, text=texto).pack(side="left", padx=(0, 4))
            combo = ttk.Combobox(fila, textvariable=variable, values=valores, width=ancho, state="readonly")
            combo.pack(side="left", padx=(0, 12))
            combo.bind("<<ComboboxSelected>>", lambda _e: self._actualizar_opciones())
            if variable is self.var_grado:
                self.cmb_grado = combo
            if variable is self.var_seccion:
                self.cmb_seccion = combo
        self.lbl_vacantes = ttk.Label(marco, text="")
        self.lbl_vacantes.pack(anchor="w", pady=8)
        self.lbl_advertencia = ttk.Label(marco, text="", foreground=PELIGRO, wraplength=760)
        self.lbl_advertencia.pack(anchor="w")
        botones = ttk.Frame(marco)
        botones.pack(anchor="w", pady=10)
        self.btn_registrar = ttk.Button(botones, text="Registrar matrícula", style="Primary.TButton",
                                        command=self.registrar)
        self.btn_registrar.pack(side="left")
        ttk.Button(botones, text="Nueva matrícula", command=self._nueva).pack(side="left", padx=8)
        self.lbl_resultado = ttk.Label(marco, text="", wraplength=760)
        self.lbl_resultado.pack(anchor="w")
        self.corresponde: tuple[str, str] | None = None

    def _al_cambiar_paso(self) -> None:
        if self.notebook.index(self.notebook.select()) == 4:
            self._preparar_matricula()

    def _preparar_matricula(self) -> None:
        faltan = []
        if not self.verificacion_confirmada():
            faltan.append("confirmar la verificación del código virtual (paso 3)")
        if not self.guardado:
            faltan.append("guardar los datos (paso 4)")
        habilitado = not faltan
        self.btn_registrar.config(state="normal" if habilitado else "disabled")
        self.lbl_requisitos.config(
            text="Listo para matricular." if habilitado else "Antes de matricular debe " + " y ".join(faltan) + ".",
            foreground=EXITO if habilitado else PELIGRO,
        )
        self.corresponde = None
        logros = [] if self.var_sin_constancia.get() else self._logros()
        nivel_constancia = self.cons.valores().get("NivelEducativo")
        if logros and nivel_constancia:
            ultimo = logros[-1]
            try:
                self.corresponde = matricula.grado_que_corresponde(
                    nivel_constancia, ultimo["GradoCursado"], self.var_situacion_vista.get())
            except ErrorApp as exc:
                self.lbl_corresponde.config(text=f"No se pudo calcular el grado: {exc}")
        if self.corresponde:
            nivel, grado = self.corresponde
            texto = ("El estudiante egresó de Secundaria." if grado == "EGRESADO"
                     else f"Según el último logro le corresponde: {nivel} {grado}.")
            self.lbl_corresponde.config(text=texto)
            if nivel and not self.var_nivel.get():
                self.var_nivel.set(nivel)
                self._actualizar_opciones()
                if grado in matricula.NIVELES.get(nivel, ()):
                    self.var_grado.set(grado)
        elif not logros:
            self.lbl_corresponde.config(text="Sin logros registrados: elija el nivel y el grado.")
        self._actualizar_opciones()

    def _actualizar_opciones(self) -> None:
        nivel = self.var_nivel.get()
        grados = matricula.NIVELES.get(nivel, ())
        secciones = matricula.SECCIONES.get(nivel, ())
        self.cmb_grado.configure(values=list(grados))
        self.cmb_seccion.configure(values=list(secciones))
        if self.var_grado.get() not in grados:
            self.var_grado.set("")
        if self.var_seccion.get() not in secciones:
            self.var_seccion.set(secciones[0] if secciones else "")
        advertencia = ""
        if self.corresponde and self.var_grado.get():
            if (self.var_nivel.get(), self.var_grado.get()) != self.corresponde:
                advertencia = (f"Atención: el grado elegido ({nivel} {self.var_grado.get()}) no coincide "
                               f"con el que corresponde ({self.corresponde[0]} {self.corresponde[1]}).")
        self.lbl_advertencia.config(text=advertencia)
        if nivel and self.var_grado.get() and self.var_seccion.get():
            try:
                cupo = matricula.cupos_seccion(int(self.var_anio.get()), nivel,
                                               self.var_grado.get(), self.var_seccion.get())
                self.lbl_vacantes.config(
                    text=f"Sección {self.var_seccion.get()}: {cupo['Matriculados']} matriculados, "
                         f"{cupo['Vacantes']} vacantes (máximo {matricula.CAPACIDAD}).",
                    foreground=PELIGRO if cupo["Vacantes"] <= 0 else EXITO)
            except ErrorApp as exc:
                self.lbl_vacantes.config(text=str(exc), foreground=PELIGRO)
        else:
            self.lbl_vacantes.config(text="Elija nivel, grado y sección para ver las vacantes.",
                                     foreground=TEXTO_SUAVE)

    def registrar(self) -> None:
        self._preparar_matricula()
        if str(self.btn_registrar.cget("state")) == "disabled":
            return
        datos = self.datos_formulario()
        sesion = auth.sesion_actual()
        if sesion is None:
            messagebox.showerror("Sesión", "Inicie sesión nuevamente.", parent=self)
            return
        try:
            matricula.registrar_matricula(
                datos["estudiante"]["DNI"], int(self.var_anio.get()), self.var_nivel.get(),
                self.var_grado.get(), self.var_seccion.get(), datos["responsable"], sesion.dni,
            )
        except ErrorApp as exc:
            self.lbl_resultado.config(text=str(exc), foreground=PELIGRO)
            messagebox.showerror("No se registró la matrícula", str(exc), parent=self)
            return
        texto = (f"Matrícula registrada: {datos['estudiante']['DNI']} en {self.var_nivel.get()} "
                 f"{self.var_grado.get()} {self.var_seccion.get()} ({self.var_anio.get()}).")
        self.lbl_resultado.config(text=texto, foreground=EXITO)
        self._actualizar_opciones()
        messagebox.showinfo("Matrícula registrada", texto, parent=self)

    def _nueva(self) -> None:
        if messagebox.askyesno("Nueva matrícula", "¿Limpiar todos los pasos para una nueva matrícula?",
                               parent=self):
            self.var_nivel.set("")
            self.var_grado.set("")
            self.reiniciar()
