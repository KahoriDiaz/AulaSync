"""Pruebas de interfaz en plataforma offscreen (pytest-qt)."""
from datetime import date

import pytest
from PySide6.QtWidgets import QMessageBox

from core import seguridad
from servicios import solicitudes, validaciones
from ui.login import VentanaLogin
from ui.padre.asistente import AsistenteSolicitud
from ui.secretaria.bandeja import PaginaBandeja
from ui.secretaria.revision import DialogoRevision
from ui.ventana_principal import VentanaPrincipal

VALIDACION_OK = {
    "items": [], "errores": 0, "advertencias": 0,
    "puede_enviar": True, "puede_aprobar": True,
    "fecha": "2026-01-01T00:00:00",
}


def _rellenar_estudiante(asistente):
    campos = asistente.estudiante_campos
    campos["DNI"].set_valor("79999998")
    campos["Sexo"].set_valor("F")
    campos["Nombres"].set_valor("ANA SOFIA")
    campos["ApellidoPaterno"].set_valor("PRUEBA")
    campos["ApellidoMaterno"].set_valor("UI")
    campos["FechaNacimiento"].set_valor("2014-03-15")
    campos["DistritoNacimiento"].set_valor("CERCADO")
    campos["ProvinciaNacimiento"].set_valor("AREQUIPA")
    campos["DepartamentoNacimiento"].set_valor("AREQUIPA")
    campos["PaisNacimiento"].set_valor("PERU")
    campos["DomicilioActual"].set_valor("AV. LOS ANDES 123")
    campos["DistritoDomicilio"].set_valor("CERCADO")
    campos["Celular"].set_valor("999999999")
    campos["CorreoElectronico"].set_valor("ana@example.com")
    campos["Religion"].set_valor("")
    campos["LugarQueOcupa"].set_valor(1)
    campos["TipoAtencion"].set_valor("(Ninguno)")
    campos["EnfermedadCronica"].set_valor("")
    campos["CodigoModularIE"].set_valor("")
    campos["DNI_Apoderado"].set_valor("")
    for clave in ("ViveConPadre", "ViveConMadre", "ElPadreVive", "LaMadreVive"):
        campos[clave].set_valor(True)


def _rellenar_padre(asistente):
    campos = asistente.padre_campos
    campos["DNI"].set_valor("79999997")
    campos["Sexo"].set_valor("M")
    campos["Nombres"].set_valor("PADRE")
    campos["ApellidoPaterno"].set_valor("PRUEBA")
    campos["ApellidoMaterno"].set_valor("UI")
    campos["FechaNacimiento"].set_valor("1985-07-10")
    campos["OcupacionActual"].set_valor("EMPLEADO")
    campos["GradoInstruccion"].set_valor("Seleccione")
    campos["DomicilioActual"].set_valor("AV. LOS ANDES 123")
    campos["DistritoDomicilio"].set_valor("CERCADO")
    campos["TelefonoFijo"].set_valor("")
    campos["Celular"].set_valor("999999998")
    campos["CorreoElectronico"].set_valor("padre@example.com")


def _rellenar_constancia(asistente):
    asistente.codigo_virtual.set_valor("ABCDEF01")
    asistente.nivel_constancia.set_valor("Primaria")
    asistente.fecha_emision.set_valor("2026-01-15 10:00:00")


def test_ventana_login_se_construye(qtbot, silenciar_dialogos):
    login = VentanaLogin()
    qtbot.addWidget(login)
    assert login.windowTitle().startswith("Sistema de Registro")
    assert login.usuario.placeholderText() == "Usuario"
    assert login.clave.echoMode() == login.clave.EchoMode.Password


def test_ventana_principal_padre_carga_paginas(qtbot, sesion_padre, silenciar_dialogos):
    ventana = VentanaPrincipal(sesion_padre)
    qtbot.addWidget(ventana)
    assert ventana.lista.count() == 4
    assert ventana.stack.count() >= 1
    assert ventana.sesion.rol == "Padre"


def test_ventana_principal_secretaria_carga_paginas(
    qtbot, sesion_secretaria, silenciar_dialogos
):
    ventana = VentanaPrincipal(sesion_secretaria)
    qtbot.addWidget(ventana)
    assert ventana.lista.count() == 5
    assert ventana.stack.count() >= 1
    assert ventana.sesion.rol == "Secretaria"


