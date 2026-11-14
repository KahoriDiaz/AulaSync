"""Inicio del portal del padre/apoderado."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from core import seguridad
from servicios import solicitudes
from ui.comunes.widgets import boton, etiqueta_ayuda, tarjeta


class PaginaInicioPadre(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(14)
        self.contenedor, self.caja = tarjeta()
        self.layout_principal.addWidget(self.contenedor)
        self.layout_principal.addStretch(1)

    def actualizar(self) -> None:
        while self.caja.count():
            item = self.caja.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sesion = seguridad.sesion_actual()
        bienvenida = QLabel(f"Bienvenido(a), {sesion.nombre_completo if sesion else ''}")
        bienvenida.setObjectName("Titulo")
        self.caja.addWidget(bienvenida)
        self.caja.addWidget(
            etiqueta_ayuda(
                "Desde aquí puede registrar la matrícula de un estudiante. Prepare el DNI del "
                "estudiante, el DNI del padre/apoderado y la constancia de logros en imagen o PDF."
            )
        )
        try:
            propias = solicitudes.listar(solo_propias=True)
            resumen = solicitudes.resumen_por_estado(propias)
        except Exception as exc:  # noqa: BLE001
            self.caja.addWidget(etiqueta_ayuda(f"No se pudo leer el almacén: {exc}"))
            return
        cuadricula = QGridLayout()
        for indice, (estado, total) in enumerate(resumen.items()):
            etiqueta = QLabel(f"{total}")
            etiqueta.setStyleSheet("font-size: 26px; font-weight: 700; color: #1F4E79;")
            cuadricula.addWidget(etiqueta, 0, indice)
            cuadricula.addWidget(QLabel(estado), 1, indice)
        self.caja.addLayout(cuadricula)
        self.caja.addWidget(
            etiqueta_ayuda("Use “Nueva solicitud” para iniciar un registro o “Mis solicitudes” "
                           "para continuar uno guardado.")
        )
