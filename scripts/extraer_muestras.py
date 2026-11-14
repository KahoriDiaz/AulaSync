"""Extrae las imágenes de muestra del informe (docx -> muestras/).

Uso: python scripts/extraer_muestras.py [--docx RUTA] [--salida CARPETA]
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCX_POR_DEFECTO = BASE_DIR / "docs" / "ENTREGA_5_v1.docx"
SALIDA_POR_DEFECTO = BASE_DIR / "muestras"


def extraer(docx: Path, salida: Path) -> list[Path]:
    if not docx.is_file():
        raise FileNotFoundError(f"No se encontró el documento: {docx}")
    salida.mkdir(parents=True, exist_ok=True)
    extraidas: list[Path] = []
    with zipfile.ZipFile(docx) as archivo:
        for nombre in archivo.namelist():
            if not nombre.startswith("word/media/") or nombre.endswith("/"):
                continue
            destino = salida / Path(nombre).name
            with archivo.open(nombre) as origen, open(destino, "wb") as fin:
                fin.write(origen.read())
            extraidas.append(destino)
    return extraidas


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae las imágenes del informe a muestras/.")
    parser.add_argument("--docx", type=Path, default=DOCX_POR_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    argumentos = parser.parse_args()
    for ruta in extraer(argumentos.docx, argumentos.salida):
        print(ruta)


if __name__ == "__main__":
    main()
