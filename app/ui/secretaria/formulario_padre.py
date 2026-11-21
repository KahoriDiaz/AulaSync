
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from app.servicios.matricula import edad
from app.ui.selector_fecha import SelectorFecha


class FormularioPadre(tk.Toplevel):

    def __init__(self, parent, modo="nuevo", datos=None, al_guardar=None):
        super().__init__(parent)

        self.modo = modo
        self.datos = datos or {}
        self.al_guardar = al_guardar

        self.campos = {}
        self.controles = {}

        self.title(
            "AulaSync - Registrar padre / apoderado"
            if modo == "nuevo"
            else "AulaSync - Editar padre / apoderado"
        )

        self.geometry("850x620")
        self.minsize(750, 550)
        self.transient(parent)
        self.grab_set()

        self._construir_formulario()
        self._cargar_datos()

    def _campo(
        self,
        parent,
        clave,
        etiqueta,
        fila,
        columna,
        tipo="texto",
        ancho=32
    ):
        contenedor = ttk.Frame(parent)
        contenedor.grid(
            row=fila,
            column=columna,
            padx=12,
            pady=9,
            sticky="ew"
        )

        ttk.Label(
            contenedor,
            text=etiqueta
        ).pack(anchor="w", pady=(0, 3))

        if tipo == "fecha":
            # El padre o apoderado debe ser mayor de edad.
            self.selector_fecha = SelectorFecha(
                contenedor, anio_min=1940, anio_max=date.today().year - 18
            )
            self.selector_fecha.pack(anchor="w")
            self.controles[clave] = self.selector_fecha
            return self.selector_fecha

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

        elif tipo == "grado":
            control = ttk.Combobox(
                contenedor,
                textvariable=valor,
                values=[
                    "Primaria",
                    "Secundaria",
                    "Superior",
                    "Otros"
                ],
                state="readonly",
                width=ancho
            )

        else:
            control = ttk.Entry(
                contenedor,
                textvariable=valor,
                width=ancho
            )

        control.pack(fill="x")
        self.controles[clave] = control

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

        self._campo(
            personal, "DNI", "DNI", 0, 0
        )

        self._campo(
            personal, "Sexo", "Sexo", 0, 1,
            tipo="sexo"
        )

        self._campo(
            personal, "Nombres", "Nombres", 1, 0
        )

        self._campo(
            personal, "ApellidoPaterno",
            "Apellido paterno", 1, 1
        )

        self._campo(
            personal, "ApellidoMaterno",
            "Apellido materno", 2, 0
        )

        self._campo(
            personal, "FechaNacimiento",
            "Fecha de nacimiento", 2, 1, "fecha"
        )

        self._campo(
            personal, "OcupacionActual",
            "Ocupación actual", 3, 0
        )

        self._campo(
            personal, "GradoInstruccion",
            "Grado de instrucción", 3, 1,
            tipo="grado"
        )

        # PESTAÑA 2: DOMICILIO Y CONTACTO
        contacto = self._pestana("Domicilio y contacto")

        self._campo(
            contacto, "DomicilioActual",
            "Domicilio actual", 0, 0
        )

        self._campo(
            contacto, "DistritoDomicilio",
            "Distrito de domicilio", 0, 1
        )

        self._campo(
            contacto, "TelefonoFijo",
            "Teléfono fijo (opcional)", 1, 0
        )

        self._campo(
            contacto, "Celular",
            "Celular", 1, 1
        )

        self._campo(
            contacto, "CorreoElectronico",
            "Correo electrónico (opcional)", 2, 0
        )

        # En edición no se permite cambiar el DNI.
        if self.modo == "editar":
            self.controles["DNI"].configure(state="readonly")

        # BOTONERA
        botonera = ttk.Frame(self)
        botonera.pack(
            fill="x",
            padx=12,
            pady=(0, 12)
        )

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

        if self.datos.get("FechaNacimiento"):
            self.selector_fecha.establecer(self.datos["FechaNacimiento"])

        for clave, variable in self.campos.items():

            valor = self.datos.get(clave)

            if valor is None:
                continue

            variable.set(str(valor))

    def _obtener(self, clave):
        valor = self.campos[clave].get().strip()
        return valor if valor else None

    def _guardar(self):

        obligatorios = [
            "DNI",
            "Sexo",
            "Nombres",
            "ApellidoPaterno",
            "ApellidoMaterno",
            "GradoInstruccion",
            "DomicilioActual",
            "DistritoDomicilio",
            "Celular"
        ]

        for clave in obligatorios:
            if not self._obtener(clave):
                messagebox.showwarning(
                    "Campo obligatorio",
                    f"Debe completar el campo: {clave}",
                    parent=self
                )
                return

        # Validar DNI
        dni = self._obtener("DNI")

        if len(dni) != 8 or not dni.isdigit():
            messagebox.showwarning(
                "DNI inválido",
                "El DNI debe contener exactamente 8 dígitos.",
                parent=self
            )
            return

        # Validar sexo
        sexo = self._obtener("Sexo")

        if sexo not in ("M", "F"):
            messagebox.showwarning(
                "Sexo inválido",
                "Seleccione M o F.",
                parent=self
            )
            return

        # Validar grado de instrucción
        grado = self._obtener("GradoInstruccion")

        if grado not in (
            "Primaria",
            "Secundaria",
            "Superior",
            "Otros"
        ):
            messagebox.showwarning(
                "Dato inválido",
                "Seleccione un grado de instrucción válido.",
                parent=self
            )
            return

        # Validar fecha de nacimiento (18 años o más)
        if not self.selector_fecha.validar():
            messagebox.showwarning(
                "Fecha inválida",
                f"Fecha de nacimiento: {self.selector_fecha.mensaje_error}",
                parent=self
            )
            return

        if edad(self.selector_fecha.fecha()) < 18:
            messagebox.showwarning(
                "Fecha inválida",
                "El padre o apoderado debe tener 18 años o más.",
                parent=self
            )
            return

        fecha = self.selector_fecha.obtener()

        # Validar teléfonos
        for clave in ("Celular", "TelefonoFijo"):

            valor = self._obtener(clave)

            if valor and (
                len(valor) != 9 or not valor.isdigit()
            ):
                messagebox.showwarning(
                    "Teléfono inválido",
                    f"{clave} debe contener exactamente 9 dígitos.",
                    parent=self
                )
                return

        # Validar longitudes de los campos
        limites = {
            "Nombres": 50,
            "ApellidoPaterno": 30,
            "ApellidoMaterno": 30,
            "OcupacionActual": 50,
            "DomicilioActual": 100,
            "DistritoDomicilio": 30,
            "CorreoElectronico": 50
        }

        for clave, limite in limites.items():

            valor = self._obtener(clave)

            if valor and len(valor) > limite:
                messagebox.showwarning(
                    "Texto demasiado largo",
                    f"{clave} admite como máximo {limite} caracteres.",
                    parent=self
                )
                return

        # Validar correo electrónico si se proporciona
        correo = self._obtener("CorreoElectronico")

        if correo and (
            "@" not in correo or "." not in correo.split("@")[-1]
        ):
            messagebox.showwarning(
                "Correo inválido",
                "Ingrese un correo electrónico válido.",
                parent=self
            )
            return

        # Los 13 parámetros deben respetar el orden del procedimiento.
        parametros = [
            dni,
            sexo,
            self._obtener("Nombres"),
            self._obtener("ApellidoPaterno"),
            self._obtener("ApellidoMaterno"),
            fecha,
            self._obtener("OcupacionActual"),
            grado,
            self._obtener("DomicilioActual"),
            self._obtener("DistritoDomicilio"),
            self._obtener("TelefonoFijo"),
            self._obtener("Celular"),
            correo
        ]

        try:

            if self.al_guardar is None:
                raise RuntimeError(
                    "No se configuró la operación para guardar."
                )

            self.al_guardar(parametros)

            messagebox.showinfo(
                "Éxito",
                "Padre / apoderado registrado correctamente."
                if self.modo == "nuevo"
                else "Padre / apoderado actualizado correctamente.",
                parent=self
            )

            self.destroy()

        except Exception as exc:

            messagebox.showerror(
                "Error",
                str(exc),
                parent=self
            )
