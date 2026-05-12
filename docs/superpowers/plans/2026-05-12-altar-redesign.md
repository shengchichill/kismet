# Altar & Report Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain-box altar animation with an incense-stick + rising-smoke ASCII art that cycles through 4 color schemes, and shrink the 誠心敬意報告 panel to content width.

**Architecture:** All changes are in `kismet/agent/tools/renderer.py`. Remove `_ALTAR_FLAME_FRAMES`, add `_smoke_row()` helper and `_ALTAR_FRAME_DATA` list, rewrite `_altar_content()` to produce ASCII art as a `Text` object, add `expand=False` to the report `Panel`. The return type of `_altar_content()` stays `Group` so existing call sites are untouched.

**Tech Stack:** Python, Rich (`Text`, `Align`, `Group`, `Panel`, `Console`)

---

### Task 1: Rewrite altar animation — incense sticks + rising smoke

**Files:**
- Modify: `kismet/agent/tools/renderer.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_renderer.py`:

```python
def test_smoke_row_is_33_chars_wide():
    from kismet.agent.tools.renderer import _smoke_row
    for shift in range(4):
        assert len(_smoke_row(shift)) == 33, f"shift={shift} produced wrong width"


def test_smoke_row_shift_moves_first_wisp_left():
    from kismet.agent.tools.renderer import _smoke_row
    row0 = _smoke_row(0)
    row1 = _smoke_row(1)
    assert row1.index("≀") == row0.index("≀") - 1


def test_altar_frame_data_has_4_frames():
    from kismet.agent.tools.renderer import _ALTAR_FRAME_DATA
    assert len(_ALTAR_FRAME_DATA) == 4


def test_altar_frame_smoke_row_counts():
    from kismet.agent.tools.renderer import _ALTAR_FRAME_DATA
    for i, (_, shades, _, _) in enumerate(_ALTAR_FRAME_DATA):
        assert len(shades) == i + 1, f"Frame {i} should have {i+1} smoke row(s)"
```

- [ ] **Step 2: Run — expect FAIL**

```
.venv\Scripts\pytest tests/test_renderer.py::test_smoke_row_is_33_chars_wide -v
```

Expected: `ImportError` or `FAILED` (symbol not defined yet).

- [ ] **Step 3: Implement the new altar constants and helper**

In `kismet/agent/tools/renderer.py`, **replace** the `_ALTAR_FLAME_FRAMES` block and add new constants. Find this block (around line 77):

```python
_ALTAR_FLAME_FRAMES: list[str] = [
    f"[{MUTED}]~   ~  ~    ~  ~[/]",
    f"[{GOLD}]~ ~ ~  ~~ ~ ~ ~  ~[/]",
    f"[{RED}]~~ ~ ~~  ~~ ~ ~~  ~[/]",
    f"[{PINK}]*  ~ ~~  ~ * ~~ ~ *[/]",
]
```

Replace it with:

```python
# ── Incense altar ASCII components (all 33 terminal columns wide) ──────────
_INCENSE_TIPS   = "      *    *    *    *    *      "
_INCENSE_STICKS = "      │    │    │    │    │      "
_ALTAR_TOP      = "╔═════╧════╧════╧════╧════╧═════╗"
_ALTAR_COL_SP   = "║ ▐█▌                       ▐█▌ ║"
_ALTAR_BODY     = "║ ▐█▌ 🔥 焚燒 Token 祭壇 🔥 ▐█▌ ║"
_ALTAR_SEP      = "╠═══════════════════════════════╣"
_ALTAR_ASH_N    = "║ " + "░ " * 15 + "║"        # frames 0-1: static ash
_ALTAR_ASH_R    = "║ ░ · ░ ░ · ░ ░ · ░ ░ · ░ ░ · ░ ║"  # frame 2: red embers
_ALTAR_ASH_P    = "║ · ░ · ░ · ░ · ░ · ░ · ░ · ░ · ║"  # frame 3: purple embers
_ALTAR_BOT      = "╚═══════════════════════════════╝"
_ALTAR_BASE     = "    ████    ████    ████    ████  "
_ORANGE         = "#fb8c00"   # incense stick colour
_INCENSE_TIP_C  = "#ef9a9a"   # incense tip colour
_BROWN          = "#4e342e"   # base stone colour
_ASH_DIM        = "#424242"   # dim ash colour (frames 0-1)

# Each entry: (altar_border_color, smoke_shades[top→bottom], ash_line, ash_color)
# smoke_shades: darkest at index 0 (top / oldest smoke), primary at last index (bottom / fresh)
_ALTAR_FRAME_DATA: list[tuple[str, list[str], str, str]] = [
    ("#607d8b", ["#607d8b"],                                           _ALTAR_ASH_N, _ASH_DIM),
    ("#ffd54f", ["#f9a825", "#ffd54f"],                                _ALTAR_ASH_N, _ASH_DIM),
    ("#ef5350", ["#b71c1c", "#e53935", "#ef5350"],                     _ALTAR_ASH_R, "#ef5350"),
    ("#ce93d8", ["#4a148c", "#7b1fa2", "#ab47bc", "#ce93d8"],          _ALTAR_ASH_P, "#ce93d8"),
]


def _smoke_row(shift: int) -> str:
    """One 33-char row of incense smoke; shift > 0 moves wisps left (upward drift)."""
    return " " * (6 - shift) + "≀" + "    ≀" * 4 + " " * (6 + shift)
```