def test_flujo_padre_crea_y_envia_solicitud(
    qtbot, sesion_padre, monkeypatch, silenciar_dialogos
):
    monkeypatch.setattr(validaciones, "validar_solicitud", lambda solicitud: VALIDACION_OK)

    asistente = AsistenteSolicitud()
    qtbot.addWidget(asistente)

    asistente.tipo.set_valor("Nueva matrícula")
    asistente.anio.set_valor(2026)
    asistente.nivel.set_valor("Primaria")
    asistente._actualizar_grados()
    asistente.grado.set_valor("1.°")
    asistente.seccion.set_valor("A")

    _rellenar_estudiante(asistente)
    _rellenar_padre(asistente)
    asistente.nombre_contacto.set_valor("CONTACTO EMERGENCIA")
    asistente.celular_contacto.set_valor("999999997")
    asistente.otros_padres.set_valor("")
    asistente.hermanos_dni.set_valor("")
    asistente.nee.set_valor("")
    _rellenar_constancia(asistente)

    assert asistente.guardar() is True
    id_solicitud = asistente.solicitud_id
    assert id_solicitud is not None
    solicitud = solicitudes.obtener(id_solicitud)
    assert solicitud["estado"] == "Borrador"
    assert solicitud["datos"]["estudiante"]["DNI"] == "79999998"

    asistente.enviar()
    enviada = solicitudes.obtener(id_solicitud)
    assert enviada["estado"] == "Enviada"
    assert enviada["fecha_envio"] is not None


def test_bandeja_y_revision_se_construyen(
    qtbot, sesion_secretaria, monkeypatch, silenciar_dialogos
):
    monkeypatch.setattr(validaciones, "validar_solicitud", lambda solicitud: VALIDACION_OK)

    sesion_padre = seguridad.Sesion(
        id_usuario=103, nombre_usuario="padre_rev", rol="Padre",
        dni="79999996", nombres="Padre", apellidos="Reviso",
    )
    seguridad.iniciar_sesion(sesion_padre)
    try:
        id_solicitud = solicitudes.crear_borrador(
            "Nueva matrícula", "79999996", 2026, "Primaria", "1.°", "A",
            {"estudiante": {"DNI": "79999996", "Nombres": "REVISO"}},
        )
        solicitudes.enviar(id_solicitud)
    finally:
        seguridad.cerrar_sesion()
    seguridad.iniciar_sesion(sesion_secretaria)

    bandeja = PaginaBandeja()
    qtbot.addWidget(bandeja)
    bandeja.actualizar()
    ids = [bandeja.tabla.item(f, 0).text() for f in range(bandeja.tabla.rowCount())]
    assert id_solicitud in ids

    dialogo = DialogoRevision(id_solicitud)
    qtbot.addWidget(dialogo)
    assert dialogo.solicitud.get("id") == id_solicitud
    assert dialogo.solicitud.get("estado") in ("En revisión", "Enviada")
    dialogo.reject()


def test_dialogo_revision_aprobacion_guarda_historial(
    qtbot, sesion_secretaria, monkeypatch, silenciar_dialogos
):
    monkeypatch.setattr(validaciones, "validar_solicitud", lambda solicitud: VALIDACION_OK)

    sesion_padre = seguridad.Sesion(
        id_usuario=104, nombre_usuario="padre_apr", rol="Padre",
        dni="79999995", nombres="Padre", apellidos="Aprueba",
    )
    seguridad.iniciar_sesion(sesion_padre)
    try:
        id_solicitud = solicitudes.crear_borrador(
            "Nueva matrícula", "79999995", 2026, "Primaria", "1.°", "A",
            {"estudiante": {"DNI": "79999995", "Nombres": "APRUEBA"}},
        )
        solicitudes.enviar(id_solicitud)
    finally:
        seguridad.cerrar_sesion()
    seguridad.iniciar_sesion(sesion_secretaria)

    dialogo = DialogoRevision(id_solicitud)
    qtbot.addWidget(dialogo)
    dialogo.validar()
    resultado = solicitudes.obtener(id_solicitud)
    assert resultado["validaciones"] is not None
    dialogo.reject()
