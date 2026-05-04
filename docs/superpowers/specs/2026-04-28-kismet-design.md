# KISMET Design Spec
**Karma-Induced SHA Mining and Exorcism Tool**
Date: 2026-04-28

## Context

KISMET 是一個為「廢物 Agent 大賽」設計的 Git commit 工具。核心主張是：commit 的穩定性不取決於單元測試，而取決於提交時的宇宙業力（K-value）。工具透過占卜 commit hash 的運勢、必要時進行「逆天改運」（重寫 commit message 直到 hash 變吉利），為每次 commit 賦予靈魂與運勢。

實用面：自動依據 `git diff` 生成 commit message，包辦 commit 一條龍服務。

---

## Architecture

**方案 B：KismetAgent 中心協調，工具層獨立**

```
CLI (Click)
    └── KismetAgent
            ├── KismetSession     # 流程狀態（session.py）
            ├── DivinationTool    # tools/divine.py
            ├── MinerTool         # tools/mine.py
            ├── GitTool           # tools/git.py
            └── RendererTool      # tools/renderer.py

config.py                         # 環境變數與預設值
model_costs.yml                   # model → cost_per_1m_tokens 對照表
```

### KismetSession（集中狀態）

```python
@dataclass
class KismetSession:
    original_diff: str
    original_message: str
    current_message: str
    predicted_hash: str
    k_value: int
    divination_text: str
    mine_attempts: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
```

### 模組職責

| 模組 | 職責 |
|------|------|
| `cli.py` | Click thin wrapper，解析參數後呼叫 KismetAgent |
| `agent/agent.py` | 流程協調，不含業務邏輯，約 100–150 行 |
| `agent/session.py` | KismetSession dataclass |
| `agent/tools/divine.py` | 呼叫 LLM，輸入 hash + diff，回傳 K-value + 塔羅解讀 |
| `agent/tools/mine.py` | 迴圈：LLM 換句話說 → Python 計算 SHA1 → 檢查吉利字串 |
| `agent/tools/git.py` | `git diff --cached`、`git write-tree`、`git commit` with fixed timestamp |
| `agent/tools/renderer.py` | 所有 Rich / ASCII Art 視覺，Agent 只呼叫其方法 |
| `config.py` | 環境變數讀取與預設值 |

---

## LLM Integration

- **Client**: `openai` Python SDK，`base_url` 指向公司 LiteLLM proxy
- **環境變數**:
  - `LITELLM_BASE_URL` — proxy URL
  - `LITELLM_API_KEY` — proxy API key
  - `KISMET_MODEL` — 使用的模型，預設 `gpt-4o-mini`
- **初版**: 純 LLM 占卜（不接外部 API）
- **預留擴充點**: `DivinationTool` 預留 `fetch_almanac_data()` 的 hook，未來可注入農民曆/星座 API 資料作為 LLM prompt 素材

---

## CLI Commands

### `kismet commit`
全自動模式：生成 message → 占卜 → 依 K-value 決定是否改運 → commit。

### `kismet divine`
只做占卜。讀取 staged diff，生成初始 message，計算 hash，輸出 K-value 和塔羅解讀。不 commit。

### `kismet mine [TARGET...]`
只做逆天改運。
- 無參數：使用預設吉利字串清單（`888`, `168`, `666`, `777`, 連號, 回文）
- 一個 TARGET：hash 必須包含此字串
- 多個 TARGET：hash 包含任一即可
- 使用 Click `nargs=-1` 接收 variadic positional args

### `kismet force`
強制 commit，不占卜不改運。觸發驅魔儀式 ASCII 動畫，Agent 輸出「警告：你已強行打破宇宙平衡」，然後 commit。

### `kismet curse`
下蠱模式（低優先）。反向挖礦，找包含 `dead`、`404`、`f00d` 等不詳字眼的 hash 才提交。

---

## K-value Logic

K-value 範圍 0–100，由 LLM 評估，傾向給出中低分（讓大部分 hash 落在需要改運的範圍）。

| K-value | 等級 | `kismet commit` 行為 |
|---------|------|----------------------|
| 0–20 | 運勢極差 ☠️ | 自動開始逆天改運 |
| 21–40 | 運勢稍差 😰 | 強烈警告後自動開始逆天改運 |
| 41–60 | 運勢普通 😐 | 詢問 user 是否改運 |
| 61–80 | 運勢尚可 🙂 | 告知「尚可但可更好」，詢問是否改運 |
| 81–100 | 運勢極佳 🎉 | 直接 commit + 慶祝動畫 |

**評分偏低設計**：LLM prompt 中明確設定嚴格標準，使大多數 hash 落在 41–60 區間，推動使用者逆天改運。

---

## Hash Mining Algorithm

### 預測 commit hash（不實際 commit）

