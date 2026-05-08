# Terminal 模式小法師 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增終端模式小法師，在 SSH remote 環境以 term-image 將 GIF 動畫渲染為 Unicode block 字元，固定顯示在 Rich Live footer。

**Architecture:** `mage_mode` config 欄位（env var `KISMET_MAGE_MODE`，預設 `"auto"`）控制行為；`detect_mage_mode()` 偵測 SSH env var 或無 DISPLAY → terminal；`TerminalMagePet` context manager 管理 Rich Live footer 和背景動畫 thread；`KismetAgent._start_mage()` 取代現有 `ensure_mage_running()` 呼叫，依模式回傳對應 context manager。

**Tech Stack:** Python 3.10+, term-image>=0.7.2 (BlockImage), rich Live/Panel/Text, threading, 現有 kismet.presence IPC（~/.kismet_presence.json）

---

## 現有程式碼脈絡

**`kismet/config.py`**: `Config` 是 `@dataclass`，欄位全部從 env var 讀取（`load_config()`）。現有欄位：`litellm_base_url`, `litellm_api_key`, `model`, `max_mine_attempts`, `max_message_tokens`, `_costs_path`, `_costs_cache`。

**`kismet/presence.py`**: 已有 `import os, sys`。現有函式：`write_state()`, `read_presence()`, `compute_mage_state()`, `ensure_mage_running()`, `stop_mage()`。

**`kismet/agent/agent.py`**: `KismetAgent` 每個 `run_*` method 一開始都呼叫 `ensure_mage_running()`。現有 import：`from kismet.presence import ensure_mage_running, write_state`。

**`kismet/mage/animation.py`**: 已定義 `ASSETS_DIR = Path(__file__).parent / "assets"`（可直接 import）。

**`tests/test_agent_presence.py`**: `_make_agent()` 直接建構 `Config(...)` 並 mock 所有子元件；所有 test 都 `@patch("kismet.agent.agent.ensure_mage_running")`。

---

## Task 1: `mage_mode` Config + `detect_mage_mode`

**Files:**
- Modify: `kismet/config.py`
- Modify: `kismet/presence.py`
- Create: `tests/test_detect_mage_mode.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: 寫 detect_mage_mode 的失敗測試**

新建 `tests/test_detect_mage_mode.py`：

```python
import sys
from unittest.mock import patch

import pytest

from kismet.presence import detect_mage_mode


def test_explicit_gui():
    assert detect_mage_mode("gui") == "gui"


def test_explicit_terminal():
    assert detect_mage_mode("terminal") == "terminal"


def test_explicit_off():
    assert detect_mage_mode("off") == "off"


def test_auto_ssh_client(monkeypatch):
    monkeypatch.setenv("SSH_CLIENT", "10.0.0.1 22 22")
    monkeypatch.delenv("SSH_TTY", raising=False)
    assert detect_mage_mode("auto") == "terminal"


