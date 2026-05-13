from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from kismet.agent.tools.mac_sensor import format_mining_omen, get_sensor_snapshot, post_kismet_event, wait_for_prayer_pose

if TYPE_CHECKING:
    from kismet.agent.tools.divine import DivinationTool
    from kismet.agent.tools.git import GitTool
    from kismet.config import Config

# Longest first to avoid partial-match false negatives; enforced by sorted() at module load
_LUCKY_STRINGS: list[str] = sorted([
    "c0ffee",  # 咖啡代表生命之水
    "b0ba",    # 珍珠奶茶
    "c001",    # cool
    "5afe",    # safe
    "c0de",    # code
    "fafa",    # 發發
    "feed",    # 有人餵食
    "face",    # 有頭有臉
    "babe",    # 寶貝
    "baba",    # 爸爸，有爸爸當靠山
    "cafe",    # 咖啡因加持
    "f00d",    # 食物吃很飽
    "168",     # 一路發
    "ace",     # 王牌
    "add",     # 增加運勢
    "aba",     # 阿爸，有爸爸當靠山
], key=len, reverse=True)

_UNLUCKY_STRINGS = [
    "dead",
    "deaf",
    "beef",
    "f001",   # fool
    "fa11",   # fall
    "0ff",    # off
    "404",
    "bad",
]


# ── Low-level pattern helpers ─────────────────────────────────────────────────

def _find_repeated_run(
    hash_str: str,
    min_len: int = 3,
    only_char: Optional[str] = None,
    skip_char: Optional[str] = None,
) -> Optional[str]:
    """Find first run of identical chars >= min_len.
    only_char: only match runs of this specific character.
    skip_char: skip runs of this specific character.
    """
    h = hash_str.lower()
    n = len(h)
    i = 0
    while i < n:
        j = i + 1
        while j < n and h[j] == h[i]:
            j += 1
        run_len = j - i
        if run_len >= min_len:
            if only_char is not None and h[i] != only_char.lower():
                i = j
                continue
            if skip_char is not None and h[i] == skip_char.lower():
                i = j
                continue
            return hash_str[i:j]
        i = j
    return None


def _find_sequential_run(hash_str: str, min_len: int = 3, ascending: bool = True) -> Optional[str]:
    """Find first run of consecutive ascending or descending chars >= min_len."""
    h = hash_str.lower()
    n = len(h)
    delta = 1 if ascending else -1
    i = 0
    while i <= n - min_len:
        j = i + 1
        while j < n and ord(h[j]) - ord(h[j - 1]) == delta:
            j += 1
        if j - i >= min_len:
            return hash_str[i:j]
        i += 1
    return None


def _find_repeated_pair(hash_str: str, patterns: list[str], min_repeats: int = 2) -> Optional[str]:
    """Find a pattern from patterns repeated consecutively min_repeats+ times."""
    h = hash_str.lower()
    for pat in patterns:
        repeated = pat * min_repeats
        if repeated in h:
            idx = h.find(repeated)
            end = idx + len(repeated)
            while h[end : end + len(pat)] == pat:
                end += len(pat)
            return hash_str[idx:end]
    return None


def _find_mountain_run(hash_str: str, min_arm: int = 2) -> Optional[str]:
    """Find an ascending-then-descending (mountain) sequence.
    Requires at least min_arm steps up and min_arm steps down (minimum 2*min_arm+1 chars).
    e.g. 'abcba', '12321' with min_arm=2.
    Represents 功德圓滿，有始有終.
    """
    h = hash_str.lower()
    n = len(h)
    for i in range(n):
        # Find end of ascending run from i
        j = i + 1
        while j < n and ord(h[j]) - ord(h[j - 1]) == 1:
            j += 1
        if j - i < min_arm + 1:  # need at least min_arm ascending steps
            continue
        # Peak is at j-1; now find the descending arm
        k = j
        while k < n and ord(h[k]) - ord(h[k - 1]) == -1:
            k += 1
        if k - (j - 1) < min_arm + 1:  # need at least min_arm descending steps
            continue
        return hash_str[i:k]
    return None


# ── Shielding helpers ─────────────────────────────────────────────────────────

def _lucky_covered_ranges(hash_str: str) -> list[tuple[int, int]]:
    """Return (start, end) index ranges in hash_str covered by lucky special strings."""
    h = hash_str.lower()
    ranges: list[tuple[int, int]] = []
    for ls in _LUCKY_STRINGS:
        pos = h.find(ls)
        while pos >= 0:
            ranges.append((pos, pos + len(ls)))
            pos = h.find(ls, pos + 1)
    return ranges


