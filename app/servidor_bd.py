"""MySQL portátil incluido en la entrega (carpeta ``mysql/`` junto al .exe).

Si existe ``mysql/bin/mysqld.exe``, AulaSync no necesita un MySQL instalado:

1. Si no existe ``mysql_data/``, copia la plantilla ``mysql_plantilla/`` (la
   base ya cargada con los datos de prueba que genera ``build.bat``). Sin
   plantilla, inicializa la base y carga los scripts 01 a 06 (más lento).
2. Enciende el servidor oculto, solo en 127.0.0.1 y en el puerto 3307 (no choca
   con un MySQL instalado en el 3306).
3. Al cerrar AulaSync lo apaga con ``SHUTDOWN``.

El administrador (root) tiene una clave aleatoria que solo se guarda dentro de
los datos, para poder apagar el servidor. Para volver a los datos de prueba
basta con borrar ``mysql_data/``.

Generar la plantilla: ``python -m app.servidor_bd --plantilla <carpeta>``.
"""
from __future__ import annotations

import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from app.config import config

PUERTO = 3307
HOST = "127.0.0.1"
CLAVE_APP = "matricula_app"
MYSQL_DIR = config.USER_DIR / "mysql"
PLANTILLA_DIR = config.USER_DIR / "mysql_plantilla"
DATOS_DIR = config.USER_DIR / "mysql_data"
MARCA = "aulasync_bd_lista.txt"
CLAVE = "aulasync_admin.txt"

_proceso: subprocess.Popen | None = None


class ErrorServidor(RuntimeError):
    """El MySQL portátil no pudo iniciar o preparar la base."""


def disponible() -> bool:
    """True si la entrega incluye el MySQL portátil."""
    return (MYSQL_DIR / "bin" / "mysqld.exe").is_file()


def _mysqld() -> Path:
    return MYSQL_DIR / "bin" / "mysqld.exe"


def _opciones_comunes(datos: Path) -> list[str]:
    return [
        "--no-defaults",
        f"--basedir={MYSQL_DIR}",
        f"--datadir={datos}",
        "--character-set-server=utf8mb4",
        "--collation-server=utf8mb4_unicode_ci",
        # Base pequeña: menos archivos que escribir y copiar.
        "--innodb-redo-log-capacity=8388608",
        "--innodb-undo-tablespaces=2",
        "--innodb-data-file-path=ibdata1:12M:autoextend",
        "--innodb-temp-data-file-path=ibtmp1:12M:autoextend",
    ]


