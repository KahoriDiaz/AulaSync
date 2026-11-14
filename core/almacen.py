"""Almacén de solicitudes en trámite (archivos JSON + documentos).

Las solicitudes no validadas no viven en la base de datos: se guardan en una
carpeta por solicitud, con escritura atómica y control de versión.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import config
from core.errores import ErrorConflicto, ErrorValidacion

TIPOS_DOCUMENTO = (
    "DNI estudiante",
    "DNI padre/apoderado",
    "Constancia de logros",
    "Otro",
)

_PREFIJOS = {
    "DNI estudiante": "dni_estudiante",
    "DNI padre/apoderado": "dni_padre",
    "Constancia de logros": "constancia",
    "Otro": "otro",
}

_MAXIMO_BYTES = 10 * 1024 * 1024
_PATRON_ID = re.compile(r"^SOL-\d{4}-\d{4}$")


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def detectar_tipo_archivo(cabecera: bytes) -> str | None:
    """Devuelve el MIME real a partir de la firma del archivo."""
    if cabecera.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if cabecera.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if cabecera.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def calcular_sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def validar_documento(ruta: Path) -> dict[str, Any]:
    """Valida tamaño y firma real del archivo. Devuelve sus metadatos básicos."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ErrorValidacion("El archivo seleccionado no existe.")
    tamano = ruta.stat().st_size
    if tamano == 0:
        raise ErrorValidacion("El archivo está vacío.")
    if tamano > _MAXIMO_BYTES:
        raise ErrorValidacion("El archivo supera el máximo permitido de 10 MB.")
    with open(ruta, "rb") as archivo:
        cabecera = archivo.read(8)
    mime = detectar_tipo_archivo(cabecera)
    if mime is None:
        raise ErrorValidacion("El archivo debe ser una imagen JPG o PNG, o un PDF válido.")
    return {"mime": mime, "bytes": tamano, "sha256": calcular_sha256(ruta)}


