-- Script 05: Datos de prueba (Entrega 4, sin modificar DNIs ni valores)
-- + Usuarios demo (§14.5) con marcadores pbkdf2$200000$5963182383439fb212bce924957084ed$cb007513cbd9e5ceca5db182f36c9b795042211dc2d683ec2e0725570ace6e7a y pbkdf2$200000$b075b6e9c7975305d351c1f50b568591$51cfb9db276a40b6f315763bac6cbca82b61b1557c2c263303af3af30a732ad0
-- que setup_bd.py reemplaza con hashes generados por app/seguridad.py.
USE bd_matricula;

-- Contactos de emergencia
INSERT INTO CONTACTO_EMERGENCIA (IdContactoEmergencia, NombreContactoEmergencia, CelularEmergencia) VALUES
    (1, 'Manuel Vera', '950123490'),
    (2, 'Teresa Mamani Condori', '954778899'),
    (3, 'Hilda Cáceres Rondón', '958334455'),
    (4, 'Marco Salas Pinto', '951667788'),
    (5, 'Elena Choque Mamani', '959223344'),
    (6, 'Rosario Ramos Quispe', '953445566');
-- Instituciones educativas de procedencia
INSERT INTO INSTITUCION_EDUCATIVA (CodigoModularIE, NombreIE, TipoIE) VALUES
    ('0234567', 'Pamer', 'Particular'),
    ('1137421-0', 'I.E. 40174 Paola Frassinetti', 'Estatal'),
    ('0456789', 'I.E. Santa Rosa de Lima', 'Particular'),
    ('0567890', 'I.E. Independencia Americana', 'Estatal');
-- Padres y apoderados
INSERT INTO PADRE_APODERADO (DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento, OcupacionActual, GradoInstruccion, DomicilioActual, DistritoDomicilio, TelefonoFijo, Celular, CorreoElectronico) VALUES
    ('29481029', 'F', 'María Elena', 'Acosta', 'Porras', '1975-08-30', 'Contadora', 'Superior', 'Av. Goyeneche 130', 'Cercado', '054217734', '950123456', 'maria@hotmail.com'),
    ('10334546', 'M', 'Víctor Hugo', 'Diaz', 'Nuñez', '1978-08-30', 'Abogado', 'Superior', 'Urb. Guardia Civil J-9', 'Paucarpata', '054610266', '974650282', 'victor@hotmail.com'),
    ('56345876', 'M', 'Alberto', 'Diaz', 'Acosta', '1985-01-15', 'Comerciante', 'Secundaria', 'Av. Goyeneche 130', 'Cercado', '054345666', '977123456', 'albert@hotmail.com'),
    ('40125874', 'F', 'Rosa Elvira', 'Quispe', 'Mamani', '1984-02-11', 'Docente', 'Superior', 'Calle Mercaderes 215', 'Cercado', '054223344', '954112233', 'rosa.quispe@gmail.com'),
    ('41238796', 'M', 'Jorge Luis', 'Mamani', 'Condori', '1981-07-19', 'Electricista', 'Secundaria', 'Calle Mercaderes 215', 'Cercado', '054223344', '955887766', NULL),
    ('42365871', 'F', 'Carmen Rosa', 'Huamán', 'Flores', '1988-11-03', 'Comerciante', 'Secundaria', 'Av. Jesús 450', 'Paucarpata', NULL, '956221100', 'carmen.huaman@hotmail.com'),
    ('43457812', 'M', 'Luis Alberto', 'Cáceres', 'Rondón', '1986-04-27', 'Ingeniero civil', 'Superior', 'Av. Jesús 450', 'Paucarpata', NULL, '957334455', 'luis.caceres@gmail.com'),
    ('44512369', 'F', 'Lucía Fernanda', 'Salas', 'Pinto', '1990-09-14', 'Enfermera', 'Superior', 'Urb. Cayma Nueva B-12', 'Cayma', '054255667', '958990011', 'lucia.salas@gmail.com'),
    ('45678123', 'M', 'Pedro Pablo', 'Vilca', 'Choque', '1979-12-02', 'Chofer', 'Secundaria', 'Av. Aviación 820', 'Miraflores', NULL, '959112233', NULL),
    ('46789512', 'F', 'Gladys Marisol', 'Valdivia', 'Ramos', '1985-05-23', 'Secretaria', 'Superior', 'Calle Piérola 310', 'Yanahuara', '054228899', '960445566', 'gladys.valdivia@hotmail.com');
