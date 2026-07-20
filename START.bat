@echo off
chcp 65001 > nul
cls
echo ╔════════════════════════════════════════════════════╗
echo ║  📅 PLANIFICADOR DE VISITAS - IPP                 ║
echo ║                                                    ║
echo ║  Selecciona una opción:                           ║
echo ╚════════════════════════════════════════════════════╝
echo.
echo  [1] Iniciar Interfaz Web (Recomendado)
echo  [2] Generar Plan Excel de Julio
echo  [3] Análisis de Datos
echo  [4] Abrir carpeta de proyecto
echo  [5] Salir
echo.
set /p choice="Ingresa tu opción (1-5): "

if "%choice%"=="1" (
    echo.
    echo Iniciando servidor web...
    py server.py
) else if "%choice%"=="2" (
    echo.
    echo Generando plan de Julio...
    py generar_plan.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo Analizando datos...
    py analyze_data.py
    pause
) else if "%choice%"=="4" (
    start explorer .
    exit /b 0
) else if "%choice%"=="5" (
    echo Hasta luego!
    exit /b 0
) else (
    echo Opción inválida
    pause
    goto :eof
)
