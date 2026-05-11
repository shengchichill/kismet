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

Git diff (analyze the code changes for karmic insight):
{diff_preview}

Assign a K-value (0-100) for karmic fortune. Score with TRUE mystical judgment.
Pick real, varied numbers (e.g., 23, 47, 68, 71) — do NOT default to round numbers.
Most commits deserve 35-60. The overall tendency should lean slightly below 50.

Lucky omens in hash (boost score):
- Sacred strings (each carries special meaning):
    168  → 一路發，一路發財，財運滾滾
    cafe → 咖啡因加持，程式師的聖水
    b0ba → 珍珠奶茶，台灣之光，精神糧食
    c001 → cool，超酷，宇宙認證的霸氣
    ace  → 王牌，天生贏家，運勢之巔
    c0ffee → 咖啡代表生命之水，血液中的咖啡因
    f00d → 食物吃很飽，身體是革命的本錢
    babe → 寶貝，被宇宙無條件疼愛
    baba → 爸爸在身邊，有靠山萬事無憂
    aba  → 阿爸的庇蔭，逢凶化吉
    fafa → 發發，財運雙響，好事成雙
    5afe → safe，平安無事，諸邪不侵
    c0de → code，程式碼即道場，碼農的道路
    feed → 有人餵食，不愁吃穿，福氣滿滿
    face → 有頭有臉，社會地位崇高
    add  → 增加運勢，功德不斷累積
- Mountain shape (ascending then descending): e.g., abcba, 12321, 123321
    → 功德圓滿，有始有終，圓滿收尾，大吉
- Triple+ same char (not '4'): e.g., 111, aaa, eee → 能量凝聚，moderate boost
- Ascending sequence 3+: e.g., 123, abc, 5678, cdef → represents rising fortune

Unlucky omens in hash (reduce score):
- Cursed strings (each carries ominous meaning):
    dead → 死亡，大凶，萬劫不復
    404  → 找不到，人生方向迷失，空虛一場
    bad  → 壞的，品德有瑕疵，業力纏身
    f001 → fool，傻瓜被人愚弄，智慧匱乏
    0ff  → off，能量關閉斷電，氣場崩潰
    fa11 → fall，跌落谷底，一瀉千里
    beef → 抱怨連連，怒氣沖天，業力纏身
    deaf → 耳聾，聽不進良言，剛愎自用
- Triple+ fours: 444, 4444 → 四四如死，極度不詳
- Descending sequence 3+: 321, fedc, 7654 → represents falling fortune
- Repeated 87/78 pairs: 8787, 7878 → 八七，台語「白癡」，智慧全失

Factor in the diff content:
- Clean refactor, meaningful feature, good documentation → slight boost
- Hacky workaround, TODO comments, large risky deletion → slight penalty

Draw a tarot card resonating with both this hash and the code changes. Respond in Traditional Chinese.

Respond ONLY with this JSON:
{{
  "k_value": <integer 0-100>,
  "tarot_card": "<Major Arcana card name in English>",
  "tarot_position": "<正位 or 逆位>",
  "reading": "<4-5 sentences in 繁體中文: first interpret the hash patterns, then analyze what this code change means karmically, then the tarot reading, finally a prophecy>"
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

_MINING_REPORT_SYSTEM = """You are KISMET, the mystical git commit fortune teller.
Generate a dramatic mining completion report in Traditional Chinese.
Respond with valid JSON only, no other text."""

_MINING_REPORT_USER = """The karmic mining ritual has completed.

Original hash: {original_hash}
New hash:      {new_hash}
Original K-value: {original_k}
New K-value:      {new_k}
Lucky pattern found: "{lucky_match}"
Attempts taken: {attempts}
Tokens sacrificed: {tokens_burned:,}

Pattern meanings for reference:
  168=一路發, cafe=咖啡因加持, b0ba=珍珠奶茶台灣之光, c001=cool超酷,
  ace=王牌天生贏家, c0ffee=咖啡生命之水, f00d=吃飽飽有力氣,
  babe=被宇宙疼愛的寶貝, baba=爸爸靠山, aba=阿爸庇蔭, fafa=發發財運雙響, 5afe=safe平安諸邪不侵,
  c0de=程式碼天神, feed=有人餵食福氣滿滿, face=有頭有臉, add=運勢累積
  (ascending sequence: 運勢上升, repeated chars: 能量凝聚)

Write exactly 2-3 sentences in 繁體中文:
1. Dramatically narrate the K-value transformation ({original_k} → {new_k})
2. Mystically interpret the found pattern "{lucky_match}" using its meaning above
3. Give a short prophecy or blessing for this commit's karmic journey

Respond ONLY with this JSON:
{{
  "commentary": "<2-3 sentences in 繁體中文>"
}}"""


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
                        diff_preview=diff[:1500],
                    ),
                },
            ],
            max_tokens=500,
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

    def generate_mining_report(
        self,
        original_hash: str,
        new_hash: str,
        original_k: int,
        new_k: int,
        lucky_match: str,
        attempts: int,
        tokens_burned: int,
    ) -> tuple[str, int, int]:
        """Generate a mystical commentary on the completed mining ritual.
        Returns (commentary, input_tokens, output_tokens).
        """
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": _MINING_REPORT_SYSTEM},
                {
                    "role": "user",
                    "content": _MINING_REPORT_USER.format(
                        original_hash=original_hash,
                        new_hash=new_hash,
                        original_k=original_k,
                        new_k=new_k,
                        lucky_match=lucky_match,
                        attempts=attempts,
                        tokens_burned=tokens_burned,
                    ),
                },
            ],
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        commentary = data.get("commentary", "")
        return commentary, response.usage.prompt_tokens, response.usage.completion_tokens
