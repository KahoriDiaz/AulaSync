"""Bandeja de solicitudes para la secretaría."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from core.errores import ErrorApp
from servicios import solicitudes
from ui.comunes.widgets import (
    Tabla,
    boton,
    mostrar_error,
    mostrar_info,
    tarjeta,
)
from ui.secretaria.revision import DialogoRevision


class PaginaBandeja(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        filtros, caja = tarjeta()
        fila = QHBoxLayout()
        self.estado = QComboBox()
        self.estado.addItem("Todos los estados", None)
        for estado in solicitudes.ESTADOS_SOLICITUD:
            self.estado.addItem(estado, estado)
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar por ID, DNI, estudiante o padre")
        self.busqueda.returnPressed.connect(self.actualizar)
        buscar = boton("Buscar")
        buscar.clicked.connect(self.actualizar)
        limpiar = boton("Limpiar", "Secundario")
        limpiar.clicked.connect(self._limpiar)
        fila.addWidget(QLabel("Estado:"))
        fila.addWidget(self.estado)
        fila.addWidget(self.busqueda, 1)
        fila.addWidget(buscar)
        fila.addWidget(limpiar)
        caja.addLayout(fila)
        layout.addWidget(filtros)

        self.tabla = Tabla(
            [
                ("ID", "id"), ("Tipo", "tipo"), ("Estudiante", "estudiante"),
                ("Padre/apoderado", "padre"), ("Año", "anio"), ("Nivel", "nivel"),
                ("Grado", "grado"), ("Sección", "seccion"), ("Estado", "estado"),
                ("Enviada", "fecha_envio"),
            ]
        )
        self.tabla.doubleClicked.connect(self.revisar)
        layout.addWidget(self.tabla, 1)

        acciones = QHBoxLayout()
        self.resumen = QLabel("")
        acciones.addWidget(self.resumen)
        acciones.addStretch(1)
        revisar = boton("Abrir revisión")
        revisar.clicked.connect(self.revisar)
        acciones.addWidget(revisar)
        layout.addLayout(acciones)

    def _limpiar(self) -> None:
        self.busqueda.clear()
        self.estado.setCurrentIndex(0)
        self.actualizar()

    def actualizar(self) -> None:
        try:
            lista = solicitudes.listar(
                estado=self.estado.currentData(), filtro=self.busqueda.text()
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        filas = []
        for solicitud in lista:
            est = solicitud.get("datos", {}).get("estudiante") or {}
            nombre = " ".join(
                valor for valor in (
                    est.get("ApellidoPaterno"), est.get("ApellidoMaterno"), est.get("Nombres")
                ) if valor
            )
            filas.append(
                {
                    "id": solicitud.get("id"),
                    "tipo": solicitud.get("tipo"),
                    "estudiante": nombre or solicitud.get("estudiante_dni", ""),
                    "padre": solicitud.get("padre", {}).get("nombre", ""),
                    "anio": solicitud.get("anio"),
                    "nivel": solicitud.get("nivel"),
                    "grado": solicitud.get("grado"),
                    "seccion": solicitud.get("seccion"),
                    "estado": solicitud.get("estado"),
                    "fecha_envio": str(solicitud.get("fecha_envio") or "")[:16],
                }
            )
        self.tabla.cargar(filas)
        pendientes = sum(1 for s in lista if s.get("estado") in ("Enviada", "En revisión"))
        self.resumen.setText(f"{len(lista)} solicitud(es) · {pendientes} pendiente(s) de revisión")

    def revisar(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0:
            mostrar_info(self, "Seleccione una solicitud de la lista.")
            return
        id_solicitud = self.tabla.item(fila, 0).text()
        DialogoRevision(id_solicitud, self).exec()
        self.actualizar()
