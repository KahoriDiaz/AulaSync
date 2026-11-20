# ENTREGA 5 — Aplicativo de escritorio de Registro de Matrícula (sin frameworks)

> **PRECEDENCIA:** si hay conflicto, manda la sección 14, luego la 13, luego las secciones 0 a 12.
> Instrucción para OpenCode: este archivo reemplaza el plan anterior (Flask/web).
> Reutiliza del repositorio actual SOLO lo que sirva: scripts SQL de las 12 tablas, datos de prueba, las 10 consultas y los tests de base de datos.
> Elimina Flask, plantillas HTML, Bootstrap, Werkzeug y PySide6. Trabaja por fases y haz un commit al terminar cada una. No avances de fase si los tests de la actual no pasan.

---

## 0. Restricciones DURAS (la consigna de la docente)

1. **Prohibido usar frameworks.** No Flask, Django, Qt/PySide, Kivy, Avalonia, Electron, ni ORM (SQLAlchemy, etc.).
   Permitido: librería estándar de Python (`tkinter`, `ttk`, `json`, `configparser`, `hashlib`, `hmac`, `pathlib`, `unittest`, `webbrowser`, `shutil`, `datetime`, `os`) y estas librerías de apoyo (no son frameworks): `mysql-connector-python` (driver), `openpyxl` (Excel), `reportlab` (PDF), `Pillow` y `pytesseract` (OCR), `pyinstaller` (solo para empaquetar).
2. **No crear tablas nuevas.** El diseño son las 12 tablas de la Entrega 4 (no hacer `ALTER` sobre ellas). La única tabla adicional permitida es `USUARIO`.
3. **Todo INSERT / UPDATE / DELETE se hace con procedimientos almacenados y triggers.** El código Python NO puede contener sentencias `INSERT`, `UPDATE` ni `DELETE`; solo `CALL sp_...` y `SELECT`.
4. La aplicación **no muestra el logo ni el nombre de la institución** (condición del proyecto).
5. Debe correr **localmente** y entregarse como **ZIP completo + .exe** (Windows). Quien lo revise debe poder ejecutarlo sin instalar Python.
6. Lenguaje de la interfaz y de los comentarios: español. Código fuente documentado (docstrings en cada módulo, clase y función pública).

## 1. Stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Interfaz | `tkinter` + `ttk` (Treeview, Notebook, Combobox) |
| Base de datos | MySQL 8.0 (InnoDB) — se mantiene el modelo físico |
| Driver | `mysql-connector-python` (`use_pure=True`, `charset='utf8mb4'`, `autocommit=False`) |
| OCR (opcional) | Tesseract + `pytesseract` + `Pillow` (idioma `spa`) |
| Exportar | `openpyxl` (xlsx), `reportlab` (pdf), `csv` (estándar) |
| Contraseñas | `hashlib.pbkdf2_hmac` (SHA-256, sal aleatoria, ≥ 200 000 iteraciones). Formato guardado: `pbkdf2$<iter>$<sal_hex>$<hash_hex>` |
| Empaquetado | PyInstaller `--onedir --windowed` → `MatriculaApp.exe` |

## 2. Estructura del proyecto

```
matricula_app/
├─ main.py                      # punto de entrada
├─ config.ini.example           # servidor, puerto, usuario, clave, base (NO subir config.ini real)
├─ requirements.txt
├─ build.bat                    # genera el .exe con PyInstaller
├─ LEEME.txt                    # pasos de ejecución para el revisor
├─ app/
│  ├─ config.py                 # lee/escribe config.ini
│  ├─ db.py                     # conexión, call_proc(), query(), transacción
│  ├─ seguridad.py              # hash y verificación de contraseñas
│  ├─ setup_bd.py               # asistente: crea BD, usuario matricula_app y carga scripts
│  ├─ servicios/
│  │  ├─ auth.py
│  │  ├─ solicitudes.py         # bandeja en archivos JSON (ver §5)
│  │  ├─ ocr.py
│  │  ├─ matricula.py           # aprobar solicitud → llamadas a procedimientos
│  │  ├─ reportes.py            # las consultas y sus parámetros
│  │  └─ exportar.py            # Excel / PDF / CSV
│  └─ ui/
│     ├─ ventana_principal.py
│     ├─ login.py
│     ├─ asistente_conexion.py
│     ├─ componentes.py         # tabla con orden/filtro, formularios, diálogos
│     ├─ padre/                 # mis_solicitudes.py, asistente_solicitud.py
│     └─ secretaria/            # bandeja.py, revision.py, mantenimiento.py,
│                               # distribucion.py, listas.py, reportes.py
├─ sql/
│  ├─ 01_esquema.sql            # 12 tablas + índices (de la Entrega 4, sin cambios)
│  ├─ 02_usuario.sql            # tabla USUARIO
│  ├─ 03_procedimientos.sql     # CRUD + consultas + función
│  ├─ 04_triggers.sql           # validaciones
│  ├─ 05_datos_prueba.sql       # datos de la Entrega 4 + usuarios demo
│  └─ 06_consultas.sql          # las 10 consultas de la Entrega 4 + extras
├─ data/solicitudes/            # se crea sola: pendientes/, aprobadas/, rechazadas/
├─ tests/
└─ docs/                        # capturas, memoria, manual
```

Arquitectura en 3 capas: **UI (ui/) → servicios (servicios/) → acceso a datos (db.py + procedimientos SQL)**. La UI nunca habla directo con MySQL.

## 3. Base de datos

### 3.1 Tabla USUARIO (reemplaza a la del informe anterior; no duplicar)

El padre puede no existir aún en PADRE_APODERADO, así que no hay FK a SECRETARIA y la validación se hace con trigger. Solo roles `Secretaria` y `Padre` (sin Administrador).

