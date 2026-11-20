-- Script 02: Tabla de soporte USUARIO (inicio de sesión del aplicativo)
-- Solo roles 'Secretaria' y 'Padre'.
-- No hay FK a SECRETARIA: la validación del DNI de la secretaria se hace con trigger.
-- No pertenece a las 12 tablas del modelo de la funcionalidad.
USE bd_matricula;

CREATE TABLE USUARIO (
    IdUsuario     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    NombreUsuario VARCHAR(30)  NOT NULL,
    ClaveHash     VARCHAR(255) NOT NULL,
    Rol           VARCHAR(15)  NOT NULL,
    Estado        VARCHAR(10)  NOT NULL DEFAULT 'Activo',
    DNI           CHAR(8)      NOT NULL,
    UltimoAcceso  DATETIME     NULL,
    CONSTRAINT PK_Usuario PRIMARY KEY (IdUsuario),
    CONSTRAINT UQ_Usuario_Nombre UNIQUE (NombreUsuario),
    CONSTRAINT UQ_Usuario_DNI UNIQUE (DNI),
    CONSTRAINT CK_Usuario_Rol CHECK (Rol IN ('Secretaria','Padre')),
    CONSTRAINT CK_Usuario_Estado CHECK (Estado IN ('Activo','Inactivo')),
    CONSTRAINT CK_Usuario_DNI CHECK (DNI REGEXP '^[0-9]{8}$')
) ENGINE=InnoDB;
