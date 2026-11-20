"""Pruebas estáticas de la interfaz: tkinter, sin dependencias de escritorio.

El agente no dispone de un intérprete con tkinter, por lo que la interfaz se
verifica revisando el árbol de importaciones y el código fuente. Las pruebas
funcionales de la capa de servicios están en ``test_fase_b`` y ``test_fase_d``.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IGNORADOS = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache", "tesseract"}


def _modulos_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])
    return modulos


def _todos_los_py() -> list[Path]:
    return [
        ruta for ruta in RAIZ.rglob("*.py")
        if not IGNORADOS.intersection(ruta.relative_to(RAIZ).parts)
    ]


class TestInterfazTkinter(unittest.TestCase):
    def test_la_ui_importa_tkinter(self) -> None:
        for ruta in sorted((RAIZ / "app" / "ui").rglob("*.py")):
            if ruta.name == "__init__.py":
                continue
            with self.subTest(modulo=ruta.relative_to(RAIZ)):
                self.assertIn("tkinter", _modulos_importados(ruta))

    def test_no_hay_importaciones_de_otro_toolkit(self) -> None:
        for ruta in _todos_los_py():
            for modulo in _modulos_importados(ruta):
                with self.subTest(modulo=ruta.relative_to(RAIZ), libreria=modulo):
                    self.assertFalse(modulo.startswith(("PySide", "PyQt")))
                    self.assertNotEqual(modulo, "wx")

    def test_login_y_ventana_principal_no_muestran_marca(self) -> None:
        for relativo in ("app/ui/login.py", "app/ui/ventana_principal.py"):
            fuente = (RAIZ / relativo).read_text(encoding="utf-8")
            with self.subTest(relativo=relativo):
                self.assertNotIn("PhotoImage", fuente)
                self.assertNotIn("BitmapImage", fuente)
                self.assertIsNone(re.search(r"\blogo\b", fuente, re.IGNORECASE))
                self.assertNotIn("nombre de la institución", fuente.lower())

    def test_menu_expone_el_nuevo_flujo(self) -> None:
        principal = (RAIZ / "app/ui/ventana_principal.py").read_text(encoding="utf-8")
        bandeja = (RAIZ / "app/ui/padre/mis_solicitudes.py").read_text(encoding="utf-8")
        self.assertIn("Solicitar vacante", principal)
        self.assertIn("Vacantes por atender", principal)
        self.assertIn("Completar matrícula", bandeja)


if __name__ == "__main__":
    unittest.main()
