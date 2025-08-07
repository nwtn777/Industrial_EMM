@echo off
title Motion Magnification GUI Launcher
echo ========================================
echo   Motion Magnification GUI Launcher
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python no está instalado o no está en el PATH
    echo Por favor instala Python desde https://python.org
    pause
    exit /b 1
)

echo Python detectado correctamente.
echo.
echo NOTA: La GUI completa requiere pyrtools como dependencia OBLIGATORIA
echo      Si pyrtools no está instalado, usa la opción 1 o 4 para instalarlo
echo.

REM Mostrar opciones al usuario
echo Selecciona una opción:
echo 1. Verificar dependencias y ejecutar launcher
echo 2. Ejecutar GUI completa (requiere pyrtools)
echo 3. Instalar dependencias manualmente
echo 4. Salir
echo.

set /p choice="Ingresa tu opción (1-4): "

if "%choice%"=="1" goto launcher
if "%choice%"=="2" goto fullgui
if "%choice%"=="3" goto install
if "%choice%"=="4" goto exit
goto invalid

:launcher
echo.
echo Ejecutando launcher con verificador de dependencias...
python launcher.py
goto end

:fullgui
echo.
echo Ejecutando GUI completa...
python motion_magnification_gui.py
goto end

:install
echo.
echo Instalando dependencias desde requirements_gui.txt...
python -m pip install -r requirements_gui.txt
echo.
echo Instalación completada. Presiona cualquier tecla para continuar.
pause
goto start

:invalid
echo.
echo Opción inválida. Por favor selecciona una opción del 1 al 5.
echo.
goto start

:exit
echo.
echo Saliendo...
exit /b 0

:end
echo.
echo Aplicación finalizada.
pause

:start
goto :eof
