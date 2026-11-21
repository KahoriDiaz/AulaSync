"""Asistente de conexion (tkinter): probar conexion y crear/cargar la base de datos."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector

from app.ui.tema import EXITO, PELIGRO, aplicar_tema, separador, tarjeta
from app.config import config
from app.setup_bd import (
    APP_USER,
    crear_base_y_usuario,
    ejecutar_todos_los_scripts,
)


class AsistenteConexion(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        aplicar_tema(self)
        self.title("AulaSync - Asistente de conexión")
        self.resizable(False, False)
        self._construir_ui()

    def _construir_ui(self) -> None:
        marco = ttk.Frame(self, padding=18)
        marco.grid(row=0, column=0, sticky="nsew")

        ttk.Label(marco, text="AulaSync", style="Titulo.TLabel").pack(anchor="w", pady=(0, 8))
        separador(marco).pack(fill="x", pady=(0, 12))

        tarjeta_datos = tarjeta(marco)
        tarjeta_datos.pack(fill="x")
        ttk.Label(
            tarjeta_datos, text="Conexión a MySQL", style="Card.Seccion.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(tarjeta_datos, text="Servidor MySQL", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=3
        )
        self.ent_host = ttk.Entry(tarjeta_datos)
        self.ent_host.insert(0, config.host)
        self.ent_host.grid(row=1, column=1, pady=3, sticky="ew")

        ttk.Label(tarjeta_datos, text="Puerto", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", pady=3
        )
        self.ent_port = ttk.Entry(tarjeta_datos, width=10)
        self.ent_port.insert(0, str(config.port))
        self.ent_port.grid(row=2, column=1, pady=3, sticky="w")

        ttk.Label(
            tarjeta_datos, text="Usuario administrador (ej. root)", style="Card.TLabel"
        ).grid(row=3, column=0, sticky="w", pady=3)
        self.ent_root_user = ttk.Entry(tarjeta_datos)
        self.ent_root_user.insert(0, "root")
        self.ent_root_user.grid(row=3, column=1, pady=3, sticky="ew")

        ttk.Label(
            tarjeta_datos, text="Clave del administrador", style="Card.TLabel"
        ).grid(row=4, column=0, sticky="w", pady=3)
        self.ent_root_pass = ttk.Entry(tarjeta_datos, show="*")
        self.ent_root_pass.grid(row=4, column=1, pady=3, sticky="ew")

        tarjeta_acciones = tarjeta(marco)
        tarjeta_acciones.pack(fill="x", pady=(12, 0))
        ttk.Label(
            tarjeta_acciones, text="Preparar el entorno", style="Card.Seccion.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        self.btn_probar = ttk.Button(
            tarjeta_acciones, text="Probar conexión", command=self.probar_conexion
        )
        self.btn_probar.pack(fill="x", pady=4)

        self.btn_crear = ttk.Button(
            tarjeta_acciones,
            text="Crear base de datos y cargar datos de prueba",
            style="Accent.TButton",
            command=self.crear_y_cargar,
        )
        self.btn_crear.pack(fill="x", pady=4)

        self.lbl_estado = ttk.Label(
            tarjeta_acciones, text="", foreground=EXITO, style="Card.Muted.TLabel",
            wraplength=360,
        )
        self.lbl_estado.pack(fill="x", pady=(8, 0))

        tarjeta_datos.columnconfigure(1, weight=1)

    def _credenciales_root(self) -> tuple[str, int, str, str] | None:
        """Lee los datos del formulario; devuelve None si el puerto no es vÃ¡lido."""
        texto_puerto = self.ent_port.get().strip() or "3306"
        if not texto_puerto.isdigit() or not 0 < int(texto_puerto) < 65536:
            self.lbl_estado.config(text="El puerto debe ser un nÃºmero entre 1 y 65535.",
                                   foreground=PELIGRO)
            messagebox.showerror("Dato invÃ¡lido", "El puerto debe ser un nÃºmero entre 1 y 65535.",
                                 parent=self)
            return None
        return (
            self.ent_host.get().strip() or "localhost",
            int(texto_puerto),
            self.ent_root_user.get().strip() or "root",
            self.ent_root_pass.get(),
        )

    def probar_conexion(self) -> None:
        credenciales = self._credenciales_root()
        if credenciales is None:
            return
        host, port, root_user, root_password = credenciales
        # Conectar como administrador para obtener la versiÃ³n sin depender de que exista la BD
        try:
            root_cnx = mysql.connector.connect(
                host=host,
                port=port,
                user=root_user,
                password=root_password,
                charset="utf8mb4",
                use_unicode=True,
                use_pure=True,
                autocommit=False,
            )
            try:
                cur = root_cnx.cursor()
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
                msg = f"Conexion OK. MySQL {version}"
                try:
                    cur.execute("SELECT COUNT(*) FROM bd_matricula.ESTUDIANTE")
                    msg += f" | estudiantes: {cur.fetchone()[0]}"
                except Exception:
                    msg += " | (bd_matricula no creada aún)"
                cur.close()
                self.lbl_estado.config(text=msg, foreground=EXITO)
                messagebox.showinfo("Conexion", msg)
            finally:
                root_cnx.close()
        except Exception as exc:
            self.lbl_estado.config(text=f"Error: {exc}", foreground=PELIGRO)
            messagebox.showerror("Error de conexion", str(exc))

    def crear_y_cargar(self) -> None:
        credenciales = self._credenciales_root()
        if credenciales is None:
            return
        host, port, root_user, root_password = credenciales
        app_password = "matricula_app"  # clave de la aplicacion (se guarda en config.ini)
        try:
            crear_base_y_usuario(host, port, root_user, root_password, app_password)
            ejecutar_todos_los_scripts(
                config.RECURSOS_DIR,
                host,
                port,
                root_user,
                root_password,
                app_password,
            )
            config.guardar(
                {
                    "host": host,
                    "port": port,
                    "user": APP_USER,
                    "password": app_password,
                    "database": "bd_matricula",
                }
            )
            self.lbl_estado.config(
                text="Base de datos creada y cargada. config.ini guardado.",
                foreground=EXITO,
            )
            messagebox.showinfo(
                "Listo",
                "Base de datos creada y datos de prueba cargados.\n"
                "Ingrese con el DNI de la secretaria demo:\n"
                "DNI 87733221 / clave secretaria123  |  DNI 87733222 / clave secretaria123",
            )
            self.destroy()
        except Exception as exc:
            self.lbl_estado.config(text=f"Error: {exc}", foreground=PELIGRO)
            messagebox.showerror("Error", str(exc))


def main() -> None:
    app = AsistenteConexion()
    app.mainloop()


if __name__ == "__main__":
    main()