```sql
CREATE TABLE USUARIO (
    IdUsuario     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    NombreUsuario VARCHAR(30)  NOT NULL,
    ClaveHash     VARCHAR(255) NOT NULL,
    Rol           VARCHAR(15)  NOT NULL,            -- 'Secretaria' | 'Padre'
    Estado        VARCHAR(10)  NOT NULL DEFAULT 'Activo',
    DNI           CHAR(8)      NOT NULL,            -- DNI de la secretaria o del padre/apoderado
    UltimoAcceso  DATETIME     NULL,
    CONSTRAINT PK_Usuario PRIMARY KEY (IdUsuario),
    CONSTRAINT UQ_Usuario_Nombre UNIQUE (NombreUsuario),
    CONSTRAINT UQ_Usuario_DNI UNIQUE (DNI),
    CONSTRAINT CK_Usuario_Rol CHECK (Rol IN ('Secretaria','Padre')),
    CONSTRAINT CK_Usuario_Estado CHECK (Estado IN ('Activo','Inactivo')),
    CONSTRAINT CK_Usuario_DNI CHECK (DNI REGEXP '^[0-9]{8}$')
) ENGINE=InnoDB;
```

### 3.2 Usuario MySQL de la aplicación (prueba del requisito "todo por procedimientos")

```sql
CREATE USER IF NOT EXISTS 'matricula_app'@'localhost' IDENTIFIED BY '<clave>';
GRANT SELECT, EXECUTE ON bd_matricula.* TO 'matricula_app'@'localhost';
-- Sin INSERT/UPDATE/DELETE: la app solo puede modificar datos llamando a procedimientos.
```
Los procedimientos usan `SQL SECURITY DEFINER` (por defecto) para poder escribir.

### 3.3 Procedimientos almacenados

Reglas: no hacen `COMMIT` (la transacción la controla el servicio de Python); validan y usan `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '...'` con mensajes claros en español.

**CRUD (insertar / actualizar / eliminar):**

| Tabla | Procedimientos |
|---|---|
| ESTUDIANTE | `sp_estudiante_insertar` (recibe nombre y celular del contacto y un `p_id_contacto` opcional; ver §14.8), `sp_estudiante_actualizar`, `sp_estudiante_eliminar` |
| PADRE_APODERADO | `sp_padre_insertar`, `sp_padre_actualizar`, `sp_padre_eliminar` |
| CONTACTO_EMERGENCIA | `sp_contacto_actualizar` (se crea desde el de estudiante) |
| INSTITUCION_EDUCATIVA | `sp_ie_insertar`, `sp_ie_actualizar`, `sp_ie_eliminar` |
| CONSTANCIA_LOGROS | `sp_constancia_insertar`, `sp_constancia_actualizar`, `sp_constancia_eliminar` |
| LOGRO | `sp_logro_insertar`, `sp_logro_actualizar`, `sp_logro_eliminar` |
| MATRICULA | `sp_registrar_matricula`, `sp_actualizar_estado_matricula`, `sp_cambiar_seccion`, `sp_eliminar_matricula` |
| TIENE_PADRES | `sp_tiene_padres_insertar`, `sp_tiene_padres_eliminar` |
| HERMANDAD | `sp_hermandad_insertar`, `sp_hermandad_eliminar` |
| ESTUDIANTE_NEE | `sp_nee_insertar`, `sp_nee_eliminar` |
| ESTUDIANTE_HERMANOS_IE | `sp_hermanos_ie_insertar`, `sp_hermanos_ie_eliminar` |
| USUARIO | `sp_usuario_registrar` (siempre rol Padre), `sp_usuario_obtener` (devuelve hash para que Python verifique), `sp_usuario_registrar_acceso`, `sp_usuario_cambiar_clave`, `sp_usuario_cambiar_estado` |

**Consultas y reglas del proceso:**
- `sp_buscar_estudiante(ap_paterno, ap_materno, nombres)`
- `sp_listar_hermanos(dni)`  (ambos sentidos de HERMANDAD)
- `sp_verificar_matriculados(anio_anterior, anio_actual)` → continúan / nuevos / no continúan
- `sp_cupos_seccion(anio, nivel, grado)` → sección, matriculados, vacantes (máx. 30)
- `sp_padron(anio, nivel, grado, seccion)` → lista de matriculados (parámetros opcionales con NULL = todos)
- **Función** `fn_grado_siguiente(nivel, grado, situacion_final)` (ver §13.5 punto 2 y §14.2).

### 3.4 Triggers (validaciones, sin tablas nuevas)

Mantener `trg_hermandad_bi` y `trg_hermandad_bu` (ya están en el esquema). Agregar en `04_triggers.sql` (con `DROP TRIGGER IF EXISTS` antes de cada uno):

| Trigger | Regla |
|---|---|
| `trg_matricula_bi` | un estudiante no puede tener dos matrículas en el mismo año; la sección no puede superar 30 matriculados; el grado debe ser válido para el nivel; la sección debe existir según los supuestos (Inicial 2, Primaria 3, Secundaria 4) |
| `trg_matricula_bu` | un estado `Retirado` o `Trasladado` no puede volver a `Matriculado`; al cambiar de sección se vuelve a validar el cupo |
| `trg_matricula_bd` | solo se puede eliminar una matrícula que no esté en estado `Matriculado` (primero se retira) |
| `trg_estudiante_bi` / `_bu` | fecha de nacimiento no futura; DNI del estudiante distinto de su apoderado |
| `trg_padre_bi` / `_bu` | el padre/apoderado debe ser mayor de 18 años |
| `trg_tiene_padres_bi` | máximo 2 padres (padre y madre) por estudiante |
| `trg_logro_bi` | `AñoEscolar` no mayor al año actual |
| `trg_usuario_bi` | si `Rol = 'Secretaria'`, el DNI debe existir en SECRETARIA; si `Rol = 'Padre'`, el DNI NO debe existir en SECRETARIA |

### 3.5 Parser de scripts
`setup_bd.py` debe ejecutar los `.sql` respetando `DELIMITER //` (el conector no lo entiende): un pequeño parser que divida el archivo según el delimitador activo.

