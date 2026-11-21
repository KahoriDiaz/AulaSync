"""Pruebas de OCR con fallback y automatizaciones de revisión/panel (sin BD)."""
from __future__ import annotations

from pathlib import Path
from unittest import TestCase, mock

from app.servicios import automatizacion, panel
from ocr import diagnostico_ocr, lineas_desde_texto

RAIZ = Path(__file__).resolve().parent.parent

SOLICITUD = {
    "id": "SOL-2027-0001",
    "anio": 2027,
    "dni_responsable": "29481029",
    "contacto_emergencia": {"nombre": "Ejemplo", "celular": "987654321"},
    "padres": [{
        "DNI": "29481029", "FechaNacimiento": "1980-01-01",
        "docs": {"dni": "docs/dni_padre.jpg"},
    }],
    "alumnos": [{
        "ficha": {"DNI": "91234567"},
        "destino": {"nivel": "Secundaria", "grado": "4.°"},
        "docs": {"dni": "docs/dni.jpg", "constancia": "docs/constancia.jpg"},
        "constancia": {"logros": []},
    }],
}
DECISIONES = {
    "91234567": {
        "dni": "91234567", "nivel_ultimo": "Secundaria", "grado_ultimo": "3.°",
        "situacion": "APROBADO", "seccion": "B",
    }
}


class TestFallbackOCR(TestCase):
    def test_texto_pegado_usa_la_misma_entrada_del_extractor(self) -> None:
        lineas = lineas_desde_texto(" DNI 91234567 \n\nCODIGO VIRTUAL D4E5F6A7\n")
        self.assertEqual(lineas, [
            ("DNI 91234567", 100), ("CODIGO VIRTUAL D4E5F6A7", 100)
        ])

    def test_diagnostico_explica_que_falta(self) -> None:
        estado = diagnostico_ocr()
        for clave in ("disponible", "ejecutable", "idioma_spa", "pillow",
                      "pytesseract", "mensaje"):
            self.assertIn(clave, estado)
        self.assertTrue(estado["mensaje"])

    def test_tesseract_portable_y_licencia_se_distribuyen(self) -> None:
        self.assertTrue((RAIZ / "tesseract" / "tesseract.exe").is_file())
        self.assertTrue((RAIZ / "tesseract" / "tessdata" / "spa.traineddata").is_file())
        self.assertTrue((RAIZ / "tesseract" / "LICENCIA_TESSERACT.txt").is_file())
        build = (RAIZ / "build.bat").read_text(encoding="utf-8")
        self.assertIn('tesseract\\tessdata\\spa.traineddata', build)

    def test_asistente_ofrece_diagnostico_y_texto_pegado(self) -> None:
        texto = (RAIZ / "app/ui/padre/asistente_solicitud.py").read_text(encoding="utf-8")
        self.assertIn("mostrar_diagnostico_ocr", texto)
        self.assertIn("pegar_texto_ocr", texto)
        self.assertIn("lineas_desde_texto", texto)
        self.assertNotIn('self.ocr_button["state"] = "disabled"', texto)


class TestSemaphoro(TestCase):
    def _parchear(self, registrado=False, cupos=8, otra=None):
        return (
            mock.patch.object(automatizacion.sol, "listar_solicitudes", return_value=otra or []),
            mock.patch.object(automatizacion, "matriculado_en_anio", return_value=False),
            mock.patch.object(automatizacion, "alumno_registrado", return_value=registrado),
            mock.patch.object(automatizacion.matricula, "grado_siguiente", return_value="4.°"),
            mock.patch.object(automatizacion.matricula, "cupos_seccion",
                              return_value={"Vacantes": cupos, "Matriculados": 30 - cupos}),
        )

    def test_sin_bloqueos_cuando_todo_esta_listo(self) -> None:
        parches = self._parchear()
        with parches[0], parches[1], parches[2], parches[3], parches[4]:
            resultado = automatizacion.evaluar(SOLICITUD, DECISIONES, "SOL-2027-0001")
        self.assertEqual(resultado["estado"], automatizacion.VERDE, resultado)
        self.assertTrue(resultado["por_alumno"]["91234567"]["chequeos"])

    def test_alumno_existente_es_ambar_no_bloqueo(self) -> None:
        parches = self._parchear(registrado=True)
        with parches[0], parches[1], parches[2], parches[3], parches[4]:
            resultado = automatizacion.evaluar(SOLICITUD, DECISIONES, "SOL-2027-0001")
        self.assertEqual(resultado["estado"], automatizacion.AMBAR)
        self.assertIn("se actualizarán", str(resultado))

    def test_cupo_agotado_bloquea_la_aprobacion(self) -> None:
        parches = self._parchear(cupos=0)
        with parches[0], parches[1], parches[2], parches[3], parches[4]:
            resultado = automatizacion.evaluar(SOLICITUD, DECISIONES, "SOL-2027-0001")
        self.assertEqual(resultado["estado"], automatizacion.ROJO)
        self.assertTrue(any(
            chequeo["etiqueta"] == "Cupo" and chequeo["nivel"] == automatizacion.ROJO
            for chequeo in resultado["por_alumno"]["91234567"]["chequeos"]
        ))

    def test_solicitud_duplicada_bloquea_la_aprobacion(self) -> None:
        otra = [{"id": "SOL-2027-0002", "anio": 2027, "alumnos": [{"ficha": {"DNI": "91234567"}}]}]
        parches = self._parchear(otra=otra)
        with parches[0], parches[1], parches[2], parches[3], parches[4]:
            resultado = automatizacion.evaluar(SOLICITUD, DECISIONES, "SOL-2027-0001")
        self.assertEqual(resultado["estado"], automatizacion.ROJO)

    def test_seccion_sugerida_es_la_de_mas_vacantes(self) -> None:
        cupos = [
            {"seccion": "A", "Vacantes": 3},
            {"seccion": "B", "Vacantes": 12},
            {"seccion": "C", "Vacantes": 7},
        ]
        with mock.patch.object(automatizacion.matricula, "verificar_cupos", return_value=cupos):
            self.assertEqual(
                automatizacion.sugerir_seccion(2027, "Secundaria", "4.°"), "B"
            )


class TestPanelRelaciones(TestCase):
    def test_indicadores_y_detalle_son_solo_lectura(self) -> None:
        with mock.patch.object(panel.db, "query_uno", return_value={"total": 3}) as uno, \
             mock.patch.object(panel.db, "query", return_value=[{"DNI": "91234567"}]) as consulta:
            indicadores = panel.indicadores()
            filas = panel.detalle()
        self.assertEqual(len(indicadores), len(panel.INDICADORES))
        self.assertTrue(all(fila["Valor"] == 3 for fila in indicadores))
        self.assertEqual(filas, [{"DNI": "91234567"}])
        self.assertTrue(all(
            str(llamada.args[0]).lstrip().upper().startswith("SELECT")
            for llamada in uno.call_args_list + consulta.call_args_list
        ))

    def test_revision_muestra_semaforo_y_panel_esta_en_el_menu(self) -> None:
        revision = (RAIZ / "app/ui/secretaria/revision.py").read_text(encoding="utf-8")
        principal = (RAIZ / "app/ui/ventana_principal.py").read_text(encoding="utf-8")
        self.assertIn("actualizar_semaforo", revision)
        self.assertIn("sugerir_seccion", revision)
        self.assertIn("Panel de relaciones", principal)
        self.assertIn("PanelRelaciones", principal)
