"""Pruebas de la fase 6: distribución, listas, reportes y exportación."""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db
from app.errores import ErrorValidacion
from app.servicios import distribucion, exportar, listas, reportes

RAIZ = Path(__file__).resolve().parent.parent

FILAS = [
    {"DNI": "12345678", "ApellidoPaterno": "Diaz", "Nombres": "Ana", "Seccion": "B", "AñoEscolar": 2026},
    {"DNI": "87654321", "ApellidoPaterno": "Pérez", "Nombres": "Luis", "Seccion": "A", "AñoEscolar": 2026},
]


def _consultas_del_script() -> list[str]:
    texto = (RAIZ / "sql" / "06_consultas.sql").read_text(encoding="utf-8")
    sin_comentarios = "\n".join(
        linea for linea in texto.splitlines() if not linea.lstrip().startswith("--")
    )
    return [
        parte.strip() for parte in sin_comentarios.split(";")
        if parte.strip().upper().startswith("SELECT")
    ]


def _normal(texto: str) -> str:
    return " ".join(texto.split())


class TestReportes(unittest.TestCase):
    def test_diez_consultas_con_seis_join_y_valores_del_script(self):
        consultas = reportes.todos()
        self.assertEqual(len(consultas), 10)
        self.assertEqual([c.numero for c in consultas], list(range(1, 11)))
        self.assertGreaterEqual(sum(c.joins > 0 for c in consultas), 6)
        esperados = [
            (2026, "Secundaria", "3.°", "B", "Matriculado"),
            ("Diaz", "Acosta"),
            ("74922482", "Secundaria"),
            ("56743478",),
            (),
            ("56345876",),
            ("29481029",),
            ("56743478",),
            ("74922482",),
            (2026,),
        ]
        for consulta, valores in zip(consultas, esperados):
            self.assertEqual(consulta.defaults, valores)
            self.assertEqual(len(consulta.parametros), len(valores))
        script = _consultas_del_script()
        self.assertEqual(len(script), 10)
        for consulta, original in zip(consultas, script):
            self.assertEqual(
                _normal(reportes.sql_con_valores_por_defecto(consulta)),
                _normal(original),
                f"La consulta {consulta.numero} no coincide con 06_consultas.sql",
            )

    def test_ejecutar_usa_valores_por_defecto_y_repite_el_dni_en_la_consulta_4(self):
        vistos = []

        def falso(sql, parametros=()):
            vistos.append((sql, tuple(parametros)))
            return [{"DNI": "12345678"}]

        with patch.object(db, "query", side_effect=falso):
            for numero in range(1, 11):
                filas = reportes.ejecutar(numero)
                self.assertEqual(filas, [{"DNI": "12345678"}])
        self.assertEqual(len(vistos), 10)
        self.assertEqual(
            vistos[0][1], (2026, "Secundaria", "3.°", "B", "Matriculado")
        )
        self.assertEqual(vistos[3][1], ("56743478", "56743478"))
        self.assertEqual(vistos[9][1], (2026,))
        self.assertIn("%s", vistos[3][0])

    def test_parametros_incorrectos_y_consulta_inexistente(self):
        with self.assertRaises(ErrorValidacion):
            reportes.obtener(11)
        with self.assertRaises(ErrorValidacion):
            reportes.ejecutar(1, (2026,))


