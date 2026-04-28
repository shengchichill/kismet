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
