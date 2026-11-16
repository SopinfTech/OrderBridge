@echo off
setlocal

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

set "SERVICE_NAME=OrderBridge"
set "EMBEDDED_PYTHON=%BASE_DIR%python\python.exe"
set "PYTHON_SERVICE_SRC=%BASE_DIR%python\Lib\site-packages\win32\pythonservice.exe"
set "PYTHON_SERVICE_DST=%BASE_DIR%python\pythonservice.exe"
set "PYWIN32_SYS32=%BASE_DIR%python\Lib\site-packages\pywin32_system32"

if not exist logs mkdir logs

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Please run install_service.bat as Administrator.
  exit /b 1
)

if not exist "%EMBEDDED_PYTHON%" (
  echo Embedded Python not found at "%EMBEDDED_PYTHON%"
  exit /b 1
)

if not exist "%PYTHON_SERVICE_SRC%" (
  echo pythonservice.exe not found at "%PYTHON_SERVICE_SRC%"
  exit /b 1
)

for /f "usebackq delims=" %%i in (`"%EMBEDDED_PYTHON%" -c "import sys; print(f'pythoncom{sys.version_info.major}{sys.version_info.minor}.dll')"` ) do set "PYTHONCOM_DLL=%%i"
for /f "usebackq delims=" %%i in (`"%EMBEDDED_PYTHON%" -c "import sys; print(f'pywintypes{sys.version_info.major}{sys.version_info.minor}.dll')"` ) do set "PYWINTYPES_DLL=%%i"

copy /Y "%PYTHON_SERVICE_SRC%" "%PYTHON_SERVICE_DST%" >nul
copy /Y "%PYWIN32_SYS32%\%PYTHONCOM_DLL%" "%BASE_DIR%python\%PYTHONCOM_DLL%" >nul
copy /Y "%PYWIN32_SYS32%\%PYWINTYPES_DLL%" "%BASE_DIR%python\%PYWINTYPES_DLL%" >nul

sc.exe query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel%==0 (
  sc.exe stop "%SERVICE_NAME%" >nul 2>&1
  timeout /t 2 /nobreak >nul
  sc.exe delete "%SERVICE_NAME%" >nul 2>&1
  timeout /t 2 /nobreak >nul
)

"%EMBEDDED_PYTHON%" windows_service.py --startup=auto install
if errorlevel 1 exit /b %errorlevel%

sc.exe description "%SERVICE_NAME%" "Local Windows service for the embedded OrderBridge Python app." >nul
sc.exe failure "%SERVICE_NAME%" reset= 86400 actions= restart/5000/restart/5000/restart/5000 >nul
sc.exe failureflag "%SERVICE_NAME%" 1 >nul
sc.exe start "%SERVICE_NAME%"
