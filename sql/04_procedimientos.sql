USE bd_matricula_paola_frassinetti;

-- ============================================================
-- Procedimientos almacenados del aplicativo
-- No modifican ninguna tabla del modelo: solo leen y escriben datos.
-- Errores de regla de negocio: SIGNAL SQLSTATE '45000' con mensaje claro.
-- ============================================================
DROP PROCEDURE IF EXISTS sp_registrar_matricula;
DROP PROCEDURE IF EXISTS sp_actualizar_estado_matricula;
DROP PROCEDURE IF EXISTS sp_buscar_estudiante;
DROP PROCEDURE IF EXISTS sp_listar_hermanos;
DROP PROCEDURE IF EXISTS sp_verificar_matriculados;

DELIMITER //

-- 1) Registrar una matrícula validando las reglas del proceso
CREATE PROCEDURE sp_registrar_matricula(
    IN p_dni_estudiante   CHAR(8),
    IN p_anio             SMALLINT,
    IN p_nivel            VARCHAR(10),
    IN p_grado            VARCHAR(5),
    IN p_seccion          VARCHAR(5),
    IN p_dni_responsable  CHAR(8),
    IN p_dni_secretaria   CHAR(8),
    IN p_lugar            VARCHAR(30),
    IN p_fecha            DATE
)
BEGIN
    DECLARE v_capacidad INT DEFAULT 30;
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_msg VARCHAR(128);

    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no está registrado';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM PADRE_APODERADO WHERE DNI = p_dni_responsable) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El responsable no está registrado';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = p_dni_secretaria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria no está registrada';
    END IF;
    IF p_anio < 2000 OR p_anio > 2100 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El año escolar no es válido';
    END IF;

    -- El responsable debe ser el apoderado del estudiante o uno de sus padres
    IF NOT (EXISTS (SELECT 1 FROM ESTUDIANTE
                    WHERE DNI = p_dni_estudiante AND DNI_Apoderado = p_dni_responsable)
         OR EXISTS (SELECT 1 FROM TIENE_PADRES
                    WHERE DNI_Estudiante = p_dni_estudiante AND DNI_Padre = p_dni_responsable)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El responsable debe ser el apoderado o uno de los padres del estudiante';
    END IF;

    -- Una sola matrícula por estudiante y año escolar
    IF EXISTS (SELECT 1 FROM MATRICULA
               WHERE DNI_Estudiante = p_dni_estudiante AND AñoEscolar = p_anio) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El estudiante ya tiene una matrícula en ese año escolar';
    END IF;

    -- Capacidad máxima por sección (solo cuentan los matriculados)
    SELECT COUNT(*) INTO v_total
    FROM MATRICULA
    WHERE AñoEscolar = p_anio AND Nivel = p_nivel AND Grado = p_grado
      AND Seccion = p_seccion AND Estado = 'Matriculado';
    IF v_total >= v_capacidad THEN
        SET v_msg = CONCAT('La sección ya alcanzó el máximo de ', v_capacidad, ' estudiantes');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    INSERT INTO MATRICULA (DNI_Estudiante, AñoEscolar, Nivel, Grado, Seccion, Estado,
                           LugarSuscripcion, FechaSuscripcion, DNI_Responsable, DNI_Secretaria)
    VALUES (p_dni_estudiante, p_anio, p_nivel, p_grado, p_seccion, 'Matriculado',
            p_lugar, p_fecha, p_dni_responsable, p_dni_secretaria);
END//

-- 2) Cambiar el estado de una matrícula
CREATE PROCEDURE sp_actualizar_estado_matricula(
    IN p_dni_estudiante CHAR(8),
    IN p_anio           SMALLINT,
    IN p_estado         VARCHAR(15)
)
BEGIN
    DECLARE v_estado_actual VARCHAR(15);
    DECLARE v_nivel VARCHAR(10);
    DECLARE v_grado VARCHAR(5);
    DECLARE v_seccion VARCHAR(5);
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_capacidad INT DEFAULT 30;
    DECLARE v_msg VARCHAR(128);

    IF p_estado NOT IN ('Matriculado', 'Retirado', 'Trasladado') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Estado no válido: use Matriculado, Retirado o Trasladado';
    END IF;

    SELECT Estado, Nivel, Grado, Seccion
      INTO v_estado_actual, v_nivel, v_grado, v_seccion
    FROM MATRICULA
    WHERE DNI_Estudiante = p_dni_estudiante AND AñoEscolar = p_anio;

    IF v_estado_actual IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No existe una matrícula de ese estudiante en ese año escolar';
    END IF;

    -- Reactivar una matrícula no puede superar la capacidad de la sección
    IF p_estado = 'Matriculado' AND v_estado_actual <> 'Matriculado' THEN
        SELECT COUNT(*) INTO v_total
        FROM MATRICULA
        WHERE AñoEscolar = p_anio AND Nivel = v_nivel AND Grado = v_grado
          AND Seccion = v_seccion AND Estado = 'Matriculado';
        IF v_total >= v_capacidad THEN
            SET v_msg = CONCAT('La sección ya alcanzó el máximo de ', v_capacidad, ' estudiantes');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    UPDATE MATRICULA SET Estado = p_estado
    WHERE DNI_Estudiante = p_dni_estudiante AND AñoEscolar = p_anio;
