"""Tema visual compartido por todas las ventanas de AulaSync.

Se usa únicamente ``tkinter``/``ttk``: paleta cálida, tarjetas suaves, botones
con jerarquía y tablas más legibles. No incluye imágenes ni elementos de marca.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONDO = "#F7F6F2"
SUPERFICIE = "#FFFFFF"
PRIMARIO = "#2F6F6A"
PRIMARIO_OSCURO = "#245651"
ACENTO = "#E0A458"
TEXTO = "#23303A"
TEXTO_SUAVE = "#66737E"
BORDE = "#E3E0D8"
EXITO = "#3D8A5A"
ALERTA = "#C9821A"
PELIGRO = "#B3544A"
INFO = "#3B6EA8"
BLANCO = "#FFFFFF"

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
                     borderwidth=1, padding=12)
    estilo.configure("SobreTarjeta.TFrame", background=SUPERFICIE)
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
    estilo.configure("OnDarkMuted.TLabel", background=PRIMARIO, foreground="#D7E7E4",
                     font=FUENTE_SUAVE)

    estilo.configure("TButton", font=FUENTE_BOTON, background=SUPERFICIE,
                     foreground=TEXTO, borderwidth=1, relief="flat", padding=(10, 6))
    estilo.map("TButton", background=[("active", "#F0EEE7"), ("disabled", "#ECEAE2")],
               foreground=[("disabled", TEXTO_SUAVE)])
    estilo.configure("Primary.TButton", background=PRIMARIO, foreground=BLANCO,
                     borderwidth=0, padding=(14, 8))
    estilo.map("Primary.TButton", background=[("active", PRIMARIO_OSCURO),
                                              ("disabled", "#B9C9C6")],
               foreground=[("disabled", "#EFF3F2")])
    estilo.configure("Accent.TButton", background=ACENTO, foreground="#2B2115",
                     borderwidth=0, padding=(14, 8))
    estilo.map("Accent.TButton", background=[("active", "#CE943F"),
                                             ("disabled", "#EDE2D0")])
    estilo.configure("Danger.TButton", background=PELIGRO, foreground=BLANCO,
                     borderwidth=0, padding=(10, 6))

    for nombre in ("TEntry", "TCombobox"):
        estilo.configure(nombre, fieldbackground=SUPERFICIE, foreground=TEXTO,
                         bordercolor=BORDE, lightcolor=SUPERFICIE, darkcolor=BORDE,
                         padding=6, insertcolor=TEXTO)
    estilo.map("TCombobox", fieldbackground=[("readonly", "#F2F1EC")])

    estilo.configure("Treeview", background=SUPERFICIE, fieldbackground=SUPERFICIE,
                     foreground=TEXTO, rowheight=30, bordercolor=BORDE)
    estilo.map("Treeview", background=[("selected", PRIMARIO)],
               foreground=[("selected", BLANCO)])
    estilo.configure("Treeview.Heading", background="#ECEAE2",
                     foreground=PRIMARIO_OSCURO, font=FUENTE_BOTON,
                     relief="flat", padding=(6, 8))
    estilo.map("Treeview.Heading", background=[("active", "#DEDCD3")])

    estilo.configure("TNotebook", background=FONDO, borderwidth=0,
                     tabmargins=(4, 8, 4, 0))
    estilo.configure("TNotebook.Tab", background="#ECEAE2", foreground=TEXTO_SUAVE,
                     font=FUENTE_BOTON, padding=(14, 8), borderwidth=0)
    estilo.map("TNotebook.Tab",
               background=[("selected", SUPERFICIE), ("active", "#DEDCD3")],
               foreground=[("selected", PRIMARIO_OSCURO)])

    estilo.configure("TLabelframe", background=FONDO, bordercolor=BORDE,
                     relief="solid", borderwidth=1, padding=10)
    estilo.configure("TLabelframe.Label", background=FONDO,
                     foreground=PRIMARIO_OSCURO, font=FUENTE_SECCION)
    estilo.configure("TRadiobutton", background=FONDO, foreground=TEXTO,
                     focuscolor=FONDO)
    estilo.configure("TCheckbutton", background=FONDO, foreground=TEXTO,
                     focuscolor=FONDO)
    estilo.configure("TScrollbar", background="#DAD7CE", troughcolor=FONDO,
                     borderwidth=0, arrowcolor=TEXTO_SUAVE)
    estilo.configure("TSeparator", background=BORDE)
    estilo.configure("Horizontal.TProgressbar", background=PRIMARIO,
                     troughcolor="#E6E3DA", borderwidth=0)
    return estilo


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
