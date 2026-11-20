@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Registro de Matricula - generando MatriculaApp.exe ===

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo Falta PyInstaller. Instale las dependencias primero:
    echo   pip install -r requirements.txt
    exit /b 1
)

if exist "dist\MatriculaApp" rmdir /s /q "dist\MatriculaApp"
if exist "build\MatriculaApp" rmdir /s /q "build\MatriculaApp"
if exist "MatriculaApp.spec" del /q "MatriculaApp.spec"

set "OPTS=--noconfirm --onedir --windowed --name MatriculaApp --add-data "sql;sql" --collect-submodules mysql.connector --hidden-import mysql.connector.plugins.caching_sha2_password --hidden-import mysql.connector.plugins.mysql_native_password --hidden-import mysql.connector.locales.eng"

set "TESS="
if exist "tesseract\tessdata\spa.traineddata" set TESS=--add-data "tesseract;tesseract"

python -m PyInstaller %OPTS% %TESS% main.py
if errorlevel 1 (
    echo Error al generar el ejecutable.
    exit /b 1
)

:: Archivos configurables y bandeja de solicitudes: FUERA del ejecutable.
copy /y "config.ini.example" "dist\MatriculaApp\config.ini.example" >nul
copy /y "LEEME.txt" "dist\MatriculaApp\LEEME.txt" >nul
for %%D in (pendientes aprobadas rechazadas) do (
    if not exist "dist\MatriculaApp\data\solicitudes\%%D" mkdir "dist\MatriculaApp\data\solicitudes\%%D"
)
if not exist "dist\MatriculaApp\data\perfiles" mkdir "dist\MatriculaApp\data\perfiles"

echo.
echo Listo: dist\MatriculaApp\MatriculaApp.exe
echo Ahora ejecute empaquetar.bat para generar el ZIP de entrega.
endlocal
