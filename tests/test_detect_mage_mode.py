import sys
from unittest.mock import patch

from kismet.presence import detect_mage_mode


def test_explicit_gui():
    assert detect_mage_mode("gui") == "gui"


def test_explicit_off():
    assert detect_mage_mode("off") == "off"


def test_auto_ssh_client(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "10.0.0.1 22 22")
    monkeypatch.delenv("SSH_TTY", raising=False)
    assert detect_mage_mode("auto") == "off"


def test_auto_ssh_tty(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.setenv("SSH_TTY", "/dev/pts/0")
    assert detect_mage_mode("auto") == "off"


def test_auto_no_display_linux(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    with patch("sys.platform", "linux"):
        assert detect_mage_mode("auto") == "off"


def test_auto_has_display_linux(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    with patch("sys.platform", "linux"):
        assert detect_mage_mode("auto") == "gui"


def test_auto_windows_no_ssh(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    with patch("sys.platform", "win32"):
        assert detect_mage_mode("auto") == "gui"


def test_unknown_mode_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown mage_mode"):
        detect_mage_mode("invalid_mode")
