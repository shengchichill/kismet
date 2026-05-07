# Terminal 模式小法師 Design

## Goal

讓 SSH remote 使用者也能在終端看到小法師桌面寵物，以 `term-image` 將 GIF 動畫渲染為 Unicode block 字元，顯示在 Rich Live 固定 footer。

## Architecture

新增 `mage_mode` config 選項，決定啟動哪種模式：

| 模式 | 行為 |
|------|------|
| `"auto"` | 偵測 `SSH_CLIENT`/`SSH_TTY` env var 或無 `DISPLAY` → `"terminal"`；否則 → `"gui"` |
| `"gui"` | 現有 PyQt6 背景 subprocess（不變） |
| `"terminal"` | Rich Live footer + term-image GIF 動畫 |
| `"off"` | 不啟動任何寵物 |

顯示結構（terminal 模式）：

```
  ⠙ 占卜中...           ← 正常 terminal 捲動輸出（不受影響）
  K-value: 72
  ⛏ 逆天改運中...
  [committed: abc1234]
╔══════════════════════╗  ← Rich Live footer（固定底部）
║  [小法師 GIF 動畫]   ║
╚══════════════════════╝
```

## Tech Stack

- `term-image` — GIF frame → Unicode block string（optional 依賴，缺少時降級）
- `rich.live.Live` + `rich.panel.Panel` — footer 渲染
- `threading.Thread` + `threading.Event` — 背景 frame 動畫 + state polling
- 現有 IPC：`~/.kismet_presence.json`（不變）

## Components

### `kismet/config.py`

新增欄位：

```python
mage_mode: str = "auto"  # "auto" | "gui" | "terminal" | "off"
```

### `kismet/presence.py`

新增 `detect_mage_mode(config_value: str) -> str`：

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

### `kismet/mage/terminal_pet.py`（新增）

```python
class TerminalMagePet:
    """Context manager: Rich Live footer with GIF animation for terminal mode."""

    def __enter__(self) -> "TerminalMagePet": ...
    def __exit__(self, *args) -> None: ...
```

**`__enter__` 行為：**
1. 嘗試 `import term_image`；失敗則設 `self._disabled = True`，直接回傳（降級）
2. 啟動 `Rich Live(Panel(...), refresh_per_second=10)`
3. 啟動背景 thread（`daemon=True`）

**背景 thread 職責（loop interval = 100ms）：**
- 每 100ms 前進一幀：用 `term_image` seek + render → `str(image)` 取得 ANSI block string，呼叫 `self._live.update(Panel(Text(frame_str)))` 更新 footer
- 每 3 次 loop（≈300ms）呼叫 `read_presence()` + `compute_mage_state()`，state 改變時載入對應 GIF，重置 frame index

**`__exit__` 行為：**
1. 設 stop event
2. Join thread（timeout=1s）
3. `self._live.stop()`

**錯誤處理：**
- GIF 不存在：跳過該 state，保持前一個 GIF
- `term_image` 未安裝：`__enter__` 捕捉 `ImportError`，設 `_disabled=True`，靜默降級

### `kismet/agent/agent.py`

新增 `_start_mage()` method，取代各 `run_*` 裡的 `ensure_mage_running()` 呼叫：

```python
import contextlib
from kismet.mage.terminal_pet import TerminalMagePet
from kismet.mage.animation import ASSETS_DIR
from kismet.presence import detect_mage_mode, ensure_mage_running

def _start_mage(self):
    mode = detect_mage_mode(self.config.mage_mode)
    if mode == "gui":
        ensure_mage_running()
        return contextlib.nullcontext()
    if mode == "terminal":
        return TerminalMagePet(ASSETS_DIR)
    return contextlib.nullcontext()  # "off"
```

所有 `run_*` method 改為：

```python
def run_commit(self) -> None:
    with self._start_mage():
        self.renderer.show_banner()
        session = self._build_session()
        ...
```

**`RendererTool` 不需要修改**，文字輸出在 Live footer 上方正常捲動。

**`kismet mage stop` 在 terminal 模式不適用**：terminal pet 的生命週期由 context manager 管理，CLI 指令結束時自動停止，無 PID file 寫入。`stop_mage()` 仍正常運作（僅 GUI 模式有效）。

## Data Flow

```
kismet commit
  └─ _start_mage()
       ├─ gui mode: ensure_mage_running() → PyQt6 subprocess（現有）
       ├─ terminal mode: TerminalMagePet.__enter__()
       │    └─ 背景 thread: poll JSON → switch GIF → cycle frames → Live.update()
       └─ off mode: nullcontext()

write_state("divine")  →  ~/.kismet_presence.json
                               ↑ 背景 thread 每 300ms 讀取（terminal 模式）
                               ↑ StateWatcher 每 300ms 讀取（gui 模式）
```

## Testing

### `test_detect_mage_mode.py`

| 情境 | 預期回傳 |
|------|---------|
| config="gui" | "gui" |
| config="terminal" | "terminal" |
| config="off" | "off" |
| config="auto", SSH_CLIENT 設定 | "terminal" |
| config="auto", SSH_TTY 設定 | "terminal" |
| config="auto", Linux 無 DISPLAY | "terminal" |
| config="auto", 無 SSH, 有 DISPLAY | "gui" |
| config="auto", Windows（無 SSH） | "gui" |

### `test_terminal_pet.py`

- `term_image` ImportError → `_disabled=True`，`__exit__` 不 crash
- state 改變時切換 GIF（mock `read_presence`）
- GIF 不存在時靜默保持前一個 GIF

### `test_agent_start_mage.py`

- `mage_mode="gui"` → 呼叫 `ensure_mage_running()`，回傳 `nullcontext`
- `mage_mode="terminal"` → 回傳 `TerminalMagePet` instance
- `mage_mode="off"` → 回傳 `nullcontext`，不呼叫 `ensure_mage_running()`

## Scope

| 項目 | 說明 |
|------|------|
| 新增 | `kismet/mage/terminal_pet.py` |
| 修改 | `kismet/config.py`, `kismet/presence.py`, `kismet/agent/agent.py` |
| 不動 | `RendererTool`, `pet.py`, `__main__.py`, CLI, 現有 tests |
| 新依賴 | `term-image`（optional，`pyproject.toml` extras） |
