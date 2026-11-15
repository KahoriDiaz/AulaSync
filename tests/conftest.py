"""Configuración de pruebas de interfaz (offscreen)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QDesktopServices  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from core import seguridad  # noqa: E402
from core.config import config  # noqa: E402


@pytest.fixture(autouse=True)
def _config_temporal(monkeypatch, tmp_path):
    """Redirige el almacén de solicitudes a un directorio temporal."""
    monkeypatch.setattr(config, "_data_dir", str(tmp_path / "almacen_solicitudes"))
    yield


@pytest.fixture
def sesion_padre():
    sesion = seguridad.Sesion(
        id_usuario=101, nombre_usuario="padre_ui", rol="Padre",
        dni="79999998", nombres="Padre", apellidos="UI",
    )
    seguridad.iniciar_sesion(sesion)
    yield sesion
    seguridad.cerrar_sesion()


@pytest.fixture
def sesion_secretaria():
    sesion = seguridad.Sesion(
        id_usuario=102, nombre_usuario="sec_ui", rol="Secretaria",
        dni="87733221", nombres="Secretaria", apellidos="Pruebas",
    )
    seguridad.iniciar_sesion(sesion)
    yield sesion
    seguridad.cerrar_sesion()


@pytest.fixture
def silenciar_dialogos(monkeypatch):
    """Evita que los diálogos modales bloqueen las pruebas."""
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes
    )
    monkeypatch.setattr(
        QInputDialog, "getMultiLineText", lambda *args, **kwargs: ("", False)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", "")
    )
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: None)
