-- Script 03: Procedimientos almacenados del aplicativo
-- Conserva nombres y parámetros de los 5 existentes (§14.3).
-- Los procedimientos NO hacen COMMIT (la transacción la controla el servicio de Python).
-- Errores de regla de negocio: SIGNAL SQLSTATE '45000' con mensaje claro en español.
-- SQL SECURITY DEFINER (por defecto) para poder escribir con matricula_app (solo SELECT/EXECUTE).
USE bd_matricula;

DROP PROCEDURE IF EXISTS sp_registrar_matricula;
DROP PROCEDURE IF EXISTS sp_actualizar_estado_matricula;
DROP PROCEDURE IF EXISTS sp_buscar_estudiante;
DROP PROCEDURE IF EXISTS sp_listar_hermanos;
DROP PROCEDURE IF EXISTS sp_verificar_matriculados;
DROP PROCEDURE IF EXISTS sp_estudiante_insertar;
DROP PROCEDURE IF EXISTS sp_estudiante_actualizar;
DROP PROCEDURE IF EXISTS sp_estudiante_eliminar;
DROP PROCEDURE IF EXISTS sp_padre_insertar;
DROP PROCEDURE IF EXISTS sp_padre_actualizar;
DROP PROCEDURE IF EXISTS sp_padre_eliminar;
DROP PROCEDURE IF EXISTS sp_contacto_actualizar;
DROP PROCEDURE IF EXISTS sp_ie_insertar;
DROP PROCEDURE IF EXISTS sp_ie_actualizar;
DROP PROCEDURE IF EXISTS sp_ie_eliminar;
DROP PROCEDURE IF EXISTS sp_constancia_insertar;
DROP PROCEDURE IF EXISTS sp_constancia_actualizar;
DROP PROCEDURE IF EXISTS sp_constancia_eliminar;
DROP PROCEDURE IF EXISTS sp_logro_insertar;
DROP PROCEDURE IF EXISTS sp_logro_actualizar;
DROP PROCEDURE IF EXISTS sp_logro_eliminar;
DROP PROCEDURE IF EXISTS sp_cambiar_seccion;
DROP PROCEDURE IF EXISTS sp_eliminar_matricula;
DROP PROCEDURE IF EXISTS sp_tiene_padres_insertar;
DROP PROCEDURE IF EXISTS sp_tiene_padres_eliminar;
DROP PROCEDURE IF EXISTS sp_hermandad_insertar;
DROP PROCEDURE IF EXISTS sp_hermandad_eliminar;
DROP PROCEDURE IF EXISTS sp_nee_insertar;
DROP PROCEDURE IF EXISTS sp_nee_eliminar;
DROP PROCEDURE IF EXISTS sp_hermanos_ie_insertar;
DROP PROCEDURE IF EXISTS sp_hermanos_ie_eliminar;
DROP PROCEDURE IF EXISTS sp_usuario_registrar;
DROP PROCEDURE IF EXISTS sp_usuario_obtener;
DROP PROCEDURE IF EXISTS sp_usuario_registrar_acceso;
DROP PROCEDURE IF EXISTS sp_usuario_cambiar_clave;
DROP PROCEDURE IF EXISTS sp_usuario_cambiar_estado;
DROP PROCEDURE IF EXISTS sp_cupos_seccion;
DROP PROCEDURE IF EXISTS sp_padron;
DROP PROCEDURE IF EXISTS sp_secretaria_insertar;
DROP PROCEDURE IF EXISTS sp_secretaria_actualizar;
DROP PROCEDURE IF EXISTS sp_secretaria_eliminar;
DROP PROCEDURE IF EXISTS sp_contacto_insertar;
DROP PROCEDURE IF EXISTS sp_contacto_eliminar;

DROP FUNCTION IF EXISTS fn_grado_siguiente;

DELIMITER //

-- ===========================================================================
-- 1) Registrar una matrícula (conservado, §14.3) + FOR UPDATE en el cupo
-- ===========================================================================
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

    IF NOT (EXISTS (SELECT 1 FROM ESTUDIANTE
                    WHERE DNI = p_dni_estudiante AND DNI_Apoderado = p_dni_responsable)
         OR EXISTS (SELECT 1 FROM TIENE_PADRES
                    WHERE DNI_Estudiante = p_dni_estudiante AND DNI_Padre = p_dni_responsable)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El responsable debe ser el apoderado o uno de los padres del estudiante';
    END IF;

    IF EXISTS (SELECT 1 FROM MATRICULA
               WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El estudiante ya tiene una matrícula en ese año escolar';
    END IF;

    -- Cupo máximo por sección (solo matriculados), con SELECT ... FOR UPDATE
    SELECT COUNT(*) INTO v_total
    FROM MATRICULA
    WHERE `AñoEscolar` = p_anio AND Nivel = p_nivel AND Grado = p_grado
      AND Seccion = p_seccion AND Estado = 'Matriculado'
    FOR UPDATE;
    IF v_total >= v_capacidad THEN
        SET v_msg = CONCAT('La sección ya alcanzó el máximo de ', v_capacidad, ' estudiantes');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    INSERT INTO MATRICULA (DNI_Estudiante, `AñoEscolar`, Nivel, Grado, Seccion, Estado,
                           LugarSuscripcion, FechaSuscripcion, DNI_Responsable, DNI_Secretaria)
    VALUES (p_dni_estudiante, p_anio, p_nivel, p_grado, p_seccion, 'Matriculado',
            p_lugar, p_fecha, p_dni_responsable, p_dni_secretaria);
END//

-- ===========================================================================
-- 2) Cambiar el estado de una matrícula (conservado, §14.3)
-- ===========================================================================
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
    WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio;

    IF v_estado_actual IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No existe una matrícula de ese estudiante en ese año escolar';
    END IF;

    IF p_estado = 'Matriculado' AND v_estado_actual <> 'Matriculado' THEN
        SELECT COUNT(*) INTO v_total
        FROM MATRICULA
        WHERE `AñoEscolar` = p_anio AND Nivel = v_nivel AND Grado = v_grado
          AND Seccion = v_seccion AND Estado = 'Matriculado';
        IF v_total >= v_capacidad THEN
            SET v_msg = CONCAT('La sección ya alcanzó el máximo de ', v_capacidad, ' estudiantes');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    UPDATE MATRICULA SET Estado = p_estado
    WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio;
END//

-- ===========================================================================
-- 3) Buscar estudiantes por apellidos y nombres (conservado, §14.3)
-- ===========================================================================
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

