import json
from unittest.mock import MagicMock
import pytest
from kismet.agent.tools.divine import DivinationTool, DivinationResult


def _make_mock_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    response = MagicMock()
    response.choices[0].message.content = content
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    return response


@pytest.fixture
def mock_config():
    from kismet.config import Config
    return Config(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test-key",
        model="gpt-4o-mini",
        max_mine_attempts=3,
        max_message_tokens=100,
        _costs_path="nonexistent.yml",
    )


def test_divine_returns_divination_result(mock_config):
    payload = json.dumps({
        "k_value": 23,
        "tarot_card": "The Tower",
        "tarot_position": "逆位",
        "reading": "此 hash 帶有不詳之氣，系統崩潰在即。",
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(payload, 120, 60)

    tool = DivinationTool(mock_config, client=mock_client)
    result = tool.divine(
        hash_str="3f7a404d8c2b",
        message="feat: add feature",
        diff="diff --git a/f.txt",
    )

    assert isinstance(result, DivinationResult)
    assert result.k_value == 23
    assert result.tarot_card == "The Tower"
    assert result.tarot_position == "逆位"
    assert "不詳" in result.reading
    assert result.input_tokens == 120
    assert result.output_tokens == 60


def test_divine_k_value_clamped(mock_config):
    payload = json.dumps({
        "k_value": 150,  # out of range
        "tarot_card": "The Fool",
        "tarot_position": "正位",
        "reading": "運勢極佳。",
    })
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(payload)
    tool = DivinationTool(mock_config, client=mock_client)
    result = tool.divine("abc888", "msg", "diff")
    assert 0 <= result.k_value <= 100


def test_generate_message_returns_string(mock_config):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "feat: add user authentication", 80, 20
    )
    tool = DivinationTool(mock_config, client=mock_client)
    message, in_tok, out_tok = tool.generate_message("diff --git a/auth.py +def login():")
    assert message == "feat: add user authentication"
    assert in_tok == 80
    assert out_tok == 20


def test_rephrase_message_returns_string(mock_config):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "feat: implement login functionality", 70, 15
    )
    tool = DivinationTool(mock_config, client=mock_client)
    message, in_tok, out_tok = tool.rephrase_message(
        "feat: add user authentication", attempt=1, max_attempts=10
    )
    assert message == "feat: implement login functionality"
    assert in_tok == 70
