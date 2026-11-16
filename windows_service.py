from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
BOOT_LOG = LOG_DIR / "service-boot.log"
SERVICE_NAME = "OrderBridge"
SERVICE_DISPLAY_NAME = "OrderBridge Local Service"
SERVICE_DESCRIPTION = "Local Windows service for the embedded OrderBridge Python app."
PYTHON_EXE = BASE_DIR / "python" / "python.exe"


def boot_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with BOOT_LOG.open("a", encoding="utf-8") as file:
        file.write(f"{timestamp} | {message}\n")


def ensure_project_on_path() -> None:
    project_path = str(BASE_DIR)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)


def get_settings():
    ensure_project_on_path()
    from app.config import settings

    return settings


def build_server_command() -> list[str]:
    settings = get_settings()
    return [
        str(PYTHON_EXE),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        settings.api_host,
        "--port",
        str(settings.api_port),
    ]


def build_server_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["ORDERBRIDGE_SERVICE"] = "1"
    python_path = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = str(BASE_DIR) if not python_path else f"{BASE_DIR};{python_path}"
    return env


class OrderBridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    _exe_name_ = str(BASE_DIR / "python" / "pythonservice.exe")

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server_process: subprocess.Popen | None = None
        self.stdout_file = None
        self.stderr_file = None

    def SvcStop(self):
        boot_log("SvcStop called")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        servicemanager.LogInfoMsg(f"{SERVICE_NAME} stopping")
        win32event.SetEvent(self.stop_event)
        self.stop_server_process()

    def SvcDoRun(self):
        boot_log("SvcDoRun entered")
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        servicemanager.LogInfoMsg(f"{SERVICE_NAME} starting")

        try:
            self.server_process = self.start_server_process()
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            servicemanager.LogInfoMsg(f"{SERVICE_NAME} running")

            while win32event.WaitForSingleObject(self.stop_event, 1000) != win32event.WAIT_OBJECT_0:
                if self.server_process is not None and self.server_process.poll() is not None:
                    message = (
                        f"{SERVICE_NAME} worker exited unexpectedly "
                        f"with code {self.server_process.returncode}"
                    )
                    boot_log(message)
                    servicemanager.LogErrorMsg(message)
                    break
        except Exception as error:
            boot_log(f"SvcDoRun failed: {error!r}")
            servicemanager.LogErrorMsg(f"{SERVICE_NAME} failed to start: {error!r}")
            raise
        finally:
            self.stop_server_process()
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            boot_log("Service stopped")

    def start_server_process(self) -> subprocess.Popen:
        if not PYTHON_EXE.exists():
            raise FileNotFoundError(f"Embedded Python not found: {PYTHON_EXE}")

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stdout_path = LOG_DIR / "service-stdout.log"
        stderr_path = LOG_DIR / "service-stderr.log"
        self.stdout_file = stdout_path.open("a", encoding="utf-8")
        self.stderr_file = stderr_path.open("a", encoding="utf-8")

        command = build_server_command()
        boot_log(f"Launching server: {' '.join(command)}")

        return subprocess.Popen(
            command,
            cwd=BASE_DIR,
            env=build_server_environment(),
            stdout=self.stdout_file,
            stderr=self.stderr_file,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def stop_server_process(self) -> None:
        if self.server_process is not None and self.server_process.poll() is None:
            boot_log("Stopping worker process")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                boot_log("Worker did not stop in time; killing process")
                self.server_process.kill()
                self.server_process.wait(timeout=10)

        self.server_process = None

        if self.stdout_file is not None:
            self.stdout_file.close()
            self.stdout_file = None

        if self.stderr_file is not None:
            self.stderr_file.close()
            self.stderr_file = None


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(OrderBridgeService)
