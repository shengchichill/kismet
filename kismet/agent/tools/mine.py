from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from kismet.agent.tools.mac_sensor import format_mining_omen, get_sensor_snapshot, post_kismet_event, wait_for_prayer_pose

if TYPE_CHECKING:
    from kismet.agent.tools.divine import DivinationTool
    from kismet.agent.tools.git import GitTool
    from kismet.config import Config


def find_lucky_match(hash_str: str, targets: list[str]) -> Optional[str]:
    """Return the matched lucky substring, or None if not lucky."""
    if targets:
        for t in targets:
            if t.lower() in hash_str.lower():
                idx = hash_str.lower().find(t.lower())
                return hash_str[idx : idx + len(t)]
        return None
    for s in _LUCKY_STRINGS:
        if s in hash_str:
            return s
    for i in range(len(hash_str) - 2):
        if (
            ord(hash_str[i + 1]) == ord(hash_str[i]) + 1
            and ord(hash_str[i + 2]) == ord(hash_str[i]) + 2
        ):
            return hash_str[i : i + 3]
    n = len(hash_str)
    for length in range(4, n + 1):
        for start in range(n - length + 1):
            sub = hash_str[start : start + length]
            if sub == sub[::-1]:
                return sub
    return None


def is_lucky(hash_str: str, targets: list[str]) -> bool:
    """Return True if hash_str matches custom targets or default lucky patterns."""
    return find_lucky_match(hash_str, targets) is not None


_LUCKY_STRINGS = ["888", "168", "666", "777"]


class MineStatus(Enum):
    SUCCESS = "success"
    EXHAUSTED = "exhausted"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class MineResult:
    status: MineStatus
    reason: str = ""

    @property
    def success(self) -> bool:
        return self.status is MineStatus.SUCCESS


class MinerTool:
    def __init__(self, divine_tool: DivinationTool, git_tool: GitTool, config: Config):
        self.divine_tool = divine_tool
        self.git_tool = git_tool
        self.config = config

    def mine(self, session, renderer, targets: list[str]) -> MineResult:
        """Rephrase commit message until hash is lucky or max attempts reached.
        Modifies session in place. Returns a status for success, exhaustion, or ritual blocking.
        """
        from kismet.agent.tools.git import GitContext

        session.original_predicted_hash = session.predicted_hash
        max_attempts = self.config.max_mine_attempts
        status = MineStatus.EXHAUSTED

        renderer.show_mining_start()
        post_kismet_event(
            "MiningStart",
            f"target={', '.join(targets) if targets else 'default'} max={max_attempts}",
            hash=session.predicted_hash,
        )
        try:
            for attempt in range(1, max_attempts + 1):
                prayer_snapshot = None
                if self.config.require_prayer_pose:
                    renderer.show_prayer_pose_wait(attempt, max_attempts)
                    ok, reason, prayer_snapshot = wait_for_prayer_pose(self.config.prayer_pose_timeout_seconds)
                    if not ok:
                        status = MineStatus.BLOCKED
                        post_kismet_event("MiningBlocked", reason, attempt=attempt, max_attempts=max_attempts)
                        renderer.show_prayer_pose_blocked(reason)
                        return MineResult(status, reason=reason)
                    renderer.show_prayer_pose_confirmed()

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
                lucky_match = find_lucky_match(new_hash, targets)
                lucky = lucky_match is not None
                sensor_omen = format_mining_omen(prayer_snapshot or get_sensor_snapshot())
                attempt_summary = f"{attempt}/{max_attempts} {new_hash[:12]} {'lucky ' + lucky_match if lucky_match else 'no omen'}"
                post_kismet_event(
                    "MiningAttempt",
                    attempt_summary,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    hash=new_hash,
                    lucky=lucky,
                    target=lucky_match,
                )

                renderer.show_mining_attempt(
                    attempt,
                    max_attempts,
                    new_hash,
                    lucky,
                    target=lucky_match,
                    sensor_omen=sensor_omen,
                )

                session.current_message = new_msg
                session.predicted_hash = new_hash
                session.mine_attempts = attempt

                if lucky:
                    status = MineStatus.SUCCESS
                    post_kismet_event("MiningSuccess", attempt_summary, attempt=attempt, hash=new_hash, target=lucky_match)
                    return MineResult(status)

            return MineResult(status)
        finally:
            post_kismet_event("MiningEnd", f"{status.value} after {session.mine_attempts}/{max_attempts}", hash=session.predicted_hash)
            renderer.show_mining_end()