class Almacen:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base = Path(base_dir) if base_dir is not None else config.data_dir
        self.base.mkdir(parents=True, exist_ok=True)

    def ruta(self, id_solicitud: str) -> Path:
        if not _PATRON_ID.match(id_solicitud):
            raise ErrorValidacion("El identificador de la solicitud no es válido.")
        return self.base / id_solicitud

    def existe(self, id_solicitud: str) -> bool:
        return (self.ruta(id_solicitud) / "solicitud.json").is_file()

    def listar_ids(self) -> list[str]:
        if not self.base.is_dir():
            return []
        return sorted(
            p.name
            for p in self.base.iterdir()
            if p.is_dir() and (p / "solicitud.json").is_file()
        )

    def _siguiente_id(self) -> str:
        anio = datetime.now().year
        maximo = 0
        patron = re.compile(rf"^SOL-{anio}-(\d{{4}})$")
        if self.base.is_dir():
            for entrada in self.base.iterdir():
                coincidencia = patron.match(entrada.name)
                if coincidencia:
                    maximo = max(maximo, int(coincidencia.group(1)))
        return f"SOL-{anio}-{maximo + 1:04d}"

    def crear(self, datos_iniciales: dict[str, Any], version: str = "1") -> str:
        """Crea una carpeta de solicitud de forma exclusiva y su solicitud.json."""
        while True:
            id_solicitud = self._siguiente_id()
            carpeta = self.base / id_solicitud
            try:
                carpeta.mkdir(exist_ok=False)
            except FileExistsError:
                continue
            break
        carpeta_docs = carpeta / "documentos"
        carpeta_docs.mkdir()
        solicitud: dict[str, Any] = {
            "id": id_solicitud,
            "version": 1,
            "padre": datos_iniciales.get("padre", {}),
            "estudiante_dni": datos_iniciales.get("estudiante_dni", ""),
            "anio": datos_iniciales.get("anio"),
            "nivel": datos_iniciales.get("nivel", ""),
            "grado": datos_iniciales.get("grado", ""),
            "estado": "Borrador",
            "fecha_creacion": _ahora(),
            "fecha_envio": None,
            "fecha_resolucion": None,
            "revisor": None,
            "observacion": "",
            "documentos": [],
            "datos": datos_iniciales.get("datos", {}),
            "historial": [],
        }
        self._agregar_historial(
            solicitud,
            usuario=datos_iniciales.get("padre", {}).get("id_usuario"),
            accion="Creación de la solicitud",
            estado_nuevo="Borrador",
            nota="Solicitud creada por el padre/apoderado.",
        )
        self._escribir(solicitud)
        return id_solicitud

    def cargar(self, id_solicitud: str) -> dict[str, Any]:
        ruta = self.ruta(id_solicitud) / "solicitud.json"
        if not ruta.is_file():
            raise ErrorValidacion("La solicitud no existe o fue eliminada.")
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    def _escribir(self, solicitud: dict[str, Any]) -> None:
        carpeta = self.ruta(solicitud["id"])
        carpeta.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(
            prefix=".solicitud-", suffix=".tmp", dir=str(carpeta)
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                json.dump(solicitud, archivo, ensure_ascii=False, indent=2)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, carpeta / "solicitud.json")
        finally:
            if os.path.exists(temporal):
                os.unlink(temporal)

    def guardar(self, solicitud: dict[str, Any], version_esperada: int | None = None) -> int:
        """Guarda con control de versión. Devuelve la nueva versión."""
        id_solicitud = solicitud.get("id", "")
        actual = self.cargar(id_solicitud)
        if version_esperada is not None:
            if int(actual.get("version", 0)) != int(version_esperada):
                raise ErrorConflicto(
                    "La solicitud cambió mientras la editaba. Se volvió a cargar; "
                    "revise los datos e intente nuevamente."
                )
        solicitud["version"] = int(actual.get("version", 0)) + 1
        self._escribir(solicitud)
        return solicitud["version"]

    def carpeta_documentos(self, id_solicitud: str, crear: bool = True) -> Path:
        carpeta = self.ruta(id_solicitud) / "documentos"
        if crear:
            carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def agregar_documento(
        self, id_solicitud: str, ruta_origen: Path | str, tipo: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Valida, copia y registra un documento. Devuelve (metadatos, solicitud)."""
        if tipo not in TIPOS_DOCUMENTO:
            raise ErrorValidacion("El tipo de documento no es válido.")
        origen = Path(ruta_origen)
        meta = validar_documento(origen)
        solicitud = self.cargar(id_solicitud)
        for documento in solicitud.get("documentos", []):
            if documento.get("sha256") == meta["sha256"]:
                raise ErrorValidacion("Este mismo archivo ya fue cargado en la solicitud.")
        extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf",
        }[meta["mime"]]
        prefijo = _PREFIJOS[tipo]
        carpeta = self.carpeta_documentos(id_solicitud)
        nombre = f"{prefijo}{extension}"
        if tipo == "Otro":
            numero = 1
            while (carpeta / f"otro_{numero}{extension}").exists():
                numero += 1
            nombre = f"otro_{numero}{extension}"
        destino = carpeta / nombre
        with open(origen, "rb") as entrada, open(destino, "wb") as salida:
            while True:
                bloque = entrada.read(1024 * 1024)
                if not bloque:
                    break
                salida.write(bloque)
        registro = {
            "tipo": tipo,
            "archivo": f"documentos/{nombre}",
            "mime": meta["mime"],
            "bytes": meta["bytes"],
            "sha256": meta["sha256"],
            "fecha": _ahora(),
        }
        solicitud["documentos"].append(registro)
        self._agregar_historial(
            solicitud,
            usuario=solicitud.get("padre", {}).get("id_usuario"),
            accion=f"Carga de documento: {tipo}",
            estado_nuevo=solicitud.get("estado", "Borrador"),
            nota=nombre,
        )
        self.guardar(solicitud, version_esperada=solicitud.get("version"))
        return registro, solicitud

    def eliminar_documento(self, id_solicitud: str, sha256: str) -> dict[str, Any]:
        solicitud = self.cargar(id_solicitud)
        restantes = []
        eliminado = None
        for documento in solicitud.get("documentos", []):
            if documento.get("sha256") == sha256:
                eliminado = documento
            else:
                restantes.append(documento)
        if eliminado is None:
            raise ErrorValidacion("El documento no pertenece a la solicitud.")
        archivo = self.ruta(id_solicitud) / eliminado["archivo"]
        if archivo.is_file():
            archivo.unlink()
        solicitud["documentos"] = restantes
        self._agregar_historial(
            solicitud,
            usuario=solicitud.get("padre", {}).get("id_usuario"),
            accion=f"Eliminación de documento: {eliminado.get('tipo')}",
            estado_nuevo=solicitud.get("estado", "Borrador"),
            nota=eliminado.get("archivo", ""),
        )
        self.guardar(solicitud, version_esperada=solicitud.get("version"))
        return solicitud

    def eliminar_documentos(self, id_solicitud: str) -> int:
        """Elimina los archivos de una solicitud resuelta. Devuelve cuántos borró."""
        carpeta = self.carpeta_documentos(id_solicitud, crear=False)
        borrados = 0
        if carpeta.is_dir():
            for archivo in carpeta.iterdir():
                if archivo.is_file():
                    archivo.unlink()
                    borrados += 1
        solicitud = self.cargar(id_solicitud)
        solicitud["documentos"] = []
        self.guardar(solicitud, version_esperada=solicitud.get("version"))
        return borrados

    def ruta_documento(self, id_solicitud: str, documento: dict[str, Any]) -> Path:
        return self.ruta(id_solicitud) / documento["archivo"]

    @staticmethod
    def _agregar_historial(
        solicitud: dict[str, Any],
        usuario: Any,
        accion: str,
        estado_nuevo: str | None,
        nota: str = "",
    ) -> None:
        solicitud.setdefault("historial", []).append(
            {
                "fecha": _ahora(),
                "usuario": usuario,
                "accion": accion,
                "estado_nuevo": estado_nuevo,
                "nota": nota,
            }
        )

    @staticmethod
    def registrar_historial(
        solicitud: dict[str, Any],
        usuario: Any,
        accion: str,
        estado_nuevo: str | None,
        nota: str = "",
    ) -> None:
        Almacen._agregar_historial(solicitud, usuario, accion, estado_nuevo, nota)