## 4. Conexión y primera ejecución

1. Al abrir, `main.py` lee `config.ini` (junto al .exe). Si no existe o la conexión falla → abre el **asistente de conexión**: servidor, puerto, usuario administrador (ej. root), clave.
2. Botón **Probar conexión** (muestra versión de MySQL y número de estudiantes si la BD ya existe).
3. Botón **Crear base de datos y cargar datos de prueba**: ejecuta `sql/01` a `05`, crea el usuario `matricula_app` con los permisos de §3.2 y guarda `config.ini` con ese usuario (la clave del administrador NO se guarda).
4. Luego muestra el login.

## 5. Solicitudes (sin tabla nueva)

Como no se pueden agregar tablas, la solicitud del padre es una **bandeja de archivos** en `data/solicitudes/`. Solo cuando la secretaria **aprueba**, los datos validados entran a la base de datos mediante procedimientos.

```
data/solicitudes/
  pendientes/SOL-2027-0001/solicitud.json
                           docs/dni_alumno_1.jpg, dni_padre.jpg, constancia_1.jpg
  aprobadas/   rechazadas/
```

`solicitud.json` (esquema):
```json
{
  "id": "SOL-2027-0001",
  "anio": 2027,
  "estado": "Enviada",                 // Borrador | Enviada | Observada | Aprobada | Rechazada
  "dni_solicitante": "00000000",       // usuario padre que la crea
  "fecha_envio": "2026-11-20T10:30:00",
  "padres": [ { /* columnas de PADRE_APODERADO */ } ],
  "dni_responsable": "00000000",       // quien suscribe la matrícula
  "dni_apoderado": null,
  "contacto_emergencia": { "nombre": "", "celular": "" },   // uno por ficha, compartido por los hermanos (§14.8)
  "alumnos": [
    {
      "ficha": { /* columnas de ESTUDIANTE (sin FK) */ },
      "nee": [], "hermanos_ie": [],
      "ie_procedencia": { "codigo_modular": "", "nombre": "", "tipo": "" },
      "destino": { "nivel": "Primaria", "grado": "3.°" },
      "constancia": {
        "codigo_virtual": "ABCD1234",
        "logros": [ { "anio": 2026, "grado": "2.°", "codigo_modular_ie": "", "nombre_ie": "", "situacion": "APROBADO" } ]
      },
      "docs": { "dni": "docs/dni_alumno_1.jpg", "constancia": "docs/constancia_1.jpg" },
      "verificacion": { "estado": "Pendiente", "verificado_por": null }
    }
  ],
  "observaciones": [ { "fecha": "", "de": "Secretaria", "texto": "" } ]
}
```
Varios alumnos en una misma solicitud (máximo 6, como la ficha física) = **hermanos**. Al aprobar se generan los pares de HERMANDAD entre ellos.

## 6. Pantallas por rol

### 6.1 Login y registro
- Login con usuario y clave; mensaje genérico si falla (no decir cuál dato falló).
- "Crear cuenta de padre/apoderado": DNI, usuario, clave (rol fijo `Padre`).
- Tras ingresar, el menú depende del rol. No mostrar logo ni nombre de la institución.

### 6.2 Padre / apoderado
1. **Mis solicitudes**: lista con estado; abrir observaciones de la secretaria; editar si está `Observada`.
2. **Nueva solicitud** (asistente de 5 pasos, con botones Anterior/Siguiente y validación por paso):
   1. Año escolar y alumnos: agregar uno o varios alumnos (hermanos, máx. 6); por cada uno, nivel y grado al que postula.
   2. Datos del alumno (campos de ESTUDIANTE + contacto de emergencia + NEE + hermanos en la I.E.).
   3. Datos del padre, madre y/o apoderado (campos de PADRE_APODERADO) y quién es el responsable de la matrícula.
   4. Documentos: adjuntar imagen del DNI del alumno, DNI de padres y constancia de logros; botón **"Autocompletar con OCR"**; campo del **código virtual** de la constancia y tabla de logros (año, grado, I.E., situación).
   5. Resumen y **Enviar**.
3. OCR = ayuda, nunca obligatorio: los campos siempre se pueden escribir a mano y el resultado del OCR se muestra para que el padre lo confirme. Si Tesseract no está disponible, el botón se desactiva con un aviso y el formulario sigue funcionando.
   - DNI: extraer número de 8 dígitos, apellidos y nombres, fecha de nacimiento (expresiones regulares sobre el texto).
   - Constancia: extraer código virtual (8 caracteres) y filas de año/grado/situación en la medida de lo posible.

### 6.3 Secretaria
1. **Bandeja de solicitudes**: filtros por año y estado; contador de pendientes.
2. **Revisión de una solicitud**: ver datos y documentos adjuntos (abrir imagen con el visor del sistema); por cada alumno:
   - botón **"Consultar constancia en MINEDU"** (`webbrowser.open` a la URL oficial configurada en `config.ini` → `url_consulta_constancia`; copiar el código virtual al portapapeles);
   - registrar lo que ve en la plataforma: último año cursado y situación final (`APROBADO` / `REQUIERE RECUPERACIÓN`);
   - el sistema calcula el grado que corresponde con `fn_grado_siguiente` y lo compara con el grado solicitado (advertencia si no coincide);
   - elegir sección viendo los cupos (`sp_cupos_seccion`).
   Acciones: **Observar** (escribe una observación), **Rechazar**, **Aprobar y matricular**.
3. **Aprobar y matricular** (una transacción; si algo falla → `ROLLBACK` y mensaje con el texto del `SIGNAL`). Orden obligatorio por las FK:
   `sp_padre_insertar/actualizar` → `sp_ie_insertar` (procedencia) → `sp_estudiante_insertar` (crea contacto) → `sp_tiene_padres_insertar` → `sp_nee_insertar` → `sp_hermanos_ie_insertar` → `sp_constancia_insertar` → `sp_logro_insertar` → `sp_hermandad_insertar` (pares entre hermanos de la solicitud) → `sp_registrar_matricula`. Luego mover la carpeta a `aprobadas/`. Si el estudiante o el padre ya existen, usar los procedimientos `_actualizar`.
