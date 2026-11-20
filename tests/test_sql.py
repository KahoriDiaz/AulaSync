"""Pruebas de BD: procedimientos, triggers y función fn_grado_siguiente (§3.3, §3.4, §13.5).

Cada test corre sobre una conexión propia con autocommit=False y hace ROLLBACK
al terminar, así ningún test contamina los datos de prueba ni el estado de otro
test.
"""
from __future__ import annotations

import unittest

from app.db import conectar


class BaseBD(unittest.TestCase):
    """Cada test usa una conexión propia que se deshace al final."""

    def setUp(self):
        self.cnx = conectar()
        self.cnx.autocommit = False

    def tearDown(self):
        try:
            self.cnx.rollback()
        finally:
            self.cnx.close()

    def _columnas(self, cur):
        return [d[0] for d in cur.description or []]

    def call(self, nombre, parametros=()):
        cur = self.cnx.cursor()
        marcadores = ", ".join(["%s"] * len(parametros))
        cur.execute(f"CALL `{nombre}`({marcadores})", tuple(parametros))
        resultados = []
        while True:
            if cur.with_rows:
                columnas = self._columnas(cur)
                resultados.append(
                    [dict(zip(columnas, fila)) for fila in cur.fetchall()]
                )
            else:
                resultados.append([])
            if not cur.nextset():
                break
        cur.close()
        return resultados

    def query(self, sql, parametros=()):
        cur = self.cnx.cursor(dictionary=True)
        cur.execute(sql, tuple(parametros))
        filas = cur.fetchall()
        cur.close()
        return filas

    def query_uno(self, sql, parametros=()):
        filas = self.query(sql, parametros)
        return filas[0] if filas else None


class TestProcedimientosEstudiante(BaseBD):
    def test_insertar_y_actualizar_estudiante(self):
        out = self.call("sp_estudiante_insertar", [
            "91111111", "M", "Juan", "Perez", "Gomez", "2015-01-10",
            "Cercado", "Arequipa", "Arequipa", "Peru", "Av. Siempre Viva 123", "Cercado",
            "911111111", "juan@mail.com", "Catolica", 1, "SIS", None,
            True, True, True, True, None, "Maria Contacto", "922222222", None, None
        ])
        id_contacto = out[0][0]["id_contacto"] if out and out[0] else None
        self.assertIsNotNone(id_contacto)

        filas = self.query("SELECT DNI FROM ESTUDIANTE WHERE DNI = %s", ("91111111",))
        self.assertEqual(len(filas), 1)

        self.call("sp_estudiante_actualizar", [
            "91111111", "M", "Juan Carlos", "Perez", "Gomez", "2015-01-10",
            "Cercado", "Arequipa", "Arequipa", "Peru", "Av. Siempre Viva 123", "Cercado",
            "911111111", "juan@mail.com", "Catolica", 1, "SIS", None,
            True, True, True, True, id_contacto, None, None
        ])
        fila = self.query_uno("SELECT Nombres FROM ESTUDIANTE WHERE DNI = %s", ("91111111",))
        self.assertEqual(fila["Nombres"], "Juan Carlos")

    def test_eliminar_estudiante_sin_matricula(self):
        self.call("sp_estudiante_insertar", [
            "92222222", "F", "Ana", "Lopez", "Diaz", "2016-02-11",
            "Cayma", "Arequipa", "Arequipa", "Peru", "Calle X 1", "Cayma",
            None, None, None, 1, "SIS", None, True, True, True, True,
            None, "Contacto Ana", "933333333", None, None
        ])
        self.call("sp_estudiante_eliminar", ("92222222",))
        filas = self.query("SELECT COUNT(*) AS total FROM ESTUDIANTE WHERE DNI = %s", ("92222222",))
        self.assertEqual(filas[0]["total"], 0)

    def test_insertar_estudiante_duplicado_falla(self):
        self.call("sp_estudiante_insertar", [
            "93333333", "M", "Luis", "Torres", "Ruiz", "2014-03-12",
            "Miraflores", "Arequipa", "Arequipa", "Peru", "Av. Z 1", "Miraflores",
            None, None, None, 1, "SIS", None, True, True, True, True,
            None, "Contacto Luis", "944444444", None, None
        ])
        with self.assertRaises(Exception):
            self.call("sp_estudiante_insertar", [
                "93333333", "M", "Luis", "Torres", "Ruiz", "2014-03-12",
                "Miraflores", "Arequipa", "Arequipa", "Peru", "Av. Z 1", "Miraflores",
                None, None, None, 1, "SIS", None, True, True, True, True,
                None, "Contacto Luis", "944444444", None, None
            ])