```
1. git write-tree                    → tree_sha
2. git rev-parse HEAD                → parent_sha
3. 固定 timestamp = now（字串）
4. 組合 commit object 字串
5. Python SHA1(commit_object)        → predicted_hash
```

在迴圈中純 Python 計算，不跑 git，速度快（每秒數十次）。

### 吉利字串判斷

預設清單：`888`, `168`, `666`, `777`, 連號（長度 ≥ 3 的連續字元，如 `123`、`abc`）, 回文（長度 ≥ 4 的回文子字串，如 `abba`、`1221`）。
`kismet mine [TARGET...]` 可覆蓋此清單（使用者指定時不檢查連號/回文）。

### 改運迴圈

```
while attempts < MAX_MINE_ATTEMPTS:
    wait_for_ritual_gate()                 # prayer pose 或綠色乖乖供品
    new_message = LLM.rephrase(current_message)   # 換句話說
    predicted_hash = compute_sha1(new_message, fixed_timestamp)
    if is_lucky(predicted_hash, targets):
        break
    attempts += 1
```

達上限 → 祈福儀式 → 仍然 commit。

### MacSensorAgent Ritual Gate

KISMET 可透過 MacSensorAgent 的本機 snapshot API，在每次 mining attempt 前確認儀式是否完成。這讓 `git commit` 從單純工程操作升級成一場具身化法會：LLM 負責改咒語，SHA-1 負責看天命，MacBook camera 負責確認你到底有沒有誠意。

目前 ritual gate 的通過條件：

- `latestPrayerPoseActive == true`，且 confidence 與 hand count 達標。
- 或 `latestKuaiKuaiDetected == true`、`latestKuaiKuaiColor == "green"`，且 confidence 達標。
- 如果 `latestKuaiKuaiDetected == true` 但 `latestKuaiKuaiColor != "green"`，立即終止 mining。

綠色乖乖是 prayer pose 的 bypass，不是替代整個 MacSensorAgent。因為雙手合十是人類對宇宙的懇求，綠色乖乖是工程師對機房穩定性的正式賄賂。兩者任一成立，都可以視為「准予逆天改運」。黃色、紅色等非綠色乖乖則是禁忌供品；KISMET 應停止 mining，避免把機器靈搞到不知道今天到底要乖還是要壞。

Snapshot example：

```json
{
  "latestPrayerPoseActive": false,
  "latestPrayerPoseConfidence": 0.12,
  "latestPrayerPoseHandCount": 0,
  "latestKuaiKuaiDetected": true,
  "latestKuaiKuaiColor": "green",
  "latestKuaiKuaiConfidence": 0.78,
  "camera": {
    "authorizationStatus": "authorized"
  }
}
```

KISMET 判定邏輯：

```python
def is_ritual_gate_open(snapshot):
    if (
        snapshot.get("latestKuaiKuaiDetected") is True
        and snapshot.get("latestKuaiKuaiColor") != "green"
        and snapshot.get("latestKuaiKuaiConfidence", 0) >= 0.55
    ):
        raise ForbiddenOffering("non-green Kuai Kuai detected")

    prayer_pose_ok = (
        snapshot.get("latestPrayerPoseActive") is True
        and snapshot.get("latestPrayerPoseConfidence", 0) >= 0.62
        and snapshot.get("latestPrayerPoseHandCount", 0) >= 2
    )
    green_kuai_kuai_ok = (
        snapshot.get("latestKuaiKuaiDetected") is True
        and snapshot.get("latestKuaiKuaiColor") == "green"
        and snapshot.get("latestKuaiKuaiConfidence", 0) >= 0.55
    )
    return prayer_pose_ok or green_kuai_kuai_ok
```

Renderer 文案方向：

```text
🙏 祈禱姿勢確認，准予本輪改運。
```

```text
🟢 綠色乖乖供品確認，機器已被安撫，准予本輪改運。
```

```text
✗ 改運中止：偵測到黃色/紅色乖乖。這不是供品，是機房禁忌。
```

Fail behavior：

- MacSensorAgent 不可用且 `KISMET_REQUIRE_PRAYER_POSE=1` 時，停止 mining，避免無供品硬闖天庭。
- 有 prayer pose 或綠色乖乖任一成立時，繼續 mining。
- 黃色、紅色或其他非綠色乖乖成立時，立即停止 mining，不進入 LLM rephrase，不燃燒 token。
- 若只偵測到普通綠色物體而誤判，系統可接受；這不是 bug，是宇宙突然很好說話。

### 實際 commit

找到吉利 hash 後：
```
GIT_COMMITTER_DATE=fixed_timestamp git commit -m "message" --date=fixed_timestamp
```
確保實際 hash 與預測一致。

---

## Configuration

