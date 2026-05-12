# Rich Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all manual ASCII string-padding in the divination animation, mining altar, and success report with Rich `Panel`/`Table`/`Group` layouts that handle emoji and CJK character widths automatically.

**Architecture:** Three display functions in `renderer.py` are rewritten to use Rich renderables instead of markup strings with hardcoded spaces. A new helper `draw_three_tarot_cards` in `divine.py` provides deterministic 3-card draws. All new display helpers are module-level functions (no `self` needed).

**Tech Stack:** Python 3.10+, Rich ≥ 13.0 (`Panel`, `Table`, `Columns`, `Group`, `Align`), pytest

---

## File Map

| File | Change |
|------|--------|
| `kismet/agent/tools/divine.py` | Add `draw_three_tarot_cards()` |
| `kismet/agent/tools/renderer.py` | Add `_TAROT_ZH`, `_TAROT_EMOJI`; add `_make_card_panel()`, `_make_spread_table()`; remove `_tarot_card_row()`, `_ALTAR_HEADER`, `_ALTAR_BODY`, `_ALTAR_FLAMES`; rewrite `show_divination_animation()`, `_altar_content()`, `_animate_altar()`, `show_mining_start()`, `show_mining_end()`, `show_success()` |
| `tests/test_divine.py` | Add 2 tests for `draw_three_tarot_cards` |
| `tests/test_renderer.py` | New file — tests for `_make_card_panel`, `_make_spread_table`, smoke tests for animations, `show_success` report |

---

## Task 1: `draw_three_tarot_cards` in divine.py

**Files:**
- Modify: `kismet/agent/tools/divine.py`
- Modify: `tests/test_divine.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_divine.py`:

```python
from kismet.agent.tools.divine import draw_tarot_card, draw_three_tarot_cards


def test_draw_three_tarot_cards_returns_three():
    cards = draw_three_tarot_cards("bf44a92cafe2f8")
    assert len(cards) == 3
    for card, pos in cards:
        assert isinstance(card, str)
        assert pos in ("正位", "逆位")


def test_draw_three_tarot_cards_first_matches_single():
    hash_str = "bf44a92cafe2f8"
    first_card, first_pos = draw_three_tarot_cards(hash_str)[0]
    single_card, single_pos = draw_tarot_card(hash_str)
    assert first_card == single_card
    assert first_pos == single_pos


def test_draw_three_tarot_cards_deterministic():
    h = "3f7a404d8c2bdeadbeef"
    assert draw_three_tarot_cards(h) == draw_three_tarot_cards(h)
```

- [ ] **Step 2: Run to verify they fail**

```
uv run pytest tests/test_divine.py::test_draw_three_tarot_cards_returns_three -v
```

Expected: `ImportError: cannot import name 'draw_three_tarot_cards'`

- [ ] **Step 3: Add the function to divine.py**

In `kismet/agent/tools/divine.py`, after `draw_tarot_card`:

```python
def draw_three_tarot_cards(hash_str: str) -> list[tuple[str, str]]:
    """Draw three Major Arcana cards deterministically. First card matches draw_tarot_card."""
    seed = int(hash_str, 16)
    rng = random.Random(seed)
    return [(rng.choice(_MAJOR_ARCANA), rng.choice(["正位", "逆位"])) for _ in range(3)]
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/test_divine.py -v
```

