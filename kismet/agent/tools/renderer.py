import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from kismet.agent.tools.divine import DivinationResult

PINK = "#ff6b9d"
PURPLE = "#c084fc"
CYAN = "#67e8f9"
GOLD = "#fbbf24"
GREEN = "#4ade80"
RED = "#f87171"
MUTED = "#6b7280"

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

BANNER = f"""[{PINK}]  ██╗  ██╗██╗███████╗███╗   ███╗███████╗████████╗[/]
[{PINK}]  ██║ ██╔╝██║██╔════╝████╗ ████║██╔════╝╚══██╔══╝[/]
[{PURPLE}]  █████╔╝ ██║███████╗██╔████╔██║█████╗     ██║   [/]
[{PURPLE}]  ██╔═██╗ ██║╚════██║██║╚██╔╝██║██╔══╝     ██║   [/]
[{CYAN}]  ██║  ██╗██║███████║██║ ╚═╝ ██║███████╗   ██║   [/]
[{CYAN}]  ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝╚══════╝   ╚═╝   [/]
[{MUTED}]    業力引發哈希挖礦暨驅魔工具  v1.0.0[/]
[{MUTED}]    Karma-Induced SHA Mining and Exorcism Tool[/]"""


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
_ALTAR_BASE     = "    ████    ████    ████    ████ "
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
    assert 0 <= shift <= 6, f"shift must be 0–6, got {shift}"
    return " " * (6 - shift) + "≀" + "    ≀" * 4 + " " * (6 + shift)


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


def _highlight_hash(
    hash_str: str,
    lucky_match: Optional[str] = None,
    unlucky_match: Optional[str] = None,
) -> str:
    """Return Rich markup with the lucky (green) or unlucky (red) substring highlighted."""
    h = hash_str.lower()

    # Unlucky takes priority
    target = unlucky_match or lucky_match
    color = RED if unlucky_match else GREEN
    if target:
        idx = h.find(target.lower())
        if idx >= 0:
            before = hash_str[:idx]
            matched = hash_str[idx : idx + len(target)]
            after = hash_str[idx + len(target) :]
            result = ""
            if before:
                result += f"[{CYAN}]{before}[/]"
            result += f"[{color}][bold]{matched}[/bold][/]"
            if after:
                result += f"[{CYAN}]{after}[/]"
            return result

    return f"[{CYAN}]{hash_str}[/]"