-- Secretaria
INSERT INTO SECRETARIA (DNI, Nombres, ApellidoPaterno, ApellidoMaterno) VALUES
    ('87733221', 'Claudia Graciela', 'Acosta', 'Neira');
-- Estudiantes (DNI 56743478 y 74922482 son los DNIs del caso de prueba; los otros 8 son estudiantes adicionales)
INSERT INTO ESTUDIANTE (DNI, Sexo, Nombres, ApellidoPaterno, ApellidoMaterno, FechaNacimiento, DistritoNacimiento, ProvinciaNacimiento, DepartamentoNacimiento, PaisNacimiento, DomicilioActual, DistritoDomicilio, Celular, CorreoElectronico, Religion, LugarQueOcupa, TipoAtencion, EnfermedadCronica, ViveConPadre, ViveConMadre, ElPadreVive, LaMadreVive, IdContactoEmergencia, CodigoModularIE, DNI_Apoderado) VALUES
    ('56743478', 'F', 'Domenica Yuri', 'Diaz', 'Acosta', '2012-05-13', 'Cayma', 'Arequipa', 'Arequipa', 'Perú', 'Av. Independencia 730', 'Paucarpata', '929294782', 'dome@gmail.com', 'Católica', 1, 'SIS', NULL, TRUE, TRUE, TRUE, TRUE, 1, '0234567', '56345876'),
    ('74922482', 'M', 'Franklin Manuel', 'Peña', 'Ancajima', '2010-03-22', 'Cercado', 'Arequipa', 'Arequipa', 'Perú', 'Av. Bolognesi 145', 'Cercado', '912345678', NULL, NULL, 1, 'ESSALUD', NULL, TRUE, FALSE, TRUE, FALSE, 1, '1137421-0', NULL),
    ('78120001', 'M', 'Mateo Andrés', 'Mamani', 'Quispe', '2021-06-08', 'Cercado', 'Arequipa', 'Arequipa', 'Perú', 'Calle Mercaderes 215', 'Cercado', NULL, NULL, 'Católica', 2, 'SIS', NULL, TRUE, TRUE, TRUE, TRUE, 2, NULL, NULL),
    ('78120002', 'F', 'Valentina Sofía', 'Cáceres', 'Huamán', '2020-08-17', 'Paucarpata', 'Arequipa', 'Arequipa', 'Perú', 'Av. Jesús 450', 'Paucarpata', NULL, NULL, 'Católica', 2, 'ESSALUD', NULL, TRUE, TRUE, TRUE, TRUE, 3, NULL, NULL),
    ('78120003', 'F', 'Camila Alejandra', 'Mamani', 'Quispe', '2017-09-25', 'Cercado', 'Arequipa', 'Arequipa', 'Perú', 'Calle Mercaderes 215', 'Cercado', NULL, NULL, 'Católica', 1, 'SIS', NULL, TRUE, TRUE, TRUE, TRUE, 2, '1137421-0', NULL),
    ('78120004', 'M', 'Sebastián Andrés', 'Salas', 'Pinto', '2019-03-12', 'Cayma', 'Arequipa', 'Arequipa', 'Perú', 'Urb. Cayma Nueva B-12', 'Cayma', NULL, NULL, 'Católica', 2, 'SIS', NULL, FALSE, TRUE, TRUE, TRUE, 4, '1137421-0', NULL),
    ('78120005', 'M', 'Joaquín Mauricio', 'Cáceres', 'Huamán', '2012-10-30', 'Paucarpata', 'Arequipa', 'Arequipa', 'Perú', 'Av. Jesús 450', 'Paucarpata', '961223344', 'joaquin.caceres@gmail.com', 'Católica', 1, 'ESSALUD', 'Asma', TRUE, TRUE, TRUE, TRUE, 3, '1137421-0', NULL),
    ('78120006', 'F', 'Luciana Fernanda', 'Salas', 'Pinto', '2013-08-04', 'Cayma', 'Arequipa', 'Arequipa', 'Perú', 'Urb. Cayma Nueva B-12', 'Cayma', '962334455', NULL, 'Católica', 1, 'SIS', NULL, FALSE, TRUE, TRUE, TRUE, 4, '1137421-0', NULL),
    ('78120007', 'M', 'Diego Armando', 'Torres', 'Choque', '2010-05-21', 'Miraflores', 'Arequipa', 'Arequipa', 'Perú', 'Av. Aviación 820', 'Miraflores', '963445566', NULL, 'Católica', 1, 'Otros', NULL, FALSE, FALSE, TRUE, TRUE, 5, '0567890', '45678123'),
    ('78120008', 'F', 'Ximena Alexandra', 'Valdivia', 'Ramos', '2015-12-16', 'Yanahuara', 'Arequipa', 'Arequipa', 'Perú', 'Calle Piérola 310', 'Yanahuara', NULL, NULL, 'Católica', 1, 'SIS', NULL, FALSE, TRUE, TRUE, TRUE, 6, '0456789', NULL);
