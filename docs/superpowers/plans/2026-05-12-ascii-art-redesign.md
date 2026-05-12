# ASCII Art Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the simple ASCII art in `show_blessing()` and `show_exorcism()` with 15-line 符籙卷軸式 designs featuring inner 八卦 rows.

**Architecture:** Both functions get a new `scroll_art` / `art` variable built with `Text.from_markup()`. The rest of each function (Panel wrapper, stats, title) stays unchanged. No new files, no new helpers — edit in place.

**Tech Stack:** Python, Rich (`Text.from_markup`, `Group`, `Align.center`, `Panel`)

---

## File Map

| File | Change |
|------|--------|
| `kismet/agent/tools/renderer.py` | Modify `show_blessing()` lines 527–534 and `show_exorcism()` lines 549–556 |

---

## Design Reference

All content lines must be **exactly 27 display columns wide** (the inner content between the `║  ║` spindles). Chinese characters = 2 columns, ASCII/trigrams = 1 column.

```
╔══╦═══════════════════════════╦══╗   ← outer width 35 = 4+27+4
║  ║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║  ║   ← seal bar: 27 ▓
╠══╬═══════════════════════════╬══╣
║  ║  ☰  ☱  ☲  ☳  ☴  ☵  ☶  ☷   ║  ║   ← bagua top
║  ║  ─────────────────────────║  ║   ← separator (25 dashes)
║  ║  ✦    奉  天  承  運  ✦    ║  ║   ← title
║  ║                           ║  ║   ← empty (27 spaces)
║  ║  🙏   祈  福  法  壇  🙏  ║  ║   ← main art
║  ║        ☯    ☰    ☯        ║  ║   ← trigrams (8+1+4+1+4+1+8=27)
║  ║  業  力  化  解  進  行   ║  ║   ← subtitle
║  ║  ─────────────────────────║  ║   ← separator
║  ║  ☷  ☶  ☵  ☴  ☳  ☲  ☱  ☰   ║  ║   ← bagua bottom
╠══╬═══════════════════════════╬══╣
║  ║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║  ║   ← seal bar: 27 ▓
╚══╩═══════════════════════════╩══╝
```

---

## Task 1: Replace 祈福 ASCII art

**Files:**
- Modify: `kismet/agent/tools/renderer.py:527-534`

- [ ] **Step 1: Replace `candle_art` in `show_blessing()`**

Open `kismet/agent/tools/renderer.py`. Find `show_blessing()` (line 524). Replace the `candle_art = Text.from_markup(...)` block (currently 5 lines) with:

```python
    scroll_art = Text.from_markup(
        f"[{GOLD}]╔══╦═══════════════════════════╦══╗[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]╠══╬═══════════════════════════╬══╣[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]  ☰  ☱  ☲  ☳  ☴  ☵  ☶  ☷   [/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]  ─────────────────────────[/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]║  ║  ✦    奉  天  承  運  ✦    ║  ║[/]\n"
        f"[{GOLD}]║  ║                           ║  ║[/]\n"
        f"[{GOLD}]║  ║  🙏   祈  福  法  壇  🙏  ║  ║[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]        ☯    ☰    ☯        [/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]║  ║  業  力  化  解  進  行   ║  ║[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]  ─────────────────────────[/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]  ☷  ☶  ☵  ☴  ☳  ☲  ☱  ☰   [/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]╠══╬═══════════════════════════╬══╣[/]\n"
        f"[{GOLD}]║  ║[/][{PURPLE}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/][{GOLD}]║  ║[/]\n"
        f"[{GOLD}]╚══╩═══════════════════════════╩══╝[/]"
    )
```

Then change the one reference from `candle_art` → `scroll_art` in the `Group(...)` call below it:

```python
    panel = Panel(
        Group(Align.center(scroll_art), Text(""), stats),
        ...
    )
```

- [ ] **Step 2: Visual test**

```bash
uv run python -c "
from kismet.agent.tools.renderer import RendererTool
from types import SimpleNamespace
r = RendererTool()
session = SimpleNamespace(total_cost_usd=0.0042, total_input_tokens=1000, total_output_tokens=500, mine_attempts=3)
r.show_blessing(session)
"
```

Verify:
- 15-line scroll art appears, centered in the terminal
- Outer frame and text are gold (`#fbbf24`)
- Seal bars, bagua rows, separators, and ☯ ☰ ☯ trigrams are purple (`#c084fc`)
- All box-drawing lines are the same width (no ragged edges)
- If any line is misaligned, adjust leading/trailing spaces in that line to compensate — Chinese chars are 2 columns wide, ASCII/trigrams are 1 column wide

- [ ] **Step 3: Commit**

```bash
git add kismet/agent/tools/renderer.py
git commit -m "feat: redesign 祈福 ASCII art — 符籙卷軸式 with 八卦 rows"
```

---

## Task 2: Replace 驅魔 ASCII art

**Files:**
- Modify: `kismet/agent/tools/renderer.py:549-556`

- [ ] **Step 1: Replace `art` in `show_exorcism()`**

Find `show_exorcism()` (line 548). Replace the `art = Text.from_markup(...)` block with:

```python
    DARK_RED = "#7f1d1d"
    art = Text.from_markup(
        f"[{RED}]╔══╦═══════════════════════════╦══╗[/]\n"
        f"[{RED}]║  ║[/][{DARK_RED}]███████████████████████████[/][{RED}]║  ║[/]\n"
        f"[{RED}]╠══╬═══════════════════════════╬══╣[/]\n"
        f"[{RED}]║  ║  ☰  ☱  ☲  ☳  ☴  ☵  ☶  ☷   ║  ║[/]\n"
        f"[{RED}]║  ║  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔║  ║[/]\n"
        f"[{RED}]║  ║  ☠    凶  咒  解  除  ☠    ║  ║[/]\n"
        f"[{RED}]║  ║                           ║  ║[/]\n"
        f"[{RED}]║  ║  ⚡   驅  魔  法  壇  ⚡  ║  ║[/]\n"
        f"[{RED}]║  ║        ☠    ☳    ☠        ║  ║[/]\n"
        f"[{RED}]║  ║  厄  運  消  散  進  行   ║  ║[/]\n"
        f"[{RED}]║  ║  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔║  ║[/]\n"
        f"[{RED}]║  ║  ☷  ☶  ☵  ☴  ☳  ☲  ☱  ☰   ║  ║[/]\n"
        f"[{RED}]╠══╬═══════════════════════════╬══╣[/]\n"
        f"[{RED}]║  ║[/][{DARK_RED}]███████████████████████████[/][{RED}]║  ║[/]\n"
        f"[{RED}]╚══╩═══════════════════════════╩══╝[/]"
    )
```

Note: `DARK_RED` is a local variable defined at the top of the function body — do **not** add it as a module-level constant.

- [ ] **Step 2: Visual test**

```bash
uv run python -c "
from kismet.agent.tools.renderer import RendererTool
r = RendererTool()
r.show_exorcism()
"
```

Verify:
- 15-line scroll art appears, centered in the terminal
- Everything is blood red (`#f87171`)
- Seal bars (████) are dark red (`#7f1d1d`)
- `▔` separators (upper block) visually contrast with the `─` dashes in the blessing version
- ☳ (震卦) is visible in the center trigram row
- If any line is misaligned, adjust spacing — same rule as Task 1

- [ ] **Step 3: Commit**

```bash
git add kismet/agent/tools/renderer.py
git commit -m "feat: redesign 驅魔 ASCII art — 符籙卷軸式 with 八卦 rows"
```
