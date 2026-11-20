USE bd_matricula;

-- ============================================================
-- Tabla de soporte USUARIO (inicio de sesión del aplicativo)
-- Roles: Padre (padre/madre/apoderado que solicita la matrícula),
--        Secretaria (valida solicitudes) y Administrador.
-- No pertenece a las 12 tablas del modelo de la funcionalidad.
-- ============================================================
CREATE TABLE USUARIO (
    IdUsuario INT UNSIGNED NOT NULL AUTO_INCREMENT,
    NombreUsuario VARCHAR(30) NOT NULL,
    ClaveHash VARCHAR(255) NOT NULL,
    Rol VARCHAR(15) NOT NULL DEFAULT 'Padre',
    Estado VARCHAR(10) NOT NULL DEFAULT 'Activo',
    DNI CHAR(8) NOT NULL,
    Nombres VARCHAR(50) NOT NULL,
    Apellidos VARCHAR(60) NOT NULL,
    FechaRegistro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UltimoAcceso DATETIME NULL,
    CONSTRAINT PK_Usuario PRIMARY KEY (IdUsuario),
    CONSTRAINT UQ_Usuario_Nombre UNIQUE (NombreUsuario),
    CONSTRAINT UQ_Usuario_DNI UNIQUE (DNI),
    CONSTRAINT CK_Usuario_DNI CHECK (DNI REGEXP '^[0-9]{8}$'),
    CONSTRAINT CK_Usuario_Rol CHECK (Rol IN ('Padre', 'Secretaria', 'Administrador')),
    CONSTRAINT CK_Usuario_Estado CHECK (Estado IN ('Activo', 'Inactivo'))
) ENGINE=InnoDB;

-- Una cuenta de Secretaria solo puede existir si su DNI está en SECRETARIA
DELIMITER //
CREATE TRIGGER trg_usuario_bi BEFORE INSERT ON USUARIO
FOR EACH ROW
BEGIN
    IF NEW.Rol = 'Secretaria' AND NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = NEW.DNI) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El DNI de una cuenta Secretaria debe estar registrado en SECRETARIA';
    END IF;
END//

CREATE TRIGGER trg_usuario_bu BEFORE UPDATE ON USUARIO
FOR EACH ROW
BEGIN
    IF NEW.Rol = 'Secretaria' AND NOT EXISTS (SELECT 1 FROM SECRETARIA WHERE DNI = NEW.DNI) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El DNI de una cuenta Secretaria debe estar registrado en SECRETARIA';
    END IF;
END//
DELIMITER ;
