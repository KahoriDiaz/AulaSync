"""Reportes del sistema (anexo de consultas)."""
from __future__ import annotations

import csv
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.db import consultar
from core.errores import ErrorApp
from core.formatos import NIVELES, grados_de_nivel
from ui.comunes.widgets import Tabla, boton, mostrar_error, mostrar_info


def _anio() -> QSpinBox:
    control = QSpinBox()
    control.setRange(2000, 2100)
    control.setValue(2026)
    return control


def _dni() -> QLineEdit:
    control = QLineEdit()
    control.setMaxLength(8)
    control.setPlaceholderText("DNI")
    return control


def _texto(marcador: str = "") -> QLineEdit:
    control = QLineEdit()
    control.setPlaceholderText(marcador)
    return control


def _nivel() -> QComboBox:
    control = QComboBox()
    control.addItems(NIVELES)
    return control


def _grado() -> QComboBox:
    control = QComboBox()
    control.addItems(grados_de_nivel("Inicial"))
    return control


REPORTES: list[dict[str, Any]] = [
    {
        "nombre": "1. Matriculados por año, nivel, grado y sección",
        "controles": {"año": _anio, "nivel": _nivel, "grado": _grado, "sección": _texto},
        "sql": lambda p: (
            "SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres, m.AñoEscolar, "
            "m.Nivel, m.Grado, m.Seccion, m.Estado FROM MATRICULA m "
            "INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI "
            "WHERE m.AñoEscolar = %s AND m.Nivel = %s AND m.Grado = %s AND m.Seccion = %s "
            "AND m.Estado = 'Matriculado' ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres",
            (p["año"], p["nivel"], p["grado"], p["sección"].strip().upper()),
        ),
    },
    {
        "nombre": "2. Buscar estudiante por apellidos y nombres",
        "controles": {"apellido paterno": _texto, "apellido materno": _texto, "nombres": _texto},
        "sql": lambda p: (
            "SELECT DNI, ApellidoPaterno, ApellidoMaterno, Nombres, FechaNacimiento, Celular "
            "FROM ESTUDIANTE WHERE ApellidoPaterno LIKE CONCAT(%s, '%') "
            "AND ApellidoMaterno LIKE CONCAT(%s, '%') AND Nombres LIKE CONCAT(%s, '%') "
            "ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres",
            (p["apellido paterno"], p["apellido materno"], p["nombres"]),
        ),
    },
    {
        "nombre": "3. Constancias de un estudiante por nivel",
        "controles": {"dni": _dni, "nivel": _nivel},
        "sql": lambda p: (
            "SELECT c.CodigoVirtual, c.DNI_Estudiante, c.NivelEducativo, c.FechaHoraEmision, "
            "CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante "
            "FROM CONSTANCIA_LOGROS c INNER JOIN ESTUDIANTE e ON c.DNI_Estudiante = e.DNI "
            "WHERE c.DNI_Estudiante = %s AND c.NivelEducativo = %s",
            (p["dni"], p["nivel"]),
        ),
    },
    {
        "nombre": "4. Hermanos de un estudiante",
        "controles": {"dni": _dni},
        "sql": lambda p: (
            "SELECT h.DNI_HermanoB AS DNI_Hermano, CONCAT(e.ApellidoPaterno, ' ', "
            "e.ApellidoMaterno, ', ', e.Nombres) AS Hermano FROM HERMANDAD h "
            "INNER JOIN ESTUDIANTE e ON h.DNI_HermanoB = e.DNI WHERE h.DNI_HermanoA = %s "
            "UNION SELECT h.DNI_HermanoA, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, "
            "', ', e.Nombres) FROM HERMANDAD h INNER JOIN ESTUDIANTE e ON h.DNI_HermanoA = e.DNI "
            "WHERE h.DNI_HermanoB = %s",
            (p["dni"], p["dni"]),
        ),
    },
    {
        "nombre": "5. Padrón de matriculados por año, nivel y grado",
        "controles": {"año": _anio},
        "sql": lambda p: (
            "SELECT m.AñoEscolar, m.Nivel, m.Grado, m.Seccion, COUNT(*) AS Total_Matriculados, "
            "SUM(CASE WHEN m.Estado = 'Matriculado' THEN 1 ELSE 0 END) AS Activos, "
            "SUM(CASE WHEN m.Estado = 'Retirado' THEN 1 ELSE 0 END) AS Retirados, "
            "SUM(CASE WHEN m.Estado = 'Trasladado' THEN 1 ELSE 0 END) AS Trasladados "
            "FROM MATRICULA m WHERE m.AñoEscolar = %s "
            "GROUP BY m.AñoEscolar, m.Nivel, m.Grado, m.Seccion ORDER BY m.Nivel, m.Grado",
            (p["año"],),
        ),
    },
    {
        "nombre": "6. Estudiantes de un apoderado",
        "controles": {"dni apoderado": _dni},
        "sql": lambda p: (
            "SELECT e.DNI, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) "
            "AS Estudiante, e.FechaNacimiento, e.DistritoDomicilio FROM ESTUDIANTE e "
            "WHERE e.DNI_Apoderado = %s ORDER BY e.ApellidoPaterno",
            (p["dni apoderado"],),
        ),
    },
    {
        "nombre": "7. Matrículas declaradas por un responsable",
        "controles": {"dni responsable": _dni},
        "sql": lambda p: (
            "SELECT m.DNI_Estudiante, m.AñoEscolar, m.Nivel, m.Grado, m.Seccion, "
            "m.FechaSuscripcion, m.LugarSuscripcion FROM MATRICULA m "
            "WHERE m.DNI_Responsable = %s ORDER BY m.AñoEscolar DESC",
            (p["dni responsable"],),
        ),
    },
    {
        "nombre": "8. Detalle de la última matrícula de un estudiante",
        "controles": {"dni": _dni},
        "sql": lambda p: (
            "SELECT e.DNI, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) "
            "AS Estudiante, m.AñoEscolar, m.Nivel, m.Grado, m.Seccion, m.Estado, "
            "m.LugarSuscripcion, m.FechaSuscripcion, CONCAT(p.ApellidoPaterno, ' ', "
            "p.ApellidoMaterno, ', ', p.Nombres) AS Responsable, CONCAT(s.ApellidoPaterno, ' ', "
            "s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria FROM MATRICULA m "
            "INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI "
            "INNER JOIN PADRE_APODERADO p ON m.DNI_Responsable = p.DNI "
            "INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI "
            "WHERE m.DNI_Estudiante = %s ORDER BY m.AñoEscolar DESC LIMIT 1",
            (p["dni"],),
        ),
    },
    {
        "nombre": "9. Logros académicos y su institución",
        "controles": {"dni": _dni},
        "sql": lambda p: (
            "SELECT c.CodigoVirtual, l.AñoEscolar, l.GradoCursado, i.NombreIE, i.TipoIE, "
            "l.SituacionFinal FROM CONSTANCIA_LOGROS c "
            "INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual "
            "INNER JOIN INSTITUCION_EDUCATIVA i ON l.CodigoModularIE = i.CodigoModularIE "
            "WHERE c.DNI_Estudiante = %s ORDER BY l.AñoEscolar",
            (p["dni"],),
        ),
    },
    {
        "nombre": "10. Matrículas registradas por secretaría en un año",
        "controles": {"año": _anio},
        "sql": lambda p: (
            "SELECT s.DNI, CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) "
            "AS Secretaria, m.Nivel, COUNT(*) AS TotalMatriculas FROM MATRICULA m "
            "INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI WHERE m.AñoEscolar = %s "
            "GROUP BY s.DNI, s.ApellidoPaterno, s.ApellidoMaterno, s.Nombres, m.Nivel "
            "ORDER BY m.Nivel",
            (p["año"],),
        ),
    },
]


