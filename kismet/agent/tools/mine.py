from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kismet.agent.tools.divine import DivinationTool
    from kismet.agent.tools.git import GitTool
    from kismet.config import Config


def is_lucky(hash_str: str, targets: list[str]) -> bool:
    """Return True if hash_str matches custom targets or default lucky patterns."""
    if targets:
        return any(t.lower() in hash_str.lower() for t in targets)
    return _has_default_lucky(hash_str)


_LUCKY_STRINGS = ["888", "168", "666", "777"]


def _has_default_lucky(hash_str: str) -> bool:
    if any(s in hash_str for s in _LUCKY_STRINGS):
        return True
    # Consecutive ascending characters, length >= 3
    for i in range(len(hash_str) - 2):
        if (
            ord(hash_str[i + 1]) == ord(hash_str[i]) + 1
            and ord(hash_str[i + 2]) == ord(hash_str[i]) + 2
        ):
            return True
    # Palindrome substring, length >= 4
    n = len(hash_str)
    for length in range(4, n + 1):
        for start in range(n - length + 1):
            sub = hash_str[start : start + length]
            if sub == sub[::-1]:
                return True
    return False


class MinerTool:
    def __init__(self, divine_tool: DivinationTool, git_tool: GitTool, config: Config):
        self.divine_tool = divine_tool
        self.git_tool = git_tool
        self.config = config

    def mine(self, session, renderer, targets: list[str]) -> bool:
        """Rephrase commit message until hash is lucky or max attempts reached.
        Modifies session in place. Returns True if a lucky hash was found.
        """
        from kismet.agent.tools.git import GitContext

        session.original_predicted_hash = session.predicted_hash
        max_attempts = self.config.max_mine_attempts

        renderer.show_mining_start()

        for attempt in range(1, max_attempts + 1):
            new_msg, in_tok, out_tok = self.divine_tool.rephrase_message(
                session.current_message,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            session.total_input_tokens += in_tok
            session.total_output_tokens += out_tok

            ctx = GitContext(
                tree_sha=session.tree_sha,
                parent_sha=session.parent_sha,
                author_name=session.author_name,
                author_email=session.author_email,
                fixed_timestamp=session.fixed_timestamp,
            )
            new_hash = self.git_tool.compute_hash(new_msg, ctx)
            lucky = is_lucky(new_hash, targets)

            renderer.show_mining_attempt(attempt, max_attempts, new_hash, lucky)

            session.current_message = new_msg
            session.predicted_hash = new_hash
            session.mine_attempts = attempt

            if lucky:
                return True

        return False
