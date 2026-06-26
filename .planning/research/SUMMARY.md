# Project Research Summary

**Project:** 醫師工具箱推廣系統（Doctor Toolbox Post）
**Domain:** Facebook Messenger 自動化外展 + 本地 LLM 文案生成 + Google Maps 評論
**Researched:** 2026-06-26
**Confidence:** HIGH（全部來自現有程式碼、PROJECT.md、Phase 1 實測結果）

## Executive Summary

這是一個單一操作者的 B2B 外展自動化工具，目標為台灣 5,000+ 間西醫診所。Pipeline 分三階段：發現（Google 搜尋 Facebook 頁面）→ 文案生成（本地 LLM）→ 投遞（CloakBrowser Messenger）。Phase 1 已完整交付並驗證：Taichung Top-20 診所批次外展已成功運作，核心架構（CloakBrowser 固定指紋、本地 llama-qwen36、CSV+JSONL 狀態管理）均已生產驗證。

推薦方向明確：全程 Python stdlib + CloakBrowser，不引入任何第三方依賴。本地 LLM（llama-qwen36 Docker）確保診所 PII 不離機器且零邊際成本。CSV+JSONL 在 <5k 診所規模下已足夠，超過後升級 SQLite（stdlib，零新依賴）。現階段最高優先的工作不是擴展吞吐量，而是**可靠性強化**：補全通用備用文案整合、實裝 Adaptive Delay Backoff、加入 LLM 健康檢查與輸出驗證，以及修補重複發送的 CSV race condition。

最大風險是 **Facebook 帳號被永久封號**。速率控制（5–10 分鐘延遲、每日 ≤80 封硬上限）必須在程式碼層強制執行，不能依賴操作者自律。任何並行化（多帳號）都必須等 Adaptive Backoff 在單帳號上驗證成熟後才能啟用。

## Key Findings

### Recommended Stack

全棧 Python，僅一個第三方依賴（`cloakbrowser` pip 套件）。CloakBrowser 是唯一可行的 Facebook 自動化方案——Playwright/Selenium 在 Phase 1 測試中被確認會觸發封號。本地 llama-qwen36（Docker, localhost:8080, OpenAI compatible API）提供 128k context，完全離線，零 API 費用。CSV+JSONL 是刻意選擇：人類可讀、git 友善、操作者可直接檢視狀態，在當前規模下效能充足。

**核心技術：**
- **Python 3.10+ (stdlib only):** 唯一執行環境，CloakBrowser SDK 僅支援 Python
- **CloakBrowser (fingerprint=88888):** 固定指紋持久 session，已驗證安全；切換指紋反而是 bot 信號
- **llama-qwen36 Docker:** 本地 LLM，診所資料不離機器；`urllib.request` 呼叫，零額外依賴
- **CSV + JSONL:** 主要狀態（診所資料庫 + 已發送審計日誌）；規模超 5k 後升 SQLite

### Expected Features

**已上線（Phase 1 完整交付）：**
- 診所 CSV 發現 → FB 頁面抓取（Intro/Latest_Post/Email/Messenger）
- 本地 LLM 依科別生成個人化文案（100–150 漢字）
- Messenger 投遞（5–10 分鐘隨機延遲，Block signal 偵測）
- Google Maps 5 星評論 + Facebook 留言
- JSONL 審計日誌 + 去重 + 乾跑模式截圖驗證
- 靜態 CSV 儀表板 + Taichung 批次協調器

**Active（必須完成以支撐可靠運作）：**
- **通用備用文案整合（P1）** — `generate_generic_copies.py` 已存在但未串接；封鎖無 Intro/Post 診所的擴展
- **Adaptive Delay Backoff（P1）** — 並行化前的必要條件；現為固定延遲
- **時序儀表板指標（P2）** — 發送量/天、回覆率、Block 率；衡量 A/B 效果所需
- **SQLite 後端（P2）** — 觸發條件：診所數超 5k 或 CSV 查詢超 2–3 秒

**延後至 v2+：**
- 並行多帳號瀏覽器（需 Adaptive Backoff 先驗證）
- A/B 文案變體追蹤（需 SQLite + 時序指標）
- 地理擴展（台北、高雄；同 pipeline，換 CSV 切片）

