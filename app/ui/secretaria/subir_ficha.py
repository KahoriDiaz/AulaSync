"""Pantalla para subir ficha de alumno con OCR (§6.2, §13.6 punto 5).

La secretaria sube una imagen de la ficha física, el OCR extrae los datos y
los muestra en un formulario editable antes de registrar al estudiante.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from app import errores
from app.servicios import estudiantes, ocr as servicio_ocr
from app.ui.tema import aplicar_tema, PELIGRO, EXITO, separador, tarjeta


class SubirFichaAlumno(tk.Toplevel):
    def __init__(self, parent, al_guardar=None):
        super().__init__(parent)
        aplicar_tema(self)
        self.title("AulaSync - Subir ficha de alumno (OCR)")
        self.geometry("1000x800")
        self.transient(parent)
        self.al_guardar = al_guardar
        self.ruta_imagen: Path | None = None
        self.campos: dict[str, ttk.Entry] = {}
        self._construir()

    def _construir(self) -> None:
        # Zona de archivo
        archivo = tarjeta(self)
        archivo.pack(fill="x", padx=8, pady=(8, 6))
        ttk.Label(archivo, text="Ficha de alumno (imagen)", style="Card.Seccion.TLabel").pack(
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

        # Formulario editable con todos los campos del procedimiento (27)
        form = ttk.LabelFrame(self, text="Datos del alumno (revisar y editar antes de guardar)", padding=6)
        form.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Cada campo: (clave, etiqueta, ancho)
        campos_form = [
            ("DNI", "DNI (8 dígitos)", 10),
            ("Sexo", "Sexo (M/F)", 5),
            ("Nombres", "Nombres", 20),
            ("ApellidoPaterno", "Apellido paterno", 18),
            ("ApellidoMaterno", "Apellido materno", 18),
            ("FechaNacimiento", "Fecha nacimiento (AAAA-MM-DD)", 14),
            ("DistritoNacimiento", "Distrito nacimiento", 15),
            ("ProvinciaNacimiento", "Provincia nacimiento", 15),
            ("DepartamentoNacimiento", "Departamento nacimiento", 15),
            ("PaisNacimiento", "País nacimiento", 12),
            ("DomicilioActual", "Domicilio actual", 25),
            ("DistritoDomicilio", "Distrito domicilio", 15),
            ("Celular", "Celular (9 dígitos)", 12),
            ("CorreoElectronico", "Correo electrónico", 20),
            ("Religion", "Religión", 12),
            ("LugarQueOcupa", "Lugar que ocupa (n.º)", 8),
            ("TipoAtencion", "Tipo atención (ESSALUD/SIS/Otros)", 15),
            ("EnfermedadCronica", "Enfermedad crónica", 20),
            ("ViveConPadre", "Vive con padre (Sí/No)", 10),
            ("ViveConMadre", "Vive con madre (Sí/No)", 10),
            ("ElPadreVive", "El padre vive (Sí/No)", 10),
            ("LaMadreVive", "La madre vive (Sí/No)", 10),
            ("NombreContactoEmergencia", "Contacto emergencia (nombre)", 22),
            ("CelularEmergencia", "Contacto emergencia (celular)", 12),
            ("CodigoModularIE", "Código modular I.E.", 12),
            ("DNI_Apoderado", "DNI apoderado", 10),
        ]

        columnas = 4
        for i, (clave, etiqueta, ancho) in enumerate(campos_form):
            fila = i // columnas
            col = i % columnas
            bloque = ttk.Frame(form)
            bloque.grid(row=fila, column=col, sticky="w", padx=6, pady=4)
            ttk.Label(bloque, text=etiqueta, style="Card.TLabel", width=ancho).pack(anchor="w")
            ent = ttk.Entry(bloque, width=max(10, ancho - 2))
            ent.pack(anchor="w", pady=(1, 0))
            self.campos[clave] = ent

        # Botones
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Guardar alumno", style="Primary.TButton", command=self._guardar).pack(
            side="right", padx=3
        )
        ttk.Button(btns, text="Limpiar", command=self._limpiar).pack(side="right", padx=3)
        ttk.Button(btns, text="Cerrar", command=self.destroy).pack(side="right", padx=3)

        self.lbl_estado = ttk.Label(self, text="", style="Card.Muted.TLabel")
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 8))

    def _seleccionar_imagen(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de ficha",
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
        datos = servicio_ocr.procesar_ficha_alumno(resultado.texto_completo)
        self._aplicar_datos(datos)
        self.lbl_estado.config(
            text=f"OCR completado. Se extrajeron {len(datos)} campo(s). Revise y edite antes de guardar.",
            foreground=EXITO,
        )

    def _aplicar_datos(self, datos: dict) -> None:
        for clave, valor in datos.items():
            if clave in self.campos and valor:
                self.campos[clave].delete(0, "end")
                self.campos[clave].insert(0, str(valor))

    def _limpiar(self) -> None:
        self._limpiar_formulario()
        self.txt_ocr.delete("1.0", "end")
        self.lbl_estado.config(text="")

    def _limpiar_formulario(self) -> None:
        for ent in self.campos.values():
            ent.delete(0, "end")

    def _guardar(self) -> None:
        valores = {clave: ent.get().strip() for clave, ent in self.campos.items()}
        dni = valores.get("DNI", "")
        if not dni:
            messagebox.showwarning("Atención", "El DNI es obligatorio.", parent=self)
            return

        # 27 parámetros en el orden exacto de sp_estudiante_insertar
        parametros = (
            dni,                                                  # 1 p_dni
            valores.get("Sexo", "") or "M",                       # 2 p_sexo
            valores.get("Nombres", ""),                           # 3 p_nombres
            valores.get("ApellidoPaterno", ""),                   # 4 p_apellido_paterno
            valores.get("ApellidoMaterno", ""),                   # 5 p_apellido_materno
            valores.get("FechaNacimiento", ""),                   # 6 p_fecha_nacimiento
            valores.get("DistritoNacimiento", ""),                # 7 p_distrito_nacimiento
            valores.get("ProvinciaNacimiento", ""),               # 8 p_provincia_nacimiento
            valores.get("DepartamentoNacimiento", ""),            # 9 p_departamento_nacimiento
            valores.get("PaisNacimiento", ""),                    # 10 p_pais_nacimiento
            valores.get("DomicilioActual", ""),                   # 11 p_domicilio_actual
            valores.get("DistritoDomicilio", ""),                 # 12 p_distrito_domicilio
            valores.get("Celular", ""),                           # 13 p_celular
            valores.get("CorreoElectronico", ""),                 # 14 p_correo_electronico
            valores.get("Religion", ""),                          # 15 p_religion
            int(valores.get("LugarQueOcupa", "1") or "1"),        # 16 p_lugar_que_ocupa
            valores.get("TipoAtencion", ""),                      # 17 p_tipo_atencion
            valores.get("EnfermedadCronica", ""),                 # 18 p_enfermedad_cronica
            self._a_bool(valores.get("ViveConPadre", "")),        # 19 p_vive_con_padre
            self._a_bool(valores.get("ViveConMadre", "")),        # 20 p_vive_con_madre
            self._a_bool(valores.get("ElPadreVive", "")),         # 21 p_el_padre_vive
            self._a_bool(valores.get("LaMadreVive", "")),         # 22 p_la_madre_vive
            None,                                                 # 23 p_id_contacto (NULL = crear nuevo)
            valores.get("NombreContactoEmergencia", ""),          # 24 p_nombre_contacto
            valores.get("CelularEmergencia", ""),                 # 25 p_celular_contacto
            valores.get("CodigoModularIE", ""),                   # 26 p_codigo_modular_ie
            valores.get("DNI_Apoderado", ""),                     # 27 p_dni_apoderado
        )
        try:
            estudiantes.insertar_estudiante(parametros)
            messagebox.showinfo("Éxito", "Alumno registrado correctamente.", parent=self)
            if self.al_guardar:
                self.al_guardar()
            self.destroy()
        except errores.ErrorApp as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    @staticmethod
    def _a_bool(valor: str) -> bool:
        return str(valor or "").strip().lower() in ("sí", "si", "true", "1", "s", "yes")
