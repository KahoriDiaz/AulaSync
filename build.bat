@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === AulaSync - generando AulaSync.exe ===

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo Falta PyInstaller. Instale las dependencias primero:
    echo   pip install -r requirements.txt
    exit /b 1
)

if exist "dist\AulaSync" rmdir /s /q "dist\AulaSync"
if exist "build\AulaSync" rmdir /s /q "build\AulaSync"
if exist "AulaSync.spec" del /q "AulaSync.spec"

set "OPTS=--noconfirm --onedir --windowed --name AulaSync --add-data "sql;sql" --collect-submodules mysql.connector --hidden-import mysql.connector.plugins.caching_sha2_password --hidden-import mysql.connector.plugins.mysql_native_password --hidden-import mysql.connector.locales.eng"

set "TESS="
if exist "tesseract\tessdata\spa.traineddata" set TESS=--add-data "tesseract;tesseract"

python -m PyInstaller %OPTS% %TESS% main.py
if errorlevel 1 (
    echo Error al generar el ejecutable.
    exit /b 1
)

:: Archivos configurables: FUERA del ejecutable (config.ini se crea con el asistente).
copy /y "config.ini.example" "dist\AulaSync\config.ini.example" >nul
copy /y "LEEME.txt" "dist\AulaSync\LEEME.txt" >nul

echo.
echo Listo: dist\AulaSync\AulaSync.exe
echo Ahora ejecute empaquetar.bat para generar el ZIP de entrega.
endlocal
