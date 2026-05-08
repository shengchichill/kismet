import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Generator, Optional

import click

PRESENCE_FILE = Path.home() / ".kismet_presence.json"
MAGE_PID_FILE = Path.home() / ".kismet_mage.pid"
_STALE_TIMEOUT = 5.0


def write_state(state: str) -> None:
    PRESENCE_FILE.write_text(json.dumps({
        "state": state,
        "timestamp": time.time(),
        "cli_pid": os.getpid(),
    }), encoding="utf-8")


def read_presence() -> Optional[dict]:
    try:
        return json.loads(PRESENCE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        # os.kill(pid, 0) on Windows calls GenerateConsoleCtrlEvent, not a
        # liveness probe. Processes created with CREATE_NO_WINDOW don't share
        # the caller's console, so the call always raises OSError regardless of
        # whether the process is alive. Use OpenProcess + GetExitCodeProcess
        # instead.
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _is_stale(data: dict) -> bool:
    if time.time() - data["timestamp"] < _STALE_TIMEOUT:
        return False
    return not _pid_alive(data["cli_pid"])


def compute_mage_state(data: Optional[dict]) -> str:
    if data is None or _is_stale(data):
        return "idle"
    return data.get("state", "idle")


@contextlib.contextmanager
def keep_state_alive(state: str, interval: float = 2.0) -> Generator[None, None, None]:
    """Refresh presence state in the background while a long-running operation runs.
    Caller is responsible for the initial write_state(state) call."""
    stop = threading.Event()

    def _refresh() -> None:
        while not stop.wait(interval):
            write_state(state)

    t = threading.Thread(target=_refresh, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1.0)


def ensure_mage_running() -> None:
    if MAGE_PID_FILE.exists():
        try:
            pid = int(MAGE_PID_FILE.read_text(encoding="utf-8").strip())
            if _pid_alive(pid):
                return
        except ValueError:
            pass
    kwargs: dict = {}
    if sys.platform == "win32":
        # MSDN: CREATE_NO_WINDOW is silently ignored when combined with
        # DETACHED_PROCESS, so we drop DETACHED_PROCESS here.
        # STARTUPINFO SW_HIDE is a belt-and-suspenders fallback.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        [sys.executable, "-m", "kismet.mage"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )
    MAGE_PID_FILE.write_text(str(proc.pid), encoding="utf-8")


def stop_mage() -> None:
    if not MAGE_PID_FILE.exists():
        click.echo("小法師 not running")
        return
    try:
        pid = int(MAGE_PID_FILE.read_text(encoding="utf-8").strip())
        os.kill(pid, signal.SIGTERM)
    except (ValueError, OSError):
        pass
    MAGE_PID_FILE.unlink(missing_ok=True)
    click.echo("小法師 已關閉")


_VALID_MAGE_MODES = {"auto", "gui", "off"}


def detect_mage_mode(config_value: str) -> str:
    if config_value not in _VALID_MAGE_MODES:
        raise ValueError(f"Unknown mage_mode {config_value!r}. Valid values: {sorted(_VALID_MAGE_MODES)}")
    if config_value != "auto":
        return config_value
    # In headless environments (SSH, no display server) fall back to off.
    if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
        return "off"
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        return "off"
    return "gui"