-- ===========================================================================
-- 4) Hermanos de un estudiante (conservado, §14.3)
-- ===========================================================================
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

-- ===========================================================================
-- 5) Comparar dos años (conservado, §14.3)
-- ===========================================================================
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
           ON mc.DNI_Estudiante = ma.DNI_Estudiante AND mc.`AñoEscolar` = p_anio_actual
    WHERE ma.`AñoEscolar` = p_anio_anterior
    UNION ALL
    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
           NULL, NULL, mc.Nivel, mc.Grado, 'Nuevo'
    FROM MATRICULA mc
    INNER JOIN ESTUDIANTE e ON e.DNI = mc.DNI_Estudiante
    WHERE mc.`AñoEscolar` = p_anio_actual
      AND NOT EXISTS (SELECT 1 FROM MATRICULA ma
                      WHERE ma.DNI_Estudiante = mc.DNI_Estudiante
                        AND ma.`AñoEscolar` = p_anio_anterior)
    ORDER BY Situacion, ApellidoPaterno, ApellidoMaterno, Nombres;
END//

-- ===========================================================================
-- 6) CRUD ESTUDIANTE
--    sp_estudiante_insertar recibe p_id_contacto opcional; si es NULL crea el
--    contacto y lo devuelve por p_id_contacto_out (§14.8).
-- ===========================================================================
CREATE PROCEDURE sp_estudiante_insertar(
    IN  p_dni                 CHAR(8),
    IN  p_sexo                CHAR(1),
    IN  p_nombres             VARCHAR(50),
    IN  p_apellido_paterno    VARCHAR(30),
    IN  p_apellido_materno    VARCHAR(30),
    IN  p_fecha_nacimiento    DATE,
    IN  p_distrito_nacimiento VARCHAR(30),
    IN  p_provincia_nacimiento VARCHAR(30),
    IN  p_departamento_nacimiento VARCHAR(30),
    IN  p_pais_nacimiento     VARCHAR(30),
    IN  p_domicilio_actual    VARCHAR(100),
    IN  p_distrito_domicilio  VARCHAR(30),
    IN  p_celular             CHAR(9),
    IN  p_correo_electronico  VARCHAR(50),
    IN  p_religion            VARCHAR(20),
    IN  p_lugar_que_ocupa     TINYINT UNSIGNED,
    IN  p_tipo_atencion       VARCHAR(20),
    IN  p_enfermedad_cronica  VARCHAR(50),
    IN  p_vive_con_padre      BOOLEAN,
    IN  p_vive_con_madre      BOOLEAN,
    IN  p_el_padre_vive       BOOLEAN,
    IN  p_la_madre_vive       BOOLEAN,
    IN  p_id_contacto         INT UNSIGNED,
    IN  p_nombre_contacto     VARCHAR(110),
    IN  p_celular_contacto    CHAR(9),
    IN  p_codigo_modular_ie   VARCHAR(10),
    IN  p_dni_apoderado       CHAR(8)
)
BEGIN
    DECLARE v_id_contacto INT UNSIGNED;

    IF EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante ya está registrado';
    END IF;

    -- Resolver contacto de emergencia
    IF p_id_contacto IS NULL THEN
        INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia)
        VALUES (p_nombre_contacto, p_celular_contacto);
        SET v_id_contacto = LAST_INSERT_ID();
    ELSE
        IF NOT EXISTS (SELECT 1 FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = p_id_contacto) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El contacto de emergencia no existe';
        END IF;
        SET v_id_contacto = p_id_contacto;
    END IF;

    INSERT INTO ESTUDIANTE (
        DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento,
        DistritoNacimiento, ProvinciaNacimiento, DepartamentoNacimiento, PaisNacimiento,
        DomicilioActual, DistritoDomicilio, Celular, CorreoElectronico, Religion,
        LugarQueOcupa, TipoAtencion, EnfermedadCronica,
        ViveConPadre, ViveConMadre, ElPadreVive, LaMadreVive,
        IdContactoEmergencia, CodigoModularIE, DNI_Apoderado
    ) VALUES (
        p_dni, p_sexo, p_nombres, p_apellido_paterno, p_apellido_materno, p_fecha_nacimiento,
        p_distrito_nacimiento, p_provincia_nacimiento, p_departamento_nacimiento, p_pais_nacimiento,
        p_domicilio_actual, p_distrito_domicilio, p_celular, p_correo_electronico, p_religion,
        p_lugar_que_ocupa, p_tipo_atencion, p_enfermedad_cronica,
        p_vive_con_padre, p_vive_con_madre, p_el_padre_vive, p_la_madre_vive,
        v_id_contacto, p_codigo_modular_ie, p_dni_apoderado
    );

    SELECT v_id_contacto AS id_contacto;
