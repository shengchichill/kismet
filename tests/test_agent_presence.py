from unittest.mock import MagicMock, patch

import pytest

from kismet.agent.agent import KismetAgent
from kismet.agent.session import KismetSession
from kismet.config import Config


def _make_agent() -> KismetAgent:
    config = Config(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test-key",
        model="gpt-4o-mini",
        max_mine_attempts=3,
        max_message_tokens=100,
        _costs_path="nonexistent.yml",
        mage_mode="gui",
    )
    agent = KismetAgent.__new__(KismetAgent)
    agent.config = config
    agent.git = MagicMock()
    agent.divine = MagicMock()
    agent.miner = MagicMock()
    agent.renderer = MagicMock()
    return agent


def _make_session() -> KismetSession:
    return KismetSession(
        diff="diff",
        original_message="feat: test",
        current_message="feat: test",
        predicted_hash="abc123",
        tree_sha="a" * 40,
        parent_sha="b" * 40,
        author_name="Test",
        author_email="t@t.com",
        fixed_timestamp="1714300000 +0800",
    )


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_mine_writes_mining_and_success(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.miner.mine.return_value = True
    divine_result = MagicMock()
    divine_result.k_value = 85
    divine_result.input_tokens = 10
    divine_result.output_tokens = 5
    agent.divine.divine.return_value = divine_result
    agent.divine.generate_mining_report.return_value = ("great", 5, 3)

    agent.run_mine([])

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "mining" in states
    assert "success" in states


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_mine_writes_failed_and_blessing_on_fail(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.miner.mine.return_value = False

    agent.run_mine([])

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "mining" in states
    assert "failed" in states
    assert "blessing" in states


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_curse_writes_curse_and_failed_on_miss(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.divine.rephrase_message.return_value = ("feat: rephrased", 10, 5)
    agent.git.commit.return_value = "deadbeef"

    agent.run_curse([])

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "curse" in states
    assert "failed" in states


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_divine_writes_divine(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.divine.divine.return_value = MagicMock(
        k_value=50, reading="test", tarot_card="X", tarot_position="up",
        input_tokens=10, output_tokens=5,
    )

    agent.run_divine()

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "divine" in states


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_commit_high_k_writes_divine_and_success(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.divine.divine.return_value = MagicMock(
        k_value=90, reading="test", tarot_card="X", tarot_position="up",
        input_tokens=10, output_tokens=5,
    )
    agent.git.commit.return_value = "deadbeef"

    agent.run_commit()

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "divine" in states
    assert "success" in states
    assert "mining" not in states


@patch("kismet.agent.agent.write_state")
@patch("kismet.agent.agent.ensure_mage_running")
def test_run_commit_low_k_writes_mining(mock_ensure, mock_write):
    agent = _make_agent()
    agent.git.get_staged_diff.return_value = "diff"
    ctx = MagicMock(tree_sha="a"*40, parent_sha="b"*40,
                    author_name="T", author_email="t@t.com",
                    fixed_timestamp="1714300000 +0800")
    agent.git.get_context.return_value = ctx
    agent.divine.generate_message.return_value = ("feat: test", 10, 5)
    agent.git.compute_hash.return_value = "abc123"
    agent.divine.divine.return_value = MagicMock(
        k_value=20, reading="test", tarot_card="X", tarot_position="up",
        input_tokens=10, output_tokens=5,
    )
    agent.miner.mine.return_value = True
    agent.git.commit.return_value = "deadbeef"

    agent.run_commit()

    mock_ensure.assert_called_once()
    states = [c.args[0] for c in mock_write.call_args_list]
    assert "divine" in states
    assert "mining" in states
    assert "success" in states
