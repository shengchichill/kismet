# KISMET

```
  ██╗  ██╗██╗███████╗███╗   ███╗███████╗████████╗
  ██║ ██╔╝██║██╔════╝████╗ ████║██╔════╝╚══██╔══╝
  █████╔╝ ██║███████╗██╔████╔██║█████╗     ██║
  ██╔═██╗ ██║╚════██║██║╚██╔╝██║██╔══╝     ██║
  ██║  ██╗██║███████║██║ ╚═╝ ██║███████╗   ██║
  ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝╚══════╝   ╚═╝

  業力引發哈希挖礦暨驅魔工具
  Karma-Induced SHA Mining and Exorcism Tool
```

> 一本正經胡說八道。

KISMET divines the karmic fortune of your git commit hash via LLM (K-value 0–100), then offers to "exorcise" bad luck by rephrasing your commit message until the SHA contains an auspicious pattern — `888`, `168`, palindromes, ascending sequences. Commits with full ASCII altar ceremony.

---

## Features

- **占卜 (Divination)** — LLM reads your diff, predicts the commit hash, draws a tarot card, and assigns a K-value
- **逆天改運 (Mining)** — Rephrases your commit message in a loop until the hash contains a lucky string, using pure-Python SHA1 (no git subprocess in hot loop)
- **驅魔 (Exorcism)** — Force-commit with ritual ASCII art, no questions asked
- **下蠱 (Curse)** — Reverse mode: mine for an *unlucky* hash
- **Fixed-timestamp commits** — Predicted hash always matches actual commit hash via `GIT_COMMITTER_DATE`
- **Token cost tracking** — Input/output tokens tracked separately, cost computed from `model_costs.yml`

---

## Installation

Requires [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/yourname/kismet.git
```

Install as a global tool so `kismet` works from any directory:

```bash
uv tool install --editable ./kismet
```

---

## Configuration

| Variable | Default | Required |
|---|---|---|
| `LITELLM_BASE_URL` | — | ✅ |
| `LITELLM_API_KEY` | — | ✅ |
| `KISMET_MODEL` | `gpt-4o-mini` | |
| `MAX_MINE_ATTEMPTS` | `10` | |
| `MAX_MESSAGE_TOKENS` | `200` | |

KISMET calls LLMs via [LiteLLM proxy](https://github.com/BerriAI/litellm), so any model supported by your proxy works.

Set environment variables before running:

```bash
export LITELLM_BASE_URL="http://your-proxy:4000"
export LITELLM_API_KEY="your-key"
```

---

## Usage

Go to any git repo, stage your changes, then run kismet:

```bash
cd your-project
git add .
kismet commit
```

### `kismet commit` — Full auto

Generates a commit message → divines the hash → decides based on K-value:

| K-value | Verdict | Action |
|---|---|---|
| 0–20 | ☠ 運勢極差 | Auto-mine |
| 21–40 | 😰 運勢稍差 | Auto-mine |
| 41–60 | 😐 運勢普通 | Ask user |
| 61–80 | 🙂 運勢尚可 | Ask user |
| 81–100 | 🎉 運勢極佳 | Commit + celebrate |

```bash
kismet commit
```

### `kismet divine` — Divination only

Reads your diff, predicts the hash, draws tarot, shows K-value. No commit.

```bash
kismet divine
```

### `kismet mine [TARGETS...]` — Mining only

Rephrases commit message until the hash matches target strings. No commit.

```bash
kismet mine              # default lucky list: 888 168 777 666 + palindromes + runs
kismet mine 888 168      # custom targets
```

### `kismet force` — Exorcism commit

Generates message, skips divination, performs exorcism ritual, commits immediately.

```bash
kismet force
```

### `kismet curse [TARGETS...]` — Curse mode

Mines for an *unlucky* hash (dead, 404, f00d, bad) and commits it.

```bash
kismet curse
kismet curse dead 404
```

---

## Lucky Patterns (default)

| Pattern | Example |
|---|---|
| Fixed strings | `888`, `168`, `777`, `666` |
| Ascending run ≥ 3 | `123`, `abc` |
| Palindrome ≥ 4 chars | `abba`, `1221` |

---

## Development

```bash
uv run pytest -v
```

37 tests. No live LLM calls in tests (all mocked).

---

## Architecture

```
KismetAgent          ← flow coordinator
├── GitTool          ← staged diff, pure-Python SHA1, fixed-timestamp commit
├── DivinationTool   ← LLM: generate message, divine hash, rephrase message
├── MinerTool        ← mining loop, token accumulation
└── RendererTool     ← all Rich/ASCII visuals, interactive prompts
```

State flows through a central `KismetSession` dataclass. CLI is a thin Click wrapper.
