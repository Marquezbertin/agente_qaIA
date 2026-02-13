@echo off
title QA Agent - Iniciando...
color 0A

echo.
echo  ====================================
echo       QA Agent - Assistente de QA
echo  ====================================
echo.
echo  Iniciando servidor...
echo.

cd /d "%~dp0"

:: Aguardar 2 segundos e abrir navegador
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

:: Iniciar Streamlit
streamlit run app.py --server.headless true

pause
