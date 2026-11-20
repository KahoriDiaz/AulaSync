"""Ventana principal con menú y pestañas según el rol del usuario (§6).

- Secretaria: Mantenimiento (CRUD) de Estudiantes, Padres/Apoderados e
  Instituciones Educativas, y Reportes (las 10 consultas).
- Padre: Mis solicitudes (bandeja de archivos JSON, §5).
Todo el acceso a datos usa servicios (SELECT / CALL sp_...).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app.servicios import auth, estudiantes, padres, instituciones
from app.ui.componentes import CampoBusqueda, Tabla
from app.ui.padre.mis_solicitudes import MisSolicitudes
from app.ui.secretaria.bandeja import BandejaSolicitudes
from app.ui.secretaria.distribucion import Distribucion
from app.ui.secretaria.listas import Listas
from app.ui.secretaria.reportes import Reportes


class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Registro de Matrícula")
        self.geometry("1000x600")
        self._construir_menu()
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

        sesion = auth.sesion_actual()
        rol = sesion.rol if sesion else ""

        if rol == "Secretaria":
            barra.add_command(
                label="Bandeja de solicitudes",
                command=lambda: self.mostrar_pestana("bandeja"),
            )
            m_mant = tk.Menu(barra, tearoff=0)
            m_mant.add_command(label="Estudiantes", command=lambda: self.mostrar_pestana("estudiantes"))
            m_mant.add_command(label="Padres / Apoderados", command=lambda: self.mostrar_pestana("padres"))
            m_mant.add_command(label="Instituciones Educativas", command=lambda: self.mostrar_pestana("instituciones"))
            barra.add_cascade(label="Mantenimiento", menu=m_mant)

            m_procesos = tk.Menu(barra, tearoff=0)
            m_procesos.add_command(label="Distribución por secciones", command=lambda: self.mostrar_pestana("distribucion"))
            m_procesos.add_command(label="Listas y comparación", command=lambda: self.mostrar_pestana("listas"))
            barra.add_cascade(label="Procesos", menu=m_procesos)

            m_reportes = tk.Menu(barra, tearoff=0)
            m_reportes.add_command(label="10 consultas representativas", command=lambda: self.mostrar_pestana("reportes"))
            m_reportes.add_command(label="Cupos por sección", command=lambda: self.mostrar_pestana("distribucion"))
            m_reportes.add_command(label="Comparación de listas", command=lambda: self.mostrar_pestana("listas"))
            barra.add_cascade(label="Reportes", menu=m_reportes)

        if rol == "Padre":
            barra.add_command(
                label="Mis solicitudes",
                command=lambda: self.mostrar_pestana("solicitudes"),
            )

        barra.add_command(label="Ayuda", command=self._ayuda)

    # ---------------------------------------------------------------- contenido
    def _construir_contenido(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

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
        self.pestanas["instituciones"] = self._pestana_crud(
            "instituciones", "Instituciones Educativas",
            columnas=["CodigoModularIE", "NombreIE", "TipoIE"],
            servicio=instituciones,
            campos_alta=["CodigoModularIE", "NombreIE", "TipoIE"],
        )
        sesion = auth.sesion_actual()
        if sesion and sesion.rol == "Secretaria":
            self.pestanas["bandeja"] = self._pestana_bandeja()
            self.pestanas["distribucion"] = self._pestana_distribucion()
            self.pestanas["listas"] = self._pestana_listas()
            self.pestanas["reportes"] = self._pestana_reportes()
        if sesion and sesion.rol == "Padre":
            self.pestanas["solicitudes"] = self._pestana_solicitudes()

    def _pestana_crud(self, clave, titulo, columnas, servicio, campos_alta):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=titulo)

        alto = frame.winfo_screenheight() if frame.winfo_screenheight() else 600

        marco_botonera = ttk.Frame(frame)
        marco_botonera.pack(fill="x", padx=5, pady=4)

        ttk.Button(
            marco_botonera, text="Nuevo",
            command=lambda: self._nuevo(clave, servicio, campos_alta),
        ).pack(side="left", padx=3)
        ttk.Button(
            marco_botonera, text="Editar",
            command=lambda: self._editar(clave, servicio, campos_alta),
        ).pack(side="left", padx=3)
        ttk.Button(
            marco_botonera, text="Eliminar",
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

    def _pestana_solicitudes(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Mis solicitudes")
        frame.contenido = MisSolicitudes(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _pestana_bandeja(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Bandeja de solicitudes")
        frame.contenido = BandejaSolicitudes(frame)
        frame.contenido.pack(fill="both", expand=True)
        return frame

    def _cargar_pestana_activa(self):
        indice = self.notebook.index("end") - 1
        if indice >= 0:
            self.notebook.select(indice)
        clave = self._clave_pestana_actual()
        if clave and clave in self.pestanas:
            self._recargar(clave)

    def _clave_pestana_actual(self):
        pestaña = self.notebook.select()
        if not pestaña:
            return None
        texto = self.notebook.tab(pestaña, "text")
        for clave, frame in self.pestanas.items():
            # Comparar por título conocido
            if clave == "estudiantes" and texto == "Estudiantes":
                return clave
            if clave == "padres" and texto == "Padres / Apoderados":
                return clave
            if clave == "instituciones" and texto == "Instituciones Educativas":
                return clave
            if clave == "solicitudes" and texto == "Mis solicitudes":
                return clave
            if clave == "bandeja" and texto == "Bandeja de solicitudes":
                return clave
            if clave == "distribucion" and texto == "Distribución":
                return clave
            if clave == "listas" and texto == "Listas y comparación":
                return clave
            if clave == "reportes" and texto == "Reportes (10 consultas)":
                return clave
        return None

    def mostrar_pestana(self, clave):
        for frame in self.pestanas.values():
            pass
        for i in range(self.notebook.index("end")):
            self.notebook.select(i)
            if self._clave_pestana_actual() == clave:
                self._recargar(clave)
                return

    def _recargar(self, clave):
        frame = self.pestanas.get(clave)
        if not frame:
            return
        if clave in ("solicitudes", "bandeja", "distribucion", "listas", "reportes"):
            frame.contenido.recargar()
            return
        servicio = frame.servicio
        filas = servicio.listar_estudiantes() if hasattr(servicio, "listar_estudiantes") else []
        if clave == "padres":
            filas = padres.listar_padres()
        elif clave == "instituciones":
            filas = instituciones.listar_instituciones()
        elif clave == "estudiantes":
            filas = estudiantes.listar_estudiantes()
        frame.tabla.cargar(filas)

    # ---------------------------------------------------------------- CRUD acciones
    def _nuevo(self, clave, servicio, campos_alta):
        valores = simpledialog.askstring(
            "Nuevo registro",
            "Ingrese los valores separados por coma (en orden de los campos del formulario).",
        )
        if not valores:
            return
        parametros = [v.strip() for v in valores.split(",")]
        try:
            servicio.insertar_estudiante(parametros) if clave == "estudiantes" else (
                servicio.insertar_padre(parametros) if clave == "padres" else servicio.insertar_institucion(parametros)
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._recargar(clave)
        messagebox.showinfo("Éxito", "Registro creado.")

    def _editar(self, clave, servicio, campos_alta):
        frame = self.pestanas[clave]
        sel = frame.tabla.seleccion()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un registro.")
            return
        valores = simpledialog.askstring(
            "Editar registro",
            "Ingrese los nuevos valores separados por coma.",
        )
        if not valores:
            return
        parametros = [v.strip() for v in valores.split(",")]
        try:
            servicio.actualizar_estudiante(parametros) if clave == "estudiantes" else (
                servicio.actualizar_padre(parametros) if clave == "padres" else servicio.actualizar_institucion(parametros)
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._recargar(clave)
        messagebox.showinfo("Éxito", "Registro actualizado.")

    def _eliminar(self, clave, servicio):
        frame = self.pestanas[clave]
        sel = frame.tabla.seleccion()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un registro.")
            return
        clave_pk = sel.get("DNI") or sel.get("CodigoModularIE")
        if not clave_pk:
            messagebox.showerror("Error", "No se pudo identificar la clave del registro.")
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el registro {clave_pk}?"):
            return
        try:
            servicio.eliminar_estudiante(clave_pk) if clave == "estudiantes" else (
                servicio.eliminar_padre(clave_pk) if clave == "padres" else servicio.eliminar_institucion(clave_pk)
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._recargar(clave)
        messagebox.showinfo("Éxito", "Registro eliminado.")

    # ---------------------------------------------------------------- acciones generales
    def cerrar_sesion(self):
        auth.logout()
        self.destroy()

    def _ayuda(self):
        messagebox.showinfo(
            "Ayuda",
            "Registro de Matrícula - Entrega 5\n"
            "Aplicativo de escritorio sin frameworks (tkinter + mysql-connector).\n"
            "Usuarios demo: secretaria / secretaria123  |  padre_demo / padre123",
        )


def abrir_ventana_principal():
    app = VentanaPrincipal()
    app.mainloop()
