"""Estilos y paleta visual de la aplicación."""
from __future__ import annotations

PRIMARIO = "#1F4E79"
PRIMARIO_OSCURO = "#16395A"
PRIMARIO_CLARO = "#E8F0F7"
ACENTO = "#2E8B57"
PELIGRO = "#C0392B"
ADVERTENCIA = "#B7791F"
FONDO = "#F4F6F8"
TARJETA = "#FFFFFF"
BORDE = "#D6DEE6"
TEXTO = "#1F2933"
TEXTO_SUAVE = "#52606D"
SIDEBAR = "#1B2A41"
SIDEBAR_ACTIVO = "#2C4A6E"

COLORES_ESTADO = {
    "Correcto": ACENTO,
    "Advertencia": ADVERTENCIA,
    "Error": PELIGRO,
    "Borrador": "#6B7280",
    "Enviada": PRIMARIO,
    "En revisión": "#7C3AED",
    "Subsanación": ADVERTENCIA,
    "Aprobada": ACENTO,
    "Rechazada": PELIGRO,
    "Matriculado": ACENTO,
    "Retirado": ADVERTENCIA,
    "Trasladado": "#7C3AED",
}


def hoja_estilos() -> str:
    return f"""
    * {{
        font-family: 'Segoe UI', 'Noto Sans', Arial, sans-serif;
        font-size: 13px;
        color: {TEXTO};
    }}
    QWidget#Fondo {{ background-color: {FONDO}; }}
    QWidget#Tarjeta {{
        background-color: {TARJETA};
        border: 1px solid {BORDE};
        border-radius: 10px;
    }}
    QLabel#Titulo {{ font-size: 22px; font-weight: 700; color: {PRIMARIO}; }}
    QLabel#Subtitulo {{ font-size: 15px; font-weight: 600; color: {TEXTO}; }}
    QLabel#Ayuda {{ color: {TEXTO_SUAVE}; }}
    QLabel#TituloSeccion {{
        font-size: 16px; font-weight: 700; color: {PRIMARIO};
        padding-bottom: 4px;
    }}
    QLabel#Etiqueta {{ color: {TEXTO_SUAVE}; font-weight: 600; }}
    QLabel#Marca {{
        color: white; font-size: 18px; font-weight: 700;
        padding: 18px 16px;
    }}
    QPushButton {{
        background-color: {PRIMARIO};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {PRIMARIO_OSCURO}; }}
    QPushButton:disabled {{ background-color: #B7C2CC; color: #EEF2F5; }}
    QPushButton#Secundario {{
        background-color: {TARJETA}; color: {PRIMARIO};
        border: 1px solid {PRIMARIO};
    }}
    QPushButton#Secundario:hover {{ background-color: {PRIMARIO_CLARO}; }}
    QPushButton#Peligro {{ background-color: {PELIGRO}; }}
    QPushButton#Peligro:hover {{ background-color: #9C2A1F; }}
    QPushButton#Exito {{ background-color: {ACENTO}; }}
    QPushButton#Exito:hover {{ background-color: #246B43; }}
    QPushButton#Enlace {{
        background: transparent; color: {PRIMARIO};
        border: none; padding: 2px 4px; font-weight: 600;
    }}
    QPushButton#Enlace:hover {{ color: {PRIMARIO_OSCURO}; text-decoration: underline; }}
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
        background-color: white;
        border: 1px solid {BORDE};
        border-radius: 6px;
        padding: 6px 8px;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {PRIMARIO};
    }}
    QLineEdit:read-only {{ background-color: #F1F4F7; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QTableWidget {{
        background-color: white;
        border: 1px solid {BORDE};
        border-radius: 8px;
        gridline-color: #EDF1F5;
        selection-background-color: {PRIMARIO_CLARO};
        selection-color: {TEXTO};
    }}
    QHeaderView::section {{
        background-color: {PRIMARIO_CLARO};
        color: {PRIMARIO};
        padding: 8px;
        border: none;
        border-right: 1px solid {BORDE};
        border-bottom: 1px solid {BORDE};
        font-weight: 700;
    }}
    QListWidget#Menu {{
        background-color: {SIDEBAR};
        border: none;
        outline: none;
        padding-top: 6px;
    }}
    QListWidget#Menu::item {{
        color: #D3DCE6; padding: 11px 18px; border: none;
    }}
    QListWidget#Menu::item:selected {{
        background-color: {SIDEBAR_ACTIVO}; color: white;
        border-left: 4px solid #5FA8E8;
    }}
    QListWidget#Menu::item:hover {{ background-color: {SIDEBAR_ACTIVO}; }}
    QProgressBar {{
        border: 1px solid {BORDE}; border-radius: 6px;
        text-align: center; background: white; height: 18px;
    }}
    QProgressBar::chunk {{ background-color: {ACENTO}; border-radius: 5px; }}
    QTabWidget::pane {{ border: 1px solid {BORDE}; border-radius: 8px; background: white; }}
    QTabBar::tab {{
        background: #E4EAF0; padding: 8px 16px; margin-right: 2px;
        border-top-left-radius: 6px; border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{ background: white; color: {PRIMARIO}; font-weight: 700; }}
    QScrollArea {{ border: none; background: transparent; }}
    QGroupBox {{
        border: 1px solid {BORDE}; border-radius: 8px;
        margin-top: 14px; padding-top: 10px; font-weight: 700;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {PRIMARIO};
    }}
    """
