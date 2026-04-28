import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import openai
import yaml


@dataclass
class ModelCosts:
    input_cost_per_1m: float
    output_cost_per_1m: float


@dataclass
class Config:
    litellm_base_url: str
    litellm_api_key: str
    model: str
    max_mine_attempts: int
    max_message_tokens: int
    _costs_path: str
    _costs_cache: Optional[dict] = None

    def get_model_costs(self) -> Optional[ModelCosts]:
        if self._costs_cache is None:
            try:
                with open(self._costs_path) as f:
                    self._costs_cache = yaml.safe_load(f) or {}
            except FileNotFoundError:
                self._costs_cache = {}
        entry = self._costs_cache.get(self.model)
        if entry is None:
            return None
        return ModelCosts(
            input_cost_per_1m=entry["input_cost_per_1m"],
            output_cost_per_1m=entry["output_cost_per_1m"],
        )

    def make_llm_client(self) -> openai.OpenAI:
        return openai.OpenAI(
            base_url=self.litellm_base_url,
            api_key=self.litellm_api_key,
        )

    def compute_cost_usd(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        costs = self.get_model_costs()
        if costs is None:
            return None
        return (
            input_tokens / 1_000_000 * costs.input_cost_per_1m
            + output_tokens / 1_000_000 * costs.output_cost_per_1m
        )


_DEFAULT_COSTS_PATH = str(Path(__file__).parent.parent / "model_costs.yml")


def load_config(costs_path: str = _DEFAULT_COSTS_PATH) -> Config:
    base_url = os.environ.get("LITELLM_BASE_URL")
    api_key = os.environ.get("LITELLM_API_KEY")
    if not base_url:
        raise ValueError("LITELLM_BASE_URL environment variable is required")
    if not api_key:
        raise ValueError("LITELLM_API_KEY environment variable is required")
    return Config(
        litellm_base_url=base_url,
        litellm_api_key=api_key,
        model=os.environ.get("KISMET_MODEL", "gpt-4o-mini"),
        max_mine_attempts=int(os.environ.get("MAX_MINE_ATTEMPTS", "10")),
        max_message_tokens=int(os.environ.get("MAX_MESSAGE_TOKENS", "200")),
        _costs_path=costs_path,
    )
