"""Pruebas de integracion con la base de datos real (unittest, carpeta tests/).

Se ejecutan contra bd_matricula ya cargada (scripts 01 a 06).
No dependen de servicios inexistentes: solo acceden a la BD directamente.
"""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

from app.config import config
from app.db import conectar, query, query_uno

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
    "USUARIO": 2,
}


def _conectar():
    return conectar()


class TestIntegracionBD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cnx = _conectar()

    def test_conexion_y_version(self):
        filas = query("SELECT VERSION() AS v")
        self.assertTrue(filas[0]["v"].startswith("8.0."), filas[0]["v"])

    def test_trece_tablas(self):
        filas = query(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
        )
        self.assertEqual(len(filas), 13, [f["TABLE_NAME"] for f in filas])

    def test_cinco_procedimientos_originales_existen(self):
        esperados = {
            "sp_registrar_matricula", "sp_actualizar_estado_matricula",
            "sp_buscar_estudiante", "sp_listar_hermanos", "sp_verificar_matriculados",
        }
        filas = query(
            "SELECT ROUTINE_NAME FROM information_schema.ROUTINES "
            "WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'PROCEDURE'"
        )
        nombres = {f["ROUTINE_NAME"] for f in filas}
        self.assertTrue(
            esperados.issubset(nombres),
            f"Faltan procedimientos: {esperados - nombres}",
        )

    def test_conteos_de_datos_de_prueba(self):
        for tabla, esperado in CONTEOS_ESPERADOS.items():
            filas = query(f"SELECT COUNT(*) AS total FROM `{tabla}`")
            self.assertEqual(
                filas[0]["total"], esperado, f"{tabla} no coincide"
            )

    def test_usuarios_demo_existen(self):
        filas = query(
            "SELECT NombreUsuario, Rol, DNI FROM USUARIO ORDER BY NombreUsuario"
        )
        nombres = {f["NombreUsuario"] for f in filas}
        self.assertIn("secretaria", nombres)
        self.assertIn("padre_demo", nombres)
        sec = [f for f in filas if f["NombreUsuario"] == "secretaria"][0]
        self.assertEqual(sec["Rol"], "Secretaria")
        self.assertEqual(sec["DNI"], "87733221")
        pad = [f for f in filas if f["NombreUsuario"] == "padre_demo"][0]
        self.assertEqual(pad["Rol"], "Padre")
        self.assertEqual(pad["DNI"], "29481029")

    def test_las_diez_consultas_devuelven_filas(self):
        # Consulta 1
        filas = query(
            "SELECT e.DNI FROM MATRICULA m INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI "
            "WHERE m.`AñoEscolar` = 2026 AND m.Nivel = 'Secundaria' AND m.Grado = '3.°' "
            "AND m.Seccion = 'B' AND m.Estado = 'Matriculado' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 2
        filas = query(
            "SELECT DNI FROM ESTUDIANTE WHERE ApellidoPaterno = 'Diaz' "
            "AND ApellidoMaterno = 'Acosta' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 3
        filas = query(
            "SELECT c.CodigoVirtual FROM CONSTANCIA_LOGROS c "
            "WHERE c.DNI_Estudiante = '74922482' AND c.NivelEducativo = 'Secundaria' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 4
        filas = query(
            "SELECT h.DNI_HermanoB AS DNI_Hermano FROM HERMANDAD h "
            "WHERE h.DNI_HermanoA = '56743478' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 5
        filas = query(
            "SELECT m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, COUNT(*) AS total "
            "FROM MATRICULA m GROUP BY m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 6
        filas = query(
            "SELECT e.DNI FROM ESTUDIANTE e WHERE e.DNI_Apoderado = '56345876' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 7
        filas = query(
            "SELECT m.DNI_Estudiante FROM MATRICULA m WHERE m.DNI_Responsable = '29481029' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 8
        filas = query(
            "SELECT e.DNI FROM MATRICULA m INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI "
            "WHERE m.DNI_Estudiante = '56743478' ORDER BY m.`AñoEscolar` DESC LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 9
        filas = query(
            "SELECT c.CodigoVirtual FROM CONSTANCIA_LOGROS c WHERE c.DNI_Estudiante = '74922482' LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)
        # Consulta 10
        filas = query(
            "SELECT s.DNI FROM MATRICULA m INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI "
            "WHERE m.`AñoEscolar` = 2026 GROUP BY s.DNI LIMIT 1"
        )
        self.assertGreaterEqual(len(filas), 1)

    def test_no_hay_dml_en_codigo_python(self):
        """Regex sin distincion de mayusculas sobre app/*.prohibe INSERT/UPDATE/DELETE."""
        patrones = [
            re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
            re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
            re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
        ]
        base = Path(__file__).resolve().parent.parent / "app"
        for py in base.rglob("*.py"):
            texto = py.read_text(encoding="utf-8")
            for patron in patrones:
                self.assertIsNone(
                    patron.search(texto),
                    f"DML prohibido en {py}: {patron.pattern}",
                )

    def test_usuario_matricula_app_sin_dml_directo(self):
        """El usuario matricula_app no puede hacer INSERT directo (solo SELECT/EXECUTE)."""
        cnx = _conectar()
        try:
            cur = cnx.cursor()
            with self.assertRaises(Exception):
                cur.execute("INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI) VALUES ('x','y','Padre','Activo','00000000')")
            cnx.rollback()
        finally:
            cnx.close()


if __name__ == "__main__":
    unittest.main()
