---
name: doctor-toolbox-poster
description: Guide and execute the clinic search, FB scraping, and Facebook messages posting pipeline for Doctor Toolbox. Use this skill when asked to run, test, crawl, post, or manage comments/posts to clinic FB pages or Google Maps, or check post logs.
---

# Doctor Toolbox — 診所 FB Messenger 自動行銷流水線

This skill guides you (the agent) through running, configuring, testing, and troubleshooting the automated clinic promotional posting and Facebook Messages outreach pipeline for **醫師工具箱 (Doctor Toolbox)**.

---

## 📋 Pipeline Overview

The pipeline automates marketing outreach to Western Medicine (西醫) clinics in Taiwan, **one clinic at a time**:

```
For each clinic in target city:
  1. 🔍 Google search → find FB page URL
  2. 🕷️ Scrape FB page → Intro, Messenger link, Latest Posts
  3. ✍️  Local LLM generates personalized copy (fallback: generic copy)
  4. 📤 Send copy via Facebook Messenger (facebook.com/messages/t/)
  5. ✅ Mark status=sent + timestamp in CSV → save immediately
  6. ⏳ Random cooldown 5-10 min → next clinic
```

**Key design**: Each clinic is fully processed end-to-end before moving to the next. CSV is saved after every single clinic for crash safety.

---

## ⚙️ Core Parameters & Fingerprint Persistence

| Parameter | Value |
|-----------|-------|
| **Fingerprint Seed** | `--fingerprint=77889` (MUST be consistent across all sessions) |
| **Browser Profile** | `./browser_profile` → `/home/hsu/doctor-toolbox-post/browser_profile` |
| **Database CSV** | `./clinics西醫.csv` (auto-fallback to workspace root) |
| **Outreach Log** | `./outreach_sent_log.jsonl` |
| **Local LLM** | `http://localhost:8080/v1/chat/completions` (Qwythos-9B reasoning model) |
| **LLM max_tokens** | `1024` (must be ≥1024 — reasoning model uses tokens for chain-of-thought) |
| **Python Environment** | `python3` (Uses system python environment) |
| **Local Firecrawl** | `http://localhost:3002` (Self-hosted docker container for website scraping) |

---

## 🚀 Primary Workflow: City Pipeline (`run_city_pipeline.py`)

This is the **recommended** script for all outreach operations. It handles the complete per-clinic flow.

### Step 0: Prerequisites (one-time setup)

1. **Start Local Scraper (Firecrawl)**:
   ```bash
   cd firecrawl
   docker compose up -d
   cd ..
   ```

2. **Release browser locks** before any browser script:
   ```bash
   pkill -f browser_profile
   ```

3. **Inject Facebook cookies** (required when session expires):
   - Log in to Facebook in your regular browser
   - Export cookies via Cookie-Editor extension → JSON
   - Save to `./fb_cookies.json`
   - Run: `python3 import_cookies.py`

4. **Verify LLM is running**:
   ```bash
   curl -s http://localhost:8080/v1/models | head -5
   ```

### Step 1: Check city stats
```bash
python3 run_city_pipeline.py --city 台中 --stats
```

### Step 2: Dry-run test (verify without sending)
```bash
python3 run_city_pipeline.py --city 台中 --limit 3 --dry-run --delay-min 10 --delay-max 20
```

### Step 3: Full campaign (SLOW & SAFE)
```bash
python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 300 --delay-max 600
```

### All CLI options
```
--city CITY        Target city (台中, 台北, 新北, 桃園, 台南, 高雄, etc.)
--limit N          Max clinics to process (default: 20)
--dry-run          Test mode — paste text but don't send
--stats            Show statistics only, don't execute
--delay-min SEC    Min cooldown between sends (default: 300 = 5 min)
--delay-max SEC    Max cooldown between sends (default: 600 = 10 min)
```

### Supported cities
台中, 台北, 新北, 桃園, 台南, 高雄, 基隆, 新竹, 嘉義, 彰化, 南投, 雲林, 屏東, 宜蘭, 花蓮, 台東, 苗栗, 澎湖, 金門, 連江

---

## 🤖 Hermes / Autonomous Agent Long-Term Operation (自動化代理長效運作協定)

當使用自動化代理（如 Hermes、`/goal` 或背景任務）進行推廣時，必須嚴格遵守以下兩大核心步驟以確保系統安全、帳號防封鎖與資訊準確性：

### 1. 收集診所資訊 (Information Gathering via Local Firecrawl)
- **原理**：流水線會首先搜尋該診所的官網網址。若找到，會自動調用本地 `Firecrawl`（運行在 `http://localhost:3002`）進行深度解析。
- **目標**：自動提取診所官網中的 **Email 電子郵件**、**Facebook 專頁網址**、以及**診所診療內容 (Markdown)**。
- **優勢**：
  - **精準 Email 行銷**：有了 Email 後，能優先通過 Email 進行高投遞率的開發，不會遇到臉書發送限制。
  - **極致個人化**：抓取到的診所介紹會提供給本地 LLM（Qwen 8080 端口），生成高度擬人化的診所專屬文案。

### 2. 擬人化慢速發送 (Humanized Multichannel Posting)
為防止 Facebook 帳號被鎖及郵件伺服器被列為垃圾郵件，發送時需模擬真人的發送行為：
- **多管道發送鏈 (SMTP Email -> Messenger -> FB Comment Fallback)**：
  - **優先發送 Email**：若有 Email 優先以 Gmail app password 自動寄出內嵌 `doctor-toolbox-post.png` 配圖的精美廣告。
  - **次要發送 Messenger**：若無 Email，開啟 CloakBrowser 自動上傳廣告配圖並輸入文案發送。
  - **保底留言**：若 Messenger 發送失敗或未開啟，則自動在該診所粉專的最新貼文下留下完整排版文案。
