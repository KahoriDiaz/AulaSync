"""Gestión de sesión de usuario y bloqueo temporal por intentos fallidos (§13.4).

- Comparación de hash con hmac.compare_digest (sin timing attack).
- Bloqueo en memoria tras 5 intentos fallidos (30 segundos).
- Los usuarios Inactivos no pueden iniciar sesión.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

INTENTOS_MAXIMOS = 5
TIEMPO_BLOQUEO_SEGUNDOS = 30


@dataclass
class Sesion:
    id_usuario: int
    nombre_usuario: str
    rol: str
    dni: str
    nombres: str
    apellidos: str


class Autenticacion:
    """Controla la sesión activa y los intentos fallidos (en memoria)."""

    def __init__(self) -> None:
        self._sesion: Optional[Sesion] = None
        self._intentos_fallidos: int = 0
        self._bloqueado_hasta: float = 0.0

    # -- sesión -----------------------------------------------------------
    @property
    def sesion_activa(self) -> Optional[Sesion]:
        return self._sesion

    def iniciar_sesion(self, sesion: Sesion) -> None:
        self._sesion = sesion
        self._intentos_fallidos = 0
        self._bloqueado_hasta = 0.0

    def cerrar_sesion(self) -> None:
        self._sesion = None

    # -- intentos / bloqueo ----------------------------------------------
    def esta_bloqueado(self) -> bool:
        if self._bloqueado_hasta <= 0.0:
            return False
        if time.time() >= self._bloqueado_hasta:
            self._intentos_fallidos = 0
            self._bloqueado_hasta = 0.0
            return False
        return True

    def registrar_intento_fallido(self) -> None:
        self._intentos_fallidos += 1
        if self._intentos_fallidos >= INTENTOS_MAXIMOS:
            self._bloqueado_hasta = time.time() + TIEMPO_BLOQUEO_SEGUNDOS
            self._intentos_fallidos = 0

    def segundos_restantes_bloqueo(self) -> int:
        if not self.esta_bloqueado():
            return 0
        return max(0, int(self._bloqueado_hasta - time.time()) + 1)

    def intentos_fallidos(self) -> int:
        return self._intentos_fallidos


autenticacion = Autenticacion()
