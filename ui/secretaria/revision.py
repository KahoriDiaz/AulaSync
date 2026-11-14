"""Revisión de una solicitud por parte de la secretaría."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.almacen import Almacen
from core.errores import ErrorApp
from servicios import aprobacion, solicitudes
from ui.comunes.widgets import (
    Tabla,
    badge_estado,
    boton,
    confirmar,
    etiqueta_ayuda,
    mostrar_error,
    mostrar_info,
    tarjeta,
    titulo_seccion,
)


def _dato(datos: dict[str, Any], grupo: str, campo: str, defecto: str = "—") -> str:
    valor = (datos.get(grupo) or {}).get(campo)
    return str(valor) if valor not in (None, "") else defecto


class DialogoRevision(QDialog):
    def __init__(self, id_solicitud: str, padre: QWidget | None = None):
        super().__init__(padre)
        self.id_solicitud = id_solicitud
        self.setWindowTitle(f"Revisión de la solicitud {id_solicitud}")
        self.resize(1040, 720)
        try:
            if solicitudes.obtener(id_solicitud).get("estado") == "Enviada":
                solicitudes.marcar_en_revision(id_solicitud)
            self.solicitud = solicitudes.obtener(id_solicitud)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            self.solicitud = {}
        self._construir()

    # ------------------------------------------------------------ interfaz
    def _construir(self) -> None:
        raiz = QVBoxLayout(self)
        cabecera = QHBoxLayout()
        titulo = QLabel(f"Solicitud {self.solicitud.get('id', '')}")
        titulo.setObjectName("Subtitulo")
        cabecera.addWidget(titulo)
        cabecera.addStretch(1)
        cabecera.addWidget(badge_estado(self.solicitud.get("estado", "")))
        raiz.addLayout(cabecera)
        raiz.addWidget(
            etiqueta_ayuda(
                f"Tipo: {self.solicitud.get('tipo')} · Año: {self.solicitud.get('anio')} · "
                f"{self.solicitud.get('nivel')} {self.solicitud.get('grado')} "
                f"{self.solicitud.get('seccion')} · Padre: "
                f"{self.solicitud.get('padre', {}).get('nombre', '')}"
            )
        )

        columnas = QHBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        caja = QVBoxLayout(contenido)
        caja.addWidget(self._panel_datos())
        caja.addWidget(self._panel_documentos())
        caja.addWidget(self._panel_historial())
        caja.addStretch(1)
        scroll.setWidget(contenido)
        columnas.addWidget(scroll, 3)
        columnas.addWidget(self._panel_validaciones(), 2)
        raiz.addLayout(columnas, 1)

        acciones = QHBoxLayout()
        validar = boton("Validar", "Secundario")
        validar.clicked.connect(self.validar)
        acciones.addWidget(validar)
        acciones.addStretch(1)
        subsanar = boton("Solicitar subsanación", "Secundario")
        subsanar.clicked.connect(self.subsanar)
        acciones.addWidget(subsanar)
        rechazar = boton("Rechazar", "Peligro")
        rechazar.clicked.connect(self.rechazar)
        acciones.addWidget(rechazar)
        aprobar = boton("Aprobar", "Exito")
        aprobar.clicked.connect(self.aprobar)
        acciones.addWidget(aprobar)
        cerrar = boton("Cerrar", "Secundario")
        cerrar.clicked.connect(self.reject)
        acciones.addWidget(cerrar)
        raiz.addLayout(acciones)
        self._refrescar()

    def _panel_datos(self) -> QWidget:
        panel, caja = tarjeta()
        caja.addWidget(titulo_seccion("Datos declarados"))
        datos = self.solicitud.get("datos") or {}
        cuadricula = QGridLayout()
        filas = [
            ("Estudiante", "estudiante", "DNI", "Nombres"),
            ("Nacimiento", "estudiante", "FechaNacimiento", "Sexo"),
            ("Domicilio", "estudiante", "DomicilioActual", "DistritoDomicilio"),
            ("Padre/apoderado", "padre", "DNI", "Nombres"),
            ("Contacto", "contacto", "NombreContactoEmergencia", "CelularEmergencia"),
            ("Constancia", "constancia", "CodigoVirtual", "NivelEducativo"),
        ]
        for indice, (titulo, grupo, campo1, campo2) in enumerate(filas):
            etiqueta = QLabel(titulo)
            etiqueta.setObjectName("Etiqueta")
            cuadricula.addWidget(etiqueta, indice, 0)
            cuadricula.addWidget(
                QLabel(f"{_dato(datos, grupo, campo1)} · {_dato(datos, grupo, campo2)}"),
                indice, 1,
            )
        caja.addLayout(cuadricula)
        logros = (datos.get("constancia") or {}).get("logros") or []
        caja.addWidget(etiqueta_ayuda(f"Logros declarados: {len(logros)}"))
        for logro in logros:
            caja.addWidget(
                etiqueta_ayuda(
                    f"• {logro.get('AñoEscolar')} · {logro.get('GradoCursado')} · "
                    f"{logro.get('CodigoModularIE')} · {logro.get('SituacionFinal')}"
                )
            )
        return panel

    def _panel_documentos(self) -> QWidget:
        panel, caja = tarjeta()
        caja.addWidget(titulo_seccion("Documentos"))
        documentos = self.solicitud.get("documentos") or []
        if not documentos:
            caja.addWidget(etiqueta_ayuda("No hay documentos cargados."))
            return panel
        almacen = Almacen()
        for documento in documentos:
            fila = QHBoxLayout()
            fila.addWidget(QLabel(f"{documento.get('tipo')} · {documento.get('mime')} · "
                                  f"{documento.get('bytes', 0)} bytes"))
            fila.addStretch(1)
            abrir = boton("Abrir", "Enlace")
            abrir.clicked.connect(lambda _=False, d=documento: self._abrir_documento(almacen, d))
            fila.addWidget(abrir)
            contenedor = QWidget()
            contenedor.setLayout(fila)
            caja.addWidget(contenedor)
        return panel

    def _panel_historial(self) -> QWidget:
        panel, caja = tarjeta()
        caja.addWidget(titulo_seccion("Historial"))
        tabla = Tabla(
            [("Fecha", "fecha"), ("Acción", "accion"), ("Estado", "estado_nuevo"), ("Nota", "nota")]
        )
        tabla.cargar(self.solicitud.get("historial", []))
        caja.addWidget(tabla)
        return panel

    def _panel_validaciones(self) -> QWidget:
        panel, caja = tarjeta()
        caja.addWidget(titulo_seccion("Resultado de las validaciones"))
        self.resumen_validacion = QLabel("")
        self.resumen_validacion.setWordWrap(True)
        caja.addWidget(self.resumen_validacion)
        self.tabla_validaciones = Tabla(
            [("Campo", "campo"), ("Resultado", "estado"), ("Detalle", "mensaje")]
        )
        caja.addWidget(self.tabla_validaciones)
        return panel

    def _refrescar(self) -> None:
        self.tabla_validaciones.cargar([])
        self.resumen_validacion.setText("Pulse “Validar” para ejecutar las comprobaciones.")

    def _abrir_documento(self, almacen: Almacen, documento: dict[str, Any]) -> None:
        try:
            ruta = almacen.ruta_documento(self.solicitud["id"], documento)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))

    # ------------------------------------------------------------ acciones
    def validar(self) -> None:
        try:
            resultado = solicitudes.guardar_validaciones(self.id_solicitud)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.solicitud = solicitudes.obtener(self.id_solicitud)
        self.tabla_validaciones.cargar(resultado.get("items", []))
        self.resumen_validacion.setText(
            f"Errores: {resultado['errores']} · Advertencias: {resultado['advertencias']}"
        )

    def aprobar(self) -> None:
        if not confirmar(
            self,
            "¿Confirma la aprobación? Los datos se registrarán y los archivos se eliminarán.",
            "Aprobar solicitud",
        ):
            return
        try:
            aprobacion.aprobar(self.id_solicitud)
        except ErrorApp as exc:
            mostrar_error(self, str(exc), "No se pudo aprobar")
            return
        mostrar_info(self, "La matrícula fue registrada correctamente.", "Solicitud aprobada")
        self.accept()

    def rechazar(self) -> None:
        motivo, aceptado = QInputDialog.getMultiLineText(
            self, "Rechazar solicitud", "Motivo del rechazo:"
        )
        if not aceptado or not motivo.strip():
            return
        try:
            aprobacion.rechazar(self.id_solicitud, motivo)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        mostrar_info(self, "La solicitud fue rechazada.")
        self.accept()

    def subsanar(self) -> None:
        observacion, aceptado = QInputDialog.getMultiLineText(
            self, "Solicitar subsanación", "Indique qué debe corregir el padre/apoderado:"
        )
        if not aceptado or not observacion.strip():
            return
        try:
            solicitudes.solicitar_subsanacion(self.id_solicitud, observacion)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        mostrar_info(self, "Se solicitó la subsanación al padre/apoderado.")
        self.accept()
