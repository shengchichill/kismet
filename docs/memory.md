# KISMET 開發進度紀錄

## 專案概述

KISMET（Karma-Induced SHA Mining and Exorcism Tool）是一個 Git commit hash「算命」CLI 工具，為廢物 Agent 大賽提案。

透過 LLM 占卜 commit hash 的宇宙業力（K-value），必要時「逆天改運」（反覆修改 commit message 直到 hash 出現吉利字符），最終以隆重的 ASCII Art 儀式 commit。

## 關鍵設計文件

| 文件 | 路徑 |
|------|------|
| 設計 Spec | `docs/superpowers/specs/2026-04-28-kismet-design.md` |
| 實作計畫 | `docs/superpowers/plans/2026-04-28-kismet.md` |

## 技術決策摘要

| 項目 | 決策 |
|------|------|
| Language | Python 3.10+ |
| Package manager | **uv** |
| CLI framework | Click |
| Terminal visuals | Rich（Live, Panel, Text） |
| LLM client | openai SDK → 公司 LiteLLM proxy |
| Architecture | KismetAgent 中心協調，4 個工具層獨立 |
| 視覺風格 | Vaporwave 粉紫 + 傳統神壇 ASCII art |

### 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `LITELLM_BASE_URL` | 必填 | 公司 LiteLLM proxy URL |
| `LITELLM_API_KEY` | 必填 | proxy API key |
| `KISMET_MODEL` | `gpt-4o-mini` | 使用模型 |
| `MAX_MINE_ATTEMPTS` | `10` | 逆天改運最大次數 |
| `MAX_MESSAGE_TOKENS` | `200` | commit message token 上限 |

### CLI 指令

| 指令 | 說明 |
|------|------|
| `kismet commit` | 全自動：生成 message → 占卜 → 視 K-value 決定是否改運 → commit |
| `kismet divine` | 只做占卜（不 commit） |
| `kismet mine [TARGET...]` | 只做逆天改運（不占卜不 commit），可指定目標字串 |
| `kismet force` | 強制 commit + 驅魔儀式 |
| `kismet curse [TARGET...]` | 下蠱模式：反向找不詳 hash（P2 低優先） |

### K-value 邏輯

| K-value | 等級 | `kismet commit` 行為 |
|---------|------|----------------------|
| 0–20 | 運勢極差 ☠️ | 自動開始逆天改運 |
| 21–40 | 運勢稍差 😰 | 自動開始逆天改運（強烈警告） |
| 41–60 | 運勢普通 😐 | 詢問 user 是否改運 |
| 61–80 | 運勢尚可 🙂 | 詢問 user 是否改運（告知可更好） |
| 81–100 | 運勢極佳 🎉 | 直接 commit + 慶祝動畫 |

### Hash 挖礦算法

- 開始時呼叫 `git write-tree` 取得 tree_sha
- 固定 timestamp（`datetime.now().astimezone()`）
- 純 Python SHA1 計算預測 hash（不跑 git subprocess，速度快）
- 找到吉利 hash 後，用 `GIT_COMMITTER_DATE` + `--date` 確保實際 commit hash 與預測一致

### 吉利字串預設清單

`888`, `168`, `666`, `777`，連號（長度 ≥ 3，如 `123`、`abc`），回文（長度 ≥ 4，如 `abba`）

## 檔案結構

```
kismet/
├── pyproject.toml
├── model_costs.yml
├── uv.lock
├── docs/
│   ├── memory.md                          ← 本檔案
│   └── superpowers/
│       ├── specs/2026-04-28-kismet-design.md
│       └── plans/2026-04-28-kismet.md
├── kismet/
│   ├── __init__.py
│   ├── cli.py                             (Task 10，未做)
│   ├── config.py                          ✅ 已完成
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py                       (Task 9，未做)
│   │   ├── session.py                     ✅ 已完成
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── divine.py                  (Task 6，未做)
│   │       ├── mine.py                    (Tasks 5+7，未做)
│   │       ├── git.py                     (Task 4，未做)
│   │       └── renderer.py               (Task 8，未做)
└── tests/
    ├── __init__.py
    ├── conftest.py                        ✅ 已完成（含 git_repo fixture）
    ├── test_config.py                     ✅ 已完成（4 tests）
    ├── test_session.py                    ✅ 已完成（3 tests）
    ├── test_git.py                        (Task 4，未做)
    ├── test_mine.py                       (Tasks 5+7，未做)
    └── test_divine.py                     (Task 6，未做)
```

## 執行進度

**方式：** Subagent-Driven Development，每 3 個 Task 暫停讓 user 檢視

| Task | 內容 | 狀態 |
|------|------|------|
| 1 | Project scaffolding（uv, pyproject.toml, model_costs.yml） | ✅ |
| 2 | Config module | ✅ |
| 3 | KismetSession dataclass | ✅ |
| **4** | **GitTool（staged diff, SHA1 hash computation, commit）** | **⬅ 下一個** |
| 5 | is_lucky() lucky string detection | 待做 |
| 6 | DivinationTool（LLM calls） | 待做 |
| 7 | MinerTool（mining loop） | 待做 |
| 8 | RendererTool（ASCII art + animations） | 待做 |
| 9 | KismetAgent（flow coordinator） | 待做 |
| 10 | CLI（Click commands） | 待做 |
| 11 | End-to-end verification | 待做 |

## Git Log（目前）

```
3f51718 feat: KismetSession dataclass
(config commit) feat: config module with env vars and model cost lookup
4e939c4 fix: git_repo fixture needs initial commit so HEAD exists
b256f20 chore: project scaffolding with uv, click, rich, openai
```

## 下一步（Task 4：GitTool）

實作 `kismet/agent/tools/git.py`，包含：

- `GitContext` dataclass（tree_sha, parent_sha, author_name, author_email, fixed_timestamp）
- `GitTool.get_staged_diff()` → 若無 staged changes 則 raise RuntimeError
- `GitTool.get_context()` → 呼叫 git write-tree、rev-parse HEAD（初始 commit 時為 None）、git config user.name/email，建立 fixed_timestamp
- `GitTool.compute_hash(message, ctx)` → 純 Python SHA1，格式：`commit <size>\0tree ...\nparent ...\nauthor ...\ncommitter ...\n\n<message>\n`
- `GitTool.commit(message, ctx)` → 用 `GIT_COMMITTER_DATE` + `--date` 確保 hash 一致，回傳實際 hash

**重要注意事項：**
- `conftest.py` 的 `git_repo` fixture 現在有初始 commit（HEAD 存在）並有 staged 變更
- Task 4 的 `test_get_context_returns_git_context` 測試中，`ctx.parent_sha` **不會是 None**（因為 fixture 已有初始 commit），應改為 `assert ctx.parent_sha is not None`
- `test_commit_produces_matching_hash` 仍然有效（有 parent 的情況也適用）

## conftest.py 現況（重要）

```python
@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    # Initial commit so HEAD exists
    (tmp_path / "file.txt").write_text("hello world")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    # Stage new changes so tests have a diff to work with
    (tmp_path / "file.txt").write_text("hello world updated")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path
```
