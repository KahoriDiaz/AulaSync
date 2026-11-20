"""Asistente de conexión: ejecuta los scripts SQL 01..06 y verifica la base."""
from __future__ import annotations

from pathlib import Path

import mysql.connector

from core.config import config
from core.sql_parser import ejecutar_archivo

SCRIPTS = [
    "sql/01_creacion.sql",
    "sql/02_datos_prueba.sql",
    "sql/03_usuario.sql",
    "sql/04_procedimientos.sql",
    "sql/06_consultas.sql",
]


def _conexion_kwargs(database: str | None) -> dict:
    return dict(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        charset="utf8mb4",
        use_unicode=True,
        use_pure=True,
        autocommit=False,
        database=database,
    )


def conectar(database: str | None = None) -> mysql.connector.MySQLConnection:
    try:
        return mysql.connector.connect(**_conexion_kwargs(database))
    except mysql.connector.Error as exc:
        raise SystemExit(
            f"No se pudo conectar a MySQL. Verifique el servidor y el .env: {exc}"
        ) from exc


def ejecutar_todos_los_scripts(base_dir: Path) -> None:
    # 01 crea la base de datos: se ejecuta sin seleccionar una BD destino.
    cnx = conectar(None)
    try:
        n = ejecutar_archivo(cnx, base_dir / SCRIPTS[0])
        cnx.commit()
        print(f"[01] {SCRIPTS[0]} -> {n} sentencias ejecutadas (base creada).")
    finally:
        cnx.close()

    # El resto opera sobre bd_matricula.
    for ruta_rel in SCRIPTS[1:]:
        cnx = conectar(config.db_name)
        try:
            n = ejecutar_archivo(cnx, base_dir / ruta_rel)
            cnx.commit()
            print(f"[{ruta_rel}] -> {n} sentencias ejecutadas.")
        finally:
            cnx.close()


def verificar() -> None:
    cnx = conectar(config.db_name)
    try:
        cursor = cnx.cursor()
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
        cursor.close()
    finally:
        cnx.close()


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    ejecutar_todos_los_scripts(base_dir)
    print("--- Verificación ---")
    verificar()


if __name__ == "__main__":
    main()
