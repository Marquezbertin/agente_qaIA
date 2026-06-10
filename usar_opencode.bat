@echo off
title QA Agent + OpenCode

echo ============================================
echo  QA Agent + OpenCode - Interface Gratuita
echo ============================================
echo.

:: Verificar se opencode existe
where opencode >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] OpenCode nao encontrado.
    echo.
    echo Para instalar, execute:
    echo    winget install -e --id SST.OpenCodeDesktop
    echo.
    echo Ou baixe manualmente de:
    echo    https://github.com/anomalyco/opencode/releases
    echo.
    pause
    exit /b 1
)

echo [*] Iniciando OpenCode com integracao QA Agent...
echo [*] Pasta do projeto: %CD%
echo.
echo Comandos disponiveis no OpenCode:
echo   "Rode os testes de API"
echo   "Crie um bug: login quebrado"
echo   "Mostre o dashboard de QA"
echo   "Teste o endpoint de posts"
echo.
echo Pressione CTRL+C para sair
echo ============================================
echo.

opencode --model free
