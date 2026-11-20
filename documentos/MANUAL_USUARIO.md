# Manual de usuario — Registro de Matrícula

## 1. Requisitos
- MySQL 8.0 instalado y en ejecución. El ejecutable **no incluye** MySQL.
- Windows 10/11. No hace falta instalar Python para usar `MatriculaApp.exe`.
- Opcional: Tesseract con idioma `spa` para el autocompletado OCR. Si falta, los datos se escriben a mano.
- Los campos de DNI solo aceptan números y como máximo 8 dígitos; no permite escribir ni pegar más.

## 2. Primera ejecución
1. Descomprimir `Entrega5_GrupoXX.zip`.
2. Entrar en `MatriculaApp/` y ejecutar `MatriculaApp.exe`.
3. Aparece el **asistente de conexión**:
   - Probar la conexión con el usuario administrador de MySQL.
   - Presionar **Crear base de datos y cargar datos de prueba**.
   - Se crea `bd_matricula`, el usuario `matricula_app` y se cargan los scripts `01` a `06`.
4. Se crea `config.ini` **junto al exe** con el usuario `matricula_app`. La clave del administrador nunca se guarda.
5. Ingresar con los usuarios demo:

| Usuario | Clave | Rol |
|---|---|---|
| `secretaria` | `secretaria123` | Secretaria |
| `padre_demo` | `padre123` | Padre |

## 3. Menú de la secretaria
- **Mantenimiento**: alta, edición y baja de estudiantes, padres/apoderados e instituciones.
- **Procesos → Distribución**: cupos por nivel/grado/sección, padrón y cambio de sección.
- **Procesos → Listas y comparación**: padrón, comparación de dos años e importación de DNIs (solo compara; no modifica la BD).
- **Reportes**: las 10 consultas representativas con sus parámetros y botones **Excel / PDF / CSV**.
- **Bandeja de solicitudes**: revisión de todas las etapas.
- **Vacantes por atender**: filtra la bandeja en la etapa Vacante. Muestra el
  contador de solicitudes Enviadas y resalta con ⚠ las que llevan más de 7 días
  sin respuesta.

### Revisión de una vacante
Al abrir una solicitud de vacante se muestra si el alumno es nuevo o anterior,
su última matrícula, el grado sugerido con `fn_grado_siguiente` y las vacantes
por sección (`30 − matriculados`). El teléfono y correo se pueden copiar; el
botón **Registrar contacto** deja constancia sin cambiar el estado. Después se
puede **Aceptar vacante**, **Observar** o **Rechazar**. Aceptar solo actualiza el
JSON: no reserva cupo ni escribe en la BD.

## 4. Menú del padre
- **Solicitar vacante**: formulario corto con contacto, hijos (hasta 6 hermanos)
  y nivel/grado deseado. Se puede enviar aunque el aviso diga «Sin vacantes».
- **Mis solicitudes**: seguimiento de cada solicitud. Cuando la secretaria acepta
  la vacante aparece **Completar matrícula**: se abre el asistente de 5 pasos con
  el nivel y grado ya definidos, bloqueados. El envío queda en etapa Matrícula y
  la aprobación la hace la secretaria.

## 5. Bandeja de archivos
Las solicitudes viven en `data/solicitudes/` junto al exe:

```
data/solicitudes/
├─ pendientes/
├─ aprobadas/
└─ rechazadas/
```

La importación de listas externas de DNIs solo muestra «En el sistema» / «No está en el sistema».

El paquete incluye ejemplos ficticios en `datos_demo/solicitudes/` que `build.bat`
copia a `data/solicitudes/` del ejecutable. Cubren todas las combinaciones válidas
de etapa y estado; por eso la bandeja ya viene con ejemplos para revisar.

## 5.1 Decisiones de diseño
No se crearon tablas nuevas ni se modificaron las 12 tablas; `USUARIO` es la
única tabla adicional y no se toca. No existe el rol `Administrador`: el alta de
cuentas desde el login solo crea padres/apoderados y la revisión es exclusiva de
secretaría. El máximo por sección sigue siendo 30 y una vacante aceptada no
reserva cupo. El detalle está en `documentos/DISENO_FLUJO.md`.

## 6. OCR opcional
Si se incluye la carpeta `tesseract/` con `tesseract.exe` y `tessdata/spa.traineddata`, la aplicación la detecta sola. También se puede indicar la ruta en `config.ini`:

```ini
[app]
tesseract_cmd = C:\Ruta\a\tesseract.exe
```

Si no está disponible, el botón de OCR se desactiva y los campos se llenan manualmente.

## 7. Regenerar el entregable
```bat
pip install -r requirements.txt
.\build.bat
.\empaquetar.bat
```

En PowerShell hace falta el `.\` delante; en CMD basta con `build.bat`.

No hace falta tener `pyinstaller.exe` en el PATH: `build.bat` usa `python -m PyInstaller`.

El ZIP resultante es `Entrega5_GrupoXX.zip` (renombrar `XX` con el número de grupo).