-- Constancias de logros
INSERT INTO CONSTANCIA_LOGROS (CodigoVirtual, DNI_Estudiante, NivelEducativo, FechaHoraEmision) VALUES
    ('A1F75CFC', '74922482', 'Secundaria', '2024-03-01 19:26:24'),
    ('B2C94D1E', '78120008', 'Primaria', '2026-02-18 09:40:12'),
    ('C3D05E2F', '78120007', 'Secundaria', '2026-02-20 10:15:37');
-- Logros (grados cursados por el estudiante)
INSERT INTO LOGRO (CodigoVirtual, `AñoEscolar`, GradoCursado, CodigoModularIE, SituacionFinal) VALUES
    ('A1F75CFC', 2017, '1.°', '1137421-0', 'APROBADO'),
    ('B2C94D1E', 2022, '1.°', '0456789', 'APROBADO'),
    ('B2C94D1E', 2023, '2.°', '0456789', 'APROBADO'),
    ('B2C94D1E', 2024, '3.°', '0456789', 'REQUIERE RECUPERACIÓN'),
    ('B2C94D1E', 2025, '4.°', '0456789', 'APROBADO'),
    ('C3D05E2F', 2023, '1.°', '0567890', 'APROBADO'),
    ('C3D05E2F', 2024, '2.°', '0567890', 'APROBADO'),
    ('C3D05E2F', 2025, '3.°', '0567890', 'APROBADO');
-- Matrículas (año 2026 y matrículas previas de 2025 de estudiantes que continúan)
INSERT INTO MATRICULA (DNI_Estudiante, `AñoEscolar`, Nivel, Grado, Seccion, Estado, LugarSuscripcion, FechaSuscripcion, DNI_Responsable, DNI_Secretaria) VALUES
    ('56743478', 2026, 'Secundaria', '3.°', 'B', 'Matriculado', 'Paucarpata', '2026-03-12', '29481029', '87733221'),
    ('78120001', 2026, 'Inicial', '4 a.', 'A', 'Matriculado', 'Cercado', '2026-03-02', '40125874', '87733221'),
    ('78120002', 2026, 'Inicial', '5 a.', 'A', 'Matriculado', 'Paucarpata', '2026-03-03', '42365871', '87733221'),
    ('78120003', 2026, 'Primaria', '3.°', 'B', 'Matriculado', 'Cercado', '2026-03-02', '40125874', '87733221'),
    ('78120004', 2026, 'Primaria', '2.°', 'A', 'Matriculado', 'Cayma', '2026-03-04', '44512369', '87733221'),
    ('78120005', 2026, 'Secundaria', '2.°', 'C', 'Matriculado', 'Paucarpata', '2026-03-03', '42365871', '87733221'),
    ('78120006', 2026, 'Secundaria', '1.°', 'A', 'Matriculado', 'Cayma', '2026-03-04', '44512369', '87733221'),
    ('78120007', 2026, 'Secundaria', '4.°', 'D', 'Matriculado', 'Miraflores', '2026-03-09', '45678123', '87733221'),
    ('78120008', 2026, 'Primaria', '5.°', 'B', 'Matriculado', 'Yanahuara', '2026-03-10', '46789512', '87733221'),
    ('78120003', 2025, 'Primaria', '2.°', 'B', 'Matriculado', 'Cercado', '2025-03-03', '40125874', '87733221'),
    ('78120004', 2025, 'Primaria', '1.°', 'A', 'Matriculado', 'Cayma', '2025-03-04', '44512369', '87733221'),
    ('78120005', 2025, 'Secundaria', '1.°', 'C', 'Matriculado', 'Paucarpata', '2025-03-03', '42365871', '87733221'),
    ('78120006', 2025, 'Primaria', '6.°', 'A', 'Matriculado', 'Cayma', '2025-03-04', '44512369', '87733221');
