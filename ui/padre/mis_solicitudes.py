"""Listado de solicitudes del padre/apoderado."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.errores import ErrorApp
from servicios import solicitudes
from ui.comunes.widgets import (
    Tabla,
    badge_estado,
    boton,
    etiqueta_ayuda,
    mostrar_error,
    mostrar_info,
    tarjeta,
    titulo_seccion,
)
from ui.padre.asistente import AsistenteSolicitud


class DialogoAsistente(QDialog):
    def __init__(self, solicitud_id: str, padre: QWidget | None = None):
        super().__init__(padre)
        self.setWindowTitle(f"Solicitud {solicitud_id}")
        self.resize(1000, 700)
        layout = QVBoxLayout(self)
        self.asistente = AsistenteSolicitud(solicitud_id)
        layout.addWidget(self.asistente, 1)
        cerrar = boton("Cerrar", "Secundario")
        cerrar.clicked.connect(self.accept)
        contenedor = QHBoxLayout()
        contenedor.addStretch(1)
        contenedor.addWidget(cerrar)
        layout.addLayout(contenedor)


class DialogoDetalleSolicitud(QDialog):
    def __init__(self, solicitud: dict[str, Any], padre: QWidget | None = None):
        super().__init__(padre)
        self.solicitud = solicitud
        self.setWindowTitle(f"Solicitud {solicitud.get('id')}")
        self.resize(860, 640)
        layout = QVBoxLayout(self)

        cabecera = QHBoxLayout()
        cabecera.addWidget(QLabel(f"Solicitud {solicitud.get('id')}"))
        cabecera.addStretch(1)
        cabecera.addWidget(badge_estado(solicitud.get("estado", "")))
        layout.addLayout(cabecera)
        layout.addWidget(
            etiqueta_ayuda(
                f"Tipo: {solicitud.get('tipo')} · Año: {solicitud.get('anio')} · "
                f"{solicitud.get('nivel')} {solicitud.get('grado')} {solicitud.get('seccion')}"
            )
        )
        if solicitud.get("observacion"):
            layout.addWidget(etiqueta_ayuda(f"Observación: {solicitud['observacion']}"))

        layout.addWidget(titulo_seccion("Validaciones"))
        self.tabla_validaciones = Tabla(
            [("Sección", "seccion"), ("Campo", "campo"), ("Resultado", "estado"), ("Detalle", "mensaje")]
        )
        layout.addWidget(self.tabla_validaciones)

        layout.addWidget(titulo_seccion("Historial"))
        self.tabla_historial = Tabla(
            [("Fecha", "fecha"), ("Acción", "accion"), ("Estado", "estado_nuevo"), ("Nota", "nota")]
        )
        layout.addWidget(self.tabla_historial)

        botones = QHBoxLayout()
        botones.addStretch(1)
        if solicitud.get("estado") in ("Borrador", "Subsanación"):
            editar = boton("Editar")
            editar.clicked.connect(self.editar)
            botones.addWidget(editar)
        validar = boton("Validar", "Secundario")
        validar.clicked.connect(self.validar)
        botones.addWidget(validar)
        if solicitud.get("estado") in ("Borrador", "Subsanación"):
            enviar = boton("Enviar", "Exito")
            enviar.clicked.connect(self.enviar)
            botones.addWidget(enviar)
        cerrar = boton("Cerrar", "Secundario")
        cerrar.clicked.connect(self.reject)
        botones.addWidget(cerrar)
        layout.addLayout(botones)

        self._cargar()

    def _cargar(self) -> None:
        resultado = self.solicitud.get("validaciones") or {}
        self.tabla_validaciones.cargar(resultado.get("items", []))
        self.tabla_historial.cargar(self.solicitud.get("historial", []))

    def validar(self) -> None:
        try:
            resultado = solicitudes.validar(self.solicitud["id"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.solicitud = solicitudes.obtener(self.solicitud["id"])
        self._cargar()
        mostrar_info(
            self,
            f"Errores: {resultado['errores']} · Advertencias: {resultado['advertencias']}",
            "Resultado de la validación",
        )

    def enviar(self) -> None:
        try:
            solicitud = solicitudes.enviar(self.solicitud["id"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc), "No se pudo enviar")
            return
        self.solicitud = solicitud
        self._cargar()
        mostrar_info(self, "La solicitud fue enviada a la secretaría.", "Solicitud enviada")

    def editar(self) -> None:
        dialogo = DialogoAsistente(self.solicitud["id"], self)
        dialogo.exec()
        self.solicitud = solicitudes.obtener(self.solicitud["id"])
        self._cargar()


class PaginaMisSolicitudes(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        filtros, caja_filtros = tarjeta()
        fila = QHBoxLayout()
        self.estado = QLabel("Todas")
        self.boton_todas = boton("Ver todas", "Secundario")
        self.boton_todas.clicked.connect(self.actualizar)
        fila.addWidget(QLabel("Mis solicitudes"))
        fila.addStretch(1)
        self.boton_nueva = boton("Nueva solicitud")
        self.boton_nueva.clicked.connect(self.nueva)
        fila.addWidget(self.boton_nueva)
        caja_filtros.addLayout(fila)
        layout.addWidget(filtros)

        self.tabla = Tabla(
            [
                ("ID", "id"), ("Tipo", "tipo"), ("Estudiante", "estudiante"),
                ("Año", "anio"), ("Nivel", "nivel"), ("Grado", "grado"),
                ("Estado", "estado"), ("Creada", "fecha_creacion"),
            ]
        )
        self.tabla.doubleClicked.connect(self.abrir)
        layout.addWidget(self.tabla, 1)

        acciones = QHBoxLayout()
        abrir = boton("Abrir", "Secundario")
        abrir.clicked.connect(self.abrir)
        acciones.addWidget(abrir)
        acciones.addStretch(1)
        layout.addLayout(acciones)

    def actualizar(self) -> None:
        try:
            propias = solicitudes.listar(solo_propias=True)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        filas = []
        for solicitud in propias:
            est = solicitud.get("datos", {}).get("estudiante") or {}
            nombre = " ".join(
                filtro for filtro in (
                    est.get("ApellidoPaterno"), est.get("ApellidoMaterno"), est.get("Nombres")
                ) if filtro
            )
            filas.append(
                {
                    "id": solicitud.get("id"),
                    "tipo": solicitud.get("tipo"),
                    "estudiante": nombre or solicitud.get("estudiante_dni", ""),
                    "anio": solicitud.get("anio"),
                    "nivel": solicitud.get("nivel"),
                    "grado": solicitud.get("grado"),
                    "estado": solicitud.get("estado"),
                    "fecha_creacion": str(solicitud.get("fecha_creacion", ""))[:16],
                }
            )
        self.tabla.cargar(filas)

    def _seleccionada(self) -> str | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            mostrar_info(self, "Seleccione una solicitud de la lista.")
            return None
        return self.tabla.item(fila, 0).text()

    def abrir(self) -> None:
        id_solicitud = self._seleccionada()
        if not id_solicitud:
            return
        try:
            solicitud = solicitudes.obtener(id_solicitud)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        DialogoDetalleSolicitud(solicitud, self).exec()
        self.actualizar()

    def nueva(self) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Nueva solicitud de matrícula")
        dialogo.resize(1000, 700)
        caja = QVBoxLayout(dialogo)
        asistente = AsistenteSolicitud()
        caja.addWidget(asistente, 1)
        cerrar = boton("Cerrar", "Secundario")
        cerrar.clicked.connect(dialogo.accept)
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(cerrar)
        caja.addLayout(fila)
        dialogo.exec()
        self.actualizar()
