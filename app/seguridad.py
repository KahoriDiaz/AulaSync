"""Hash y verificacion de contrasenias con PBKDF2-HMAC-SHA256.

Formato guardado: pbkdf2$<iteraciones>$<sal_hex>$<hash_hex>
"""
from __future__ import annotations

import hashlib
import hmac
import os

ITERACIONES = 200_000
SEPARADOR = "$"


def hash_clave(clave_texto: str) -> str:
    """Genera el hash PBKDF2-HMAC-SHA256 de una contrasenia en texto plano."""
    sal = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", clave_texto.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2{SEPARADOR}{ITERACIONES}{SEPARADOR}{sal.hex()}{SEPARADOR}{dk.hex()}"


def verificar_clave(clave_texto: str, hash_guardado: str) -> bool:
    """Verifica una contrasenia contra su hash usando hmac.compare_digest (sin timing attack)."""
    try:
        partes = hash_guardado.split(SEPARADOR)
        if len(partes) != 4 or partes[0] != "pbkdf2":
            return False
        _, iteraciones_s, sal_hex, hash_hex = partes
        iteraciones = int(iteraciones_s)
        sal = bytes.fromhex(sal_hex)
        hash_esperado = bytes.fromhex(hash_hex)
    except (ValueError, IndexError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", clave_texto.encode("utf-8"), sal, iteraciones)
    return hmac.compare_digest(dk, hash_esperado)
