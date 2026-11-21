
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime


class FormularioEstudiante(tk.Toplevel):

    def __init__(self, parent, modo="nuevo", datos=None, al_guardar=None):
        super().__init__(parent)

        self.modo = modo
        self.datos = datos or {}
        self.al_guardar = al_guardar
        self.campos = {}

        self.title(
            "Registrar estudiante" if modo == "nuevo"
            else "Editar estudiante"
        )
        self.geometry("950x720")
        self.minsize(800, 600)
        self.transient(parent)
        self.grab_set()

        self._construir_formulario()
        self._cargar_datos()

    def _campo(self, parent, clave, etiqueta, fila, columna,
               tipo="texto", ancho=32):

        contenedor = ttk.Frame(parent)
        contenedor.grid(
            row=fila,
            column=columna,
            padx=12,
            pady=7,
            sticky="ew"
        )

        ttk.Label(
            contenedor,
            text=etiqueta
        ).pack(anchor="w", pady=(0, 3))

        valor = tk.StringVar()
        self.campos[clave] = valor

        if tipo == "sexo":
            control = ttk.Combobox(
                contenedor,
                textvariable=valor,
                values=["M", "F"],
                state="readonly",
                width=ancho
            )
        elif tipo == "atencion":
            control = ttk.Combobox(
                contenedor, textvariable=valor,
                values=["ESSALUD", "SIS", "Otros"],
                state="readonly", width=ancho
            )
        elif tipo == "booleano":
            control = ttk.Combobox(
                contenedor,
                textvariable=valor,
                values=["Sí", "No"],
                state="readonly",
                width=ancho
            )
        elif tipo == "numero":
            control = ttk.Spinbox(
                contenedor,
                from_=1,
                to=20,
                textvariable=valor,
                width=ancho
            )
        else:
            control = ttk.Entry(
                contenedor,
                textvariable=valor,
                width=ancho
            )

        control.pack(fill="x")

        return control

    def _pestana(self, titulo):
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text=titulo)

        marco.columnconfigure(0, weight=1)
        marco.columnconfigure(1, weight=1)

        return marco

    def _construir_formulario(self):

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=12
        )

        # PESTAÑA 1: DATOS PERSONALES
        personal = self._pestana("Datos personales")

        self._campo(personal, "DNI", "DNI", 0, 0)
        self._campo(personal, "Sexo", "Sexo", 0, 1, "sexo")
        self._campo(personal, "Nombres", "Nombres", 1, 0)
        self._campo(personal, "ApellidoPaterno", "Apellido paterno", 1, 1)
        self._campo(personal, "ApellidoMaterno", "Apellido materno", 2, 0)
        self._campo(personal, "FechaNacimiento", "Fecha de nacimiento (AAAA-MM-DD)", 2, 1)

        # PESTAÑA 2: NACIMIENTO Y DOMICILIO
        domicilio = self._pestana("Nacimiento y domicilio")

        self._campo(domicilio, "DistritoNacimiento", "Distrito de nacimiento", 0, 0)
        self._campo(domicilio, "ProvinciaNacimiento", "Provincia de nacimiento", 0, 1)
        self._campo(domicilio, "DepartamentoNacimiento", "Departamento de nacimiento", 1, 0)
        self._campo(domicilio, "PaisNacimiento", "País de nacimiento", 1, 1)
        self._campo(domicilio, "DomicilioActual", "Domicilio actual", 2, 0)
        self._campo(domicilio, "DistritoDomicilio", "Distrito de domicilio", 2, 1)
        self._campo(domicilio, "Celular", "Celular del estudiante", 3, 0)
        self._campo(domicilio, "CorreoElectronico", "Correo electrónico", 3, 1)
        self._campo(domicilio, "Religion", "Religión", 4, 0)

        # PESTAÑA 3: FAMILIA Y SALUD
        familia = self._pestana("Familia y salud")

        self._campo(familia, "LugarQueOcupa", "Lugar que ocupa entre sus hermanos", 0, 0, "numero")
        self._campo(familia, "TipoAtencion", "Tipo de atención", 0, 1, tipo="atencion")
        self._campo(familia, "EnfermedadCronica", "Enfermedad crónica", 1, 0)

        self._campo(familia, "ViveConPadre", "¿Vive con su padre?", 2, 0, "booleano")
        self._campo(familia, "ViveConMadre", "¿Vive con su madre?", 2, 1, "booleano")
        self._campo(familia, "ElPadreVive", "¿El padre vive?", 3, 0, "booleano")
        self._campo(familia, "LaMadreVive", "¿La madre vive?", 3, 1, "booleano")

        # PESTAÑA 4: CONTACTO Y DATOS ACADÉMICOS
        contacto = self._pestana("Contacto y datos académicos")

        self._campo(
            contacto,
            "NombreContactoEmergencia",
            "Nombre del contacto de emergencia",
            0, 0
        )
        self._campo(
            contacto,
            "CelularEmergencia",
            "Celular del contacto de emergencia",
            0, 1
        )
        self._campo(
            contacto,
            "CodigoModularIE",
            "Código modular de la I.E.",
            1, 0
        )
        self._campo(
            contacto,
            "DNI_Apoderado",
            "DNI del apoderado",
            1, 1
        )

        if self.modo == "editar":
            self._campo(
                contacto,
                "IdContactoEmergencia",
                "ID del contacto de emergencia",
                2, 0
            )

            self.campos["IdContactoEmergencia"].set(
                str(self.datos.get("IdContactoEmergencia") or "")
            )

            # El contacto se conserva durante la edición.
            # Sus datos se muestran, pero no se modifican aquí.
            for clave in ("NombreContactoEmergencia", "CelularEmergencia"):
                for widget in contacto.winfo_children():
                    for hijo in widget.winfo_children():
                        if isinstance(hijo, ttk.Entry):
                            if hijo.cget("textvariable") == str(self.campos[clave]):
                                hijo.configure(state="readonly")

        # BOTONES
        botonera = ttk.Frame(self)
        botonera.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Button(
            botonera,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

        ttk.Button(
            botonera,
            text="Guardar",
            style="Primary.TButton",
            command=self._guardar
        ).pack(side="right", padx=5)

    def _cargar_datos(self):

        for clave, variable in self.campos.items():
            valor = self.datos.get(clave)

            if valor is None:
                continue

            if clave in (
                "ViveConPadre", "ViveConMadre",
                "ElPadreVive", "LaMadreVive"
            ):
                variable.set("Sí" if bool(valor) else "No")
            elif isinstance(valor, (date, datetime)):
                variable.set(valor.strftime("%Y-%m-%d"))
            else:
                variable.set(str(valor))

    def _obtener(self, clave):
        valor = self.campos[clave].get().strip()
        return valor if valor else None

    def _guardar(self):

        obligatorios = [
            "DNI", "Sexo", "Nombres",
            "ApellidoPaterno", "ApellidoMaterno",
            "FechaNacimiento", "DistritoNacimiento",
            "ProvinciaNacimiento", "DepartamentoNacimiento",
            "PaisNacimiento", "DomicilioActual",
            "DistritoDomicilio", "LugarQueOcupa",
            "ViveConPadre", "ViveConMadre",
            "ElPadreVive", "LaMadreVive"
        ]

        if self.modo == "nuevo":
            obligatorios += [
                "NombreContactoEmergencia",
                "CelularEmergencia"
            ]

        for clave in obligatorios:
            if not self._obtener(clave):
                messagebox.showwarning(
                    "Campo obligatorio",
                    f"Debe completar el campo: {clave}",
                    parent=self
                )
                return

        dni = self._obtener("DNI")

        if len(dni) != 8 or not dni.isdigit():
            messagebox.showwarning(
                "DNI inválido",
                "El DNI debe contener exactamente 8 dígitos.",
                parent=self
            )
            return

        if self._obtener("Sexo") not in ("M", "F"):
            messagebox.showwarning(
                "Sexo inválido",
                "Seleccione M o F.",
                parent=self
            )
            return

        try:
            fecha = datetime.strptime(
                self._obtener("FechaNacimiento"),
                "%Y-%m-%d"
            ).date()

            if fecha > date.today():
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Fecha inválida",
                "Ingrese una fecha válida con formato AAAA-MM-DD.",
                parent=self
            )
            return

        for clave in ("Celular", "CelularEmergencia"):
            valor = self._obtener(clave)
            if valor and (len(valor) != 9 or not valor.isdigit()):
                messagebox.showwarning(
                    "Celular inválido",
                    f"{clave} debe contener exactamente 9 dígitos.",
                    parent=self
                )
                return

        dni_apoderado = self._obtener("DNI_Apoderado")
        if dni_apoderado and (
            len(dni_apoderado) != 8 or not dni_apoderado.isdigit()
        ):
            messagebox.showwarning(
                "DNI inválido",
                "El DNI del apoderado debe contener 8 dígitos.",
                parent=self
            )
            return

        try:
            lugar = int(self._obtener("LugarQueOcupa"))
            if lugar < 1 or lugar > 255:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Dato inválido",
                "El lugar que ocupa debe ser un número entre 1 y 255.",
                parent=self
            )
            return

        def booleano(clave):
            return 1 if self._obtener(clave) == "Sí" else 0

        # Orden exacto de los parámetros de los procedimientos SQL.
        comunes = [
            dni,
            self._obtener("Sexo"),
            self._obtener("Nombres"),
            self._obtener("ApellidoPaterno"),
            self._obtener("ApellidoMaterno"),
            fecha,
            self._obtener("DistritoNacimiento"),
            self._obtener("ProvinciaNacimiento"),
            self._obtener("DepartamentoNacimiento"),
            self._obtener("PaisNacimiento"),
            self._obtener("DomicilioActual"),
            self._obtener("DistritoDomicilio"),
            self._obtener("Celular"),
            self._obtener("CorreoElectronico"),
            self._obtener("Religion"),
            lugar,
            self._obtener("TipoAtencion"),
            self._obtener("EnfermedadCronica"),
            booleano("ViveConPadre"),
            booleano("ViveConMadre"),
            booleano("ElPadreVive"),
            booleano("LaMadreVive"),
        ]

        if self.modo == "nuevo":
            parametros = comunes + [
                None,
                self._obtener("NombreContactoEmergencia"),
                self._obtener("CelularEmergencia"),
                self._obtener("CodigoModularIE"),
                dni_apoderado
            ]
        else:
            try:
                id_contacto = int(self._obtener("IdContactoEmergencia"))
            except (TypeError, ValueError):
                messagebox.showerror(
                    "Error",
                    "No se pudo recuperar el ID del contacto.",
                    parent=self
                )
                return

            parametros = comunes + [
                id_contacto,
                self._obtener("CodigoModularIE"),
                dni_apoderado
            ]

        try:
            if self.al_guardar:
                self.al_guardar(parametros)

            messagebox.showinfo(
                "Éxito",
                "Estudiante registrado correctamente."
                if self.modo == "nuevo"
                else "Estudiante actualizado correctamente.",
                parent=self
            )
            self.destroy()

        except Exception as exc:
            messagebox.showerror(
                "Error",
                str(exc),
                parent=self
            )
