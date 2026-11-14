"""Perfil del padre/apoderado."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from core import seguridad
from core.db import consultar
from core.errores import ErrorApp
from ui.comunes.widgets import Tabla, etiqueta_ayuda, tarjeta, titulo_seccion


class PaginaPerfilPadre(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(14)
        self.tarjeta_datos, self.caja = tarjeta()
        self.layout_principal.addWidget(self.tarjeta_datos)

        self.tarjeta_hijos, self.caja_hijos = tarjeta()
        self.caja_hijos.addWidget(titulo_seccion("Estudiantes a mi cargo"))
        self.tabla = Tabla(
            [("DNI", "DNI"), ("Estudiante", "Estudiante"), ("Nacimiento", "FechaNacimiento"),
             ("Distrito", "DistritoDomicilio")]
        )
        self.caja_hijos.addWidget(self.tabla)
        self.layout_principal.addWidget(self.tarjeta_hijos)
        self.layout_principal.addStretch(1)

    def actualizar(self) -> None:
        while self.caja.count():
            item = self.caja.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sesion = seguridad.sesion_actual()
        if not sesion:
            return
        self.caja.addWidget(titulo_seccion("Datos de la cuenta"))
        cuadricula = QGridLayout()
        datos = [
            ("Usuario", sesion.nombre_usuario), ("Nombre", sesion.nombre_completo),
            ("Rol", sesion.rol), ("DNI", sesion.dni),
        ]
        for indice, (etiqueta, valor) in enumerate(datos):
            titulo = QLabel(etiqueta)
            titulo.setObjectName("Etiqueta")
            cuadricula.addWidget(titulo, indice // 2, (indice % 2) * 2)
            cuadricula.addWidget(QLabel(valor), indice // 2, (indice % 2) * 2 + 1)
        self.caja.addLayout(cuadricula)

        try:
            filas = consultar(
                "SELECT e.DNI, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', "
                "e.Nombres) AS Estudiante, e.FechaNacimiento, e.DistritoDomicilio "
                "FROM ESTUDIANTE e WHERE e.DNI_Apoderado = %s "
                "OR EXISTS (SELECT 1 FROM TIENE_PADRES tp WHERE tp.DNI_Estudiante = e.DNI "
                "AND tp.DNI_Padre = %s) ORDER BY e.ApellidoPaterno",
                (sesion.dni, sesion.dni),
            )
            self.tabla.cargar(filas)
            if not filas:
                self.caja_hijos.addWidget(
                    etiqueta_ayuda("Todavía no hay estudiantes registrados a su nombre.")
                )
        except ErrorApp as exc:
            self.tabla.cargar([])
            self.caja_hijos.addWidget(etiqueta_ayuda(str(exc)))
