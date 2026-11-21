# Diseño del flujo por etapas

## 1. Alcance y decisiones generales

- La base de datos sigue siendo **MySQL 8.0 externo**; el ejecutable no la incluye.
- No se crean tablas nuevas ni se ejecuta `ALTER` sobre las 12 tablas del proyecto.
  `USUARIO` es la única tabla adicional y **no se modifica**.
- El código de la aplicación solo ejecuta `SELECT` y `CALL sp_...`; no contiene
  sentencias de escritura directa. Las escrituras las hacen los procedimientos
  almacenados y, cuando corresponde, la transacción única de aprobación.
- **No se agrega el rol `Administrador`.** Solo existen `Padre` y `Secretaria`:
  el alta de cuentas desde el login está restringida a padres/apoderados y la
  revisión de solicitudes a secretaría. Esto evita ampliar la superficie de
  permisos y mantiene el modelo de roles ya validado por los triggers.
- La interfaz no muestra logo ni nombre de la institución. El listado de
  instituciones es un dato administrativo de la secretaría, no una marca.
- El nombre del sistema es **AulaSync**, sin subtítulo. Todas las ventanas
  llevan ese nombre en su título.

## 2. Bandeja de archivos JSON

La solicitud se guarda en `data/solicitudes/` junto al ejecutable:

```
data/solicitudes/
├─ pendientes/     Borrador, Enviada, Observada, Vacante aceptada
├─ aprobadas/      Aprobada
└─ rechazadas/     Rechazada
```

Cada solicitud tiene un `id` `SOL-AAAA-NNNN` y un `solicitud.json`. La etapa se
registra en el campo `etapa`:

| Etapa | Ultimo paso del padre | Quien decide |
|---|---|---|
| `vacante` | Solicitar vacante (formulario corto) | Secretaría acepta, observa o rechaza |
| `matricula` | Completar matrícula (asistente de 5 pasos) | Secretaría aprueba, observa o rechaza |

Los JSON antiguos que no tienen `etapa` se interpretan como `matricula`, para no
perder solicitudes generadas antes de este rediseño.

### Transiciones

```
Borrador → Enviada → Vacante aceptada → Enviada → (Observada ↔ Enviada) → Aprobada
     └────────────── Rechazada (desde cualquier etapa) ──────────────────┘
```

`Vacante aceptada` ya pertenece a la etapa `matricula`. El envío siguiente es la
matrícula enviada; por eso la aprobación solo es válida en etapa `matricula` y
estado `Enviada`.

## 3. Cupos y escrituras en MySQL

- El máximo sigue siendo **30 alumnos por sección**.
- `sp_cupos_seccion` cuenta únicamente matrículas en estado `Matriculado`.
- Aceptar una vacante **no reserva cupo**: solo cambia el JSON y agrega la
  observación con los documentos a presentar. No mueve archivos ni llama a la BD.
- La disponibilidad mostrada al padre y a la secretaría es referencial
  (`30 − matriculados` por sección). Se puede enviar una solicitud aunque diga
  «Sin vacantes».
- Solo la aprobación escribe en MySQL, mediante `matricula.aprobar_y_matricular`,
  que ejecuta todas las sentencias en una sola transacción antes de mover la
  carpeta a `aprobadas/`.

## 4. Permisos

- Los servicios validan el rol en cada operación; la interfaz no es la única
  barrera.
- Un padre solo puede leer y modificar solicitudes cuyo `dni_solicitante` sea
  igual al de su sesión.
- La secretaria ve todas las solicitudes, puede registrar contacto, observar,
  rechazar, aceptar vacantes y aprobar matrículas.
- Para revisar una vacante se distingue alumno nuevo de anterior, se muestra la
  última matrícula y se calcula el grado sugerido con `fn_grado_siguiente`. El
  teléfono y correo se pueden copiar y además existe «Registrar contacto».

## 5. Datos demo

`datos_demo/solicitudes/` contiene ejemplos de todas las combinaciones válidas
de etapa y estado. `build.bat` los copia a la carpeta `data/solicitudes/` del
ejecutable; `empaquetar.ps1` vuelve a reemplazar esa carpeta antes de comprimir
y elimina credenciales o perfiles locales. La bandeja real del desarrollador no
se distribuye.

