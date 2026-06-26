---
name: doctor-toolbox-poster
description: Guide and execute the clinic search, FB scraping, and Facebook messages posting pipeline for Doctor Toolbox. Use this skill when asked to run, test, crawl, post, or manage comments/posts to clinic FB pages or Google Maps, or check post logs.
---

# Doctor Toolbox Poster & Facebook Messages Outreach Pipeline Skill

This skill guides you (the agent/Hermes) through running, configuring, testing, and troubleshooting the automated clinic promotional posting and Facebook Messages outreach pipeline for **醫師工具箱 (Doctor Toolbox)**.

---

## 📋 Project Overview

The Doctor Toolbox pipeline is designed to automate marketing and outreach to Western Medicine (西醫) clinics in Taiwan:
1. **Information Gathering**: Collect clinic details, Facebook page links, public Emails, and Messenger URLs. Extract the clinic's page **Intro (簡介)** and **Latest Posts (最新貼文)**.
2. **Specialty Exclusion Filter**: Automatically filters out and skips Traditional Chinese Medicine (中醫) and Dentists (牙醫/牙科) from the list.
3. **AI Personalization**: Use a local LLM (Ollama / llama.cpp / llama-qwen36) to analyze the clinic's specialty and automatically generate customized, high-converting promotional copies, falling back to a generic copy if the LLM fails.
4. **Slow Outreach (Facebook Messages)**: Open the clinic's message thread directly under the `facebook.com` domain. Simulate human typing to send the pitch. Set a strict **5 to 10 minutes randomized delay** (scaled by backoff multiplier if warnings are encountered) to avoid account blocks.
5. **Log Tracking**: Record sending status in local logs and update the database CSV files.

---

## ⚙️ Core Parameters & Fingerprint Persistence

To bypass Facebook's automated security filters, the browser fingerprint must remain identical across sessions.
* **Fixed Fingerprint Seed**: You **MUST** ensure that `args=["--fingerprint=77889"]` is passed into `launch_persistent_context()` in all browser script launches (e.g., `setup_session.py`, `send_outreach.py`, `scrape_fb_info.py`, and `post_clinics.py`).
* **Profile Path**: `./browser_profile` (resolves to `/home/hsu/doctor-toolbox-post/browser_profile`).
* **Main Database CSV**: `./clinics西醫.csv` (falls back automatically to workspace root if external directory is not present).
* **Outreach Log**: `./outreach_sent_log.jsonl`.
* **Local LLM Endpoint**: `http://localhost:8080/v1/chat/completions` (llama-qwen36, configured with 128k context size `-c 131072`).

---

## 🚀 Step-by-Step Execution Guide for Hermes Agent

When asked to run or manage the outreach process, follow these exact steps:

### Step 1: Release Browser Locks
Before launching any browser script, check and terminate any lingering Chrome or CloakBrowser processes that might lock the profile directory:
```bash
pkill -f browser_profile
```

### Step 2: Initialize / Verify Session (Bypass Captcha)
Facebook blocks direct manual login in automated browsers. To bypass this, use **Cookie Injection**:
1. Log in to Facebook on your everyday browser (Chrome/Edge/Firefox).
2. Install the **Cookie-Editor** extension.
3. Click the extension, select **Export -> JSON** to copy Facebook cookies. *(註：由於本系統直接使用 `facebook.com/messages/t/` 頁面進行發送，因此您只需在 Facebook 分頁上匯出 Cookie 即可，不需要另外匯出 Messenger 的 Cookie！)*
4. Create a file named `fb_cookies.json` in the workspace root and paste the copied JSON array.
5. Run the cookie importer:
   ```bash
   uv run python3 import_cookies.py
   ```
   *This imports cookies into `./browser_profile` and validates the Facebook login session, saving a check screenshot to `./facebook_check.png`.*

### Step 3: Run the Orchestrator CLI (`run_campaign.py`)
Instead of running scripts manually, you can orchestrate the entire pipeline sequentially using `run_campaign.py`.

* **To perform a safe Dry-Run (Verification without sending)**:
  ```bash
  uv run python3 run_campaign.py --dry-run-only
  ```
  *This runs lock release, session verification, FB scraping, AI copy generation, and simulates pasting the message into the text box for 2 clinics. You can verify the result in `/tmp/outreach_dryrun.png`.*

* **To run the actual outreach campaign**:
  ```bash
  uv run python3 run_campaign.py --limit 10 --delay-min 300 --delay-max 600
  ```
  *Processes up to 10 clinics, fetching data, generating copy, and slowly sending out messages.*

---

## 🛠️ Direct Script Usage (Manual Executions)

If you need to run specific parts of the pipeline manually:

### 1. Scrape Facebook Page Info
```bash
uv run python3 scrape_fb_info.py
```
*Action*: Automatically filters out 中醫 and 牙醫, scrapes remaining clinic details (FB page, Email, Intro, latest post) from Google and FB. Updates `./clinics西醫.csv` and `./clinic_links.json`.

### 2. Generate AI Custom Copywriting
```bash
uv run python3 generate_copy_llm.py
```
*Action*: Calls the local Qwen model to write traditional Chinese pitches (80-180 characters, no forbidden words). Updates `Personalized_Copy` in `clinics西醫.csv`.

### 3. Send Outreach Campaigns
```bash
# Dry-run test
uv run python3 send_outreach.py --dry-run --limit 2

# Actual campaign sending
uv run python3 send_outreach.py --limit 10 --delay-min 300 --delay-max 600
```
*Action*: Automatically converts Messenger links (`m.me/xxx`) to direct Facebook message URL formats (`facebook.com/messages/t/xxx`), opens the chat threads, types the copy, and clicks Send.

---

## 🔍 Log Schema & Progress Tracking

Progress is logged in `outreach_sent_log.jsonl` with the following status indicators:
* `sent`: Message sent successfully.
* `dry_run`: Pasted text successfully in dry-run mode.
* `textbox_not_found`: Input box could not be located.
* `login_required`: Session expired or needs re-authentication.
* `delivery_failed`: Facebook restricted message sending.
* `backoff`: Encounted warning; cooling down with scaled delay.
* `session_halted`: Circuit breaker triggered (3 consecutive blocks).

---

## 🛠️ Diagnostics & Troubleshooting for Agent

1. **`login_required`**:
   The session cookies for `facebook.com` have expired. Instruct the user to re-export cookies from their browser and run `uv run python3 import_cookies.py` again.

2. **`textbox_not_found`**:
   Can occur if the page doesn't allow direct messaging. The script will log it and skip. If it occurs on valid pages, inspect `/tmp/outreach_textbox_failed.png` to check layout changes.

3. **`delivery_failed` (Circuit Breaker)**:
   If the screenshot shows the message bubble sent but with **「無法傳送」** or account restriction banners:
   * **The script will automatically scale delay_multiplier (double the delay time)**.
   * **If this happens 3 times consecutively, it triggers `session_halted` and terminates immediately** to prevent account ban.
   * **IMMEDIATELY TERMINATE** if manual intervention is required.