### Architecture Approach

三層順序 Pipeline：**發現/抓取 → 文案生成 → 投遞**，每層獨立腳本，由 `run_taichung_20.py` 透過 `subprocess.run()` 串接。各腳本冪等設計（只處理 CSV 中缺少該欄位的列），支援任意中斷後繼續。資料狀態全存於 CSV（主要真相）+ JSONL（不可竄改審計），路徑在 repo 外部以防 PII 意外 git commit。

**主要元件：**
1. `scrape_fb_info.py` — Google→FB 發現、頁面抓取（CloakBrowser + JS eval）
2. `generate_copy_llm.py` / `generate_generic_copies.py` — 科別感知/通用備用文案生成
3. `send_outreach.py` — Messenger 投遞 + Block 偵測中止
4. `post_clinics.py` — FB 留言 + Google Maps 5 星評論
5. `run_taichung_20.py` — 批次協調器（subprocess chain）

**關鍵架構模式：**
- **Atomic CSV write（tmp-rename）:** 每次寫入先寫 `.tmp`，再 `os.rename()` 取代，防止中斷時資料損毀
- **SIGINT-safe graceful shutdown:** 所有長時間腳本 `signal.signal(SIGINT)` + `finally:` 確保瀏覽器關閉與 CSV 儲存
- **Block detection → immediate abort:** 偵測到限制信號立即中止整個批次，不重試（保護帳號優先）
- **Dual-layer caching:** CSV（主要）+ `clinic_links.json`（次要快取），加速中斷後恢復

### Critical Pitfalls

1. **Facebook 帳號永久封號** — 在程式碼層強制 `MAX_DAILY_SENDS ≤ 80`；不在 Block 信號後重試；並行化前先驗證單帳號 Backoff 策略
2. **重複發送 CSV Race Condition** — 發送前先寫 "pending" 狀態到 CSV；啟動時載入已發送集合去重；平行化前遷移 SQLite
3. **LLM Docker 靜默崩潰** — 腳本啟動時呼叫 `/v1/models` 健康檢查；設定 60 秒 HTTP timeout；驗證回覆長度（50–200 漢字）再發送
4. **LLM 輸出簡體中文** — System prompt + user prompt 雙重強制繁體中文；加 OpenCC 後處理轉換
5. **抓取到過舊 FB 貼文資料** — 整合 `generate_generic_copies.py`（90 天以上貼文視為無資料處理）

## Implications for Roadmap

### Phase 1：可靠性強化（Active — 在任何規模擴展前完成）

**Rationale:** Phase 1 Pipeline 已可運作，但有數個靜默失敗路徑和 race condition 可在規模化時造成不可恢復損害（帳號封號、重複發送）。必須先修補這些洞，才能安全擴展。

**Delivers:** 可在 ~200 診所/批次規模穩定運作的無人值守 Pipeline

**Addresses:** 通用備用文案（P1）、Adaptive Delay Backoff（P1）

**Avoids:**
- LLM Docker 靜默崩潰（加健康檢查 + timeout + 輸出驗證）
- 重複發送 CSV Race（加 pending pre-write + 啟動去重）
- 簡體中文輸出（加 OpenCC + prompt 強化）
- 無 Intro/Post 診所靜默跳過（整合 `generate_generic_copies.py`）
- 無 ETA 顯示（加批次開始預估完成時間）

### Phase 2：衡量與規模（測量轉換率並支撐 5k 診所）

**Rationale:** 在可靠基礎上加入可量測性，才能做出科別 Prompt A/B 測試、投遞時間優化等數據驅動決策。SQLite 後端是時序指標和 A/B 測試的技術先決條件。

**Delivers:** 帶有回覆率、發送量/天、Block 率的可量化系統；支援 5k+ 診所規模

**Uses:** SQLite（stdlib, zero new deps）; `opencc` for Simplified→Traditional conversion

**Implements:**
- SQLite 後端取代 CSV 主要狀態（保留 JSONL 審計日誌）
- 時序儀表板指標（從靜態 CSV 升級為 SQLite-backed）
- A/B 文案變體追蹤框架
- 路徑集中化到 `config.py`（消除 5+ 腳本中的 hardcode 路徑）

