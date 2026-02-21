@echo off
echo ================================================
echo   Poster Printer - Instalador y Compilador
echo ================================================
echo.

echo [1/3] Verificando dependencias...
python -c "import tkinterdnd2" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo tkinterdnd2 no encontrado - instalando dependencias...
    call INSTALAR.bat
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
) else (
    echo Dependencias verificadas OK
)

echo.
echo [2/3] Instalando PyInstaller...
pip install pyinstaller

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudo instalar PyInstaller
    pause
    exit /b 1
)

echo.
echo [3/3] Compilando ejecutable...
python build_exe.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudo compilar el ejecutable
    pause
    exit /b 1
)

echo.
echo [4/4] Limpiando archivos temporales...
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
