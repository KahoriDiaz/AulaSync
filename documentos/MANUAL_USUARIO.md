# Manual de usuario — Registro de Matrícula

## 1. Requisitos
- MySQL 8.0 instalado y en ejecución. El ejecutable **no incluye** MySQL.
- Windows 10/11. No hace falta instalar Python para usar `MatriculaApp.exe`.
- Opcional: Tesseract con idioma `spa` para el autocompletado OCR. Si falta, los datos se escriben a mano.

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
- **Bandeja de solicitudes**: revisión y aprobación del flujo del padre.

## 4. Menú del padre
- **Mis solicitudes**: asistente por pasos y seguimiento de sus solicitudes.

## 5. Bandeja de archivos
Las solicitudes viven en `data/solicitudes/` junto al exe:

```
data/solicitudes/
├─ pendientes/
├─ aprobadas/
└─ rechazadas/
```

La importación de listas externas de DNIs solo muestra «En el sistema» / «No está en el sistema».

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
build.bat
empaquetar.bat
```

El ZIP resultante es `Entrega5_GrupoXX.zip` (renombrar `XX` con el número de grupo).
