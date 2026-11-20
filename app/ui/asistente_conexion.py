"""Asistente de conexion (tkinter): probar conexion y crear/cargar la base de datos."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import mysql.connector

from app import db
from app.config import config
from app.setup_bd import (
    APP_USER,
    crear_base_y_usuario,
    ejecutar_todos_los_scripts,
)


class AsistenteConexion(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Registro de Matricula - Asistente de conexion")
        self.resizable(False, False)
        self._construir_ui()

    def _construir_ui(self) -> None:
        marco = ttk.Frame(self, padding=20)
        marco.grid(row=0, column=0, sticky="nsew")

        ttk.Label(marco, text="Servidor MySQL").grid(row=0, column=0, sticky="w", pady=3)
        self.ent_host = ttk.Entry(marco)
        self.ent_host.insert(0, config.host)
        self.ent_host.grid(row=0, column=1, pady=3, sticky="ew")

        ttk.Label(marco, text="Puerto").grid(row=1, column=0, sticky="w", pady=3)
        self.ent_port = ttk.Entry(marco, width=10)
        self.ent_port.insert(0, str(config.port))
        self.ent_port.grid(row=1, column=1, pady=3, sticky="w")

        ttk.Label(marco, text="Usuario administrador (ej. root)").grid(
            row=2, column=0, sticky="w", pady=3
        )
        self.ent_root_user = ttk.Entry(marco)
        self.ent_root_user.insert(0, "root")
        self.ent_root_user.grid(row=2, column=1, pady=3, sticky="ew")

        ttk.Label(marco, text="Clave del administrador").grid(row=3, column=0, sticky="w", pady=3)
        self.ent_root_pass = ttk.Entry(marco, show="*")
        self.ent_root_pass.grid(row=3, column=1, pady=3, sticky="ew")

        ttk.Separator(marco, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=12
        )

        self.btn_probar = ttk.Button(
            marco, text="Probar conexion", command=self.probar_conexion
        )
        self.btn_probar.grid(row=5, column=0, columnspan=2, pady=6, sticky="ew")

        self.btn_crear = ttk.Button(
            marco,
            text="Crear base de datos y cargar datos de prueba",
            command=self.crear_y_cargar,
        )
        self.btn_crear.grid(row=6, column=0, columnspan=2, pady=6, sticky="ew")

        self.lbl_estado = ttk.Label(marco, text="", foreground="#1a7a1a")
        self.lbl_estado.grid(row=7, column=0, columnspan=2, pady=10)

        marco.columnconfigure(1, weight=1)

    def _credenciales_root(self) -> tuple[str, int, str, str]:
        return (
            self.ent_host.get().strip() or "localhost",
            int(self.ent_port.get().strip() or "3306"),
            self.ent_root_user.get().strip() or "root",
            self.ent_root_pass.get(),
        )

    def probar_conexion(self) -> None:
        host, port, root_user, root_password = self._credenciales_root()
        try:
            cnx = db.conectar()  # usa config (matricula_app); puede fallar si no existe BD
        except Exception:
            cnx = None
        # Conectar como root para obtener la version sin depender de que exista la BD
        try:
            import mysql.connector

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
                self.lbl_estado.config(text=msg, foreground="#1a7a1a")
                messagebox.showinfo("Conexion", msg)
            finally:
                root_cnx.close()
        except Exception as exc:
            self.lbl_estado.config(text=f"Error: {exc}", foreground="#a31a1a")
            messagebox.showerror("Error de conexion", str(exc))

    def crear_y_cargar(self) -> None:
        host, port, root_user, root_password = self._credenciales_root()
        app_password = "matricula_app"  # clave de la aplicacion (se guarda en config.ini)
        try:
            crear_base_y_usuario(host, port, root_user, root_password, app_password)
            ejecutar_todos_los_scripts(
                Path(__file__).resolve().parent.parent,
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
                foreground="#1a7a1a",
            )
            messagebox.showinfo(
                "Listo",
                "Base de datos creada y datos de prueba cargados.\n"
                "Usuarios demo: secretaria / secretaria123  |  padre_demo / padre123",
            )
            self.destroy()
            from main import iniciar_aplicacion

            iniciar_aplicacion()
        except Exception as exc:
            self.lbl_estado.config(text=f"Error: {exc}", foreground="#a31a1a")
            messagebox.showerror("Error", str(exc))


def main() -> None:
    app = AsistenteConexion()
    app.mainloop()


if __name__ == "__main__":
    main()