4. **Mantenimiento (CRUD)**: una pestaña por tabla (Estudiante, Padre/Apoderado, Institución educativa, Constancia, Logro, Matrícula, Hermandad, NEE, Hermanos en la I.E.) con tabla, buscador, y botones Nuevo / Editar / Eliminar que llaman a los procedimientos. Mostrar al usuario el mensaje de los triggers cuando rechazan una operación.
5. **Distribución**: elegir año → ver nivel / grado / sección con matriculados y vacantes; mover un alumno de sección (`sp_cambiar_seccion`).
6. **Listas**: padrón por año/nivel/grado/sección; **comparar listas** de dos años (`sp_verificar_matriculados`) mostrando continúan / nuevos / no continúan; opción de importar un CSV/Excel de DNIs y compararlo contra la lista del sistema. Botones **Exportar a Excel / PDF / CSV** en todas las listas y reportes.
7. **Reportes**: las 10 consultas de la Entrega 4 (numeración y resultado inicial idénticos a las Figuras 22 a 31) como pantallas con parámetros, **al menos 6 con JOIN**. Extras: cupos por sección y comparación de listas.

## 7. Datos de prueba
- Reutilizar los de la Entrega 4 (no usar DNIs reales de personas).
- Usuarios demo: ver §14.5.
- Solicitudes de ejemplo: ver §14.6.

## 8. Pruebas (`unittest`, carpeta tests/)
- Conexión y versión del gestor.
- Cada procedimiento: caso correcto y caso de error.
- Cada trigger: caso que debe fallar (cupo 30, matrícula duplicada, hermano de sí mismo, padre menor de edad, 3 padres, retirado→matriculado, etc.).
- **Prueba de "sin DML en el código"**: ver §13.5 punto 4.
- Flujo completo: crear solicitud con 2 hermanos → aprobar → verificar filas en ESTUDIANTE, TIENE_PADRES, HERMANDAD, MATRICULA.
- `fn_grado_siguiente`, exportación a Excel/PDF (el archivo se genera y no está vacío).
- Las 10 consultas devuelven filas con los datos de prueba.
- Pruebas adicionales: ver §13.7.

## 9. Empaquetado y entrega
1. `build.bat` (se ejecuta **en Windows**):
   `pyinstaller --noconfirm --onedir --windowed --name MatriculaApp --add-data "sql;sql" --hidden-import mysql.connector.plugins.caching_sha2_password --hidden-import mysql.connector.plugins.mysql_native_password --hidden-import mysql.connector.locales.eng main.py` (o `--collect-submodules mysql.connector`).
   Incluir, si se usa OCR, la carpeta `tesseract/` (con `tessdata/spa.traineddata`) junto al .exe y apuntar `pytesseract.tesseract_cmd` a esa ruta relativa.
2. `config.ini` y `data/` quedan **fuera** del ejecutable, al lado del .exe.
3. Estructura del ZIP final:
```
Entrega5_GrupoXX.zip
├─ MatriculaApp/            (.exe + dependencias + sql/ + tesseract/ opcional)
├─ codigo_fuente/           (todo el proyecto documentado)
├─ script_bd/               (los .sql 01 a 06)
├─ documentos/              (informe, memoria descriptiva, manual de usuario)
└─ LEEME.txt                (requisitos y pasos)
```
4. `LEEME.txt` debe decir: requiere **MySQL 8.0 instalado y en ejecución** (el .exe no lo incluye); abrir MatriculaApp.exe → asistente de conexión → "Crear base de datos y cargar datos de prueba" → ingresar con los usuarios demo (con sus contraseñas).
5. Probar el .exe en una PC o máquina virtual limpia (sin Python) antes de entregar. Windows Defender puede marcar falsos positivos con PyInstaller: avisar en el LEEME.

## 10. Orden de trabajo

| Fase | Contenido | Commit |
|---|---|---|
| 1 | Limpiar Flask; estructura de carpetas; `config`, `db.py`, asistente de conexión, parser de scripts, USUARIO | `f1-conexion` |
| 2 | Procedimientos CRUD + triggers + función; tests de BD | `f2-sql` |
| 3 | Login, roles, ventana principal, CRUD de la secretaria (tablas principales) | `f3-crud` |
| 4 | Asistente del padre (pasos 1–3) y guardado de solicitudes | `f4-padre` |
| 5 | Documentos, OCR, constancia y revisión de la secretaria, aprobar y matricular | `f5-flujo` |
| 6 | Distribución, listas, comparación, 10 reportes + exportar Excel/PDF | `f6-reportes` |
| 7 | Pruebas completas, `build.bat`, ZIP, LEEME | `f7-entrega` |

Si el tiempo no alcanza, recortar en este orden: matrícula masiva → importación de lista externa → OCR de la constancia → OCR del DNI. **No recortar:** CRUD por procedimientos, triggers, flujo padre → secretaria → matrícula, los 10 reportes (6 con JOIN) y el .exe.

## 11. Distribución de porcentajes (solo para el informe; no afecta el código)

| Módulo | Peso % | Responsable | Reunión |
|---|---|---|---|
| A. Conexión, asistente, login, roles y menús | 10 | Diaz Acosta, K. | 10 |
| B. CRUD Estudiante y datos del alumno en la ficha | 10 | Diaz Porras, L. | 10 |
| C. CRUD Padre/Apoderado, cuenta de padre y datos de padres en la ficha | 10 | Handa Milla, A. | 10 |
| D. Solicitud del padre, bandeja de la secretaria y registro de matrícula | 15 | Diaz Acosta, K. | 11 |
| E. Constancia, logros, I.E., OCR y verificación de grado | 10 | Diaz Porras, L. | 11 |
| F. Hermandad, contacto, NEE, hermanos en la I.E. y distribución por secciones | 10 | Handa Milla, A. | 11 |
| G. Procedimientos y triggers restantes y validaciones | 5 | Diaz Porras, L. | 11 |
| H. Reportes (10 consultas), comparación de listas y exportación | 20 | Sarmiento Ccari, R. | 12 |
| I. Pruebas, empaquetado .exe y manual | 10 | Handa Milla, A. (5) y Sarmiento Ccari, R. (5) | 12 |

