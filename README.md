# 醫師工具箱 (Doctor Toolbox) - 診所推廣與自動化行銷系統

本專案是一套專為 **醫師工具箱 (Doctor Toolbox)** 設計的自動化診所推廣、資訊收集與 Messenger 開發系統。主要針對台灣西醫診所進行自動化行銷，結合 AI 技術客製化文案，並模擬真人行為進行慢速推廣以防止帳號被 Facebook 限制。

## 📋 功能特色

1. **逐診所完整流水線 (`run_city_pipeline.py`)** ⭐ 推薦
   - 指定城市，逐診所走完完整流程：**爬取 FB → 生成文案 → 發送 Messenger → 標記+存檔**，再換下一間。
   - 每間診所完成後**立即存檔 CSV**，斷電不丟資料。
   - 支援全台 22 縣市篩選（台中、台北、新北、高雄等）。
   - 內建安全機制：連續 3 次失敗自動斷路、CAPTCHA 暫停、Ctrl+C 安全退出。

2. **診所資訊自動爬取 (`scrape_fb_info.py`)**
   - 自動搜尋並收集診所的 Facebook 粉絲專頁、公開 Email 以及 Messenger 連結。
   - **中醫與牙醫過濾**：系統會自動偵測「中醫」、「牙科」、「牙醫」等科別與關鍵字並予以排除，只針對西醫診所進行行銷外展。
   - 提取專頁的「簡介」與「最新貼文」，做為後續 AI 分析與文案生成的基礎資料。

3. **AI 客製化文案生成 (`generate_copy_llm.py`)**
   - 串接本地大型語言模型（Qwythos-9B reasoning model，`http://localhost:8080`）。
   - 根據診所名稱、診療科別（如兒科、眼科、外科）以及簡介與貼文，自動生成**高度客製化**的行銷文案。
   - 內建 Pydantic 驗證與黑名單過濾，排除違反台灣醫療法之誇大不實詞彙（如「最佳」、「全台第一」）及簡體中文洩漏，失敗時提供重試與通用文案備用。
   - **注意**：`max_tokens` 必須 ≥ 1024，因 reasoning model 會先消耗 token 在內部推理鏈（chain-of-thought），再輸出實際內容。

4. **智慧慢速開發發送 (`send_outreach.py`)**
   - 模擬真人輸入與發送，自動將 Messenger 網址轉換為 Facebook 訊息頁面 (`https://www.facebook.com/messages/t/`) 進行發送，完美繞過 `messenger.com` 獨立域名的登入封鎖與二階段登入攔截。
   - **防封鎖動態退避 (Adaptive Backoff)**：偵測到臉書限制關鍵字時，自動將隨機冷卻延遲乘數加倍，拉長間隔；成功發送後逐步降速恢復。
   - **硬熔斷機制 (Halt Circuit Breaker)**：連續 3 次遭遇發送失敗或臉書限制時，自動終止任務並進行硬熔斷，避免帳號遭受永久停權。

5. **城市批次協調 (`run_city_campaign.py`)**
   - 按城市篩選，可單獨執行爬取、文案生成或發送步驟。
   - 適合需要分階段處理的場景。

6. **主控協調 CLI (`run_campaign.py`)**
   - 提供一鍵式協調整個 Pipeline 的入口（不分城市）。

7. **追蹤與統計儀表板 (`outreach_dashboard.html`)**
   - 提供直觀的網頁儀表板，可載入 `clinics西醫.csv` 並即時統計已處理、待發送、發送失敗等進度。

---

## ⚙️ 專案路徑與配置

| 項目 | 路徑 |
|------|------|
| 資料庫 CSV | `./clinics西醫.csv` |
| 發送日誌 | `./outreach_sent_log.jsonl` |
| JSON 快取 | `./clinic_links.json` |
| 瀏覽器 Profile | `./browser_profile` |
| 瀏覽器指紋 | `--fingerprint=77889` |
| Local LLM | `http://localhost:8080/v1/chat/completions` |
| Venv Python | `./.venv/bin/python3` |

---

## 🚀 快速開始

### 第一步：環境初始化
```bash
uv venv
uv pip install -r requirements.txt
uv run playwright install chromium
```

### 第二步：建立 Facebook 登入工作階段 (Cookie 匯入)
1. 在日常瀏覽器中登入 Facebook。
2. 安裝 **Cookie-Editor** 擴充功能，選擇 **Export → JSON** 複製 Cookie。
3. 存為 `./fb_cookies.json`。
4. 執行匯入：
   ```bash
   ./.venv/bin/python3 import_cookies.py
   ```

### 第三步：指定城市，一鍵執行

```bash
# 查看台中診所統計
./.venv/bin/python3 run_city_pipeline.py --city 台中 --stats

# Dry-run 測試 3 筆
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 3 --dry-run

# 正式發送 20 筆（每筆間隔 5-10 分鐘）
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 20
```

### CLI 參數

```
--city CITY        目標城市（台中、台北、新北、高雄等）
--limit N          處理上限（預設 20）
--dry-run          測試模式，貼上文案但不發送
--stats            僅顯示統計
--delay-min SEC    最小冷卻秒數（預設 300）
--delay-max SEC    最大冷卻秒數（預設 600）
```