END//

CREATE PROCEDURE sp_estudiante_actualizar(
    IN  p_dni                 CHAR(8),
    IN  p_sexo                CHAR(1),
    IN  p_nombres             VARCHAR(50),
    IN  p_apellido_paterno    VARCHAR(30),
    IN  p_apellido_materno    VARCHAR(30),
    IN  p_fecha_nacimiento    DATE,
    IN  p_distrito_nacimiento VARCHAR(30),
    IN  p_provincia_nacimiento VARCHAR(30),
    IN  p_departamento_nacimiento VARCHAR(30),
    IN  p_pais_nacimiento     VARCHAR(30),
    IN  p_domicilio_actual    VARCHAR(100),
    IN  p_distrito_domicilio  VARCHAR(30),
    IN  p_celular             CHAR(9),
    IN  p_correo_electronico  VARCHAR(50),
    IN  p_religion            VARCHAR(20),
    IN  p_lugar_que_ocupa     TINYINT UNSIGNED,
    IN  p_tipo_atencion       VARCHAR(20),
    IN  p_enfermedad_cronica  VARCHAR(50),
    IN  p_vive_con_padre      BOOLEAN,
    IN  p_vive_con_madre      BOOLEAN,
    IN  p_el_padre_vive       BOOLEAN,
    IN  p_la_madre_vive       BOOLEAN,
    IN  p_id_contacto         INT UNSIGNED,
    IN  p_codigo_modular_ie   VARCHAR(10),
    IN  p_dni_apoderado       CHAR(8)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;

    UPDATE ESTUDIANTE SET
        Sexo = p_sexo,
        Nombres = p_nombres,
        ApellidoPaterno = p_apellido_paterno,
        ApellidoMaterno = p_apellido_materno,
        FechaNacimiento = p_fecha_nacimiento,
        DistritoNacimiento = p_distrito_nacimiento,
        ProvinciaNacimiento = p_provincia_nacimiento,
        DepartamentoNacimiento = p_departamento_nacimiento,
        PaisNacimiento = p_pais_nacimiento,
        DomicilioActual = p_domicilio_actual,
        DistritoDomicilio = p_distrito_domicilio,
        Celular = p_celular,
        CorreoElectronico = p_correo_electronico,
        Religion = p_religion,
        LugarQueOcupa = p_lugar_que_ocupa,
        TipoAtencion = p_tipo_atencion,
        EnfermedadCronica = p_enfermedad_cronica,
        ViveConPadre = p_vive_con_padre,
        ViveConMadre = p_vive_con_madre,
        ElPadreVive = p_el_padre_vive,
        LaMadreVive = p_la_madre_vive,
        IdContactoEmergencia = p_id_contacto,
        CodigoModularIE = p_codigo_modular_ie,
        DNI_Apoderado = p_dni_apoderado
    WHERE DNI = p_dni;
END//

CREATE PROCEDURE sp_estudiante_eliminar(IN p_dni CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;

    -- Si tiene matrícula Matriculado → rechaza (§13.3)
    IF EXISTS (SELECT 1 FROM MATRICULA WHERE DNI_Estudiante = p_dni AND Estado = 'Matriculado') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Primero debe retirar la matrícula antes de eliminar el estudiante';
    END IF;

    -- Borrar en orden por las FK
    DELETE FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = p_dni;
    DELETE FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = p_dni;
    DELETE FROM HERMANDAD WHERE DNI_HermanoA = p_dni OR DNI_HermanoB = p_dni;
    DELETE FROM TIENE_PADRES WHERE DNI_Estudiante = p_dni;
    DELETE FROM LOGRO WHERE CodigoVirtual IN (SELECT CodigoVirtual FROM CONSTANCIA_LOGROS WHERE DNI_Estudiante = p_dni);
    DELETE FROM CONSTANCIA_LOGROS WHERE DNI_Estudiante = p_dni;

    -- Borrar contacto solo si ningún otro estudiante lo usa
    DELETE FROM ESTUDIANTE WHERE DNI = p_dni;

    DELETE FROM CONTACTO_EMERGENCIA
    WHERE IdContactoEmergencia NOT IN (SELECT DISTINCT IdContactoEmergencia FROM ESTUDIANTE);
END//

-- ===========================================================================
-- 7) CRUD PADRE_APODERADO
-- ===========================================================================
CREATE PROCEDURE sp_padre_insertar(
    IN p_dni               CHAR(8),
    IN p_sexo              CHAR(1),
    IN p_nombres           VARCHAR(50),
    IN p_apellido_paterno  VARCHAR(30),
    IN p_apellido_materno  VARCHAR(30),
    IN p_fecha_nacimiento  DATE,
    IN p_ocupacion_actual  VARCHAR(50),
    IN p_grado_instruccion VARCHAR(30),
    IN p_domicilio_actual  VARCHAR(100),
    IN p_distrito_domicilio VARCHAR(30),
    IN p_telefono_fijo     CHAR(9),
    IN p_celular           CHAR(9),
    IN p_correo_electronico VARCHAR(50)
)
BEGIN
    IF EXISTS (SELECT 1 FROM PADRE_APODERADO WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre/apoderado ya está registrado';
    END IF;
    INSERT INTO PADRE_APODERADO (
        DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento,
        OcupacionActual, GradoInstruccion, DomicilioActual, DistritoDomicilio,
        TelefonoFijo, Celular, CorreoElectronico
    ) VALUES (
        p_dni, p_sexo, p_nombres, p_apellido_paterno, p_apellido_materno, p_fecha_nacimiento,
        p_ocupacion_actual, p_grado_instruccion, p_domicilio_actual, p_distrito_domicilio,
        p_telefono_fijo, p_celular, p_correo_electronico
    );
END//

CREATE PROCEDURE sp_padre_actualizar(
    IN p_dni               CHAR(8),
    IN p_sexo              CHAR(1),
    IN p_nombres           VARCHAR(50),
    IN p_apellido_paterno  VARCHAR(30),
    IN p_apellido_materno  VARCHAR(30),
    IN p_fecha_nacimiento  DATE,
    IN p_ocupacion_actual  VARCHAR(50),
    IN p_grado_instruccion VARCHAR(30),
    IN p_domicilio_actual  VARCHAR(100),
    IN p_distrito_domicilio VARCHAR(30),
    IN p_telefono_fijo     CHAR(9),
    IN p_celular           CHAR(9),
    IN p_correo_electronico VARCHAR(50)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM PADRE_APODERADO WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre/apoderado no existe';
    END IF;
    UPDATE PADRE_APODERADO SET
        Sexo = p_sexo, Nombres = p_nombres, ApellidoPaterno = p_apellido_paterno,
        ApellidoMaterno = p_apellido_materno, FechaNacimiento = p_fecha_nacimiento,
        OcupacionActual = p_ocupacion_actual, GradoInstruccion = p_grado_instruccion,
        DomicilioActual = p_domicilio_actual, DistritoDomicilio = p_distrito_domicilio,
        TelefonoFijo = p_telefono_fijo, Celular = p_celular,
        CorreoElectronico = p_correo_electronico
    WHERE DNI = p_dni;
END//

CREATE PROCEDURE sp_padre_eliminar(IN p_dni CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM PADRE_APODERADO WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre/apoderado no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM TIENE_PADRES WHERE DNI_Padre = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre está referenciado por TIENE_PADRES';
    END IF;
    IF EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI_Apoderado = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre es apoderado de un estudiante';
    END IF;
    IF EXISTS (SELECT 1 FROM MATRICULA WHERE DNI_Responsable = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre es responsable de una matrícula';
    END IF;
    DELETE FROM PADRE_APODERADO WHERE DNI = p_dni;
END//

-- ===========================================================================
-- 8) sp_contacto_actualizar (afecta a todos los hermanos que lo comparten)
-- ===========================================================================
CREATE PROCEDURE sp_contacto_actualizar(
    IN p_id_contacto             INT UNSIGNED,
    IN p_nombre_contacto_emergencia VARCHAR(110),
    IN p_celular_emergencia      CHAR(9)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = p_id_contacto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El contacto de emergencia no existe';
    END IF;
    UPDATE CONTACTO_EMERGENCIA
    SET NombreContactoEmergencia = p_nombre_contacto_emergencia,
        CelularEmergencia = p_celular_emergencia
    WHERE IdContactoEmergencia = p_id_contacto;
END//

-- ===========================================================================
-- 9) CRUD INSTITUCION_EDUCATIVA
-- ===========================================================================
CREATE PROCEDURE sp_ie_insertar(
    IN p_codigo_modular_ie VARCHAR(10),
    IN p_nombre_ie         VARCHAR(50),
    IN p_tipo_ie           VARCHAR(20)
)
BEGIN
    IF EXISTS (SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La institución educativa ya existe';
    END IF;
    INSERT INTO INSTITUCION_EDUCATIVA (CodigoModularIE, NombreIE, TipoIE)
    VALUES (p_codigo_modular_ie, p_nombre_ie, p_tipo_ie);
END//

CREATE PROCEDURE sp_ie_actualizar(
    IN p_codigo_modular_ie VARCHAR(10),
    IN p_nombre_ie         VARCHAR(50),
    IN p_tipo_ie           VARCHAR(20)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La institución educativa no existe';
    END IF;
    UPDATE INSTITUCION_EDUCATIVA SET NombreIE = p_nombre_ie, TipoIE = p_tipo_ie
    WHERE CodigoModularIE = p_codigo_modular_ie;
END//

CREATE PROCEDURE sp_ie_eliminar(IN p_codigo_modular_ie VARCHAR(10))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La institución educativa no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM ESTUDIANTE WHERE CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Hay estudiantes que referencian la I.E.';
    END IF;
    IF EXISTS (SELECT 1 FROM LOGRO WHERE CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Hay logros que referencian la I.E.';
    END IF;
    IF EXISTS (SELECT 1 FROM CONSTANCIA_LOGROS c INNER JOIN LOGRO l ON l.CodigoVirtual = c.CodigoVirtual WHERE l.CodigoModularIE = p_codigo_modular_ie) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Hay constancias que referencian la I.E.';
    END IF;
    DELETE FROM INSTITUCION_EDUCATIVA WHERE CodigoModularIE = p_codigo_modular_ie;
END//

-- ===========================================================================
-- 10) CRUD CONSTANCIA_LOGROS
-- ===========================================================================
CREATE PROCEDURE sp_constancia_insertar(
    IN p_codigo_virtual    CHAR(8),
    IN p_dni_estudiante    CHAR(8),
    IN p_nivel_educativo   VARCHAR(10),
    IN p_fecha_hora_emision DATETIME
)
BEGIN
    IF EXISTS (SELECT 1 FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = p_codigo_virtual) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La constancia ya existe';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;
    INSERT INTO CONSTANCIA_LOGROS (CodigoVirtual, DNI_Estudiante, NivelEducativo, FechaHoraEmision)
    VALUES (p_codigo_virtual, p_dni_estudiante, p_nivel_educativo, p_fecha_hora_emision);
END//

CREATE PROCEDURE sp_constancia_actualizar(
    IN p_codigo_virtual    CHAR(8),
    IN p_dni_estudiante    CHAR(8),
    IN p_nivel_educativo   VARCHAR(10),
    IN p_fecha_hora_emision DATETIME
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = p_codigo_virtual) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La constancia no existe';
    END IF;
    UPDATE CONSTANCIA_LOGROS
    SET DNI_Estudiante = p_dni_estudiante, NivelEducativo = p_nivel_educativo,
        FechaHoraEmision = p_fecha_hora_emision
    WHERE CodigoVirtual = p_codigo_virtual;
END//

CREATE PROCEDURE sp_constancia_eliminar(IN p_codigo_virtual CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = p_codigo_virtual) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La constancia no existe';
    END IF;
    DELETE FROM LOGRO WHERE CodigoVirtual = p_codigo_virtual;
    DELETE FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = p_codigo_virtual;
END//

-- ===========================================================================
-- 11) CRUD LOGRO
-- ===========================================================================
CREATE PROCEDURE sp_logro_insertar(
    IN p_codigo_virtual  CHAR(8),
    IN p_anio_escolar    SMALLINT,
    IN p_grado_cursado   VARCHAR(5),
    IN p_codigo_modular_ie VARCHAR(10),
    IN p_situacion_final  VARCHAR(30)
)
BEGIN
    IF EXISTS (SELECT 1 FROM LOGRO WHERE CodigoVirtual = p_codigo_virtual AND `AñoEscolar` = p_anio_escolar) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El logro ya existe';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM CONSTANCIA_LOGROS WHERE CodigoVirtual = p_codigo_virtual) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La constancia no existe';
    END IF;
    INSERT INTO LOGRO (CodigoVirtual, `AñoEscolar`, GradoCursado, CodigoModularIE, SituacionFinal)
    VALUES (p_codigo_virtual, p_anio_escolar, p_grado_cursado, p_codigo_modular_ie, p_situacion_final);
END//

CREATE PROCEDURE sp_logro_actualizar(
    IN p_codigo_virtual  CHAR(8),
    IN p_anio_escolar    SMALLINT,
    IN p_grado_cursado   VARCHAR(5),
    IN p_codigo_modular_ie VARCHAR(10),
    IN p_situacion_final  VARCHAR(30)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM LOGRO WHERE CodigoVirtual = p_codigo_virtual AND `AñoEscolar` = p_anio_escolar) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El logro no existe';
    END IF;
    UPDATE LOGRO
    SET GradoCursado = p_grado_cursado, CodigoModularIE = p_codigo_modular_ie,
        SituacionFinal = p_situacion_final
    WHERE CodigoVirtual = p_codigo_virtual AND `AñoEscolar` = p_anio_escolar;
END//

CREATE PROCEDURE sp_logro_eliminar(IN p_codigo_virtual CHAR(8), IN p_anio_escolar SMALLINT)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM LOGRO WHERE CodigoVirtual = p_codigo_virtual AND `AñoEscolar` = p_anio_escolar) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El logro no existe';
    END IF;
    DELETE FROM LOGRO WHERE CodigoVirtual = p_codigo_virtual AND `AñoEscolar` = p_anio_escolar;
END//

-- ===========================================================================
-- 12) sp_cambiar_seccion y sp_eliminar_matricula
-- ===========================================================================
CREATE PROCEDURE sp_cambiar_seccion(
    IN p_dni_estudiante CHAR(8),
    IN p_anio           SMALLINT,
    IN p_nueva_seccion  VARCHAR(5)
)
BEGIN
    DECLARE v_nivel VARCHAR(10);
    DECLARE v_grado VARCHAR(5);
    DECLARE v_seccion_actual VARCHAR(5);
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_capacidad INT DEFAULT 30;
    DECLARE v_msg VARCHAR(128);

    SELECT Nivel, Grado, Seccion INTO v_nivel, v_grado, v_seccion_actual
    FROM MATRICULA
    WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio;

    IF v_seccion_actual IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No existe matrícula de ese estudiante en ese año';
    END IF;

    IF v_seccion_actual = p_nueva_seccion THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La sección es la misma';
    END IF;

    SELECT COUNT(*) INTO v_total
    FROM MATRICULA
    WHERE `AñoEscolar` = p_anio AND Nivel = v_nivel AND Grado = v_grado
      AND Seccion = p_nueva_seccion AND Estado = 'Matriculado';
    IF v_total >= v_capacidad THEN
        SET v_msg = CONCAT('La sección ya alcanzó el máximo de ', v_capacidad, ' estudiantes');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    UPDATE MATRICULA SET Seccion = p_nueva_seccion
    WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio;
END//

CREATE PROCEDURE sp_eliminar_matricula(IN p_dni_estudiante CHAR(8), IN p_anio SMALLINT)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM MATRICULA WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No existe matrícula de ese estudiante en ese año';
    END IF;
    DELETE FROM MATRICULA WHERE DNI_Estudiante = p_dni_estudiante AND `AñoEscolar` = p_anio;
END//

-- ===========================================================================
-- 13) CRUD TIENE_PADRES
-- ===========================================================================
CREATE PROCEDURE sp_tiene_padres_insertar(IN p_dni_estudiante CHAR(8), IN p_dni_padre CHAR(8))
BEGIN
    DECLARE v_total INT DEFAULT 0;
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM PADRE_APODERADO WHERE DNI = p_dni_padre) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El padre no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM TIENE_PADRES WHERE DNI_Estudiante = p_dni_estudiante AND DNI_Padre = p_dni_padre) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ya existe la relación estudiante-padre';
    END IF;
    SELECT COUNT(*) INTO v_total FROM TIENE_PADRES WHERE DNI_Estudiante = p_dni_estudiante;
    IF v_total >= 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Máximo 2 padres por estudiante';
    END IF;
    INSERT INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES (p_dni_estudiante, p_dni_padre);
