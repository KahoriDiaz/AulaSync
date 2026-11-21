-- Script 04: Triggers de validación (§3.4)
-- Cada trigger va con DROP TRIGGER IF EXISTS antes de su definición.
-- Nota: las reglas que requieren leer la propia tabla (cupo 30, matrícula
-- duplicada) se validan en los procedimientos almacenados, porque un trigger
-- BEFORE sobre MATRICULA no puede consultar MATRICULA (error 1442 tabla mutante).
USE bd_matricula;
DELIMITER //

-- ---------------------------------------------------------------------------
-- trg_matricula_bi: grado válido para el nivel y sección existente para el nivel
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_matricula_bi//
CREATE TRIGGER trg_matricula_bi
BEFORE INSERT ON MATRICULA
FOR EACH ROW
BEGIN
    DECLARE v_msg VARCHAR(200);

    -- Grado válido según el nivel
    IF NEW.Nivel = 'Inicial' THEN
        IF NEW.Grado NOT IN ('3 a.', '4 a.', '5 a.') THEN
            SET v_msg = CONCAT('Grado ', NEW.Grado, ' no válido para Inicial (use 3 a., 4 a. o 5 a.)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
        IF NEW.Seccion NOT IN ('A', 'B') THEN
            SET v_msg = CONCAT('Sección ', NEW.Seccion, ' no válida para Inicial (use A o B)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    ELSEIF NEW.Nivel = 'Primaria' THEN
        IF NEW.Grado NOT IN ('1.°', '2.°', '3.°', '4.°', '5.°', '6.°') THEN
            SET v_msg = CONCAT('Grado ', NEW.Grado, ' no válido para Primaria (use 1.° a 6.°)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
        IF NEW.Seccion NOT IN ('A', 'B', 'C') THEN
            SET v_msg = CONCAT('Sección ', NEW.Seccion, ' no válida para Primaria (use A, B o C)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    ELSEIF NEW.Nivel = 'Secundaria' THEN
        IF NEW.Grado NOT IN ('1.°', '2.°', '3.°', '4.°', '5.°') THEN
            SET v_msg = CONCAT('Grado ', NEW.Grado, ' no válido para Secundaria (use 1.° a 5.°)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
        IF NEW.Seccion NOT IN ('A', 'B', 'C', 'D') THEN
            SET v_msg = CONCAT('Sección ', NEW.Seccion, ' no válida para Secundaria (use A, B, C o D)');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    ELSE
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Nivel no válido: use Inicial, Primaria o Secundaria';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_matricula_bu: Retirado/Trasladado no puede volver a Matriculado
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_matricula_bu//
CREATE TRIGGER trg_matricula_bu
BEFORE UPDATE ON MATRICULA
FOR EACH ROW
BEGIN
    IF OLD.Estado IN ('Retirado', 'Trasladado') AND NEW.Estado = 'Matriculado' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Una matrícula Retirada o Trasladada no puede volver a Matriculado';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_matricula_bd: solo se puede eliminar una matrícula que no esté Matriculado
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_matricula_bd//
CREATE TRIGGER trg_matricula_bd
BEFORE DELETE ON MATRICULA
FOR EACH ROW
BEGIN
    IF OLD.Estado = 'Matriculado' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Primero debe retirar la matrícula antes de eliminarla';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_estudiante_bi / _bu: fecha de nacimiento no futura; DNI distinto del apoderado
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_estudiante_bi//
CREATE TRIGGER trg_estudiante_bi
BEFORE INSERT ON ESTUDIANTE
FOR EACH ROW
BEGIN
    IF NEW.FechaNacimiento > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La fecha de nacimiento no puede ser futura';
    END IF;
    IF NEW.DNI_Apoderado IS NOT NULL AND NEW.DNI_Apoderado = NEW.DNI THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El DNI del estudiante debe ser distinto del de su apoderado';
    END IF;
END//

DROP TRIGGER IF EXISTS trg_estudiante_bu//
CREATE TRIGGER trg_estudiante_bu
BEFORE UPDATE ON ESTUDIANTE
FOR EACH ROW
BEGIN
    IF NEW.FechaNacimiento > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La fecha de nacimiento no puede ser futura';
    END IF;
    IF NEW.DNI_Apoderado IS NOT NULL AND NEW.DNI_Apoderado = NEW.DNI THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El DNI del estudiante debe ser distinto del de su apoderado';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_padre_bi / _bu: el padre/apoderado debe ser mayor de 18 años
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_padre_bi//
CREATE TRIGGER trg_padre_bi
BEFORE INSERT ON PADRE_APODERADO
FOR EACH ROW
BEGIN
    IF TIMESTAMPDIFF(YEAR, NEW.FechaNacimiento, CURDATE()) < 18 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El padre/apoderado debe ser mayor de 18 años';
    END IF;
END//

DROP TRIGGER IF EXISTS trg_padre_bu//
CREATE TRIGGER trg_padre_bu
BEFORE UPDATE ON PADRE_APODERADO
FOR EACH ROW
BEGIN
    IF TIMESTAMPDIFF(YEAR, NEW.FechaNacimiento, CURDATE()) < 18 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El padre/apoderado debe ser mayor de 18 años';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_tiene_padres_bi: máximo 2 padres por estudiante
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_tiene_padres_bi//
CREATE TRIGGER trg_tiene_padres_bi
BEFORE INSERT ON TIENE_PADRES
FOR EACH ROW
BEGIN
    DECLARE v_total INT DEFAULT 0;
    SELECT COUNT(*) INTO v_total FROM TIENE_PADRES WHERE DNI_Estudiante = NEW.DNI_Estudiante;
    IF v_total >= 2 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Máximo 2 padres por estudiante';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_logro_bi: AñoEscolar no mayor al año actual
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_logro_bi//
CREATE TRIGGER trg_logro_bi
BEFORE INSERT ON LOGRO
FOR EACH ROW
BEGIN
    IF NEW.`AñoEscolar` > YEAR(CURDATE()) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El año escolar del logro no puede ser mayor al año actual';
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_usuario_bi: Secretaria → DNI en SECRETARIA; Padre → DNI NO en SECRETARIA
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_usuario_bi//
CREATE TRIGGER trg_usuario_bi
BEFORE INSERT ON USUARIO
FOR EACH ROW
BEGIN
    IF NEW.Rol = 'Secretaria' THEN
        IF NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = NEW.DNI) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El DNI de una cuenta Secretaria debe estar registrado en SECRETARIA';
        END IF;
    END IF;
END//

-- ---------------------------------------------------------------------------
-- trg_hermandad_bi / bu: DNI_HermanoA <> DNI_HermanoB (movidos de 01_esquema.sql)
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_hermandad_bi//
CREATE TRIGGER trg_hermandad_bi
BEFORE INSERT ON HERMANDAD
FOR EACH ROW
BEGIN
    IF NEW.DNI_HermanoA = NEW.DNI_HermanoB THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Un estudiante no puede ser hermano de sí mismo';
    END IF;
END//

DROP TRIGGER IF EXISTS trg_hermandad_bu//
CREATE TRIGGER trg_hermandad_bu
BEFORE UPDATE ON HERMANDAD
FOR EACH ROW
BEGIN
    IF NEW.DNI_HermanoA = NEW.DNI_HermanoB THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Un estudiante no puede ser hermano de sí mismo';
    END IF;
END//

DELIMITER ;
