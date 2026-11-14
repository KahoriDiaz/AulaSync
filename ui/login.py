"""Ventana de inicio de sesión y registro de padres."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.errores import ErrorApp
from servicios import usuarios
from ui.comunes.widgets import boton, mostrar_error, mostrar_info, tarjeta
from ui.ventana_principal import VentanaPrincipal


class DialogoRegistro(QDialog):
    def __init__(self, padre: QWidget | None = None):
        super().__init__(padre)
        self.setWindowTitle("Crear cuenta de padre/apoderado")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        titulo = QLabel("Registro de cuenta")
        titulo.setObjectName("Subtitulo")
        layout.addWidget(titulo)
        formulario = QFormLayout()
        self.dni = QLineEdit()
        self.dni.setMaxLength(8)
        self.nombres = QLineEdit()
        self.apellidos = QLineEdit()
        self.usuario = QLineEdit()
        self.clave = QLineEdit()
        self.clave.setEchoMode(QLineEdit.Password)
        self.confirmar = QLineEdit()
        self.confirmar.setEchoMode(QLineEdit.Password)
        formulario.addRow("DNI", self.dni)
        formulario.addRow("Nombres", self.nombres)
        formulario.addRow("Apellidos", self.apellidos)
        formulario.addRow("Usuario", self.usuario)
        formulario.addRow("Contraseña", self.clave)
        formulario.addRow("Confirmar contraseña", self.confirmar)
        layout.addLayout(formulario)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = boton("Cancelar", "Secundario")
        cancelar.clicked.connect(self.reject)
        registrar = boton("Registrar")
        registrar.clicked.connect(self.registrar)
        botones.addWidget(cancelar)
        botones.addWidget(registrar)
        layout.addLayout(botones)

    def registrar(self) -> None:
        try:
            usuarios.registrar_padre(
                self.dni.text(), self.nombres.text(), self.apellidos.text(),
                self.usuario.text(), self.clave.text(), self.confirmar.text(),
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        mostrar_info(self, "La cuenta fue creada. Ya puede iniciar sesión.")
        self.accept()


class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        self.setWindowTitle("Sistema de Registro de Matrícula")
        self.setFixedSize(460, 420)
        self.principal: VentanaPrincipal | None = None

        contenedor = QVBoxLayout(self)
        contenedor.setContentsMargins(50, 40, 50, 40)
        tarjeta_login, caja = tarjeta()

        titulo = QLabel("Sistema de Registro de Matrícula")
        titulo.setObjectName("Titulo")
        titulo.setAlignment(Qt.AlignCenter)
        subtitulo = QLabel("Acceso al sistema")
        subtitulo.setObjectName("Ayuda")
        subtitulo.setAlignment(Qt.AlignCenter)
        caja.addWidget(titulo)
        caja.addWidget(subtitulo)
        caja.addSpacing(10)

        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Usuario")
        self.clave = QLineEdit()
        self.clave.setPlaceholderText("Contraseña")
        self.clave.setEchoMode(QLineEdit.Password)
        self.clave.returnPressed.connect(self.ingresar)
        caja.addWidget(self.usuario)
        caja.addWidget(self.clave)

        self.ingresar_boton = boton("Iniciar sesión")
        self.ingresar_boton.clicked.connect(self.ingresar)
        caja.addWidget(self.ingresar_boton)

        registro = QPushButton("¿No tiene cuenta? Regístrese como padre/apoderado")
        registro.setObjectName("Enlace")
        registro.setCursor(Qt.PointingHandCursor)
        registro.clicked.connect(self.abrir_registro)
        caja.addWidget(registro, alignment=Qt.AlignCenter)

        contenedor.addWidget(tarjeta_login)
        self.usuario.setFocus()

    def abrir_registro(self) -> None:
        DialogoRegistro(self).exec()

    def ingresar(self) -> None:
        try:
            sesion = usuarios.iniciar_sesion(self.usuario.text(), self.clave.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc), "Acceso denegado")
            return
        self.principal = VentanaPrincipal(sesion)
        self.principal.show()
        self.close()
