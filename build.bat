@echo off
title SCRCPY WEB - CREAR .EXE CON SCRCPY
color 0A

echo ============================================================
echo   SCRCPY WEB - CREAR .EXE CON SCRCPY
echo ============================================================
echo.

cd /d "C:\Users\chuva\OneDrive\Desktop\scrpywebexe"

echo [1/5] Instalando PyInstaller...
pip install pyinstaller

echo.
echo [2/5] Construyendo Frontend...
cd frontend
if not exist "node_modules" (
    echo Instalando dependencias...
    call npm install --legacy-peer-deps
)
call npm run build
if errorlevel 1 (
    echo ERROR: Fallo la construccion del frontend
    pause
    exit /b
)
cd ..
echo ✅ Frontend construido

echo.
echo [3/5] Verificando scrcpy...
if exist "tools\scrcpy\scrcpy.exe" (
    echo ✅ scrcpy encontrado en tools\scrcpy
) else (
    echo ⚠️ scrcpy no encontrado. Descargando...
    mkdir tools\scrcpy 2>nul
    cd tools\scrcpy
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip' -OutFile 'scrcpy.zip'"
    powershell -Command "Expand-Archive scrcpy.zip -DestinationPath ."
    move scrcpy-win64-v2.4\* . 2>nul
    rmdir scrcpy-win64-v2.4 2>nul
    del scrcpy.zip 2>nul
    cd ..
    echo ✅ scrcpy descargado
)

echo.
echo [4/5] Limpiando builds anteriores...
cd backend
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
echo ✅ Limpieza completada

echo.
echo [5/5] Creando .exe con icono y scrcpy incluido...
echo.

:: Verificar que existe el icono
if exist "logo.ico" (
    echo ✅ Icono encontrado: logo.ico
    set ICON_OPTS=--icon logo.ico
) else (
    echo ⚠️ No se encontro logo.ico. Usando icono por defecto.
    set ICON_OPTS=
)

pyinstaller --onefile ^
    %ICON_OPTS% ^
    --add-data "..\frontend\build;frontend\build" ^
    --add-data "..\frontend\build\index.html;." ^
    --add-data "..\tools\scrcpy\*;tools\scrcpy" ^
    --add-binary "..\tools\scrcpy\scrcpy.exe;." ^
    --add-binary "..\tools\scrcpy\adb.exe;." ^
    --name "SCRCPY-Web" ^
    --clean ^
    --noconsole ^
    --hidden-import flask ^
    --hidden-import flask_cors ^
    --hidden-import json ^
    --hidden-import re ^
    --hidden-import subprocess ^
    --hidden-import os ^
    --hidden-import sys ^
    --hidden-import threading ^
    --hidden-import webbrowser ^
    --hidden-import time ^
    --hidden-import psutil ^
    --hidden-import signal ^
    --hidden-import atexit ^
    app.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   ERROR: Fallo la creacion del .exe
    echo ============================================================
    pause
    exit /b
)

echo.
if exist "dist\SCRCPY-Web.exe" (
    echo ============================================================
    echo   ✅ .EXE CREADO CON EXITO
    echo ============================================================
    echo.
    echo Ubicacion: %cd%\dist\SCRCPY-Web.exe
    echo.
    for %%A in ("dist\SCRCPY-Web.exe") do (
        set /a TAMANO=%%~zA/1024
        echo Tamaño: !TAMANO! KB
    )
    echo.
    echo ¿Quieres ejecutarlo ahora?
    set /p EJECUTAR="Ejecutar? (S/N): "
    if /i "!EJECUTAR!"=="S" (
        start dist\SCRCPY-Web.exe
    )
) else (
    echo ERROR: No se encontro el ejecutable
)

pause