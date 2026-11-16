# OrderBridge Python

Consulta la [guía técnica del proyecto](docs/GUIA_DEL_PROYECTO.md) para la arquitectura, el runtime embebido, la configuración, la API y las notas de operación.

Local FastAPI app for syncing GoodBarber orders, storing them in SQLite, generating printable PDFs, and sending them to a Windows printer.

## What lives inside this folder

Everything needed to run the app is kept inside this project folder:

- `python\` embedded Python runtime
- `app\` backend source
- `frontend\` local UI
- `storage\` SQLite database and generated files
- `logs\` runtime and service logs

The goal is that you can copy this folder to another Windows machine, update `.env`, and reinstall the service from this same folder.

## Run manually

For a foreground local run:

```bat
run_embedded.bat
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

## Windows service

The recommended production mode is a local Windows service using the embedded Python runtime.

### Why use the service

- no black console window
- keeps running independently of your user session
- starts automatically with Windows
- restarts automatically if it crashes
- stays self-contained inside this folder

### Files

- `windows_service.py`
- `install_service.bat`
- `uninstall_service.bat`
- `start_service.bat`
- `stop_service.bat`
- `restart_service.bat`
- `service_status.bat`

### Install

Open `PowerShell` or `CMD` as Administrator in this folder and run:

```powershell
.\install_service.bat
```

This script:

1. uses `python\python.exe`
2. copies `pythonservice.exe` into `python\`
3. copies the required `pywin32` helper DLLs into `python\`
4. installs the `OrderBridge` service
5. sets startup to automatic
6. configures restart-on-failure
7. starts the service

### Daily service commands

```powershell
.\service_status.bat
.\start_service.bat
.\stop_service.bat
.\restart_service.bat
```

### Uninstall

```powershell
.\uninstall_service.bat
```

## Move to another machine

To run this on another Windows PC:

1. copy the full folder
2. update `.env` if needed
3. make sure the target printer exists on that machine
4. open an Administrator terminal in the copied folder
5. run:

```powershell
.\install_service.bat
```

Important:

- the Windows service stores the current folder path when installed
- if you move the folder later on the same machine, run:

```powershell
.\uninstall_service.bat
.\install_service.bat
```

That refreshes the service registration to the new path.

## Logs

Runtime logs stay inside `logs\`:

- `logs\orderbridge.log`
- `logs\service-boot.log`
- `logs\service-stdout.log`
- `logs\service-stderr.log`
- `logs\embedded_service.log`

## Main config

Environment settings live in `.env`.

Important values:

- `GOODBARBER_APP_ID`
- `GOODBARBER_API_KEY`
- `API_HOST`
- `API_PORT`
- `GOODBARBER_SYNC_ENABLED`
- `GOODBARBER_SYNC_INTERVAL_SECONDS`
- `PRINTER_NAME`

If `PRINTER_NAME` is empty, the app falls back to:

1. the printer selected in the frontend
2. the printer configured in `.env`
3. the Windows default printer