class PaginaReportes(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        self.controles: dict[str, QWidget] = {}
        self.filas: list[dict[str, Any]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        superior = QHBoxLayout()
        self.selector = QComboBox()
        for reporte in REPORTES:
            self.selector.addItem(reporte["nombre"])
        self.selector.currentIndexChanged.connect(self._cambiar_reporte)
        generar = boton("Generar reporte")
        generar.clicked.connect(self.generar)
        exportar = boton("Exportar CSV", "Secundario")
        exportar.clicked.connect(self.exportar)
        superior.addWidget(QLabel("Reporte:"))
        superior.addWidget(self.selector, 1)
        superior.addWidget(generar)
        superior.addWidget(exportar)
        layout.addLayout(superior)

        self.panel_parametros = QHBoxLayout()
        layout.addLayout(self.panel_parametros)

        self.tabla = Tabla([])
        layout.addWidget(self.tabla, 1)
        self.resumen = QLabel("")
        layout.addWidget(self.resumen)
        self._cambiar_reporte(0)

    def _limpiar_parametros(self) -> None:
        while self.panel_parametros.count():
            item = self.panel_parametros.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.controles = {}

    def _cambiar_reporte(self, indice: int) -> None:
        self._limpiar_parametros()
        reporte = REPORTES[indice]
        for nombre, fabrica in reporte["controles"].items():
            etiqueta = QLabel(nombre.capitalize())
            etiqueta.setObjectName("Etiqueta")
            control = fabrica()
            self.panel_parametros.addWidget(etiqueta)
            self.panel_parametros.addWidget(control)
            self.controles[nombre] = control
        self.panel_parametros.addStretch(1)

    def _valores(self) -> dict[str, Any]:
        valores: dict[str, Any] = {}
        for nombre, control in self.controles.items():
            if isinstance(control, QSpinBox):
                valores[nombre] = control.value()
            elif isinstance(control, QComboBox):
                valores[nombre] = control.currentText()
            else:
                valores[nombre] = control.text()
        return valores

    def generar(self) -> None:
        indice = self.selector.currentIndex()
        reporte = REPORTES[indice]
        try:
            sql, parametros = reporte["sql"](self._valores())
            self.filas = consultar(sql, parametros)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        if not self.filas:
            self.tabla.setColumnCount(0)
            self.tabla.setRowCount(0)
            self.resumen.setText("La consulta no devolvió resultados.")
            return
        columnas = [(clave, clave) for clave in self.filas[0].keys()]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.columnas = columnas
        self.tabla.setHorizontalHeaderLabels([c[0] for c in columnas])
        self.tabla.cargar(self.filas)
        self.resumen.setText(f"{len(self.filas)} fila(s).")

    def exportar(self) -> None:
        if not self.filas:
            mostrar_info(self, "Primero genere un reporte.")
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte", "reporte.csv", "CSV (*.csv)"
        )
        if not ruta:
            return
        with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(self.filas[0].keys()))
            escritor.writeheader()
            escritor.writerows(self.filas)
        mostrar_info(self, f"Reporte exportado en:\n{ruta}")
