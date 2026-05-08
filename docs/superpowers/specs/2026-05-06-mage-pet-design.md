# KISMET 懸浮小法師（MagePet）設計文件

**日期：** 2026-05-06  
**功能：** 桌面寵物，隨 KISMET CLI 執行階段切換動畫狀態

---

## 背景

KISMET 已有完整的 terminal UI（Rich）。本功能在此之外，新增一個常駐桌面的「懸浮小法師」視窗，以動畫反映 CLI 目前的執行階段，強化數位玄學的沉浸感。

---

## 架構概覽

```
kismet CLI (foreground)
  ├── 每個指令啟動時：ensure_mage_running()
  ├── 各關鍵時間點：write_state(state)
  └── kismet mage stop → stop_mage()

~/.kismet_presence.json       ← CLI 寫、MagePet 讀
~/.kismet_mage.pid            ← 小法師 PID 記錄
~/.kismet_mage_pos.json       ← 視窗位置記憶

MagePet process (python -m kismet.mage)
  ├── PyQt6 QMainWindow（透明背景、置頂、無邊框、無 taskbar）
  ├── AnimationController（GIF/PNG 序列載入、fallback chain）
  ├── StateWatcher（QTimer 300ms polling）
  └── 拖曳支援 + 位置記憶
```

---

## 狀態機

共 8 個狀態：

| 狀態 | 觸發時機 | 表情 |
|------|----------|------|
| `idle` | 無 CLI 執行，或 stale timeout | 😴 |
| `divine` | `_run_divination()` 開始 | 🔮 |
| `mining` | `miner.mine()` 開始 | ⚒ |
| `curse` | `run_curse()` mining 開始 | 💀 |
| `failed` | 挖礦/下蠱達上限未中 | 😰 |
| `blessing` | `show_blessing()` 顯示後 | 🙏 |
| `success` | 找到吉利 hash 或 k≥81 直接 commit | ✨ |
| `exorcism` | `run_force()` 驅魔儀式時 | ☠ |

### 各指令流程

**`kismet commit`**
```
start → divine
  k ≥ 81 → success → commit
  k ≤ 40 → mining
    命中 → success → commit
    未中 → failed → blessing → commit
  40 < k ≤ 80 → (詢問使用者) → mining 或 success
CLI 結束 → idle (stale timeout)
```

**`kismet mine`**
```
start → mining
  命中 → success
  未中 → failed → blessing
CLI 結束 → idle
```

**`kismet curse`**
```
start → curse
  命中不詳 hash → success → commit
  未中 → failed → commit anyway
CLI 結束 → idle
```

**`kismet force`**
```
start → exorcism
  驅魔後 commit
CLI 結束 → idle
```

**`kismet divine`**
```
start → divine
  完成 → CLI 結束 → idle
```

### Idle 回退條件（stale detection）

StateWatcher 每次 poll 時檢查：
- `cli_pid` 對應的 process 已死亡，**且**
- `timestamp` 超過 5 秒

滿足以上條件 → 強制切換到 `idle`，防止 CLI crash 導致小法師卡住。

---

## 新增模組

### `kismet/presence.py`

CLI 端的狀態寫入與進程管理：

```python
PRESENCE_FILE = Path.home() / ".kismet_presence.json"
MAGE_PID_FILE = Path.home() / ".kismet_mage.pid"

def write_state(state: str) -> None:
    """寫入 {"state": ..., "timestamp": ..., "cli_pid": ...}"""

def ensure_mage_running() -> None:
    """若小法師未在跑，以 DETACHED_PROCESS 啟動 python -m kismet.mage"""

def stop_mage() -> None:
    """讀 .kismet_mage.pid，送 SIGTERM，清除 pid 檔"""
```

### `kismet/mage/pet.py` — `MagePet`

```python
class MagePet(QMainWindow):
    """PyQt6 桌面寵物視窗。"""
```

視窗屬性：
- `Qt.WindowType.FramelessWindowHint` — 無邊框
- `Qt.WindowType.WindowStaysOnTopHint` — 置頂
- `Qt.WindowType.Tool` — 不出現在 taskbar
- `Qt.WidgetAttribute.WA_TranslucentBackground` — per-pixel alpha 透明

行為：
- 啟動時讀 `~/.kismet_mage_pos.json`，定位到記憶位置；預設右下角（`screen.availableGeometry().bottomRight() - QPoint(width + 20, height + 40)`）
- 支援滑鼠拖曳（`mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent`）
- 放開後寫入 `~/.kismet_mage_pos.json`
- `StateWatcher.state_changed` signal → `_set_state(state)` → 切換動畫

### `kismet/mage/animation.py` — `AnimationController`

資產載入策略（優先順序）：

1. `assets/{state}.gif` → `QMovie`
2. `assets/{state}/` 資料夾內的 PNG 序列（按檔名排序）→ `QTimer` 循環切換 `QPixmap` list，更新 `QLabel`
3. Fallback chain：`exorcism → blessing → idle`，任何缺失 state → `idle`

```python
class AnimationController:
    def __init__(self, assets_dir: Path): ...
    def get(self, state: str) -> QMovie | None: ...
```

### `kismet/mage/state_watcher.py` — `StateWatcher`

```python
class StateWatcher(QObject):
    state_changed = pyqtSignal(str)

    def start(self): ...   # 啟動 QTimer 300ms
    def _poll(self): ...   # 讀 presence.json，偵測 stale，emit state_changed
```

### `kismet/mage/__main__.py`

```python
app = QApplication(sys.argv)
pet = MagePet()
pet.show()
sys.exit(app.exec())
```

---

## Assets 目錄

```
kismet/mage/assets/
  idle.gif
  divine.gif
  mining.gif
  curse.gif
  failed.gif
  blessing.gif
  success.gif
  exorcism.gif
```

GIF 或子資料夾 PNG 序列均可，`AnimationController` 自動偵測。  
初期可先放佔位 GIF，日後替換素材不需改 code。

---

## CLI 整合點

### `kismet/cli.py` — 新增指令

```python
@cli.group()
def mage():
    """小法師桌面寵物管理"""

@mage.command()
def stop():
    """關閉小法師"""
    from kismet.presence import stop_mage
    stop_mage()
```

### `kismet/agent/agent.py` — 狀態注入

每個 `run_*()` 方法頂部加：

```python
from kismet.presence import ensure_mage_running, write_state
ensure_mage_running()
```

各關鍵時間點：

| 位置 | 呼叫 |
|------|------|
| `_run_divination()` 開始前 | `write_state("divine")` |
| `miner.mine()` 開始前 | `write_state("mining")` |
| `show_success()` 之後 | `write_state("success")` |
| mining 未中後 | `write_state("failed")` |
| `show_blessing()` 之後 | `write_state("blessing")` |
| `run_curse()` 下蠱 loop 開始前 | `write_state("curse")` |
| `run_curse()` 未中後 | `write_state("failed")` |
| `run_force()` 驅魔時 | `write_state("exorcism")` |

---

## 依賴

新增：

```toml
[project.optional-dependencies]
mage = ["pyqt6"]
```

或直接加入 `[project.dependencies]`（若要讓 `kismet` 預設帶入）。

---

## 不在範圍內

- 右鍵選單（mage 視窗）
- 多螢幕支援
- 小法師點擊互動（點擊顯示 K-value 等）
- 系統匣（System Tray）圖示
