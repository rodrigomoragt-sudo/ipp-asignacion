@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

cls
echo ╔════════════════════════════════════════════════════╗
echo ║  📅 PLANIFICADOR DE VISITAS - IPP                 ║
echo ║                                                    ║
echo ║  Instalando dependencias y ejecutando...          ║
echo ╚════════════════════════════════════════════════════╝
echo.

echo [1/3] Verificando Python...
py --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python no está instalado
    echo Descargalo desde https://www.python.org
    pause
    exit /b 1
)
echo OK - Python encontrado

echo.
echo [2/3] Instalando/verificando librerías...
py -m pip install --quiet pandas openpyxl flask >nul 2>&1
if errorlevel 1 (
    echo Intentando con pip...
    pip install --quiet pandas openpyxl flask
)
echo OK - Librerías instaladas

echo.
echo [3/3] Iniciando servidor...
echo.
echo ╔════════════════════════════════════════════════════╗
echo ║  El servidor está iniciando...                     ║
echo ║  URL: http://localhost:5000                        ║
echo ║  Presiona Ctrl+C para detener                      ║
echo ╚════════════════════════════════════════════════════╝
echo.

timeout /t 2 /nobreak

py app.py

pause
