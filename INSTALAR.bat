@echo off
echo ================================================
echo   Poster Printer - Instalador Rapido
echo ================================================
echo.

echo Instalando dependencias necesarias...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias
    echo Asegurate de tener Python 3.8 o superior instalado
    pause
    exit /b 1
)

echo.
echo ================================================
echo   INSTALACION COMPLETADA
echo ================================================
echo.
echo Para ejecutar el programa usa: EJECUTAR.bat
echo O ejecuta directamente: python poster_printer.py
echo.
pause
