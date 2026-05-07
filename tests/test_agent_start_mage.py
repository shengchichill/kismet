import contextlib
from unittest.mock import MagicMock, patch

import pytest

from kismet.agent.agent import KismetAgent
from kismet.config import Config
from kismet.mage.terminal_pet import TerminalMagePet


def _make_agent(mage_mode: str = "gui") -> KismetAgent:
    config = Config(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test-key",
        model="gpt-4o-mini",
        max_mine_attempts=3,
        max_message_tokens=100,
        _costs_path="nonexistent.yml",
        mage_mode=mage_mode,
    )
    agent = KismetAgent.__new__(KismetAgent)
    agent.config = config
    return agent


def test_start_mage_gui_calls_ensure_running():
    agent = _make_agent(mage_mode="gui")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="gui"), \
         patch("kismet.agent.agent.ensure_mage_running") as mock_ensure:
        ctx = agent._start_mage()
        mock_ensure.assert_called_once()
        assert isinstance(ctx, contextlib.nullcontext)


def test_start_mage_terminal_returns_terminal_pet():
    agent = _make_agent(mage_mode="terminal")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="terminal"):
        ctx = agent._start_mage()
        assert isinstance(ctx, TerminalMagePet)


def test_start_mage_off_no_ensure_running():
    agent = _make_agent(mage_mode="off")
    with patch("kismet.agent.agent.detect_mage_mode", return_value="off"), \
         patch("kismet.agent.agent.ensure_mage_running") as mock_ensure:
        ctx = agent._start_mage()
        mock_ensure.assert_not_called()
        assert isinstance(ctx, contextlib.nullcontext)
