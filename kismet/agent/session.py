from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KismetSession:
    # Git context — set once at start, used for all hash computations
    diff: str
    original_message: str
    current_message: str
    predicted_hash: str
    tree_sha: str
    parent_sha: Optional[str]  # None for initial commit
    author_name: str
    author_email: str
    fixed_timestamp: str  # e.g. "1714300000 +0800"

    # Divination state
    k_value: int = 0
    divination_text: str = ""
    tarot_card: str = ""
    tarot_position: str = ""

    # Mining state
    mine_attempts: int = 0
    original_predicted_hash: str = ""  # saved before mining starts

    # Cost tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: Optional[float] = None
