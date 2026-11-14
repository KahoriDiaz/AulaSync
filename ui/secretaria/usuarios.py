"""Administración de cuentas de usuario (solo Administrador)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.errores import ErrorApp
from servicios import usuarios
from ui.comunes.widgets import (
    CampoCombo,
    CampoTexto,
    Tabla,
    boton,
    confirmar,
    etiqueta_ayuda,
    mostrar_error,
    mostrar_info,
)


class DialogoUsuario(QDialog):
    def __init__(self, padre: QWidget | None = None):
        super().__init__(padre)
        self.setWindowTitle("Nueva cuenta de usuario")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cree una cuenta de Secretaría o Administrador."))
        self.usuario = CampoTexto("Usuario", obligatorio=True, maximo=30)
        self.rol = CampoCombo("Rol", ["Secretaria", "Administrador"])
        self.dni = CampoTexto("DNI", obligatorio=True, maximo=8)
        self.nombres = CampoTexto("Nombres", obligatorio=True, maximo=50)
        self.apellidos = CampoTexto("Apellidos", obligatorio=True, maximo=50)
        self.clave = CampoTexto("Contraseña", obligatorio=True, maximo=100)
        self.clave.edicion.setEchoMode(QLineEdit.Password)
        self.confirmar = CampoTexto("Confirmar contraseña", obligatorio=True, maximo=100)
        self.confirmar.edicion.setEchoMode(QLineEdit.Password)
        for campo in (self.usuario, self.rol, self.dni, self.nombres, self.apellidos,
                      self.clave, self.confirmar):
            layout.addWidget(campo)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = boton("Cancelar", "Secundario")
        cancelar.clicked.connect(self.reject)
        crear = boton("Crear cuenta")
        crear.clicked.connect(self.crear)
        botones.addWidget(cancelar)
        botones.addWidget(crear)
        layout.addLayout(botones)

    def crear(self) -> None:
        try:
            usuarios.crear_usuario_rol(
                self.usuario.valor(), self.rol.valor(), self.dni.valor(),
                self.nombres.valor(), self.apellidos.valor(),
                self.clave.valor(), self.confirmar.valor(),
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        mostrar_info(self, "La cuenta fue creada correctamente.")
        self.accept()


class PaginaUsuarios(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        superior = QHBoxLayout()
        superior.addWidget(etiqueta_ayuda(
            "Solo el Administrador puede gestionar las cuentas. Las cuentas de padre se "
            "registran desde la ventana de acceso."
        ), 1)
        nuevo = boton("Nueva cuenta")
        nuevo.clicked.connect(self.crear)
        self.alternar = boton("Activar/Desactivar", "Secundario")
        self.alternar.clicked.connect(self.cambiar_estado)
        actualizar = boton("Actualizar", "Secundario")
        actualizar.clicked.connect(self.actualizar)
        superior.addWidget(nuevo)
        superior.addWidget(self.alternar)
        superior.addWidget(actualizar)
        layout.addLayout(superior)

        self.tabla = Tabla(
            [
                ("Id", "IdUsuario"), ("Usuario", "NombreUsuario"), ("Rol", "Rol"),
                ("Estado", "Estado"), ("DNI", "DNI"), ("Nombres", "Nombres"),
                ("Apellidos", "Apellidos"), ("Registro", "FechaRegistro"),
                ("Último acceso", "UltimoAcceso"),
            ]
        )
        layout.addWidget(self.tabla, 1)

    def actualizar(self) -> None:
        try:
            filas = usuarios.listar_usuarios()
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla.cargar(filas)

    def crear(self) -> None:
        if DialogoUsuario(self).exec() == QDialog.Accepted:
            self.actualizar()

    def cambiar_estado(self) -> None:
        seleccionado = self.tabla.fila_actual()
        if not seleccionado:
            mostrar_info(self, "Seleccione una cuenta.")
            return
        nuevo_estado = "Inactivo" if seleccionado["Estado"] == "Activo" else "Activo"
        if not confirmar(self, f"¿Cambiar el estado de la cuenta a {nuevo_estado}?"):
            return
        try:
            usuarios.cambiar_estado(int(seleccionado["IdUsuario"]), nuevo_estado)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()