## 6. Interfaz

- El tema visual vive en `app/ui/tema.py` y se aplica en todas las ventanas:
  fondo cálido, tarjetas con borde suave, botones con jerarquía y tablas con
  filas alternadas y estados resaltados.
- Las acciones principales usan el color primario o el de acento; las acciones
  destructivas se distinguen con el estilo `Danger.TButton`.
- No se usa ningún toolkit distinto de `tkinter`/`ttk`, ni imágenes o recursos
  de marca.

## 7. Automatizaciones visible en la revisión

Las mejoras de automatización (§13.6) se implementan sin escribir en MySQL y sin
quitarle la decisión a la secretaria:

1. **Semáforo de validación** (`app/servicios/automatizacion.py`): comprueba DNI,
   duplicados en `MATRICULA` y en la bandeja, registro previo en `ESTUDIANTE`,
   grado con `fn_grado_siguiente`, cupo con `sp_cupos_seccion`, documentos y
   mayoría de edad del responsable. Rojo bloquea la aprobación; ámbar pide
   confirmación; verde la permite.
2. **Aviso de alumnos existentes**: si el DNI ya está en `ESTUDIANTE`, se muestra
   «Alumno ya registrado: se actualizarán sus datos». Si no está, «Alumno nuevo».
3. **Sección sugerida**: se preselecciona la sección con más vacantes de las
   posibles para el nivel/grado, usando `sp_cupos_seccion` (30 menos matriculados
   en estado `Matriculado`).

Un fallo de MySQL se convierte en aviso ámbar, nunca en un bloqueo silencioso ni
en una excepción que cierre la ventana. La aprobación sigue siendo una única
transacción y sigue moviendo la carpeta solo cuando la secretaria confirma.

## 8. OCR con fallback

El ZIP incluye un `tesseract.exe` portable y `tessdata/spa.traineddata`, por lo
que el autocompletado funciona sin instalación adicional. El módulo `ocr/lector.py`
expone `diagnostico_ocr()`, `probar_ocr()` y `lineas_desde_texto()`:

- **Diagnóstico**: indica si falta el ejecutable, el idioma `spa` o las librerías
  `Pillow`/`pytesseract`, y el botón **Probar OCR** comprueba el funcionamiento
  real con una imagen generada.
- **Fallback**: **Pegar texto OCR** alimenta los mismos extractores con texto
  obtenido en otra herramienta, así que el formulario nunca queda inutilizable.
- **Preprocesamiento**: conversión a escala de grises, autocontraste y escalado,
  con respaldo al idioma `eng` si `spa` no reconoce nada.

Los campos reconocidos se muestran siempre para confirmación antes de aplicarlos.
La consulta del código virtual solo lo copia al portapapeles y abre la URL
configurada: **no** verifica el código contra MINEDU automáticamente.

## 9. Relaciones entre tablas visibles en la interfaz

El menú Reportes incluye **Panel de relaciones** (`app/ui/secretaria/panel.py`),
una vista de solo lectura que hace visible el modelo entity-relacional:

- Indicadores por tabla: `ESTUDIANTE`, `MATRICULA`, `PADRE_APODERADO`,
  `INSTITUCION_EDUCATIVA`, `CONSTANCIA_LOGROS`, `LOGRO`, `TIENE_PADRES`,
  `HERMANDAD`, `ESTUDIANTE_NEE` y `ESTUDIANTE_HERMANOS_IE`.
- Ficha 360° de cada matrícula: cruza `MATRICULA` con `ESTUDIANTE`,
  `PADRE_APODERADO` (responsable), `SECRETARIA`, `INSTITUCION_EDUCATIVA` y,
  mediante subconsultas, `TIENE_PADRES`, `HERMANDAD` y `LOGRO`.

Todas las consultas son `SELECT`; no se agregaron tablas ni se modificaron las
10 consultas representativas de `sql/06_consultas.sql`.
