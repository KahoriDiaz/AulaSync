"""Componentes reutilizables de la interfaz."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.comunes.estilos import (
    ACENTO,
    COLORES_ESTADO,
    PELIGRO,
    PRIMARIO,
    TEXTO_SUAVE,
    TARJETA,
)


class CampoTexto(QWidget):
    def __init__(self, etiqueta: str, obligatorio: bool = False, maximo: int = 100):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        texto = f"{etiqueta} *" if obligatorio else etiqueta
        self.etiqueta = QLabel(texto)
        self.etiqueta.setObjectName("Etiqueta")
        self.edicion = QLineEdit()
        self.edicion.setMaxLength(maximo)
        self.edicion.setPlaceholderText(etiqueta)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.edicion)

    def valor(self) -> str:
        return self.edicion.text().strip()

    def set_valor(self, valor: Any) -> None:
        self.edicion.setText("" if valor is None else str(valor))

    def limpiar(self) -> None:
        self.edicion.clear()

    def set_solo_lectura(self, solo_lectura: bool = True) -> None:
        self.edicion.setReadOnly(solo_lectura)

    def marcar_error(self, error: bool) -> None:
        color = PELIGRO if error else "#D6DEE6"
        self.edicion.setStyleSheet(f"border: 1px solid {color};")


class CampoArea(QWidget):
    def __init__(self, etiqueta: str, alto: int = 70):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.etiqueta = QLabel(etiqueta)
        self.etiqueta.setObjectName("Etiqueta")
        self.edicion = QPlainTextEdit()
        self.edicion.setFixedHeight(alto)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.edicion)

    def valor(self) -> str:
        return self.edicion.toPlainText().strip()

    def set_valor(self, valor: Any) -> None:
        self.edicion.setPlainText("" if valor is None else str(valor))


class CampoCombo(QWidget):
    def __init__(self, etiqueta: str, opciones: Sequence[str], vacio: str | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.etiqueta = QLabel(etiqueta)
        self.etiqueta.setObjectName("Etiqueta")
        self.combo = QComboBox()
        if vacio is not None:
            self.combo.addItem(vacio, None)
        for opcion in opciones:
            self.combo.addItem(opcion, opcion)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.combo)

    def valor(self) -> Any:
        return self.combo.currentData()

    def set_valor(self, valor: Any) -> None:
        indice = self.combo.findData(valor)
        self.combo.setCurrentIndex(indice if indice >= 0 else 0)

    def cambiar_opciones(self, opciones: Sequence[str], vacio: str | None = None) -> None:
        actual = self.valor()
        self.combo.clear()
        if vacio is not None:
            self.combo.addItem(vacio, None)
        for opcion in opciones:
            self.combo.addItem(opcion, opcion)
        self.set_valor(actual)


class CampoFecha(QWidget):
    def __init__(self, etiqueta: str, valor: QDate | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.etiqueta = QLabel(etiqueta)
        self.etiqueta.setObjectName("Etiqueta")
        self.edicion = QDateEdit()
        self.edicion.setCalendarPopup(True)
        self.edicion.setDisplayFormat("dd/MM/yyyy")
        self.edicion.setDate(valor or QDate.currentDate())
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.edicion)

    def valor(self) -> str:
        return self.edicion.date().toString("yyyy-MM-dd")

    def valor_qdate(self) -> QDate:
        return self.edicion.date()

    def set_valor(self, valor: Any) -> None:
        if not valor:
            self.edicion.setDate(QDate.currentDate())
            return
        if isinstance(valor, str):
            fecha = QDate.fromString(valor[:10], "yyyy-MM-dd")
        else:
            fecha = QDate(valor)
        if fecha.isValid():
            self.edicion.setDate(fecha)


class CampoEntero(QWidget):
    def __init__(self, etiqueta: str, minimo: int = 1, maximo: int = 20):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.etiqueta = QLabel(etiqueta)
        self.etiqueta.setObjectName("Etiqueta")
        self.edicion = QSpinBox()
        self.edicion.setRange(minimo, maximo)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.edicion)

    def valor(self) -> int:
        return self.edicion.value()

    def set_valor(self, valor: Any) -> None:
        try:
            self.edicion.setValue(int(valor))
        except (TypeError, ValueError):
            self.edicion.setValue(1)


class CampoSiNo(QWidget):
    def __init__(self, etiqueta: str, defecto: bool = False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.etiqueta = QLabel(etiqueta)
        self.etiqueta.setObjectName("Etiqueta")
        self.combo = QComboBox()
        self.combo.addItem("Sí", True)
        self.combo.addItem("No", False)
        self.combo.setCurrentIndex(0 if defecto else 1)
        layout.addWidget(self.etiqueta)
        layout.addWidget(self.combo)

    def valor(self) -> bool:
        return bool(self.combo.currentData())

    def set_valor(self, valor: Any) -> None:
        self.combo.setCurrentIndex(0 if valor in (True, 1, "1", "Sí", "SI") else 1)


def titulo_seccion(texto: str) -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setObjectName("TituloSeccion")
    return etiqueta


def etiqueta_ayuda(texto: str) -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setObjectName("Ayuda")
    etiqueta.setWordWrap(True)
    return etiqueta


def badge_estado(texto: str) -> QLabel:
    color = COLORES_ESTADO.get(texto, TEXTO_SUAVE)
    etiqueta = QLabel(texto)
    etiqueta.setAlignment(Qt.AlignCenter)
    etiqueta.setStyleSheet(
        f"background-color: {color}; color: white; border-radius: 9px; "
        "padding: 2px 10px; font-weight: 600;"
    )
    return etiqueta


def boton(texto: str, tipo: str | None = None) -> QPushButton:
    control = QPushButton(texto)
    if tipo:
        control.setObjectName(tipo)
    control.setCursor(Qt.PointingHandCursor)
    return control


def separador() -> QFrame:
    linea = QFrame()
    linea.setFrameShape(QFrame.HLine)
    linea.setStyleSheet("color: #E1E8EF;")
    return linea


def tarjeta() -> tuple[QWidget, QVBoxLayout]:
    contenedor = QWidget()
    contenedor.setObjectName("Tarjeta")
    layout = QVBoxLayout(contenedor)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    return contenedor, layout


class Tabla(QTableWidget):
    def __init__(self, columnas: Sequence[tuple[str, str]]):
        super().__init__(0, len(columnas))
        self.columnas = list(columnas)
        self.setHorizontalHeaderLabels([titulo for titulo, _ in columnas])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setWordWrap(False)

    def cargar(self, filas: Iterable[dict[str, Any]]) -> None:
        filas = list(filas)
        self.setRowCount(len(filas))
        for indice_fila, fila in enumerate(filas):
            for indice_columna, (_, clave) in enumerate(self.columnas):
                valor = fila.get(clave, "")
                item = QTableWidgetItem("" if valor is None else str(valor))
                if clave in COLORES_ESTADO:
                    item.setForeground(QColor(COLORES_ESTADO[str(valor)]))
                self.setItem(indice_fila, indice_columna, item)
        self.resizeColumnsToContents()

    def fila_actual(self) -> dict[str, Any] | None:
        fila = self.currentRow()
        if fila < 0:
            return None
        datos: dict[str, Any] = {}
        for indice_columna, (_, clave) in enumerate(self.columnas):
            item = self.item(fila, indice_columna)
            datos[clave] = item.text() if item else ""
        return datos


def mostrar_error(padre: QWidget, mensaje: str, titulo: str = "No se pudo completar") -> None:
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Warning)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.exec()


def mostrar_info(padre: QWidget, mensaje: str, titulo: str = "Información") -> None:
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Information)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.exec()


def confirmar(padre: QWidget, mensaje: str, titulo: str = "Confirmar") -> bool:
    respuesta = QMessageBox.question(
        padre, titulo, mensaje, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    return respuesta == QMessageBox.Yes


def encabezado(texto: str) -> QLabel:
    etiqueta = QLabel(texto)
    fuente = QFont()
    fuente.setPointSize(11)
    fuente.setBold(True)
    etiqueta.setFont(fuente)
    etiqueta.setStyleSheet(f"color: {PRIMARIO};")
    return etiqueta


def chip(texto: str, color: str = PRIMARIO) -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setStyleSheet(
        f"background-color: {color}; color: white; border-radius: 10px; "
        "padding: 3px 10px; font-weight: 600;"
    )
    return etiqueta


def fila_horizontal(*widgets: QWidget, separacion: int = 10) -> QWidget:
    contenedor = QWidget()
    layout = QHBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(separacion)
    for widget in widgets:
        layout.addWidget(widget)
    return contenedor


def indicador(color: str, texto: str) -> QLabel:
    etiqueta = QLabel(f"● {texto}")
    etiqueta.setStyleSheet(f"color: {color}; font-weight: 600;")
    return etiqueta
