"""Asistente de solicitud de matrícula para el padre/apoderado."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import seguridad
from core.errores import ErrorApp, ErrorValidacion
from core.formatos import GRADOS_INSTRUCCION, NIVELES, TIPOS_ATENCION, TIPOS_IE, grados_de_nivel
from servicios import solicitudes
from ui.comunes.widgets import (
    CampoArea,
    CampoCombo,
    CampoEntero,
    CampoFecha,
    CampoSiNo,
    CampoTexto,
    boton,
    etiqueta_ayuda,
    mostrar_error,
    mostrar_info,
    tarjeta,
    titulo_seccion,
)

TIPOS_DOCUMENTO = ("DNI estudiante", "DNI padre/apoderado", "Constancia de logros", "Otro")


class AsistenteSolicitud(QWidget):
    def __init__(self, solicitud_id: str | None = None):
        super().__init__()
        self.setObjectName("Fondo")
        self.solicitud_id = solicitud_id
        self.confianzas: dict[str, int] = {}
        self.instituciones: list[dict[str, Any]] = []
        self.estudiante_campos: dict[str, QWidget] = {}
        self.padre_campos: dict[str, QWidget] = {}
        self.documentos: list[dict[str, Any]] = []
        self._construir()
        if solicitud_id:
            self.cargar(solicitud_id)

    # ------------------------------------------------------------ construcción
    def _construir(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(10)

        self.indicador = QLabel()
        self.indicador.setObjectName("Subtitulo")
        raiz.addWidget(self.indicador)

        self.pila = QStackedWidget()
        self.pila.addWidget(self._paso_estudiante())
        self.pila.addWidget(self._paso_familia())
        self.pila.addWidget(self._paso_constancia())
        self.pila.addWidget(self._paso_documentos())
        raiz.addWidget(self.pila, 1)

        barra = QWidget()
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(0, 0, 0, 0)
        self.boton_anterior = boton("Anterior", "Secundario")
        self.boton_anterior.clicked.connect(lambda: self.ir_paso(self.pila.currentIndex() - 1))
        self.boton_siguiente = boton("Siguiente")
        self.boton_siguiente.clicked.connect(lambda: self.ir_paso(self.pila.currentIndex() + 1))
        self.boton_guardar = boton("Guardar borrador", "Secundario")
        self.boton_guardar.clicked.connect(lambda: self.guardar(mostrar=True))
        self.boton_enviar = boton("Enviar solicitud", "Exito")
        self.boton_enviar.clicked.connect(self.enviar)
        barra_layout.addWidget(self.boton_anterior)
        barra_layout.addWidget(self.boton_siguiente)
        barra_layout.addStretch(1)
        barra_layout.addWidget(self.boton_guardar)
        barra_layout.addWidget(self.boton_enviar)
        raiz.addWidget(barra)

        self.ir_paso(0)

    def _contenedor_paso(self, titulo: str, subtitulo: str) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        interior = QWidget()
        interior.setObjectName("Fondo")
        layout = QVBoxLayout(interior)
        layout.setContentsMargins(4, 4, 12, 4)
        layout.setSpacing(12)
        layout.addWidget(titulo_seccion(titulo))
        layout.addWidget(etiqueta_ayuda(subtitulo))
        scroll.setWidget(interior)
        return scroll, layout

    def _paso_estudiante(self) -> QWidget:
        scroll, layout = self._contenedor_paso(
            "1. Datos del estudiante",
            "Complete los datos. Puede importarlos desde una imagen o PDF del DNI.",
        )
        basico = QGridLayout()
        self.tipo = CampoCombo("Tipo de solicitud", solicitudes.TIPOS_SOLICITUD)
        self.anio = CampoEntero("Año escolar", 2000, 2100)
        self.anio.set_valor(QDate.currentDate().year())
        self.nivel = CampoCombo("Nivel", NIVELES)
        self.grado = CampoCombo("Grado", grados_de_nivel("Inicial"))
        self.seccion = CampoTexto("Sección", obligatorio=True, maximo=5)
        self.nivel.combo.currentTextChanged.connect(self._actualizar_grados)
        basico.addWidget(self.tipo, 0, 0)
        basico.addWidget(self.anio, 0, 1)
        basico.addWidget(self.nivel, 0, 2)
        basico.addWidget(self.grado, 0, 3)
        basico.addWidget(self.seccion, 0, 4)
        layout.addLayout(basico)

        fila = QHBoxLayout()
        self.boton_ocr = boton("Importar DNI del estudiante (OCR)", "Secundario")
        self.boton_ocr.clicked.connect(lambda: self._importar_dni("estudiante"))
        self.estado_ocr = QLabel("")
        self.estado_ocr.setObjectName("Ayuda")
        fila.addWidget(self.boton_ocr)
        fila.addWidget(self.estado_ocr)
        fila.addStretch(1)
        layout.addLayout(fila)

        campos = QGridLayout()
        definicion = [
            ("DNI", lambda: CampoTexto("DNI", obligatorio=True, maximo=8)),
            ("Sexo", lambda: CampoCombo("Sexo", ["M", "F"], vacio="Seleccione")),
            ("Nombres", lambda: CampoTexto("Nombres", obligatorio=True, maximo=50)),
            ("ApellidoPaterno", lambda: CampoTexto("Apellido paterno", obligatorio=True, maximo=30)),
            ("ApellidoMaterno", lambda: CampoTexto("Apellido materno", obligatorio=True, maximo=30)),
            ("FechaNacimiento", lambda: CampoFecha("Fecha de nacimiento")),
            ("DistritoNacimiento", lambda: CampoTexto("Distrito de nacimiento", obligatorio=True, maximo=30)),
            ("ProvinciaNacimiento", lambda: CampoTexto("Provincia de nacimiento", obligatorio=True, maximo=30)),
            ("DepartamentoNacimiento", lambda: CampoTexto("Departamento de nacimiento", obligatorio=True, maximo=30)),
            ("PaisNacimiento", lambda: CampoTexto("País de nacimiento", maximo=30)),
            ("DomicilioActual", lambda: CampoTexto("Domicilio actual", obligatorio=True, maximo=100)),
            ("DistritoDomicilio", lambda: CampoTexto("Distrito de domicilio", obligatorio=True, maximo=30)),
            ("Celular", lambda: CampoTexto("Celular", maximo=9)),
            ("CorreoElectronico", lambda: CampoTexto("Correo electrónico", maximo=50)),
            ("Religion", lambda: CampoTexto("Religión", maximo=20)),
            ("LugarQueOcupa", lambda: CampoEntero("Lugar que ocupa", 1, 20)),
            ("TipoAtencion", lambda: CampoCombo("Tipo de atención", TIPOS_ATENCION, vacio="(Ninguno)")),
            ("EnfermedadCronica", lambda: CampoTexto("Enfermedad crónica", maximo=50)),
            ("CodigoModularIE", lambda: CampoTexto("Código modular de la I.E. de procedencia", maximo=10)),
            ("DNI_Apoderado", lambda: CampoTexto("DNI del apoderado (si es otra persona)", maximo=8)),
        ]
        for indice, (clave, fabrica) in enumerate(definicion):
            campo = fabrica()
            self.estudiante_campos[clave] = campo
            campos.addWidget(campo, indice // 3, indice % 3)
        for clave, etiqueta, defecto in (
            ("ViveConPadre", "Vive con el padre", False),
            ("ViveConMadre", "Vive con la madre", False),
            ("ElPadreVive", "El padre vive", True),
            ("LaMadreVive", "La madre vive", True),
        ):
            campo = CampoSiNo(etiqueta, defecto)
            self.estudiante_campos[clave] = campo
            campos.addWidget(campo, len(definicion) // 3 + 1, len(definicion) % 3)
        layout.addLayout(campos)
        layout.addStretch(1)
        return scroll

    def _paso_familia(self) -> QWidget:
        scroll, layout = self._contenedor_paso(
            "2. Padre/apoderado y contacto de emergencia",
            "Registre los datos del responsable y del contacto de emergencia.",
        )
        fila = QHBoxLayout()
        self.boton_ocr_padre = boton("Importar DNI del padre (OCR)", "Secundario")
        self.boton_ocr_padre.clicked.connect(lambda: self._importar_dni("padre"))
        fila.addWidget(self.boton_ocr_padre)
        fila.addStretch(1)
        layout.addLayout(fila)

        definicion = [
            ("DNI", lambda: CampoTexto("DNI", obligatorio=True, maximo=8)),
            ("Sexo", lambda: CampoCombo("Sexo", ["M", "F"], vacio="Seleccione")),
            ("Nombres", lambda: CampoTexto("Nombres", obligatorio=True, maximo=50)),
            ("ApellidoPaterno", lambda: CampoTexto("Apellido paterno", obligatorio=True, maximo=30)),
            ("ApellidoMaterno", lambda: CampoTexto("Apellido materno", obligatorio=True, maximo=30)),
            ("FechaNacimiento", lambda: CampoFecha("Fecha de nacimiento")),
            ("OcupacionActual", lambda: CampoTexto("Ocupación actual", maximo=50)),
            ("GradoInstruccion", lambda: CampoCombo("Grado de instrucción", GRADOS_INSTRUCCION, vacio="Seleccione")),
            ("DomicilioActual", lambda: CampoTexto("Domicilio actual", obligatorio=True, maximo=100)),
            ("DistritoDomicilio", lambda: CampoTexto("Distrito de domicilio", obligatorio=True, maximo=30)),
            ("TelefonoFijo", lambda: CampoTexto("Teléfono fijo", maximo=9)),
            ("Celular", lambda: CampoTexto("Celular", obligatorio=True, maximo=9)),
            ("CorreoElectronico", lambda: CampoTexto("Correo electrónico", maximo=50)),
        ]
        campos = QGridLayout()
        for indice, (clave, fabrica) in enumerate(definicion):
            campo = fabrica()
            self.padre_campos[clave] = campo
            campos.addWidget(campo, indice // 3, indice % 3)
        layout.addLayout(campos)

        self.nombre_contacto = CampoTexto("Nombre del contacto de emergencia", obligatorio=True, maximo=110)
        self.celular_contacto = CampoTexto("Celular del contacto", obligatorio=True, maximo=9)
        contacto = QGridLayout()
        contacto.addWidget(self.nombre_contacto, 0, 0)
        contacto.addWidget(self.celular_contacto, 0, 1)
        layout.addLayout(contacto)

        self.otros_padres = CampoTexto("DNI de otros padres/apoderados (separados por coma)", maximo=200)
        self.hermanos_dni = CampoTexto("DNI de hermanos en el colegio (separados por coma)", maximo=200)
        self.nee = CampoTexto("Necesidades educativas especiales (separadas por coma)", maximo=300)
        extra = QGridLayout()
        extra.addWidget(self.otros_padres, 0, 0)
        extra.addWidget(self.hermanos_dni, 0, 1)
        extra.addWidget(self.nee, 0, 2)
        layout.addLayout(extra)

        layout.addWidget(QLabel("¿Tiene hermanos en algún nivel de la institución?"))
        self.hermanos_ie = {}
        fila_ie = QHBoxLayout()
        for nivel in NIVELES:
            casilla = QCheckBox(nivel)
            self.hermanos_ie[nivel] = casilla
            fila_ie.addWidget(casilla)
        fila_ie.addStretch(1)
        layout.addLayout(fila_ie)
        layout.addStretch(1)
        return scroll

    def _paso_constancia(self) -> QWidget:
        scroll, layout = self._contenedor_paso(
            "3. Constancia de logros",
            "Registre el código virtual y los logros de la constancia. Puede importarla por OCR.",
        )
        fila = QHBoxLayout()
        self.boton_ocr_constancia = boton("Importar constancia (OCR)", "Secundario")
        self.boton_ocr_constancia.clicked.connect(self._importar_constancia)
        self.estado_ocr_constancia = QLabel("")
        self.estado_ocr_constancia.setObjectName("Ayuda")
        fila.addWidget(self.boton_ocr_constancia)
        fila.addWidget(self.estado_ocr_constancia)
        fila.addStretch(1)
        layout.addLayout(fila)

        encabezado = QGridLayout()
        self.codigo_virtual = CampoTexto("Código virtual", obligatorio=True, maximo=8)
        self.nivel_constancia = CampoCombo("Nivel educativo de la constancia", NIVELES)
        self.fecha_emision = CampoTexto("Fecha y hora de emisión (AAAA-MM-DD HH:MM)", maximo=20)
        encabezado.addWidget(self.codigo_virtual, 0, 0)
        encabezado.addWidget(self.nivel_constancia, 0, 1)
        encabezado.addWidget(self.fecha_emision, 0, 2)
        layout.addLayout(encabezado)

        self.tabla_logros = QTableWidget(0, 4)
        self.tabla_logros.setHorizontalHeaderLabels(["Año escolar", "Grado cursado", "Código modular I.E.", "Situación final"])
        self.tabla_logros.horizontalHeader().setStretchLastSection(True)
        self.tabla_logros.setMinimumHeight(180)
        layout.addWidget(self.tabla_logros)
        fila_botones = QHBoxLayout()
        agregar = boton("Agregar logro", "Secundario")
        agregar.clicked.connect(lambda: self._agregar_logro())
        quitar = boton("Quitar seleccionado", "Secundario")
        quitar.clicked.connect(self._quitar_logro)
        fila_botones.addWidget(agregar)
        fila_botones.addWidget(quitar)
        fila_botones.addStretch(1)
        layout.addLayout(fila_botones)
        layout.addStretch(1)
        return scroll

    def _paso_documentos(self) -> QWidget:
        scroll, layout = self._contenedor_paso(
            "4. Documentos y envío",
            "Cargue el DNI del estudiante, el DNI del padre/apoderado y la constancia de logros "
            "(imagen JPG/PNG o PDF, hasta 10 MB).",
        )
        self.filas_documentos: dict[str, QLineEdit] = {}
        for tipo in TIPOS_DOCUMENTO:
            fila = QHBoxLayout()
            etiqueta = QLabel(tipo)
            etiqueta.setObjectName("Etiqueta")
            etiqueta.setFixedWidth(170)
            ruta = QLineEdit()
            ruta.setReadOnly(True)
            ruta.setPlaceholderText("Sin archivo")
            seleccionar = boton("Elegir archivo", "Secundario")
            seleccionar.clicked.connect(lambda _=False, t=tipo: self._elegir_documento(t))
            fila.addWidget(etiqueta)
            fila.addWidget(ruta, 1)
            fila.addWidget(seleccionar)
            layout.addLayout(fila)
            self.filas_documentos[tipo] = ruta

        layout.addWidget(titulo_seccion("Documentos cargados"))
        self.lista_documentos = QVBoxLayout()
        layout.addLayout(self.lista_documentos)
        layout.addWidget(titulo_seccion("Resumen"))
        self.resumen = QLabel("")
        self.resumen.setWordWrap(True)
        layout.addWidget(self.resumen)
        layout.addStretch(1)
        return scroll

    # ------------------------------------------------------------ navegación
    def ir_paso(self, indice: int) -> None:
        total = self.pila.count()
        indice = max(0, min(total - 1, indice))
        self.pila.setCurrentIndex(indice)
        self.indicador.setText(f"Paso {indice + 1} de {total}")
        self.boton_anterior.setEnabled(indice > 0)
        self.boton_siguiente.setEnabled(indice < total - 1)
        if indice == total - 1:
            self._refrescar_resumen()

    def _actualizar_grados(self) -> None:
        nivel = self.nivel.valor()
        self.grado.cambiar_opciones(grados_de_nivel(nivel))

    # ------------------------------------------------------------ OCR
    def _importar_dni(self, quien: str) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccione el DNI", "", "Imágenes y PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        if not ruta:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from ocr.motor import leer_documento

            resultado = leer_documento(ruta, "DNI estudiante" if quien == "estudiante" else "DNI padre/apoderado")
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        campos = self.estudiante_campos if quien == "estudiante" else self.padre_campos
        tabla = "ESTUDIANTE" if quien == "estudiante" else "PADRE_APODERADO"
        aplicados = 0
        for clave, (valor, confianza, _origen) in resultado.campos.items():
            columna = clave.split(".", 1)[-1]
            campo = campos.get(columna)
            if campo is None or not valor:
                continue
            self._poner_valor(campo, valor)
            self.confianzas[f"{tabla}.{columna}"] = int(confianza)
            aplicados += 1
        etiqueta = self.estado_ocr if quien == "estudiante" else self.estado_ocr_padre
        etiqueta.setText(f"Se importaron {aplicados} campos. Revise los datos resaltados.")
        self._marcar_confianza(campos)

    def _importar_constancia(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccione la constancia", "", "Imágenes y PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        if not ruta:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from ocr.motor import leer_documento

            resultado = leer_documento(ruta, "Constancia de logros")
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        for clave, (valor, confianza, _origen) in resultado.campos.items():
            columna = clave.split(".", 1)[-1]
            if columna == "CodigoVirtual":
                self.codigo_virtual.set_valor(valor)
            elif columna == "NivelEducativo":
                self.nivel_constancia.set_valor(valor)
            elif columna == "FechaHoraEmision":
                self.fecha_emision.set_valor(str(valor)[:16])
            elif columna == "CodigoModularIE":
                self.instituciones.append({"CodigoModularIE": valor})
            elif columna == "NombreIE":
                if self.instituciones:
                    self.instituciones[-1]["NombreIE"] = valor
            elif columna == "TipoIE":
                if self.instituciones:
                    self.instituciones[-1]["TipoIE"] = valor
            self.confianzas[f"CONSTANCIA.{columna}"] = int(confianza)
        for logro in resultado.logros:
            fila = self.tabla_logros.rowCount()
            self.tabla_logros.insertRow(fila)
            valores = {}
            for clave, (valor, _conf, _origen) in logro.items():
                valores[clave.split(".", 1)[-1]] = valor
            self._escribir_logro(fila, valores)
        self.estado_ocr_constancia.setText(
            f"Se importaron {len(resultado.logros)} logro(s). Revise la información."
        )

    def _poner_valor(self, campo: QWidget, valor: Any) -> None:
        for metodo in ("set_valor",):
            funcion = getattr(campo, metodo, None)
            if callable(funcion):
                funcion(valor)
                return

    def _marcar_confianza(self, campos: dict[str, QWidget]) -> None:
        for clave, campo in campos.items():
            if not hasattr(campo, "edicion"):
                continue
            confianza = self.confianzas.get(f"{self._tabla_de(campos)}.{clave}")
            color = "#D6DEE6"
            if confianza is not None and confianza < 80:
                color = "#E7A33E"
            elif confianza is not None:
                color = "#8BC34A"
            if hasattr(campo.edicion, "setStyleSheet"):
                campo.edicion.setStyleSheet(f"border: 1px solid {color};")

    @staticmethod
    def _tabla_de(campos: dict[str, QWidget]) -> str:
        return "PADRE_APODERADO" if "OcupacionActual" in campos else "ESTUDIANTE"

    # ------------------------------------------------------------ logros
    def _agregar_logro(self) -> None:
        fila = self.tabla_logros.rowCount()
        self.tabla_logros.insertRow(fila)

    def _quitar_logro(self) -> None:
        fila = self.tabla_logros.currentRow()
        if fila >= 0:
            self.tabla_logros.removeRow(fila)

    def _escribir_logro(self, fila: int, valores: dict[str, Any]) -> None:
        orden = ("AñoEscolar", "GradoCursado", "CodigoModularIE", "SituacionFinal")
        for columna, clave in enumerate(orden):
            self.tabla_logros.setItem(fila, columna, QTableWidgetItem(str(valores.get(clave, ""))))

    def _leer_logros(self) -> list[dict[str, Any]]:
        logros = []
        for fila in range(self.tabla_logros.rowCount()):
            valores = []
            for columna in range(4):
                item = self.tabla_logros.item(fila, columna)
                valores.append(item.text().strip() if item else "")
            if not any(valores):
                continue
            logros.append(
                {
                    "AñoEscolar": valores[0], "GradoCursado": valores[1],
                    "CodigoModularIE": valores[2], "SituacionFinal": valores[3],
                }
            )
        return logros

    # ------------------------------------------------------------ documentos
    def _elegir_documento(self, tipo: str) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, f"Seleccione: {tipo}", "", "Imágenes y PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        if not ruta:
            return
        if not self.guardar(mostrar=False):
            return
        try:
            solicitud = solicitudes.agregar_documento(self.solicitud_id, ruta, tipo)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.documentos = solicitud.get("documentos", [])
        self.filas_documentos[tipo].setText(ruta)
        self._refrescar_documentos()

    def _quitar_documento(self, sha256: str) -> None:
        try:
            solicitud = solicitudes.eliminar_documento(self.solicitud_id, sha256)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.documentos = solicitud.get("documentos", [])
        self._refrescar_documentos()

    def _refrescar_documentos(self) -> None:
        while self.lista_documentos.count():
            item = self.lista_documentos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.documentos:
            self.lista_documentos.addWidget(etiqueta_ayuda("Aún no hay documentos cargados."))
            return
        for documento in self.documentos:
            fila = QWidget()
            caja = QHBoxLayout(fila)
            caja.setContentsMargins(0, 0, 0, 0)
            caja.addWidget(QLabel(f"{documento.get('tipo')}: {Path(documento.get('archivo', '')).name}"))
            caja.addStretch(1)
            quitar = boton("Quitar", "Enlace")
            quitar.clicked.connect(lambda _=False, s=documento.get("sha256"): self._quitar_documento(s))
            caja.addWidget(quitar)
            self.lista_documentos.addWidget(fila)

    def _refrescar_resumen(self) -> None:
        total = len(self.documentos)
        self.resumen.setText(
            f"Estudiante: {self.estudiante_campos['Nombres'].valor()} "
            f"{self.estudiante_campos['ApellidoPaterno'].valor()} "
            f"{self.estudiante_campos['ApellidoMaterno'].valor()}\n"
            f"Año: {self.anio.valor()} · {self.nivel.valor()} {self.grado.valor()} "
            f"{self.seccion.valor()}\nDocumentos cargados: {total}"
        )

    # ------------------------------------------------------------ datos
    def _recolectar(self) -> dict[str, Any]:
        estudiante = {clave: campo.valor() for clave, campo in self.estudiante_campos.items()}
        padre = {clave: campo.valor() for clave, campo in self.padre_campos.items()}
        datos = {
            "estudiante": estudiante,
            "padre": padre,
            "contacto": {
                "NombreContactoEmergencia": self.nombre_contacto.valor(),
                "CelularEmergencia": self.celular_contacto.valor(),
            },
            "constancia": {
                "CodigoVirtual": self.codigo_virtual.valor(),
                "NivelEducativo": self.nivel_constancia.valor(),
                "FechaHoraEmision": self.fecha_emision.valor(),
                "logros": self._leer_logros(),
            },
            "padres": [d.strip() for d in self.otros_padres.valor().split(",") if d.strip()],
            "hermanos_dni": [d.strip() for d in self.hermanos_dni.valor().split(",") if d.strip()],
            "nee": [n.strip() for n in self.nee.valor().split(",") if n.strip()],
            "hermanos_ie": [n for n, casilla in self.hermanos_ie.items() if casilla.isChecked()],
            "instituciones": self.instituciones,
            "ocr_confianzas": self.confianzas,
        }
        return datos

    def guardar(self, mostrar: bool = True) -> bool:
        try:
            datos = self._recolectar()
            dni = datos["estudiante"].get("DNI") or ""
            if self.solicitud_id:
                solicitud = solicitudes.actualizar(
                    self.solicitud_id, datos,
                    seccion=self.seccion.valor(),
                    anio=self.anio.valor(),
                    nivel=self.nivel.valor(),
                    grado=self.grado.valor(),
                )
            else:
                self.solicitud_id = solicitudes.crear_borrador(
                    self.tipo.valor(), dni, self.anio.valor(), self.nivel.valor(),
                    self.grado.valor(), self.seccion.valor(), datos,
                )
                solicitud = solicitudes.obtener(self.solicitud_id)
            self.documentos = solicitud.get("documentos", [])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return False
        if mostrar:
            mostrar_info(self, f"Solicitud guardada como borrador ({self.solicitud_id}).")
        return True

    def enviar(self) -> None:
        if not self.guardar(mostrar=False):
            return
        try:
            solicitud = solicitudes.enviar(self.solicitud_id)
        except ErrorApp as exc:
            mostrar_error(self, str(exc), "No se pudo enviar")
            return
        mostrar_info(
            self,
            f"La solicitud {solicitud['id']} fue enviada. La secretaría la revisará.",
            "Solicitud enviada",
        )
        self.solicitud_id = None
        self.confianzas = {}
        self.instituciones = []
        self.documentos = []
        self._limpiar_formularios()
        self.ir_paso(0)

    def _limpiar_formularios(self) -> None:
        for campos in (self.estudiante_campos, self.padre_campos):
            for campo in campos.values():
                if hasattr(campo, "limpiar"):
                    campo.limpiar()
                elif hasattr(campo, "set_valor"):
                    campo.set_valor("")
        self.nombre_contacto.limpiar()
        self.celular_contacto.limpiar()
        self.otros_padres.limpiar()
        self.hermanos_dni.limpiar()
        self.nee.limpiar()
        self.codigo_virtual.limpiar()
        self.fecha_emision.limpiar()
        self.tabla_logros.setRowCount(0)
        for casilla in self.hermanos_ie.values():
            casilla.setChecked(False)
        self._refrescar_documentos()

    def cargar(self, solicitud_id: str) -> None:
        self.solicitud_id = solicitud_id
        try:
            solicitud = solicitudes.obtener(solicitud_id)
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tipo.set_valor(solicitud.get("tipo"))
        self.anio.set_valor(solicitud.get("anio"))
        self.nivel.set_valor(solicitud.get("nivel"))
        self._actualizar_grados()
        self.grado.set_valor(solicitud.get("grado"))
        self.seccion.set_valor(solicitud.get("seccion"))
        datos = solicitud.get("datos") or {}
        for clave, campo in self.estudiante_campos.items():
            if clave in (datos.get("estudiante") or {}):
                self._poner_valor(campo, datos["estudiante"][clave])
        for clave, campo in self.padre_campos.items():
            if clave in (datos.get("padre") or {}):
                self._poner_valor(campo, datos["padre"][clave])
        contacto = datos.get("contacto") or {}
        self.nombre_contacto.set_valor(contacto.get("NombreContactoEmergencia"))
        self.celular_contacto.set_valor(contacto.get("CelularEmergencia"))
        self.otros_padres.set_valor(", ".join(datos.get("padres") or []))
        self.hermanos_dni.set_valor(", ".join(datos.get("hermanos_dni") or []))
        self.nee.set_valor(", ".join(datos.get("nee") or []))
        for nivel in datos.get("hermanos_ie") or []:
            if nivel in self.hermanos_ie:
                self.hermanos_ie[nivel].setChecked(True)
        constancia = datos.get("constancia") or {}
        self.codigo_virtual.set_valor(constancia.get("CodigoVirtual"))
        self.nivel_constancia.set_valor(constancia.get("NivelEducativo"))
        self.fecha_emision.set_valor(constancia.get("FechaHoraEmision"))
        self.tabla_logros.setRowCount(0)
        for logro in constancia.get("logros") or []:
            fila = self.tabla_logros.rowCount()
            self.tabla_logros.insertRow(fila)
            self._escribir_logro(fila, logro)
        self.instituciones = datos.get("instituciones") or []
        self.confianzas = {k: int(v) for k, v in (datos.get("ocr_confianzas") or {}).items()}
        self.documentos = solicitud.get("documentos", [])
        self._refrescar_documentos()
        self.ir_paso(0)


class PaginaAsistente(QWidget):
    """Envuelve el asistente para usarlo como página principal."""

    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.asistente = AsistenteSolicitud()
        layout.addWidget(self.asistente)

    def actualizar(self) -> None:
        return