- [ ] **Step 4: Rewrite `_altar_content()`**

Find the existing `_altar_content` method (around line 176) and replace it entirely:

```python
def _altar_content(self) -> Group:
    altar_color, smoke_shades, ash_line, ash_color = (
        _ALTAR_FRAME_DATA[self._altar_frame % len(_ALTAR_FRAME_DATA)]
    )

    lines: list[str] = []

    # Smoke rows — more rows per frame, drifting left as they rise
    for i, shade in enumerate(smoke_shades):
        shift = len(smoke_shades) - 1 - i  # bottom row = shift 0 (nearest tips)
        lines.append(f"[{shade}]{_smoke_row(shift)}[/]")

    # Incense tips and sticks (fixed colours)
    lines.append(f"[{_INCENSE_TIP_C}]{_INCENSE_TIPS}[/]")
    lines.append(f"[{_ORANGE}]{_INCENSE_STICKS}[/]")

    # Altar box
    for part in [_ALTAR_TOP, _ALTAR_COL_SP, _ALTAR_BODY, _ALTAR_COL_SP, _ALTAR_SEP]:
        lines.append(f"[{altar_color}]{part}[/]")

    # Ash layer
    lines.append(f"[{ash_color}]{ash_line}[/]")

    # Bottom and base
    lines.append(f"[{altar_color}]{_ALTAR_BOT}[/]")
    lines.append(f"[{_BROWN}]{_ALTAR_BASE}[/]")

    altar_art = Align.center(Text.from_markup("\n".join(lines)))
    header = Panel(
        Align.center("正在燃燒 Token 祭天，請耐心等候..."),
        title=f"[{GOLD}]⚒ 逆天改運中 ⚒[/]",
        border_style=PURPLE,
        expand=False,
    )
    return Group(header, altar_art)
```

- [ ] **Step 5: Run all tests — expect PASS**

```
.venv\Scripts\pytest tests/test_renderer.py -v
```

Expected: all tests green, including the 4 new ones and all pre-existing renderer tests.

- [ ] **Step 6: Delete the temp preview file**

```
del _preview_altar.py
```

- [ ] **Step 7: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git rm _preview_altar.py
git commit -m "feat: redesign altar with incense sticks and rising smoke animation"
```

---

### Task 2: Shrink 誠心敬意報告 panel to content width

**Files:**
- Modify: `kismet/agent/tools/renderer.py:434`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_renderer.py`:

```python
def test_show_success_report_not_full_width():
    import re
    from unittest.mock import MagicMock
    from kismet.agent.tools.renderer import RendererTool

    renderer = RendererTool()
    output = StringIO()
    renderer.console = Console(file=output, force_terminal=True, width=200, no_color=True)

    session = MagicMock()
    session.total_cost_usd = 0.01
    session.original_predicted_hash = "abc"
    session.predicted_hash = "def"
    session.mine_attempts = 5
    session.k_value = 50
    session.total_input_tokens = 100
    session.total_output_tokens = 50

    renderer.show_success(session, max_attempts=100, new_k_value=75, lucky_match="a")

    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    plain = ansi_escape.sub("", output.getvalue())
    report_lines = [
        l for l in plain.splitlines()
        if "改運嘗試次數" in l or "燃燒 Token" in l or "花費誠意" in l
    ]
    assert report_lines, "Report rows not found in output"
    for line in report_lines:
        assert len(line) < 100, f"Report line too wide ({len(line)}): {line!r}"
```

- [ ] **Step 2: Run — expect FAIL**

```
.venv\Scripts\pytest tests/test_renderer.py::test_show_success_report_not_full_width -v
```

Expected: `FAILED` — lines are ~200 chars wide without `expand=False`.

- [ ] **Step 3: Add `expand=False` to the report Panel**

In `kismet/agent/tools/renderer.py` around line 434, change:

```python
self.console.print(Panel(report_table, title=f"[{PURPLE}]誠心敬意報告[/]", border_style=PURPLE))
```

to:

```python
self.console.print(Panel(report_table, title=f"[{PURPLE}]誠心敬意報告[/]", border_style=PURPLE, expand=False))
```

- [ ] **Step 4: Run all tests — expect PASS**

```
.venv\Scripts\pytest tests/test_renderer.py -v
```

Expected: all tests green.

- [ ] **Step 5: Commit**

```bash
git add kismet/agent/tools/renderer.py tests/test_renderer.py
git commit -m "fix: shrink 誠心敬意報告 panel to content width (expand=False)"
```
