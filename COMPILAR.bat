@echo off
echo ================================================
echo   Poster Printer - Instalador y Compilador
echo ================================================
echo.

echo [1/3] Instalando dependencias...
pip install -r requirements.txt
pip install pyinstaller

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias
    echo Asegurate de tener Python instalado y agregado al PATH
    pause
    exit /b 1
)

echo.
echo [2/3] Compilando ejecutable...
python build_exe.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudo compilar el ejecutable
    pause
    exit /b 1
)

echo.
echo [3/3] Limpiando archivos temporales...
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist PosterPrinter.spec del /q PosterPrinter.spec

echo.
echo ================================================
echo   COMPILACION EXITOSA
echo ================================================
echo.
echo El ejecutable esta en: dist\PosterPrinter.exe
echo.
echo Puedes copiar ese archivo a cualquier PC con Windows
echo y ejecutarlo sin necesidad de instalar Python.
echo.
pause
