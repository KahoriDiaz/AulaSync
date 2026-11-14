"""Punto de entrada de la aplicación de escritorio."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.comunes.estilos import hoja_estilos
from ui.login import VentanaLogin


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema de Registro de Matrícula")
    app.setStyleSheet(hoja_estilos())
    ventana = VentanaLogin()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