class TestProcedimientosPadre(BaseBD):
    def test_insertar_actualizar_eliminar_padre(self):
        self.call("sp_padre_insertar", [
            "95555555", "M", "Carlos", "Ruiz", "Sosa", "1980-05-05",
            "Ingeniero", "Superior", "Av. Padre 1", "Cercado", "054111111",
            "955555555", "carlos@mail.com"
        ])
        filas = self.query("SELECT DNI FROM PADRE_APODERADO WHERE DNI = %s", ("95555555",))
        self.assertEqual(len(filas), 1)

        self.call("sp_padre_actualizar", [
            "95555555", "M", "Carlos Alberto", "Ruiz", "Sosa", "1980-05-05",
            "Ingeniero", "Superior", "Av. Padre 1", "Cercado", "054111111",
            "955555555", "carlos@mail.com"
        ])
        fila = self.query_uno("SELECT Nombres FROM PADRE_APODERADO WHERE DNI = %s", ("95555555",))
        self.assertEqual(fila["Nombres"], "Carlos Alberto")

        self.call("sp_padre_eliminar", ("95555555",))
        filas = self.query("SELECT COUNT(*) AS total FROM PADRE_APODERADO WHERE DNI = %s", ("95555555",))
        self.assertEqual(filas[0]["total"], 0)

    def test_padre_menor_de_18_falla(self):
        with self.assertRaises(Exception):
            self.call("sp_padre_insertar", [
                "96666666", "M", "Joven", "Perez", "Gomez", "2010-01-01",
                "Estudiante", "Secundaria", "Calle X", "Cercado", None,
                "966666666", None
            ])


class TestProcedimientosMatricula(BaseBD):
    def test_registrar_matricula_exito(self):
        self.call("sp_registrar_matricula", [
            "78120001", 2027, "Inicial", "4 a.", "A", "40125874", "87733221",
            "Cercado", "2027-03-01"
        ])
        filas = self.query(
            "SELECT COUNT(*) AS total FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = 2027",
            ("78120001",)
        )
        self.assertEqual(filas[0]["total"], 1)

    def test_matricula_duplicada_falla(self):
        # 56743478 ya tiene matrícula 2026 (datos de prueba)
        with self.assertRaises(Exception):
            self.call("sp_registrar_matricula", [
                "56743478", 2026, "Secundaria", "3.°", "B", "29481029", "87733221",
                "Paucarpata", "2026-03-12"
            ])

    def test_actualizar_estado_matricula(self):
        self.call("sp_actualizar_estado_matricula", ("56743478", 2026, "Retirado"))
        fila = self.query_uno(
            "SELECT Estado FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = 2026",
            ("56743478",)
        )
        self.assertEqual(fila["Estado"], "Retirado")

        # Retirado no puede volver a Matriculado (trigger)
        with self.assertRaises(Exception):
            self.call("sp_actualizar_estado_matricula", ("56743478", 2026, "Matriculado"))

    def test_cambiar_seccion(self):
        self.call("sp_cambiar_seccion", ("78120001", 2026, "B"))
        fila = self.query_uno(
            "SELECT Seccion FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = 2026",
            ("78120001",)
        )
        self.assertEqual(fila["Seccion"], "B")

    def test_eliminar_matricula_solo_si_no_matriculado(self):
        self.call("sp_actualizar_estado_matricula", ("78120001", 2026, "Retirado"))
        self.call("sp_eliminar_matricula", ("78120001", 2026))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM MATRICULA WHERE DNI_Estudiante = %s AND `AñoEscolar` = 2026",
            ("78120001",)
        )
        self.assertEqual(filas[0]["total"], 0)

    def test_eliminar_matricula_matriculado_falla(self):
        # 56743478, 2026 está Matriculado → el trigger rechaza el DELETE
        with self.assertRaises(Exception):
            self.call("sp_eliminar_matricula", ("56743478", 2026))


