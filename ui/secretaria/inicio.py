"""Inicio del portal de secretaría."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from core.db import consultar_uno
from core.errores import ErrorApp
from servicios import solicitudes
from ui.comunes.widgets import etiqueta_ayuda, tarjeta, titulo_seccion


class PaginaInicioSecretaria(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(14)
        self.tarjeta, self.caja = tarjeta()
        self.layout_principal.addWidget(self.tarjeta)
        self.layout_principal.addStretch(1)

    def _limpiar(self) -> None:
        while self.caja.count():
            item = self.caja.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def actualizar(self) -> None:
        self._limpiar()
        self.caja.addWidget(titulo_seccion("Resumen general"))
        indicadores: dict[str, object] = {}
        try:
            propias = solicitudes.listar()
            resumen = solicitudes.resumen_por_estado(propias)
            pendientes = resumen.get("Enviada", 0) + resumen.get("En revisión", 0)
            indicadores = {
                "Solicitudes pendientes": pendientes,
                "En subsanación": resumen.get("Subsanación", 0),
                "Aprobadas": resumen.get("Aprobada", 0),
                "Rechazadas": resumen.get("Rechazada", 0),
            }
        except ErrorApp as exc:
            self.caja.addWidget(etiqueta_ayuda(f"No se pudo leer el almacén: {exc}"))
        try:
            estudiantes = consultar_uno("SELECT COUNT(*) AS total FROM ESTUDIANTE")
            matriculas = consultar_uno(
                "SELECT COUNT(*) AS total FROM MATRICULA WHERE Estado = 'Matriculado'"
            )
            indicadores["Estudiantes registrados"] = estudiantes["total"] if estudiantes else 0
            indicadores["Matrículas activas"] = matriculas["total"] if matriculas else 0
        except ErrorApp as exc:
            self.caja.addWidget(etiqueta_ayuda(f"No se pudo consultar la base: {exc}"))
        cuadricula = QGridLayout()
        for indice, (etiqueta, valor) in enumerate(indicadores.items()):
            numero = QLabel(str(valor))
            numero.setStyleSheet("font-size: 26px; font-weight: 700; color: #1F4E79;")
            cuadricula.addWidget(numero, (indice // 4) * 2, indice % 4)
            cuadricula.addWidget(QLabel(etiqueta), (indice // 4) * 2 + 1, indice % 4)
        self.caja.addLayout(cuadricula)
        self.caja.addWidget(
            etiqueta_ayuda(
                "Revise la bandeja de solicitudes, valide los datos y apruebe o rechace. "
                "Recuerde que el OCR solo propone; usted confirma."
            )
        )
