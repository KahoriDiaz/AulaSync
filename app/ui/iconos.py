"""Íconos de línea para la interfaz (sin emojis ni símbolos unicode).

Se dibujan con Pillow a partir de su geometría en una cuadrícula de 24x24 y
trazo de 2 px, al estilo del set Lucide (licencia ISC, https://lucide.dev).
Se renderizan a 4 veces el tamaño y se reducen para obtener bordes suaves.

Uso::

    boton = ttk.Button(padre, text="Nuevo", image=icono(padre, "plus", color=BLANCO),
                       compound="left")
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from PIL import Image, ImageDraw, ImageTk

ESCALA = 4
Dibujo = Callable[["Lienzo"], None]


class Lienzo:
    """Primitivas sobre la cuadrícula de 24x24 con trazo redondeado."""

    def __init__(self, tamano: int, color: str, grosor: float = 2.0):
        self.lado = tamano * ESCALA
        self.factor = self.lado / 24
        self.color = color
        self.ancho = max(1, round(grosor * self.factor))
        self.imagen = Image.new("RGBA", (self.lado, self.lado), (0, 0, 0, 0))
        self.dibujo = ImageDraw.Draw(self.imagen)

    def _p(self, x: float, y: float) -> tuple[float, float]:
        return x * self.factor, y * self.factor

    def _punta(self, x: float, y: float) -> None:
        cx, cy = self._p(x, y)
        r = self.ancho / 2
        self.dibujo.ellipse((cx - r, cy - r, cx + r, cy + r), fill=self.color)

    def linea(self, *puntos: float) -> None:
        """Polilínea: linea(x1, y1, x2, y2, ...), con uniones y puntas redondas."""
        pares = [self._p(puntos[i], puntos[i + 1]) for i in range(0, len(puntos), 2)]
        self.dibujo.line(pares, fill=self.color, width=self.ancho, joint="curve")
        for i in range(0, len(puntos), 2):
            self._punta(puntos[i], puntos[i + 1])

    def circulo(self, cx: float, cy: float, r: float, relleno: bool = False) -> None:
        x0, y0 = self._p(cx - r, cy - r)
        x1, y1 = self._p(cx + r, cy + r)
        if relleno:
            self.dibujo.ellipse((x0, y0, x1, y1), fill=self.color)
        else:
            self.dibujo.ellipse((x0, y0, x1, y1), outline=self.color, width=self.ancho)

    def arco(self, x0: float, y0: float, x1: float, y1: float, inicio: float, fin: float) -> None:
        """Arco de la elipse inscrita en el rectángulo; ángulos en grados, horario desde las 3."""
        self.dibujo.arc((*self._p(x0, y0), *self._p(x1, y1)), inicio, fin,
                        fill=self.color, width=self.ancho)

    def rect(self, x: float, y: float, ancho: float, alto: float, radio: float = 2) -> None:
        self.dibujo.rounded_rectangle(
            (*self._p(x, y), *self._p(x + ancho, y + alto)),
            radius=radio * self.factor, outline=self.color, width=self.ancho,
        )


def _persona(c: Lienzo, cx: float, base: float = 21, cabeza: float = 7) -> None:
    """Cabeza y hombros (usado por user, user-plus y users)."""
    c.circulo(cx, cabeza, 4)
    c.linea(cx - 7, base, cx - 7, base - 2)
    c.arco(cx - 7, base - 6, cx + 1, base + 2, 180, 270)
    c.linea(cx - 3, base - 6, cx + 3, base - 6)
    c.arco(cx - 1, base - 6, cx + 7, base + 2, 270, 360)
    c.linea(cx + 7, base - 2, cx + 7, base)


ICONOS: dict[str, Dibujo] = {
    "house": lambda c: (c.linea(3, 10, 12, 3, 21, 10, 21, 21, 3, 21, 3, 10),
                        c.linea(9, 21, 9, 13, 15, 13, 15, 21)),
    "database": lambda c: (c.arco(3, 2, 21, 8, 0, 360),
                           c.linea(3, 5, 3, 19), c.linea(21, 5, 21, 19),
                           c.arco(3, 9, 21, 15, 0, 180), c.arco(3, 16, 21, 22, 0, 180)),
    "user-plus": lambda c: (_persona(c, 9), c.linea(19, 8, 19, 14), c.linea(16, 11, 22, 11)),
    "user": lambda c: _persona(c, 12),
    "users": lambda c: (_persona(c, 9), c.arco(13, 3, 21, 11, 270, 450),
                        c.linea(22, 21, 22, 19), c.arco(16, 15, 24, 23, 300, 360)),
    "chart-column": lambda c: (c.linea(3, 3, 3, 21, 21, 21), c.linea(8, 17, 8, 14),
                               c.linea(13, 17, 13, 5), c.linea(18, 17, 18, 9)),
    "log-out": lambda c: (c.linea(9, 21, 5, 21), c.arco(3, 17, 7, 21, 90, 180),
                          c.linea(3, 19, 3, 5), c.arco(3, 3, 7, 7, 180, 270), c.linea(5, 3, 9, 3),
                          c.linea(16, 17, 21, 12, 16, 7), c.linea(21, 12, 9, 12)),
    "log-in": lambda c: (c.linea(15, 3, 19, 3), c.arco(17, 3, 21, 7, 270, 360),
                         c.linea(21, 5, 21, 19), c.arco(17, 17, 21, 21, 0, 90), c.linea(19, 21, 15, 21),
                         c.linea(10, 17, 15, 12, 10, 7), c.linea(15, 12, 3, 12)),
    "refresh": lambda c: (c.arco(3, 3, 21, 21, 200, 340), c.linea(21, 3, 21, 8, 16, 8),
                          c.arco(3, 3, 21, 21, 20, 160), c.linea(3, 21, 3, 16, 8, 16)),
    "plus": lambda c: (c.linea(12, 5, 12, 19), c.linea(5, 12, 19, 12)),
    "pencil": lambda c: (c.linea(17, 3, 21, 7, 8, 20, 3, 21, 4, 16, 17, 3),
                         c.linea(15, 5, 19, 9)),
    "trash": lambda c: (c.linea(3, 6, 21, 6), c.linea(19, 6, 18, 20, 16, 21, 8, 21, 6, 20, 5, 6),
                        c.linea(8, 6, 8, 4, 10, 2, 14, 2, 16, 4, 16, 6),
                        c.linea(10, 11, 10, 17), c.linea(14, 11, 14, 17)),
    "search": lambda c: (c.circulo(11, 11, 8), c.linea(21, 21, 16.65, 16.65)),
    "upload": lambda c: (c.linea(3, 15, 3, 19, 5, 21, 19, 21, 21, 19, 21, 15),
                         c.linea(17, 8, 12, 3, 7, 8), c.linea(12, 3, 12, 15)),
    "external-link": lambda c: (c.linea(15, 3, 21, 3, 21, 9), c.linea(10, 14, 21, 3),
                                c.linea(18, 13, 18, 19, 16, 21, 5, 21, 3, 19, 3, 8, 5, 6, 11, 6)),
    "copy": lambda c: (c.rect(8, 8, 14, 14), c.linea(4, 16, 2, 14, 2, 4, 4, 2, 14, 2, 16, 4)),
    "save": lambda c: (c.linea(5, 3, 16, 3, 21, 8, 21, 19, 19, 21, 5, 21, 3, 19, 3, 5, 5, 3),
                       c.linea(17, 21, 17, 13, 7, 13, 7, 21), c.linea(7, 3, 7, 8, 15, 8)),
    "check-circle": lambda c: (c.circulo(12, 12, 10), c.linea(9, 12, 11, 14, 15, 10)),
    "lock": lambda c: (c.rect(3, 11, 18, 11), c.linea(7, 11, 7, 7), c.linea(17, 11, 17, 7),
                       c.arco(7, 2, 17, 12, 180, 360)),
    "id-card": lambda c: (c.rect(2, 5, 20, 14), c.circulo(8, 11, 2),
                          c.linea(15, 10, 19, 10), c.linea(15, 14, 18, 14), c.linea(5, 16, 11, 16)),
    "graduation-cap": lambda c: (c.linea(2, 10, 12, 5, 22, 10, 12, 15, 2, 10),
                                 c.linea(6, 12, 6, 16, 9, 18, 15, 18, 18, 16, 18, 12),
                                 c.linea(22, 10, 22, 16)),
    "layout-grid": lambda c: (c.rect(3, 3, 7, 7, 1), c.rect(14, 3, 7, 7, 1),
                              c.rect(14, 14, 7, 7, 1), c.rect(3, 14, 7, 7, 1)),
    "file-text": lambda c: (c.linea(14, 2, 6, 2, 4, 4, 4, 20, 6, 22, 18, 22, 20, 20, 20, 8, 14, 2),
                            c.linea(14, 2, 14, 8, 20, 8), c.linea(8, 13, 16, 13), c.linea(8, 17, 16, 17)),
    "arrow-right": lambda c: (c.linea(5, 12, 19, 12), c.linea(12, 5, 19, 12, 12, 19)),
    "download": lambda c: (c.linea(3, 15, 3, 19, 5, 21, 19, 21, 21, 19, 21, 15),
                           c.linea(7, 10, 12, 15, 17, 10), c.linea(12, 15, 12, 3)),
    "play": lambda c: c.linea(6, 3, 20, 12, 6, 21, 6, 3),
    "x": lambda c: (c.linea(18, 6, 6, 18), c.linea(6, 6, 18, 18)),
    "help-circle": lambda c: (c.circulo(12, 12, 10), c.arco(9, 6, 15, 12, 180, 30),
                              c.linea(14.6, 10.5, 12, 12.5, 12, 13.5), c.circulo(12, 17, 0.6, relleno=True)),
}


def imagen(nombre: str, tamano: int = 18, color: str = "#1E293B") -> Image.Image:
    """Imagen RGBA del ícono (útil para pruebas o para exportar)."""
    if nombre not in ICONOS:
        raise KeyError(f"Ícono desconocido: {nombre}")
    lienzo = Lienzo(tamano, color)
    ICONOS[nombre](lienzo)
    return lienzo.imagen.resize((tamano, tamano), Image.LANCZOS)


def icono(widget: tk.Misc, nombre: str, tamano: int = 18, color: str = "#1E293B") -> ImageTk.PhotoImage:
    """Ícono listo para ``image=`` de tkinter, guardado en caché por ventana raíz."""
    raiz = widget._root()
    cache = raiz.__dict__.setdefault("_iconos_aulasync", {})
    clave = (nombre, tamano, color)
    if clave not in cache:
        cache[clave] = ImageTk.PhotoImage(imagen(nombre, tamano, color), master=raiz)
    return cache[clave]
