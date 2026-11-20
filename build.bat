@echo off
:: Genera el .exe con PyInstaller (Windows).
:: Ejecutar en Windows con Python instalado y dependencias de requirements.txt.
pyinstaller --noconfirm --onedir --windowed --name MatriculaApp --add-data "sql;sql" --hidden-import mysql.connector.plugins.caching_sha2_password --hidden-import mysql.connector.plugins.mysql_native_password --hidden-import mysql.connector.locales.eng main.py
echo Listo: dist\MatriculaApp\MatriculaApp.exe