END//

CREATE PROCEDURE sp_tiene_padres_eliminar(IN p_dni_estudiante CHAR(8), IN p_dni_padre CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM TIENE_PADRES WHERE DNI_Estudiante = p_dni_estudiante AND DNI_Padre = p_dni_padre) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No existe la relación estudiante-padre';
    END IF;
    DELETE FROM TIENE_PADRES WHERE DNI_Estudiante = p_dni_estudiante AND DNI_Padre = p_dni_padre;
END//

-- ===========================================================================
-- 14) CRUD HERMANDAD
-- ===========================================================================
CREATE PROCEDURE sp_hermandad_insertar(IN p_dni_hermano_a CHAR(8), IN p_dni_hermano_b CHAR(8))
BEGIN
    IF p_dni_hermano_a = p_dni_hermano_b THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un estudiante no puede ser hermano de sí mismo';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_hermano_a) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El hermano A no existe';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_hermano_b) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El hermano B no existe';
    END IF;
    INSERT INTO HERMANDAD (DNI_HermanoA, DNI_HermanoB) VALUES (p_dni_hermano_a, p_dni_hermano_b);
END//

CREATE PROCEDURE sp_hermandad_eliminar(IN p_dni_hermano_a CHAR(8), IN p_dni_hermano_b CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM HERMANDAD WHERE DNI_HermanoA = p_dni_hermano_a AND DNI_HermanoB = p_dni_hermano_b) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No existe la relación de hermandad';
    END IF;
    DELETE FROM HERMANDAD WHERE DNI_HermanoA = p_dni_hermano_a AND DNI_HermanoB = p_dni_hermano_b;