- **慢速冷卻設定**：
  - **每輪上限**：強烈建議每次背景執行僅設定 **3~5 筆診所**（`--limit 5`）。
  - **發送延遲**：每次發送之間必須設置 **5~10 分鐘** 的隨機冷卻時間（`--delay-min 300 --delay-max 600`），或更安全的 **10~20 分鐘**（`--delay-min 600 --delay-max 1200`）。
  - **每日上限**：每天發送不超過 **10~15 筆**。

### 🚀 自動化安全執行指令 (Slow & Safe Run Commands)
```bash
# 推薦：台中市 5 筆慢速發送，每次發送隨機冷卻 5~10 分鐘 (耗時約 30~50 分鐘)
python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 300 --delay-max 600

# 極致安全模式：隨機冷卻 10~20 分鐘 (適合新帳號或防止郵件限制)
python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 600 --delay-max 1200
```

### Safety mechanisms (built into the script)
1. **Per-clinic CSV save**: Every clinic result is saved immediately — no data loss on crash
2. **Circuit breaker**: 3 consecutive `delivery_failed` → auto-stop
3. **CAPTCHA pause**: Google CAPTCHA → script waits for human input
4. **Ctrl+C safe**: Finishes current clinic, saves, then exits
5. **Login detection**: If FB login required → logs `login_required` and stops

### Agent decision tree
```
IF status == "login_required":
  → STOP. Tell user to re-export cookies and run import_cookies.py
IF status == "delivery_failed" (3x consecutive):
  → STOP. Circuit breaker triggered. Wait 24 hours before retrying.
IF Google CAPTCHA detected:
  → PAUSE. Wait for user to solve manually in the browser window.
IF LLM timeout:
  → Auto-fallback to generic copy (no action needed)
IF all clinics processed:
  → Report stats and move to next city
```

### Multi-city campaign sequence (SLOW & SAFE)
```bash
# Run cities one at a time with low limit (5) and slow delays:
python3 run_city_pipeline.py --city 台中 --limit 5 --delay-min 300 --delay-max 600
python3 run_city_pipeline.py --city 台北 --limit 5 --delay-min 300 --delay-max 600
python3 run_city_pipeline.py --city 新北 --limit 5 --delay-min 300 --delay-max 600
python3 run_city_pipeline.py --city 高雄 --limit 5 --delay-min 300 --delay-max 600
```

---

## 🛠️ Legacy Scripts (Manual / Individual Steps)

These scripts can be used to run individual pipeline steps independently:

| Script | Purpose | Command |
|--------|---------|---------|
| `scrape_fb_info.py` | Scrape FB pages (batch) | `python3 scrape_fb_info.py` |
| `generate_copy_llm.py` | Generate LLM copy (batch) | `python3 generate_copy_llm.py` |
| `send_outreach.py` | Send Messenger (batch) | `python3 send_outreach.py --limit 5` |
| `run_campaign.py` | Orchestrate all 3 steps sequentially | `python3 run_campaign.py --limit 5` |
| `run_city_campaign.py` | City-filtered batch orchestrator | `python3 run_city_campaign.py --city 台中 --limit 5` |
| `post_clinics.py` | FB page comment posting (not Messenger) | `python3 post_clinics.py` |
| `import_cookies.py` | Import FB cookies into browser profile | `python3 import_cookies.py` |

---

## 🔍 Log Schema & Progress Tracking

Progress is logged in `outreach_sent_log.jsonl`:

| Status | Meaning |
|--------|---------|
| `sent` | ✅ Message sent successfully |
| `dry_run` | 🧪 Text pasted in test mode |
| `no_fb` | FB page not found for this clinic |
| `no_messenger` | FB page found but no Messenger link |
| `textbox_not_found` | Messenger input box not located |
| `login_required` | ⚠️ Session expired — re-import cookies |
| `delivery_failed` | 🛑 FB restricted sending |
| `session_halted` | 🛑 Circuit breaker triggered (3 consecutive blocks) |

CSV columns updated per clinic:
- `FB_URL`: Facebook page URL
- `Email`: Contact email
- `Messenger`: Messenger link (m.me/xxx)
- `Intro`: FB page introduction text
- `Latest_Post`: Most recent FB post content
- `Personalized_Copy`: Generated outreach text
- `Messenger_Status`: Delivery status (sent/dry_run/failed/etc.)
- `Outreach_Time`: ISO timestamp of last action

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `login_required` | Re-export FB cookies → `import_cookies.py` |
| `textbox_not_found` | Check `/tmp/pipeline_textbox_failed.png`. Page may block DMs. |
| `delivery_failed` | FB restricted account. Wait 24h. Check screenshot in `/tmp/`. |
| LLM empty string | Verify `max_tokens ≥ 1024` in `generate_copy_llm.py`. Qwythos-9B reasoning model consumes tokens for chain-of-thought before output. |
| LLM timeout | Check `llama-server` is running: `ss -tlnp sport = :8080`. May need to restart. |
| Google CAPTCHA | Solve manually in the browser window, then press Enter in terminal. |
| Browser lock error | Run `pkill -f browser_profile` before starting. |
