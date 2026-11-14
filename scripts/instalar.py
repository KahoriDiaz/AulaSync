"""Instalación interactiva de la base de datos y de la cuenta de la secretaria.

Uso:  python scripts/instalar.py

Nunca imprime ni guarda la contraseña de root. El usuario matricula_app recibe
una contraseña aleatoria que se escribe únicamente en el archivo .env.
"""
from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import mysql.connector

from core.seguridad import generar_hash

DB_NAME = "bd_matricula_paola_frassinetti"
DB_USER_APP = "matricula_app"
SQL_DIR = BASE_DIR / "sql"

COLUMNAS_ESPERADAS = {
    "CONSTANCIA_LOGROS": 4,
    "CONTACTO_EMERGENCIA": 3,
    "ESTUDIANTE": 25,
    "ESTUDIANTE_HERMANOS_IE": 2,
    "ESTUDIANTE_NEE": 2,
    "HERMANDAD": 2,
    "INSTITUCION_EDUCATIVA": 3,
    "LOGRO": 5,
    "MATRICULA": 10,
    "PADRE_APODERADO": 13,
    "SECRETARIA": 4,
    "TIENE_PADRES": 2,
    "USUARIO": 10,
}

CONTEOS_ESPERADOS = {
    "CONTACTO_EMERGENCIA": 6,
    "INSTITUCION_EDUCATIVA": 4,
    "PADRE_APODERADO": 10,
    "ESTUDIANTE": 10,
    "ESTUDIANTE_NEE": 9,
    "ESTUDIANTE_HERMANOS_IE": 7,
    "HERMANDAD": 4,
    "TIENE_PADRES": 13,
    "CONSTANCIA_LOGROS": 3,
    "LOGRO": 8,
    "MATRICULA": 13,
    "SECRETARIA": 1,
    "USUARIO": 1,
}


def sentencias(texto: str) -> list[str]:
    """Separa un script SQL respetando DELIMITER (comando del cliente)."""
    delim, buf, out = ";", [], []
    for linea in texto.splitlines():
        s = linea.strip()
        if s.upper().startswith("DELIMITER "):
            delim = s.split(None, 1)[1].strip()
            continue
        if not buf and (not s or s.startswith("--")):
            continue
        buf.append(linea)
        if s.endswith(delim):
            sql = "\n".join(buf).rstrip()
            out.append(sql[: -len(delim)].rstrip())
            buf = []
    if "".join(buf).strip():
        out.append("\n".join(buf).strip())
    return out


def ejecutar_script(cursor, ruta: Path) -> int:
    texto = ruta.read_text(encoding="utf-8")
    total = 0
    for sql in sentencias(texto):
        if not sql.strip():
            continue
        cursor.execute(sql)
        while cursor.nextset():
            pass
        total += 1
    return total


def verificar_esquema(cursor) -> list[str]:
    problemas: list[str] = []
    cursor.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
        (DB_NAME,),
    )
    tablas = {fila[0].upper() for fila in cursor.fetchall()}
    if len(tablas) != 13:
        problemas.append(f"Se esperaban 13 tablas y hay {len(tablas)}: {sorted(tablas)}")
    for tabla, columnas in COLUMNAS_ESPERADAS.items():
        if tabla not in tablas:
            problemas.append(f"Falta la tabla {tabla}.")
            continue
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (DB_NAME, tabla),
        )
        cantidad = cursor.fetchone()[0]
        if cantidad != columnas:
            problemas.append(
                f"{tabla} tiene {cantidad} columnas; se esperaban {columnas}."
            )
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.ROUTINES "
        "WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'",
        (DB_NAME,),
    )
    procedimientos = cursor.fetchone()[0]
    if procedimientos != 5:
        problemas.append(f"Se esperaban 5 procedimientos y hay {procedimientos}.")
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.TRIGGERS "
        "WHERE TRIGGER_SCHEMA = %s",
        (DB_NAME,),
    )
    disparadores = cursor.fetchone()[0]
    if disparadores != 4:
        problemas.append(f"Se esperaban 4 triggers y hay {disparadores}.")
    return problemas


