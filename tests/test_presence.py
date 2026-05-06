import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from kismet import presence as p


@pytest.fixture
def pfiles(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "PRESENCE_FILE", tmp_path / "presence.json")
    monkeypatch.setattr(p, "MAGE_PID_FILE", tmp_path / "mage.pid")
    return tmp_path


def test_write_state_creates_file(pfiles):
    p.write_state("divine")
    data = json.loads((pfiles / "presence.json").read_text())
    assert data["state"] == "divine"
    assert data["cli_pid"] == os.getpid()
    assert abs(data["timestamp"] - time.time()) < 2


def test_write_state_overwrites(pfiles):
    p.write_state("mining")
    p.write_state("success")
    data = json.loads((pfiles / "presence.json").read_text())
    assert data["state"] == "success"


def test_is_stale_when_pid_dead_and_old():
    data = {"state": "mining", "timestamp": time.time() - 10, "cli_pid": 9_999_999}
    assert p._is_stale(data) is True


def test_not_stale_when_pid_alive():
    data = {"state": "mining", "timestamp": time.time() - 10, "cli_pid": os.getpid()}
    assert p._is_stale(data) is False


def test_not_stale_when_recent():
    data = {"state": "mining", "timestamp": time.time(), "cli_pid": 9_999_999}
    assert p._is_stale(data) is False


def test_compute_mage_state_none():
    assert p.compute_mage_state(None) == "idle"


def test_compute_mage_state_stale():
    data = {"state": "mining", "timestamp": time.time() - 10, "cli_pid": 9_999_999}
    assert p.compute_mage_state(data) == "idle"


def test_compute_mage_state_active():
    data = {"state": "divine", "timestamp": time.time(), "cli_pid": os.getpid()}
    assert p.compute_mage_state(data) == "divine"


def test_read_presence_missing_file(pfiles):
    assert p.read_presence() is None


def test_read_presence_returns_data(pfiles):
    p.write_state("idle")
    data = p.read_presence()
    assert data["state"] == "idle"


def test_stop_mage_no_pid_file(pfiles, capsys):
    p.stop_mage()
    assert "not running" in capsys.readouterr().out


def test_stop_mage_sends_signal_and_removes_file(pfiles):
    (pfiles / "mage.pid").write_text(str(os.getpid()))
    with patch("os.kill"):
        p.stop_mage()
    assert not (pfiles / "mage.pid").exists()


def test_ensure_mage_running_starts_process(pfiles):
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        p.ensure_mage_running()
    mock_popen.assert_called_once()
    assert (pfiles / "mage.pid").read_text() == "12345"


def test_ensure_mage_running_skips_if_alive(pfiles):
    (pfiles / "mage.pid").write_text(str(os.getpid()))
    with patch("subprocess.Popen") as mock_popen:
        p.ensure_mage_running()
    mock_popen.assert_not_called()
