import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

PRESENCE_FILE = Path.home() / ".kismet_presence.json"
MAGE_PID_FILE = Path.home() / ".kismet_mage.pid"
_STALE_TIMEOUT = 5.0


def write_state(state: str) -> None:
    PRESENCE_FILE.write_text(json.dumps({
        "state": state,
        "timestamp": time.time(),
        "cli_pid": os.getpid(),
    }))


def read_presence() -> Optional[dict]:
    try:
        return json.loads(PRESENCE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _is_stale(data: dict) -> bool:
    if time.time() - data["timestamp"] < _STALE_TIMEOUT:
        return False
    try:
        os.kill(data["cli_pid"], 0)
        return False
    except OSError:
        return True


def compute_mage_state(data: Optional[dict]) -> str:
    if data is None or _is_stale(data):
        return "idle"
    return data.get("state", "idle")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ensure_mage_running() -> None:
    if MAGE_PID_FILE.exists():
        try:
            pid = int(MAGE_PID_FILE.read_text().strip())
            if _pid_alive(pid):
                return
        except ValueError:
            pass
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen([sys.executable, "-m", "kismet.mage"], **kwargs)
    MAGE_PID_FILE.write_text(str(proc.pid))


def stop_mage() -> None:
    if not MAGE_PID_FILE.exists():
        print("小法師 not running")
        return
    try:
        pid = int(MAGE_PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except (ValueError, OSError):
        pass
    MAGE_PID_FILE.unlink(missing_ok=True)
    print("小法師 已關閉")
