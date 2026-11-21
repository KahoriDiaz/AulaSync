"""Tema visual compartido por todas las ventanas de AulaSync.

Se usa únicamente ``tkinter``/``ttk``: paleta fría en celestes, tarjetas suaves, botones
con jerarquía y tablas más legibles. No incluye imágenes ni elementos de marca.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONDO = "#F3F7FB"
SUPERFICIE = "#FFFFFF"
PRIMARIO = "#0284C7"
PRIMARIO_OSCURO = "#075985"
ACENTO = "#38BDF8"
TEXTO = "#1E293B"
TEXTO_SUAVE = "#64748B"
BORDE = "#E2E8F0"
EXITO = "#059669"
ALERTA = "#D97706"
PELIGRO = "#DC2626"
INFO = "#4F46E5"
BLANCO = "#FFFFFF"
LATERAL = "#0B2540"
LATERAL_HOVER = "#133A5E"
LATERAL_TEXTO = "#B9D7EE"
FONDO_SUAVE = "#EAF2F9"

FUENTE = ("Segoe UI", 10)
FUENTE_BOTON = ("Segoe UI", 10, "bold")
FUENTE_TITULO = ("Segoe UI", 18, "bold")
FUENTE_SECCION = ("Segoe UI", 11, "bold")
FUENTE_SUAVE = ("Segoe UI", 9)


def aplicar_tema(ventana: tk.Misc) -> ttk.Style:
    """Configura el estilo global y el fondo de una ventana raíz o diálogo."""
    estilo = ttk.Style(ventana)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    try:
        ventana.configure(bg=FONDO)
    except (tk.TclError, AttributeError):
        pass

    estilo.configure(".", background=FONDO, foreground=TEXTO, font=FUENTE,
                     fieldbackground=SUPERFICIE, insertcolor=TEXTO)
    estilo.configure("TFrame", background=FONDO)
    estilo.configure("Card.TFrame", background=SUPERFICIE, relief="solid",
                     borderwidth=1, padding=12, bordercolor=BORDE,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE)
    estilo.configure("SobreTarjeta.TFrame", background=SUPERFICIE)
    estilo.configure("Lateral.TFrame", background=LATERAL)
    estilo.configure("Lateral.TLabel", background=LATERAL, foreground=BLANCO,
                     font=("Segoe UI", 17, "bold"))
    estilo.configure("LateralSuave.TLabel", background=LATERAL, foreground=LATERAL_TEXTO,
                     font=FUENTE_SUAVE)
    estilo.configure("LateralUsuario.TLabel", background=LATERAL, foreground=BLANCO,
                     font=FUENTE_BOTON)
    estilo.configure("Nav.TButton", background=LATERAL, foreground=LATERAL_TEXTO,
                     font=("Segoe UI", 10, "bold"), anchor="w", borderwidth=0,
                     relief="flat", padding=(18, 11), focuscolor=LATERAL)
    estilo.map("Nav.TButton", background=[("active", LATERAL_HOVER)],
               foreground=[("active", BLANCO)])
    estilo.configure("NavActivo.TButton", background=PRIMARIO, foreground=BLANCO,
                     font=("Segoe UI", 10, "bold"), anchor="w", borderwidth=0,
                     relief="flat", padding=(18, 11), focuscolor=PRIMARIO)
    estilo.map("NavActivo.TButton", background=[("active", PRIMARIO)])
    estilo.configure("Salir.TButton", background=LATERAL, foreground=LATERAL_TEXTO,
                     borderwidth=1, bordercolor="#24507A", lightcolor=LATERAL,
                     darkcolor=LATERAL, relief="solid", padding=(12, 7), focuscolor=LATERAL)
    estilo.map("Salir.TButton", background=[("active", LATERAL_HOVER)],
               foreground=[("active", BLANCO)])
    # Notebook sin pestañas visibles: la navegación la hace la barra lateral.
    estilo.layout("SinPestanas.TNotebook.Tab", [])
    estilo.configure("SinPestanas.TNotebook", background=FONDO, borderwidth=0,
                     tabmargins=0, bordercolor=FONDO, lightcolor=FONDO, darkcolor=FONDO)
    # Lista vertical de sub-secciones (por ejemplo, las tablas del mantenimiento).
    estilo.configure("SubNav.TButton", background=FONDO, foreground=TEXTO_SUAVE,
                     font=FUENTE, anchor="w", borderwidth=0, relief="flat",
                     padding=(12, 7), focuscolor=FONDO)
    estilo.map("SubNav.TButton", background=[("active", FONDO_SUAVE)],
               foreground=[("active", TEXTO)])
    estilo.configure("SubNavActivo.TButton", background=SUPERFICIE, foreground=PRIMARIO_OSCURO,
                     font=FUENTE_BOTON, anchor="w", borderwidth=1, relief="solid",
                     bordercolor=BORDE, lightcolor=SUPERFICIE, darkcolor=SUPERFICIE,
                     padding=(12, 7), focuscolor=SUPERFICIE)
    estilo.map("SubNavActivo.TButton", background=[("active", SUPERFICIE)])
    estilo.configure("Pagina.TLabel", background=FONDO, foreground=TEXTO,
                     font=("Segoe UI", 20, "bold"))
    estilo.configure("PaginaSuave.TLabel", background=FONDO, foreground=TEXTO_SUAVE,
                     font=FUENTE)
    estilo.configure("Dato.TLabel", background=SUPERFICIE, foreground=PRIMARIO_OSCURO,
                     font=("Segoe UI", 24, "bold"))
    estilo.configure("Header.TFrame", background=PRIMARIO, padding=(18, 14))
    estilo.configure("Barra.TFrame", background=SUPERFICIE, padding=(8, 6))

    estilo.configure("TLabel", background=FONDO, foreground=TEXTO, font=FUENTE)
    estilo.configure("Card.TLabel", background=SUPERFICIE)
    estilo.configure("Muted.TLabel", background=FONDO, foreground=TEXTO_SUAVE,
                     font=FUENTE_SUAVE)
    estilo.configure("Titulo.TLabel", background=FONDO, foreground=PRIMARIO_OSCURO,
                     font=FUENTE_TITULO)
    estilo.configure("Seccion.TLabel", background=FONDO, foreground=PRIMARIO_OSCURO,
                     font=FUENTE_SECCION)
    estilo.configure("Card.Titulo.TLabel", background=SUPERFICIE,
                     foreground=PRIMARIO_OSCURO, font=FUENTE_TITULO)
    estilo.configure("Card.Seccion.TLabel", background=SUPERFICIE,
                     foreground=PRIMARIO_OSCURO, font=FUENTE_SECCION)
    estilo.configure("Card.Muted.TLabel", background=SUPERFICIE,
                     foreground=TEXTO_SUAVE, font=FUENTE_SUAVE)
    estilo.configure("OnDark.TLabel", background=PRIMARIO, foreground=BLANCO,
                     font=FUENTE_TITULO)
    estilo.configure("OnDarkMuted.TLabel", background=PRIMARIO, foreground="#CFE8F7",
                     font=FUENTE_SUAVE)

    estilo.configure("TButton", font=FUENTE_BOTON, background=FONDO_SUAVE,
                     foreground=TEXTO, borderwidth=1, relief="solid", padding=(12, 7),
                     bordercolor="#CBD5E1", lightcolor=FONDO_SUAVE, darkcolor=FONDO_SUAVE,
                     focuscolor=FONDO_SUAVE)
    estilo.map("TButton", background=[("active", "#DCEAF5"), ("disabled", "#EEF2F6")],
               foreground=[("disabled", TEXTO_SUAVE)])
    estilo.configure("Primary.TButton", background=PRIMARIO, foreground=BLANCO,
                     borderwidth=0, padding=(14, 8))
    estilo.map("Primary.TButton", background=[("active", PRIMARIO_OSCURO),
                                              ("disabled", "#A5CDE6")],
               foreground=[("disabled", "#F0F7FC")])
    estilo.configure("Accent.TButton", background=ACENTO, foreground="#0B2540",
                     borderwidth=0, padding=(14, 8))
    estilo.map("Accent.TButton", background=[("active", "#7DD3FC"),
                                             ("disabled", "#E0F2FE")])
    estilo.configure("Danger.TButton", background=PELIGRO, foreground=BLANCO,
                     borderwidth=0, padding=(10, 6))

    for nombre in ("TEntry", "TCombobox", "TSpinbox"):
        estilo.configure(nombre, fieldbackground=SUPERFICIE, foreground=TEXTO,
                         bordercolor="#CBD5E1", lightcolor=SUPERFICIE, darkcolor=SUPERFICIE,
                         padding=7, insertcolor=TEXTO, arrowcolor=TEXTO_SUAVE)
        # Borde del color principal mientras el campo tiene el foco.
        estilo.map(nombre, bordercolor=[("focus", PRIMARIO)],
                   lightcolor=[("focus", PRIMARIO)], darkcolor=[("focus", PRIMARIO)])
    estilo.map("TCombobox", fieldbackground=[("readonly", SUPERFICIE), ("disabled", "#F1F5F9")],
               bordercolor=[("focus", PRIMARIO)])
    estilo.map("TEntry", fieldbackground=[("readonly", "#F1F5F9")])

    estilo.configure("Treeview", background=SUPERFICIE, fieldbackground=SUPERFICIE,
                     foreground=TEXTO, rowheight=30, bordercolor=BORDE)
    estilo.map("Treeview", background=[("selected", PRIMARIO)],
               foreground=[("selected", BLANCO)])
    estilo.configure("Treeview.Heading", background="#EEF2F6",
                     foreground=PRIMARIO_OSCURO, font=FUENTE_BOTON,
                     relief="flat", padding=(6, 8))
    estilo.map("Treeview.Heading", background=[("active", "#DCEAF5")])

    estilo.configure("TNotebook", background=FONDO, borderwidth=1,
                     tabmargins=(0, 4, 0, 0), bordercolor=BORDE,
                     lightcolor=SUPERFICIE, darkcolor=BORDE)
    estilo.configure("TNotebook.Tab", background=FONDO, foreground=TEXTO_SUAVE,
                     font=FUENTE_BOTON, padding=(14, 8), borderwidth=0,
                     bordercolor=BORDE, lightcolor=FONDO)
    estilo.map("TNotebook.Tab",
               background=[("selected", SUPERFICIE), ("active", FONDO_SUAVE)],
               foreground=[("selected", PRIMARIO_OSCURO)],
               lightcolor=[("selected", PRIMARIO)])

    estilo.configure("TLabelframe", background=FONDO, bordercolor=BORDE,
                     lightcolor=FONDO, darkcolor=FONDO,
                     relief="solid", borderwidth=1, padding=10)
    estilo.configure("TLabelframe.Label", background=FONDO,
                     foreground=PRIMARIO_OSCURO, font=FUENTE_SECCION)
    estilo.configure("TRadiobutton", background=FONDO, foreground=TEXTO,
                     focuscolor=FONDO)
    estilo.configure("TCheckbutton", background=FONDO, foreground=TEXTO,
                     focuscolor=FONDO)
    estilo.configure("TScrollbar", background="#CBD5E1", troughcolor=FONDO,
                     borderwidth=0, arrowcolor=TEXTO_SUAVE)
    estilo.configure("TSeparator", background=BORDE)
    estilo.configure("Horizontal.TProgressbar", background=PRIMARIO,
                     troughcolor="#E2EAF2", borderwidth=0)
    return estilo


def centrar(ventana: tk.Misc, ancho: int, alto: int) -> None:
    """Ubica la ventana en el centro de la pantalla con el tamaño indicado."""
    ventana.update_idletasks()
    x = max(0, (ventana.winfo_screenwidth() - ancho) // 2)
    y = max(0, (ventana.winfo_screenheight() - alto) // 3)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


class PantallaCarga(tk.Toplevel):
    """Ventana de carga con barra de avance, para que el usuario sepa que la
    aplicación sigue trabajando (por ejemplo, tras iniciar sesión)."""

    def __init__(self, parent: tk.Misc, mensaje: str = "Cargando...", pasos: int = 0):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync")
        self.overrideredirect(True)
        self.configure(bg=LATERAL)
        borde = tk.Frame(self, bg=LATERAL, padx=1, pady=1)
        borde.pack(fill="both", expand=True)
        cuerpo = tk.Frame(borde, bg=SUPERFICIE, padx=32, pady=26)
        cuerpo.pack(fill="both", expand=True)
        tk.Label(cuerpo, text="AulaSync", bg=SUPERFICIE, fg=PRIMARIO_OSCURO,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(cuerpo, text="Sistema de matrícula escolar", bg=SUPERFICIE,
                 fg=TEXTO_SUAVE, font=FUENTE_SUAVE).pack(anchor="w")
        self.var_mensaje = tk.StringVar(value=mensaje)
        tk.Label(cuerpo, textvariable=self.var_mensaje, bg=SUPERFICIE, fg=TEXTO,
                 font=FUENTE, anchor="w").pack(fill="x", pady=(22, 8))
        self.pasos = pasos
        self.barra = ttk.Progressbar(
            cuerpo, length=340, maximum=max(pasos, 1),
            mode="determinate" if pasos else "indeterminate",
        )
        self.barra.pack(fill="x")
        if not pasos:
            self.barra.start(12)
        centrar(self, 420, 190)
        self.attributes("-topmost", True)
        self.update()

    def avanzar(self, mensaje: str) -> None:
        """Muestra el paso actual y lo refleja en la barra."""
        self.var_mensaje.set(mensaje)
        if self.pasos:
            self.barra.step(1)
        self.update()


def tarjeta(parent, **kwargs) -> ttk.Frame:
    """Devuelve un marco con apariencia de tarjeta."""
    return ttk.Frame(parent, style="Card.TFrame", **kwargs)


def cabecera(parent, titulo: str, detalle: str | None = None) -> ttk.Frame:
    """Franja superior de una ventana con título y contexto opcional."""
    marco = ttk.Frame(parent, style="Header.TFrame")
    ttk.Label(marco, text=titulo, style="OnDark.TLabel").pack(anchor="w")
    if detalle:
        ttk.Label(marco, text=detalle, style="OnDarkMuted.TLabel").pack(anchor="w", pady=(2, 0))
    return marco


def separador(parent, **kwargs) -> ttk.Separator:
    """Línea fina para agrupar secciones."""
    return ttk.Separator(parent, orient="horizontal", **kwargs)
