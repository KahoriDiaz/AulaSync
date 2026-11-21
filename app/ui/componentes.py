"""Componentes de UI reutilizables (tkinter + ttk).

Tabla: Treeview con encabezados clickeables para ordenar y un campo de búsqueda.
BarraExportacion: botones Excel / PDF / CSV para listas y reportes.
"""
from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import errores
from app.servicios import exportar
from app.ui.tema import SUPERFICIE

DIGITOS = re.compile(r"^[0-9]{0,8}$")


def encabezado(columna: str) -> str:
    """Texto legible para una columna: 'ApellidoPaterno' -> 'Apellido Paterno',
    'DNI_Estudiante' -> 'DNI Estudiante', 'AñoEscolar' -> 'Año Escolar'."""
    texto = str(columna).replace("_", " ")
    texto = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", texto)
    return " ".join(texto.split())


def normalizar_dni(texto: object) -> str:
    """Devuelve solo los dígitos del DNI, recortados a 8 caracteres."""
    return re.sub(r"[^0-9]", "", str(texto or ""))[:8]


def entry_dni(parent, textvariable=None, **kwargs) -> ttk.Entry:
    """Entrada que solo permite escribir o pegar hasta 8 dígitos."""
    variable = textvariable if textvariable is not None else tk.StringVar()
    control = ttk.Entry(parent, textvariable=variable, **kwargs)

    def validar(propuesto: str) -> bool:
        return bool(DIGITOS.fullmatch(propuesto))

    control.configure(
        validate="key",
        validatecommand=(control.register(validar), "%P"),
    )
    return control