def conteos(cursor) -> dict[str, int]:
    resultado = {}
    for tabla in CONTEOS_ESPERADOS:
        cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`")
        resultado[tabla] = cursor.fetchone()[0]
    return resultado


def escribir_env(puerto: int, clave: str) -> None:
    contenido = (
        "# Generado por scripts/instalar.py\n"
        f"DB_HOST=localhost\n"
        f"DB_PORT={puerto}\n"
        f"DB_USER={DB_USER_APP}\n"
        f"DB_PASSWORD={clave}\n"
        f"DB_NAME={DB_NAME}\n"
        f"DATA_DIR=almacen/solicitudes\n"
    )
    (BASE_DIR / ".env").write_text(contenido, encoding="utf-8")


def main() -> None:
    print("=== Instalación del Sistema de Registro de Matrícula ===")
    servidor = input("Servidor MySQL [localhost]: ").strip() or "localhost"
    puerto_texto = input("Puerto [3306]: ").strip() or "3306"
    try:
        puerto = int(puerto_texto)
    except ValueError:
        print("El puerto debe ser un número.")
        return
    clave_root = getpass.getpass("Contraseña de root (no se muestra ni se guarda): ")

    try:
        cnx = mysql.connector.connect(
            host=servidor,
            port=puerto,
            user="root",
            password=clave_root,
            charset="utf8mb4",
            use_unicode=True,
        )
    except mysql.connector.Error as exc:
        print(f"No se pudo conectar como root: {exc}")
        return
    clave_root = ""

    cursor = cnx.cursor()
    try:
        cursor.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
        existe = cursor.fetchone() is not None
        if existe:
            print(f"La base {DB_NAME} ya existe.")
            confirmacion = input(
                "Escriba BORRAR para eliminarla y recrearla (otra cosa cancela): "
            ).strip()
            if confirmacion != "BORRAR":
                print("Instalación cancelada. No se modificó la base.")
                return
            cursor.execute(f"DROP DATABASE `{DB_NAME}`")
            cnx.commit()
            print("Base anterior eliminada.")

        for nombre in ("01_creacion.sql", "02_datos_prueba.sql", "03_usuario.sql", "04_procedimientos.sql"):
            ruta = SQL_DIR / nombre
            cantidad = ejecutar_script(cursor, ruta)
            cnx.commit()
            print(f"Ejecutado {nombre}: {cantidad} sentencias.")

        clave_app = secrets.token_urlsafe(24)
        cursor.execute(
            f"CREATE USER IF NOT EXISTS '{DB_USER_APP}'@'localhost' IDENTIFIED BY %s",
            (clave_app,),
        )
        cursor.execute(
            f"ALTER USER '{DB_USER_APP}'@'localhost' IDENTIFIED BY %s",
            (clave_app,),
        )
        cursor.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON `{DB_NAME}`.* "
            f"TO '{DB_USER_APP}'@'localhost'"
        )
        cursor.execute("FLUSH PRIVILEGES")
        cnx.commit()
        escribir_env(puerto, clave_app)
        print("Usuario de la aplicación creado y archivo .env escrito.")

        cursor.execute(
            f"USE `{DB_NAME}`"
        )
        print("\n--- Cuenta de la secretaria de prueba ---")
        usuario = input("Usuario [secretaria]: ").strip() or "secretaria"
        dni = input("DNI registrado en SECRETARIA [87733221]: ").strip() or "87733221"
        clave = getpass.getpass("Contraseña de la secretaria: ")
        confirmacion_clave = getpass.getpass("Confirme la contraseña: ")
        if clave != confirmacion_clave:
            print("Las contraseñas no coinciden. No se creó la cuenta.")
        elif len(clave) < 8:
            print("La contraseña debe tener al menos 8 caracteres. No se creó la cuenta.")
        else:
            cursor.execute("SELECT DNI, Nombres, ApellidoPaterno, ApellidoMaterno FROM SECRETARIA WHERE DNI = %s", (dni,))
            fila = cursor.fetchone()
            if not fila:
                print("Ese DNI no existe en SECRETARIA. No se creó la cuenta.")
            else:
                cursor.execute("SELECT IdUsuario FROM USUARIO WHERE NombreUsuario = %s", (usuario,))
                existente = cursor.fetchone()
                if existente:
                    cursor.execute(
                        "UPDATE USUARIO SET ClaveHash = %s, Rol = 'Secretaria', Estado = 'Activo', "
                        "DNI = %s, Nombres = %s, Apellidos = %s WHERE IdUsuario = %s",
                        (
                            generar_hash(clave),
                            dni,
                            fila[1],
                            f"{fila[2]} {fila[3]}",
                            existente[0],
                        ),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI, Nombres, Apellidos) "
                        "VALUES (%s, %s, 'Secretaria', 'Activo', %s, %s, %s)",
                        (
                            usuario,
                            generar_hash(clave),
                            dni,
                            fila[1],
                            f"{fila[2]} {fila[3]}",
                        ),
                    )
                cnx.commit()
                print(f"Cuenta de secretaria '{usuario}' creada/actualizada.")
        clave = confirmacion_clave = ""

        print("\n--- Verificación ---")
        problemas = verificar_esquema(cursor)
        if problemas:
            for problema in problemas:
                print(f"  ERROR: {problema}")
        else:
            print("  Esquema correcto: 13 tablas, columnas exactas, 5 procedimientos y 4 triggers.")
        cursor.execute(f"USE `{DB_NAME}`")
        for tabla, esperado in conteos(cursor).items():
            estado = "OK" if esperado == CONTEOS_ESPERADOS[tabla] else "ERROR"
            print(f"  {tabla}: {esperado} (esperado {CONTEOS_ESPERADOS[tabla]}) [{estado}]")
        print("\nInstalación finalizada. Ejecute: python probar_conexion.py")
    finally:
        cursor.close()
        cnx.close()


if __name__ == "__main__":
    main()