class TestExportar(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name)

    def tearDown(self):
        self.temporal.cleanup()

    def test_csv_excel_y_pdf_se_generan_no_vacios(self):
        columnas = ("DNI", "ApellidoPaterno", "Nombres")
        csv_destino = exportar.exportar(FILAS, self.ruta / "lista.csv", "csv", "Padrón", columnas)
        self.assertGreater(csv_destino.stat().st_size, 0)
        self.assertIn("12345678", csv_destino.read_text(encoding="utf-8-sig"))

        xlsx_destino = exportar.exportar(FILAS, self.ruta / "lista.xlsx", "xlsx", "Padrón", columnas)
        self.assertGreater(xlsx_destino.stat().st_size, 0)
        self.assertEqual(xlsx_destino.read_bytes()[:2], b"PK")
        from openpyxl import load_workbook

        libro = load_workbook(xlsx_destino)
        try:
            self.assertEqual(tuple(c.value for c in libro.active[1]), columnas)
        finally:
            libro.close()

        pdf_destino = exportar.exportar(FILAS, self.ruta / "lista.pdf", "pdf", "Padrón", columnas)
        self.assertGreater(pdf_destino.stat().st_size, 0)
        self.assertEqual(pdf_destino.read_bytes()[:4], b"%PDF")

    def test_nombre_seguro_y_formatos(self):
        self.assertEqual(exportar.nombre_archivo('Padrón/2026: "A"', "pdf"), "Padrón_2026_ _A_.pdf")
        with self.assertRaises(ErrorValidacion):
            exportar.exportar(FILAS, self.ruta / "x.txt", "txt")
        with self.assertRaises(ErrorValidacion):
            exportar.nombre_archivo("x", "docx")

    def test_preparar_con_filas_vacias_y_valores_especiales(self):
        encabezados, cuerpo = exportar.preparar([{"A": None, "B": 7}])
        self.assertEqual(encabezados, ("A", "B"))
        self.assertEqual(cuerpo, [["", "7"]])
        self.assertEqual(exportar.a_csv([]), "")
        self.assertEqual(exportar.preparar([])[0], ())


class TestDistribucion(unittest.TestCase):
    def test_anios_y_resumen_con_cupos_vacios(self):
        with patch.object(db, "query", return_value=[{"anio": 2025}, {"anio": 2026}]):
            anios = distribucion.anios()
        self.assertEqual(anios[0], max(anios))

        with patch.object(db, "call_proc", return_value=[]):
            filas = distribucion.resumen(2027, "Inicial")
        self.assertEqual(len(filas), 3 * 2)
        self.assertTrue(all(f["Matriculados"] == 0 for f in filas))
        self.assertTrue(all(f["Vacantes"] == 30 for f in filas))
        self.assertEqual(
            [f["Seccion"] for f in filas[:2]], ["A", "B"]
        )

    def test_cupos_y_sugerir_seccion(self):
        respuestas = [
            [[{"Matriculados": 25, "Vacantes": 5}]],
            [[{"Matriculados": 2, "Vacantes": 28}]],
        ]
        with patch.object(db, "call_proc", side_effect=respuestas):
            sugerida = distribucion.sugerir_seccion(2026, "Inicial", "3 a.")
        self.assertEqual(sugerida, "B")

        with patch.object(db, "call_proc", return_value=[[{
            "AñoEscolar": 2026, "Nivel": "Primaria", "Grado": "2.°",
            "Seccion": "C", "Matriculados": 31, "Vacantes": 0,
        }]]):
            fila = distribucion.cupos_seccion(2026, "Primaria", "2.°", "C")
        self.assertEqual(fila["Matriculados"], 31)

    def test_padron_y_mover_seccion_valida_nivel(self):
        filas_padron = [{"DNI": "12345678", "Nivel": "Secundaria", "Seccion": "A"}]
        with patch.object(db, "call_proc", return_value=[filas_padron]) as proc:
            self.assertEqual(distribucion.padron(2026, "Secundaria", "1.°", "A"), filas_padron)
            proc.assert_called_with("sp_padron", (2026, "Secundaria", "1.°", "A"))

        with patch.object(db, "query_uno", return_value={"Nivel": "Inicial"}):
            with patch.object(db, "call_proc") as proc:
                with self.assertRaises(ErrorValidacion):
                    distribucion.mover_seccion("12345678", 2026, "D")
                proc.assert_not_called()
        with patch.object(db, "query_uno", return_value={"Nivel": "Secundaria"}):
            with patch.object(db, "call_proc") as proc:
                distribucion.mover_seccion("12345678", 2026, "c")
            proc.assert_called_with("sp_cambiar_seccion", ("12345678", 2026, "C"))


