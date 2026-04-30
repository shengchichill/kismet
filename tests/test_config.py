import os
import pytest
from kismet.config import Config, ModelCosts, load_config


def test_load_config_reads_env_vars(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    cfg = load_config()
    assert cfg.litellm_base_url == "http://proxy:4000"
    assert cfg.litellm_api_key == "test-key"
    assert cfg.model == "gpt-4o-mini"  # default
    assert cfg.max_mine_attempts == 10  # default
    assert cfg.max_message_tokens == 200  # default
    assert cfg.require_prayer_pose is True
    assert cfg.prayer_pose_timeout_seconds == 15


def test_load_config_reads_prayer_pose_env_vars(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("KISMET_REQUIRE_PRAYER_POSE", "0")
    monkeypatch.setenv("KISMET_PRAYER_POSE_TIMEOUT", "3.5")
    cfg = load_config()

    assert cfg.require_prayer_pose is False
    assert cfg.prayer_pose_timeout_seconds == 3.5


def test_load_config_raises_if_missing_required(monkeypatch):
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="LITELLM_BASE_URL"):
        load_config()


def test_get_model_costs_known_model(tmp_path, monkeypatch):
    costs_file = tmp_path / "model_costs.yml"
    costs_file.write_text(
        "gpt-4o-mini:\n  input_cost_per_1m: 0.15\n  output_cost_per_1m: 0.60\n"
    )
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "key")
    cfg = load_config(costs_path=str(costs_file))
    costs = cfg.get_model_costs()
    assert costs is not None
    assert costs.input_cost_per_1m == 0.15
    assert costs.output_cost_per_1m == 0.60


def test_get_model_costs_unknown_model(tmp_path, monkeypatch):
    costs_file = tmp_path / "model_costs.yml"
    costs_file.write_text("gpt-4o:\n  input_cost_per_1m: 2.50\n  output_cost_per_1m: 10.00\n")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://proxy:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "key")
    monkeypatch.setenv("KISMET_MODEL", "unknown-model")
    cfg = load_config(costs_path=str(costs_file))
    assert cfg.get_model_costs() is None
