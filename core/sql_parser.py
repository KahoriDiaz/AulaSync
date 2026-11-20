"""Parser de scripts SQL con soporte para el comando DELIMITER del cliente MySQL."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import mysql.connector


def parsear_script(texto: str) -> list[str]:
    """Divide un script SQL en sentencias respetando DELIMITER.

    El comando DELIMITER es exclusivo del cliente mysql; aquí se interpreta para
    segmentar el script sin enviarlo al servidor. Devuelve sentencias listas para
    cursor.execute().
    """
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


def ejecutar_archivo(
    cnx: mysql.connector.MySQLConnection, ruta: str | Path
) -> int:
    """Ejecuta todos los statements de un archivo SQL en orden. Devuelve el count."""
    texto = Path(ruta).read_text(encoding="utf-8")
    sentencias = parsear_script(texto)
    cursor = cnx.cursor()
    try:
        for sentencia in sentencias:
            cursor.execute(sentencia)
            # Consumir cualquier result set (p. ej. SELECT del script 06) para
            # evitar "Unread result found" al cerrar el cursor.
            if cursor.with_rows:
                cursor.fetchall()
            while cursor.nextset():
                if cursor.with_rows:
                    cursor.fetchall()
        return len(sentencias)
    finally:
        cursor.close()