def test_auto_ssh_tty(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.setenv("SSH_TTY", "/dev/pts/0")
    assert detect_mage_mode("auto") == "terminal"


def test_auto_no_display_linux(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    with patch("sys.platform", "linux"):
        assert detect_mage_mode("auto") == "terminal"


def test_auto_has_display_linux(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    with patch("sys.platform", "linux"):
        assert detect_mage_mode("auto") == "gui"


def test_auto_windows_no_ssh(monkeypatch):
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    with patch("sys.platform", "win32"):
        assert detect_mage_mode("auto") == "gui"
```

- [ ] **Step 2: 確認 detect_mage_mode 測試失敗**

```bash
uv run pytest tests/test_detect_mage_mode.py -v
```

預期：`ImportError` 或 `AttributeError`（函式尚未存在）

- [ ] **Step 3: 實作 `detect_mage_mode` 於 presence.py**

在 `kismet/presence.py` 檔案末尾加入（`stop_mage` 之後）：

```python
def detect_mage_mode(config_value: str) -> str:
    if config_value != "auto":
        return config_value
    if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
        return "terminal"
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        return "terminal"
    return "gui"
```

- [ ] **Step 4: 確認 detect_mage_mode 測試通過**

```bash
uv run pytest tests/test_detect_mage_mode.py -v
```

預期：8 tests PASSED

- [ ] **Step 5: 寫 mage_mode config 的失敗測試**

在 `tests/test_config.py` 末尾加入：

```python
def test_load_config_mage_mode_default(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.delenv("KISMET_MAGE_MODE", raising=False)
    cfg = load_config()
    assert cfg.mage_mode == "auto"


def test_load_config_mage_mode_env_var(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("KISMET_MAGE_MODE", "terminal")
    cfg = load_config()
    assert cfg.mage_mode == "terminal"
```

- [ ] **Step 6: 確認 config 測試失敗**

```bash
uv run pytest tests/test_config.py::test_load_config_mage_mode_default tests/test_config.py::test_load_config_mage_mode_env_var -v
```

預期：FAILED（`Config` 尚無 `mage_mode` 欄位）

- [ ] **Step 7: 在 Config dataclass 加入 `mage_mode` 欄位**

修改 `kismet/config.py`，在 `_costs_path: str` 和 `_costs_cache` 之間加入：

```python
@dataclass
class Config:
    litellm_base_url: str
    litellm_api_key: str
    model: str
    max_mine_attempts: int
    max_message_tokens: int
    _costs_path: str
    mage_mode: str = "auto"
    _costs_cache: Optional[dict] = None
```

並在 `load_config()` 的 `return Config(...)` 中加入：

```python
    return Config(
        litellm_base_url=base_url,
        litellm_api_key=api_key,
        model=os.environ.get("KISMET_MODEL", "gpt-4o-mini"),
        max_mine_attempts=int(os.environ.get("MAX_MINE_ATTEMPTS", "10")),
        max_message_tokens=int(os.environ.get("MAX_MESSAGE_TOKENS", "200")),
        _costs_path=costs_path,
        mage_mode=os.environ.get("KISMET_MAGE_MODE", "auto"),
    )
```

- [ ] **Step 8: 確認所有 config 和 detect 測試通過**

```bash
uv run pytest tests/test_config.py tests/test_detect_mage_mode.py -v
```

預期：全部 PASSED

- [ ] **Step 9: 確認現有測試不 break**

```bash
uv run pytest -v
```

預期：全部 PASSED（`Config` 新增欄位有 default，現有直接建構的地方不受影響）

- [ ] **Step 10: Commit**

```bash
git add kismet/config.py kismet/presence.py tests/test_detect_mage_mode.py tests/test_config.py
git commit -m "feat: add mage_mode config and detect_mage_mode"
```

---

## Task 2: `TerminalMagePet`

**Files:**
- Create: `kismet/mage/terminal_pet.py`
- Create: `tests/mage/test_terminal_pet.py`

**Background:** term-image 的 `BlockImage` 強制使用 Unicode block 字元渲染（跨平台可靠），不使用 sixel 或 kitty 協定。GIF 動畫透過 `BlockImage.from_file(path)` 載入，`img.seek(n)` 切換 frame，`img.n_frames` 取得總 frame 數，`str(img)` 取得 ANSI block string。ANSI string 透過 `Text.from_ansi()` 轉成 Rich Text 後放入 `Panel`。

- [ ] **Step 1: 寫 TerminalMagePet 的失敗測試**

新建 `tests/mage/test_terminal_pet.py`：

```python
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kismet.mage.terminal_pet import TerminalMagePet


def test_import_error_disables(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "term_image", None)
    monkeypatch.setitem(sys.modules, "term_image.image", None)
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


def test_exit_without_enter_does_not_crash(tmp_path):
    pet = TerminalMagePet(tmp_path)
    pet._disabled = True
    pet.__exit__(None, None, None)  # _live is None, should not raise
```

- [ ] **Step 2: 確認測試失敗**

```bash
uv run pytest tests/mage/test_terminal_pet.py -v
```

預期：`ModuleNotFoundError`（`terminal_pet` 尚未存在）

- [ ] **Step 3: 實作 `kismet/mage/terminal_pet.py`**

新建 `kismet/mage/terminal_pet.py`：

```python
from __future__ import annotations

import threading
from pathlib import Path

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from kismet.mage.animation import ASSETS_DIR
from kismet.presence import compute_mage_state, read_presence


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
        try:
            from term_image.image import BlockImage  # noqa: F401
        except ImportError:
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
            from term_image.image import BlockImage
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
                except Exception:
                    pass
                self._frame_idx = (self._frame_idx + 1) % self._frame_count

            self._stop.wait(0.1)
```

- [ ] **Step 4: 確認 TerminalMagePet 測試通過**

```bash
uv run pytest tests/mage/test_terminal_pet.py -v
```

預期：4 tests PASSED

- [ ] **Step 5: 確認所有測試不 break**

```bash
uv run pytest -v
```

預期：全部 PASSED

- [ ] **Step 6: Commit**

```bash
git add kismet/mage/terminal_pet.py tests/mage/test_terminal_pet.py
git commit -m "feat: add TerminalMagePet for terminal mode GIF animation"
```

---

## Task 3: Agent `_start_mage()` 整合

**Files:**
- Modify: `kismet/agent/agent.py`
- Create: `tests/test_agent_start_mage.py`
- Modify: `tests/test_agent_presence.py`

**Background:** 現有 `test_agent_presence.py` 的 `_make_agent()` 用 `Config(...)` 直接建構，未傳 `mage_mode`（預設 `"auto"`）。加入 `_start_mage()` 後，若 `detect_mage_mode("auto")` 在 CI Linux 環境回傳 `"terminal"`，`ensure_mage_running` 就不會被呼叫，導致 `mock_ensure.assert_called_once()` 失敗。解法：在 `_make_agent()` 明確傳入 `mage_mode="gui"`。

- [ ] **Step 1: 寫 `_start_mage` 的失敗測試**

新建 `tests/test_agent_start_mage.py`：

```python
import contextlib
from unittest.mock import MagicMock, patch

import pytest

from kismet.agent.agent import KismetAgent
from kismet.config import Config
from kismet.mage.terminal_pet import TerminalMagePet


def _make_agent(mage_mode: str = "gui") -> KismetAgent:
    config = Config(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test-key",
        model="gpt-4o-mini",
        max_mine_attempts=3,
        max_message_tokens=100,
        _costs_path="nonexistent.yml",
        mage_mode=mage_mode,
    )
    agent = KismetAgent.__new__(KismetAgent)
    agent.config = config
    return agent


def test_start_mage_gui_calls_ensure_running():
    agent = _make_agent(mage_mode="gui")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="gui"), \
         patch("kismet.agent.agent.ensure_mage_running") as mock_ensure:
        ctx = agent._start_mage()
        mock_ensure.assert_called_once()
        assert isinstance(ctx, contextlib.nullcontext)


def test_start_mage_terminal_returns_terminal_pet():
    agent = _make_agent(mage_mode="terminal")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="terminal"):
        ctx = agent._start_mage()
        assert isinstance(ctx, TerminalMagePet)


def test_start_mage_off_no_ensure_running():
    agent = _make_agent(mage_mode="off")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="off"), \
         patch("kismet.agent.agent.ensure_mage_running") as mock_ensure:
        ctx = agent._start_mage()
        mock_ensure.assert_not_called()
        assert isinstance(ctx, contextlib.nullcontext)
```

- [ ] **Step 2: 確認測試失敗**

```bash
uv run pytest tests/test_agent_start_mage.py -v
```

預期：FAILED（`_start_mage` 尚未存在）

- [ ] **Step 3: 在 `agent.py` 加入 `_start_mage()` 並重構 `run_*` methods**

修改 `kismet/agent/agent.py`：

**imports 區塊改為：**

```python
import contextlib

from kismet.agent.session import KismetSession
from kismet.agent.tools.divine import DivinationTool
from kismet.agent.tools.git import GitContext, GitTool
from kismet.agent.tools.mine import MinerTool, is_lucky
from kismet.agent.tools.renderer import RendererTool
from kismet.config import Config
from kismet.mage.animation import ASSETS_DIR
from kismet.mage.terminal_pet import TerminalMagePet
from kismet.presence import detect_mage_mode, ensure_mage_running, write_state
```

**在 `KismetAgent` 的 `_ctx_from_session()` 之後、`_run_divination()` 之前加入 `_start_mage()`：**

```python
    def _start_mage(self):
        mode = detect_mage_mode(self.config.mage_mode)
        if mode == "gui":
            ensure_mage_running()
            return contextlib.nullcontext()
        if mode == "terminal":
            return TerminalMagePet(ASSETS_DIR)
        return contextlib.nullcontext()
```

**修改每個 `run_*` method，移除 `ensure_mage_running()` 並用 `with self._start_mage():` 包住 body：**

```python
    def run_commit(self) -> None:
        """Full auto: generate message → divine → decide → [mine] → commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            self._run_divination(session)

            k = session.k_value
            if k >= 81:
                write_state("success")
                self.renderer.show_celebration()
                actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
                self.renderer.show_committed(actual_hash)
            elif k <= 40:
                self._mine_and_commit(session, targets=[])
            else:
                if self.renderer.ask_should_mine(k):
                    self._mine_and_commit(session, targets=[])
                else:
                    write_state("success")
                    actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
                    self.renderer.show_committed(actual_hash)

    def run_divine(self) -> None:
        """Only divine — no commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            self._run_divination(session)

    def run_mine(self, targets: list[str]) -> None:
        """Only mine for a lucky hash — no commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            write_state("mining")
            success = self.miner.mine(session, self.renderer, targets)
            if success:
                write_state("success")
                self.renderer.show_success(session, max_attempts=self.config.max_mine_attempts)
            else:
                write_state("failed")
                self.renderer.show_blessing(session)
                write_state("blessing")
            target_label = " ".join(targets) if targets else "default lucky list"
            self.renderer.console.print(
                f"\n  Lucky target: [{target_label}]\n"
                f"  [bold]{session.current_message}[/bold]\n"
                f"  predicted hash: {session.predicted_hash}"
            )

    def run_force(self) -> None:
        """Force commit with exorcism ritual, no divination."""
        with self._start_mage():
            self.renderer.show_banner()
            diff = self.git.get_staged_diff()
            ctx = self.git.get_context()
            message, _, _ = self.divine.generate_message(diff)
            write_state("exorcism")
            self.renderer.show_exorcism()
            actual_hash = self.git.commit(message, ctx)
            self.renderer.show_committed(actual_hash)

    def run_curse(self, targets: list[str]) -> None:
        """Reverse mine: find an unlucky hash and commit it."""
        with self._start_mage():
            _DEFAULT_CURSE = ["dead", "404", "f00d", "bad"]
            effective = targets if targets else _DEFAULT_CURSE
            self.renderer.show_banner()
            session = self._build_session()
            self.renderer.console.print(
                f"\n  [bold red]⬇ 下蠱模式啟動 — 尋找不詳 hash...[/bold red]\n"
                f"  目標字串: {effective}"
            )
            write_state("curse")
            self.renderer.show_mining_start()

            for attempt in range(1, self.config.max_mine_attempts + 1):
                new_msg, in_tok, out_tok = self.divine.rephrase_message(
                    session.current_message, attempt, self.config.max_mine_attempts
                )
                self._add_tokens(session, in_tok, out_tok)
                new_hash = self.git.compute_hash(new_msg, self._ctx_from_session(session))
                cursed = is_lucky(new_hash, effective)
                self.renderer.show_mining_attempt(attempt, self.config.max_mine_attempts, new_hash, cursed)
                session.current_message = new_msg
                session.predicted_hash = new_hash
                if cursed:
                    write_state("success")
                    self.renderer.console.print(f"\n  [red]☠ 下蠱成功！不詳 hash 已就位。[/red]")
                    actual_hash = self.git.commit(new_msg, self._ctx_from_session(session))
                    self.renderer.show_committed(actual_hash)
                    return

            write_state("failed")
            self.renderer.console.print("\n  [yellow]下蠱未成功，天地不從。仍以普通 hash 提交。[/yellow]")
            actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
            self.renderer.show_committed(actual_hash)
```

- [ ] **Step 4: 確認 `_start_mage` 測試通過**

```bash
uv run pytest tests/test_agent_start_mage.py -v
```

預期：3 tests PASSED

- [ ] **Step 5: 修正 `tests/test_agent_presence.py` 的 `_make_agent()`**

在 `tests/test_agent_presence.py` 找到 `_make_agent()` 函式，加入 `mage_mode="gui"`：

```python
def _make_agent() -> KismetAgent:
    config = Config(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test-key",
        model="gpt-4o-mini",
        max_mine_attempts=3,
        max_message_tokens=100,
        _costs_path="nonexistent.yml",
        mage_mode="gui",
    )
    agent = KismetAgent.__new__(KismetAgent)
    agent.config = config
    agent.git = MagicMock()
    agent.divine = MagicMock()
    agent.miner = MagicMock()
    agent.renderer = MagicMock()
    return agent
```

- [ ] **Step 6: 確認所有 agent presence 測試通過**

```bash
uv run pytest tests/test_agent_presence.py -v
```

預期：6 tests PASSED

- [ ] **Step 7: 確認所有測試通過**

```bash
uv run pytest -v
```

預期：全部 PASSED

- [ ] **Step 8: Commit**

```bash
git add kismet/agent/agent.py tests/test_agent_start_mage.py tests/test_agent_presence.py
git commit -m "feat: add _start_mage() to KismetAgent for terminal/gui/off mode dispatch"
```
