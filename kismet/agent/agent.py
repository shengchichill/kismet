import contextlib

from kismet.agent.session import KismetSession
from kismet.agent.tools.divine import DivinationTool
from kismet.agent.tools.git import GitContext, GitTool
from kismet.agent.tools.mine import MinerTool, find_lucky_match, is_lucky
from kismet.agent.tools.renderer import RendererTool
from kismet.config import Config
from kismet.presence import detect_mage_mode, ensure_mage_running, keep_state_alive, write_state

_DEFAULT_CURSE = ["dead", "404", "bad", "f001", "0ff", "fa11", "beef", "deaf"]


class KismetAgent:
    def __init__(self, config: Config):
        self.config = config
        client = config.make_llm_client()
        self.git = GitTool()
        self.divine = DivinationTool(config, client=client)
        self.miner = MinerTool(divine_tool=self.divine, git_tool=self.git, config=config)
        self.renderer = RendererTool()

    def _add_tokens(self, session: KismetSession, in_tok: int, out_tok: int) -> None:
        session.total_input_tokens += in_tok
        session.total_output_tokens += out_tok
        session.total_cost_usd = self.config.compute_cost_usd(
            session.total_input_tokens, session.total_output_tokens
        )

    def _build_session(self) -> KismetSession:
        diff = self.git.get_staged_diff()
        ctx = self.git.get_context()
        message, in_tok, out_tok = self.divine.generate_message(diff)
        predicted_hash = self.git.compute_hash(message, ctx)
        session = KismetSession(
            diff=diff,
            original_message=message,
            current_message=message,
            predicted_hash=predicted_hash,
            tree_sha=ctx.tree_sha,
            parent_sha=ctx.parent_sha,
            author_name=ctx.author_name,
            author_email=ctx.author_email,
            fixed_timestamp=ctx.fixed_timestamp,
        )
        self._add_tokens(session, in_tok, out_tok)
        return session

    def _ctx_from_session(self, session: KismetSession) -> GitContext:
        return GitContext(
            tree_sha=session.tree_sha,
            parent_sha=session.parent_sha,
            author_name=session.author_name,
            author_email=session.author_email,
            fixed_timestamp=session.fixed_timestamp,
        )

    def _start_mage(self) -> contextlib.AbstractContextManager:
        mode = detect_mage_mode(self.config.mage_mode)
        if mode == "gui":
            ensure_mage_running()
        return contextlib.nullcontext()

    def _run_divination(self, session: KismetSession) -> None:
        write_state("divine")
        self.renderer.show_divination_animation(session.predicted_hash)
        with self.renderer.divination_spinner(session.predicted_hash):
            result = self.divine.divine(session.predicted_hash, session.current_message, session.diff)
        self._add_tokens(session, result.input_tokens, result.output_tokens)
        session.k_value = result.k_value
        session.divination_text = result.reading
        session.tarot_card = result.tarot_card
        session.tarot_position = result.tarot_position
        self.renderer.show_divination_reading(session.predicted_hash, result)
        self.renderer.show_divination_result(session.predicted_hash, result)

    def _generate_success_report(
        self, session: KismetSession, targets: list[str]
    ) -> tuple[int, str]:
        """Re-divine the lucky hash and generate a mystical report.
        Returns (new_k_value, commentary).
        """
        with self.renderer.divination_spinner(session.predicted_hash):
            new_result = self.divine.divine(
                session.predicted_hash, session.current_message, session.diff
            )
        self._add_tokens(session, new_result.input_tokens, new_result.output_tokens)

        lucky_match = find_lucky_match(session.predicted_hash, targets)
        try:
            commentary, in_tok, out_tok = self.divine.generate_mining_report(
                original_hash=session.original_predicted_hash,
                new_hash=session.predicted_hash,
                original_k=session.k_value,
                new_k=new_result.k_value,
                lucky_match=lucky_match or "",
                attempts=session.mine_attempts,
                tokens_burned=session.total_input_tokens + session.total_output_tokens,
            )
            self._add_tokens(session, in_tok, out_tok)
        except Exception:
            commentary = ""

        return new_result.k_value, commentary

    def _mine_and_commit(self, session: KismetSession, targets: list[str]) -> None:
        write_state("mining")
        with keep_state_alive("mining"):
            success = self.miner.mine(session, self.renderer, targets)
        if success:
            write_state("success")
            new_k_value, commentary = self._generate_success_report(session, targets)
            self.renderer.show_success(
                session,
                max_attempts=self.config.max_mine_attempts,
                new_k_value=new_k_value,
                commentary=commentary,
            )
        else:
            write_state("failed")
            self.renderer.show_blessing(session)
            write_state("blessing")
        actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
        self.renderer.show_committed(actual_hash)

    def run_commit(self) -> None:
        """Full auto: generate message → divine → decide → [mine] → commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            self._run_divination(session)

            k = session.k_value
            if k >= 81:
                write_state("success")
                self.renderer.show_celebration()
                actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
                self.renderer.show_committed(actual_hash)
            elif k <= 40:
                self._mine_and_commit(session, targets=[])
            else:
                if self.renderer.ask_should_mine(k):
                    self._mine_and_commit(session, targets=[])
                else:
                    write_state("success")
                    actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
                    self.renderer.show_committed(actual_hash)

    def run_divine(self) -> None:
        """Only divine — no commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            self._run_divination(session)

    def run_mine(self, targets: list[str]) -> None:
        """Only mine for a lucky hash — no commit."""
        with self._start_mage():
            self.renderer.show_banner()
            session = self._build_session()
            write_state("mining")
            with keep_state_alive("mining"):
                success = self.miner.mine(session, self.renderer, targets)
            if success:
                write_state("success")
                new_k_value, commentary = self._generate_success_report(session, targets)
                self.renderer.show_success(
                    session,
                    max_attempts=self.config.max_mine_attempts,
                    new_k_value=new_k_value,
                    commentary=commentary,
                )
            else:
                write_state("failed")
                self.renderer.show_blessing(session)
                write_state("blessing")
            target_label = " ".join(targets) if targets else "default lucky list"
            self.renderer.console.print(
                f"\n  Lucky target: [{target_label}]\n"
                f"  [bold]{session.current_message}[/bold]\n"
                f"  predicted hash: {session.predicted_hash}"
            )

    def run_force(self) -> None:
        """Force commit with exorcism ritual, no divination."""
        with self._start_mage():
            self.renderer.show_banner()
            diff = self.git.get_staged_diff()
            ctx = self.git.get_context()
            message, _, _ = self.divine.generate_message(diff)
            write_state("exorcism")
            self.renderer.show_exorcism()
            actual_hash = self.git.commit(message, ctx)
            self.renderer.show_committed(actual_hash)

    def run_curse(self, targets: list[str]) -> None:
        """Reverse mine: find an unlucky hash and commit it."""
        with self._start_mage():
            effective = targets if targets else _DEFAULT_CURSE
            self.renderer.show_banner()
            session = self._build_session()
            self.renderer.console.print(
                f"\n  [bold red]⬇ 下蠱模式啟動 — 尋找不詳 hash...[/bold red]\n"
                f"  目標字串: {effective}"
            )
            self.renderer.show_mining_start()

            write_state("curse")
            with keep_state_alive("curse"):
                for attempt in range(1, self.config.max_mine_attempts + 1):
                    new_msg, in_tok, out_tok = self.divine.rephrase_message(
                        session.current_message, attempt, self.config.max_mine_attempts
                    )
                    self._add_tokens(session, in_tok, out_tok)
                    new_hash = self.git.compute_hash(new_msg, self._ctx_from_session(session))
                    cursed = is_lucky(new_hash, effective)
                    self.renderer.show_mining_attempt(attempt, self.config.max_mine_attempts, new_hash, cursed)
                    session.current_message = new_msg
                    session.predicted_hash = new_hash
                    if cursed:
                        write_state("success")
                        self.renderer.console.print(f"\n  [red]☠ 下蠱成功！不詳 hash 已就位。[/red]")
                        actual_hash = self.git.commit(new_msg, self._ctx_from_session(session))
                        self.renderer.show_committed(actual_hash)
                        return

            write_state("failed")
            self.renderer.console.print("\n  [yellow]下蠱未成功，天地不從。仍以普通 hash 提交。[/yellow]")
            actual_hash = self.git.commit(session.current_message, self._ctx_from_session(session))
            self.renderer.show_committed(actual_hash)
