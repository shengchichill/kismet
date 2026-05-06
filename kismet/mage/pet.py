from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

from kismet.mage.animation import AnimationController
from kismet.mage.state_watcher import StateWatcher

POS_FILE = Path.home() / ".kismet_mage_pos.json"
_WINDOW_SIZE = (128, 128)


def _load_pos() -> Optional[tuple[int, int]]:
    try:
        data = json.loads(POS_FILE.read_text(encoding="utf-8"))
        return int(data["x"]), int(data["y"])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return None


def _save_pos(x: int, y: int) -> None:
    POS_FILE.write_text(json.dumps({"x": x, "y": y}), encoding="utf-8")


def _default_pos() -> tuple[int, int]:
    screen = QApplication.primaryScreen().availableGeometry()
    w, h = _WINDOW_SIZE
    return screen.width() - w - 20, screen.height() - h - 40


class MagePet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(*_WINDOW_SIZE)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.resize(*_WINDOW_SIZE)

        self._png_timer = QTimer(self)
        self._png_timer.timeout.connect(self._advance_png_frame)
        self._png_frames: list[QPixmap] = []
        self._png_idx = 0

        self._drag_pos: Optional[QPoint] = None

        self._animation = AnimationController()
        self._watcher = StateWatcher()
        self._watcher.state_changed.connect(self._set_state)
        self._watcher.start()

        pos = _load_pos() or _default_pos()
        self.move(*pos)
        self._set_state("idle")

    def _set_state(self, state: str) -> None:
        self._png_timer.stop()
        asset = self._animation.get(state)
        if asset is None:
            return
        if hasattr(asset, "start"):
            # QMovie (GIF)
            self._label.setMovie(asset)
            asset.start()
        elif isinstance(asset, list):
            # PNG frame list
            self._png_frames = asset
            self._png_idx = 0
            self._label.setPixmap(asset[0])
            if len(asset) > 1:
                self._png_timer.start(100)

    def _advance_png_frame(self) -> None:
        if not self._png_frames:
            return
        self._png_idx = (self._png_idx + 1) % len(self._png_frames)
        self._label.setPixmap(self._png_frames[self._png_idx])

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        _save_pos(self.x(), self.y())
