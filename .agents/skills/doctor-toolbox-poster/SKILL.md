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
| **Venv Python** | `./.venv/bin/python3` |

---

## 🚀 Primary Workflow: City Pipeline (`run_city_pipeline.py`)

This is the **recommended** script for all outreach operations. It handles the complete per-clinic flow.

### Step 0: Prerequisites (one-time setup)

1. **Release browser locks** before any browser script:
   ```bash
   pkill -f browser_profile
   ```

2. **Inject Facebook cookies** (required when session expires):
   - Log in to Facebook in your regular browser
   - Export cookies via Cookie-Editor extension → JSON
   - Save to `./fb_cookies.json`
   - Run: `./.venv/bin/python3 import_cookies.py`

3. **Verify LLM is running**:
   ```bash
   curl -s http://localhost:8080/v1/models | head -5
   ```

### Step 1: Check city stats
```bash
./.venv/bin/python3 run_city_pipeline.py --city 台中 --stats
```

### Step 2: Dry-run test (verify without sending)
```bash
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 3 --dry-run --delay-min 10 --delay-max 20
```

### Step 3: Full campaign
```bash
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 20
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

## 🤖 Hermes / Autonomous Agent Long-Term Operation

When running as an autonomous agent (Hermes, `/goal`, or background task), follow this protocol:

### Autonomous execution command
```bash
# Run 50 clinics in 台中 (will take ~4-8 hours with delays)
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 50

# Run with shorter delays (more aggressive, higher risk)
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 50 --delay-min 180 --delay-max 300
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

### Multi-city campaign sequence
```bash
# Run cities one at a time:
./.venv/bin/python3 run_city_pipeline.py --city 台中 --limit 50
./.venv/bin/python3 run_city_pipeline.py --city 台北 --limit 50
./.venv/bin/python3 run_city_pipeline.py --city 新北 --limit 50
./.venv/bin/python3 run_city_pipeline.py --city 高雄 --limit 50
```

---

## 🛠️ Legacy Scripts (Manual / Individual Steps)

These scripts can be used to run individual pipeline steps independently:

| Script | Purpose | Command |
|--------|---------|---------|
| `scrape_fb_info.py` | Scrape FB pages (batch) | `./.venv/bin/python3 scrape_fb_info.py` |
| `generate_copy_llm.py` | Generate LLM copy (batch) | `./.venv/bin/python3 generate_copy_llm.py` |
| `send_outreach.py` | Send Messenger (batch) | `./.venv/bin/python3 send_outreach.py --limit 10` |
| `run_campaign.py` | Orchestrate all 3 steps sequentially | `./.venv/bin/python3 run_campaign.py --limit 10` |
| `run_city_campaign.py` | City-filtered batch orchestrator | `./.venv/bin/python3 run_city_campaign.py --city 台中 --limit 20` |
| `post_clinics.py` | FB page comment posting (not Messenger) | `./.venv/bin/python3 post_clinics.py` |
| `import_cookies.py` | Import FB cookies into browser profile | `./.venv/bin/python3 import_cookies.py` |

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
