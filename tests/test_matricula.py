"""Login por DNI, validaciones y matrícula (sin MySQL: la BD se simula)."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

from app import db
from app.errores import ErrorBaseDatos, ErrorValidacion, traducir_error
from app.seguridad import hash_clave
from app.servicios import auth, mantenimiento, matricula
from app.sesion import autenticacion


def _estudiante(**cambios):
    datos = {
        "DNI": "91234567", "Sexo": "F", "Nombres": "Ana", "ApellidoPaterno": "Quispe",
        "ApellidoMaterno": "Paz", "FechaNacimiento": "2015-05-10", "DistritoNacimiento": "Cayma",
        "ProvinciaNacimiento": "Arequipa", "DepartamentoNacimiento": "Arequipa",
        "PaisNacimiento": "Perú", "DomicilioActual": "Av. 1", "DistritoDomicilio": "Cayma",
        "LugarQueOcupa": "1", "ViveConPadre": "Sí", "ViveConMadre": "Sí", "ElPadreVive": "Sí",
        "LaMadreVive": "Sí", "NombreContactoEmergencia": "Rosa Paz", "CelularEmergencia": "912345678",
    }
    datos.update(cambios)
    return datos


def _madre(**cambios):
    datos = {
        "DNI": "41234567", "Sexo": "F", "Nombres": "María", "ApellidoPaterno": "Paz",
        "ApellidoMaterno": "Rojas", "FechaNacimiento": "1985-01-02", "GradoInstruccion": "Superior",
        "DomicilioActual": "Av. 1", "DistritoDomicilio": "Cayma", "Celular": "987654321",
    }
    datos.update(cambios)
    return datos


class CursorFalso:
    """Registra cada sentencia; los SELECT no encuentran nada (todo es nuevo)."""

    with_rows = False

    def __init__(self):
        self.sentencias: list[tuple[str, tuple]] = []

    def execute(self, sql, parametros=()):
        self.sentencias.append((sql, tuple(parametros)))

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def nextset(self):
        return False


class TestLoginPorDni(unittest.TestCase):
    def setUp(self):
        autenticacion.cerrar_sesion()
        autenticacion._intentos_fallidos = 0
        autenticacion._bloqueado_hasta = 0.0
        self.fila = {
            "IdUsuario": 1, "NombreUsuario": "secretaria", "ClaveHash": hash_clave("secretaria123"),
            "Rol": "Secretaria", "Estado": "Activo", "DNI": "87733221", "Nombres": "Claudia",
            "ApellidoPaterno": "Acosta", "ApellidoMaterno": "Neira",
        }

    def tearDown(self):
        autenticacion.cerrar_sesion()

    def test_login_correcto_con_dni(self):
        with patch.object(db, "query_uno", return_value=self.fila) as consulta, \
             patch.object(db, "call_proc"):
            resultado = auth.login("87733221", "secretaria123")
        self.assertTrue(resultado.exito)
        self.assertEqual(consulta.call_args.args[1], ("87733221",))
        self.assertEqual(auth.sesion_actual().dni, "87733221")

    def test_clave_incorrecta_mensaje_generico(self):
        with patch.object(db, "query_uno", return_value=self.fila):
            resultado = auth.login("87733221", "otra")
        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.mensaje, "DNI o clave incorrectos.")

    def test_nombre_de_usuario_no_sirve_como_dni(self):
        with patch.object(db, "query_uno") as consulta:
            resultado = auth.login("secretaria", "secretaria123")
        self.assertFalse(resultado.exito)
        consulta.assert_not_called()

    def test_usuario_inactivo_no_entra(self):
        self.fila["Estado"] = "Inactivo"
        with patch.object(db, "query_uno", return_value=self.fila):
            self.assertFalse(auth.login("87733221", "secretaria123").exito)

    def test_bloqueo_tras_cinco_intentos(self):
        with patch.object(db, "query_uno", return_value=self.fila):
            for _ in range(5):
                auth.login("87733221", "mala")
            resultado = auth.login("87733221", "secretaria123")
        self.assertFalse(resultado.exito)
        self.assertGreater(resultado.segundos_bloqueo, 0)


class TestValidaciones(unittest.TestCase):
    def test_estudiante_valido(self):
        self.assertEqual(matricula.validar_estudiante(_estudiante()), [])

    def test_estudiante_invalido(self):
        for cambios in ({"DNI": "123"}, {"Sexo": "X"}, {"FechaNacimiento": "2999-01-01"},
                        {"CelularEmergencia": "123"}, {"Nombres": ""}, {"LugarQueOcupa": "0"}):
            with self.subTest(cambios=cambios):
                self.assertTrue(matricula.validar_estudiante(_estudiante(**cambios)))

    def test_padre_mayor_de_edad(self):
        self.assertEqual(matricula.validar_padre(_madre()), [])
        menor = date(date.today().year - 17, 1, 1).isoformat()
        self.assertTrue(matricula.validar_padre(_madre(FechaNacimiento=menor)))
        self.assertTrue(matricula.validar_padre(_madre(Celular="12")))

    def test_responsable_debe_ser_padre_o_madre(self):
        errores = matricula.validar_datos({
            "estudiante": _estudiante(), "madre": _madre(), "responsable": "11111111",
        })
        self.assertTrue(any("responsable" in e for e in errores))

    def test_traduccion_de_signal(self):
        exc = type("E", (Exception,), {})()
        exc.errno, exc.msg = 1644, "La sección ya alcanzó el máximo de 30 estudiantes"
        self.assertEqual(traducir_error(exc), "La sección ya alcanzó el máximo de 30 estudiantes")


class TestGuardarDatos(unittest.TestCase):
    def test_orden_de_claves_foraneas_en_una_transaccion(self):
        cursor = CursorFalso()

        @contextmanager
        def transaccion():
            yield cursor

        datos = {
            "estudiante": _estudiante(), "padre": None, "madre": _madre(),
            "responsable": "41234567",
            "ie": {"CodigoModularIE": "0234567", "NombreIE": "IE Arequipa", "TipoIE": "Estatal"},
            "constancia": {"CodigoVirtual": "ab12cd34", "NivelEducativo": "Primaria",
                           "FechaHoraEmision": None},
            "logros": [{"AñoEscolar": 2026, "GradoCursado": "3.°", "CodigoModularIE": "0234567",
                        "NombreIE": "IE Arequipa", "SituacionFinal": "APROBADO"}],
        }
        with patch.object(db, "transaccion", transaccion):
            matricula.guardar_datos(datos)
        llamadas = [sql.split("`")[1] for sql, _ in cursor.sentencias if sql.startswith("CALL")]
        self.assertEqual(llamadas, [
            "sp_padre_insertar", "sp_ie_insertar", "sp_ie_insertar", "sp_estudiante_insertar",
            "sp_tiene_padres_insertar", "sp_constancia_insertar", "sp_logro_insertar",
        ])
        estudiante = next(p for sql, p in cursor.sentencias if "sp_estudiante_insertar" in sql)
        self.assertEqual(len(estudiante), 27)
        self.assertEqual(estudiante[-1], "41234567")  # apoderado = responsable
        constancia = next(p for sql, p in cursor.sentencias if "sp_constancia_insertar" in sql)
        self.assertEqual(constancia[0], "AB12CD34")

    def test_datos_invalidos_no_abren_transaccion(self):
        with patch.object(db, "transaccion") as transaccion:
            with self.assertRaises(ErrorValidacion):
                matricula.guardar_datos({"estudiante": _estudiante(DNI="1"), "madre": _madre(),
                                         "responsable": "41234567"})
        transaccion.assert_not_called()


class TestRegistrarMatricula(unittest.TestCase):
    def _registrar(self, **cambios):
        datos = dict(dni_estudiante="91234567", anio=2027, nivel="Primaria", grado="4.°",
                     seccion="A", dni_responsable="41234567", dni_secretaria="87733221")
        datos.update(cambios)
        return matricula.registrar_matricula(**datos)

    def test_exito_llama_al_procedimiento(self):
        with patch.object(db, "call_proc", return_value=[]) as llamada:
            self._registrar()
        nombre, parametros = llamada.call_args.args
        self.assertEqual(nombre, "sp_registrar_matricula")
        self.assertEqual(parametros[:7], ("91234567", 2027, "Primaria", "4.°", "A", "41234567", "87733221"))
        self.assertEqual(parametros[7], "Virtual")

    def test_matricula_duplicada_muestra_el_mensaje(self):
        error = ErrorBaseDatos("El estudiante ya tiene una matrícula en ese año escolar")
        with patch.object(db, "call_proc", side_effect=error):
            with self.assertRaisesRegex(ErrorBaseDatos, "ya tiene una matrícula"):
                self._registrar()

    def test_seccion_llena_muestra_el_mensaje(self):
        error = ErrorBaseDatos("La sección ya alcanzó el máximo de 30 estudiantes")
        with patch.object(db, "call_proc", side_effect=error):
            with self.assertRaisesRegex(ErrorBaseDatos, "máximo de 30"):
                self._registrar()

    def test_seccion_inexistente_para_el_nivel(self):
        with patch.object(db, "call_proc") as llamada:
            with self.assertRaises(ErrorValidacion):
                self._registrar(nivel="Inicial", grado="4 a.", seccion="D")
        llamada.assert_not_called()

    def test_seccion_llena_tiene_cero_vacantes(self):
        with patch.object(db, "call_proc", return_value=[[{"Matriculados": 30, "Vacantes": 0}]]):
            self.assertEqual(matricula.cupos_seccion(2027, "Primaria", "4.°", "A")["Vacantes"], 0)
        with patch.object(db, "call_proc", return_value=[]):
            self.assertEqual(matricula.cupos_seccion(2027, "Primaria", "4.°", "A")["Vacantes"], 30)

    def test_grado_que_corresponde(self):
        with patch.object(db, "query_uno", return_value={"grado": "1.°"}):
            self.assertEqual(matricula.grado_que_corresponde("Primaria", "6.°", "APROBADO"),
                             ("Secundaria", "1.°"))


class TestMantenimiento(unittest.TestCase):
    def test_todas_las_tablas_tienen_insertar_y_eliminar(self):
        for clave, tabla in mantenimiento.TABLAS.items():
            with self.subTest(tabla=clave):
                self.assertTrue(tabla.sp_insertar)
                self.assertTrue(tabla.sp_eliminar)

    def test_cambiar_estado_y_seccion_de_matricula(self):
        anterior = {"DNI_Estudiante": "78120001", "AñoEscolar": "2026", "Estado": "Matriculado",
                    "Seccion": "A"}
        with patch.object(db, "call_proc") as llamada:
            mantenimiento.actualizar("matricula", anterior, {"Estado": "Retirado", "Seccion": "B"})
        self.assertEqual([c.args[0] for c in llamada.call_args_list],
                         ["sp_actualizar_estado_matricula", "sp_cambiar_seccion"])

    def test_insertar_secretaria_valida_el_dni(self):
        with patch.object(db, "call_proc") as llamada:
            with self.assertRaises(ErrorValidacion):
                mantenimiento.insertar("secretaria", {"DNI": "12", "Nombres": "A",
                                                      "ApellidoPaterno": "B", "ApellidoMaterno": "C"})
            mantenimiento.insertar("secretaria", {"DNI": "87733229", "Nombres": "A",
                                                  "ApellidoPaterno": "B", "ApellidoMaterno": "C"})
        llamada.assert_called_once_with("sp_secretaria_insertar", ("87733229", "A", "B", "C"))


if __name__ == "__main__":
    unittest.main()
