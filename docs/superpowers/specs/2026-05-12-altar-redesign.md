# Altar & Report Panel Redesign

## Summary

Redesign the `token 焚燒祭壇` animation and `誠心敬意報告` panel to be:
1. More visually altar-like (incense sticks + rising smoke instead of a plain box)
2. Content-width instead of full-terminal-width

---

## Altar Design

### Structure (top → bottom)

```
      ≀    ≀    ≀    ≀    ≀        ← smoke rows (frame-dependent count)
      *    *    *    *    *        ← incense tips (fixed pink #ef9a9a)
      │    │    │    │    │        ← incense sticks (fixed orange #fb8c00)
╔═════╧════╧════╧════╧════╧═════╗
║ ▐█▌                       ▐█▌ ║  ← decorative columns
║ ▐█▌ 🔥 焚燒 Token 祭壇 🔥 ▐█▌ ║  ← body (color cycles per frame)
║ ▐█▌                       ▐█▌ ║
╠═══════════════════════════════╣
║ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ░ ║  ← ash layer (pattern varies per frame)
╚═══════════════════════════════╝
    ████    ████    ████    ████   ← base stones (fixed brown #4e342e)
```

5 incense sticks. Box is 33 chars wide (fits ~40% of an 80-col terminal, centered).

### Animation — 4 frames, cycling

| Frame | Name   | Smoke rows | Altar/smoke color | Ash pattern |
|-------|--------|------------|-------------------|-------------|
| 1     | 微煙   | 1          | `#607d8b` (grey)  | `░` static  |
| 2     | 金焰   | 2          | `#ffd54f` (gold)  | `░` static  |
| 3     | 烈焰   | 3          | `#ef5350` (red)   | `░ ·` jump  |
| 4     | 鬼火   | 4          | `#ce93d8` (purple)| `· ░` jump  |

**Smoke rising effect:** each frame adds one more row of `≀` above the previous.
Each row shifts 1 char left relative to the row below to simulate drift.
Within a single frame, the bottom row (nearest the tips) uses the frame's primary
color (brightest). Each row above uses a progressively darker shade of the same
hue, simulating the smoke dissipating as it rises.

**Fixed elements (never change color):**
- Incense tips `*` → `#ef9a9a` (pink)
- Incense sticks `│` → `#fb8c00` (orange)
- Base stones `████` → `#4e342e` (brown)
- Ash base character `░` → `#424242` (dark grey)

### Implementation approach

Replace the current two-nested-Panel approach in `_altar_content()` with a
single multi-line `Text` object rendered via `Align.center()`. No Rich Panel
wrapping the altar — the ASCII art box-drawing characters form the border.

Keep the header Panel (`⚒ 逆天改運中 ⚒`) above the altar, but add `expand=False`
so it shrinks to content width.

The `_ALTAR_FLAME_FRAMES` list becomes a list of frame dicts (or a frame index
drives a `_build_altar_frame(n)` function that assembles the full Text).

---

## 誠心敬意報告 Panel

Currently renders as a full-width Panel. Change: add `expand=False` to the
`Panel(report_table, ...)` call. Rich will size it to the table's natural width.
No other changes needed.

---

## Files Changed

- `kismet/agent/tools/renderer.py` — all changes are here:
  - `_ALTAR_FLAME_FRAMES` → new frame data structure
  - `_altar_content()` → rewritten to produce incense + smoke ASCII art
  - `show_report()` → add `expand=False` to Panel
