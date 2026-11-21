"""Selector de fecha con tres listas (día, mes, año) para tkinter.

Uso::

    selector = SelectorFecha(parent, anio_min=1990)
    selector.establecer("2015-05-10")      # date, datetime o texto AAAA-MM-DD
    if selector.validar():                 # False si falta un dato o la fecha no existe
        valor = selector.obtener()         # "AAAA-MM-DD"
    else:
        print(selector.mensaje_error)
"""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
    "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


class SelectorFecha(ttk.Frame):
    def __init__(self, parent, anio_min: int = 1900, anio_max: int | None = None,
                 permitir_futuro: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        self.anio_min = int(anio_min)
        self.anio_max = int(anio_max if anio_max is not None else date.today().year)
        self.permitir_futuro = permitir_futuro
        self.mensaje_error = ""

        self.var_dia = tk.StringVar()
        self.var_mes = tk.StringVar()
        self.var_anio = tk.StringVar()

        self.cmb_dia = ttk.Combobox(self, textvariable=self.var_dia, width=4, state="readonly",
                                    values=[f"{d:02d}" for d in range(1, 32)])
        self.cmb_mes = ttk.Combobox(self, textvariable=self.var_mes, width=11, state="readonly",
                                    values=list(MESES))
        self.cmb_anio = ttk.Combobox(self, textvariable=self.var_anio, width=6, state="readonly",
                                     values=[str(a) for a in range(self.anio_max, self.anio_min - 1, -1)])
        self.cmb_dia.pack(side="left")
        ttk.Label(self, text="/").pack(side="left", padx=2)
        self.cmb_mes.pack(side="left")
        ttk.Label(self, text="/").pack(side="left", padx=2)
        self.cmb_anio.pack(side="left")
        self.cmb_mes.bind("<<ComboboxSelected>>", lambda _e: self._ajustar_dias())
        self.cmb_anio.bind("<<ComboboxSelected>>", lambda _e: self._ajustar_dias())

    def _ajustar_dias(self) -> None:
        """Limita los días al mes elegido (p. ej. 29 de febrero solo en bisiesto)."""
        if not self.var_mes.get() or not self.var_anio.get():
            return
        mes = MESES.index(self.var_mes.get()) + 1
        dias = calendar.monthrange(int(self.var_anio.get()), mes)[1]
        self.cmb_dia.configure(values=[f"{d:02d}" for d in range(1, dias + 1)])
        if self.var_dia.get() and int(self.var_dia.get()) > dias:
            self.var_dia.set(f"{dias:02d}")

    def establecer(self, valor) -> None:
        """Muestra una fecha (date, datetime o texto AAAA-MM-DD); vacío limpia."""
        if isinstance(valor, datetime):
            valor = valor.date()
        if isinstance(valor, str):
            texto = valor.strip()[:10]
            try:
                valor = date.fromisoformat(texto) if texto else None
            except ValueError:
                valor = None
        if not isinstance(valor, date):
            self.limpiar()
            return
        if valor.year < self.anio_min or valor.year > self.anio_max:
            # Se amplía el rango para no perder un dato ya guardado en la base.
            self.anio_min = min(self.anio_min, valor.year)
            self.anio_max = max(self.anio_max, valor.year)
            self.cmb_anio.configure(
                values=[str(a) for a in range(self.anio_max, self.anio_min - 1, -1)]
            )
        self.var_anio.set(str(valor.year))
        self.var_mes.set(MESES[valor.month - 1])
        self.var_dia.set(f"{valor.day:02d}")
        self._ajustar_dias()

    def limpiar(self) -> None:
        self.var_dia.set("")
        self.var_mes.set("")
        self.var_anio.set("")

    def fecha(self) -> date | None:
        """La fecha elegida como ``date`` o None si está incompleta o no existe."""
        if not (self.var_dia.get() and self.var_mes.get() and self.var_anio.get()):
            return None
        try:
            return date(int(self.var_anio.get()), MESES.index(self.var_mes.get()) + 1,
                        int(self.var_dia.get()))
        except ValueError:
            return None

    def validar(self) -> bool:
        """True si hay una fecha completa, válida, dentro del rango y no futura."""
        valor = self.fecha()
        if valor is None:
            self.mensaje_error = "Seleccione el día, el mes y el año."
            return False
        if not self.anio_min <= valor.year <= self.anio_max:
            self.mensaje_error = f"El año debe estar entre {self.anio_min} y {self.anio_max}."
            return False
        if not self.permitir_futuro and valor > date.today():
            self.mensaje_error = "La fecha no puede ser posterior a hoy."
            return False
        self.mensaje_error = ""
        return True

    def obtener(self) -> str:
        """Fecha en formato AAAA-MM-DD ("" si está incompleta)."""
        valor = self.fecha()
        return valor.isoformat() if valor else ""

    def configure_estado(self, estado: str) -> None:
        """'readonly' para editar o 'disabled' para bloquear las tres listas."""
        for combo in (self.cmb_dia, self.cmb_mes, self.cmb_anio):
            combo.configure(state=estado)