## 12. Capturas que el informe necesitará (guardar en docs/)
Estructura de USUARIO; prueba de conexión; asistente de conexión; login (y error); menú del padre y de la secretaria; los 5 pasos del asistente del padre (con dos hermanos); OCR en acción; bandeja; revisión con la consulta a MINEDU; aprobar y matricular (éxito y error por cupo/duplicado); un CRUD por tabla con un mensaje de trigger; distribución por secciones; comparación de listas; exportación a Excel y PDF; los 10 reportes; resultado de las pruebas; el .exe abierto en una PC limpia.

---

# 13. AJUSTES Y MEJORAS

## 13.1 Regla de oro de integridad: dónde vive cada dato

Un alumno solo existe en la base de datos cuando ya está **matriculado**. Mientras esté en prematrícula, vive únicamente en la bandeja de archivos.

| Situación del alumno | Dónde está | ¿Aparece en ESTUDIANTE / padrón / reportes / CRUD? |
|---|---|---|
| Solicitud Borrador, Enviada u Observada | solo `data/solicitudes/pendientes/` | **NO** |
| Solicitud Rechazada | solo `data/solicitudes/rechazadas/` | **NO** |
| Solicitud Aprobada | BD (ESTUDIANTE, PADRE_APODERADO, TIENE_PADRES, MATRICULA, etc.) + copia en `aprobadas/` | **SÍ** |
| Alumno con matrícula Retirado/Trasladado | BD | Sí en el CRUD y en el histórico; **NO** en el padrón de matriculados del año vigente |

Consecuencias obligatorias:
1. Ninguna pantalla de la secretaria (Mantenimiento, Distribución, Listas, Reportes) lee los JSON de solicitudes, salvo la Bandeja y la Revisión.
2. Ninguna solicitud no aprobada ejecuta un `CALL sp_...` de escritura. Observar o rechazar solo modifica el JSON y mueve archivos.
3. Los cupos de sección (`sp_cupos_seccion`) cuentan solo MATRICULA con estado `Matriculado`; una solicitud pendiente no reserva cupo.
4. El padre solo ve sus propias solicitudes (filtro por `dni_solicitante` = DNI de su usuario, validado en la capa de servicios, no solo en la UI).
5. El padre nunca consulta tablas de la BD con datos de otros alumnos. Solo lee sus JSON.

## 13.2 Integridad al "Aprobar y matricular"

1. **Transición de estados permitida** (cualquier otra se rechaza en `solicitudes.py`):
   `Borrador → Enviada → (Observada → Enviada) → Aprobada | Rechazada`. Una solicitud Aprobada o Rechazada es de solo lectura.
2. **Bloqueo contra doble aprobación**: al empezar, renombrar la carpeta de forma atómica (`pendientes/SOL-X` → `pendientes/SOL-X.procesando`). Si el renombrado falla, otra persona la está procesando: abortar con mensaje.
3. **Orden de operaciones**: primero la transacción en MySQL; solo tras `COMMIT` exitoso mover la carpeta a `aprobadas/`. Si falla la BD → `ROLLBACK` y la carpeta vuelve a `pendientes/` con su nombre original. Si el `COMMIT` fue exitoso pero falla el movimiento, el sistema detecta en la siguiente apertura que ya existe MATRICULA para ese alumno y año, y solo completa el movimiento, sin volver a insertar.
4. **Una sola transacción** por solicitud con todos sus alumnos (hermanos): si falla uno, no se matricula ninguno.
5. **Detección de existentes antes de insertar** (solo `SELECT`): DNI de alumno, de cada padre/apoderado y código modular de la I.E. Si ya existe → usar el `sp_..._actualizar`; si no → `sp_..._insertar`. Al actualizar nunca se pisan datos existentes con valores vacíos.
6. **Hermandad**: se generan los pares entre los alumnos de la solicitud una sola vez por par (ordenando los DNI) y se omiten los pares que ya existan.
7. **Bloqueo de cupo**: `sp_registrar_matricula` hace `SELECT ... FOR UPDATE` sobre las matrículas de esa sección/año/grado antes de validar el cupo (máx. 30).
8. **Un alumno, una matrícula por año**: se valida en el trigger (BD) y también antes, al enviar y al abrir la revisión (SELECT).
9. **Solicitudes duplicadas**: al enviar, rechazar si ya hay otra solicitud pendiente del mismo DNI de alumno en el mismo año, o si ese alumno ya tiene matrícula ese año.
10. **Validación de datos al enviar** (padre) y de nuevo al aprobar (secretaria): DNI de 8 dígitos, fecha de nacimiento no futura, apoderado mayor de 18 años, DNI del alumno distinto del de sus padres, nivel/grado válido, año escolar = año actual o siguiente, máximo 2 padres por alumno.
11. **Documentos**: solo .jpg/.jpeg/.png/.pdf, máx. 5 MB cada uno, copiados a `docs/` con nombre generado (nunca el nombre original).
12. **Escritura de JSON atómica**: escribir en archivo temporal y reemplazar con `os.replace`. Al leer, validar el esquema; si un JSON está dañado, mostrar la solicitud como "ilegible" sin romper la bandeja.
13. **Generación del ID** `SOL-AAAA-NNNN`: crear la carpeta con `os.mkdir` (atómico) reintentando con el siguiente número si ya existe.

## 13.3 Integridad en eliminaciones y relaciones (sin tablas nuevas, sin ALTER)

Los procedimientos validan y borran en el orden correcto, o rechazan con mensaje claro:

