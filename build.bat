@echo off
title SCRCPY WEB - CREAR .EXE (VERSION FINAL)
color 0A

echo ============================================================
echo   SCRCPY WEB - CREAR .EXE (VERSION FINAL)
echo ============================================================
echo.

cd /d "C:\Users\chuva\OneDrive\Desktop\scrpywebexe"

echo [1/4] Construyendo Frontend...
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
echo [2/4] Verificando scrcpy...
if exist "tools\scrcpy\scrcpy.exe" (
    echo ✅ scrcpy encontrado
) else (
    echo ⚠️ scrcpy no encontrado. Copiando...
    mkdir tools\scrcpy 2>nul
    xcopy "C:\Users\chuva\Downloads\scrcpy-win64-v4.0\*" "tools\scrcpy\" /E /I /Y
)

echo.
echo [3/4] Limpiando builds anteriores...
cd backend
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
echo ✅ Limpieza completada

echo.
echo [4/4] Creando .exe (con frontend empaquetado)...
echo.

pyinstaller --onefile ^
    --icon "logo.ico" ^
    --add-data "..\frontend\build;frontend\build" ^
    --add-data "..\frontend\build\index.html;." ^
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
    echo   ✅ .EXE CREADO
    echo ============================================================
    echo.
    echo Ubicacion: %cd%\dist\SCRCPY-Web.exe
    echo.
    echo ============================================================
    echo   PARA DISTRIBUIR:
    echo ============================================================
    echo.
    echo 1. Copia SCRCPY-Web.exe a una carpeta
    echo 2. Copia la carpeta tools\scrcpy\ junto al .exe
    echo.
    echo 🚀 El .exe funciona en CUALQUIER PC
    echo    (usa rutas dinámicas, no rutas fijas)
    echo.
    start dist\SCRCPY-Web.exe
) else (
    echo ERROR: No se encontro el ejecutable
)

pause