from unittest.mock import MagicMock
from kismet.agent.tools.mine import is_lucky, find_lucky_match, find_unlucky_match, _find_mountain_run


# --- Default lucky list (no targets specified) ---

def test_lucky_168():
    assert is_lucky("a168bcd", []) is True

def test_lucky_special_cafe():
    assert is_lucky("xxcafexx", []) is True

def test_lucky_special_c0ffee():
    # "0ff" (unlucky) lives inside "c0ffee" (lucky) — lucky string shields the substring
    assert is_lucky("aac0ffeexx", []) is True

def test_lucky_special_babe():
    assert is_lucky("xxbabexx", []) is True

def test_lucky_special_baba():
    assert is_lucky("xxbabaxx", []) is True

def test_lucky_special_aba():
    assert is_lucky("xxabaxx", []) is True

def test_lucky_baba_matches_before_aba():
    # "baba" contains "aba" — the longer match "baba" should win
    match = find_lucky_match("xxbabaxx", [])
    assert match is not None and match.lower() == "baba"

def test_lucky_special_f00d():
    assert is_lucky("xxf00dxx", []) is True

def test_lucky_consecutive_digits():
    assert is_lucky("aa123bb", []) is True   # ascending digits

def test_lucky_consecutive_letters():
    assert is_lucky("xxabcyy", []) is True   # ascending letters

def test_lucky_consecutive_4_chars():
    assert is_lucky("xx5678yy", []) is True  # ascending 4-char

def test_lucky_888():
    assert is_lucky("abc888def", []) is True  # repeated non-4 char

def test_lucky_777():
    assert is_lucky("xxx777yyy", []) is True

def test_lucky_666():
    assert is_lucky("aaa666bbb", []) is True

def test_lucky_repeated_not_4():
    assert is_lucky("xxeeexx", []) is True

def test_lucky_mountain_abcba():
    # "abcba" = ascending then descending → 功德圓滿，有始有終
    assert is_lucky("xabcbaxx", []) is True

def test_lucky_mountain_12321():
    assert is_lucky("xx12321xx", []) is True

def test_lucky_mountain_match_value():
    match = find_lucky_match("xx12321xx", [])
    assert match == "12321"

def test_mountain_minimum_arm():
    # "aba" has only 1 step each direction — not enough (need 2+)
    assert _find_mountain_run("xabaxxx") is None

def test_mountain_detected():
    assert _find_mountain_run("xabcbaxx") == "abcba"

def test_not_lucky_repeated_4():
    # Triple 4 is UNLUCKY, not lucky — use a hash with no other lucky patterns
    assert is_lucky("d8444e5b", []) is False

def test_not_lucky_plain():
    assert is_lucky("3f7a5d8c2b", []) is False

def test_not_lucky_2_consecutive():
    assert is_lucky("aa12bb", []) is False   # only 2 ascending, not enough

def test_not_lucky_2_repeated():
    assert is_lucky("aabb", []) is False     # only 2 repeated, not enough


# --- Default unlucky patterns ---

def test_unlucky_dead():
    assert find_unlucky_match("xxdeadxx") is not None

def test_unlucky_404():
    assert find_unlucky_match("a404b") is not None

def test_unlucky_bad():
    assert find_unlucky_match("xxbadxx") is not None

def test_unlucky_f001():
    assert find_unlucky_match("xxf001xx") is not None

def test_unlucky_beef():
    assert find_unlucky_match("xxbeefxx") is not None

def test_unlucky_deaf():
    assert find_unlucky_match("xxdeafxx") is not None

def test_unlucky_triple_4():
    assert find_unlucky_match("abc444def") is not None

def test_unlucky_quad_4():
    assert find_unlucky_match("xx4444xx") is not None

def test_unlucky_descending_321():
    assert find_unlucky_match("xx321xx") is not None

def test_unlucky_descending_fedc():
    assert find_unlucky_match("xxfedcxx") is not None

def test_unlucky_descending_7654():
    assert find_unlucky_match("xx7654xx") is not None

def test_unlucky_8787():
    assert find_unlucky_match("xx8787xx") is not None

def test_unlucky_7878():
    assert find_unlucky_match("xx7878xx") is not None

def test_unlucky_878787():
    assert find_unlucky_match("xx878787xx") is not None

def test_not_unlucky_plain():
    assert find_unlucky_match("3f7a5d8c2b") is None

def test_not_unlucky_double_87():
    # Single 87 is fine, need repeated
    assert find_unlucky_match("xx87xx") is None

def test_not_unlucky_single_4():
    assert find_unlucky_match("xx4xx") is None

def test_not_unlucky_double_4():
    assert find_unlucky_match("xx44xx") is None


# --- Unlucky overrides lucky when both appear ---

def test_unlucky_overrides_lucky_special():
    # "cafe" lucky + "dead" unlucky as independent patterns — unlucky wins
    assert is_lucky("xxcafedeadxx", []) is False

def test_unlucky_overrides_lucky_ascending():
    # "abc" lucky ascending + "404" unlucky — unlucky wins
    assert is_lucky("xx404abcxx", []) is False

def test_unlucky_overrides_lucky_repeated():
    # "aaa" lucky repeated + "bad" unlucky — unlucky wins
    assert is_lucky("xxaaabadfxx", []) is False