class RendererTool:
    def __init__(self):
        self.console = Console()
        self._mining_live: Optional[Live] = None
        self._mining_log: deque[str] = deque(maxlen=10)
        self._altar_frame: int = 0
        self._altar_stop: threading.Event = threading.Event()
        self._altar_thread: Optional[threading.Thread] = None
        self._curse_mode: bool = False

    def _altar_content(self) -> Group:
        altar_color, smoke_shades, ash_line, ash_color = (
            _ALTAR_FRAME_DATA[self._altar_frame % len(_ALTAR_FRAME_DATA)]
        )

        lines: list[str] = []

        # Smoke rows — pad to max 4 rows so total height stays constant across frames
        _MAX_SMOKE_ROWS = 4
        for _ in range(_MAX_SMOKE_ROWS - len(smoke_shades)):
            lines.append(" " * 33)
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

        altar_art = Text.from_markup("\n".join("   " + line for line in lines))
        if self._curse_mode:
            header = Panel(
                "正在施術下蠱，等待不詳 hash 降臨...",
                title=f"[{RED}]☠ 下蠱施術中 ☠[/]",
                border_style=RED,
                expand=False,
            )
        else:
            header = Panel(
                "正在燃燒 Token 祭天，請耐心等候...",
                title=f"[{GOLD}]⚒ 逆天改運中 ⚒[/]",
                border_style=PURPLE,
                expand=False,
            )
        return Group(Text(""), header, altar_art, Text(""))

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

    def show_banner(self) -> None:
        self.console.print()
        self.console.print(BANNER)
        self.console.print()
        time.sleep(0.3)

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

    @contextmanager
    def divination_spinner(self, hash_str: str):
        with Status(
            f"[{MUTED}]水晶球感應中... hash: [{CYAN}]{hash_str}[/][/]",
            console=self.console,
            spinner="dots",
        ):
            yield

    def _typewriter(self, text: str, delay: float = 0.02) -> None:
        with Live(console=self.console, refresh_per_second=50) as live:
            displayed = ""
            for char in text:
                displayed += char
                live.update(Text.from_markup(
                    f"  [{CYAN}]「{displayed}[/{CYAN}][{PINK}]█[/{PINK}]"
                ))
                time.sleep(delay)
            live.update(Text.from_markup(f"  [{CYAN}]「{text}」[/]"))

    def show_divination_reading(self, hash_str: str, result: DivinationResult) -> None:
        self.console.print()
        self._typewriter(result.reading, delay=0.025)

    def show_divination_result(self, hash_str: str, result: DivinationResult) -> None:
        k = result.k_value
        if k <= 20:
            bar_color, label = RED, "☠ 運勢極差"
        elif k <= 40:
            bar_color, label = "#f97316", "😰 運勢稍差"
        elif k <= 60:
            bar_color, label = GOLD, "😐 運勢普通"
        elif k <= 80:
            bar_color, label = "#84cc16", "🙂 運勢尚可"
        else:
            bar_color, label = GREEN, "🎉 運勢極佳"

        filled = int(k / 10)
        bar = "█" * filled + "░" * (10 - filled)
        tarot_lines = "\n".join(
            f"  [{MUTED}]    {pz}  {_TAROT_EMOJI.get(c, '✦')} {_TAROT_ZH.get(c, c)} {p}[/]"
            for (c, p), pz in zip(result.tarot_cards, ["過去", "現在", "未來"])
        )
        self.console.print(
            f"\n  [{bar_color}]◈ K-value：{bar}  {k} / 100[/]\n"
            f"  [{bar_color}]◈ 運勢等級：{label}[/]\n"
            f"  [{MUTED}]◈ 塔羅牌陣：[/]\n"
            f"{tarot_lines}"
        )

    # ── Mining (Live rolling display with animated altar) ─────────────────────

    def show_mining_start(self, curse: bool = False) -> None:
        self._curse_mode = curse
        self._mining_log.clear()
        self._altar_frame = 0
        self._altar_stop.clear()
        self._mining_live = Live(console=self.console, refresh_per_second=8)
        self._mining_live.start()
        self._mining_live.update(self._altar_content())
        self._altar_thread = threading.Thread(target=self._animate_altar, daemon=True)
        self._altar_thread.start()

    def show_mining_attempt(
        self, attempt: int, max_attempts: int, hash_str: str, lucky: bool, target: Optional[str] = None
    ) -> None:
        if self._curse_mode:
            highlighted = _highlight_hash(hash_str, unlucky_match=target if lucky else None)
            if lucky:
                line = f"  [{MUTED}]嘗試 {attempt}/{max_attempts}[/]  hash: {highlighted}  [{RED}]☠ 中蠱！含 {target or '不詳字串'}[/]"
            else:
                line = f"  [{MUTED}]嘗試 {attempt}/{max_attempts}[/]  [{MUTED}]hash:[/] {highlighted}  [{MUTED}]✗ 尚未中蠱[/]"
        else:
            highlighted = _highlight_hash(hash_str, target if lucky else None)
            if lucky:
                line = f"  [{MUTED}]嘗試 {attempt}/{max_attempts}[/]  hash: {highlighted}  [{GREEN}]✦ 吉兆！含 {target or '幸運字串'}[/]"
            else:
                line = f"  [{MUTED}]嘗試 {attempt}/{max_attempts}[/]  [{MUTED}]hash:[/] {highlighted}  [{RED}]✗ 無緣[/]"
        self._mining_log.append(line)

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

    # ── Outcomes ─────────────────────────────────────────────────────────────

    def _show_outcome(
        self,
        session,
        max_attempts: int,
        new_k_value: int,
        commentary: str,
        match: Optional[str],
        *,
        mode: str,  # "success" or "curse"
    ) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"
        original_k = session.k_value

        if mode == "success":
            header = f"\n[{GREEN}]  ✦ ✧ ✦ ✧ ✦  改運成功  ✦ ✧ ✦ ✧ ✦[/]\n"
            original_hash_color, before_label, after_label = RED, "改運前", "改運後"
            k_before_color = RED if original_k <= 40 else (GOLD if original_k <= 60 else GREEN)
            k_after_color_fn = lambda k: GREEN if k >= 60 else (GOLD if k >= 40 else RED)
            new_hash_display = _highlight_hash(session.predicted_hash, lucky_match=match)
            attempts_label, footer = "改運嘗試次數", "花錢消災，物有所值"
            panel_title, panel_border = f"[{PURPLE}]誠心敬意報告[/]", PURPLE
            commentary_prefix = f"[{PURPLE}]✦ 天機批示：[/{PURPLE}]"
        else:  # curse
            header = f"\n[{RED}]  ☠ ☠ ☠  下蠱成功  ☠ ☠ ☠[/]\n"
            original_hash_color, before_label, after_label = CYAN, "下蠱前", "下蠱後"
            k_before_color = GREEN if original_k >= 80 else (GOLD if original_k >= 40 else RED)
            k_after_color_fn = lambda k: RED
            new_hash_display = _highlight_hash(session.predicted_hash, unlucky_match=match)
            attempts_label, footer = "下蠱嘗試次數", "業力纏身，自作自受"
            panel_title, panel_border = f"[{RED}]蠱術報告[/]", RED
            commentary_prefix = f"[{RED}]☠ 天機批示：[/{RED}]"

        output = (
            f"{header}\n"
            f"  [{MUTED}]{before_label}[/]  [{original_hash_color}]{session.original_predicted_hash}[/]\n"
            f"  [{MUTED}]{after_label}[/]  {new_hash_display}\n"
        )
        if original_k > 0 and new_k_value > 0:
            filled_orig = int(original_k / 10)
            bar_orig = "█" * filled_orig + "░" * (10 - filled_orig)
            filled_new = int(new_k_value / 10)
            bar_new = "█" * filled_new + "░" * (10 - filled_new)
            output += (
                f"\n  [{MUTED}]◈ K-value 對照[/]\n"
                f"  [{k_before_color}]    {before_label}  {bar_orig}  {original_k:3d} / 100[/]\n"
                f"  [{k_after_color_fn(new_k_value)}]    {after_label}  {bar_new}  {new_k_value:3d} / 100[/]\n"
            )
        self.console.print(output)

        total_tokens = session.total_input_tokens + session.total_output_tokens
        report_table = Table.grid(padding=(0, 2))
        report_table.add_column(style=MUTED)
        report_table.add_column()
        report_table.add_row(attempts_label, f"[{CYAN}]{session.mine_attempts} / {max_attempts}[/]")
        report_table.add_row("燃燒 Token", f"[{CYAN}]{total_tokens:,}[/]")
        report_table.add_row("花費誠意", f"[{GOLD}]{cost_str}  💸[/]")
        report_table.add_row(f"[{MUTED}]{footer}[/]", "")
        self.console.print(Panel(report_table, title=panel_title, border_style=panel_border, expand=False))

        if commentary:
            self.console.print(f"\n  {commentary_prefix}")
            self._typewriter(commentary)

    def show_success(
        self,
        session,
        max_attempts: int,
        new_k_value: int = 0,
        commentary: str = "",
        lucky_match: Optional[str] = None,
    ) -> None:
        self._show_outcome(session, max_attempts, new_k_value, commentary, lucky_match, mode="success")

    def show_blessing(self, session) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"
        total_tokens = session.total_input_tokens + session.total_output_tokens
        scroll_art = Text.from_markup(
            f"[{GOLD}]╔══╦═══════════════════════════╦══╗[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]╠══╬═══════════════════════════╬══╣[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]      ☰ ☱ ☲ ☳ ☴ ☵ ☶ ☷      [/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]  ─────────────────────────[/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]║  ║  ✦    奉  天  承  運  ✦   ║  ║[/]\n"
            f"[{GOLD}]║  ║                           ║  ║[/]\n"
            f"[{GOLD}]║  ║  🙏  祈  福  法  壇  🙏   ║  ║[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]        ☯    ☰    ☯        [/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]║  ║  業  力  化  解  進  行   ║  ║[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]  ─────────────────────────[/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]      ☷ ☶ ☵ ☴ ☳ ☲ ☱ ☰      [/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]╠══╬═══════════════════════════╬══╣[/]\n"
            f"[{GOLD}]║  ║[/][{PURPLE}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/][{GOLD}]║  ║[/]\n"
            f"[{GOLD}]╚══╩═══════════════════════════╩══╝[/]"
        )
        stats = Text.from_markup(
            f"[{PURPLE}]◈ 總消耗：[/{PURPLE}][{CYAN}]{total_tokens:,} tokens  {cost_str} 💸[/]\n"
            f"[{MUTED}]◈ 花錢消災，功德圓滿[/]\n"
            f"[{GOLD}]◈ 強行提交，聽天由命...[/]"
        )
        self.console.print()
        self.console.print(Padding(scroll_art, (0, 0, 0, 3)))
        self.console.print()
        self.console.print(Panel(
            stats,
            title=f"[{GOLD}]🙏 祈福儀式（改運 {session.mine_attempts} 次）🙏[/]",
            border_style=GOLD,
            expand=False,
        ))

    def show_exorcism(self) -> None:
        DARK_RED = "#7f1d1d"
        art = Text.from_markup(
            f"[{RED}]╔══╦═══════════════════════════╦══╗[/]\n"
            f"[{RED}]║  ║[/][{DARK_RED}]███████████████████████████[/][{RED}]║  ║[/]\n"
            f"[{RED}]╠══╬═══════════════════════════╬══╣[/]\n"
            f"[{RED}]║  ║      ☰ ☱ ☲ ☳ ☴ ☵ ☶ ☷      ║  ║[/]\n"
            f"[{RED}]║  ║  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔║  ║[/]\n"
            f"[{RED}]║  ║  ☠    凶  咒  解  除  ☠   ║  ║[/]\n"
            f"[{RED}]║  ║                           ║  ║[/]\n"
            f"[{RED}]║  ║  ⚡   驅  魔  法  壇  ⚡  ║  ║[/]\n"
            f"[{RED}]║  ║        ☠    ☳    ☠        ║  ║[/]\n"
            f"[{RED}]║  ║  厄  運  消  散  進  行   ║  ║[/]\n"
            f"[{RED}]║  ║  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔║  ║[/]\n"
            f"[{RED}]║  ║      ☷ ☶ ☵ ☴ ☳ ☲ ☱ ☰      ║  ║[/]\n"
            f"[{RED}]╠══╬═══════════════════════════╬══╣[/]\n"
            f"[{RED}]║  ║[/][{DARK_RED}]███████████████████████████[/][{RED}]║  ║[/]\n"
            f"[{RED}]╚══╩═══════════════════════════╩══╝[/]"
        )
        self.console.print()
        self.console.print(f"  [{RED}]⚡ 警告：強行打破宇宙平衡 ⚡[/]")
        self.console.print()
        self.console.print(Padding(art, (0, 0, 0, 3)))
        self.console.print()

    def show_celebration(self) -> None:
        self.console.print(
            f"\n[{GREEN}]  ✦ ✧ ✦ 因緣俱足，天時地利人和 ✦ ✧ ✦[/]\n"
            f"  [{CYAN}]◈ 此次 commit 乃宇宙眷顧，必當功成！[/]"
        )

    def show_committed(self, actual_hash: str) -> None:
        self.console.print(
            f"\n  [{GREEN}]✓ 已提交[/]  [{CYAN}]{actual_hash}[/]"
        )

    def ask_should_curse(self, k_value: int) -> bool:
        prompt = f"[{RED}]  此 hash 尚無凶兆（K={k_value}），真的要下蠱施術？[y/N] [/]"
        self.console.print()
        answer = self.console.input(prompt).strip().lower()
        return answer == "y"

    def show_curse_initial_success(self, hash_str: str, unlucky_match: str) -> None:
        hash_display = _highlight_hash(hash_str, unlucky_match=unlucky_match)
        self.console.print(
            f"\n[{RED}]  ☠ ☠ ☠  天降凶兆，不詳 hash 已至  ☠ ☠ ☠[/]\n\n"
            f"  [{MUTED}]不詳 hash[/]  {hash_display}\n"
            f"  [{RED}]◈ 凶兆字符：{unlucky_match}[/]\n"
        )

    def show_curse_success(
        self,
        session,
        max_attempts: int,
        new_k_value: int = 0,
        commentary: str = "",
        unlucky_match: Optional[str] = None,
    ) -> None:
        self._show_outcome(session, max_attempts, new_k_value, commentary, unlucky_match, mode="curse")

    def show_curse_blessing(self, session) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"
        total_tokens = session.total_input_tokens + session.total_output_tokens
        stats = Text.from_markup(
            f"[{PURPLE}]◈ 總消耗：[/{PURPLE}][{CYAN}]{total_tokens:,} tokens  {cost_str} 💸[/]\n"
            f"[{MUTED}]◈ 天道有常，此劫難逃[/]\n"
            f"[{MUTED}]◈ 強行提交，聽天由命...[/]"
        )
        panel = Panel(
            stats,
            title=f"[{MUTED}]🔮 施術未果（下蠱 {session.mine_attempts} 次）🔮[/]",
            border_style=MUTED,
            expand=False,
        )
        self.console.print()
        self.console.print(Align.center(panel))

    def ask_should_mine(self, k_value: int) -> bool:
        if k_value <= 60:
            prompt = f"[{GOLD}]  運勢普通（K={k_value}），是否進行逆天改運？[Y/N] [/]"
        else:
            prompt = f"[{CYAN}]  運勢尚可（K={k_value}），逆天改運可更上一層樓。是否進行？[Y/N] [/]"
        self.console.print()
        answer = self.console.input(prompt).strip().lower()
        return answer == "y"
