"""Consultas y procedimientos almacenados."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.db import consultar
from core.errores import ErrorApp
from core.formatos import NIVELES, grados_de_nivel
from servicios import matriculas
from ui.comunes.widgets import Tabla, boton, mostrar_error


def _fila(*widgets: QWidget) -> QWidget:
    contenedor = QWidget()
    caja = QHBoxLayout(contenedor)
    caja.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        caja.addWidget(widget)
    return contenedor


class PaginaConsultas(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_buscar(), "Buscar estudiante")
        self.tabs.addTab(self._tab_hermanos(), "Hermanos")
        self.tabs.addTab(self._tab_grado(), "Grado que corresponde")
        self.tabs.addTab(self._tab_comparar(), "Comparar años")
        self.tabs.addTab(self._tab_seccion(), "Matriculados por sección")
        layout.addWidget(self.tabs)

    # ------------------------------------------------------------ pestañas
    def _tab_buscar(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        self.buscar_paterno = QLineEdit()
        self.buscar_paterno.setPlaceholderText("Apellido paterno")
        self.buscar_materno = QLineEdit()
        self.buscar_materno.setPlaceholderText("Apellido materno")
        self.buscar_nombres = QLineEdit()
        self.buscar_nombres.setPlaceholderText("Nombres")
        accion = boton("Buscar")
        accion.clicked.connect(self.buscar_estudiante)
        caja.addWidget(_fila(self.buscar_paterno, self.buscar_materno, self.buscar_nombres, accion))
        self.tabla_buscar = Tabla(
            [("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
             ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres"),
             ("Nacimiento", "FechaNacimiento"), ("Celular", "Celular")]
        )
        caja.addWidget(self.tabla_buscar)
        return pagina

    def _tab_hermanos(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        self.dni_hermanos = QLineEdit()
        self.dni_hermanos.setPlaceholderText("DNI del estudiante")
        self.dni_hermanos.setMaxLength(8)
        accion = boton("Listar hermanos")
        accion.clicked.connect(self.listar_hermanos)
        caja.addWidget(_fila(self.dni_hermanos, accion))
        self.tabla_hermanos = Tabla(
            [("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
             ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres")]
        )
        caja.addWidget(self.tabla_hermanos)
        return pagina

    def _tab_grado(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        self.dni_grado = QLineEdit()
        self.dni_grado.setPlaceholderText("DNI del estudiante")
        self.dni_grado.setMaxLength(8)
        self.anio_grado = QSpinBox()
        self.anio_grado.setRange(2000, 2100)
        self.anio_grado.setValue(2026)
        accion = boton("Verificar")
        accion.clicked.connect(self.verificar_grado)
        caja.addWidget(_fila(self.dni_grado, self.anio_grado, accion))
        self.resultado_grado = QLabel("")
        self.resultado_grado.setWordWrap(True)
        caja.addWidget(self.resultado_grado)
        caja.addStretch(1)
        return pagina

    def _tab_comparar(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        self.anio_anterior = QSpinBox()
        self.anio_anterior.setRange(2000, 2100)
        self.anio_anterior.setValue(2025)
        self.anio_actual = QSpinBox()
        self.anio_actual.setRange(2000, 2100)
        self.anio_actual.setValue(2026)
        accion = boton("Comparar")
        accion.clicked.connect(self.comparar)
        caja.addWidget(_fila(QLabel("Año anterior:"), self.anio_anterior,
                             QLabel("Año actual:"), self.anio_actual, accion))
        self.resumen_comparar = QLabel("")
        caja.addWidget(self.resumen_comparar)
        self.tabla_comparar = Tabla(
            [("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
             ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres"),
             ("Nivel anterior", "NivelAnterior"), ("Grado anterior", "GradoAnterior"),
             ("Nivel actual", "NivelActual"), ("Grado actual", "GradoActual"),
             ("Situación", "Situacion")]
        )
        caja.addWidget(self.tabla_comparar)
        return pagina

    def _tab_seccion(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        self.anio_seccion = QSpinBox()
        self.anio_seccion.setRange(2000, 2100)
        self.anio_seccion.setValue(2026)
        self.nivel_seccion = QComboBox()
        self.nivel_seccion.addItems(NIVELES)
        self.grado_seccion = QComboBox()
        self.grado_seccion.addItems(grados_de_nivel("Inicial"))
        self.nivel_seccion.currentTextChanged.connect(
            lambda nivel: self.grado_seccion.clear() or self.grado_seccion.addItems(grados_de_nivel(nivel))
        )
        self.seccion_seccion = QLineEdit()
        self.seccion_seccion.setPlaceholderText("Sección")
        self.seccion_seccion.setMaxLength(5)
        accion = boton("Listar")
        accion.clicked.connect(self.listar_seccion)
        caja.addWidget(_fila(self.anio_seccion, self.nivel_seccion, self.grado_seccion,
                             self.seccion_seccion, accion))
        self.tabla_seccion = Tabla(
            [("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
             ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres"),
             ("Año", "AñoEscolar"), ("Nivel", "Nivel"), ("Grado", "Grado"),
             ("Sección", "Seccion"), ("Estado", "Estado")]
        )
        caja.addWidget(self.tabla_seccion)
        return pagina

    # ------------------------------------------------------------ acciones
    def buscar_estudiante(self) -> None:
        try:
            filas = matriculas.buscar_estudiantes(
                self.buscar_paterno.text(), self.buscar_materno.text(), self.buscar_nombres.text()
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla_buscar.cargar(filas)

    def listar_hermanos(self) -> None:
        try:
            filas = matriculas.listar_hermanos(self.dni_hermanos.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla_hermanos.cargar(filas)

    def verificar_grado(self) -> None:
        try:
            resultado = matriculas.verificar_grado(self.dni_grado.text(), self.anio_grado.value())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        color = {"Correcto": "#2E8B57", "Advertencia": "#B7791F", "Error": "#C0392B"}.get(
            resultado.get("estado"), "#52606D"
        )
        self.resultado_grado.setStyleSheet(f"color: {color}; font-weight: 700;")
        self.resultado_grado.setText(
            f"{resultado.get('mensaje')}\nEdad al 31 de marzo: {resultado.get('edad')} · "
            f"Grado sugerido: {resultado.get('nivel')} {resultado.get('grado')}"
        )

    def comparar(self) -> None:
        try:
            resultado = matriculas.verificar_matriculados(
                self.anio_anterior.value(), self.anio_actual.value()
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        resumen = resultado["resumen"]
        self.resumen_comparar.setText(
            f"Total: {resumen['Total']} · Continúan: {resumen['Continúa']} · "
            f"Sin matrícula: {resumen['Sin matrícula en el año actual']} · Nuevos: {resumen['Nuevo']}"
        )
        self.tabla_comparar.cargar(resultado["filas"])

    def listar_seccion(self) -> None:
        try:
            filas = consultar(
                "SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres, "
                "m.AñoEscolar, m.Nivel, m.Grado, m.Seccion, m.Estado "
                "FROM MATRICULA m INNER JOIN ESTUDIANTE e ON e.DNI = m.DNI_Estudiante "
                "WHERE m.AñoEscolar = %s AND m.Nivel = %s AND m.Grado = %s AND m.Seccion = %s "
                "ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres",
                (
                    self.anio_seccion.value(), self.nivel_seccion.currentText(),
                    self.grado_seccion.currentText(), self.seccion_seccion.text().strip().upper(),
                ),
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla_seccion.cargar(filas)
