import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
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

EXORCISM_ART = f"""[{RED}]
  ╔══════════════════════════════════════╗
  ║  ⚡ 警告：強行打破宇宙平衡 ⚡       ║
  ╚══════════════════════════════════════╝

      符 咒 驅 魔 儀 式 開 始
      ━━━━━━━━━━━━━━━━━━━━━━

        ☠  厄  運  解  除  ☠
       /|\\ 驅  除  不  詳  /|\\
      / | \\ 宇  宙  平  衡 / | \\

  「雖違宇宙法則，誠意已達，特此驅魔。」
[/]"""

_ALTAR_FLAME_FRAMES: list[str] = [
    f"[{MUTED}]~   ~  ~    ~  ~[/]",
    f"[{GOLD}]~ ~ ~  ~~ ~ ~ ~  ~[/]",
    f"[{RED}]~~ ~ ~~  ~~ ~ ~~  ~[/]",
    f"[{PINK}]*  ~ ~~  ~ * ~~ ~ *[/]",
]


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
        self._mining_log: deque = deque(maxlen=10)
        self._altar_frame: int = 0
        self._altar_stop: threading.Event = threading.Event()
        self._altar_thread: Optional[threading.Thread] = None

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

    def show_divination_reading(self, hash_str: str, result: DivinationResult) -> None:
        self.console.print()
        with Live(console=self.console, refresh_per_second=40) as live:
            displayed = ""
            for char in result.reading:
                displayed += char
                live.update(Text.from_markup(
                    f"  [{CYAN}]「{displayed}[/{CYAN}][{PINK}]█[/{PINK}]"
                ))
                time.sleep(0.025)
            live.update(Text.from_markup(f"  [{CYAN}]「{result.reading}」[/]"))

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
        self.console.print(
            f"\n  [{bar_color}]◈ K-value：{bar}  {k} / 100[/]\n"
            f"  [{bar_color}]◈ 運勢等級：{label}[/]\n"
            f"  [{MUTED}]◈ 塔羅：{result.tarot_card} {result.tarot_position}[/]"
        )

    # ── Mining (Live rolling display with animated altar) ─────────────────────

    def show_mining_start(self) -> None:
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

    def show_success(
        self,
        session,
        max_attempts: int,
        new_k_value: int = 0,
        commentary: str = "",
        lucky_match: Optional[str] = None,
    ) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"

        original_k = session.k_value
        filled_orig = int(original_k / 10)
        bar_orig = "█" * filled_orig + "░" * (10 - filled_orig)
        k_before_color = RED if original_k <= 40 else (GOLD if original_k <= 60 else GREEN)

        new_hash_display = _highlight_hash(session.predicted_hash, lucky_match)
        output = (
            f"\n[{GREEN}]  ✦ ✧ ✦ ✧ ✦  改運成功  ✦ ✧ ✦ ✧ ✦[/]\n\n"
            f"  [{MUTED}]改運前[/]  [{RED}]{session.original_predicted_hash}[/]\n"
            f"  [{MUTED}]改運後[/]  {new_hash_display}\n"
        )

        if original_k > 0 and new_k_value > 0:
            filled_new = int(new_k_value / 10)
            bar_new = "█" * filled_new + "░" * (10 - filled_new)
            k_after_color = GREEN if new_k_value >= 60 else (GOLD if new_k_value >= 40 else RED)
            output += (
                f"\n  [{MUTED}]◈ K-value 對照[/]\n"
                f"  [{k_before_color}]    改運前  {bar_orig}  {original_k:3d} / 100[/]\n"
                f"  [{k_after_color}]    改運後  {bar_new}  {new_k_value:3d} / 100[/]\n"
            )

        output += (
            f"\n  [{PURPLE}]┌──────────── 誠心敬意報告 ────────────┐[/]\n"
            f"  [{PURPLE}]│[/]  [{CYAN}]改運嘗試次數  {session.mine_attempts} / {max_attempts}[/]                [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{CYAN}]燃燒 Token    {session.total_input_tokens + session.total_output_tokens:,}[/]              [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{GOLD}]花費誠意      {cost_str}  💸[/]       [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{MUTED}]花錢消災，物有所值[/]               [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]└──────────────────────────────────────┘[/]"
        )
        self.console.print(output)

        if commentary:
            self.console.print(f"\n  [{PURPLE}]✦ 天機批示：[/{PURPLE}]")
            with Live(console=self.console, refresh_per_second=50) as live:
                displayed = ""
                for char in commentary:
                    displayed += char
                    live.update(Text.from_markup(
                        f"  [{CYAN}]「{displayed}[/{CYAN}][{PINK}]█[/{PINK}]"
                    ))
                    time.sleep(0.02)
                live.update(Text.from_markup(f"  [{CYAN}]「{commentary}」[/]"))

    def show_blessing(self, session) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"
        self.console.print(
            f"\n[{GOLD}]  ╔════════════ 🙏 祈福儀式 🙏 ════════════╗[/]\n"
            f"[{GOLD}]  ║  改運 {session.mine_attempts} 次均未成功，誠意已達上天    ║[/]\n"
            f"[{GOLD}]  ╚════════════════════════════════════════╝[/]\n\n"
            f"[{MUTED}]         ~  ~  ~  ~  ~  ~  ~[/]\n"
            f"[{GOLD}]         | | | | | | | | | |[/]\n"
            f"[{GOLD}]        _|_|_|_|_|_|_|_|_|__[/]\n"
            f"[{GOLD}]       |   🕯  祈福壇  🕯    |[/]\n"
            f"[{GOLD}]       |____________________|[/]\n\n"
            f"  [{PURPLE}]◈ 總消耗：[/{PURPLE}][{CYAN}]{session.total_input_tokens + session.total_output_tokens:,} tokens  {cost_str} 💸[/]\n"
            f"  [{MUTED}]◈ 花錢消災，功德圓滿[/]\n"
            f"  [{GOLD}]◈ 強行提交，聽天由命...[/]"
        )

    def show_exorcism(self) -> None:
        self.console.print(EXORCISM_ART)

    def show_celebration(self) -> None:
        self.console.print(
            f"\n[{GREEN}]  ✦ ✧ ✦ 因緣俱足，天時地利人和 ✦ ✧ ✦[/]\n"
            f"  [{CYAN}]◈ 此次 commit 乃宇宙眷顧，必當功成！[/]"
        )

    def show_committed(self, actual_hash: str) -> None:
        self.console.print(
            f"\n  [{GREEN}]✓ 已提交[/]  [{CYAN}]{actual_hash}[/]"
        )

    def ask_should_mine(self, k_value: int) -> bool:
        if k_value <= 60:
            prompt = f"[{GOLD}]  運勢普通（K={k_value}），是否進行逆天改運？[y/N] [/]"
        else:
            prompt = f"[{CYAN}]  運勢尚可（K={k_value}），逆天改運可更上一層樓。是否進行？[y/N] [/]"
        self.console.print()
        answer = self.console.input(prompt).strip().lower()
        return answer == "y"