---

## 🤖 AI Agent 自動化操作

本專案內建 `.agents/skills/doctor-toolbox-poster/` skill，支援 Antigravity / Hermes agent 自主執行。

### 使用 `/goal` 指令
```
/goal 執行台中 50 筆診所行銷流水線
```

### 多城市排程
```
/goal 依序對台中、台北、高雄各處理 30 筆診所行銷
```

Agent 會自動讀取 skill 並執行完整流水線，遇到問題自動處理或安全停止。

---

## 🛠️ 開發與測試

```bash
# 單元測試
PYTHONPATH=. pytest tests/test_fallback.py tests/test_backoff.py tests/test_campaign.py
```

**排錯提示**：若發送失敗，可至 `/tmp` 目錄下尋找截圖：
- `pipeline_textbox_failed.png` — 輸入框定位失敗
- `pipeline_failed_*.png` — 發送被限制
- `pipeline_sent_*.png` — 發送成功確認

---

## 📝 開發與討論紀錄 (Development & Discussion Records)

### 📅 2026-06-27 更新：資料庫遷移、A/B 測試與 Hermes 整合 (SQLite, A/B Testing, and Hermes Integration)

#### 1. 🗄️ SQLite 資料庫遷移 (SQLite Database Migration)
- **中**: 已建立 [db.py](file:///home/hsuyungfeng/DevSoft/doctor-toolbox-post/db.py) 模組並將 11,870 筆診所資料匯入本地 `clinics.db`。核心流水線 [run_city_pipeline.py](file:///home/hsuyungfeng/DevSoft/doctor-toolbox-post/run_city_pipeline.py) 與批次腳本已完全遷移至 SQLite 讀寫，解決大檔案 CSV 讀寫效能與損毀風險。
- **EN**: Created [db.py](file:///home/hsuyungfeng/DevSoft/doctor-toolbox-post/db.py) and migrated 11,870 clinics into local `clinics.db`. [run_city_pipeline.py](file:///home/hsuyungfeng/DevSoft/doctor-toolbox-post/run_city_pipeline.py) and batch scripts now read/write directly to SQLite, resolving CSV performance bottlenecks and data corruption risks.

#### 2. ⚖️ A/B 測試機制 (A/B Copy Testing)
- **中**: 實作隨機分流機制（`generic-v1` 與 `personalized-v1`）。`generic-v1` 套用通用文案，`personalized-v1` 則調用本地 LLM（Qwythos-9B）生成客製化文案，分流組別與發送狀態皆記錄於 SQLite。
- **EN**: Implemented random A/B splits (`generic-v1` and `personalized-v1`). The `generic-v1` uses the generic template, whereas `personalized-v1` triggers the local LLM (Qwythos-9B) for customized copy. Splits are recorded in SQLite.

#### 3. 🤖 Hermes Agent 整合 (Hermes Agent Setup)
- **中**:
  - 於 `~/.hermes/skills/` 中建立軟連結指向專案技能。
  - 於 `~/.hermes/tools/doctor_outreach/tool.yaml` 註冊自訂工具 `doctor_outreach`。
  - 確認 Hermes 預設使用本地 `llama-qwen36` 容器作為 LLM 引擎。
- **EN**:
  - Linked the project skill in `~/.hermes/skills/`.
  - Registered a custom tool named `doctor_outreach` in `~/.hermes/tools/doctor_outreach/tool.yaml`.
  - Verified Hermes uses the local `llama-qwen36` container as its default LLM.

#### 4. 🧭 外展管道與防封鎖策略建議 (Outreach Channels & Safety Strategy)
- **💬 Messenger 私訊 (Messenger DM)** ⭐ **最優選 / Priority**:
  - **中**: 一對一商務洽談，最具私密性，不易觸發檢舉封鎖，為核心推廣管道。
  - **EN**: 1-on-1 business inquiry. Offers high privacy, lowest risk of spam flags, and acts as the primary conversion driver.
- **📍 Google Maps 5星評論 (Google Maps 5-Star Reviews)**:
  - **中**: Google 審查嚴格。**不可放網址或強烈廣告詞**，否則會被自動隱藏（Shadow-ban）。建議採用「軟性病看診體驗 + 順便推薦實用 AI 語音病歷工具」的客觀口吻撰寫評論。
  - **EN**: Google filters reviews heavily. **Avoid links or hard-selling terms** to prevent shadow-bans. Write reviews using a soft tone (e.g. sharing general positive patient experience while mentioning the useful AI voice tool).
- **📰 新聞事件/開放論壇留言 (News / Forum Comments)** ❌ **不推薦 / Not Recommended**:
  - **中**: 討論區受眾為社會大眾，並非目標客群（醫師/院長），且新聞網站具有極強的防垃圾機器人機制，容易導致官方網域 `doctor-toolbox.com` 被永久封鎖，並損害品牌形象。
  - **EN**: Public news boards target general audience, not clinic directors. Automated URL spamming triggers IP blocks, risks blacklisting `doctor-toolbox.com`, and damages brand reputation.