def test_unlucky_overrides_lucky_mountain():
    # Mountain "abcba" lucky + independent "dead" unlucky — unlucky wins
    assert is_lucky("xabcbadeadxx", []) is False

def test_mountain_shields_descending_arm():
    # "cba" is the right arm of mountain "abcba" — not independently unlucky
    assert find_unlucky_match("xabcbaxx") is None

def test_independent_descending_still_unlucky():
    # "321" after the mountain is independent — still unlucky
    assert find_unlucky_match("xabcba321xx") is not None

def test_c0ffee_shields_0ff():
    # "0ff" inside "c0ffee" is shielded — not independently unlucky
    assert find_unlucky_match("aac0ffeexx") is None

def test_standalone_0ff_is_unlucky():
    # "0ff" on its own (not inside c0ffee) is still unlucky
    assert find_unlucky_match("xx0ffyyyy") is not None

def test_custom_targets_not_affected_by_override():
    # Custom targets bypass the unlucky-override logic entirely
    assert is_lucky("cafedeadxx", ["cafe"]) is True


# --- Custom targets ---

def test_custom_single_target_match():
    assert is_lucky("deadbeef", ["dead"]) is True

def test_custom_single_target_no_match():
    assert is_lucky("abc888def", ["dead"]) is False

def test_custom_multiple_targets_first_matches():
    assert is_lucky("abc404def", ["404", "dead"]) is True

def test_custom_multiple_targets_second_matches():
    assert is_lucky("deadbeef", ["404", "dead"]) is True

def test_custom_multiple_targets_none_match():
    assert is_lucky("abc123def", ["404", "dead"]) is False

def test_custom_target_case_insensitive():
    assert is_lucky("abcDEADef", ["dead"]) is True


# --- find_lucky_match returns matched substring ---

def test_find_lucky_returns_match():
    match = find_lucky_match("xxcafexx", [])
    assert match is not None
    assert match.lower() == "cafe"

def test_find_lucky_ascending_returns_match():
    match = find_lucky_match("xx123xx", [])
    assert match == "123"

def test_find_lucky_repeated_returns_match():
    match = find_lucky_match("xxaaaxx", [])
    assert match == "aaa"


# --- MinerTool ---

from kismet.agent.tools.mine import MinerTool
from kismet.agent.tools.git import GitContext
from kismet.agent.session import KismetSession


def _make_session(predicted_hash: str = "3f7a5d8c2b1e6f") -> KismetSession:
    return KismetSession(
        diff="diff content",
        original_message="feat: add feature",
        current_message="feat: add feature",
        predicted_hash=predicted_hash,
        tree_sha="a" * 40,
        parent_sha="b" * 40,
        author_name="Test",
        author_email="t@t.com",
        fixed_timestamp="1714300000 +0800",
    )


def test_mine_succeeds_when_lucky_hash_found():
    mock_divine = MagicMock()
    mock_divine.rephrase_message.return_value = ("feat: new wording", 50, 20)
    mock_git = MagicMock()
    mock_git.compute_hash.return_value = "abc888def"  # repeated non-4 → lucky
    mock_renderer = MagicMock()

    session = _make_session()
    tool = MinerTool(divine_tool=mock_divine, git_tool=mock_git, config=MagicMock(max_mine_attempts=10))
    success = tool.mine(session, mock_renderer, targets=[])

    assert success is True
    assert session.current_message == "feat: new wording"
    assert session.predicted_hash == "abc888def"
    assert session.mine_attempts == 1


def test_mine_succeeds_on_ascending_hash():
    mock_divine = MagicMock()
    mock_divine.rephrase_message.return_value = ("feat: reword", 50, 20)
    mock_git = MagicMock()
    mock_git.compute_hash.return_value = "xx123abc"  # ascending "123"
    mock_renderer = MagicMock()

    session = _make_session()
    tool = MinerTool(divine_tool=mock_divine, git_tool=mock_git, config=MagicMock(max_mine_attempts=10))
    success = tool.mine(session, mock_renderer, targets=[])

    assert success is True


def test_mine_fails_after_max_attempts():
    mock_divine = MagicMock()
    mock_divine.rephrase_message.return_value = ("feat: rephrased", 50, 20)
    mock_git = MagicMock()
    mock_git.compute_hash.return_value = "plain_hash_no_luck"
    mock_renderer = MagicMock()

    session = _make_session()
    tool = MinerTool(divine_tool=mock_divine, git_tool=mock_git, config=MagicMock(max_mine_attempts=3))
    success = tool.mine(session, mock_renderer, targets=[])

    assert success is False
    assert session.mine_attempts == 3


def test_mine_accumulates_tokens():
    mock_divine = MagicMock()
    mock_divine.rephrase_message.return_value = ("feat: rephrased", 60, 25)
    mock_git = MagicMock()
    mock_git.compute_hash.side_effect = ["no_luck_1", "no_luck_2", "abc888xyz"]
    mock_renderer = MagicMock()

    session = _make_session()
    tool = MinerTool(divine_tool=mock_divine, git_tool=mock_git, config=MagicMock(max_mine_attempts=10))
    tool.mine(session, mock_renderer, targets=[])

    assert session.total_input_tokens == 180   # 60 * 3
    assert session.total_output_tokens == 75   # 25 * 3
