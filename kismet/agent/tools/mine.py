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