END//

-- ===========================================================================
-- 15) CRUD ESTUDIANTE_NEE
-- ===========================================================================
CREATE PROCEDURE sp_nee_insertar(IN p_dni_estudiante CHAR(8), IN p_necesidad VARCHAR(50))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = p_dni_estudiante AND NecesidadEducativaEspecial = p_necesidad) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La NEE ya existe para el estudiante';
    END IF;
    INSERT INTO ESTUDIANTE_NEE (DNI_Estudiante, NecesidadEducativaEspecial) VALUES (p_dni_estudiante, p_necesidad);
END//

CREATE PROCEDURE sp_nee_eliminar(IN p_dni_estudiante CHAR(8), IN p_necesidad VARCHAR(50))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = p_dni_estudiante AND NecesidadEducativaEspecial = p_necesidad) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La NEE no existe para el estudiante';
    END IF;
    DELETE FROM ESTUDIANTE_NEE WHERE DNI_Estudiante = p_dni_estudiante AND NecesidadEducativaEspecial = p_necesidad;
END//

-- ===========================================================================
-- 16) CRUD ESTUDIANTE_HERMANOS_IE
-- ===========================================================================
CREATE PROCEDURE sp_hermanos_ie_insertar(IN p_dni_estudiante CHAR(8), IN p_nivel_hermano VARCHAR(30))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE WHERE DNI = p_dni_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = p_dni_estudiante AND NivelHermano = p_nivel_hermano) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El hermano en la I.E. ya existe';
    END IF;
    INSERT INTO ESTUDIANTE_HERMANOS_IE (DNI_Estudiante, NivelHermano) VALUES (p_dni_estudiante, p_nivel_hermano);
