"""Fase A: crear cuenta de padre/apoderado desde el login."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import db, sesion as sesion_mod
from app.errores import ErrorBaseDatos, ErrorValidacion
from app.seguridad import verificar_clave
from app.servicios import auth, solicitudes as sol

DATOS = {
    "dni": "41234567",
    "nombres": "Carlos Ramírez",
    "celular": "987654321",
    "correo": "carlos@example.com",
    "usuario": "carlos.r",
    "clave": "Clave123",
}


class TestRegistrarPadre(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.parche_ruta = patch.object(auth.config, "USER_DIR", Path(self.temporal.name))
        self.parche_ruta.start()

    def tearDown(self):
        self.parche_ruta.stop()
        self.temporal.cleanup()

    def assert_registro(self, **cambios):
        valores = dict(DATOS)
        valores.update(cambios)
        auth.registrar_padre(
            valores["dni"], valores["usuario"], valores["clave"],
            valores.get("confirmar_clave", valores["clave"]),
            valores["nombres"], valores["celular"], valores["correo"],
        )
        return valores

    def test_registro_correcto_guarda_hash_y_no_clave_texto(self):
        with patch.object(db, "call_proc", return_value=[[{"id_usuario": 9}]]) as llamada:
            self.assert_registro()
        nombre, args = llamada.call_args.args
        self.assertEqual(nombre, "sp_usuario_registrar")
        self.assertEqual(len(args), 3)
        usuario, hash_guardado, dni = args
        self.assertEqual(usuario, "carlos.r")
        self.assertEqual(dni, "41234567")
        self.assertTrue(verificar_clave("Clave123", hash_guardado))
        self.assertTrue(hash_guardado.startswith("pbkdf2$"))
        self.assertNotIn("Clave123", str(llamada.call_args))

    def test_no_se_envia_rol_y_el_procedimiento_lo_fuerza(self):
        parametros = inspect.signature(auth.registrar_padre).parameters
        self.assertNotIn("rol", parametros)
        with patch.object(db, "call_proc", return_value=[]) as llamada:
            self.assert_registro()
        self.assertEqual(llamada.call_args.args[0], "sp_usuario_registrar")
        sql = Path("script_bd/03_procedimientos.sql").read_text(encoding="utf-8")
        cuerpo = sql.split("CREATE PROCEDURE sp_usuario_registrar(")[1].split("END//")[0]
        self.assertIn("'Padre'", cuerpo)

    def test_usuario_repetido(self):
        with patch.object(db, "call_proc", side_effect=ErrorBaseDatos("El nombre de usuario ya existe")):
            with self.assertRaises(ErrorValidacion) as ctx:
                self.assert_registro()
        self.assertIn("usuario ya existe", str(ctx.exception).lower())

    def test_dni_repetido(self):
        with patch.object(db, "call_proc", side_effect=ErrorBaseDatos("El DNI ya tiene una cuenta de usuario")):
            with self.assertRaises(ErrorValidacion) as ctx:
                self.assert_registro()
        self.assertIn("ya tiene una cuenta", str(ctx.exception).lower())

    def test_dni_de_secretaria(self):
        mensaje = "El DNI de un Padre no puede estar registrado en SECRETARIA"
        with patch.object(db, "call_proc", side_effect=ErrorBaseDatos(mensaje)):
            with self.assertRaises(ErrorValidacion) as ctx:
                self.assert_registro()
        self.assertIn("secretaria", str(ctx.exception).lower())

    def test_datos_invalidos_se_rechazan_en_el_servicio(self):
        casos = (
            {"dni": "123"},
            {"celular": "876543210"},
            {"correo": "sin-arroba"},
            {"usuario": "ab"},
            {"clave": "solo letras"},
            {"clave": "12345678"},
            {"confirmar_clave": "OtraClave1"},
            {"nombres": ""},
        )
        with patch.object(db, "call_proc") as llamada:
            for cambios in casos:
                with self.subTest(cambios=cambios):
                    with self.assertRaises(ErrorValidacion):
                        self.assert_registro(**cambios)
        llamada.assert_not_called()

    def test_perfil_guardado_atomicamente_y_con_datos_de_contacto(self):
        with patch.object(db, "call_proc", return_value=[]):
            self.assert_registro()
        ruta = auth.ruta_perfil("41234567")
        self.assertTrue(ruta.is_file())
        self.assertFalse(ruta.with_name(ruta.name + ".tmp").exists())
        perfil = auth.leer_perfil("41234567")
        self.assertEqual(perfil["nombres_apoderado"], "Carlos Ramírez")
        self.assertEqual(perfil["celular"], "987654321")
        self.assertEqual(perfil["correo"], "carlos@example.com")


class TestCuentaNuevaPuedeEntrar(unittest.TestCase):
    def setUp(self):
        self.sesion_original = sesion_mod.autenticacion.sesion_activa
        self.temporal = tempfile.TemporaryDirectory()
        sol.configurar_directorio(Path(self.temporal.name) / "solicitudes")

    def tearDown(self):
        sesion_mod.autenticacion.cerrar_sesion()
        if self.sesion_original:
            sesion_mod.autenticacion.iniciar_sesion(self.sesion_original)
        sol.restaurar_directorio()
        self.temporal.cleanup()

    def test_padre_recien_creado_entra_y_ve_mis_solicitudes_vacio(self):
        hash_guardado = "pbkdf2$1$aabb$aabb"
        fila = {
            "IdUsuario": 9, "NombreUsuario": "carlos.r", "ClaveHash": hash_guardado,
            "Rol": "Padre", "Estado": "Activo", "DNI": "41234567",
        }
        with patch.object(auth, "verificar_clave", return_value=True), patch.object(
            db, "query_uno", return_value=fila
        ), patch.object(db, "call_proc"):
            resultado = auth.login("carlos.r", "Clave123")
        self.assertTrue(resultado.exito)
        self.assertEqual(auth.sesion_actual().rol, "Padre")
        self.assertEqual(sol.listar_solicitudes(), [])


if __name__ == "__main__":
    unittest.main()
