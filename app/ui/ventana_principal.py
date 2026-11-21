"""Ventana principal de la secretaria (§6).

Menú: Archivo | Inicio | Mantenimiento | Realizar matrícula | Consultas | Ayuda,
cada uno con sus submenús. La barra lateral muestra las secciones y, bajo la
activa, sus sub-opciones (pasos de la matrícula o vistas de consultas). Cada sección es un frame con un
método ``recargar()``. Todo el acceso a datos usa servicios (SELECT / CALL sp_...).
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from app.servicios import auth
from app.ui.componentes import poner_iconos
from app.ui.iconos import icono
from app.config import config
from app.ui.tema import BLANCO, LATERAL_TEXTO, TEXTO, PantallaCarga, aplicar_tema, centrar

SECCIONES = (
    ("inicio", "Inicio", "Resumen del año escolar", "house"),
    ("mantenimiento", "Mantenimiento", "Registros de todas las tablas", "database"),
    ("matricula", "Realizar matrícula", "Documentos, datos, verificación y matrícula", "user-plus"),
    ("consultas", "Consultas", "Reportes, distribución y listas", "chart-column"),
)

# Tablas del mantenimiento agrupadas para el menú (títulos de mantenimiento.py).
GRUPOS_TABLAS = (
    ("Personas", ("Estudiante", "Padre / Apoderado", "Contacto de emergencia", "Secretaria")),
    ("Académico", ("Institución educativa", "Constancia de logros", "Logro", "Matrícula")),
    ("Relaciones", ("Tiene padres", "Hermandad", "Necesidades educativas especiales",
                    "Hermanos en la I.E.")),
)
PASOS_MATRICULA = ("1. Documentos", "2. Datos", "3. Verificación", "4. Guardar datos", "5. Matrícula")
VISTAS_CONSULTAS = ("Reportes (10 consultas)", "Distribución por secciones",
                    "Listas y comparación", "Panel de relaciones")
# Sub-opciones que se muestran en la barra lateral bajo la sección activa.
SUBOPCIONES = {
    "matricula": ("Documentos", "Datos", "Verificación", "Guardar datos", "Matrícula"),
    "consultas": ("Reportes", "Distribución", "Listas", "Panel de relaciones"),
}
NOMBRE_MANUAL = "Manual_de_usuario_AulaSync.docx"


class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # se muestra recién cuando todo está listo
        aplicar_tema(self)
        self.sesion_cerrada = False
        self.title("AulaSync - Secretaría")
        self.minsize(1000, 620)
        carga = PantallaCarga(self, "Abriendo AulaSync...", pasos=len(SECCIONES) + 1)
        try:
            self._construir_menu()
            self._construir_estructura()
            self._construir_contenido(carga)
            carga.avanzar("Cargando el resumen...")
            self.mostrar_pestana("inicio")
            poner_iconos(self)
        finally:
            carga.destroy()
        centrar(self, 1280, 780)
        self.deiconify()
        self.lift()
        self.focus_force()

    # ------------------------------------------------------------------ menú
    def _construir_menu(self):
        from app.servicios import reportes

        barra = tk.Menu(self)
        self.config(menu=barra)

        def submenu(padre=barra) -> tk.Menu:
            return tk.Menu(padre, tearoff=0, font=("Segoe UI", 10))

        def opcion(menu, texto, nombre_icono, comando, atajo=""):
            extra = {"image": icono(self, nombre_icono, 16, TEXTO), "compound": "left"} if nombre_icono else {}
            menu.add_command(label=f"  {texto}", command=comando, accelerator=atajo, **extra)

        m_archivo = submenu()
        opcion(m_archivo, "Cerrar sesión", "log-out", self.cerrar_sesion)
        m_archivo.add_separator()
        opcion(m_archivo, "Salir", "x", self.destroy, "Alt+F4")
        barra.add_cascade(label="Archivo", menu=m_archivo)

        m_inicio = submenu()
        opcion(m_inicio, "Ver resumen del año", "house", lambda: self.mostrar_pestana("inicio"), "F1")
        opcion(m_inicio, "Actualizar indicadores", "refresh", lambda: self.mostrar_pestana("inicio"))
        barra.add_cascade(label="Inicio", menu=m_inicio)

        m_mant = submenu()
        for grupo, tablas in GRUPOS_TABLAS:
            m_grupo = submenu(m_mant)
            for titulo in tablas:
                opcion(m_grupo, titulo, None, lambda t=titulo: self.ir_tabla(t))
            m_mant.add_cascade(label=f"  {grupo}", menu=m_grupo,
                               image=icono(self, "database", 16, TEXTO), compound="left")
        m_mant.add_separator()
        opcion(m_mant, "Ver todas las tablas", "layout-grid",
               lambda: self.mostrar_pestana("mantenimiento"), "F2")
        barra.add_cascade(label="Mantenimiento", menu=m_mant)

        m_matricula = submenu()
        opcion(m_matricula, "Nueva matrícula", "plus", self.nueva_matricula, "Ctrl+M")
        m_matricula.add_separator()
        iconos_pasos = ("upload", "file-text", "external-link", "save", "check-circle")
        for indice, (paso, nombre_icono) in enumerate(zip(PASOS_MATRICULA, iconos_pasos)):
            opcion(m_matricula, paso, nombre_icono, lambda i=indice: self.ir_paso(i))
        barra.add_cascade(label="Realizar matrícula", menu=m_matricula)

        m_consultas = submenu()
        m_reportes = submenu(m_consultas)
        for reporte in reportes.todos():
            opcion(m_reportes, f"{reporte.numero}. {reporte.titulo}", None,
                   lambda n=reporte.numero: self.abrir_reporte(n))
        m_consultas.add_cascade(label="  Reportes", menu=m_reportes,
                                image=icono(self, "file-text", 16, TEXTO), compound="left")
        iconos_vistas = ("chart-column", "layout-grid", "users")
        for indice, (vista, nombre_icono) in enumerate(zip(VISTAS_CONSULTAS[1:], iconos_vistas), 1):
            opcion(m_consultas, vista, nombre_icono, lambda i=indice: self.ir_consulta(i))
        barra.add_cascade(label="Consultas", menu=m_consultas)

        m_ayuda = submenu()
        opcion(m_ayuda, "Manual de usuario", "file-text", self.abrir_manual)
        opcion(m_ayuda, "Usuarios de prueba", "id-card", self._usuarios_prueba)
        m_ayuda.add_separator()
        opcion(m_ayuda, "Acerca de AulaSync", "help-circle", self._ayuda)
        barra.add_cascade(label="Ayuda", menu=m_ayuda)

        self.bind_all("<F1>", lambda _e: self.mostrar_pestana("inicio"))
        self.bind_all("<F2>", lambda _e: self.mostrar_pestana("mantenimiento"))
        self.bind_all("<Control-m>", lambda _e: self.nueva_matricula())

    # ---------------------------------------------------------- estructura
    def _construir_estructura(self):
        lateral = ttk.Frame(self, style="Lateral.TFrame", width=232)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)

        marca = ttk.Frame(lateral, style="Lateral.TFrame", padding=(20, 22, 20, 18))
        marca.pack(fill="x")
        ttk.Label(marca, text="AulaSync", style="Lateral.TLabel").pack(anchor="w")
        ttk.Label(marca, text="Matrícula escolar", style="LateralSuave.TLabel").pack(anchor="w")

        self.botones_nav: dict[str, ttk.Button] = {}
        self.marcos_sub: dict[str, ttk.Frame] = {}
        self.botones_sub: dict[str, list[ttk.Button]] = {}
        for clave, titulo, _detalle, nombre_icono in SECCIONES:
            boton = ttk.Button(lateral, text=f"   {titulo}", style="Nav.TButton",
                               image=icono(lateral, nombre_icono, 18, LATERAL_TEXTO),
                               compound="left",
                               command=lambda c=clave: self.mostrar_pestana(c))
            boton.pack(fill="x", padx=10, pady=1)
            self.botones_nav[clave] = boton
            if clave in SUBOPCIONES:
                marco = ttk.Frame(lateral, style="Lateral.TFrame")
                self.marcos_sub[clave] = marco
                self.botones_sub[clave] = []
                for indice, texto in enumerate(SUBOPCIONES[clave]):
                    sub = ttk.Button(marco, text=texto, style="NavSub.TButton",
                                     command=lambda c=clave, i=indice: self._ir_sub(c, i))
                    sub.pack(fill="x", padx=10)
                    self.botones_sub[clave].append(sub)

        pie = ttk.Frame(lateral, style="Lateral.TFrame", padding=(20, 12, 20, 20))
        pie.pack(side="bottom", fill="x")
        sesion = auth.sesion_actual()
        if sesion:
            ttk.Label(pie, text=sesion.nombres, style="LateralUsuario.TLabel",
                      wraplength=190).pack(anchor="w")
            ttk.Label(pie, text=f"Secretaria  |  DNI {sesion.dni}",
                      style="LateralSuave.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Button(pie, text="Cerrar sesión", style="Salir.TButton",
                   command=self.cerrar_sesion).pack(fill="x")

        derecha = ttk.Frame(self, padding=(26, 20, 26, 18))
        derecha.pack(side="left", fill="both", expand=True)
        encabezado = ttk.Frame(derecha)
        encabezado.pack(fill="x", pady=(0, 12))
        self.var_titulo = tk.StringVar()
        self.var_detalle = tk.StringVar()
        ttk.Label(encabezado, textvariable=self.var_titulo, style="Pagina.TLabel").pack(anchor="w")
        ttk.Label(encabezado, textvariable=self.var_detalle, style="PaginaSuave.TLabel").pack(anchor="w")
        self.notebook = ttk.Notebook(derecha, style="SinPestanas.TNotebook")
        self.notebook.pack(fill="both", expand=True)

    # ---------------------------------------------------------------- contenido
    def _construir_contenido(self, carga: PantallaCarga):
        # Importaciones diferidas: así la pantalla de carga aparece de inmediato.
        carga.avanzar("Preparando el inicio...")
        from app.ui.secretaria.inicio import Inicio

        self.pestanas: dict[str, tk.Widget] = {}
        self._agregar("inicio", Inicio(self.notebook, navegar=self.mostrar_pestana))
        carga.avanzar("Preparando el mantenimiento...")
        from app.ui.secretaria.mantenimiento import Mantenimiento

        self._agregar("mantenimiento", Mantenimiento(self.notebook))
        carga.avanzar("Preparando la matrícula...")
        from app.ui.secretaria.realizar_matricula import RealizarMatricula

        self._agregar("matricula", RealizarMatricula(self.notebook))
        carga.avanzar("Preparando las consultas...")
        from app.ui.secretaria.consultas import Consultas

        self._agregar("consultas", Consultas(self.notebook))
        self.notebook.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)
        for clave in SUBOPCIONES:
            interno = self._notebook_interno(clave)
            if interno is not None:
                interno.bind("<<NotebookTabChanged>>", lambda _e, c=clave: self._marcar_sub(c), add="+")

    def _agregar(self, clave: str, frame: tk.Widget) -> None:
        self.notebook.add(frame)
        self.pestanas[clave] = frame

    def _al_cambiar_pestana(self, _evento=None):
        clave = self._clave_pestana_actual()
        if clave:
            self._marcar(clave)
            self._recargar(clave)

    def _marcar(self, clave: str) -> None:
        """Resalta la sección activa en la barra lateral y actualiza el título."""
        for nombre, titulo, detalle, nombre_icono in SECCIONES:
            activo = nombre == clave
            self.botones_nav[nombre].configure(
                style="NavActivo.TButton" if activo else "Nav.TButton",
                image=icono(self, nombre_icono, 18, BLANCO if activo else LATERAL_TEXTO),
            )
            if activo:
                self.var_titulo.set(titulo)
                self.var_detalle.set(detalle)
            marco = self.marcos_sub.get(nombre)
            if marco is not None:
                if activo:
                    marco.pack(fill="x", pady=(2, 6), after=self.botones_nav[nombre])
                    self._marcar_sub(nombre)
                else:
                    marco.pack_forget()

    def _notebook_interno(self, clave: str):
        return getattr(self.pestanas.get(clave), "notebook", None)

    def _marcar_sub(self, clave: str) -> None:
        """Resalta la sub-opción visible (paso de la matrícula o vista de consultas)."""
        interno = self._notebook_interno(clave)
        if interno is None or clave not in self.botones_sub:
            return
        actual = interno.index(interno.select())
        for indice, boton in enumerate(self.botones_sub[clave]):
            boton.configure(style="NavSubActivo.TButton" if indice == actual else "NavSub.TButton")

    def _ir_sub(self, clave: str, indice: int) -> None:
        if clave == "matricula":
            self.ir_paso(indice)
        else:
            self.ir_consulta(indice)

    # ------------------------------------------------------- navegación directa
    def ir_tabla(self, titulo: str) -> None:
        """Abre Mantenimiento en la tabla indicada."""
        self.mostrar_pestana("mantenimiento")
        mantenimiento = self.pestanas["mantenimiento"]
        mantenimiento.notebook.select(mantenimiento.pestanas[titulo])

    def ir_paso(self, indice: int) -> None:
        """Abre Realizar matrícula en el paso indicado (0 a 4)."""
        self.mostrar_pestana("matricula")
        self.pestanas["matricula"].notebook.select(indice)

    def nueva_matricula(self) -> None:
        self.mostrar_pestana("matricula")
        self.pestanas["matricula"]._nueva()

    def ir_consulta(self, indice: int) -> None:
        """Abre Consultas en la vista indicada (0 = reportes)."""
        self.mostrar_pestana("consultas")
        self.pestanas["consultas"].notebook.select(indice)

    def abrir_reporte(self, numero: int) -> None:
        """Abre el reporte indicado con sus parámetros listos para ejecutar."""
        from app.servicios import reportes

        self.ir_consulta(0)
        self.pestanas["consultas"].pestanas[0]._seleccionar(reportes.obtener(numero))

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
            self._marcar(clave)
            self._recargar(clave)
        else:
            self.notebook.select(frame)  # <<NotebookTabChanged>> hace la recarga

    def _recargar(self, clave):
        frame = self.pestanas.get(clave)
        if frame is None:
            return
        try:
            frame.recargar()
        except Exception as exc:
            messagebox.showerror("Error al cargar los datos", str(exc), parent=self)

    # ---------------------------------------------------------------- acciones generales
    def cerrar_sesion(self):
        if not messagebox.askyesno("Cerrar sesión", "¿Desea cerrar la sesión?", parent=self):
            return
        auth.logout()
        self.sesion_cerrada = True
        self.destroy()

    def _ayuda(self):
        messagebox.showinfo(
            "Acerca de AulaSync",
            "AulaSync - Sistema de matrícula escolar\n"
            "Aplicativo de escritorio sin frameworks (tkinter + mysql-connector).\n"
            "Uso exclusivo de secretaria(s). Ingrese con DNI y clave.",
            parent=self,
        )

    def _usuarios_prueba(self):
        messagebox.showinfo(
            "Usuarios de prueba",
            "Secretaria 1: DNI 87733221, clave secretaria123\n"
            "Secretaria 2: DNI 87733222, clave secretaria123",
            parent=self,
        )

    def abrir_manual(self):
        """Abre el manual de usuario en Word si viene junto a AulaSync."""
        candidatos = (
            config.USER_DIR / NOMBRE_MANUAL,
            config.USER_DIR / "documentos" / NOMBRE_MANUAL,
            config.USER_DIR.parent / NOMBRE_MANUAL,
        )
        for ruta in candidatos:
            if ruta.is_file():
                os.startfile(ruta)  # abre con Word u otro programa asociado
                return
        messagebox.showinfo(
            "Manual de usuario",
            f"No se encontró el archivo {NOMBRE_MANUAL} junto a AulaSync.",
            parent=self,
        )


def abrir_ventana_principal() -> bool:
    """Abre la ventana principal; devuelve True si el usuario cerró sesión."""
    app = VentanaPrincipal()
    app.mainloop()
    return app.sesion_cerrada
