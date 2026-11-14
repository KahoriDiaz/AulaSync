"""Genera documentos ficticios (DNI y constancia) para probar el OCR.

Uso: python scripts/generar_documentos_demo.py [--salida CARPETA]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
SALIDA_POR_DEFECTO = BASE_DIR / "muestras" / "demo"

DATOS_ESTUDIANTE = {
    "APELLIDO PATERNO": "QUISPE",
    "APELLIDO MATERNO": "MAMANI",
    "PRE NOMBRES": "ANA SOFIA",
    "FECHA DE NACIMIENTO": "15/03/2014",
    "SEXO": "F",
    "DNI": "70000001",
    "DISTRITO DE NACIMIENTO": "CERCADO",
    "PROVINCIA DE NACIMIENTO": "AREQUIPA",
    "DEPARTAMENTO DE NACIMIENTO": "AREQUIPA",
    "DOMICILIO": "AV. LOS ANDES 123",
    "DISTRITO DE DOMICILIO": "CERCADO",
}

DATOS_PADRE = {
    "APELLIDO PATERNO": "QUISPE",
    "APELLIDO MATERNO": "TORRES",
    "PRE NOMBRES": "JOSE LUIS",
    "FECHA DE NACIMIENTO": "10/07/1985",
    "SEXO": "M",
    "DNI": "70000002",
    "DOMICILIO": "AV. LOS ANDES 123",
    "DISTRITO DE DOMICILIO": "CERCADO",
}


def _fuente(tamano: int) -> ImageFont.FreeTypeFont:
    for ruta in (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ):
        if ruta.is_file():
            return ImageFont.truetype(str(ruta), tamano)
    return ImageFont.load_default()


def _dibujar_dni(datos: dict[str, str], ruta: Path, titulo: str) -> None:
    imagen = Image.new("RGB", (1100, 680), "white")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((10, 10, 1090, 670), outline="black", width=3)
    dibujo.text((40, 30), titulo, font=_fuente(34), fill="black")
    dibujo.text((40, 80), "REPUBLICA DEL PERU", font=_fuente(22), fill="black")
    y = 140
    for etiqueta, valor in datos.items():
        dibujo.text((40, y), f"{etiqueta}:", font=_fuente(24), fill="black")
        dibujo.text((470, y), valor, font=_fuente(26), fill="black")
        y += 48
    imagen.save(ruta)


def _dibujar_constancia(ruta_png: Path, ruta_pdf: Path) -> None:
    imagen = Image.new("RGB", (1240, 900), "white")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((10, 10, 1230, 890), outline="black", width=2)
    dibujo.text((60, 40), "CONSTANCIA DE LOGROS DE APRENDIZAJE", font=_fuente(34), fill="black")
    lineas = [
        ("CODIGO VIRTUAL:", "D4E5F6A7"),
        ("DNI:", "70000001"),
        ("NIVEL EDUCATIVO:", "PRIMARIA"),
        ("FECHA DE EMISION:", "15/12/2025 10:30:00"),
        ("INSTITUCION EDUCATIVA:", "I.E. 40174 EJEMPLO"),
        ("CODIGO MODULAR:", "1137421-0"),
        ("TIPO DE INSTITUCION:", "ESTATAL"),
    ]
    y = 120
    for etiqueta, valor in lineas:
        dibujo.text((60, y), etiqueta, font=_fuente(24), fill="black")
        dibujo.text((480, y), valor, font=_fuente(26), fill="black")
        y += 50
    y += 20
    dibujo.text((60, y), "AÑO        GRADO        SITUACION FINAL", font=_fuente(24), fill="black")
    y += 46
    for anio, grado, situacion in (
        ("2022", "1.°", "APROBADO"),
        ("2023", "2.°", "APROBADO"),
        ("2024", "3.°", "APROBADO"),
        ("2025", "4.°", "REQUIERE RECUPERACION"),
    ):
        dibujo.text((60, y), anio, font=_fuente(26), fill="black")
        dibujo.text((230, y), grado, font=_fuente(26), fill="black")
        dibujo.text((480, y), situacion, font=_fuente(26), fill="black")
        y += 46
    imagen.save(ruta_png)
    imagen.save(ruta_pdf, "PDF", resolution=300.0)


def generar(salida: Path) -> list[Path]:
    salida.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    ruta_dni = salida / "dni_estudiante.png"
    _dibujar_dni(DATOS_ESTUDIANTE, ruta_dni, "DOCUMENTO NACIONAL DE IDENTIDAD")
    rutas.append(ruta_dni)
    ruta_padre = salida / "dni_padre.png"
    _dibujar_dni(DATOS_PADRE, ruta_padre, "DOCUMENTO NACIONAL DE IDENTIDAD")
    rutas.append(ruta_padre)
    ruta_constancia = salida / "constancia.png"
    ruta_pdf = salida / "constancia.pdf"
    _dibujar_constancia(ruta_constancia, ruta_pdf)
    rutas.extend([ruta_constancia, ruta_pdf])
    return rutas


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera documentos ficticios para probar el OCR.")
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    argumentos = parser.parse_args()
    for ruta in generar(argumentos.salida):
        print(ruta)


if __name__ == "__main__":
    main()
