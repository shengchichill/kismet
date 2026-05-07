from __future__ import annotations

import threading
from pathlib import Path

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from kismet.mage.animation import ASSETS_DIR
from kismet.presence import compute_mage_state, read_presence

try:
    from term_image.image import BlockImage
except ImportError:
    BlockImage = None  # type: ignore[assignment,misc]


class TerminalMagePet:
    """Context manager: Rich Live footer with GIF animation for terminal mode."""

    def __init__(self, assets_dir: Path = ASSETS_DIR):
        self._assets_dir = assets_dir
        self._disabled = False
        self._stop = threading.Event()
        self._live: Live | None = None
        self._thread: threading.Thread | None = None
        self._current_img = None
        self._frame_count = 1
        self._frame_idx = 0
        self._current_state = ""

    def __enter__(self) -> "TerminalMagePet":
        if BlockImage is None:
            self._disabled = True
            return self
        self._live = Live(Panel(""), refresh_per_second=10, transient=True)
        self._live.start()
        self._load_gif("idle")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args) -> None:
        if self._disabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        if self._live:
            self._live.stop()

    def _load_gif(self, state: str) -> None:
        gif_path = self._assets_dir / f"{state}.gif"
        if not gif_path.exists():
            return
        try:
            img = BlockImage.from_file(str(gif_path))
            self._current_img = img
            self._frame_count = max(getattr(img, "n_frames", 1), 1)
            self._frame_idx = 0
            self._current_state = state
        except Exception:
            pass

    def _run(self) -> None:
        poll_counter = 0
        while not self._stop.is_set():
            poll_counter += 1
            if poll_counter >= 3:
                poll_counter = 0
                new_state = compute_mage_state(read_presence())
                if new_state != self._current_state:
                    self._load_gif(new_state)

            if self._current_img is not None and self._live is not None:
                try:
                    self._current_img.seek(self._frame_idx % self._frame_count)
                    frame_str = str(self._current_img)
                    self._live.update(Panel(Text.from_ansi(frame_str), title="小法師"))
                    self._frame_idx = (self._frame_idx + 1) % self._frame_count
                except Exception:
                    pass

            self._stop.wait(0.1)
