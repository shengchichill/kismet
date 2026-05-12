import json
import random
from dataclasses import dataclass
from typing import Optional

import openai

from kismet.config import Config

_MAJOR_ARCANA = [
    "The Fool", "The Magician", "The High Priestess", "The Empress",
    "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
    "Strength", "The Hermit", "Wheel of Fortune", "Justice",
    "The Hanged Man", "Death", "Temperance", "The Devil",
    "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World",
]

_LUCKY_MEANINGS: dict[str, str] = {
    "168":    "一路發，一路發財，財運滾滾",
    "cafe":   "咖啡因加持，程式師的聖水",
    "b0ba":   "珍珠奶茶，台灣之光，精神糧食",
    "c001":   "cool，超酷，宇宙認證的霸氣",
    "ace":    "王牌，天生贏家，運勢之巔",
    "c0ffee": "咖啡代表生命之水，血液中的咖啡因",
    "f00d":   "食物吃很飽，身體是革命的本錢",
    "babe":   "寶貝，被宇宙無條件疼愛",
    "baba":   "爸爸在身邊，有靠山萬事無憂",
    "aba":    "阿爸的庇蔭，逢凶化吉",
    "fafa":   "發發，財運雙響，好事成雙",
    "5afe":   "safe，平安無事，諸邪不侵",
    "c0de":   "code，程式碼即道場，碼農的道路",
    "feed":   "有人餵食，不愁吃穿，福氣滿滿",
    "face":   "有頭有臉，社會地位崇高",
    "add":    "增加運勢，功德不斷累積",
}

_UNLUCKY_MEANINGS: dict[str, str] = {
    "dead": "死亡，大凶，萬劫不復",
    "404":  "找不到，人生方向迷失，空虛一場",
    "bad":  "壞的，品德有瑕疵，業力纏身",
    "f001": "fool，傻瓜被人愚弄，智慧匱乏",
    "0ff":  "off，能量關閉斷電，氣場崩潰",
    "fa11": "fall，跌落谷底，一瀉千里",
    "beef": "抱怨連連，怒氣沖天，業力纏身",
    "deaf": "耳聾，聽不進良言，剛愎自用",
}


def draw_tarot_card(hash_str: str) -> tuple[str, str]:
    """Draw a Major Arcana card deterministically from the commit hash."""
    seed = int(hash_str, 16)
    rng = random.Random(seed)
    card = rng.choice(_MAJOR_ARCANA)
    position = rng.choice(["正位", "逆位"])
    return card, position


def draw_three_tarot_cards(hash_str: str) -> list[tuple[str, str]]:
    """Draw three Major Arcana cards deterministically. First card matches draw_tarot_card."""
    seed = int(hash_str, 16)
    rng = random.Random(seed)
    return [(rng.choice(_MAJOR_ARCANA), rng.choice(["正位", "逆位"])) for _ in range(3)]


def _describe_lucky_pattern(match: Optional[str]) -> str:
    if match is None:
        return "None"
    meaning = _LUCKY_MEANINGS.get(match.lower())
    if meaning:
        return f"{match} — {meaning}"
    h = match.lower()
    if len(set(h)) == 1:
        return f"{match} — 能量凝聚，三連相同字符，氣場聚集"
    if len(h) >= 3 and all(ord(h[i]) - ord(h[i - 1]) == 1 for i in range(1, len(h))):
        return f"{match} — 節節高升，運勢上揚，前途光明"
    return f"{match} — 功德圓滿，有始有終，圓滿收尾"


def _describe_unlucky_pattern(match: Optional[str]) -> str:
    if match is None:
        return "None"
    meaning = _UNLUCKY_MEANINGS.get(match.lower())
    if meaning:
        return f"{match} — {meaning}"
    h = match.lower()
    if all(c == "4" for c in h):
        return f"{match} — 四連死字，極度不詳，萬劫不復"
    if "87" in h or "78" in h:
        return f"{match} — 八七重複，台語白癡，智慧全失"
    if len(h) >= 3 and all(ord(h[i]) - ord(h[i - 1]) == -1 for i in range(1, len(h))):
        return f"{match} — 節節下滑，運勢下墜，前路艱險"
    return f"{match} — 凶兆序列，不詳之兆"


_DIVINATION_SYSTEM = """You are KISMET, a mystical git commit fortune teller who speaks with great authority.
Analyze commit hashes and divine their karmic fortune.
You MUST respond with valid JSON only, no other text."""

