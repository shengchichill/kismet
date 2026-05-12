# Rich Layout Redesign

**Date:** 2026-05-12
**Scope:** `kismet/agent/tools/renderer.py`, `kismet/agent/tools/divine.py`

## Problem

三個顯示區塊都用手動字串拼接 + 硬編碼 padding：

1. **`show_divination_animation`** — 只有 2 個靜態 frame；牌名寫死（`FOOL/WHEEL/TOWER`）
2. **`show_mining_start` 祭壇動畫** — `🔥` emoji 寬度導致框線偏移
3. **`show_success` 誠心敬意報告** — 數字長度不一致時右框線歪掉

改用 Rich 的 layout 系統（`Panel`、`Table`、`Columns`），讓 Rich 的 `wcwidth` 計算處理 emoji 和中文寬度。

---

## 1. 塔羅牌動畫（`show_divination_animation`）

### 8-frame 序列（~3.75s）

| Frame | Duration | Description |
|-------|----------|-------------|
| F1 | 0.30s | 星塵聚集：`· · · · · · · · · · · ·`（muted） |
| F2 | 0.30s | 能量浮現：`✦ · ✦ · ✦ · ✦ · ✦ · ✦`（purple） |
| F3 | 0.35s | 光芒大放：`★  ·  ★  ·  ★  ·  ★`（gold） |
| F4 | 0.40s | 牌陣成形：三張 Panel 出現，牌面 `░░░`（face-down） |
| F5 | 0.40s | 能量消散：牌面變 `▓▓▓`（翻轉中，gold border） |
| F6 | 0.50s | 第一張揭示（過去），其餘仍 `▓▓▓` |
| F7 | 0.50s | 第二張揭示（現在），第三仍 `▓▓▓` |
| F8 | 1.00s | 第三張揭示（未來）＋ hash 行（含吉凶標記） |

### 牌面格式

使用 `Panel` + `Columns`。Rich 自動處理 emoji / 中文寬度。

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│    🌕    │  │    💀    │  │  命運之輪 │   ← 長名自動撐寬
│   月亮   │  │   死神   │  │    ☸️    │
└──────────┘  └──────────┘  └──────────┘
   逆位           正位           正位
   過去           現在           未來
```

- 牌框內：emoji（上）+ 中文牌名（下），用 `Align.center`
- 牌框外：正/逆位 + 過去/現在/未來（Rich `Text` 行）

### Three-card draw

新增 `draw_three_tarot_cards(hash_str) -> list[tuple[str, str]]`。
第一張與現有 `draw_tarot_card()` 相同，不影響 LLM 邏輯。

### Emoji & 中文名稱 mapping（新增至 `renderer.py`）

```python
_TAROT_ZH = {
    "The Fool": "愚者", "The Magician": "魔術師",
    "The High Priestess": "女祭司", "The Empress": "皇后",
    "The Emperor": "皇帝", "The Hierophant": "教皇",
    "The Lovers": "戀人", "The Chariot": "戰車",
    "Strength": "力量", "The Hermit": "隱者",
    "Wheel of Fortune": "命運之輪", "Justice": "正義",
    "The Hanged Man": "倒吊人", "Death": "死神",
    "Temperance": "節制", "The Devil": "惡魔",
    "The Tower": "高塔", "The Star": "星星",
    "The Moon": "月亮", "The Sun": "太陽",
    "Judgement": "審判", "The World": "世界",
}

_TAROT_EMOJI = {
    "The Fool": "🃏", "The Magician": "🪄",
    "The High Priestess": "🔮", "The Empress": "⚜️",
    "The Emperor": "👑", "The Hierophant": "⛪",
    "The Lovers": "💕", "The Chariot": "🏇",
    "Strength": "🦁", "The Hermit": "🕯️",
    "Wheel of Fortune": "☸️", "Justice": "⚖️",
    "The Hanged Man": "🙃", "Death": "💀",
    "Temperance": "🫗", "The Devil": "😈",
    "The Tower": "🗼", "The Star": "🌟",
    "The Moon": "🌕", "The Sun": "☀️",
    "Judgement": "📯", "The World": "🌍",
}
```

---

## 2. Token 祭壇動畫（`show_mining_start` / `_animate_altar`）

### 現狀問題

`_ALTAR_BODY` 中的 `🔥` 造成 `|________________________|` 邊框偏移，因為 `🔥` = 2 display col 但字串 padding 沒有補償。

### 新設計

- **Header box**（`逆天改運中`）→ Rich `Panel(title="⚒ 逆天改運中 ⚒", style=PURPLE)`
- **祭壇本體**（altar art + flames）→ 移除手動 `|______|` 框線，改用 `Panel` 包住祭壇文字內容，由 Rich 畫框；`🔥` 留在 Panel 內部作為內容，Rich 自動處理寬度
- **四幀火焰動畫**（`_ALTAR_FLAMES`）→ 保留邏輯，但內容放進 `Panel.renderable` 讓 Rich 管框線
- `_altar_content()` 回傳一個 Rich `renderable`（而非 markup 字串），由 `live.update()` 接收

---

## 3. 誠心敬意報告（`show_success`）

### 現狀問題

右框線靠手動計算空格對齊，數字長度（token 數、USD 金額）變動時就歪掉。

### 新設計

用 `Table`（兩欄：label + value）放進 `Panel`：

```
╭──────── 誠心敬意報告 ────────╮
│ 改運嘗試次數   12 / 100      │
│ 燃燒 Token     4,821         │
│ 花費誠意       $0.0231 USD 💸│
│ 花錢消災，物有所值            │
╰──────────────────────────────╯
```

- `Table(show_header=False, box=None, padding=(0,1))` 兩欄
- 整個 Table 包進 `Panel(title="誠心敬意報告", style=PURPLE)`
- Rich 自動計算欄寬，右框線永遠對齊

---

## Code Changes Summary

### `divine.py`
- 新增 `draw_three_tarot_cards(hash_str) -> list[tuple[str, str]]`

### `renderer.py`
- 新增 `_TAROT_ZH`, `_TAROT_EMOJI`
- 移除 `_tarot_card_row()`, `_ALTAR_HEADER`, `_ALTAR_BODY`, `_ALTAR_FLAMES` 字串常數
- 新增 `_make_card_panel(emoji, name, state) -> Panel` helper
- 重寫 `show_divination_animation()` — 8-frame 序列，用 `Columns`
- 重寫 `_altar_content()` — 回傳 Rich renderable
- 重寫 `show_success()` 的報告區塊 — 用 `Table` + `Panel`

## Out of Scope

- `DivinationResult` 資料結構不改
- LLM prompt 不改
- `show_divination_result` / `show_committed` / `show_celebration` 不改
- `show_blessing` 的祈福壇不在本次範圍
