"""Ventana principal con navegación lateral según el rol."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core import seguridad
from ui.comunes.estilos import SIDEBAR
from ui.comunes.widgets import boton


def _paginas_padre() -> list[tuple[str, str]]:
    return [
        ("Inicio", "ui.padre.inicio:PaginaInicioPadre"),
        ("Nueva solicitud", "ui.padre.asistente:PaginaAsistente"),
        ("Mis solicitudes", "ui.padre.mis_solicitudes:PaginaMisSolicitudes"),
        ("Mi perfil", "ui.padre.mi_perfil:PaginaPerfilPadre"),
    ]


def _paginas_secretaria(es_admin: bool) -> list[tuple[str, str]]:
    paginas = [
        ("Inicio", "ui.secretaria.inicio:PaginaInicioSecretaria"),
        ("Bandeja de solicitudes", "ui.secretaria.bandeja:PaginaBandeja"),
        ("Consultas", "ui.secretaria.consultas:PaginaConsultas"),
        ("Reportes", "ui.secretaria.reportes:PaginaReportes"),
        ("Gestión de datos", "ui.secretaria.catalogos:PaginaCatalogos"),
    ]
    if es_admin:
        paginas.append(("Usuarios", "ui.secretaria.usuarios:PaginaUsuarios"))
    return paginas


def _cargar_pagina(ruta: str) -> QWidget:
    modulo_nombre, clase_nombre = ruta.split(":")
    import importlib

    modulo = importlib.import_module(modulo_nombre)
    clase = getattr(modulo, clase_nombre)
    return clase()


class VentanaPrincipal(QWidget):
    def __init__(self, sesion: seguridad.Sesion):
        super().__init__()
        self.sesion = sesion
        self.setObjectName("Fondo")
        self.setWindowTitle("Sistema de Registro de Matrícula")
        self.resize(1180, 720)
        self.paginas: list[tuple[str, str, QWidget]] = []

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        menu = QWidget()
        menu.setFixedWidth(240)
        menu.setStyleSheet(f"background-color: {SIDEBAR};")
        menu_layout = QVBoxLayout(menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(0)

        marca = QLabel("Sistema de Registro\nde Matrícula")
        marca.setObjectName("Marca")
        menu_layout.addWidget(marca)

        self.lista = QListWidget()
        self.lista.setObjectName("Menu")
        menu_layout.addWidget(self.lista, 1)

        usuario = QLabel(f"{sesion.nombre_completo}\nRol: {sesion.rol}")
        usuario.setStyleSheet("color: #C7D3E0; padding: 10px 16px;")
        menu_layout.addWidget(usuario)
        salir = QPushButton("Cerrar sesión")
        salir.setObjectName("Secundario")
        salir.setCursor(Qt.PointingHandCursor)
        salir.clicked.connect(self.cerrar_sesion)
        contenedor_salir = QWidget()
        caja_salir = QVBoxLayout(contenedor_salir)
        caja_salir.setContentsMargins(12, 6, 12, 14)
        caja_salir.addWidget(salir)
        menu_layout.addWidget(contenedor_salir)

        raiz.addWidget(menu)

        derecha = QWidget()
        derecha.setObjectName("Fondo")
        derecha_layout = QVBoxLayout(derecha)
        derecha_layout.setContentsMargins(20, 16, 20, 16)
        derecha_layout.setSpacing(12)

        self.barra = QLabel()
        self.barra.setObjectName("Titulo")
        derecha_layout.addWidget(self.barra)

        self.stack = QStackedWidget()
        derecha_layout.addWidget(self.stack, 1)
        raiz.addWidget(derecha, 1)

        rutas = _paginas_padre() if sesion.es_padre else _paginas_secretaria(sesion.es_administrador)
        for titulo, ruta in rutas:
            self.lista.addItem(QListWidgetItem(titulo))
            self.paginas.append((titulo, ruta, None))
        self.lista.currentRowChanged.connect(self.cambiar_pagina)
        self.lista.setCurrentRow(0)

    def cambiar_pagina(self, indice: int) -> None:
        if indice < 0 or indice >= len(self.paginas):
            return
        titulo, ruta, pagina = self.paginas[indice]
        if pagina is None:
            try:
                pagina = _cargar_pagina(ruta)
            except Exception as exc:  # noqa: BLE001
                pagina = QLabel(f"No se pudo cargar la sección: {exc}")
                pagina.setWordWrap(True)
            self.paginas[indice] = (titulo, ruta, pagina)
            self.stack.addWidget(pagina)
        self.stack.setCurrentWidget(pagina)
        self.barra.setText(titulo)
        actualizar = getattr(pagina, "actualizar", None)
        if callable(actualizar):
            try:
                actualizar()
            except Exception as exc:  # noqa: BLE001
                self.barra.setText(f"{titulo} (revise la conexión: {exc})")

    def cerrar_sesion(self) -> None:
        seguridad.cerrar_sesion()
        from ui.login import VentanaLogin

        self.login = VentanaLogin()
        self.login.show()
        self.close()