-- TIENE_PADRES
INSERT INTO TIENE_PADRES (DNI_Estudiante, DNI_Padre) VALUES
    ('56743478', '29481029'),
    ('56743478', '10334546'),
    ('78120001', '40125874'),
    ('78120001', '41238796'),
    ('78120002', '42365871'),
    ('78120002', '43457812'),
    ('78120003', '40125874'),
    ('78120003', '41238796'),
    ('78120004', '44512369'),
    ('78120005', '42365871'),
    ('78120005', '43457812'),
    ('78120006', '44512369'),
    ('78120008', '46789512');
-- HERMANDAD (sin duplicados gracias a los triggers)
INSERT INTO HERMANDAD (DNI_HermanoA, DNI_HermanoB) VALUES
    ('56743478', '74922482'),
    ('78120001', '78120003'),
    ('78120002', '78120005'),
    ('78120004', '78120006');
-- ESTUDIANTE_NEE
INSERT INTO ESTUDIANTE_NEE (DNI_Estudiante, NecesidadEducativaEspecial) VALUES
    ('56743478', 'Ninguna'),
    ('78120001', 'Ninguna'),
    ('78120002', 'Ninguna'),
    ('78120003', 'Ninguna'),
    ('78120004', 'Trastorno del lenguaje'),
    ('78120005', 'Ninguna'),
    ('78120006', 'Ninguna'),
    ('78120007', 'Ninguna'),
    ('78120008', 'Ninguna');
-- ESTUDIANTE_HERMANOS_IE (nivel en el que estudian los hermanos dentro de la I.E.)
INSERT INTO ESTUDIANTE_HERMANOS_IE (DNI_Estudiante, NivelHermano) VALUES
    ('56743478', 'Primaria'),
    ('78120001', 'Primaria'),
    ('78120002', 'Secundaria'),
    ('78120003', 'Inicial'),
    ('78120004', 'Secundaria'),
    ('78120005', 'Inicial'),
    ('78120006', 'Primaria');

-- Usuarios demo (§14.5): setup_bd.py reemplaza pbkdf2$200000$5963182383439fb212bce924957084ed$cb007513cbd9e5ceca5db182f36c9b795042211dc2d683ec2e0725570ace6e7a y pbkdf2$200000$b075b6e9c7975305d351c1f50b568591$51cfb9db276a40b6f315763bac6cbca82b61b1557c2c263303af3af30a732ad0
INSERT INTO USUARIO (NombreUsuario, ClaveHash, Rol, Estado, DNI, UltimoAcceso) VALUES
    ('secretaria', 'pbkdf2$200000$5963182383439fb212bce924957084ed$cb007513cbd9e5ceca5db182f36c9b795042211dc2d683ec2e0725570ace6e7a', 'Secretaria', 'Activo', '87733221', NULL),
    ('padre_demo', 'pbkdf2$200000$b075b6e9c7975305d351c1f50b568591$51cfb9db276a40b6f315763bac6cbca82b61b1557c2c263303af3af30a732ad0', 'Padre', 'Activo', '29481029', NULL);
