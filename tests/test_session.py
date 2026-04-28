import pytest
from kismet.agent.session import KismetSession


def test_session_defaults():
    session = KismetSession(
        diff="diff content",
        original_message="feat: add feature",
        current_message="feat: add feature",
        predicted_hash="abc123",
        tree_sha="tree456",
        parent_sha="parent789",
        author_name="Test User",
        author_email="test@example.com",
        fixed_timestamp="1714300000 +0800",
    )
    assert session.total_input_tokens == 0
    assert session.total_output_tokens == 0
    assert session.total_cost_usd is None
    assert session.k_value == 0
    assert session.mine_attempts == 0
    assert session.divination_text == ""
    assert session.tarot_card == ""
    assert session.tarot_position == ""
    assert session.original_predicted_hash == ""


def test_session_accepts_none_parent_sha():
    session = KismetSession(
        diff="diff",
        original_message="msg",
        current_message="msg",
        predicted_hash="abc",
        tree_sha="tree",
        parent_sha=None,
        author_name="User",
        author_email="u@e.com",
        fixed_timestamp="1714300000 +0800",
    )
    assert session.parent_sha is None


def test_session_fields_are_mutable():
    session = KismetSession(
        diff="diff",
        original_message="msg",
        current_message="msg",
        predicted_hash="abc",
        tree_sha="tree",
        parent_sha="parent",
        author_name="User",
        author_email="u@e.com",
        fixed_timestamp="1714300000 +0800",
    )
    session.total_input_tokens = 1000
    session.total_output_tokens = 500
    session.total_cost_usd = 0.000450
    session.k_value = 42
    session.mine_attempts = 3
    assert session.total_input_tokens == 1000
    assert session.total_output_tokens == 500
    assert session.total_cost_usd == pytest.approx(0.000450)
    assert session.k_value == 42
    assert session.mine_attempts == 3
