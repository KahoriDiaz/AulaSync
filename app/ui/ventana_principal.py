"""Ventana principal con menú y pestañas según el rol del usuario (§6).

- Secretaria: Mantenimiento (CRUD) de Estudiantes y Padres/Apoderados, y
  Reportes (las 10 consultas con botón propio cada una). Procesos: subir
  ficha de alumno y constancia de logros con OCR.
Todo el acceso a datos usa servicios (SELECT / CALL sp_...).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app.servicios import auth, estudiantes, padres
from app.ui.componentes import CampoBusqueda, Tabla, normalizar_dni
from app.ui.tema import aplicar_tema, cabecera
from app.ui.secretaria.bandeja import BandejaSolicitudes
from app.ui.secretaria.distribucion import Distribucion
from app.ui.secretaria.listas import Listas
from app.ui.secretaria.panel import PanelRelaciones
from app.ui.secretaria.reportes import Reportes
from app.ui.secretaria.subir_constancia import SubirConstancia
from app.ui.secretaria.subir_ficha import SubirFichaAlumno
from app.ui.secretaria.formulario_estudiante import FormularioEstudiante
from app.ui.secretaria.formulario_padre import FormularioPadre


def _limitar_dnis(campos: list[str], parametros: list[str]) -> list[str]:
    """Recorta los campos de DNI aunque vengan de un diálogo de texto libre."""
    for indice, campo in enumerate(campos):
        if campo in ("DNI", "DNI_Apoderado") and indice < len(parametros):
            parametros[indice] = normalizar_dni(parametros[indice])
    return parametros


class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        aplicar_tema(self)
        sesion = auth.sesion_actual()
        self.title("AulaSync - Bandeja de solicitudes")
        self.geometry("1000x600")
        self._construir_menu()
        cabecera(self, "AulaSync", "Secretaria").pack(fill="x")
        self._construir_contenido()
        self._cargar_pestana_activa()

    # ------------------------------------------------------------------ menú
    def _construir_menu(self):
        barra = tk.Menu(self)
        self.config(menu=barra)

        m_archivo = tk.Menu(barra, tearoff=0)
        m_archivo.add_command(label="Cerrar sesión", command=self.cerrar_sesion)
        m_archivo.add_separator()
        m_archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=m_archivo)

        barra.add_command(
            label="Bandeja de solicitudes",
            command=lambda: self.mostrar_pestana("bandeja"),
        )
        barra.add_command(
            label="Vacantes por atender",
            command=self._vacantes_por_atender,
        )
        m_mant = tk.Menu(barra, tearoff=0)
        m_mant.add_command(label="Estudiantes", command=lambda: self.mostrar_pestana("estudiantes"))
        m_mant.add_command(label="Padres / Apoderados", command=lambda: self.mostrar_pestana("padres"))
        barra.add_cascade(label="Mantenimiento", menu=m_mant)

        m_procesos = tk.Menu(barra, tearoff=0)
        m_procesos.add_command(label="Subir ficha de alumno (OCR)", command=self._subir_ficha)
        m_procesos.add_command(label="Subir constancia de logros (OCR)", command=self._subir_constancia)
        m_procesos.add_separator()
        m_procesos.add_command(label="Distribución por secciones", command=lambda: self.mostrar_pestana("distribucion"))
        m_procesos.add_command(label="Listas y comparación", command=lambda: self.mostrar_pestana("listas"))
        barra.add_cascade(label="Procesos", menu=m_procesos)

        m_reportes = tk.Menu(barra, tearoff=0)
        m_reportes.add_command(label="10 consultas representativas", command=lambda: self.mostrar_pestana("reportes"))
        m_reportes.add_command(label="Panel de relaciones", command=lambda: self.mostrar_pestana("panel"))
        m_reportes.add_command(label="Cupos por sección", command=lambda: self.mostrar_pestana("distribucion"))
        m_reportes.add_command(label="Comparación de listas", command=lambda: self.mostrar_pestana("listas"))
        barra.add_cascade(label="Reportes", menu=m_reportes)

        barra.add_command(label="Ayuda", command=self._ayuda)

    # ---------------------------------------------------------------- contenido
    def _construir_contenido(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self.pestanas = {}
        self.pestanas["estudiantes"] = self._pestana_crud(
            "estudiantes", "Estudiantes",
            columnas=["DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "FechaNacimiento", "Celular"],
            servicio=estudiantes,
            campos_alta=[
                "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno", "FechaNacimiento",
                "DistritoNacimiento", "ProvinciaNacimiento", "DepartamentoNacimiento", "PaisNacimiento",
                "DomicilioActual", "DistritoDomicilio", "Celular", "CorreoElectronico", "Religion",
                "LugarQueOcupa", "TipoAtencion", "EnfermedadCronica", "ViveConPadre", "ViveConMadre",
                "ElPadreVive", "LaMadreVive", "IdContactoEmergencia", "NombreContactoEmergencia",
                "CelularEmergencia", "CodigoModularIE", "DNI_Apoderado",
            ],
        )
        self.pestanas["padres"] = self._pestana_crud(
            "padres", "Padres / Apoderados",
            columnas=["DNI", "ApellidoPaterno", "ApellidoMaterno", "Nombres", "Celular", "CorreoElectronico"],
            servicio=padres,
            campos_alta=[
                "DNI", "Sexo", "Nombres", "ApellidoPaterno", "ApellidoMaterno", "FechaNacimiento",
                "OcupacionActual", "GradoInstruccion", "DomicilioActual", "DistritoDomicilio",
                "TelefonoFijo", "Celular", "CorreoElectronico",
            ],
        )
        self.pestanas["bandeja"] = self._pestana_bandeja()
        self.pestanas["distribucion"] = self._pestana_distribucion()
        self.pestanas["listas"] = self._pestana_listas()
        self.pestanas["reportes"] = self._pestana_reportes()
        self.pestanas["panel"] = self._pestana_panel()
        self.notebook.bind(
            "<<NotebookTabChanged>>",
            self._al_cambiar_pestana
        )
    def _al_cambiar_pestana(self, evento=None):
        clave = self._clave_pestana_actual()
        if clave:
            self._recargar(clave)
    def _pestana_crud(self, clave, titulo, columnas, servicio, campos_alta):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=titulo)

        alto = frame.winfo_screenheight() if frame.winfo_screenheight() else 600

        marco_botonera = ttk.Frame(frame)
        marco_botonera.pack(fill="x", padx=5, pady=4)

        ttk.Button(
            marco_botonera, text="Nuevo", style="Primary.TButton",
            command=lambda: self._nuevo(clave, servicio, campos_alta),
        ).pack(side="left", padx=3)
        ttk.Button(
            marco_botonera, text="Editar",
            command=lambda: self._editar(clave, servicio, campos_alta),
        ).pack(side="left", padx=3)
        ttk.Button(
            marco_botonera, text="Eliminar", style="Danger.TButton",
            command=lambda: self._eliminar(clave, servicio),
        ).pack(side="left", padx=3)

        busqueda = CampoBusqueda(
            marco_botonera, etiqueta="Buscar:",
            comando=lambda t: tabla.filtrar(t),
        )
        busqueda.pack(side="right", padx=5)

        tabla = Tabla(frame, columnas=columnas, anchos={c: 130 for c in columnas})
        tabla.pack(fill="both", expand=True, padx=5, pady=4)

        frame.tabla = tabla
        frame.servicio = servicio
        frame.campos_alta = campos_alta
        return frame

    def _pestana_reportes(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Reportes (10 consultas)")
        frame.contenido = Reportes(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _pestana_panel(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Panel de relaciones")
        frame.contenido = PanelRelaciones(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _pestana_distribucion(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Distribución")
        frame.contenido = Distribucion(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _pestana_listas(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Listas y comparación")
        frame.contenido = Listas(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _pestana_bandeja(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Bandeja de solicitudes")
        frame.contenido = BandejaSolicitudes(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    # def _cargar_pestana_activa(self):
    #     indice = self.notebook.index("end") - 1
    #     if indice >= 0:
    #         self.notebook.select(indice)
    #     clave = self._clave_pestana_actual()
    #     if clave and clave in self.pestanas:
    #         self._recargar(clave)
    def _cargar_pestana_activa(self):
        # La primera pestaña ya está seleccionada; el evento <<NotebookTabChanged>>
        # puede no dispararse antes del mainloop, así que se carga explícitamente.
        self.mostrar_pestana("estudiantes")

    def _clave_pestana_actual(self):
        """Clave de la pestaña visible, comparando el widget (no el título)."""
        seleccionada = self.notebook.select()
        for clave, frame in self.pestanas.items():
            if str(frame) == seleccionada:
                return clave
        return None

    def mostrar_pestana(self, clave):
        """Selecciona y recarga solo la pestaña pedida."""
        frame = self.pestanas.get(clave)
        if frame is None:
            return
        if self._clave_pestana_actual() == clave:
            # Ya visible: select() no dispara el evento, se recarga a mano.
            self._recargar(clave)
        else:
            self.notebook.select(frame)  # <<NotebookTabChanged>> hace la recarga

    def _recargar(self, clave):
        frame = self.pestanas.get(clave)
        if not frame:
            return
        try:
            if clave in ("bandeja", "distribucion", "listas", "reportes", "panel"):
                frame.contenido.recargar()
                return
            if clave == "padres":
                filas = padres.listar_padres()
            elif clave == "estudiantes":
                filas = estudiantes.listar_estudiantes()
            else:
                filas = []
            frame.tabla.cargar(filas)
        except Exception as exc:
            messagebox.showerror("Error al cargar los datos", str(exc), parent=self)

    # ---------------------------------------------------------------- CRUD acciones
    # def _nuevo(self, clave, servicio, campos_alta):
    #     valores = simpledialog.askstring(
    #         "Nuevo registro",
    #         "Ingrese los valores separados por coma (en orden de los campos del formulario).",
    #     )
    #     if not valores:
    #         return
    #     parametros = _limitar_dnis(campos_alta, [v.strip() for v in valores.split(",")])
    #     try:
    #         servicio.insertar_estudiante(parametros) if clave == "estudiantes" else (
    #             servicio.insertar_padre(parametros) if clave == "padres" else servicio.insertar_institucion(parametros)
    #         )
    #     except Exception as exc:
    #         messagebox.showerror("Error", str(exc))
    #         return
    #     self._recargar(clave)
    #     messagebox.showinfo("Éxito", "Registro creado.")

    # def _nuevo(self, clave, servicio, campos_alta):

    #     # Formulario completo para registrar estudiantes.
    #     if clave == "estudiantes":

    #         def guardar_estudiante(parametros):
    #             servicio.insertar_estudiante(parametros)
    #             self._recargar("estudiantes")

    #         self.formulario_estudiante = FormularioEstudiante(
    #             self,
    #             modo="nuevo",
    #             al_guardar=guardar_estudiante
    #         )
    #         return

    #     # Conservamos el registro anterior para padres e instituciones.
    #     valores = simpledialog.askstring(
    #         "Nuevo registro",
    #         "Ingrese los valores separados por coma."
    #     )

    #     if not valores:
    #         return

    #     parametros = _limitar_dnis(
    #         campos_alta,
    #         [v.strip() for v in valores.split(",")]
    #     )

    #     try:
    #         if clave == "padres":
    #             servicio.insertar_padre(parametros)
    #         elif clave == "instituciones":
    #             servicio.insertar_institucion(parametros)

    #     except Exception as exc:
    #         messagebox.showerror("Error", str(exc))
    #         return

    #     self._recargar(clave)
    #     messagebox.showinfo("Éxito", "Registro creado.")

    def _nuevo(self, clave, servicio, campos_alta):

        # Registro de estudiantes.
        if clave == "estudiantes":

            def guardar_estudiante(parametros):
                servicio.insertar_estudiante(parametros)
                self._recargar("estudiantes")

            self.formulario_estudiante = FormularioEstudiante(
                self,
                modo="nuevo",
                al_guardar=guardar_estudiante
            )
            return

        # Registro de padres y apoderados.
        if clave == "padres":

            def guardar_padre(parametros):
                servicio.insertar_padre(parametros)
                self._recargar("padres")

            self.formulario_padre = FormularioPadre(
                self,
                modo="nuevo",
                al_guardar=guardar_padre
            )
            return

        # Registro de instituciones educativas.
        valores = simpledialog.askstring(
            "Nuevo registro",
            "Ingrese los valores separados por coma."
        )

        if not valores:
            return

        parametros = _limitar_dnis(
            campos_alta,
            [v.strip() for v in valores.split(",")]
        )

        try:
            if clave == "instituciones":
                servicio.insertar_institucion(parametros)

        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return

        self._recargar(clave)

        messagebox.showinfo(
            "Éxito",
            "Registro creado.",
            parent=self
        )



    # def _editar(self, clave, servicio, campos_alta):

    #     frame = self.pestanas[clave]
    #     sel = frame.tabla.seleccion()
    #     if not sel:
    #         messagebox.showwarning("Atención", "Seleccione un registro.")
    #         return
    #     valores = simpledialog.askstring(
    #         "Editar registro",
    #         "Ingrese los nuevos valores separados por coma.",
    #     )
    #     if not valores:
    #         return
    #     parametros = _limitar_dnis(campos_alta, [v.strip() for v in valores.split(",")])
    #     try:
    #         servicio.actualizar_estudiante(parametros) if clave == "estudiantes" else (
    #             servicio.actualizar_padre(parametros) if clave == "padres" else servicio.actualizar_institucion(parametros)
    #         )
    #     except Exception as exc:
    #         messagebox.showerror("Error", str(exc))
    #         return
    #     self._recargar(clave)
    #     messagebox.showinfo("Éxito", "Registro actualizado.")


    # def _editar(self, clave, servicio, campos_alta):

    #     # Edición de estudiantes mediante el formulario completo.
    #     if clave == "estudiantes":
    #         frame = self.pestanas[clave]
    #         seleccionado = frame.tabla.seleccion()

    #         if not seleccionado:
    #             messagebox.showwarning(
    #                 "Atención",
    #                 "Seleccione un estudiante para editar.",
    #                 parent=self
    #             )
    #             return

    #         datos = servicio.obtener_estudiante(seleccionado["DNI"])

    #         if not datos:
    #             messagebox.showerror(
    #                 "Error",
    #                 "No se encontró el estudiante seleccionado.",
    #                 parent=self
    #             )
    #             return

    #         def guardar_cambios(parametros):
    #             servicio.actualizar_estudiante(parametros)
    #             self._recargar("estudiantes")

    #         self.formulario_estudiante = FormularioEstudiante(
    #             self,
    #             modo="editar",
    #             datos=datos,
    #             al_guardar=guardar_cambios
    #         )
    #         return

    #     # Edición de padres e instituciones con el método anterior.
    #     frame = self.pestanas[clave]
    #     sel = frame.tabla.seleccion()

    #     if not sel:
    #         messagebox.showwarning("Atención", "Seleccione un registro.")
    #         return

    #     valores = simpledialog.askstring(
    #         "Editar registro",
    #         "Ingrese los nuevos valores separados por coma.",
    #     )

    #     if not valores:
    #         return

    #     parametros = _limitar_dnis(
    #         campos_alta,
    #         [v.strip() for v in valores.split(",")]
    #     )

    #     try:
    #         if clave == "padres":
    #             servicio.actualizar_padre(parametros)
    #         elif clave == "instituciones":
    #             servicio.actualizar_institucion(parametros)

    #     except Exception as exc:
    #         messagebox.showerror("Error", str(exc))
    #         return

    #     self._recargar(clave)
    #     messagebox.showinfo("Éxito", "Registro actualizado.")


    def _editar(self, clave, servicio, campos_alta):

        # Edición de estudiantes.
        if clave == "estudiantes":
            frame = self.pestanas[clave]
            seleccionado = frame.tabla.seleccion()

            if not seleccionado:
                messagebox.showwarning(
                    "Atención",
                    "Seleccione un estudiante para editar.",
                    parent=self
                )
                return

            datos = servicio.obtener_estudiante(seleccionado["DNI"])

            if not datos:
                messagebox.showerror(
                    "Error",
                    "No se encontró el estudiante seleccionado.",
                    parent=self
                )
                return

            def guardar_cambios(parametros):
                servicio.actualizar_estudiante(parametros)
                self._recargar("estudiantes")

            self.formulario_estudiante = FormularioEstudiante(
                self,
                modo="editar",
                datos=datos,
                al_guardar=guardar_cambios
            )
            return

        # Edición de padres / apoderados.
        if clave == "padres":
            frame = self.pestanas[clave]
            seleccionado = frame.tabla.seleccion()

            if not seleccionado:
                messagebox.showwarning(
                    "Atención",
                    "Seleccione un padre o apoderado para editar.",
                    parent=self
                )
                return

            datos = servicio.obtener_padre(seleccionado["DNI"])

            if not datos:
                messagebox.showerror(
                    "Error",
                    "No se encontró el padre o apoderado seleccionado.",
                    parent=self
                )
                return

            def guardar_cambios(parametros):
                servicio.actualizar_padre(parametros)
                self._recargar("padres")

            self.formulario_padre = FormularioPadre(
                self,
                modo="editar",
                datos=datos,
                al_guardar=guardar_cambios
            )
            return

        # Edición de instituciones educativas.
        frame = self.pestanas[clave]
        seleccionado = frame.tabla.seleccion()

        if not seleccionado:
            messagebox.showwarning(
                "Atención",
                "Seleccione un registro.",
                parent=self
            )
            return

        valores = simpledialog.askstring(
            "Editar registro",
            "Ingrese los nuevos valores separados por coma.",
        )

        if not valores:
            return

        parametros = _limitar_dnis(
            campos_alta,
            [v.strip() for v in valores.split(",")]
        )

        try:
            if clave == "instituciones":
                servicio.actualizar_institucion(parametros)

        except Exception as exc:
            messagebox.showerror(
                "Error",
                str(exc),
                parent=self
            )
            return

        self._recargar(clave)

        messagebox.showinfo(
            "Éxito",
            "Registro actualizado.",
            parent=self
        )



    # def _eliminar(self, clave, servicio):
    #     frame = self.pestanas[clave]
    #     sel = frame.tabla.seleccion()
    #     if not sel:
    #         messagebox.showwarning("Atención", "Seleccione un registro.")
    #         return
    #     clave_pk = sel.get("DNI") or sel.get("CodigoModularIE")
    #     if not clave_pk:
    #         messagebox.showerror("Error", "No se pudo identificar la clave del registro.")
    #         return
    #     if not messagebox.askyesno("Confirmar", f"¿Eliminar el registro {clave_pk}?"):
    #         return
    #     try:
    #         servicio.eliminar_estudiante(clave_pk) if clave == "estudiantes" else (
    #             servicio.eliminar_padre(clave_pk) if clave == "padres" else servicio.eliminar_institucion(clave_pk)
    #         )
    #     except Exception as exc:
    #         messagebox.showerror("Error", str(exc))
    #         return
    #     self._recargar(clave)
    #     messagebox.showinfo("Éxito", "Registro eliminado.")


    def _eliminar(self, clave, servicio):
        frame = self.pestanas[clave]
        sel = frame.tabla.seleccion()

        if not sel:
            messagebox.showwarning(
                "Atención",
                "Seleccione un registro.",
                parent=self
            )
            return

        clave_pk = sel.get("DNI") or sel.get("CodigoModularIE")

        if not clave_pk:
            messagebox.showerror(
                "Error",
                "No se pudo identificar la clave del registro.",
                parent=self
            )
            return

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar el registro {clave_pk}?",
            parent=self
        ):
            return

        try:
            if clave == "estudiantes":
                servicio.eliminar_estudiante(clave_pk)
            elif clave == "padres":
                servicio.eliminar_padre(clave_pk)
            elif clave == "instituciones":
                servicio.eliminar_institucion(clave_pk)

        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return

        self._recargar(clave)

        messagebox.showinfo(
            "Éxito",
            "Registro eliminado.",
            parent=self
        )


    # ---------------------------------------------------------------- acciones generales
    def _subir_ficha(self) -> None:
        SubirFichaAlumno(self)

    def _subir_constancia(self) -> None:
        SubirConstancia(self)

    def _vacantes_por_atender(self):
        self.mostrar_pestana("bandeja")
        bandeja = self.pestanas.get("bandeja")
        if bandeja and hasattr(bandeja.contenido, "etapa_var"):
            bandeja.contenido.etapa_var.set("Vacante")
            bandeja.contenido.recargar()

    def cerrar_sesion(self):
        auth.logout()
        self.destroy()

    def _ayuda(self):
        messagebox.showinfo(
            "AulaSync - Ayuda",
            "AulaSync - Sistema de Registro de Matrícula\n"
            "Aplicativo de escritorio sin frameworks (tkinter + mysql-connector).\n"
            "Uso exclusivo de secretaria(s). Ingrese con DNI y clave.\n"
            "Secretarias demo: DNI 87733221 / secretaria123  |  DNI 87733222 / secretaria123",
        )


def abrir_ventana_principal():
    app = VentanaPrincipal()
    app.mainloop()