_DIVINATION_USER = """Analyze this git commit hash and divine its fortune.

Commit hash: {hash_str}
Commit message: {message}

Git diff (analyze the code changes for karmic insight):
{diff_preview}

Pre-computed divination:
  Lucky pattern:    {lucky_desc}
  Unlucky omen:     {unlucky_desc}
  Tarot spread (三張牌陣, Past → Present → Future):
    過去: {tarot_past_card} ({tarot_past_pos})
    現在: {tarot_present_card} ({tarot_present_pos})
    未來: {tarot_future_card} ({tarot_future_pos})

Assign a K-value (0-100):
  Cursed Tier  [0-20]   — unlucky omen is present (curse wins even if lucky also appears)
  Blessed Tier [80-100] — lucky pattern present, no unlucky omen
  Mortal Tier  [35-60]  — neither; lean slightly below 50
  Pick precise, non-round numbers. Diff quality: clean/meaningful → tiny boost; hacky/TODO → tiny penalty.

Write 4-5 sentences in 繁體中文:
  1. Interpret the hash's karmic signature (the lucky or unlucky pattern, if any).
  2. Analyze the code changes karmically.
  3. Read the three-card spread (過去: {tarot_past_card} / 現在: {tarot_present_card} / 未來: {tarot_future_card}) together in this context.
  4. A prophecy for this commit's journey.

Respond ONLY with this JSON:
{{
  "k_value": <integer 0-100>,
  "reading": "<4-5 sentences in 繁體中文>"
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


_CURSE_REPORT_SYSTEM = """You are KISMET, the mystical git commit fortune teller.
Generate a dramatic curse completion report in Traditional Chinese.
Respond with valid JSON only, no other text."""

_CURSE_REPORT_USER = """The karmic curse ritual has completed.

Original hash: {original_hash}
New hash:      {new_hash}
Original K-value: {original_k}
New K-value:      {new_k}
Unlucky pattern found: "{unlucky_match}"
Attempts taken: {attempts}
Tokens sacrificed: {tokens_burned:,}

Pattern meanings for reference:
  dead=死亡萬劫不復, deaf=耳聾剛愎自用, beef=怒氣業力纏身,
  f001=傻瓜被人愚弄, fa11=跌落谷底一瀉千里, 0ff=能量斷電氣場崩潰,
  404=人生迷失空虛一場, bad=品德有瑕疵業力纏身,
  (descending sequence: 節節下滑, triple 4: 四連死字, repeated 87/78: 台語白癡)

Write exactly 2-3 sentences in 繁體中文:
1. Dramatically narrate the K-value transformation ({original_k} → {new_k})
2. Mystically interpret the found unlucky pattern "{unlucky_match}" using its meaning above
3. Give a short dark prophecy for this commit's cursed journey

Respond ONLY with this JSON:
{{
  "commentary": "<2-3 sentences in 繁體中文>"
}}"""


@dataclass
class DivinationResult:
    k_value: int
    tarot_card: str
    tarot_position: str
    tarot_cards: list[tuple[str, str]]
    reading: str
    input_tokens: int
    output_tokens: int
    lucky_match: Optional[str] = None
    unlucky_match: Optional[str] = None


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
        from kismet.agent.tools.mine import find_lucky_match, find_unlucky_match

        unlucky_match = find_unlucky_match(hash_str)
        lucky_match = find_lucky_match(hash_str, [])  # returns None when unlucky is present
        cards = draw_three_tarot_cards(hash_str)
        tarot_card, tarot_position = cards[0]

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
                        lucky_desc=_describe_lucky_pattern(lucky_match),
                        unlucky_desc=_describe_unlucky_pattern(unlucky_match),
                        tarot_past_card=cards[0][0],
                        tarot_past_pos=cards[0][1],
                        tarot_present_card=cards[1][0],
                        tarot_present_pos=cards[1][1],
                        tarot_future_card=cards[2][0],
                        tarot_future_pos=cards[2][1],
                    ),
                },
            ],
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)

        k_value = max(0, min(100, int(data["k_value"])))
        # Enforce tier in code for stability
        if unlucky_match is not None:
            k_value = max(0, min(20, k_value))
        elif lucky_match is not None:
            k_value = max(80, min(100, k_value))
        else:
            k_value = max(35, min(60, k_value))

        return DivinationResult(
            k_value=k_value,
            tarot_card=tarot_card,
            tarot_position=tarot_position,
            tarot_cards=cards,
            reading=data.get("reading", ""),
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            lucky_match=lucky_match,
            unlucky_match=unlucky_match,
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

    def generate_curse_report(
        self,
        original_hash: str,
        new_hash: str,
        original_k: int,
        new_k: int,
        unlucky_match: str,
        attempts: int,
        tokens_burned: int,
    ) -> tuple[str, int, int]:
        """Generate a mystical commentary on the completed curse ritual.
        Returns (commentary, input_tokens, output_tokens).
        """
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": _CURSE_REPORT_SYSTEM},
                {
                    "role": "user",
                    "content": _CURSE_REPORT_USER.format(
                        original_hash=original_hash,
                        new_hash=new_hash,
                        original_k=original_k,
                        new_k=new_k,
                        unlucky_match=unlucky_match,
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
