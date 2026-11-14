"""Gestión de datos: estudiantes, padres, instituciones y constancias."""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.errores import ErrorApp
from core.formatos import GRADOS_INSTRUCCION, NIVELES, TIPOS_ATENCION, TIPOS_IE, grados_de_nivel
from servicios import constancias, contactos, estudiantes, instituciones, padres
from ui.comunes.widgets import (
    CampoCombo,
    CampoEntero,
    CampoFecha,
    CampoSiNo,
    CampoTexto,
    Tabla,
    boton,
    confirmar,
    etiqueta_ayuda,
    mostrar_error,
    mostrar_info,
)


def _fila(*widgets: QWidget) -> QWidget:
    contenedor = QWidget()
    caja = QHBoxLayout(contenedor)
    caja.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        caja.addWidget(widget)
    return contenedor


class _DialogoBase(QDialog):
    def __init__(self, titulo: str, padre: QWidget | None = None, ancho: int = 720):
        super().__init__(padre)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(ancho)
        self.raiz = QVBoxLayout(self)
        self.campos: dict[str, QWidget] = {}

    def agregar_campos(self, definicion: list[tuple[str, QWidget]], columnas: int = 3) -> None:
        cuadricula = QGridLayout()
        for indice, (clave, widget) in enumerate(definicion):
            self.campos[clave] = widget
            cuadricula.addWidget(widget, indice // columnas, indice % columnas)
        self.raiz.addLayout(cuadricula)

    def agregar_botones(self, aceptar: str = "Guardar") -> None:
        fila = QHBoxLayout()
        fila.addStretch(1)
        cancelar = boton("Cancelar", "Secundario")
        cancelar.clicked.connect(self.reject)
        guardar = boton(aceptar)
        guardar.clicked.connect(self.accept)
        fila.addWidget(cancelar)
        fila.addWidget(guardar)
        self.raiz.addLayout(fila)

    def valores(self) -> dict[str, Any]:
        return {clave: campo.valor() for clave, campo in self.campos.items()}

    def poner(self, valores: dict[str, Any]) -> None:
        for clave, valor in valores.items():
            campo = self.campos.get(clave)
            if campo is not None and hasattr(campo, "set_valor"):
                campo.set_valor(valor)


class DialogoPadre(_DialogoBase):
    def __init__(self, padre: QWidget | None = None, datos: dict[str, Any] | None = None):
        super().__init__("Padre/apoderado", padre)
        self.agregar_campos(
            [
                ("DNI", CampoTexto("DNI", obligatorio=True, maximo=8)),
                ("Sexo", CampoCombo("Sexo", ["M", "F"], vacio="Seleccione")),
                ("Nombres", CampoTexto("Nombres", obligatorio=True, maximo=50)),
                ("ApellidoPaterno", CampoTexto("Apellido paterno", obligatorio=True, maximo=30)),
                ("ApellidoMaterno", CampoTexto("Apellido materno", obligatorio=True, maximo=30)),
                ("FechaNacimiento", CampoFecha("Fecha de nacimiento")),
                ("OcupacionActual", CampoTexto("Ocupación", maximo=50)),
                ("GradoInstruccion", CampoCombo("Grado de instrucción", GRADOS_INSTRUCCION, vacio="Seleccione")),
                ("DomicilioActual", CampoTexto("Domicilio", obligatorio=True, maximo=100)),
                ("DistritoDomicilio", CampoTexto("Distrito", obligatorio=True, maximo=30)),
                ("TelefonoFijo", CampoTexto("Teléfono fijo", maximo=9)),
                ("Celular", CampoTexto("Celular", obligatorio=True, maximo=9)),
                ("CorreoElectronico", CampoTexto("Correo", maximo=50)),
            ]
        )
        self.agregar_botones()
        if datos:
            self.poner(datos)
            self.campos["DNI"].set_solo_lectura(True)


class DialogoInstitucion(_DialogoBase):
    def __init__(self, padre: QWidget | None = None, datos: dict[str, Any] | None = None):
        super().__init__("Institución educativa", padre, 520)
        self.agregar_campos(
            [
                ("CodigoModularIE", CampoTexto("Código modular", obligatorio=True, maximo=10)),
                ("NombreIE", CampoTexto("Nombre de la institución", maximo=50)),
                ("TipoIE", CampoCombo("Tipo", TIPOS_IE, vacio="(Sin especificar)")),
            ],
            columnas=1,
        )
        self.agregar_botones()
        if datos:
            self.poner(datos)
            self.campos["CodigoModularIE"].set_solo_lectura(True)


class DialogoEstudiante(_DialogoBase):
    def __init__(self, padre: QWidget | None = None, datos: dict[str, Any] | None = None):
        super().__init__("Estudiante", padre, 900)
        self.contactos = contactos.listar_contactos()
        self.agregar_campos(
            [
                ("DNI", CampoTexto("DNI", obligatorio=True, maximo=8)),
                ("Sexo", CampoCombo("Sexo", ["M", "F"], vacio="Seleccione")),
                ("Nombres", CampoTexto("Nombres", obligatorio=True, maximo=50)),
                ("ApellidoPaterno", CampoTexto("Apellido paterno", obligatorio=True, maximo=30)),
                ("ApellidoMaterno", CampoTexto("Apellido materno", obligatorio=True, maximo=30)),
                ("FechaNacimiento", CampoFecha("Fecha de nacimiento")),
                ("DistritoNacimiento", CampoTexto("Distrito nacimiento", obligatorio=True, maximo=30)),
                ("ProvinciaNacimiento", CampoTexto("Provincia nacimiento", obligatorio=True, maximo=30)),
                ("DepartamentoNacimiento", CampoTexto("Departamento nacimiento", obligatorio=True, maximo=30)),
                ("PaisNacimiento", CampoTexto("País de nacimiento", maximo=30)),
                ("DomicilioActual", CampoTexto("Domicilio", obligatorio=True, maximo=100)),
                ("DistritoDomicilio", CampoTexto("Distrito domicilio", obligatorio=True, maximo=30)),
                ("Celular", CampoTexto("Celular", maximo=9)),
                ("CorreoElectronico", CampoTexto("Correo", maximo=50)),
                ("Religion", CampoTexto("Religión", maximo=20)),
                ("LugarQueOcupa", CampoEntero("Lugar que ocupa", 1, 20)),
                ("TipoAtencion", CampoCombo("Tipo de atención", TIPOS_ATENCION, vacio="(Ninguno)")),
                ("EnfermedadCronica", CampoTexto("Enfermedad crónica", maximo=50)),
                ("CodigoModularIE", CampoTexto("Código modular I.E.", maximo=10)),
                ("DNI_Apoderado", CampoTexto("DNI del apoderado", maximo=8)),
                ("ViveConPadre", CampoSiNo("Vive con el padre")),
                ("ViveConMadre", CampoSiNo("Vive con la madre")),
                ("ElPadreVive", CampoSiNo("El padre vive", True)),
                ("LaMadreVive", CampoSiNo("La madre vive", True)),
            ]
        )
        self.contacto_combo = QComboBox()
        self.contacto_combo.addItem("— Seleccione un contacto existente —", None)
        for contacto in self.contactos:
            self.contacto_combo.addItem(
                f"{contacto['NombreContactoEmergencia']} ({contacto['CelularEmergencia']})",
                contacto["IdContactoEmergencia"],
            )
        self.nuevo_nombre = CampoTexto("O cree un contacto nuevo: nombre", maximo=110)
        self.nuevo_celular = CampoTexto("Celular del contacto nuevo", maximo=9)
        self.raiz.addWidget(QLabel("Contacto de emergencia"))
        self.raiz.addWidget(self.contacto_combo)
        self.raiz.addWidget(self.nuevo_nombre)
        self.raiz.addWidget(self.nuevo_celular)
        self.padres_dni = CampoTexto("DNI de padres vinculados (separados por coma)", maximo=200)
        self.raiz.addWidget(self.padres_dni)
        self.agregar_botones()
        self.datos_actuales = datos or {}
        if datos:
            self.poner(datos)
            self.campos["DNI"].set_solo_lectura(True)
            if datos.get("IdContactoEmergencia"):
                indice = self.contacto_combo.findData(datos["IdContactoEmergencia"])
                if indice >= 0:
                    self.contacto_combo.setCurrentIndex(indice)
            try:
                vinculados = estudiantes.padres_de_estudiante(datos["DNI"])
                self.padres_dni.set_valor(", ".join(p["DNI"] for p in vinculados))
            except ErrorApp:
                pass

    def valores(self) -> dict[str, Any]:
        datos = super().valores()
        datos["IdContactoEmergencia"] = self.contacto_combo.currentData()
        return datos

    def contacto_nuevo(self) -> dict[str, Any] | None:
        nombre = self.nuevo_nombre.valor()
        celular = self.nuevo_celular.valor()
        if nombre or celular:
            return {"NombreContactoEmergencia": nombre, "CelularEmergencia": celular}
        return None


class DialogoConstancia(_DialogoBase):
    def __init__(self, padre: QWidget | None = None, datos: dict[str, Any] | None = None):
        super().__init__("Constancia de logros", padre, 760)
        self.agregar_campos(
            [
                ("CodigoVirtual", CampoTexto("Código virtual", obligatorio=True, maximo=8)),
                ("DNI_Estudiante", CampoTexto("DNI del estudiante", obligatorio=True, maximo=8)),
                ("NivelEducativo", CampoCombo("Nivel educativo", NIVELES)),
                ("FechaHoraEmision", CampoTexto("Fecha y hora de emisión", maximo=20)),
            ],
            columnas=2,
        )
        self.raiz.addWidget(QLabel("Logros"))
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Año", "Grado", "Código modular I.E.", "Situación final"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.raiz.addWidget(self.tabla)
        fila = QHBoxLayout()
        agregar = boton("Agregar logro", "Secundario")
        agregar.clicked.connect(lambda: self.tabla.insertRow(self.tabla.rowCount()))
        quitar = boton("Quitar seleccionado", "Secundario")
        quitar.clicked.connect(self._quitar)
        fila.addWidget(agregar)
        fila.addWidget(quitar)
        fila.addStretch(1)
        self.raiz.addLayout(fila)
        self.agregar_botones()
        if datos:
            self.poner(datos)
            self.campos["CodigoVirtual"].set_solo_lectura(True)
            for logro in datos.get("logros", []):
                indice = self.tabla.rowCount()
                self.tabla.insertRow(indice)
                for columna, clave in enumerate(
                    ("AñoEscolar", "GradoCursado", "CodigoModularIE", "SituacionFinal")
                ):
                    self.tabla.setItem(indice, columna, QTableWidgetItem(str(logro.get(clave, ""))))

    def _quitar(self) -> None:
        if self.tabla.currentRow() >= 0:
            self.tabla.removeRow(self.tabla.currentRow())

    def logros(self) -> list[dict[str, Any]]:
        salida = []
        for fila in range(self.tabla.rowCount()):
            valores = [
                (self.tabla.item(fila, columna).text().strip() if self.tabla.item(fila, columna) else "")
                for columna in range(4)
            ]
            if not any(valores):
                continue
            salida.append(
                {
                    "AñoEscolar": valores[0], "GradoCursado": valores[1],
                    "CodigoModularIE": valores[2], "SituacionFinal": valores[3],
                }
            )
        return salida


class _TablaGestion(QWidget):
    columnas: list[tuple[str, str]] = []

    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(10, 10, 10, 10)
        superior = QHBoxLayout()
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar…")
        self.busqueda.returnPressed.connect(self.actualizar)
        buscar = boton("Buscar")
        buscar.clicked.connect(self.actualizar)
        self.nuevo = boton("Nuevo")
        self.nuevo.clicked.connect(self.crear)
        self.editar = boton("Editar", "Secundario")
        self.editar.clicked.connect(self.editar_registro)
        self.eliminar = boton("Eliminar", "Peligro")
        self.eliminar.clicked.connect(self.eliminar_registro)
        superior.addWidget(self.busqueda, 1)
        superior.addWidget(buscar)
        superior.addWidget(self.nuevo)
        superior.addWidget(self.editar)
        superior.addWidget(self.eliminar)
        self.layout_principal.addLayout(superior)
        self.tabla = Tabla(self.columnas)
        self.tabla.doubleClicked.connect(self.editar_registro)
        self.layout_principal.addWidget(self.tabla, 1)

    def actualizar(self) -> None:
        raise NotImplementedError

    def crear(self) -> None:
        raise NotImplementedError

    def editar_registro(self) -> None:
        raise NotImplementedError

    def eliminar_registro(self) -> None:
        raise NotImplementedError

    def _seleccionado(self) -> dict[str, Any] | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            mostrar_info(self, "Seleccione un registro.")
            return None
        return self.tabla.fila_actual()


class TabEstudiantes(_TablaGestion):
    columnas = [
        ("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
        ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres"),
        ("Nacimiento", "FechaNacimiento"), ("Distrito", "DistritoDomicilio"),
        ("Contacto", "NombreContactoEmergencia"),
    ]

    def actualizar(self) -> None:
        try:
            filas = estudiantes.listar_estudiantes(self.busqueda.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla.cargar(filas)

    def crear(self) -> None:
        dialogo = DialogoEstudiante(self)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            estudiantes.crear_estudiante(
                dialogo.valores(),
                contacto_nuevo=dialogo.contacto_nuevo(),
                padres=[d.strip() for d in dialogo.padres_dni.valor().split(",") if d.strip()],
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def editar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado:
            return
        try:
            datos = estudiantes.obtener_estudiante(seleccionado["DNI"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        dialogo = DialogoEstudiante(self, datos)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            estudiantes.actualizar_estudiante(
                seleccionado["DNI"], dialogo.valores(),
                contacto_nuevo=dialogo.contacto_nuevo(),
                padres=[d.strip() for d in dialogo.padres_dni.valor().split(",") if d.strip()],
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def eliminar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado or not confirmar(self, "¿Eliminar el estudiante seleccionado?"):
            return
        try:
            estudiantes.eliminar_estudiante(seleccionado["DNI"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()


class TabPadres(_TablaGestion):
    columnas = [
        ("DNI", "DNI"), ("Apellido paterno", "ApellidoPaterno"),
        ("Apellido materno", "ApellidoMaterno"), ("Nombres", "Nombres"),
        ("Celular", "Celular"), ("Distrito", "DistritoDomicilio"),
    ]

    def actualizar(self) -> None:
        try:
            filas = padres.listar_padres(self.busqueda.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla.cargar(filas)

    def crear(self) -> None:
        dialogo = DialogoPadre(self)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            padres.crear_padre(dialogo.valores())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def editar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado:
            return
        try:
            datos = padres.obtener_padre(seleccionado["DNI"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        dialogo = DialogoPadre(self, datos)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            padres.actualizar_padre(seleccionado["DNI"], dialogo.valores())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def eliminar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado or not confirmar(self, "¿Eliminar el padre/apoderado seleccionado?"):
            return
        try:
            padres.eliminar_padre(seleccionado["DNI"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()


class TabInstituciones(_TablaGestion):
    columnas = [
        ("Código modular", "CodigoModularIE"), ("Nombre", "NombreIE"), ("Tipo", "TipoIE"),
    ]

    def actualizar(self) -> None:
        try:
            filas = instituciones.listar_instituciones(self.busqueda.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla.cargar(filas)

    def crear(self) -> None:
        dialogo = DialogoInstitucion(self)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            instituciones.crear_institucion(dialogo.valores())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def editar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado:
            return
        try:
            datos = instituciones.obtener_institucion(seleccionado["CodigoModularIE"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        dialogo = DialogoInstitucion(self, datos)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            instituciones.actualizar_institucion(seleccionado["CodigoModularIE"], dialogo.valores())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def eliminar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado or not confirmar(self, "¿Eliminar la institución seleccionada?"):
            return
        try:
            instituciones.eliminar_institucion(seleccionado["CodigoModularIE"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()


class TabConstancias(_TablaGestion):
    columnas = [
        ("Código", "CodigoVirtual"), ("DNI estudiante", "DNI_Estudiante"),
        ("Apellido paterno", "ApellidoPaterno"), ("Nombres", "Nombres"),
        ("Nivel", "NivelEducativo"), ("Emisión", "FechaHoraEmision"),
        ("Logros", "TotalLogros"),
    ]

    def actualizar(self) -> None:
        try:
            filas = constancias.listar_constancias(self.busqueda.text())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.tabla.cargar(filas)

    def crear(self) -> None:
        dialogo = DialogoConstancia(self)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            constancias.crear_constancia(dialogo.valores(), dialogo.logros())
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def editar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado:
            return
        try:
            datos = constancias.obtener_constancia(seleccionado["CodigoVirtual"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        dialogo = DialogoConstancia(self, datos)
        if dialogo.exec() != QDialog.Accepted:
            return
        try:
            constancias.actualizar_constancia(
                seleccionado["CodigoVirtual"], dialogo.valores(), dialogo.logros()
            )
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()

    def eliminar_registro(self) -> None:
        seleccionado = self._seleccionado()
        if not seleccionado or not confirmar(self, "¿Eliminar la constancia seleccionada?"):
            return
        try:
            constancias.eliminar_constancia(seleccionado["CodigoVirtual"])
        except ErrorApp as exc:
            mostrar_error(self, str(exc))
            return
        self.actualizar()


class PaginaCatalogos(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fondo")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(TabEstudiantes(), "Estudiantes")
        self.tabs.addTab(TabPadres(), "Padres/apoderados")
        self.tabs.addTab(TabInstituciones(), "Instituciones")
        self.tabs.addTab(TabConstancias(), "Constancias")
        self.tabs.currentChanged.connect(self._actualizar_pestana)
        layout.addWidget(self.tabs)

    def _actualizar_pestana(self, indice: int) -> None:
        pagina = self.tabs.widget(indice)
        if hasattr(pagina, "actualizar"):
            try:
                pagina.actualizar()
            except ErrorApp as exc:
                mostrar_error(self, str(exc))

    def actualizar(self) -> None:
        self._actualizar_pestana(self.tabs.currentIndex())
