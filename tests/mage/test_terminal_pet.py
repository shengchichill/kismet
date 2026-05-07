from pathlib import Path
from unittest.mock import MagicMock, patch

from kismet.mage.terminal_pet import TerminalMagePet


def test_import_error_disables(tmp_path):
    with patch("kismet.mage.terminal_pet.BlockImage", None):
        pet = TerminalMagePet(tmp_path)
        pet.__enter__()
        assert pet._disabled is True
        pet.__exit__(None, None, None)  # 不應 raise


def test_load_gif_updates_state(tmp_path):
    (tmp_path / "idle.gif").touch()
    pet = TerminalMagePet(tmp_path)
    pet._disabled = False
    pet._live = MagicMock()

    mock_img = MagicMock()
    mock_img.n_frames = 4
    with patch("kismet.mage.terminal_pet.BlockImage") as mock_cls:
        mock_cls.from_file.return_value = mock_img
        pet._load_gif("idle")

    assert pet._current_state == "idle"
    assert pet._current_img is mock_img
    assert pet._frame_count == 4


def test_load_gif_missing_keeps_previous(tmp_path):
    prev_img = MagicMock()
    pet = TerminalMagePet(tmp_path)
    pet._current_state = "idle"
    pet._current_img = prev_img

    pet._load_gif("nonexistent")

    assert pet._current_state == "idle"
    assert pet._current_img is prev_img


def test_exit_before_enter_does_not_crash(tmp_path):
    pet = TerminalMagePet(tmp_path)
    # _disabled=False, _thread=None, _live=None — guarded by if checks in __exit__
    pet.__exit__(None, None, None)  # should not raise