| 環境變數 | 預設值 | 說明 |
|----------|--------|------|
| `LITELLM_BASE_URL` | （必填） | LiteLLM proxy URL |
| `LITELLM_API_KEY` | （必填） | proxy API key |
| `KISMET_MODEL` | `gpt-4o-mini` | 使用模型 |
| `MAX_MINE_ATTEMPTS` | `10` | 逆天改運最大次數 |
| `MAX_MESSAGE_TOKENS` | `200` | commit message token 上限 |
每次 LLM 呼叫後從 `response.usage` 分別累加：
- `usage.prompt_tokens` → `KismetSession.total_input_tokens`
- `usage.completion_tokens` → `KismetSession.total_output_tokens`

USD 費用 = `input_tokens / 1_000_000 * input_cost + output_tokens / 1_000_000 * output_cost`，費率從 `kismet/model_costs.yml` 依 `KISMET_MODEL` 查表取得。若模型不在表中則顯示 `(cost unknown)`。

---

## Visual Design

**風格**：Vaporwave 粉紫色調 + 傳統神壇儀式感（C + A 混搭）。

### 主要畫面

#### 1. 啟動 Banner
大字 KISMET（block font），粉→紫→藍漸層色，持續約 0.5 秒。

#### 2. 占卜進行中（三幀動畫）

**幀 A**：桌面出現三個牌位，前兩張牌面朝下（`░░░`），第三張空白（發牌中）。水晶球坐在桌面右側：`( ✦ ) / (🔮) / (   )`，底座 `══════`。

**幀 B**：三張牌全部翻開（THE FOOL / WHEEL / TOWER）。水晶球偵測到不詳字符，`✦` 換成 `⚡`。

**幀 C**：桌面牌陣固定，下方 LLM 占卜文字逐字輸出，游標 `█` 閃爍。

#### 3. 占卜結果
塔羅牌 + K-value 進度條 + 運勢等級。

#### 4. 逆天改運進行中
Token 燒香祭壇（`~` 往上飄），每次嘗試逐行印出 `hash: xxx... ✗ 無緣 / ✦ 含 888！`

#### 5. 改運成功
改運前後 hash 對比，「誠心敬意報告」（次數、tokens、費用 💸）。

#### 6. 祈福儀式（改運失敗）
祈福壇 ASCII，LLM 生成祈福文字，顯示總消耗，「花錢消災，功德圓滿」。

#### 7. 驅魔儀式（force commit）
`kismet force` 專屬，驅魔符咒 ASCII，Agent 嘴砲「你已強行打破宇宙平衡」。

---

## Priority

| 功能 | 優先級 |
|------|--------|
| `kismet commit` 全流程 | P0 核心 |
| `kismet divine` | P0 核心 |
| `kismet mine [TARGET...]` | P0 核心 |
| `kismet force` + 驅魔儀式 | P0 核心 |
| ASCII 視覺（Banner/占卜桌/祭壇） | P0 核心 |
| 費用報告（tokens + USD） | P0 核心 |
| `kismet curse` 下蠱模式 | P2 低優先 |
| Git hook 安裝（`kismet install`） | P2 低優先 |
| 農民曆/星座外部 API 整合 | P2 低優先 |

---

## Tech Stack

| 項目 | 選擇 |
|------|------|
| Language | Python 3.10+ |
| CLI framework | Click |
| Terminal visuals | Rich（Live, Panel, Text） |
| LLM client | openai SDK → LiteLLM proxy |
| Package manager | uv |

---

## model_costs.yml 格式

```yaml
# input_cost_per_1m / output_cost_per_1m 單位均為 USD
# 視公司 LiteLLM proxy 實際使用的模型新增/修改
gpt-4o-mini:
  input_cost_per_1m: 0.15
  output_cost_per_1m: 0.60
gpt-4o:
  input_cost_per_1m: 2.50
  output_cost_per_1m: 10.00
claude-3-5-haiku:
  input_cost_per_1m: 0.80
  output_cost_per_1m: 4.00
claude-3-5-sonnet:
  input_cost_per_1m: 3.00
  output_cost_per_1m: 15.00
```

`config.py` 在啟動時讀取此檔案，查表失敗時費用欄位顯示 `(cost unknown)`，不影響其他功能。

---

## Verification

1. `uv sync && uv run kismet --help` → 顯示所有子指令
2. `git init test-repo && cd test-repo && echo "test" > f.txt && git add .`
3. `kismet divine` → 顯示占卜桌動畫 + K-value + 塔羅解讀
4. `kismet commit` → 全流程：生成 message → 占卜 → 改運（若需要）→ commit
5. `kismet mine 888 168` → 找到含 888 或 168 的 hash 後停止
6. `kismet force` → 驅魔動畫後直接 commit
7. `git log --oneline` → 確認 commit hash 符合占卜結果
8. 設 `MAX_MINE_ATTEMPTS=2` → 驗證改運失敗後觸發祈福流程
