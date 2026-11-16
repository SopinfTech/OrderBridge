@echo off
setlocal
call "%~dp0stop_service.bat"
timeout /t 2 /nobreak >nul
call "%~dp0start_service.bat"
