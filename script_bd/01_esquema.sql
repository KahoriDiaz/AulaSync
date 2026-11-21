-- ============================================================
-- Script 01: Creacion de la base de datos bd_matricula
-- 12 tablas del modelo fisico (Entrega 4) + indices secundarios
-- Triggers trg_hermandad_bi / trg_hermandad_bu (ya incluidos)
-- Motor: MySQL 8.0 (InnoDB)
-- ============================================================

CREATE DATABASE IF NOT EXISTS bd_matricula
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE bd_matricula;

-- Tabla CONTACTO_EMERGENCIA (se crea primero por ser referenciada)
CREATE TABLE CONTACTO_EMERGENCIA (
    IdContactoEmergencia INT UNSIGNED NOT NULL AUTO_INCREMENT,
    NombreContactoEmergencia VARCHAR(110) NOT NULL,
    CelularEmergencia CHAR(9) NOT NULL,
    CONSTRAINT PK_ContactoEmergencia PRIMARY KEY (IdContactoEmergencia),
    CONSTRAINT CK_CelularEmergencia CHECK (CelularEmergencia REGEXP '^[0-9]{9}$')
) ENGINE=InnoDB;

-- Tabla INSTITUCION_EDUCATIVA
CREATE TABLE INSTITUCION_EDUCATIVA (
    CodigoModularIE VARCHAR(10) NOT NULL,
    NombreIE VARCHAR(50) NULL,
    TipoIE VARCHAR(20) NULL,
    CONSTRAINT PK_InstitucionEducativa PRIMARY KEY (CodigoModularIE),
    CONSTRAINT CK_TipoIE CHECK (TipoIE IN ('Estatal', 'Particular'))
) ENGINE=InnoDB;

-- Tabla PADRE_APODERADO
CREATE TABLE PADRE_APODERADO (
    DNI CHAR(8) NOT NULL,
    Sexo CHAR(1) NOT NULL,
    Nombres VARCHAR(50) NOT NULL,
    ApellidoPaterno VARCHAR(30) NOT NULL,
    ApellidoMaterno VARCHAR(30) NOT NULL,
    FechaNacimiento DATE NOT NULL,
    OcupacionActual VARCHAR(50) NULL,
    GradoInstruccion VARCHAR(30) NOT NULL,
    DomicilioActual VARCHAR(100) NOT NULL,
    DistritoDomicilio VARCHAR(30) NOT NULL,
    TelefonoFijo CHAR(9) NULL,
    Celular CHAR(9) NOT NULL,
    CorreoElectronico VARCHAR(50) NULL,
    CONSTRAINT PK_PadreApoderado PRIMARY KEY (DNI),
    CONSTRAINT CK_SexoPA CHECK (Sexo IN ('M', 'F')),
    CONSTRAINT CK_GradoInstruccion CHECK (GradoInstruccion IN ('Primaria', 'Secundaria', 'Superior', 'Otros')),
    CONSTRAINT CK_DNI_PA CHECK (DNI REGEXP '^[0-9]{8}$'),
    CONSTRAINT CK_Celular_PA CHECK (Celular REGEXP '^[0-9]{9}$'),
    CONSTRAINT CK_TelefonoFijo_PA CHECK (TelefonoFijo IS NULL OR TelefonoFijo REGEXP '^[0-9]{9}$')
) ENGINE=InnoDB;

-- Tabla SECRETARIA
CREATE TABLE SECRETARIA (
    DNI CHAR(8) NOT NULL,
    Nombres VARCHAR(50) NOT NULL,
    ApellidoPaterno VARCHAR(30) NOT NULL,
    ApellidoMaterno VARCHAR(30) NOT NULL,
    CONSTRAINT PK_Secretaria PRIMARY KEY (DNI),
    CONSTRAINT CK_DNI_S CHECK (DNI REGEXP '^[0-9]{8}$')
) ENGINE=InnoDB;