- `sp_estudiante_eliminar`: si tiene matrícula en estado `Matriculado` → rechaza ("primero retire la matrícula"). Si solo tiene matrículas Retiradas/Trasladadas, rechaza igualmente para conservar el histórico, salvo que se elimine primero cada matrícula con `sp_eliminar_matricula`. Si no tiene matrículas, borra en este orden: ESTUDIANTE_NEE, ESTUDIANTE_HERMANOS_IE, HERMANDAD (ambos sentidos), TIENE_PADRES, LOGRO y CONSTANCIA_LOGROS propios, ESTUDIANTE y por último su CONTACTO_EMERGENCIA (solo si ningún otro estudiante lo usa).
- `sp_padre_eliminar`: rechaza si el padre está en TIENE_PADRES de algún estudiante, es apoderado de alguno o es responsable de alguna matrícula.
- `sp_ie_eliminar`: rechaza si hay constancias, logros o estudiantes que la referencian.
- `sp_constancia_eliminar`: elimina primero sus logros.
- `sp_usuario_*`: un usuario Padre inactivo no puede iniciar sesión pero sus solicitudes se conservan.
- Todo procedimiento valida que el registro exista antes de actualizar o eliminar y lanza `SIGNAL` si no existe.
- Ninguna pantalla de CRUD permite "eliminar" sin diálogo de confirmación.

## 13.4 Seguridad y roles

- `sp_usuario_registrar` (el que usa la app) crea SIEMPRE rol `Padre`; no recibe el rol como parámetro. Las cuentas de Secretaria se crean solo en `05_datos_prueba.sql`.
- El rol se verifica en la capa de servicios en cada operación (no solo ocultando menús): un Padre que invoque un servicio de secretaria recibe error.
- Login: mensaje genérico en caso de fallo, comparación de hash con `hmac.compare_digest`, bloqueo temporal en memoria tras 5 intentos fallidos (30 segundos). Los usuarios Inactivos no pueden entrar.
- La clave del administrador de MySQL nunca se guarda en disco. `config.ini` real no va en el ZIP (solo `config.ini.example`).
- Los errores de BD se muestran con el texto del `SIGNAL`; los errores inesperados se registran en `data/errores.log` y al usuario se le muestra un mensaje amable.

## 13.5 Cambios a secciones anteriores

1. **Nombre de la BD**: `bd_matricula` en `config.ini`, `01_esquema.sql` y los GRANT. Sin nombre de la institución en ningún archivo visible al usuario.
2. **`fn_grado_siguiente`** debe cubrir la secuencia completa: Inicial `3 a.` → `4 a.` → `5 a.`; Inicial `5 a.` → Primaria `1.°`; Primaria `1.°` … `6.°`; `6.°` Primaria → Secundaria `1.°`; Secundaria `1.°` … `5.°`; `5.°` Secundaria → `EGRESADO`. Con `APROBADO` devuelve el siguiente; con `REQUIERE RECUPERACIÓN` devuelve el mismo grado. Valores inválidos → `SIGNAL`. Un test por cada grado.
3. **Alumnos nuevos sin constancia**: para Inicial 3 años o ingresantes sin historial, la constancia es opcional y la secretaria marca "Sin constancia (ingresante)". No se llama a `sp_constancia_insertar` ni `sp_logro_insertar`, y no se muestra la advertencia de grado.
4. **Prueba "sin DML en el código"**: regex sin distinguir mayúsculas sobre los `.py` de `app/`: `\bINSERT\s+INTO\b`, `\bUPDATE\s+\w+\s+SET\b`, `\bDELETE\s+FROM\b`. Además comprobar que el usuario `matricula_app` realmente no puede hacer DML: intentar un `INSERT` directo desde el test y verificar que MySQL lo rechaza.
5. **PyInstaller con MySQL 8**: `use_pure=True` y los `--hidden-import` de §9. Probar el .exe en una PC o máquina virtual sin Python **antes** de continuar con las fases siguientes.
6. **Transacciones**: `autocommit=False`. Cada operación de escritura de la UI es un `CALL` seguido de `commit()`, y ante cualquier excepción un `rollback()`. Nunca dejar transacciones abiertas.
7. **Compuertas entre fases**: no avanzar si los tests de la fase actual no pasan.

## 13.6 Automatizaciones (en este orden de prioridad)

1. **Semáforo de validación** en la Revisión, por alumno (verde/ámbar/rojo): DNI válido y no duplicado en otra solicitud pendiente; grado solicitado = `fn_grado_siguiente(...)`; cupo disponible; apoderado mayor de edad y documentos completos. "Aprobar y matricular" se habilita solo si no hay rojos.
2. **Aviso de existentes**: "Alumno ya registrado: se actualizarán sus datos" / "Alumno nuevo: se creará".
3. **Sección sugerida**: preseleccionar la sección con más vacantes (`sp_cupos_seccion`); la secretaria puede cambiarla.
4. **Matrícula masiva de continuadores** (solo si sobra tiempo): con `sp_verificar_matriculados`, listar los que continúan con su grado siguiente (`fn_grado_siguiente`), marcar/desmarcar y matricular en bloque; un `CALL sp_registrar_matricula` por alumno, cada uno en su propia transacción; resumen final de matriculados y omitidos con motivo. Los alumnos sin situación final registrada quedan en "pendientes de verificar".
5. **Autocompletar con OCR** (§6.2), siempre confirmable y editable.
6. **Importar lista externa** (CSV/Excel de DNIs): solo compara, nunca modifica la base.

## 13.7 Pruebas adicionales

