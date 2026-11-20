-- Script 06: Las 10 consultas representativas del proceso de matrícula
-- (Figuras 22 a 31). Usar TAL CUAL, sin reescribir el SQL ni cambiar el orden.
USE bd_matricula;

-- Consulta 1: Lista de estudiantes matriculados en un año, nivel, grado y sección específicos
-- Usa el índice idx_matricula_periodo
SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
       m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, m.Estado
FROM MATRICULA m
INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
WHERE m.`AñoEscolar` = 2026
  AND m.Nivel = 'Secundaria'
  AND m.Grado = '3.°'
  AND m.Seccion = 'B'
  AND m.Estado = 'Matriculado'
ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres;

-- Consulta 2: Buscar estudiante por apellidos y nombres (al registrar/actualizar datos)
-- Usa el índice idx_estudiante_apellidos
SELECT DNI, ApellidoPaterno, ApellidoMaterno, Nombres, FechaNacimiento
FROM ESTUDIANTE
WHERE ApellidoPaterno = 'Diaz'
  AND ApellidoMaterno = 'Acosta'
ORDER BY Nombres;

-- Consulta 3: Constancias de un estudiante filtradas por nivel
-- Usa el índice idx_constancia_estudiante
SELECT c.CodigoVirtual, c.DNI_Estudiante, c.NivelEducativo,
       c.FechaHoraEmision,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante
FROM CONSTANCIA_LOGROS c
INNER JOIN ESTUDIANTE e ON c.DNI_Estudiante = e.DNI
WHERE c.DNI_Estudiante = '74922482'
  AND c.NivelEducativo = 'Secundaria';

-- Consulta 4: Listar hermanos de un estudiante (sentido inverso de la PK de HERMANDAD)
-- Usa el índice idx_hermandad_hermanob para el segundo hermano
SELECT h.DNI_HermanoB AS DNI_Hermano,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Hermano
FROM HERMANDAD h
INNER JOIN ESTUDIANTE e ON h.DNI_HermanoB = e.DNI
WHERE h.DNI_HermanoA = '56743478'
UNION
SELECT h.DNI_HermanoA AS DNI_Hermano,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Hermano
FROM HERMANDAD h
INNER JOIN ESTUDIANTE e ON h.DNI_HermanoA = e.DNI
WHERE h.DNI_HermanoB = '56743478';

-- Consulta 5: Reporte de matriculados por año, nivel y grado (para el padrón)
-- Usa el índice idx_matricula_periodo
SELECT m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion,
       COUNT(*) AS Total_Matriculados,
       SUM(CASE WHEN m.Estado = 'Matriculado' THEN 1 ELSE 0 END) AS Activos,
       SUM(CASE WHEN m.Estado = 'Retirado' THEN 1 ELSE 0 END) AS Retirados,
       SUM(CASE WHEN m.Estado = 'Trasladado' THEN 1 ELSE 0 END) AS Trasladados
FROM MATRICULA m
GROUP BY m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion
ORDER BY m.`AñoEscolar` DESC, m.Nivel, m.Grado;

-- Consulta 6: Estudiantes de un apoderado específico (sentido inverso de la FK)
-- Usa el índice idx_estudiante_apoderado
SELECT e.DNI, CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante,
       e.FechaNacimiento, e.DistritoDomicilio
FROM ESTUDIANTE e
WHERE e.DNI_Apoderado = '56345876'
ORDER BY e.ApellidoPaterno;

-- Consulta 7: Matrículas declaradas por un responsable (sentido inverso)
-- Usa el índice idx_matricula_responsable
SELECT m.DNI_Estudiante, m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion,
       m.FechaSuscripcion, m.LugarSuscripcion
FROM MATRICULA m
WHERE m.DNI_Responsable = '29481029'
ORDER BY m.`AñoEscolar` DESC;

-- Consulta 8: Detalle completo de la última matrícula de un estudiante
-- JOIN múltiple entre ESTUDIANTE, MATRICULA, PADRE_APODERADO y SECRETARIA
SELECT e.DNI,
       CONCAT(e.ApellidoPaterno, ' ', e.ApellidoMaterno, ', ', e.Nombres) AS Estudiante,
       m.`AñoEscolar`, m.Nivel, m.Grado, m.Seccion, m.Estado,
       m.LugarSuscripcion, m.FechaSuscripcion,
       CONCAT(p.ApellidoPaterno, ' ', p.ApellidoMaterno, ', ', p.Nombres) AS Responsable,
       CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria
FROM MATRICULA m
INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
INNER JOIN PADRE_APODERADO p ON m.DNI_Responsable = p.DNI
INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI
WHERE m.DNI_Estudiante = '56743478'
ORDER BY m.`AñoEscolar` DESC
LIMIT 1;

-- Consulta 9: Logros académicos de un estudiante y su I.E. de procedencia
-- JOIN entre CONSTANCIA_LOGROS, LOGRO e INSTITUCION_EDUCATIVA (filtro por idx_constancia_estudiante)
SELECT c.CodigoVirtual, l.`AñoEscolar`, l.GradoCursado,
       i.NombreIE, i.TipoIE, l.SituacionFinal
FROM CONSTANCIA_LOGROS c
INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual
INNER JOIN INSTITUCION_EDUCATIVA i ON l.CodigoModularIE = i.CodigoModularIE
WHERE c.DNI_Estudiante = '74922482'
ORDER BY l.`AñoEscolar`;

-- Consulta 10: Matrículas registradas por la secretaria en un año, por nivel
-- JOIN entre MATRICULA y SECRETARIA con agrupación (usa idx_matricula_secretaria y idx_matricula_periodo)
SELECT s.DNI, CONCAT(s.ApellidoPaterno, ' ', s.ApellidoMaterno, ', ', s.Nombres) AS Secretaria,
       m.Nivel, COUNT(*) AS TotalMatriculas
FROM MATRICULA m
INNER JOIN SECRETARIA s ON m.DNI_Secretaria = s.DNI
WHERE m.`AñoEscolar` = 2026
GROUP BY s.DNI, s.ApellidoPaterno, s.ApellidoMaterno, s.Nombres, m.Nivel
ORDER BY m.Nivel;