Expected: all tests PASS (including pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add kismet/agent/tools/divine.py tests/test_divine.py
git commit -m "feat: add draw_three_tarot_cards for deterministic 3-card spread"
```

---

## Task 2: Display data + card panel helpers in renderer.py

**Files:**
- Modify: `kismet/agent/tools/renderer.py`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_renderer.py`:

```python
from io import StringIO
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def test_tarot_zh_has_all_22_cards():
    from kismet.agent.tools.renderer import _TAROT_ZH
    from kismet.agent.tools.divine import _MAJOR_ARCANA
    for card in _MAJOR_ARCANA:
        assert card in _TAROT_ZH, f"Missing Chinese name for: {card}"


def test_tarot_emoji_has_all_22_cards():
    from kismet.agent.tools.renderer import _TAROT_EMOJI
    from kismet.agent.tools.divine import _MAJOR_ARCANA
    for card in _MAJOR_ARCANA:
        assert card in _TAROT_EMOJI, f"Missing emoji for: {card}"


def test_make_card_panel_returns_panel():
    from kismet.agent.tools.renderer import _make_card_panel
    for state in ("facedown", "flipping", "revealed"):
        result = _make_card_panel("🌕", "月亮", "正位", state)
        assert isinstance(result, Panel)


def test_make_card_panel_renders_without_error():
    from kismet.agent.tools.renderer import _make_card_panel
    console = _make_console()
    for state in ("facedown", "flipping", "revealed"):
        panel = _make_card_panel("💀", "死神", "逆位", state)
        console.print(panel)  # must not raise


def test_make_spread_table_returns_table():
    from kismet.agent.tools.renderer import _make_spread_table
    card_data = [("🌕", "月亮", "正位"), ("💀", "死神", "逆位"), ("☀️", "太陽", "正位")]
    result = _make_spread_table(card_data, revealed={0, 1, 2}, flipping=set())
    assert isinstance(result, Table)


def test_make_spread_table_renders_without_error():
    from kismet.agent.tools.renderer import _make_spread_table
    console = _make_console()
    card_data = [("🌕", "月亮", "正位"), ("💀", "死神", "逆位"), ("☀️", "太陽", "正位")]
    for revealed, flipping in [
        (set(), set()),
        (set(), {0, 1, 2}),
        ({0}, {1, 2}),
        ({0, 1}, {2}),
        ({0, 1, 2}, set()),
    ]:
        table = _make_spread_table(card_data, revealed, flipping)
        console.print(table)
```

- [ ] **Step 2: Run to verify they fail**

```
uv run pytest tests/test_renderer.py -v
```

Expected: `ImportError: cannot import name '_TAROT_ZH'`

- [ ] **Step 3: Add `_TAROT_ZH`, `_TAROT_EMOJI` to renderer.py**

Add after the colour constants at the top of `kismet/agent/tools/renderer.py`:

```python
_TAROT_ZH: dict[str, str] = {
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

_TAROT_EMOJI: dict[str, str] = {
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

- [ ] **Step 4: Add imports to renderer.py**

Replace the existing Rich import block with:

```python
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text
```

- [ ] **Step 5: Add `_make_card_panel` and `_make_spread_table` to renderer.py**

Add these module-level functions after the colour constants and dict definitions. Remove the old `_tarot_card_row` function entirely.

```python
def _make_card_panel(emoji: str, name: str, pos: str, state: str) -> Panel:
    """Return a Rich Panel for one tarot card in the given display state."""
    if state == "facedown":
        content = Align.center("░░░", vertical="middle")
        border_style = PURPLE
    elif state == "flipping":
        content = Align.center("▓▓▓", vertical="middle")
        border_style = GOLD
    else:
        content = Align.center(
            Text.from_markup(f"{emoji}\n[{CYAN}]{name}[/]\n[{MUTED}]{pos}[/]"),
            vertical="middle",
        )
        border_style = CYAN
    return Panel(content, border_style=border_style, padding=(1, 2))


def _make_spread_table(
    card_data: list[tuple[str, str, str]],
    revealed: set[int],
    flipping: set[int],
) -> Table:
    """Return a 3-column Table with card panels + spread labels.

    card_data: list of (emoji, zh_name, position) for each of the 3 cards.
    revealed: indices of cards to show face-up.
    flipping: indices of cards to show mid-flip (▓▓▓).
    """
    table = Table.grid(padding=(0, 3))
    for _ in range(3):
        table.add_column(justify="center")

    panels, pos_texts = [], []
    for i, (emoji, name, pos) in enumerate(card_data):
        if i in revealed:
            panels.append(_make_card_panel(emoji, name, pos, "revealed"))
            pos_texts.append(Text(pos, style=MUTED))
        elif i in flipping:
            panels.append(_make_card_panel(emoji, name, pos, "flipping"))
            pos_texts.append(Text(""))
        else:
            panels.append(_make_card_panel(emoji, name, pos, "facedown"))
            pos_texts.append(Text(""))

    table.add_row(*panels)
    table.add_row(*pos_texts)
    table.add_row(
        Text("過去", style=MUTED),
        Text("現在", style=MUTED),
        Text("未來", style=MUTED),
    )
    return table
```

- [ ] **Step 6: Run tests to verify they pass**

```
uv run pytest tests/test_renderer.py -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git commit -m "feat: add tarot display data and Rich card panel helpers"
```

---

## Task 3: Rewrite `show_divination_animation` (8-frame sequence)

**Files:**
- Modify: `kismet/agent/tools/renderer.py`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_renderer.py`:

```python
from unittest.mock import patch


@patch("kismet.agent.tools.renderer.time.sleep")
def test_show_divination_animation_8_frames(mock_sleep):
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    renderer.show_divination_animation("bf44a92cafe2f8", lucky_match="cafe")
    assert mock_sleep.call_count == 8


@patch("kismet.agent.tools.renderer.time.sleep")
def test_show_divination_animation_unlucky(mock_sleep):
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    renderer.show_divination_animation("3f7a404deadbeef", unlucky_match="dead")
    assert mock_sleep.call_count == 8
```

- [ ] **Step 2: Run to verify they fail**

```
uv run pytest tests/test_renderer.py::test_show_divination_animation_8_frames -v
```

Expected: FAIL — `mock_sleep.call_count` is 2 (old 2-frame implementation)

- [ ] **Step 3: Rewrite `show_divination_animation` in renderer.py**

Replace the entire `show_divination_animation` method with:

```python
def show_divination_animation(
    self,
    hash_str: str,
    lucky_match: Optional[str] = None,
    unlucky_match: Optional[str] = None,
) -> None:
    from kismet.agent.tools.divine import draw_three_tarot_cards

    cards = draw_three_tarot_cards(hash_str)
    card_data = [
        (_TAROT_EMOJI.get(c, "✦"), _TAROT_ZH.get(c, c), pos)
        for c, pos in cards
    ]

    header = f"[{PURPLE}]  ✦ 命盤展開中，牌語浮現於宇宙之間... ✦[/]"
    header_final = f"[{PURPLE}]  ✦ 命盤展開，天機已現 ✦[/]"
    hash_sensing = f"  [{MUTED}]hash: [{CYAN}]{hash_str}[/]   感應中 ⟳[/]"

    def spread(revealed: set[int], flipping: set[int]):
        return _make_spread_table(card_data, revealed, flipping)

    with Live(console=self.console, refresh_per_second=8) as live:
        # F1: 星塵聚集
        live.update(Group(
            Text.from_markup(header), Text(""),
            Text.from_markup(f"  [{MUTED}]· · · · · · · · · · · · · · · · ·[/]"),
            Text(""), Text.from_markup(hash_sensing),
        ))
        time.sleep(0.30)

        # F2: 能量浮現
        live.update(Group(
            Text.from_markup(header), Text(""),
            Text.from_markup(f"  [{PURPLE}]✦ · ✦ · ✦ · ✦ · ✦ · ✦ · ✦ · ✦[/]"),
            Text(""), Text.from_markup(hash_sensing),
        ))
        time.sleep(0.30)

        # F3: 光芒大放
        live.update(Group(
            Text.from_markup(header), Text(""),
            Text.from_markup(f"  [{GOLD}]★  ·  ★  ·  ★  ·  ★  ·  ★  ·  ★[/]"),
            Text(""), Text.from_markup(hash_sensing),
        ))
        time.sleep(0.35)

        # F4: 牌陣成形 (all facedown)
        live.update(Group(
            Text.from_markup(header), Text(""),
            spread(set(), set()),
            Text.from_markup(hash_sensing),
        ))
        time.sleep(0.40)

        # F5: 能量消散 (all flipping)
        live.update(Group(
            Text.from_markup(header), Text(""),
            spread(set(), {0, 1, 2}),
            Text.from_markup(hash_sensing),
        ))
        time.sleep(0.40)

        # F6: 第一張揭示 (過去)
        live.update(Group(
            Text.from_markup(header), Text(""),
            spread({0}, {1, 2}),
            Text.from_markup(hash_sensing),
        ))
        time.sleep(0.50)

        # F7: 第二張揭示 (現在)
        live.update(Group(
            Text.from_markup(header), Text(""),
            spread({0, 1}, {2}),
            Text.from_markup(hash_sensing),
        ))
        time.sleep(0.50)

        # F8: 第三張揭示 (未來) + hash 行
        hash_display = _highlight_hash(
            hash_str, lucky_match=lucky_match, unlucky_match=unlucky_match
        )
        if unlucky_match is not None:
            hash_line = f"  hash: {hash_display}  [{RED}]⚡ 不詳！含 {unlucky_match}[/]"
        elif lucky_match is not None:
            hash_line = f"  hash: {hash_display}  [{GREEN}]✦ 吉兆！含 {lucky_match}[/]"
        else:
            hash_line = f"  hash: {hash_display}"
        live.update(Group(
            Text.from_markup(header_final), Text(""),
            spread({0, 1, 2}, set()),
            Text(""), Text.from_markup(hash_line),
        ))
        time.sleep(1.00)
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/test_renderer.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git commit -m "feat: rewrite show_divination_animation with 8-frame Rich layout"
```

---

## Task 4: Rewrite altar animation with Rich Panel

**Files:**
- Modify: `kismet/agent/tools/renderer.py`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_renderer.py`:

```python
def test_altar_content_returns_renderable():
    from rich.console import Group
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    content = renderer._altar_content()
    assert isinstance(content, Group)


def test_altar_content_renders_without_error():
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    for frame in range(4):
        renderer._altar_frame = frame
        renderer.console.print(renderer._altar_content())
```

- [ ] **Step 2: Run to verify they fail**

```
uv run pytest tests/test_renderer.py::test_altar_content_returns_renderable -v
```

Expected: FAIL — `isinstance(content, Group)` is False (currently returns str)

- [ ] **Step 3: Replace altar string constants and rewrite `_altar_content`**

In `renderer.py`:

**Remove** these module-level constants entirely:
- `_ALTAR_HEADER`
- `_ALTAR_BODY`
- `_ALTAR_FLAMES`

**Add** in their place:

```python
_ALTAR_FLAME_FRAMES: list[str] = [
    f"[{MUTED}]~   ~  ~    ~  ~[/]",
    f"[{GOLD}]~ ~ ~  ~~ ~ ~ ~  ~[/]",
    f"[{RED}]~~ ~ ~~  ~~ ~ ~~  ~[/]",
    f"[{PINK}]*  ~ ~~  ~ * ~~ ~ *[/]",
]
```

**Replace** the `_altar_content` method with:

```python
def _altar_content(self) -> Group:
    flames = _ALTAR_FLAME_FRAMES[self._altar_frame % len(_ALTAR_FLAME_FRAMES)]
    header = Panel(
        Align.center("正在燃燒 Token 祭天，請耐心等候..."),
        title=f"[{GOLD}]⚒ 逆天改運中 ⚒[/]",
        border_style=PURPLE,
    )
    altar = Panel(
        Align.center(
            Text.from_markup(f"[{GOLD}]🔥 焚燒 Token 祭壇 🔥[/]\n\n{flames}")
        ),
        border_style=GOLD,
        padding=(0, 6),
    )
    return Group(header, altar)
```

- [ ] **Step 4: Update `_animate_altar`, `show_mining_start`, `show_mining_end`**

The three methods that use `_altar_content()` currently pass its string result to `live.update(Text.from_markup(...))`. Change them to pass the `Group` directly.

**Replace `_animate_altar`:**

```python
def _animate_altar(self) -> None:
    while not self._altar_stop.is_set():
        self._altar_frame += 1
        live = self._mining_live
        if live is not None:
            altar = self._altar_content()
            content = (
                Group(altar, Text.from_markup("\n".join(self._mining_log)))
                if self._mining_log
                else altar
            )
            try:
                live.update(content)
            except Exception:
                pass
        self._altar_stop.wait(timeout=0.35)
```

**Replace `show_mining_start`** (change only the `live.update` call — the rest is identical):

```python
def show_mining_start(self) -> None:
    self._mining_log.clear()
    self._altar_frame = 0
    self._altar_stop.clear()
    self._mining_live = Live(console=self.console, refresh_per_second=8)
    self._mining_live.start()
    self._mining_live.update(self._altar_content())
    self._altar_thread = threading.Thread(target=self._animate_altar, daemon=True)
    self._altar_thread.start()
```

**Replace `show_mining_end`** (change only the final render call):

```python
def show_mining_end(self) -> None:
    self._altar_stop.set()
    if self._altar_thread:
        self._altar_thread.join(timeout=1.0)
        self._altar_thread = None
    if self._mining_live:
        altar = self._altar_content()
        content = (
            Group(altar, Text.from_markup("\n".join(self._mining_log)))
            if self._mining_log
            else altar
        )
        self._mining_live.update(content)
        self._mining_live.stop()
        self._mining_live = None
```

- [ ] **Step 5: Run tests to verify they pass**

```
uv run pytest tests/test_renderer.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git commit -m "feat: rewrite altar animation with Rich Panel layout"
```

---

## Task 5: Rewrite 誠心敬意報告 with Rich Table + Panel

**Files:**
- Modify: `kismet/agent/tools/renderer.py`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_renderer.py`:

```python
def test_show_success_report_contains_key_fields():
    from unittest.mock import MagicMock
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    output = StringIO()
    renderer.console = Console(file=output, force_terminal=True, width=120)

    session = MagicMock()
    session.total_cost_usd = 0.0231
    session.original_predicted_hash = "abc123deadbeef"
    session.predicted_hash = "def456cafe7890"
    session.mine_attempts = 12
    session.k_value = 15
    session.total_input_tokens = 3000
    session.total_output_tokens = 821

    renderer.show_success(session, max_attempts=100, new_k_value=87, lucky_match="cafe")

    result = output.getvalue()
    assert "改運嘗試次數" in result
    assert "12" in result
    assert "燃燒 Token" in result
    assert "3,821" in result
    assert "花費誠意" in result
    assert "0.0231" in result
```

- [ ] **Step 2: Run to verify test passes already (or fails)**

```
uv run pytest tests/test_renderer.py::test_show_success_report_contains_key_fields -v
```

Note: this test might already pass with the old code. If so, skip to Step 3 directly.

- [ ] **Step 3: Replace the manual box in `show_success` with Rich Table + Panel**

In `show_success`, locate this block (approximately `renderer.py:290–298`):

```python
output += (
    f"\n  [{PURPLE}]┌──────────── 誠心敬意報告 ────────────┐[/]\n"
    f"  [{PURPLE}]│[/]  [{CYAN}]改運嘗試次數  {session.mine_attempts} / {max_attempts}[/]                [{PURPLE}]│[/]\n"
    f"  [{PURPLE}]│[/]  [{CYAN}]燃燒 Token    {session.total_input_tokens + session.total_output_tokens:,}[/]              [{PURPLE}]│[/]\n"
    f"  [{PURPLE}]│[/]  [{GOLD}]花費誠意      {cost_str}  💸[/]       [{PURPLE}]│[/]\n"
    f"  [{PURPLE}]│[/]  [{MUTED}]花錢消災，物有所值[/]               [{PURPLE}]│[/]\n"
    f"  [{PURPLE}]└──────────────────────────────────────┘[/]"
)
self.console.print(output)
```

Replace with:

```python
self.console.print(output)

report_table = Table.grid(padding=(0, 2))
report_table.add_column(style=MUTED)
report_table.add_column()
total_tokens = session.total_input_tokens + session.total_output_tokens
report_table.add_row("改運嘗試次數", f"[{CYAN}]{session.mine_attempts} / {max_attempts}[/]")
report_table.add_row("燃燒 Token", f"[{CYAN}]{total_tokens:,}[/]")
report_table.add_row("花費誠意", f"[{GOLD}]{cost_str}  💸[/]")
report_table.add_row(f"[{MUTED}]花錢消災，物有所值[/]", "")
self.console.print(Panel(report_table, title=f"[{PURPLE}]誠心敬意報告[/]", border_style=PURPLE))
```

**Exact change:** The current code ends with `output += (box); self.console.print(output)`. Remove the entire `output += (... ┌──── 誠心敬意報告 ...)` assignment. `self.console.print(output)` stays — it prints the hash diff and K-value bars. The new `self.console.print(Panel(...))` goes on the line right after it.

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/test_renderer.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run the full test suite**

```
uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git commit -m "feat: rewrite 誠心敬意報告 with Rich Table + Panel for auto-aligned layout"
```
