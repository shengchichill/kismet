import time
from contextlib import contextmanager
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.status import Status
from rich.text import Text

from kismet.agent.tools.divine import DivinationResult

PINK = "#ff6b9d"
PURPLE = "#c084fc"
CYAN = "#67e8f9"
GOLD = "#fbbf24"
GREEN = "#4ade80"
RED = "#f87171"
MUTED = "#6b7280"

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


def _tarot_card_row(cards: list[tuple[str, str, str]]) -> str:
    tops = "".join(f"┌─────┐  " for _ in cards)
    mids = "".join(f"│[{c}] {icon[:5].ljust(5)} [/{c}]│  " for _, icon, c in cards)
    bots = "".join(f"└─────┘  " for _ in cards)
    return f"  {tops}\n  {mids}\n  {bots}"


class RendererTool:
    def __init__(self):
        self.console = Console()

    def show_banner(self) -> None:
        self.console.print()
        self.console.print(BANNER)
        self.console.print()
        time.sleep(0.3)

    def show_divination_animation(self, hash_str: str) -> None:
        bad_chars = any(s in hash_str for s in ["404", "dead", "bad", "f00d"])
        face_down = [("░░░░░", "░░░░░", PURPLE)] * 3

        with Live(console=self.console, refresh_per_second=4) as live:
            # Frame A: cards dealing
            cards_a = [("░░░░░", "░░░░░", PURPLE), ("░░░░░", "░░░░░", PURPLE), ("     ", "     ", MUTED)]
            text = Text.from_markup(
                f"[{PURPLE}]  ✦ 命盤展開中，牌語浮現於宇宙之間... ✦[/]\n\n"
                + _tarot_card_row(cards_a)
                + f"\n\n[{MUTED}]  hash: [{CYAN}]{hash_str}[/]   感應中 ⟳[/]"
            )
            live.update(Panel(text, border_style=PURPLE, padding=(0, 1)))
            time.sleep(1.0)

            # Frame B: all revealed
            crystal_color = RED if bad_chars else GREEN
            cards_b = [
                ("FOOL ", "🃏   ", CYAN),
                ("WHEEL", "☸    ", CYAN),
                ("TOWER", "⚡💀 ", RED if bad_chars else GOLD),
            ]
            text2 = Text.from_markup(
                f"[{PURPLE}]  ✦ 命盤展開中，牌語浮現於宇宙之間... ✦[/]\n\n"
                + _tarot_card_row(cards_b)
                + (f"\n\n[{RED}]  ⚠  水晶球異動：hash 含不詳字符[/]" if bad_chars else f"\n\n[{GREEN}]  ✦  氣場穩定[/]")
            )
            live.update(Panel(text2, border_style=crystal_color, padding=(0, 1)))
            time.sleep(1.2)

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
        displayed = ""
        for char in result.reading:
            displayed += char
            self.console.print(
                f"  [{CYAN}]「{displayed}[/{CYAN}][{PINK}]█[/{PINK}]",
                end="\r",
            )
            time.sleep(0.025)
        self.console.print(f"  [{CYAN}]「{result.reading}」[/]")

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

    def show_mining_start(self) -> None:
        self.console.print(
            f"\n[{PURPLE}]  ╔════════════ ⚒ 逆天改運中 ⚒ ════════════╗[/]\n"
            f"[{GOLD}]  ║  正在燃燒 Token 祭天，請耐心等候...      ║[/]\n"
            f"[{PURPLE}]  ╚════════════════════════════════════════╝[/]\n\n"
            f"[{MUTED}]           ~   ~  ~    ~  ~[/]\n"
            f"[{GOLD}]           | | | | | | | | | |[/]\n"
            f"[{GOLD}]          _|_|_|_|_|_|_|_|_|__[/]\n"
            f"[{GOLD}]         |  🔥 焚燒 Token 祭壇 🔥  |[/]\n"
            f"[{GOLD}]         |________________________|[/]"
        )

    def show_mining_attempt(
        self, attempt: int, max_attempts: int, hash_str: str, lucky: bool, target: Optional[str] = None
    ) -> None:
        if lucky:
            status = f"[{GREEN}]  ✦ 吉兆！含 {target or '幸運字串'}！[/]"
        else:
            status = f"[{RED}]  ✗ 無緣[/]"
        self.console.print(
            f"  [{MUTED}]嘗試 {attempt}/{max_attempts}  [{CYAN}]hash: {hash_str}[/][/]{status}"
        )

    def show_success(self, session, max_attempts: int) -> None:
        cost_str = f"${session.total_cost_usd:.4f} USD" if session.total_cost_usd is not None else "(cost unknown)"
        self.console.print(
            f"\n[{GREEN}]  ✦ ✧ ✦ ✧ ✦  改運成功  ✦ ✧ ✦ ✧ ✦[/]\n\n"
            f"  [{MUTED}]改運前  [{RED}]{session.original_predicted_hash[:16]}...[/][/]\n"
            f"  [{MUTED}]改運後  [{GREEN}]{session.predicted_hash[:16]}...[/][/]\n\n"
            f"  [{PURPLE}]┌──────────── 誠心敬意報告 ────────────┐[/]\n"
            f"  [{PURPLE}]│[/]  [{CYAN}]改運嘗試次數  {session.mine_attempts} / {max_attempts}[/]                [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{CYAN}]燃燒 Token    {session.total_input_tokens + session.total_output_tokens:,}[/]              [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{GOLD}]花費誠意      {cost_str}  💸[/]       [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]│[/]  [{MUTED}]花錢消災，物有所值[/]               [{PURPLE}]│[/]\n"
            f"  [{PURPLE}]└──────────────────────────────────────┘[/]"
        )

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
