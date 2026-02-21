@echo off
echo Iniciando Poster Printer...
python poster_printer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudo ejecutar el programa
    echo.
    echo Posibles soluciones:
    echo 1. Ejecuta primero INSTALAR.bat para instalar dependencias
    echo 2. Verifica que Python este instalado y en el PATH
    echo.
    pause
)
