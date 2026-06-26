# Stack Research

**Domain:** 自動化推廣系統 — Facebook Messenger 外展 + 本地 LLM 文案生成
**Researched:** 2026-06-26
**Confidence:** HIGH（已驗證自現有程式碼與 Phase 1 運作結果）

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10+ | 唯一執行環境 | CloakBrowser SDK 僅支援 Python；stdlib 豐富（csv, json, signal, urllib）已足夠，無需引入 Node.js |
| CloakBrowser | latest | 瀏覽器自動化 + 反偵測指紋 | Playwright/Selenium 會觸發 Facebook bot 偵測；CloakBrowser 提供固定指紋（`88888`）與持久化 profile，已驗證安全 |
| llama-qwen36 (Docker) | latest | 本地 LLM 文案生成 | 零 API 費用、診所資料不離機器（隱私要求）、128k context、OpenAI compatible `/v1/chat/completions` 端點 |
| CSV + JSONL | — | 資料儲存 | 人類可讀、git 版本控制友善、`<5k` 診所規模下查詢效能足夠；無需任何資料庫基礎設施 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `csv` (stdlib) | — | 讀寫診所 CSV 資料庫 | 主要資料讀寫，所有腳本皆使用 |
| `json` (stdlib) | — | JSONL 審計日誌 + JSON 快取 | 所有輸出日誌與快取皆用 JSON，不引入外部依賴 |
| `urllib.request` (stdlib) | — | 呼叫本地 LLM API | 取代 `requests`——零依賴，適合單一 POST 呼叫 |
| `signal` (stdlib) | — | 優雅中斷（Ctrl+C 儲存進度） | 所有長時間執行腳本皆必須實作 SIGINT handler |
| `argparse` (stdlib) | — | CLI 參數（`--dry-run`, `--limit`） | 腳本操作參數控制 |
| `pathlib` (stdlib) | — | 跨平台路徑處理 | 所有腳本路徑統一使用 `Path` |
| `sqlite3` (stdlib) | — | **待升級**：取代 CSV 以支援 10k+ 診所規模查詢 | 達到 5k 診所後啟用；不引入 ORM |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker | 執行 llama-qwen36 本地 LLM | 容器固定監聽 `localhost:8080`；腳本透過環境變數 `LLM_API_URL` 可覆蓋 |
| CloakBrowser profile `browser_profile/` | 持久化 Facebook 登入 session | 指紋固定為 `88888`；由 `setup_session.py` 初始化 |
| `outreach_dashboard.html` | CSV 進度視覺化（純前端）| 無伺服器需求；CSV 資料拖入即顯示 |

---

## Installation

```bash
# CloakBrowser Python SDK
pip install cloakbrowser

# 本地 LLM（Docker）
docker pull [llama-qwen36-image]
docker run -p 8080:8080 [llama-qwen36-image]

# 無其他第三方依賴——完全使用 Python stdlib
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| CloakBrowser | Playwright / Selenium | 僅在非 Facebook 目標平台且不需反偵測時 |
| llama-qwen36 (本地) | OpenAI API / Claude API | 若診所資料可接受上傳雲端且願意付 API 費用 |
| stdlib `urllib` | `requests` / `httpx` | 若需要非同步並發 LLM 呼叫時改用 `httpx` |
| CSV + JSONL | SQLite / PostgreSQL | 超過 5k 診所或需多欄位查詢時改 SQLite（stdlib 已內建） |
| 純 HTML dashboard | React / Vue | 若需要即時更新或多人操作時才值得引入 JS 框架 |
| 固定指紋 `88888` | 隨機輪換指紋 | **不推薦**——指紋切換本身就是 bot 信號；現有策略已驗證 |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Playwright / Selenium | Facebook 偵測到後立即封號；Phase 1 測試已驗證不可用 | CloakBrowser |
| OpenAI API / 雲端 LLM | 診所 PII 資料（名稱、地址、聯絡方式）必須留在本地 | llama-qwen36 Docker |
| `requests` 套件 | 增加依賴、本專案只需一個 POST，stdlib 已足夠 | `urllib.request` |
| 多執行緒並行發送 | Facebook per-account 速率限制；並行會加速封號 | 單執行緒 + 隨機延遲 |
| ORM（SQLAlchemy 等）| 查詢需求簡單，ORM 是過度設計；升級時直接用 `sqlite3` | `sqlite3` stdlib |
| Node.js / npm 任何套件 | CloakBrowser SDK 不支援；Python-only 限制 | Python stdlib + CloakBrowser |

---

## Stack Patterns by Variant

**若需要 A/B 文案測試（Active 需求之一）：**
- 在 `generate_copy_llm.py` 加入 `variant` 欄位到 CSV
- JSONL 日誌記錄每封信的 `variant_id`
- Dashboard 依 `variant_id` 分組統計回覆率
- 不需引入外部測試框架

**若升級到 SQLite 後端（10k+ 診所規模）：**
- 使用 `sqlite3`（Python stdlib，零額外依賴）
- 保留 JSONL 作為審計日誌（append-only，不可替換）
- CSV 轉 SQLite 一次性遷移腳本，CSV 保留唯讀備份

**若需要 Adaptive Delay Backoff（Active 需求之一）：**
- 在 `send_outreach.py` 加入指數退避邏輯（偵測到限制信號後乘以 1.5–2x）
- 狀態儲存在 `outreach_sent_log.jsonl` 同一檔案
- 不需引入外部排程工具

**若並行多帳號發送（未來需求）：**
- 每個 Facebook 帳號一個獨立 `browser_profile_N/` 目錄
- 每個帳號一個獨立 Python 行程（`subprocess` 或 `multiprocessing`）
- 帳號層級速率限制獨立計算，不共享狀態

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| CloakBrowser | Python 3.10+ | 不支援 Node.js；需 Linux/Mac 桌面環境（headless=False 為主要模式） |
| llama-qwen36 Docker | `localhost:8080` OpenAI compatible | `LLM_API_URL` 環境變數可覆蓋；timeout 建議 60s |
| Python csv module | UTF-8-sig BOM | 政府開放資料 CSV 帶 BOM，必須用 `utf-8-sig` encoding |

---

## Sources

- 現有程式碼直接分析（`send_outreach.py`, `scrape_fb_info.py`, `generate_copy_llm.py`, `post_clinics.py`, `crawl_links.py`）— HIGH confidence
- PROJECT.md 設計決策記錄 — HIGH confidence（已驗證 Phase 1 運作結果）
- 程式碼中的 import 語句清單（僅 stdlib + `cloakbrowser`）— HIGH confidence

---
*Stack research for: 醫師工具箱推廣系統（Doctor Toolbox Post）*
*Researched: 2026-06-26*