class TestProcedimientosRelaciones(BaseBD):
    def test_tiene_padres_insertar_maximo_2(self):
        # 78120003 ya tiene 2 padres (40125874, 41238796)
        with self.assertRaises(Exception):
            self.call("sp_tiene_padres_insertar", ("78120003", "97777777"))

    def test_hermandad_hermano_de_si_mismo_falla(self):
        with self.assertRaises(Exception):
            self.call("sp_hermandad_insertar", ("56743478", "56743478"))

    def test_hermandad_insertar_y_eliminar(self):
        self.call("sp_hermandad_insertar", ("78120007", "78120008"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM HERMANDAD WHERE DNI_HermanoA = %s AND DNI_HermanoB = %s",
            ("78120007", "78120008")
        )
        self.assertEqual(filas[0]["total"], 1)
        self.call("sp_hermandad_eliminar", ("78120007", "78120008"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM HERMANDAD WHERE DNI_HermanoA = %s AND DNI_HermanoB = %s",
            ("78120007", "78120008")
        )
        self.assertEqual(filas[0]["total"], 0)

    def test_nee_insertar_y_eliminar(self):
        self.call("sp_nee_insertar", ("78120007", "Dislexia"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = %s AND NecesidadEducativaEspecial = 'Dislexia'",
            ("78120007",)
        )
        self.assertEqual(filas[0]["total"], 1)
        self.call("sp_nee_eliminar", ("78120007", "Dislexia"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = %s AND NecesidadEducativaEspecial = 'Dislexia'",
            ("78120007",)
        )
        self.assertEqual(filas[0]["total"], 0)

    def test_hermanos_ie_insertar_y_eliminar(self):
        self.call("sp_hermanos_ie_insertar", ("78120007", "Secundaria"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = %s AND NivelHermano = 'Secundaria'",
            ("78120007",)
        )
        self.assertEqual(filas[0]["total"], 1)
        self.call("sp_hermanos_ie_eliminar", ("78120007", "Secundaria"))
        filas = self.query(
            "SELECT COUNT(*) AS total FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = %s AND NivelHermano = 'Secundaria'",
            ("78120007",)
        )
        self.assertEqual(filas[0]["total"], 0)


class TestProcedimientosConstanciaLogroIE(BaseBD):
    def test_ie_insertar_actualizar_eliminar(self):
        self.call("sp_ie_insertar", ("09999999", "I.E. Test", "Particular"))
        filas = self.query("SELECT COUNT(*) AS total FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", ("09999999",))
        self.assertEqual(filas[0]["total"], 1)

        self.call("sp_ie_actualizar", ("09999999", "I.E. Test Modificada", "Estatal"))
        fila = self.query_uno("SELECT NombreIE FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", ("09999999",))
        self.assertEqual(fila["NombreIE"], "I.E. Test Modificada")

        self.call("sp_ie_eliminar", ("09999999",))
        filas = self.query("SELECT COUNT(*) AS total FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = %s", ("09999999",))
        self.assertEqual(filas[0]["total"], 0)

    def test_constancia_logro_insertar_actualizar_eliminar(self):
        self.call("sp_constancia_insertar", ("T1EST001", "78120007", "Secundaria", "2026-03-01 10:00:00"))
        self.call("sp_logro_insertar", ("T1EST001", 2025, "4.°", "0567890", "APROBADO"))
        filas = self.query("SELECT COUNT(*) AS total FROM LOGRO WHERE CodigoVirtual = %s AND `AñoEscolar` = 2025", ("T1EST001",))
        self.assertEqual(filas[0]["total"], 1)

        self.call("sp_logro_actualizar", ("T1EST001", 2025, "4.°", "0567890", "REQUIERE RECUPERACIÓN"))
        fila = self.query_uno("SELECT SituacionFinal FROM LOGRO WHERE CodigoVirtual = %s AND `AñoEscolar` = 2025", ("T1EST001",))
        self.assertEqual(fila["SituacionFinal"], "REQUIERE RECUPERACIÓN")

        self.call("sp_logro_eliminar", ("T1EST001", 2025))
        self.call("sp_constancia_eliminar", ("T1EST001",))
        filas = self.query("SELECT COUNT(*) AS total FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = %s", ("T1EST001",))
        self.assertEqual(filas[0]["total"], 0)


class TestProcedimientosUsuario(BaseBD):
    def test_usuario_registrar_obtener_cambiar(self):
        out = self.call("sp_usuario_registrar", ("usuario_test", "hash_falso", "98888888"))
        id_usuario = out[0][0]["id_usuario"] if out and out[0] else None
        self.assertIsNotNone(id_usuario)

        filas = self.call("sp_usuario_obtener", ("usuario_test",))
        self.assertEqual(len(filas[0]), 1)
        self.assertEqual(filas[0][0]["Rol"], "Padre")

        self.call("sp_usuario_cambiar_clave", (id_usuario, "hash_nuevo"))
        fila = self.query_uno("SELECT ClaveHash FROM USUARIO WHERE IdUsuario = %s", (id_usuario,))
        self.assertEqual(fila["ClaveHash"], "hash_nuevo")

        self.call("sp_usuario_cambiar_estado", (id_usuario, "Inactivo"))
        fila = self.query_uno("SELECT Estado FROM USUARIO WHERE IdUsuario = %s", (id_usuario,))
        self.assertEqual(fila["Estado"], "Inactivo")

    def test_usuario_registrar_rol_siempre_padre(self):
        out = self.call("sp_usuario_registrar", ("usuario_test2", "hash_x", "98888887"))
        id_usuario = out[0][0]["id_usuario"] if out and out[0] else None
        fila = self.query_uno("SELECT Rol FROM USUARIO WHERE IdUsuario = %s", (id_usuario,))
        self.assertEqual(fila["Rol"], "Padre")


class TestProcedimientosReportes(BaseBD):
    def test_cupos_seccion(self):
        filas = self.call("sp_cupos_seccion", (2026, "Secundaria", "3.°", "B"))
        self.assertGreaterEqual(len(filas[0]), 1)
        self.assertIn("Vacantes", filas[0][0])

    def test_padron(self):
        filas = self.call("sp_padron", (2026, None, None, None))
        self.assertGreaterEqual(len(filas[0]), 1)

    def test_verificar_matriculados(self):
        filas = self.call("sp_verificar_matriculados", (2025, 2026))
        self.assertGreaterEqual(len(filas[0]), 1)
        situaciones = {f["Situacion"] for f in filas[0]}
        self.assertTrue(situaciones.issubset({"Continúa", "Nuevo", "Sin matrícula en el año actual"}))


class TestFuncionGradoSiguiente(BaseBD):
    def test_secuencia_grados(self):
        casos = [
            ("Inicial", "3 a.", "APROBADO", "4 a."),
            ("Inicial", "4 a.", "APROBADO", "5 a."),
            ("Inicial", "5 a.", "APROBADO", "1.°"),
            ("Primaria", "1.°", "APROBADO", "2.°"),
            ("Primaria", "6.°", "APROBADO", "1.°"),
            ("Secundaria", "1.°", "APROBADO", "2.°"),
            ("Secundaria", "5.°", "APROBADO", "EGRESADO"),
            ("Secundaria", "3.°", "REQUIERE RECUPERACIÓN", "3.°"),
            ("Primaria", "2.°", "REQUIERE RECUPERACIÓN", "2.°"),
        ]
        for nivel, grado, situacion, esperado in casos:
            fila = self.query_uno(
                "SELECT fn_grado_siguiente(%s, %s, %s) AS siguiente",
                (nivel, grado, situacion)
            )
            self.assertEqual(fila["siguiente"], esperado, f"{nivel} {grado} {situacion}")

    def test_grado_invalido_falla(self):
        with self.assertRaises(Exception):
            self.query_uno("SELECT fn_grado_siguiente('Inicial', '9 x.', 'APROBADO')")

    def test_nivel_invalido_falla(self):
        with self.assertRaises(Exception):
            self.query_uno("SELECT fn_grado_siguiente('Universitario', '1.°', 'APROBADO')")


class TestTriggers(BaseBD):
    def test_estudiante_fecha_futura_falla(self):
        with self.assertRaises(Exception):
            self.call("sp_estudiante_insertar", [
                "97777777", "M", "Futuro", "Perez", "Gomez", "2030-01-01",
                "Cercado", "Arequipa", "Arequipa", "Peru", "Av. X 1", "Cercado",
                None, None, None, 1, "SIS", None, True, True, True, True,
                None, "Contacto", "911111111", None, None
            ])

    def test_estudiante_dni_igual_apoderado_falla(self):
        with self.assertRaises(Exception):
            self.call("sp_estudiante_insertar", [
                "97777778", "M", "Mismo", "Perez", "Gomez", "2015-01-01",
                "Cercado", "Arequipa", "Arequipa", "Peru", "Av. X 1", "Cercado",
                None, None, None, 1, "SIS", None, True, True, True, True,
                None, "Contacto", "911111111", None, "97777778"
            ])

    def test_matricula_grado_invalido_para_nivel_falla(self):
        with self.assertRaises(Exception):
            self.call("sp_registrar_matricula", [
                "78120001", 2027, "Inicial", "1.°", "A", "40125874", "87733221",
                "Cercado", "2027-03-01"
            ])

    def test_usuario_secretaria_dni_no_en_secretaria_falla(self):
        import mysql.connector
        cnx = mysql.connector.connect(
            host="localhost", port=3306, user="root", password="root",
            database="bd_matricula", use_pure=True, charset="utf8mb4", autocommit=False,
        )
        try:
            cur = cnx.cursor()
            with self.assertRaises(Exception):
                cur.execute(
                    "INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI) "
                    "VALUES ('sec_falsa','hash','Secretaria','Activo','91111111')"
                )
            cnx.rollback()
        finally:
            cnx.close()


class TestSinDMLEnCodigo(unittest.TestCase):
    def test_no_dml_en_app(self):
        import re
        from pathlib import Path
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


class TestMatriculaAppSinDMLDirecto(unittest.TestCase):
    def test_matricula_app_no_puede_insert(self):
        cnx = conectar()
        try:
            cur = cnx.cursor()
            with self.assertRaises(Exception):
                cur.execute("INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI) VALUES ('x','y','Padre','Activo','00000000')")
            cnx.rollback()
        finally:
            cnx.close()


if __name__ == "__main__":
    unittest.main()
