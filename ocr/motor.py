"""Motor de OCR: interfaz base y motor basado en Tesseract 5 (idioma spa)."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytesseract
from pytesseract import Output

from core.config import config
from core.errores import ErrorApp
from ocr.constancia import extraer_constancia
from ocr.dni import Campo, LineaOCR, extraer_dni
from ocr.preprocesado import extraer_texto_pdf, preprocesar_imagen, renderizar_pdf

ORIGEN_OCR = "OCR"
ORIGEN_PDF = "Texto PDF"


class ErrorOCR(ErrorApp):
    pass


@dataclass
class ResultadoOCR:
    campos: dict[str, Campo] = field(default_factory=dict)
    logros: list[dict[str, Campo]] = field(default_factory=list)
    texto: str = ""
    motor: str = "Tesseract"


class MotorOCR(ABC):
    nombre = "Motor"

    @abstractmethod
    def leer(self, ruta: Path | str, tipo: str) -> ResultadoOCR:
        ...

    @abstractmethod
    def disponible(self) -> bool:
        ...


def ruta_segura(ruta: Path) -> str:
    """En Windows devuelve la ruta corta (8.3) para evitar problemas con tildes."""
    if os.name != "nt":
        return str(ruta)
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        resultado = ctypes.windll.kernel32.GetShortPathNameW(str(ruta), buffer, 1024)
        if resultado:
            return buffer.value
    except Exception:
        pass
    return str(ruta)


def buscar_tesseract() -> Path | None:
    candidatos: list[Path] = [config.tesseract_dir / "tesseract.exe"]
    en_path = shutil.which("tesseract")
    if en_path:
        candidatos.append(Path(en_path))
    candidatos.append(Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"))
    candidatos.append(Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"))
    for candidato in candidatos:
        if candidato and candidato.is_file():
            return candidato
    return None


def tesseract_disponible() -> bool:
    return buscar_tesseract() is not None


_tessdata_segura: Path | None = None


def tessdata_para_tesseract() -> Path:
    """Devuelve una ruta sin tildes para tessdata (Tesseract no abre rutas Unicode)."""
    global _tessdata_segura
    if _tessdata_segura is not None:
        return _tessdata_segura
    original = config.tessdata_dir
    if str(original).isascii() or not original.is_dir():
        _tessdata_segura = original
        return original
    base = Path(os.getenv("LOCALAPPDATA") or tempfile.gettempdir()) / "SistemaMatricula"
    base.mkdir(parents=True, exist_ok=True)
    destino = base / "tessdata"
    if destino.is_dir() and (destino / "spa.traineddata").is_file():
        _tessdata_segura = destino
        return destino
    if destino.exists():
        try:
            os.rmdir(destino)
        except OSError:
            shutil.rmtree(destino, ignore_errors=True)
    try:
        creacion = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(destino), str(original)],
            check=True,
            capture_output=True,
            creationflags=creacion,
        )
    except Exception:
        try:
            shutil.copytree(original, destino)
        except Exception:
            _tessdata_segura = original
            return original
    _tessdata_segura = destino
    return destino


def _config_tesseract() -> str:
    tessdata = tessdata_para_tesseract()
    opciones = "--psm 6 -c preserve_interword_spaces=1"
    if tessdata.is_dir():
        ruta = tessdata.as_posix()
        if " " in ruta:
            corta = ruta_segura(tessdata).replace("\\", "/")
            if " " in corta:
                os.environ["TESSDATA_PREFIX"] = ruta
                return opciones
            ruta = corta
        return f"--tessdata-dir {ruta} {opciones}"
    return opciones


class MotorTesseract(MotorOCR):
    nombre = "Tesseract"

    def __init__(self) -> None:
        self.ejecutable = buscar_tesseract()
        if self.ejecutable:
            pytesseract.pytesseract.tesseract_cmd = ruta_segura(self.ejecutable)

    def disponible(self) -> bool:
        return self.ejecutable is not None

    def _exigir_tesseract(self) -> None:
        if not self.ejecutable:
            raise ErrorOCR(
                "No se encontró Tesseract OCR. Instálelo o escriba los datos manualmente."
            )

    def _ocr_imagen(self, imagen) -> list[LineaOCR]:
        self._exigir_tesseract()
        datos: dict[str, Any] = pytesseract.image_to_data(
            imagen,
            lang="spa",
            config=_config_tesseract(),
            output_type=Output.DICT,
        )
        agrupadas: dict[tuple[int, int, int, int], dict[str, Any]] = {}
        for i, texto in enumerate(datos["text"]):
            limpio = (texto or "").strip()
            if not limpio:
                continue
            clave = (
                datos["page_num"][i],
                datos["block_num"][i],
                datos["par_num"][i],
                datos["line_num"][i],
            )
            registro = agrupadas.setdefault(clave, {"palabras": [], "confianzas": []})
            registro["palabras"].append(limpio)
            try:
                confianza = float(datos["conf"][i])
            except (TypeError, ValueError):
                confianza = -1
            if confianza >= 0:
                registro["confianzas"].append(confianza)
        lineas: list[LineaOCR] = []
        for clave in sorted(agrupadas, key=lambda k: (k[0], k[1], k[2], k[3])):
            registro = agrupadas[clave]
            confianzas = registro["confianzas"] or [0]
            lineas.append((" ".join(registro["palabras"]), int(sum(confianzas) / len(confianzas))))
        return lineas

    def _lineas_archivo(self, ruta: Path) -> tuple[list[LineaOCR], str, str]:
        sufijo = ruta.suffix.lower()
        es_pdf = sufijo == ".pdf"
        if not es_pdf:
            with open(ruta, "rb") as archivo:
                es_pdf = archivo.read(5) == b"%PDF-"
        if es_pdf:
            texto = extraer_texto_pdf(ruta)
            if len(texto.strip()) > 50:
                lineas = [(linea.strip(), 99) for linea in texto.splitlines() if linea.strip()]
                return lineas, texto, ORIGEN_PDF
            lineas: list[LineaOCR] = []
            textos: list[str] = []
            for imagen in renderizar_pdf(ruta):
                lineas.extend(self._ocr_imagen(imagen))
            textos = [texto for texto, _ in lineas]
            return lineas, "\n".join(textos), ORIGEN_OCR
        imagen = preprocesar_imagen(ruta)
        lineas = self._ocr_imagen(imagen)
        return lineas, "\n".join(texto for texto, _ in lineas), ORIGEN_OCR

    def leer(self, ruta: Path | str, tipo: str) -> ResultadoOCR:
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorOCR("El archivo indicado no existe.")
        lineas, texto, origen = self._lineas_archivo(ruta)
        if tipo == "DNI estudiante":
            campos = extraer_dni(lineas, "ESTUDIANTE", origen)
            return ResultadoOCR(campos=campos, texto=texto, motor=self.nombre)
        if tipo == "DNI padre/apoderado":
            campos = extraer_dni(lineas, "PADRE_APODERADO", origen)
            return ResultadoOCR(campos=campos, texto=texto, motor=self.nombre)
        if tipo == "Constancia de logros":
            campos, logros = extraer_constancia(lineas, origen)
            return ResultadoOCR(campos=campos, logros=logros, texto=texto, motor=self.nombre)
        return ResultadoOCR(texto=texto, motor=self.nombre)


def obtener_motor() -> MotorOCR:
    motor = MotorTesseract()
    if not motor.disponible():
        raise ErrorOCR(
            "No se encontró Tesseract OCR. Instálelo o escriba los datos manualmente."
        )
    return motor


def leer_documento(ruta: Path | str, tipo: str, motor: MotorOCR | None = None) -> ResultadoOCR:
    motor = motor or obtener_motor()
    return motor.leer(ruta, tipo)
