"""Pantalla para subir constancia de logros con OCR (§6.2, §13.6 punto 5).

La secretaria sube una imagen de la constancia, el OCR extrae el código virtual
y los logros, y los muestra en un formulario editable antes de registrar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from app import db, errores
from app.servicios import ocr as servicio_ocr
from app.ui.tema import aplicar_tema, PELIGRO, EXITO, separador, tarjeta


class SubirConstancia(tk.Toplevel):
    def __init__(self, parent, al_guardar=None):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Subir constancia de logros (OCR)")
        self.geometry("900x700")
        self.transient(parent)
        self.al_guardar = al_guardar
        self.ruta_imagen: Path | None = None
        self.campos: dict[str, ttk.Entry] = {}
        self.logros_frame: ttk.Frame | None = None
        self.logros_entries: list[dict[str, ttk.Entry]] = []
        self._construir()

    def _construir(self) -> None:
        # Zona de archivo
        archivo = tarjeta(self)
        archivo.pack(fill="x", padx=8, pady=(8, 6))
        ttk.Label(archivo, text="Constancia de logros (imagen)", style="Card.Seccion.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        barra = ttk.Frame(archivo, style="SobreTarjeta.TFrame")
        barra.pack(fill="x")
        self.lbl_archivo = ttk.Label(
            barra, text="Sin archivo seleccionado", style="Card.Muted.TLabel"
        )
        self.lbl_archivo.pack(side="left", padx=(0, 8))
        ttk.Button(barra, text="Seleccionar imagen", command=self._seleccionar_imagen).pack(
            side="left", padx=(0, 6)
        )
        self.btn_ocr = ttk.Button(
            barra, text="Ejecutar OCR", command=self._ejecutar_ocr, state="disabled"
        )
        self.btn_ocr.pack(side="left")

        # Texto OCR crudo
        ocro = ttk.LabelFrame(self, text="Texto reconocido por OCR (referencia)", padding=6)
        ocro.pack(fill="both", expand=False, padx=8, pady=(0, 6))
        self.txt_ocr = tk.Text(ocro, height=6, wrap="word")
        self.txt_ocr.pack(fill="both", expand=True)

        # Formulario principal
        form = ttk.LabelFrame(self, text="Datos de la constancia (revisar y editar)", padding=6)
        form.pack(fill="x", padx=8, pady=(0, 6))
        columnas = 3
        campos_form = [
            ("codigo_virtual", "Código virtual", 12),
            ("dni_estudiante", "DNI estudiante", 12),
            ("nivel_educativo", "Nivel educativo", 15),
            ("fecha_hora_emision", "Fecha emisión (AAAA-MM-DD HH:MM:SS)", 22),
        ]
        for i, (clave, etiqueta, ancho) in enumerate(campos_form):
            fila = i // columnas
            col = i % columnas
            ttk.Label(form, text=etiqueta, style="Card.TLabel").grid(
                row=fila, column=col * 2, sticky="w", padx=4, pady=3
            )
            ent = ttk.Entry(form, width=ancho)
            ent.grid(row=fila, column=col * 2 + 1, sticky="w", padx=4, pady=3)
            self.campos[clave] = ent

        # Logros (tabla dinámica)
        logros = ttk.LabelFrame(self, text="Logros (agregar/editar filas)", padding=6)
        logros.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.logros_frame = logros
        encabezados = ttk.Frame(logros)
        encabezados.pack(fill="x")
        for col, txt in enumerate(("Año", "Grado", "I.E. (código modular)", "Situación")):
            ttk.Label(encabezados, text=txt, style="Card.TLabel").grid(
                row=0, column=col, sticky="w", padx=4, pady=2
            )
        self.logros_container = ttk.Frame(logros)
        self.logros_container.pack(fill="both", expand=True)
        ttk.Button(
            logros, text="+ Agregar logro", command=self._agregar_logro
        ).pack(anchor="w", padx=4, pady=3)

        # Botones
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Guardar constancia", style="Primary.TButton", command=self._guardar).pack(
            side="right", padx=3
        )
        ttk.Button(btns, text="Limpiar", command=self._limpiar).pack(side="right", padx=3)
        ttk.Button(btns, text="Cerrar", command=self.destroy).pack(side="right", padx=3)

        self.lbl_estado = ttk.Label(self, text="", style="Card.Muted.TLabel")
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 8))

    def _seleccionar_imagen(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de constancia",
            filetypes=(
                ("Imágenes", "*.jpg *.jpeg *.png *.pdf *.bmp *.tif *.tiff"),
                ("Todos", "*.*"),
            ),
            parent=self,
        )
        if not ruta:
            return
        self.ruta_imagen = Path(ruta)
        self.lbl_archivo.config(text=self.ruta_imagen.name)
        self.btn_ocr.config(state="normal" if servicio_ocr.esta_disponible() else "disabled")
        if not servicio_ocr.esta_disponible():
            self.lbl_estado.config(
                text="Tesseract no disponible: complete los campos a mano.", foreground=PELIGRO
            )
        else:
            self.lbl_estado.config(text="")
        self._limpiar_formulario()

    def _ejecutar_ocr(self) -> None:
        if not self.ruta_imagen:
            return
        resultado = servicio_ocr.extraer_texto(self.ruta_imagen)
        self.txt_ocr.delete("1.0", "end")
        if resultado.error:
            self.txt_ocr.insert("1.0", f"Error: {resultado.error}")
            self.lbl_estado.config(text=resultado.error, foreground=PELIGRO)
            return
        self.txt_ocr.insert("1.0", resultado.texto_completo)
        datos = servicio_ocr.procesar_constancia(resultado.texto_completo)
        self._aplicar_datos(datos)
        self.lbl_estado.config(
            text=f"OCR completado. Código: {datos.get('codigo_virtual', '-')}, "
                 f"{len(datos.get('logros', []))} logro(s). Revise y edite antes de guardar.",
            foreground=EXITO,
        )

    def _aplicar_datos(self, datos: dict) -> None:
        for clave in ("codigo_virtual", "dni_estudiante", "nivel_educativo", "fecha_hora_emision"):
            if clave in self.campos and datos.get(clave):
                self.campos[clave].delete(0, "end")
                self.campos[clave].insert(0, str(datos[clave]))
        for logro in datos.get("logros", []):
            self._agregar_logro(
                anio=str(logro.get("anio", "")),
                grado=str(logro.get("grado", "")),
                codigo_ie=str(logro.get("codigo_modular_ie", "")),
                situacion=str(logro.get("situacion", "")),
            )

    def _agregar_logro(self, anio="", grado="", codigo_ie="", situacion="") -> None:
        fila = ttk.Frame(self.logros_container)
        fila.pack(fill="x", pady=1)
        ents = {}
        for col, clave in enumerate(("anio", "grado", "codigo_ie", "situacion")):
            ent = ttk.Entry(fila, width=14 if clave != "codigo_ie" else 16)
            ent.grid(row=0, column=col, padx=2, pady=1)
            ent.insert(0, {"anio": anio, "grado": grado, "codigo_ie": codigo_ie, "situacion": situacion}[clave])
            ents[clave] = ent
        ttk.Button(fila, text="✕", width=3, command=fila.destroy).grid(row=0, column=5, padx=2)
        self.logros_entries.append(ents)

    def _limpiar(self) -> None:
        self._limpiar_formulario()
        self.txt_ocr.delete("1.0", "end")
        for fila in self.logros_container.winfo_children():
            fila.destroy()
        self.logros_entries = []
        self.lbl_estado.config(text="")

    def _limpiar_formulario(self) -> None:
        for ent in self.campos.values():
            ent.delete(0, "end")

    def _guardar(self) -> None:
        valores = {clave: ent.get().strip() for clave, ent in self.campos.items()}
        codigo_virtual = valores.get("codigo_virtual", "")
        dni_estudiante = valores.get("dni_estudiante", "")
        if not codigo_virtual or not dni_estudiante:
            messagebox.showwarning("Atención", "Código virtual y DNI estudiante son obligatorios.", parent=self)
            return
        try:
            db.call_proc(
                "sp_constancia_insertar",
                (
                    codigo_virtual,
                    dni_estudiante,
                    valores.get("nivel_educativo", ""),
                    valores.get("fecha_hora_emision", "") or None,
                ),
            )
            for ents in self.logros_entries:
                db.call_proc(
                    "sp_logro_insertar",
                    (
                        codigo_virtual,
                        int(ents["anio"].get()) if ents["anio"].get().isdigit() else 0,
                        ents["grado"].get(),
                        ents["codigo_ie"].get(),
                        ents["situacion"].get(),
                    ),
                )
            messagebox.showinfo("Éxito", "Constancia y logros registrados correctamente.", parent=self)
            if self.al_guardar:
                self.al_guardar()
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "El año debe ser un número válido.", parent=self)
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)
