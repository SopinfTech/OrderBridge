@echo off
cd /d "%~dp0"

if not exist logs mkdir logs

echo =============================== >> logs\embedded_service.log
echo Iniciando OrderBridge %date% %time% >> logs\embedded_service.log

.\python\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> logs\embedded_service.log 2>&1