class Tabla(ttk.Frame):
    """Treeview con scrollbar, orden por columna y filtro de texto."""

    def __init__(self, parent, columnas, anchos=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnas = list(columnas)
        self._orden_asc = {c: True for c in self.columnas}

        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(marco, columns=self.columnas, show="headings")
        self.tree.tag_configure("par", background="#F5F9FC")
        self.tree.tag_configure("impar", background=SUPERFICIE)
        self.tree.tag_configure("atencion", background="#FFF3CD", foreground="#8A5A00")
        self.tree.tag_configure("aprobado", background="#E7F6EF", foreground="#05603F")
        self.tree.tag_configure("pendiente", background="#FFF3CD", foreground="#8A5A00")
        self.tree.tag_configure("rechazado", background="#FDECEC", foreground="#991B1B")
        for col in self.columnas:
            texto = encabezado(col)
            ancho = (anchos or {}).get(col, 100)
            self.tree.heading(col, text=texto, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=ancho, anchor="w")

        scroll = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._filas = []

    def cargar(self, filas):
        """Carga una lista de diccionarios (claves = columnas)."""
        self._filas = list(filas)
        self._mostrar(self._filas)

    def reconfigurar(self, columnas, anchos=None):
        """Cambia las columnas del Treeview y deja la tabla vacía."""
        self.columnas = list(columnas)
        self._orden_asc = {columna: True for columna in self.columnas}
        self._filas = []
        self.tree.configure(columns=self.columnas)
        for columna in self.columnas:
            texto = encabezado(columna)
            ancho = (anchos or {}).get(columna, 100)
            self.tree.heading(
                columna, text=texto, command=lambda c=columna: self._ordenar(c)
            )
            self.tree.column(columna, width=ancho, anchor="w")

    def _mostrar(self, filas):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for numero, fila in enumerate(filas):
            # Los NULL de la base se muestran vacíos, no como "None".
            valores = ["" if fila.get(col) is None else fila.get(col) for col in self.columnas]
            base = "par" if numero % 2 else "impar"
            etiqueta = fila.get("_tag")
            etiquetas = (base, etiqueta) if etiqueta else (base,)
            self.tree.insert("", "end", values=valores, tags=etiquetas)

    def _ordenar(self, col):
        asc = self._orden_asc[col]
        self._filas.sort(key=lambda f: str(f.get(col, "")), reverse=not asc)
        self._orden_asc[col] = not asc
        self._mostrar(self._filas)

    def filtrar(self, texto):
        texto = texto.lower()
        filtradas = [
            f for f in self._filas
            if any(texto in str(f.get(c, "")).lower() for c in self.columnas)
        ]
        self._mostrar(filtradas)

    def seleccion(self):
        item = self.tree.focus()
        if not item:
            return None
        valores = self.tree.item(item, "values")
        return dict(zip(self.columnas, valores))

    def filas(self):
        """Copia de las filas cargadas, para exportar exactamente lo visible."""
        return list(self._filas)


class CampoBusqueda(ttk.Frame):
    def __init__(self, parent, etiqueta="Buscar:", comando=None, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text=etiqueta).pack(side="left", padx=(0, 5))
        self.entrada = ttk.Entry(self)
        self.entrada.pack(side="left", fill="x", expand=True)
        if comando:
            self.entrada.bind("<KeyRelease>", lambda _e: comando(self.entrada.get()))


class BarraExportacion(ttk.Frame):
    """Botones para guardar las filas actuales en Excel, PDF o CSV.

    ``obtener_filas`` y ``obtener_titulo`` son callbacks sin argumentos; así la
    barra siempre exporta exactamente lo que está visible en la pantalla.
    """

    def __init__(self, parent, obtener_filas, obtener_titulo, columnas=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.obtener_filas = obtener_filas
        self.obtener_titulo = obtener_titulo
        self.columnas = columnas
        ttk.Label(self, text="Exportar:").pack(side="left", padx=(0, 4))
        for formato, etiqueta in (("xlsx", "Excel"), ("pdf", "PDF"), ("csv", "CSV")):
            ttk.Button(
                self, text=etiqueta, command=lambda f=formato: self._guardar(f)
            ).pack(side="left", padx=2)

    def _guardar(self, formato: str) -> None:
        filas = list(self.obtener_filas() or [])
        if not filas:
            messagebox.showwarning(
                "Exportar", "No hay filas para exportar.", parent=self
            )
            return
        titulo = str(self.obtener_titulo() or "Reporte")
        nombre = exportar.nombre_archivo(titulo, formato)
        extension = exportar.EXTENSIONES[formato]
        tipos = [(f"{formato.upper()} (*{extension})", f"*{extension}"), ("Todos", "*.*")]
        destino = filedialog.asksaveasfilename(
            parent=self, title=f"Guardar como {formato.upper()}",
            defaultextension=extension, initialfile=nombre, filetypes=tipos,
        )
        if not destino:
            return
        columnas = self.columnas() if callable(self.columnas) else self.columnas
        try:
            ruta = exportar.exportar(
                filas, Path(destino), formato, titulo=titulo, columnas=columnas
            )
        except errores.ErrorApp as exc:
            messagebox.showerror("No se pudo exportar", str(exc), parent=self)
            return
        messagebox.showinfo("Listo", f"Archivo guardado:\n{ruta}", parent=self)


# ------------------------------------------------------------------ íconos
# Ícono de cada botón según el comienzo de su texto (orden: el primero que coincide).
ICONOS_BOTONES: tuple[tuple[str, str], ...] = (
    ("Nuevo", "plus"), ("Nueva matrícula", "plus"), ("Agregar", "plus"),
    ("Editar", "pencil"), ("Reemplazar", "pencil"),
    ("Eliminar", "trash"), ("Quitar", "trash"),
    ("Actualizar", "refresh"), ("Guardar", "save"), ("Cancelar", "x"),
    ("Buscar", "search"), ("Cargar datos registrados", "search"),
    ("Subir", "upload"), ("Continuar", "arrow-right"), ("Mover alumno", "arrow-right"),
    ("Abrir página", "external-link"), ("Copiar", "copy"),
    ("Registrar matrícula", "check-circle"), ("Ejecutar consulta", "play"),
    ("Excel", "download"), ("PDF", "download"), ("CSV", "download"),
    ("Comparar", "chart-column"), ("Realizar matrícula", "user-plus"),
    ("Mantenimiento", "database"), ("Probar conexión", "refresh"),
    ("Crear base de datos", "database"), ("Ingresar", "log-in"), ("Cerrar sesión", "log-out"),
)


def _color_de_icono(estilo: str) -> str:
    from app.ui import tema

    if estilo in ("Primary.TButton", "Danger.TButton", "NavActivo.TButton"):
        return tema.BLANCO
    if estilo in ("Nav.TButton", "Salir.TButton"):
        return tema.LATERAL_TEXTO
    if estilo == "Accent.TButton":
        return tema.LATERAL
    return tema.TEXTO


def poner_iconos(widget: tk.Misc) -> None:
    """Agrega el ícono que corresponde a cada botón ttk de la ventana (recursivo)."""
    from app.ui.iconos import icono

    for hijo in widget.winfo_children():
        if isinstance(hijo, ttk.Button) and not str(hijo.cget("image")):
            texto = str(hijo.cget("text")).strip()
            nombre = next((ico for prefijo, ico in ICONOS_BOTONES if texto.startswith(prefijo)), None)
            if nombre:
                color = _color_de_icono(str(hijo.cget("style")) or "TButton")
                hijo.configure(image=icono(hijo, nombre, 16, color), compound="left",
                               text=f"  {texto}")
        poner_iconos(hijo)