END//

CREATE PROCEDURE sp_hermanos_ie_eliminar(IN p_dni_estudiante CHAR(8), IN p_nivel_hermano VARCHAR(30))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = p_dni_estudiante AND NivelHermano = p_nivel_hermano) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El hermano en la I.E. no existe';
    END IF;
    DELETE FROM ESTUDIANTE_HERMANOS_IE WHERE DNI_Estudiante = p_dni_estudiante AND NivelHermano = p_nivel_hermano;
END//

-- ===========================================================================
-- 17) CRUD USUARIO
-- ===========================================================================
CREATE PROCEDURE sp_usuario_registrar(
    IN p_nombre_usuario VARCHAR(30),
    IN p_clave_hash     VARCHAR(255),
    IN p_dni            CHAR(8)
)
BEGIN
    IF EXISTS (SELECT 1 FROM USUARIO WHERE NombreUsuario = p_nombre_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de usuario ya existe';
    END IF;
    IF EXISTS (SELECT 1 FROM USUARIO WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El DNI ya tiene una cuenta de usuario';
    END IF;
    INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI)
    VALUES (p_nombre_usuario, p_clave_hash, 'Secretaria', 'Activo', p_dni);
    SELECT LAST_INSERT_ID() AS id_usuario;
END//

CREATE PROCEDURE sp_usuario_obtener(IN p_nombre_usuario VARCHAR(30))
BEGIN
    SELECT IdUsuario, NombreUsuario, ClaveHash, Rol, Estado, DNI, UltimoAcceso
    FROM USUARIO
    WHERE NombreUsuario = p_nombre_usuario;
END//

CREATE PROCEDURE sp_usuario_registrar_acceso(IN p_id_usuario INT UNSIGNED)
BEGIN
    UPDATE USUARIO SET UltimoAcceso = NOW() WHERE IdUsuario = p_id_usuario;
END//

CREATE PROCEDURE sp_usuario_cambiar_clave(IN p_id_usuario INT UNSIGNED, IN p_clave_hash VARCHAR(255))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM USUARIO WHERE IdUsuario = p_id_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El usuario no existe';
    END IF;
    UPDATE USUARIO SET ClaveHash = p_clave_hash WHERE IdUsuario = p_id_usuario;
END//

CREATE PROCEDURE sp_usuario_cambiar_estado(IN p_id_usuario INT UNSIGNED, IN p_estado VARCHAR(10))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM USUARIO WHERE IdUsuario = p_id_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El usuario no existe';
    END IF;
    UPDATE USUARIO SET Estado = p_estado WHERE IdUsuario = p_id_usuario;
END//

-- ===========================================================================
-- 18) sp_cupos_seccion y sp_padron
-- ===========================================================================
CREATE PROCEDURE sp_cupos_seccion(
    IN p_anio   SMALLINT,
    IN p_nivel  VARCHAR(10),
    IN p_grado  VARCHAR(5),
    IN p_seccion VARCHAR(5)
)
BEGIN
    SELECT `AñoEscolar`, Nivel, Grado, Seccion,
           COUNT(*) AS Matriculados,
           30 - COUNT(*) AS Vacantes
    FROM MATRICULA
    WHERE `AñoEscolar` = p_anio AND Nivel = p_nivel AND Grado = p_grado
      AND Seccion = p_seccion AND Estado = 'Matriculado'
    GROUP BY `AñoEscolar`, Nivel, Grado, Seccion;