-- Tabla ESTUDIANTE
CREATE TABLE ESTUDIANTE (
    DNI CHAR(8) NOT NULL,
    Sexo CHAR(1) NOT NULL,
    Nombres VARCHAR(50) NOT NULL,
    ApellidoPaterno VARCHAR(30) NOT NULL,
    ApellidoMaterno VARCHAR(30) NOT NULL,
    FechaNacimiento DATE NOT NULL,
    DistritoNacimiento VARCHAR(30) NOT NULL,
    ProvinciaNacimiento VARCHAR(30) NOT NULL,
    DepartamentoNacimiento VARCHAR(30) NOT NULL,
    PaisNacimiento VARCHAR(30) NOT NULL,
    DomicilioActual VARCHAR(100) NOT NULL,
    DistritoDomicilio VARCHAR(30) NOT NULL,
    Celular CHAR(9) NULL,
    CorreoElectronico VARCHAR(50) NULL,
    Religion VARCHAR(20) NULL,
    LugarQueOcupa TINYINT UNSIGNED NOT NULL,
    TipoAtencion VARCHAR(20) NULL,
    EnfermedadCronica VARCHAR(50) NULL,
    ViveConPadre BOOLEAN NOT NULL,
    ViveConMadre BOOLEAN NOT NULL,
    ElPadreVive BOOLEAN NOT NULL,
    LaMadreVive BOOLEAN NOT NULL,
    IdContactoEmergencia INT UNSIGNED NOT NULL,
    CodigoModularIE VARCHAR(10) NULL,
    DNI_Apoderado CHAR(8) NULL,
    CONSTRAINT PK_Estudiante PRIMARY KEY (DNI),
    CONSTRAINT FK_Estudiante_Contacto FOREIGN KEY (IdContactoEmergencia)
        REFERENCES CONTACTO_EMERGENCIA(IdContactoEmergencia)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_Estudiante_IE FOREIGN KEY (CodigoModularIE)
        REFERENCES INSTITUCION_EDUCATIVA(CodigoModularIE)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_Estudiante_Apoderado FOREIGN KEY (DNI_Apoderado)
        REFERENCES PADRE_APODERADO(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT CK_Sexo_E CHECK (Sexo IN ('M', 'F')),
    CONSTRAINT CK_TipoAtencion CHECK (TipoAtencion IN ('ESSALUD', 'SIS', 'Otros')),
    CONSTRAINT CK_Celular_E CHECK (Celular IS NULL OR Celular REGEXP '^[0-9]{9}$')
) ENGINE=InnoDB;

-- Tabla CONSTANCIA_LOGROS
CREATE TABLE CONSTANCIA_LOGROS (
    CodigoVirtual CHAR(8) NOT NULL,
    DNI_Estudiante CHAR(8) NOT NULL,
    NivelEducativo VARCHAR(10) NOT NULL,
    FechaHoraEmision DATETIME NULL,
    CONSTRAINT PK_ConstanciaLogros PRIMARY KEY (CodigoVirtual),
    CONSTRAINT FK_Constancia_Estudiante FOREIGN KEY (DNI_Estudiante)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT CK_NivelEducativo CHECK (NivelEducativo IN ('Inicial', 'Primaria', 'Secundaria'))
) ENGINE=InnoDB;

-- Tabla MATRICULA
CREATE TABLE MATRICULA (
    DNI_Estudiante CHAR(8) NOT NULL,
    `AñoEscolar` YEAR NOT NULL,
    Nivel VARCHAR(10) NOT NULL,
    Grado VARCHAR(5) NOT NULL,
    Seccion VARCHAR(5) NOT NULL,
    Estado VARCHAR(15) NOT NULL DEFAULT 'Matriculado',
    LugarSuscripcion VARCHAR(30) NOT NULL,
    FechaSuscripcion DATE NOT NULL,
    DNI_Responsable CHAR(8) NOT NULL,
    DNI_Secretaria CHAR(8) NOT NULL,
    CONSTRAINT PK_Matricula PRIMARY KEY (DNI_Estudiante, `AñoEscolar`),
    CONSTRAINT FK_Matricula_Estudiante FOREIGN KEY (DNI_Estudiante)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_Matricula_Responsable FOREIGN KEY (DNI_Responsable)
        REFERENCES PADRE_APODERADO(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_Matricula_Secretaria FOREIGN KEY (DNI_Secretaria)
        REFERENCES SECRETARIA(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT CK_Nivel_M CHECK (Nivel IN ('Inicial', 'Primaria', 'Secundaria')),
    CONSTRAINT CK_Estado CHECK (Estado IN ('Matriculado', 'Retirado', 'Trasladado'))
) ENGINE=InnoDB;

-- Tabla TIENE_PADRES
CREATE TABLE TIENE_PADRES (
    DNI_Estudiante CHAR(8) NOT NULL,
    DNI_Padre CHAR(8) NOT NULL,
    CONSTRAINT PK_TienePadres PRIMARY KEY (DNI_Estudiante, DNI_Padre),
    CONSTRAINT FK_TienePadres_Estudiante FOREIGN KEY (DNI_Estudiante)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT FK_TienePadres_Padre FOREIGN KEY (DNI_Padre)
        REFERENCES PADRE_APODERADO(DNI)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Tabla HERMANDAD
CREATE TABLE HERMANDAD (
    DNI_HermanoA CHAR(8) NOT NULL,
    DNI_HermanoB CHAR(8) NOT NULL,
    CONSTRAINT PK_Hermandad PRIMARY KEY (DNI_HermanoA, DNI_HermanoB),
    CONSTRAINT FK_Hermandad_A FOREIGN KEY (DNI_HermanoA)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT FK_Hermandad_B FOREIGN KEY (DNI_HermanoB)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Tabla ESTUDIANTE_NEE
CREATE TABLE ESTUDIANTE_NEE (
    DNI_Estudiante CHAR(8) NOT NULL,
    NecesidadEducativaEspecial VARCHAR(50) NOT NULL,
    CONSTRAINT PK_EstudianteNEE PRIMARY KEY (DNI_Estudiante, NecesidadEducativaEspecial),
    CONSTRAINT FK_EstudianteNEE_Estudiante FOREIGN KEY (DNI_Estudiante)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Tabla ESTUDIANTE_HERMANOS_IE
CREATE TABLE ESTUDIANTE_HERMANOS_IE (
    DNI_Estudiante CHAR(8) NOT NULL,
    NivelHermano VARCHAR(30) NOT NULL,
    CONSTRAINT PK_EstudianteHermanosIE PRIMARY KEY (DNI_Estudiante, NivelHermano),
    CONSTRAINT FK_EstudianteHermanosIE_Estudiante FOREIGN KEY (DNI_Estudiante)
        REFERENCES ESTUDIANTE(DNI)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT CK_NivelHermano CHECK (NivelHermano IN ('Inicial', 'Primaria', 'Secundaria'))
) ENGINE=InnoDB;

-- Tabla LOGRO
CREATE TABLE LOGRO (
    CodigoVirtual CHAR(8) NOT NULL,
    `AñoEscolar` YEAR NOT NULL,
    GradoCursado VARCHAR(5) NOT NULL,
    CodigoModularIE VARCHAR(10) NOT NULL,
    SituacionFinal VARCHAR(30) NOT NULL,
    CONSTRAINT PK_Logro PRIMARY KEY (CodigoVirtual, `AñoEscolar`),
    CONSTRAINT FK_Logro_Constancia FOREIGN KEY (CodigoVirtual)
        REFERENCES CONSTANCIA_LOGROS(CodigoVirtual)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT FK_Logro_IE FOREIGN KEY (CodigoModularIE)
        REFERENCES INSTITUCION_EDUCATIVA(CodigoModularIE)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT CK_SituacionFinal CHECK (SituacionFinal IN ('APROBADO', 'REQUIERE RECUPERACIoN'))
) ENGINE=InnoDB;

-- indices secundarios
CREATE INDEX idx_estudiante_apellidos ON ESTUDIANTE(ApellidoPaterno, ApellidoMaterno, Nombres);
CREATE INDEX idx_estudiante_contacto ON ESTUDIANTE(IdContactoEmergencia);
CREATE INDEX idx_estudiante_ie ON ESTUDIANTE(CodigoModularIE);
CREATE INDEX idx_estudiante_apoderado ON ESTUDIANTE(DNI_Apoderado);
CREATE INDEX idx_matricula_periodo ON MATRICULA(`AñoEscolar`, Nivel, Grado, Seccion);
CREATE INDEX idx_matricula_responsable ON MATRICULA(DNI_Responsable);
CREATE INDEX idx_matricula_secretaria ON MATRICULA(DNI_Secretaria);
CREATE INDEX idx_constancia_estudiante ON CONSTANCIA_LOGROS(DNI_Estudiante, NivelEducativo);
CREATE INDEX idx_tienepadres_padre ON TIENE_PADRES(DNI_Padre);
CREATE INDEX idx_hermandad_hermanob ON HERMANDAD(DNI_HermanoB);
CREATE INDEX idx_logro_ie ON LOGRO(CodigoModularIE);
