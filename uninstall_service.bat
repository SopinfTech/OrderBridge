@echo off
setlocal

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

set "SERVICE_NAME=OrderBridge"
set "EMBEDDED_PYTHON=%BASE_DIR%python\python.exe"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Please run uninstall_service.bat as Administrator.
  exit /b 1
)

sc.exe query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel% neq 0 (
  echo Service "%SERVICE_NAME%" is not installed.
  exit /b 0
)

sc.exe stop "%SERVICE_NAME%" >nul 2>&1
timeout /t 2 /nobreak >nul

if exist "%EMBEDDED_PYTHON%" (
  "%EMBEDDED_PYTHON%" windows_service.py remove >nul 2>&1
)

sc.exe delete "%SERVICE_NAME%" >nul 2>&1
echo Service "%SERVICE_NAME%" removed.
