@echo off
title QA Agent + OpenCode

where opencode >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo OpenCode nao encontrado.
    echo Instale: winget install -e --id SST.OpenCodeDesktop
    pause
    exit /b 1
)

echo Abrindo OpenCode...
start "" opencode