END//

CREATE PROCEDURE sp_padron(
    IN p_anio    SMALLINT,
    IN p_nivel   VARCHAR(10),
    IN p_grado   VARCHAR(5),
    IN p_seccion VARCHAR(5)
)
BEGIN
    SELECT e.DNI, e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres,
           m.Nivel, m.Grado, m.Seccion, m.Estado
    FROM MATRICULA m
    INNER JOIN ESTUDIANTE e ON m.DNI_Estudiante = e.DNI
    WHERE m.`AñoEscolar` = p_anio
      AND (p_nivel IS NULL OR m.Nivel = p_nivel)
      AND (p_grado IS NULL OR m.Grado = p_grado)
      AND (p_seccion IS NULL OR m.Seccion = p_seccion)
    ORDER BY e.ApellidoPaterno, e.ApellidoMaterno, e.Nombres;
END//

-- ===========================================================================
-- 19) Función fn_grado_siguiente (§13.5 punto 2)
-- ===========================================================================
CREATE FUNCTION fn_grado_siguiente(
    p_nivel          VARCHAR(10),
    p_grado          VARCHAR(5),
    p_situacion_final VARCHAR(30)
) RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_siguiente VARCHAR(20);

    IF p_situacion_final = 'REQUIERE RECUPERACIÓN' THEN
        RETURN p_grado;
    END IF;

    IF p_nivel = 'Inicial' THEN
        IF p_grado = '3 a.' THEN SET v_siguiente = '4 a.';
        ELSEIF p_grado = '4 a.' THEN SET v_siguiente = '5 a.';
        ELSEIF p_grado = '5 a.' THEN SET v_siguiente = '1.°';
        ELSE SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Grado de Inicial inválido';
        END IF;
    ELSEIF p_nivel = 'Primaria' THEN
        IF p_grado = '1.°' THEN SET v_siguiente = '2.°';
        ELSEIF p_grado = '2.°' THEN SET v_siguiente = '3.°';
        ELSEIF p_grado = '3.°' THEN SET v_siguiente = '4.°';
        ELSEIF p_grado = '4.°' THEN SET v_siguiente = '5.°';
        ELSEIF p_grado = '5.°' THEN SET v_siguiente = '6.°';
        ELSEIF p_grado = '6.°' THEN SET v_siguiente = '1.°';
        ELSE SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Grado de Primaria inválido';
        END IF;
    ELSEIF p_nivel = 'Secundaria' THEN
        IF p_grado = '1.°' THEN SET v_siguiente = '2.°';
        ELSEIF p_grado = '2.°' THEN SET v_siguiente = '3.°';
        ELSEIF p_grado = '3.°' THEN SET v_siguiente = '4.°';
        ELSEIF p_grado = '4.°' THEN SET v_siguiente = '5.°';
        ELSEIF p_grado = '5.°' THEN SET v_siguiente = 'EGRESADO';
        ELSE SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Grado de Secundaria inválido';
        END IF;
    ELSE
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Nivel inválido: use Inicial, Primaria o Secundaria';
    END IF;

    RETURN v_siguiente;
