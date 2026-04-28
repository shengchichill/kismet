from unittest.mock import MagicMock
from kismet.agent.tools.mine import is_lucky


# --- Default lucky list (no targets specified) ---

def test_lucky_888():
    assert is_lucky("abc888def", []) is True

def test_lucky_168():
    assert is_lucky("a168bcd", []) is True

def test_lucky_777():
    assert is_lucky("xxx777yyy", []) is True

def test_lucky_666():
    assert is_lucky("aaa666bbb", []) is True

def test_lucky_consecutive_digits():
    assert is_lucky("aa123bb", []) is True   # 3 consecutive ascending digits

def test_lucky_consecutive_letters():
    assert is_lucky("xxabcyy", []) is True   # 3 consecutive ascending letters

def test_lucky_palindrome_4():
    assert is_lucky("xxabbaxx", []) is True  # 4-char palindrome

def test_lucky_palindrome_6():
    assert is_lucky("xabcbaxx", []) is True  # 5-char palindrome abcba

def test_not_lucky_plain():
    assert is_lucky("3f7a404d8c2b", []) is False

def test_not_lucky_2_consecutive():
    # "12" is only 2 consecutive — not enough
    assert is_lucky("aa12bb", []) is False

def test_not_lucky_palindrome_3():
    # 3-char palindromes (like "aba") don't count — use string with no 4+ palindrome
    assert is_lucky("c3f7aba4d8", []) is False


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


# --- MinerTool ---

from kismet.agent.tools.mine import MinerTool
from kismet.agent.tools.git import GitContext
from kismet.agent.session import KismetSession


def _make_session(predicted_hash: str = "3f7a404d8c2b1e5f") -> KismetSession:
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
    mock_git.compute_hash.return_value = "abc888def"  # lucky on first try
    mock_renderer = MagicMock()

    session = _make_session()
    tool = MinerTool(divine_tool=mock_divine, git_tool=mock_git, config=MagicMock(max_mine_attempts=10))
    success = tool.mine(session, mock_renderer, targets=[])

    assert success is True
    assert session.current_message == "feat: new wording"
    assert session.predicted_hash == "abc888def"
    assert session.mine_attempts == 1


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
