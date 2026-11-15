# Resultados de OCR sobre muestras reales

## Objetivo

Verificar la precisión del reconocimiento óptico (Tesseract 5, idioma `spa`) sobre
las muestras reales del informe de entrega:

- **Figura 1**: DNI del estudiante.
- **Figura 2**: DNI de padre/apoderado.
- **Figura 3**: constancia de logros de aprendizaje.

Las imágenes se extraen del informe con `scripts/extraer_muestras.py` y la
evaluación se reproduce con `scripts/evaluar_ocr.py`. Por privacidad, este
documento **no reproduce los datos personales** de las muestras; solo indica si
cada campo se reconoció correctamente.

## Procedimiento

1. `python scripts/extraer_muestras.py` → imágenes en `muestras/`.
2. `python scripts/evaluar_ocr.py` → campos y confianza por documento.
3. Comparación campo a campo contra el contenido legible del documento.

## Resultados por documento

### Figura 1 — DNI del estudiante

| Campo | ¿Correcto? | Confianza |
| --- | --- | --- |
| DNI | Sí | 95 |
| Apellido paterno | Sí | 85 |
| Nombres | Sí | 85 |
| Fecha de nacimiento | Sí | 90 |
| Sexo | Sí | 90 |

Precisión: **5/5 campos** (100 %).

### Figura 2 — DNI de padre/apoderado

| Campo | ¿Correcto? | Confianza |
| --- | --- | --- |
| Fecha de nacimiento | No verificable | 90 |
| Sexo | Sí | 90 |

La fotografía está girada y con muy baja nitidez; la mayor parte de las
etiquetas no es legible, por lo que solo se reconoce la zona de lectura
mecánica. Precisión evaluable: **1/1 campo verificable**.

### Figura 3 — constancia de logros

| Campo | ¿Correcto? | Confianza |
| --- | --- | --- |
| Código virtual | Sí | 72 |
| DNI del estudiante | Sí | 60 |
| Nivel educativo | Sí | 96 |
| Fecha/hora de emisión | No reconocido | — |
| Nombre de la I.E. | No reconocido | — |
| Logros (año/grado/situación) | No reconocido | — |

Precisión: **3/3 campos esperados del encabezado** (100 %). El detalle de logros
viene en una tabla con celdas degradadas por el escaneo y no se logra segmentar.

## Mejoras aplicadas

- **Lectura de la zona MRZ (TD1) del DNI**: se agregó un extractor que lee la
  zona de lectura mecánica y recupera DNI, fecha de nacimiento, sexo y nombres
  aunque las etiquetas impresas no sean legibles. La fecha se valida con su
  dígito verificador.
- **Falso positivo del nombre de I.E.**: se descartan coincidencias que
  provienen de la frase "Sistema de Información de Apoyo a la Gestión de la
  Institución Educativa (Siagie)".

## Limitaciones y trabajo futuro

- Las fotos de DNI con giro o poca luz degradan el OCR de las etiquetas; la MRZ
  mitiga el problema pero no cubre domicilio ni distrito de domicilio.
- La tabla de logros de la constancia requiere segmentación por celdas
  (líneas de tabla) para extraer año, grado y situación.
- El aplicativo siempre permite corregir manualmente los campos reconocidos.
