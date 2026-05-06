from __future__ import annotations

from pathlib import Path
from typing import Optional

ASSETS_DIR = Path(__file__).parent / "assets"

_FALLBACK: dict[str, str] = {"exorcism": "blessing"}


class AnimationController:
    def __init__(self, assets_dir: Path = ASSETS_DIR):
        self._assets_dir = assets_dir
        self._cache: dict[str, object] = {}

    def get(self, state: str):
        """Return QMovie (GIF) or list[QPixmap] (PNG). None if no asset found."""
        if state not in self._cache:
            self._cache[state] = self._load(state)
        return self._cache[state]

    def _find_asset(self, state: str, _visited: frozenset = frozenset()) -> Optional[Path]:
        """Return path to .gif file or PNG directory, following fallback chain."""
        if state in _visited:
            return None
        _visited = _visited | {state}

        gif = self._assets_dir / f"{state}.gif"
        if gif.exists():
            return gif

        png_dir = self._assets_dir / state
        if png_dir.is_dir() and any(png_dir.glob("*.png")):
            return png_dir

        fallback = _FALLBACK.get(state)
        if fallback:
            return self._find_asset(fallback, _visited)
        if state != "idle":
            return self._find_asset("idle", _visited)
        return None

    def _load(self, state: str):
        from PyQt6.QtGui import QMovie, QPixmap

        path = self._find_asset(state)
        if path is None:
            return None
        if path.suffix == ".gif":
            movie = QMovie(str(path))
            return movie if movie.isValid() else None
        frames = [QPixmap(str(p)) for p in sorted(path.glob("*.png"))]
        return frames if frames else None