def _sin_ventana() -> dict:
    """Ejecuta mysqld sin abrir una consola en Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _puerto_abierto() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.settimeout(0.5)
        return conexion.connect_ex((HOST, PUERTO)) == 0


def _clave_admin(datos: Path) -> str:
    """Clave del administrador: vacía hasta que la base queda preparada."""
    try:
        return (datos / CLAVE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _conectar_admin(datos: Path):
    import mysql.connector

    return mysql.connector.connect(
        host=HOST, port=PUERTO, user="root", password=_clave_admin(datos),
        use_pure=True, charset="utf8mb4", connection_timeout=5,
    )


def _inicializar(datos: Path) -> None:
    datos.parent.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        [str(_mysqld()), *_opciones_comunes(datos), "--initialize-insecure"],
        capture_output=True, text=True, timeout=600, **_sin_ventana(),
    )
    if resultado.returncode != 0 or not (datos / "mysql").is_dir():
        raise ErrorServidor(
            "No se pudo preparar la base de datos portátil.\n"
            + (resultado.stderr or resultado.stdout or "")[-800:]
        )


def _encender(datos: Path) -> subprocess.Popen:
    registro = datos / "servidor.log"
    proceso = subprocess.Popen(
        [str(_mysqld()), *_opciones_comunes(datos), f"--port={PUERTO}", f"--bind-address={HOST}",
         "--mysqlx=OFF", "--skip-log-bin", "--performance-schema=OFF",
         "--innodb-buffer-pool-size=64M", f"--log-error={registro}"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        **_sin_ventana(),
    )
    limite = time.time() + 120
    while time.time() < limite:
        if proceso.poll() is not None:
            detalle = registro.read_text(encoding="utf-8", errors="replace")[-800:] if registro.exists() else ""
            raise ErrorServidor("La base de datos portátil se detuvo al iniciar.\n" + detalle)
        if _puerto_abierto():
            try:
                _conectar_admin(datos).close()
                return proceso
            except Exception:
                pass
        time.sleep(0.5)
    proceso.terminate()
    raise ErrorServidor("La base de datos portátil tardó demasiado en iniciar.")


def _apagar(datos: Path, proceso: subprocess.Popen) -> None:
    try:
        cnx = _conectar_admin(datos)
        try:
            cnx.cursor().execute("SHUTDOWN")
        finally:
            cnx.close()
        proceso.wait(timeout=60)
    except Exception:
        proceso.terminate()


def _preparar_base(datos: Path) -> None:
    """Crea bd_matricula y carga los scripts; protege al administrador con una clave aleatoria."""
    from app.setup_bd import crear_base_y_usuario, ejecutar_todos_los_scripts

    clave_actual = _clave_admin(datos)
    crear_base_y_usuario(HOST, PUERTO, "root", clave_actual, CLAVE_APP)
    ejecutar_todos_los_scripts(config.RECURSOS_DIR, HOST, PUERTO, "root", clave_actual, CLAVE_APP)
    if not clave_actual:
        nueva = secrets.token_urlsafe(24)
        cnx = _conectar_admin(datos)
        try:
            cursor = cnx.cursor()
            cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (nueva,))
            cursor.close()
        finally:
            cnx.close()
        (datos / CLAVE).write_text(nueva, encoding="utf-8")
    (datos / MARCA).write_text("Base de datos de AulaSync cargada.\n", encoding="utf-8")


def iniciar(avisar: Callable[[str], None] = lambda _texto: None) -> None:
    """Deja el MySQL portátil encendido y la base lista; configura la conexión."""
    global _proceso
    if not (DATOS_DIR / "mysql").is_dir():
        if (PLANTILLA_DIR / MARCA).is_file():
            avisar("Preparando la base de datos por primera vez...")
            shutil.copytree(PLANTILLA_DIR, DATOS_DIR, dirs_exist_ok=True)
        else:
            avisar("Preparando la base de datos por primera vez (puede tardar un minuto)...")
            _inicializar(DATOS_DIR)
    if not _puerto_abierto():
        avisar("Iniciando la base de datos...")
        _proceso = _encender(DATOS_DIR)
    if not (DATOS_DIR / MARCA).is_file():
        avisar("Cargando los datos de prueba...")
        _preparar_base(DATOS_DIR)
    config.guardar({
        "host": HOST, "port": PUERTO, "user": "matricula_app",
        "password": CLAVE_APP, "database": "bd_matricula",
    })


def detener() -> None:
    """Apaga el servidor si lo encendió esta ejecución de AulaSync."""
    global _proceso
    if _proceso is not None and _proceso.poll() is None:
        _apagar(DATOS_DIR, _proceso)
    _proceso = None


def crear_plantilla(destino: Path) -> None:
    """Genera la base ya cargada que se distribuye en mysql_plantilla/."""
    if _puerto_abierto():
        raise ErrorServidor(f"El puerto {PUERTO} está ocupado; cierre AulaSync antes de compilar.")
    destino = Path(destino).resolve()
    if destino.exists():
        shutil.rmtree(destino)
    _inicializar(destino)
    proceso = _encender(destino)
    try:
        _preparar_base(destino)
    finally:
        _apagar(destino, proceso)
    (destino / "servidor.log").unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera la plantilla de la base portátil.")
    parser.add_argument("--plantilla", required=True, help="carpeta de salida")
    parser.add_argument("--mysql", help="carpeta del MySQL portátil (por defecto ./mysql)")
    argumentos = parser.parse_args()
    if argumentos.mysql:
        MYSQL_DIR = Path(argumentos.mysql).resolve()
    crear_plantilla(Path(argumentos.plantilla))
    print(f"Plantilla de la base creada en {argumentos.plantilla}")