class TestListas(unittest.TestCase):
    COMPARACION = [
        dict(zip(listas.COLUMNAS_COMPARACION, (
            "1", "Diaz", "Acosta", "Ana", "Primaria", "6.°", "Secundaria", "1.°", "Continúa",
        ))),
        dict(zip(listas.COLUMNAS_COMPARACION, (
            "2", "Pérez", "Luis", "Luis", "", "", "Primaria", "1.°", "Nuevo",
        ))),
        dict(zip(listas.COLUMNAS_COMPARACION, (
            "3", "Pérez", "Luis", "María", "Primaria", "6.°", "", "", "Sin matrícula en el año actual",
        ))),
    ]

    def test_comparar_muestra_no_continua_y_resume(self):
        with patch.object(db, "call_proc", return_value=[self.COMPARACION]) as proc:
            filas = listas.comparar(2025, 2026)
        proc.assert_called_with("sp_verificar_matriculados", (2025, 2026))
        self.assertEqual([f["Situacion"] for f in filas], ["Continúa", "Nuevo", "No continúa"])
        for fila in filas:
            self.assertEqual(tuple(fila), listas.COLUMNAS_COMPARACION)
        self.assertEqual(
            listas.resumen(filas), {"Continúa": 1, "Nuevo": 1, "No continúa": 1}
        )

    def test_importar_csv_y_excel_y_comparar_con_patron(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal)
            csv_archivo = ruta / "dnis.csv"
            csv_archivo.write_text(
                "DNI\n12345678\n\n87654321\n12345678\nno-valido\n", encoding="utf-8-sig"
            )
            self.assertEqual(
                listas.importar_dnis(csv_archivo), ["12345678", "87654321"]
            )

            from openpyxl import Workbook

            libro = Workbook()
            libro.active.append(["DNI"])
            libro.active.append([12345678])
            xlsx_archivo = ruta / "dnis.xlsx"
            libro.save(xlsx_archivo)
            libro.close()
            self.assertEqual(listas.importar_dnis(xlsx_archivo), ["12345678"])

            with patch.object(db, "call_proc", return_value=[[FILAS[0]]]):
                comparados = listas.comparar_con_lista_externa(
                    ["12345678", "99999999"], 2026
                )
            self.assertEqual(
                [f["Situacion"] for f in comparados],
                ["En el sistema", "No está en el sistema"],
            )
            self.assertEqual(comparados[0]["Seccion"], "B")
            with self.assertRaises(ErrorValidacion):
                listas.importar_dnis(ruta / "no_existe.csv")

    def test_importacion_no_escribe_en_la_base(self):
        with patch.object(db, "call_proc", return_value=[[]]) as proc:
            listas.comparar_con_lista_externa(["12345678"], 2026)
            proc.assert_called_once()
            self.assertEqual(proc.call_args.args[0], "sp_padron")


class TestReglasFase6(unittest.TestCase):
    def test_sin_dml_en_el_codigo(self):
        patron = re.compile(
            r"\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b", re.IGNORECASE
        )
        encontrados = []
        for archivo in (RAIZ / "app").rglob("*.py"):
            if patron.search(archivo.read_text(encoding="utf-8")):
                encontrados.append(str(archivo.relative_to(RAIZ)))
        self.assertEqual(encontrados, [])

    def test_las_pantallas_de_procesos_no_leen_solicitudes(self):
        nombres = {
            "distribucion.py", "listas.py", "reportes.py", "bandeja.py", "revision.py"
        }
        for nombre in nombres - {"bandeja.py", "revision.py"}:
            texto = (RAIZ / "app" / "ui" / "secretaria" / nombre).read_text(encoding="utf-8")
            self.assertNotIn("solicitudes", texto)


if __name__ == "__main__":
    unittest.main()
