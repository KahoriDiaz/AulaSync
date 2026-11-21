"""Asistente de base de datos: crea bd_matricula, el usuario matricula_app y carga los scripts SQL.

Respeta el comando DELIMITER de los scripts (el conector MySQL no lo entiende).
Reemplaza los marcadores {{HASH_SECRETARIA}} y {{HASH_SECRETARIA2}} de 05_datos_prueba.sql
con los hashes generados por app/seguridad.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import mysql.connector

from app.config import config
from app.seguridad import hash_clave

SCRIPTS = [
    "sql/01_esquema.sql",
    "sql/02_usuario.sql",
    "sql/03_procedimientos.sql",
    "sql/04_triggers.sql",
    "sql/05_datos_prueba.sql",
    "sql/06_consultas.sql",
]

APP_USER = "matricula_app"


def _root_kwargs(host: str, port: int, user: str, password: str) -> dict[str, Any]:
    return dict(
        host=host,
        port=port,
        user=user,
        password=password,
        charset="utf8mb4",
        use_unicode=True,
        use_pure=True,
        autocommit=False,
    )


def conectar_root(host: str, port: int, user: str, password: str) -> mysql.connector.MySQLConnection:
    try:
        return mysql.connector.connect(**_root_kwargs(host, port, user, password))
    except mysql.connector.Error as exc:
        raise RuntimeError(f"No se pudo conectar como administrador de MySQL: {exc}") from exc


def parsear_script(texto: str) -> list[str]:
    """Divide un script SQL en sentencias respetando DELIMITER."""
    sentencias: list[str] = []
    buffer: list[str] = []
    delimitador = ";"

    for linea in texto.splitlines():
        linea_limpia = linea.strip()
        if linea_limpia.upper().startswith("DELIMITER "):
            if buffer:
                sentencia = "\n".join(buffer).strip()
                if sentencia:
                    sentencias.append(sentencia)
                buffer = []
            partes = linea_limpia.split(None, 1)
            if len(partes) == 2:
                delimitador = partes[1].strip()
            continue

        if linea_limpia.endswith(delimitador):
            buffer.append(linea)
            sentencia = "\n".join(buffer).strip()
            if sentencia.endswith(delimitador):
                sentencia = sentencia[: -len(delimitador)].strip()
            if sentencia:
                sentencias.append(sentencia)
            buffer = []
        else:
            buffer.append(linea)

    if buffer:
        sentencia = "\n".join(buffer).strip()
        if sentencia:
            sentencias.append(sentencia)

    return sentencias


def _aplicar_reemplazos(texto: str, replacements: dict[str, str]) -> str:
    for clave, valor in replacements.items():
        texto = texto.replace(clave, valor)
    return texto


def ejecutar_archivo(
    cnx: mysql.connector.MySQLConnection,
    ruta: str | Path,
    replacements: dict[str, str] | None = None,
) -> int:
    """Ejecuta todos los statements de un archivo SQL en orden. Devuelve el count."""
    texto = Path(ruta).read_text(encoding="utf-8")
    if replacements:
        texto = _aplicar_reemplazos(texto, replacements)
    sentencias = parsear_script(texto)
    cursor = cnx.cursor()
    try:
        for sentencia in sentencias:
            cursor.execute(sentencia)
            if cursor.with_rows:
                cursor.fetchall()
            while cursor.nextset():
                if cursor.with_rows:
                    cursor.fetchall()
        return len(sentencias)
    finally:
        cursor.close()


def crear_base_y_usuario(
    host: str,
    port: int,
    root_user: str,
    root_password: str,
    app_password: str,
    database: str = "bd_matricula",
) -> None:
    """Crea la base de datos (vacía), el usuario matricula_app y sus permisos."""
    cnx = conectar_root(host, port, root_user, root_password)
    try:
        cursor = cnx.cursor()
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
            cursor.execute(
                f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            # Sin forzar mysql_native_password: MySQL 8.4+ lo trae desactivado y
            # mysql-connector ya soporta caching_sha2_password (el predeterminado).
            cursor.execute(
                f"CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY %s",
                (app_password,),
            )
            # Si el usuario ya existÃ­a con otra clave, se alinea con config.ini.
            cursor.execute(
                f"ALTER USER '{APP_USER}'@'localhost' IDENTIFIED BY %s",
                (app_password,),
            )
            # MÃ­nimo privilegio: la aplicaciÃ³n solo lee (SELECT) y llama a los
            # procedimientos (EXECUTE); las escrituras las hacen los sp_ con
            # SQL SECURITY DEFINER. Se limpian permisos de instalaciones previas.
            cursor.execute(
                f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{APP_USER}'@'localhost'"
            )
            cursor.execute(
                f"GRANT SELECT, EXECUTE ON `{database}`.* TO '{APP_USER}'@'localhost'"
            )
            cursor.execute("SET GLOBAL log_bin_trust_function_creators = 1")
            cursor.execute("FLUSH PRIVILEGES")
            cnx.commit()
        finally:
            cursor.close()
    finally:
        cnx.close()


def ejecutar_todos_los_scripts(
    base_dir: Path,
    host: str,
    port: int,
    root_user: str,
    root_password: str,
    app_password: str,
    database: str = "bd_matricula",
) -> None:
    """Ejecuta los scripts 01 a 06 en orden. El 01 sin BD; el resto sobre bd_matricula."""
    replacements = {
        "{{HASH_SECRETARIA}}": hash_clave("secretaria123"),
        "{{HASH_SECRETARIA2}}": hash_clave("secretaria123"),
    }

    # 01 crea la base de datos: se ejecuta sin seleccionar una BD destino.
    cnx = conectar_root(host, port, root_user, root_password)
    try:
        n = ejecutar_archivo(cnx, base_dir / SCRIPTS[0])
        cnx.commit()
        print(f"[01] {SCRIPTS[0]} -> {n} sentencias (base creada).")
    finally:
        cnx.close()

    for ruta_rel in SCRIPTS[1:]:
        cnx = conectar_root(host, port, root_user, root_password)
        try:
            cnx.database = database
            n = ejecutar_archivo(cnx, base_dir / ruta_rel, replacements)
            cnx.commit()
            print(f"[{ruta_rel}] -> {n} sentencias ejecutadas.")
        finally:
            cnx.close()


def verificar(database: str = "bd_matricula") -> None:
    cnx = conectar_root(config.host, config.port, config.user, config.password)
    try:
        cnx.database = database
        cursor = cnx.cursor()
        try:
            cursor.execute("SELECT VERSION()")
            print("MySQL:", cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) AS total FROM ESTUDIANTE")
            print("ESTUDIANTE registros:", cursor.fetchone()[0])
            cursor.execute("DESCRIBE USUARIO")
            print("Columnas USUARIO:", [fila[0] for fila in cursor.fetchall()])
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME"
            )
            tablas = [fila[0] for fila in cursor.fetchall()]
            print("Tablas:", ", ".join(tablas))
        finally:
            cursor.close()
    finally:
        cnx.close()


def main() -> None:
    base_dir = config.RECURSOS_DIR
    # Las credenciales de root se piden en el asistente de la UI; aqui solo se
    # ejecuta si se invoca directamente con valores por defecto (root/root).
    ejecutar_todos_los_scripts(base_dir, config.password or "root")
    print("--- Verificacion ---")
    verificar()


if __name__ == "__main__":
    main()
