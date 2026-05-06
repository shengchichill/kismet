from pathlib import Path
import pytest
from kismet.mage.animation import AnimationController

DUMMY = b"GIF"  # only testing path discovery, not real GIF needed


def test_find_gif(tmp_path):
    (tmp_path / "idle.gif").write_bytes(DUMMY)
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("idle") == tmp_path / "idle.gif"


def test_find_png_dir(tmp_path):
    png_dir = tmp_path / "mining"
    png_dir.mkdir()
    (png_dir / "frame_001.png").write_bytes(DUMMY)
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("mining") == png_dir


def test_fallback_exorcism_to_blessing(tmp_path):
    (tmp_path / "blessing.gif").write_bytes(DUMMY)
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("exorcism") == tmp_path / "blessing.gif"


def test_fallback_to_idle(tmp_path):
    (tmp_path / "idle.gif").write_bytes(DUMMY)
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("divine") == tmp_path / "idle.gif"


def test_no_asset_returns_none(tmp_path):
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("divine") is None


def test_fallback_does_not_loop_forever(tmp_path):
    # exorcism → blessing → idle, all missing
    ctrl = AnimationController(tmp_path)
    assert ctrl._find_asset("exorcism") is None
