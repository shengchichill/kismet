import json
from dataclasses import dataclass
from typing import Optional

import openai

from kismet.config import Config

_DIVINATION_SYSTEM = """You are KISMET, a mystical git commit fortune teller who speaks with great authority.
Analyze commit hashes and divine their karmic fortune.
You MUST respond with valid JSON only, no other text."""

_DIVINATION_USER = """Analyze this git commit hash and divine its fortune.

Commit hash: {hash_str}
Commit message: {message}
Git diff summary: {diff_preview}

Assign a K-value (0-100) representing karmic fortune. Be STRICT — most commits deserve 41-60.

Deduct heavily for:
- Hash contains "404", "dead", "bad", "err", "f00d" → -30 each
- Hash starts with "000" (void energy) → -20
- Three identical consecutive chars like "aaa" → -10

Add bonus only for:
- Hash contains "888", "168", "777" → +20 each
- Clear ascending sequence of 4+ chars like "1234" → +15
- Perfect palindrome of 4+ chars like "abba" → +10

Draw a tarot card that resonates with this hash. Respond in Traditional Chinese for the reading.

Respond ONLY with this JSON:
{{
  "k_value": <integer 0-100>,
  "tarot_card": "<Major Arcana card name in English>",
  "tarot_position": "<正位 or 逆位>",
  "reading": "<2-3 sentences of mystical reading in 繁體中文>"
}}"""

_GENERATE_MSG_SYSTEM = """You are a helpful git commit message generator.
Write concise, conventional commit messages based on git diffs.
Respond with ONLY the commit message, no explanation or quotes."""

_GENERATE_MSG_USER = """Write a git commit message for this diff.
Use conventional commits format (feat/fix/refactor/chore/docs/test).
Keep it under {max_tokens} tokens.

{diff}"""

_REPHRASE_MSG_SYSTEM = """You are a git commit message rewriter.
Rephrase the given commit message while preserving its meaning.
Respond with ONLY the rephrased message, no explanation or quotes."""

_REPHRASE_MSG_USER = """Rephrase this commit message (attempt {attempt}/{max_attempts}).
Each attempt must be meaningfully different — vary length, detail level, or wording.
Keep it under {max_tokens} tokens.

Original: {message}"""


@dataclass
class DivinationResult:
    k_value: int
    tarot_card: str
    tarot_position: str
    reading: str
    input_tokens: int
    output_tokens: int


class DivinationTool:
    def __init__(self, config: Config, client: Optional[openai.OpenAI] = None):
        self.config = config
        self.client = client or config.make_llm_client()

    def generate_message(self, diff: str) -> tuple[str, int, int]:
        """Generate a commit message from a diff. Returns (message, input_tokens, output_tokens)."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": _GENERATE_MSG_SYSTEM},
                {
                    "role": "user",
                    "content": _GENERATE_MSG_USER.format(
                        max_tokens=self.config.max_message_tokens,
                        diff=diff[:3000],
                    ),
                },
            ],
            max_tokens=self.config.max_message_tokens,
        )
        message = response.choices[0].message.content.strip()
        return message, response.usage.prompt_tokens, response.usage.completion_tokens

    def rephrase_message(self, message: str, attempt: int, max_attempts: int) -> tuple[str, int, int]:
        """Rephrase a commit message. Returns (new_message, input_tokens, output_tokens)."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": _REPHRASE_MSG_SYSTEM},
                {
                    "role": "user",
                    "content": _REPHRASE_MSG_USER.format(
                        attempt=attempt,
                        max_attempts=max_attempts,
                        max_tokens=self.config.max_message_tokens,
                        message=message,
                    ),
                },
            ],
            max_tokens=self.config.max_message_tokens,
        )
        new_msg = response.choices[0].message.content.strip()
        return new_msg, response.usage.prompt_tokens, response.usage.completion_tokens

    def divine(self, hash_str: str, message: str, diff: str) -> DivinationResult:
        """Divine the karmic fortune of a commit hash. Returns DivinationResult."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": _DIVINATION_SYSTEM},
                {
                    "role": "user",
                    "content": _DIVINATION_USER.format(
                        hash_str=hash_str,
                        message=message,
                        diff_preview=diff[:500],
                    ),
                },
            ],
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        k_value = max(0, min(100, int(data["k_value"])))
        return DivinationResult(
            k_value=k_value,
            tarot_card=data.get("tarot_card", "The Fool"),
            tarot_position=data.get("tarot_position", "正位"),
            reading=data.get("reading", ""),
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