END//

-- 3) Buscar estudiantes por apellidos y nombres (coincidencia por inicio; vacío = cualquiera)
CREATE PROCEDURE sp_buscar_estudiante(
    IN p_apellido_paterno VARCHAR(30),
    IN p_apellido_materno VARCHAR(30),
    IN p_nombres          VARCHAR(50)
)
BEGIN
    SELECT DNI, ApellidoPaterno, ApellidoMaterno, Nombres, FechaNacimiento, Celular
    FROM ESTUDIANTE
    WHERE ApellidoPaterno LIKE CONCAT(TRIM(COALESCE(p_apellido_paterno, '')), '%')
      AND ApellidoMaterno LIKE CONCAT(TRIM(COALESCE(p_apellido_materno, '')), '%')
      AND Nombres         LIKE CONCAT(TRIM(COALESCE(p_nombres, '')), '%')
    ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres;
END//

-- 4) Hermanos de un estudiante (la relación se guarda en un solo sentido; se lee en ambos)
CREATE PROCEDURE sp_listar_hermanos(
    IN p_dni_estudiante CHAR(8)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no está registrado';
    END IF;

    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres
    FROM HERMANDAD h
    INNER JOIN ESTUDIANTE e ON e.DNI = h.DNI_HermanoB
    WHERE h.DNI_HermanoA = p_dni_estudiante
    UNION
    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres
    FROM HERMANDAD h
    INNER JOIN ESTUDIANTE e ON e.DNI = h.DNI_HermanoA
    WHERE h.DNI_HermanoB = p_dni_estudiante
    ORDER BY ApellidoPaterno, ApellidoMaterno, Nombres;
END//

-- 5) Comparar dos años: quiénes continúan, quiénes no tienen matrícula y quiénes son nuevos
CREATE PROCEDURE sp_verificar_matriculados(
    IN p_anio_anterior SMALLINT,
    IN p_anio_actual   SMALLINT
)
BEGIN
    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
           ma.Nivel AS NivelAnterior, ma.Grado AS GradoAnterior,
           mc.Nivel AS NivelActual,   mc.Grado AS GradoActual,
           CASE WHEN mc.DNI_Estudiante IS NOT NULL THEN 'Continúa'
                ELSE 'Sin matrícula en el año actual' END AS Situacion
    FROM MATRICULA ma
    INNER JOIN ESTUDIANTE e ON e.DNI = ma.DNI_Estudiante
    LEFT JOIN MATRICULA mc
           ON mc.DNI_Estudiante = ma.DNI_Estudiante AND mc.AñoEscolar = p_anio_actual
    WHERE ma.AñoEscolar = p_anio_anterior
    UNION ALL
    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
           NULL, NULL, mc.Nivel, mc.Grado, 'Nuevo'
    FROM MATRICULA mc
    INNER JOIN ESTUDIANTE e ON e.DNI = mc.DNI_Estudiante
    WHERE mc.AñoEscolar = p_anio_actual
      AND NOT EXISTS (SELECT 1 FROM MATRICULA ma
                      WHERE ma.DNI_Estudiante = mc.DNI_Estudiante
                        AND ma.AñoEscolar = p_anio_anterior)
    ORDER BY Situacion, ApellidoPaterno, ApellidoMaterno, Nombres;
END//

DELIMITER ;
