@echo off
title SCRCPY WEB - CREAR .EXE
color 0A

echo ============================================================
echo   SCRCPY WEB - CREAR .EXE
echo ============================================================
echo.

cd /d "C:\Users\chuva\OneDrive\Desktop\scrpywebexe"

echo [1/3] Construyendo Frontend...
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
echo [2/3] Verificando scrcpy...
if exist "tools\scrcpy\scrcpy.exe" (
    echo ✅ scrcpy encontrado
) else (
    echo ⚠️ scrcpy no encontrado. Copiando...
    mkdir tools\scrcpy 2>nul
    xcopy "C:\Users\chuva\Downloads\scrcpy-win64-v4.0\*" "tools\scrcpy\" /E /I /Y
)

echo.
echo [3/3] Creando .exe...
cd backend
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

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
    echo ERROR: Fallo la creacion
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
    start dist\SCRCPY-Web.exe
) else (
    echo ERROR: No se encontro el ejecutable
)

pause