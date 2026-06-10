@echo off
title QA Agent + OpenCode
set PORT=3000

echo ============================================
echo  QA Agent + OpenCode - Interface Gratuita
echo ============================================
echo.

where opencode >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] OpenCode nao encontrado.
    echo    Para instalar: winget install -e --id SST.OpenCodeDesktop
    pause
    exit /b 1
)

echo Iniciando servidor...
echo.
echo URL: http://localhost:%PORT%
echo.
start http://localhost:%PORT%
opencode web --port %PORT%
pause