def _covered_by_range(pos: int, length: int, ranges: list[tuple[int, int]]) -> bool:
    """Return True if [pos, pos+length) is fully contained within any range."""
    return any(start <= pos and pos + length <= end for start, end in ranges)


# ── Public pattern matchers ───────────────────────────────────────────────────

def find_unlucky_match(hash_str: str) -> Optional[str]:
    """Return the first unshielded unlucky substring, or None if not unlucky.

    Shielding rules:
    - Unlucky special strings that fall entirely inside a lucky special string are ignored
      (e.g. '0ff' inside 'c0ffee' does not count).
    - Descending sequences that are fully contained within a mountain run are ignored
      (the right arm of a mountain is part of the 功德圓滿 pattern, not an omen of doom).
    """
    h = hash_str.lower()
    lucky_ranges = _lucky_covered_ranges(hash_str)

    # Special unlucky strings — skip if shielded by a lucky string
    for s in _UNLUCKY_STRINGS:
        pos = h.find(s)
        while pos >= 0:
            if not _covered_by_range(pos, len(s), lucky_ranges):
                return hash_str[pos : pos + len(s)]
            pos = h.find(s, pos + 1)

    # Triple+ fours (no shielding needed — no lucky string contains '4')
    match = _find_repeated_run(hash_str, min_len=3, only_char="4")
    if match:
        return match

    # Descending sequence — shield if it is the right arm of a mountain
    mountain = _find_mountain_run(hash_str)
    mountain_range: Optional[tuple[int, int]] = None
    if mountain:
        m_start = h.find(mountain.lower())
        mountain_range = (m_start, m_start + len(mountain))

    n = len(h)
    i = 0
    while i <= n - 3:
        j = i + 1
        while j < n and ord(h[j]) - ord(h[j - 1]) == -1:
            j += 1
        run_len = j - i
        if run_len >= 3:
            if mountain_range is not None and _covered_by_range(i, run_len, [mountain_range]):
                i = j  # shielded — skip past this run
            else:
                return hash_str[i:j]
        else:
            i += 1

    # Repeated 87 or 78 (twice or more)
    match = _find_repeated_pair(hash_str, ["87", "78"], min_repeats=2)
    if match:
        return match

    return None


def find_lucky_match(hash_str: str, targets: list[str]) -> Optional[str]:
    """Return the matched lucky substring, or None if not lucky.

    When using default patterns:
    - Unlucky patterns override lucky patterns (unless shielded — see find_unlucky_match).
    - Mountain (ascending then descending, e.g. 'abcba') is a lucky pattern; its descending
      arm is shielded inside find_unlucky_match so it does not trigger the override.
    """
    if targets:
        for t in targets:
            if t.lower() in hash_str.lower():
                idx = hash_str.lower().find(t.lower())
                return hash_str[idx : idx + len(t)]
        return None

    # Unlucky (unshielded) overrides all lucky patterns
    if find_unlucky_match(hash_str) is not None:
        return None

    h = hash_str.lower()

    # Special lucky strings (longest first to avoid partial match)
    for s in _LUCKY_STRINGS:
        if s in h:
            idx = h.find(s)
            return hash_str[idx : idx + len(s)]

    # Mountain: ascending then descending (功德圓滿，有始有終)
    match = _find_mountain_run(hash_str)
    if match:
        return match

    # Ascending sequence of 3+ chars
    match = _find_sequential_run(hash_str, min_len=3, ascending=True)
    if match:
        return match

    # Repeated same char 3+ (runs of '4' don't count — that's unlucky)
    match = _find_repeated_run(hash_str, min_len=3, skip_char="4")
    if match:
        return match

    return None


def is_lucky(hash_str: str, targets: list[str]) -> bool:
    """Return True if hash_str matches custom targets or default lucky patterns."""
    return find_lucky_match(hash_str, targets) is not None


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
        ctx = GitContext(
            tree_sha=session.tree_sha,
            parent_sha=session.parent_sha,
            author_name=session.author_name,
            author_email=session.author_email,
            fixed_timestamp=session.fixed_timestamp,
        )

        renderer.show_mining_start()
        post_kismet_event(
            "MiningStart",
            f"target={', '.join(targets) if targets else 'default'} max={max_attempts}",
            hash=session.predicted_hash,
        )
        spotify_trigger_id = f"{session.original_predicted_hash or session.predicted_hash}:{session.tree_sha}:mine"
        try:
            for attempt in range(1, max_attempts + 1):
                prayer_snapshot = None
                if self.config.require_prayer_pose:
                    renderer.show_prayer_pose_wait(attempt, max_attempts)
                    ok, reason, prayer_snapshot = wait_for_prayer_pose(
                        self.config.prayer_pose_timeout_seconds,
                        spotify_trigger_id=spotify_trigger_id,
                    )
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
