"""Evalúa el OCR sobre las muestras reales del informe.

Lee las imágenes de ``muestras/`` con el motor configurado y muestra, por cada
documento, los campos reconocidos y su confianza. Sirve de evidencia para
``docs/OCR_RESULTADOS.md``.

Uso: python scripts/evaluar_ocr.py [--muestras CARPETA]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ocr.motor import MotorTesseract, tesseract_disponible
MUESTRAS_POR_DEFECTO = BASE_DIR / "muestras"

DOCUMENTOS = (
    ("image1.png", "DNI estudiante"),
    ("image2.png", "DNI padre/apoderado"),
    ("image3.png", "Constancia de logros"),
)


def evaluar(muestras: Path) -> int:
    if not tesseract_disponible():
        print("Tesseract OCR no está instalado; no se puede evaluar.")
        return 1
    motor = MotorTesseract()
    encontrados = 0
    for nombre, tipo in DOCUMENTOS:
        ruta = muestras / nombre
        if not ruta.is_file():
            print(f"[omitido] No existe {ruta}")
            continue
        encontrados += 1
        resultado = motor.leer(ruta, tipo)
        print(f"=== {nombre} ({tipo}) ===")
        if not resultado.campos:
            print("  (sin campos reconocidos)")
        for clave in sorted(resultado.campos):
            _, confianza, origen = resultado.campos[clave]
            print(f"  {clave}: confianza {confianza} [{origen}]")
        print(f"  logros detectados: {len(resultado.logros)}")
    if not encontrados:
        print("No se encontraron muestras. Ejecute antes scripts/extraer_muestras.py.")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa el OCR sobre las muestras reales.")
    parser.add_argument("--muestras", type=Path, default=MUESTRAS_POR_DEFECTO)
    argumentos = parser.parse_args()
    raise SystemExit(evaluar(argumentos.muestras))


if __name__ == "__main__":
    main()
