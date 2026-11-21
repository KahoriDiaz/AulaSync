"""Ventana principal de la secretaria (§6).

Menú: Archivo | Inicio | Mantenimiento | Realizar matrícula | Consultas | Ayuda.
La misma navegación está en la barra lateral. Cada sección es un frame con un
método ``recargar()``. Todo el acceso a datos usa servicios (SELECT / CALL sp_...).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.servicios import auth
from app.ui.componentes import poner_iconos
from app.ui.iconos import icono
from app.ui.tema import BLANCO, LATERAL_TEXTO, PantallaCarga, aplicar_tema, centrar

SECCIONES = (
    ("inicio", "Inicio", "Resumen del año escolar", "house"),
    ("mantenimiento", "Mantenimiento", "Registros de todas las tablas", "database"),
    ("matricula", "Realizar matrícula", "Documentos, datos, verificación y matrícula", "user-plus"),
    ("consultas", "Consultas", "Reportes, distribución y listas", "chart-column"),
)


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
        barra = tk.Menu(self)
        self.config(menu=barra)

        m_archivo = tk.Menu(barra, tearoff=0)
        m_archivo.add_command(label="Cerrar sesión", command=self.cerrar_sesion)
        m_archivo.add_separator()
        m_archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=m_archivo)

        barra.add_command(label="Inicio", command=lambda: self.mostrar_pestana("inicio"))
        barra.add_command(label="Mantenimiento", command=lambda: self.mostrar_pestana("mantenimiento"))
        barra.add_command(label="Realizar matrícula", command=lambda: self.mostrar_pestana("matricula"))
        barra.add_command(label="Consultas", command=lambda: self.mostrar_pestana("consultas"))
        barra.add_command(label="Ayuda", command=self._ayuda)

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
        for clave, titulo, _detalle, nombre_icono in SECCIONES:
            boton = ttk.Button(lateral, text=f"   {titulo}", style="Nav.TButton",
                               image=icono(lateral, nombre_icono, 18, LATERAL_TEXTO),
                               compound="left",
                               command=lambda c=clave: self.mostrar_pestana(c))
            boton.pack(fill="x", padx=10, pady=1)
            self.botones_nav[clave] = boton

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
            "AulaSync - Ayuda",
            "AulaSync - Sistema de Registro de Matrícula\n"
            "Aplicativo de escritorio sin frameworks (tkinter + mysql-connector).\n"
            "Uso exclusivo de secretaria(s). Ingrese con DNI y clave.\n"
            "Secretarias demo: DNI 87733221 / secretaria123  |  DNI 87733222 / secretaria123",
            parent=self,
        )


def abrir_ventana_principal() -> bool:
    """Abre la ventana principal; devuelve True si el usuario cerró sesión."""
    app = VentanaPrincipal()
    app.mainloop()
    return app.sesion_cerrada