END//

-- ===========================================================================
-- Mantenimiento de SECRETARIA y CONTACTO_EMERGENCIA
-- ===========================================================================
CREATE PROCEDURE sp_secretaria_insertar(
    IN p_dni              CHAR(8),
    IN p_nombres          VARCHAR(50),
    IN p_apellido_paterno VARCHAR(30),
    IN p_apellido_materno VARCHAR(30)
)
BEGIN
    IF p_dni IS NULL OR p_dni NOT REGEXP '^[0-9]{8}$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El DNI de la secretaria debe tener 8 dígitos';
    END IF;
    IF TRIM(IFNULL(p_nombres, '')) = '' OR TRIM(IFNULL(p_apellido_paterno, '')) = ''
       OR TRIM(IFNULL(p_apellido_materno, '')) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Complete los nombres y apellidos de la secretaria';
    END IF;
    IF EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria ya está registrada';
    END IF;
    INSERT INTO SECRETARIA (DNI, Nombres, ApellidoPaterno, ApellidoMaterno)
    VALUES (p_dni, TRIM(p_nombres), TRIM(p_apellido_paterno), TRIM(p_apellido_materno));
END//

CREATE PROCEDURE sp_secretaria_actualizar(
    IN p_dni              CHAR(8),
    IN p_nombres          VARCHAR(50),
    IN p_apellido_paterno VARCHAR(30),
    IN p_apellido_materno VARCHAR(30)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria no existe';
    END IF;
    IF TRIM(IFNULL(p_nombres, '')) = '' OR TRIM(IFNULL(p_apellido_paterno, '')) = ''
       OR TRIM(IFNULL(p_apellido_materno, '')) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Complete los nombres y apellidos de la secretaria';
    END IF;
    UPDATE SECRETARIA
    SET Nombres = TRIM(p_nombres),
        ApellidoPaterno = TRIM(p_apellido_paterno),
        ApellidoMaterno = TRIM(p_apellido_materno)
    WHERE DNI = p_dni;
END//

CREATE PROCEDURE sp_secretaria_eliminar(IN p_dni CHAR(8))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM MATRICULA WHERE DNI_Secretaria = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria registró matrículas y no se puede eliminar';
    END IF;
    IF EXISTS (SELECT 1 FROM USUARIO WHERE DNI = p_dni) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La secretaria tiene un usuario del sistema y no se puede eliminar';
    END IF;
    DELETE FROM SECRETARIA WHERE DNI = p_dni;
END//

CREATE PROCEDURE sp_contacto_insertar(
    IN p_nombre_contacto_emergencia VARCHAR(110),
    IN p_celular_emergencia         CHAR(9)
)
BEGIN
    IF TRIM(IFNULL(p_nombre_contacto_emergencia, '')) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ingrese el nombre del contacto de emergencia';
    END IF;
    IF p_celular_emergencia IS NULL OR p_celular_emergencia NOT REGEXP '^[0-9]{9}$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El celular de emergencia debe tener 9 dígitos';
    END IF;
    INSERT INTO CONTACTO_EMERGENCIA (NombreContactoEmergencia, CelularEmergencia)
    VALUES (TRIM(p_nombre_contacto_emergencia), p_celular_emergencia);
    SELECT LAST_INSERT_ID() AS id_contacto;
END//

CREATE PROCEDURE sp_contacto_eliminar(IN p_id_contacto INT UNSIGNED)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = p_id_contacto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El contacto de emergencia no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM ESTUDIANTE WHERE IdContactoEmergencia = p_id_contacto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El contacto está asignado a uno o más estudiantes';
    END IF;
    DELETE FROM CONTACTO_EMERGENCIA WHERE IdContactoEmergencia = p_id_contacto;
END//

DELIMITER ;
