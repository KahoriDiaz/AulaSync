"""Ventana principal de la secretaria (§6).

Menú: Archivo | Inicio | Mantenimiento | Realizar matrícula | Consultas | Ayuda.
Cada sección es un frame con un método ``recargar()``. Todo el acceso a datos
usa servicios (SELECT / CALL sp_...).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.servicios import auth
from app.ui.tema import aplicar_tema, cabecera
from app.ui.secretaria.consultas import Consultas
from app.ui.secretaria.mantenimiento import Mantenimiento
from app.ui.secretaria.panel import PanelRelaciones
from app.ui.secretaria.realizar_matricula import RealizarMatricula


class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        aplicar_tema(self)
        self.sesion_cerrada = False
        self.title("AulaSync - Secretaría")
        self.geometry("1100x680")
        self.minsize(900, 560)
        self._construir_menu()
        sesion = auth.sesion_actual()
        detalle = f"Secretaria: {sesion.nombres} {sesion.apellidos}" if sesion else "Secretaria"
        cabecera(self, "AulaSync", detalle).pack(fill="x")
        self._construir_contenido()
        self.mostrar_pestana("inicio")

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

    # ---------------------------------------------------------------- contenido
    def _construir_contenido(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.pestanas: dict[str, tk.Widget] = {}
        self._agregar("inicio", "Inicio", PanelRelaciones(self.notebook))
        self._agregar("mantenimiento", "Mantenimiento", Mantenimiento(self.notebook))
        self._agregar("matricula", "Realizar matrícula", RealizarMatricula(self.notebook))
        self._agregar("consultas", "Consultas", Consultas(self.notebook))
        self.notebook.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

    def _agregar(self, clave: str, titulo: str, frame: tk.Widget) -> None:
        self.notebook.add(frame, text=titulo)
        self.pestanas[clave] = frame

    def _al_cambiar_pestana(self, _evento=None):
        clave = self._clave_pestana_actual()
        if clave:
            self._recargar(clave)

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
        if frame is None:
            return
        try:
            frame.recargar()
        except Exception as exc:
            messagebox.showerror("Error al cargar los datos", str(exc), parent=self)

    # ---------------------------------------------------------------- acciones generales
    def cerrar_sesion(self):
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