- Una solicitud Enviada/Observada/Rechazada **no deja filas** en ESTUDIANTE, PADRE_APODERADO, TIENE_PADRES, HERMANDAD ni MATRICULA.
- Aprobar dos veces la misma solicitud: la segunda falla sin duplicar nada.
- Aprobar una solicitud con 2 hermanos donde el segundo falla (cupo lleno): la BD queda sin ninguna fila nueva y la carpeta sigue en `pendientes/`.
- Un Padre no puede ver ni abrir solicitudes de otro Padre, ni invocar servicios de secretaria.
- `sp_usuario_registrar` no puede crear una Secretaria ni usar un DNI de SECRETARIA.
- `sp_estudiante_eliminar` rechaza con matrícula `Matriculado` y limpia correctamente las tablas hijas cuando no hay matrículas.
- Doble aprobación simultánea: solo una gana.
- JSON dañado en la bandeja: la app sigue funcionando.
- Eliminar un padre referenciado por TIENE_PADRES es rechazado.

---

# 14. DATOS REALES DEL PROYECTO (prevalece sobre todo lo anterior)

## 14.1 Archivos existentes y su destino
- `01_creacion.sql` → `sql/01_esquema.sql` (12 tablas + índices + triggers `trg_hermandad_*`; NO alterar tablas).
- `03_usuario.sql` → reescribir como `sql/02_usuario.sql` según §3.1.
- `04_procedimientos.sql` → base de `sql/03_procedimientos.sql`.
- `sql/04_triggers.sql` → nuevo (triggers de §3.4).
- `02_datos_prueba.sql` → `sql/05_datos_prueba.sql` (+ usuarios demo).
- `05_consultas.sql` → `sql/06_consultas.sql`.
- Base de datos: `bd_matricula` (reemplazar `bd_matricula_paola_frassinetti` en todo). `CREATE DATABASE IF NOT EXISTS bd_matricula CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`.
- Todos los .sql en UTF-8; conexión Python con `charset='utf8mb4'`. Hay columnas con ñ (`AñoEscolar`): en SQL usar `` `AñoEscolar` `` y en Python acceder por nombre exacto.

## 14.2 Valores reales (usar EXACTAMENTE estos; si un CHECK de 01_esquema.sql dice otra cosa, manda el SQL)
- Nivel: `'Inicial'`, `'Primaria'`, `'Secundaria'`.
- Grado Inicial: `'3 a.'`, `'4 a.'`, `'5 a.'`. Primaria: `'1.°'`…`'6.°'`. Secundaria: `'1.°'`…`'5.°'`.
- Estado de matrícula: `'Matriculado'`, `'Retirado'`, `'Trasladado'`.
- SituacionFinal: `'APROBADO'`, `'REQUIERE RECUPERACIÓN'`.
- Secciones: Inicial A-B, Primaria A-C, Secundaria A-D. Capacidad 30 por sección.
- Egreso: 5.° Secundaria aprobado → `'EGRESADO'`.
- Tipos permitidos por CHECK: TipoAtencion `ESSALUD|SIS|Otros`; GradoInstruccion `Primaria|Secundaria|Superior|Otros`; TipoIE `Estatal|Particular`; Sexo `M|F`; celular y teléfono fijo exactamente 9 dígitos.

## 14.3 Procedimientos existentes
- Conservar nombres y parámetros de `sp_registrar_matricula` (9 parámetros), `sp_actualizar_estado_matricula`, `sp_buscar_estudiante`, `sp_listar_hermanos` y `sp_verificar_matriculados`. Solo agregarles lo de §13 (por ejemplo `FOR UPDATE` en el cupo) y quitar validaciones duplicadas con triggers solo si no se pierde ninguna regla.
- `sp_verificar_matriculados` devuelve la columna `Situacion` con valores `'Continúa'`, `'Nuevo'` y `'Sin matrícula en el año actual'`. No cambiar las columnas. En pantalla mostrar "Sin matrícula en el año actual" como "No continúa".
- `sp_registrar_matricula` exige que el responsable sea el apoderado del estudiante o uno de sus padres en TIENE_PADRES: por eso, al aprobar, TIENE_PADRES (o el apoderado en ESTUDIANTE) se inserta ANTES de la matrícula.
- Crear los que faltan (§3.3).

## 14.4 Las 10 consultas (Figuras 22 a 31)
- Usar `06_consultas.sql` TAL CUAL, sin reescribir el SQL ni cambiar el orden. Solo se reemplazan los valores fijos por parámetros `%s`.
- Cada pantalla arranca con los valores del script como predeterminados, para que el resultado inicial coincida con las capturas:

| N.° | Parámetros por defecto | JOIN |
|---|---|---|
| 1 | año 2026, Secundaria, 3.°, B, Matriculado | Sí |
| 2 | ap. paterno Diaz, ap. materno Acosta | No |
| 3 | DNI 74922482, nivel Secundaria | Sí |
| 4 | DNI 56743478 (se usa en las dos mitades del UNION) | Sí |
| 5 | sin parámetros | No |
| 6 | DNI apoderado 56345876 | No |
| 7 | DNI responsable 29481029 | No |
| 8 | DNI 56743478 | Sí |
| 9 | DNI 74922482 | Sí |
| 10 | año 2026 | Sí |

- Total con JOIN: 6 (cumple el mínimo). Extras: cupos por sección y comparación de listas. Un test verifica que las 10 devuelvan filas con los valores por defecto.

## 14.5 Datos de prueba (NO modificar los DNIs ni los valores; coinciden con el informe)
- Si un trigger nuevo rechaza un dato existente, corregir el TRIGGER, no el dato. Si el dato es realmente inválido, avisar antes de tocarlo.
- Contactos de emergencia COMPARTIDOS entre hermanos (id 1: 56743478 y 74922482; id 2: 78120001 y 78120003; id 3: 78120002 y 78120005; id 4: 78120004 y 78120006). Por eso `sp_contacto_actualizar` afecta a todos los hermanos que lo comparten (avisarlo en pantalla) y `sp_estudiante_eliminar` borra el contacto solo si nadie más lo usa.
- Secretaria existente: DNI 87733221 (Claudia Graciela Acosta Neira).
- Usuarios demo (en `05_datos_prueba.sql`, DESPUÉS de las tablas base):
  - `secretaria` con DNI 87733221, rol Secretaria.
  - `padre_demo` con DNI 29481029 (María Elena Acosta Porras, ya existe en PADRE_APODERADO), rol Padre.
  - El script usa marcadores `{{HASH_SECRETARIA}}` y `{{HASH_PADRE}}`; `setup_bd.py` los reemplaza con hashes generados por `seguridad.py`. Las contraseñas demo van en el LEEME.