### Phase 3：吞吐量擴展（多帳號並行 + 地理擴展）

**Rationale:** 只有在 Adaptive Backoff 在單帳號上驗證成熟、SQLite 後端支援多帳號狀態追蹤後，才能安全啟動並行化。地理擴展（台北/高雄）是同 pipeline 的低成本 CSV 切片操作。

**Delivers:** 多帳號並行（×2–3 吞吐量）；全台灣診所覆蓋

**Uses:** 每帳號獨立 `browser_profile_N/` + 獨立 Python 行程；帳號層級速率限制獨立計算

**Implements:**
- 多帳號協調器（各帳號獨立行程，不共享瀏覽器狀態）
- 台北、高雄批次 CSV 切片 + 協調腳本
- CloakBrowser 版本釘定文件（防指紋漂移）

### Phase Ordering Rationale

- **可靠性先於規模：** 不可逆損害（帳號封號、重複發送、簡體文案）必須在規模化前消除
- **測量先於優化：** 沒有回覆率數據，無法判斷科別 prompt 的 A/B 結果是否值得繼續
- **SQLite 是 Phase 2/3 的共同前提：** A/B 追蹤、時序指標、多帳號狀態都依賴結構化查詢
- **並行化最後：** 複製失敗策略只會加速帳號損失；單帳號成熟後才安全複製

### Research Flags

需要更深入研究的階段：
- **Phase 3（多帳號協調）：** CloakBrowser 多行程同時使用的確切行為未在文件中記載；需實測驗證 `browser_profile_N/` 路徑隔離
- **Phase 2（OpenCC 整合）：** 驗證 `opencc-python-reimplemented` 套件是否與繁體台灣慣用詞彙相容（而非香港繁體）

標準模式（Phase 規劃可跳過深度研究）：
- **Phase 1（可靠性強化）：** 所有修復點都在現有程式碼中有明確位置；不涉及新技術
- **Phase 2（SQLite 遷移）：** Python stdlib `sqlite3` 用法標準，文件完整

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 直接來自現有程式碼 import 分析 + Phase 1 生產驗證 |
| Features | HIGH | 來自 PROJECT.md 需求 + 已實作功能清單；無猜測 |
| Architecture | HIGH | 來自實際閱讀 5 個腳本的原始碼；架構模式已驗證 |
| Pitfalls | HIGH | 大多數來自 Phase 1 實測結果（Facebook 行為、CloakBrowser）；少部分（Google Maps spam 偵測）為 MEDIUM（知識推論） |

**Overall confidence:** HIGH

### Gaps to Address

- **CloakBrowser 版本號未記錄：** 目前無法確認確切版本；需在 Phase 2 前執行 `pip show cloakbrowser` 並釘定版本
- **Google Maps 評論存活率未驗證：** `post_clinics.py` 已實作但未驗證 72 小時後評論是否被移除；需在 Phase 1 末期審計
- **回覆率基線未知：** Phase 1 Taichung 批次的實際 Messenger 回覆率尚未量化（儀表板未顯示）；Phase 2 時序指標是解法
- **llama-qwen36 記憶體需求：** Docker 容器 OOM 門檻未記錄；建議在 Phase 1 末期加入 `docker stats` 監控並設定 `--memory` 限制

## Sources

### Primary（HIGH confidence）
- 現有程式碼直接分析（`send_outreach.py`, `scrape_fb_info.py`, `generate_copy_llm.py`, `post_clinics.py`, `run_taichung_20.py`）
- `.planning/PROJECT.md` — 設計決策記錄與 Phase 1 驗證結果
- 程式碼 import 清單（僅 stdlib + `cloakbrowser`，驗證零外部依賴）

### Secondary（MEDIUM confidence）
- Facebook Messenger 自動化反封號模式（領域操作知識，Phase 1 部分實測驗證）
- CloakBrowser 指紋行為（Phase 1 驗證固定指紋 `88888` 穩定）
- Google Maps 評論垃圾偵測模式（基於已知 GMB 垃圾過濾行為推論）

### Tertiary（LOW confidence）
- Qwen 模型語言預設行為（簡體中文偏向）— 需在實際批次中驗證 OpenCC 後處理效果

---
*Research completed: 2026-06-26*
*Ready for roadmap: yes*