- El estudiante 74922482 no tiene matrícula 2026 (solo constancia). Es intencional; no matricularlo.

## 14.6 Solicitudes de ejemplo (coherentes con la BD) — versión corregida
- Fecha actual del sistema: noviembre de 2026; las solicitudes nuevas son para el año escolar 2027.
- `pendientes/SOL-2027-0001`: DOS hermanos nuevos con DNI ficticios que NO existan en la BD (usar 9xxxxxxx), con padres nuevos ficticios. `dni_solicitante` = `29481029` (padre_demo, como cuenta que registra la solicitud). Sirve para probar hermandad.
- `pendientes/SOL-2027-0002`: el estudiante YA existente `56743478` (Domenica Diaz Acosta, 3.° Secundaria en 2026) postulando a **4.° Secundaria 2027**, con su responsable existente `29481029` y su padre `10334546`. `dni_solicitante` = `29481029`. Sirve para probar "Alumno ya registrado: se actualizarán sus datos". No tiene LOGRO 2026 en la BD: la secretaria registra la situación final al revisar.
- `aprobadas/SOL-2026-0001`: debe corresponder a una matrícula que YA esté en la BD: `56743478`, año 2026, Secundaria 3.° B, responsable `29481029`, `dni_solicitante` = `29481029`. Así no hay inconsistencias entre bandeja y base.
- Imágenes ficticias generadas con Pillow, sin datos reales.

## 14.7 Matrícula masiva de continuadores
Los datos de prueba no tienen LOGRO del 2026, así que por ahora todos quedarían "pendientes de verificar". Hacerla al final y solo si sobra tiempo; no es parte de lo mínimo.

## 14.8 Campos de la ficha de actualización (formulario del padre) y su columna en la BD

**Paso 1 – Destino** (no son columnas de ESTUDIANTE): año lectivo (`anio` de la solicitud), nivel y grado a cursar (`destino`). La **sección** NO la elige el padre: la asigna la secretaria (`MATRICULA.Seccion`).

**Paso 2 – Alumno (ESTUDIANTE)**, uno por hermano (máx. 6):
- Obligatorios: `DNI` (8 dígitos), `Sexo` (M/F), `Nombres`, `ApellidoPaterno`, `ApellidoMaterno`, `FechaNacimiento`, `DistritoNacimiento`, `ProvinciaNacimiento`, `DepartamentoNacimiento`, `PaisNacimiento`, `DomicilioActual`, `DistritoDomicilio`, `LugarQueOcupa` (posición entre los hermanos que estudian en la I.E.; sugerir el orden del alumno en la solicitud), `ViveConPadre`, `ViveConMadre`, `ElPadreVive`, `LaMadreVive` (Sí/No).
- Opcionales: `Celular` (9 dígitos), `CorreoElectronico`, `Religion`, `TipoAtencion` (ESSALUD/SIS/Otros), `EnfermedadCronica`.
- Multivalor: NEE (`ESTUDIANTE_NEE`, lista de textos de máx. 50; "Ninguna" permitido) y Hermanos en la I.E. (`ESTUDIANTE_HERMANOS_IE`, niveles Inicial/Primaria/Secundaria).
- I.E. de procedencia (opcional, solo alumnos nuevos): `CodigoModularIE`, `NombreIE`, `TipoIE` → INSTITUCION_EDUCATIVA y FK en ESTUDIANTE.

**Contacto de emergencia (CONTACTO_EMERGENCIA)** — UNO por solicitud, compartido por todos los hermanos (así lo hace la ficha física y los datos de prueba): `NombreContactoEmergencia` (máx. 110) y `CelularEmergencia` (9 dígitos). **Anula** lo dicho antes sobre crear un contacto por alumno: `sp_estudiante_insertar` recibe `p_id_contacto` opcional; si es NULL crea el contacto con nombre y celular, y devuelve su id (parámetro OUT o SELECT); los hermanos siguientes de la misma solicitud reutilizan ese id.

**Paso 3 – Padre, madre y/o apoderado (PADRE_APODERADO)**, cada uno: `DNI`, `Sexo`, `Nombres`, `ApellidoPaterno`, `ApellidoMaterno`, `FechaNacimiento`, `GradoInstruccion` (Primaria/Secundaria/Superior/Otros), `DomicilioActual`, `DistritoDomicilio`, `Celular` (obligatorio, 9 dígitos); opcionales: `OcupacionActual`, `TelefonoFijo` (9 dígitos), `CorreoElectronico`. El **apoderado** solo se registra si existe carta notarial (se guarda en `ESTUDIANTE.DNI_Apoderado`; padre y madre van en TIENE_PADRES, máx. 2). Se elige quién es el **responsable de la matrícula** (`MATRICULA.DNI_Responsable`: debe ser uno de los padres o el apoderado).

**Datos de suscripción** (`MATRICULA.LugarSuscripcion` = distrito, `FechaSuscripcion`): los propone el padre/secretaria en la revisión; por defecto la fecha del día de la aprobación. `DNI_Secretaria` = la secretaria que inició sesión al aprobar. No se modelan "Firma y Huella" ni el código QR.

**Paso 4 – Constancia de logros**: `CodigoVirtual` (8 caracteres alfanuméricos), `NivelEducativo`, `FechaHoraEmision` (opcional) y filas de LOGRO (`AñoEscolar`, `GradoCursado`, `CodigoModularIE`, `SituacionFinal`). Si la I.E. del logro no existe, se crea con `sp_ie_insertar` (NombreIE y TipoIE pueden ir vacíos).
