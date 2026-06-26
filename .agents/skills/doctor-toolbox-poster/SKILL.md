---
name: doctor-toolbox-poster
description: Guide and execute the clinic search, FB scraping, and comment posting pipeline for Doctor Toolbox. Use this skill when asked to run, test, crawl, post, or manage comments/posts to clinic FB pages or Google Maps, or check post logs.
---

# Doctor Toolbox Poster & Messenger Outreach Pipeline Skill

This skill guides you (the agent) through running, configuring, testing, and troubleshooting the automated clinic promotional posting and Messenger outreach pipeline for **醫師工具箱 (Doctor Toolbox)**.

---

## 📋 Project Overview

The Doctor Toolbox pipeline is designed to automate marketing and outreach to Western Medicine (西醫) clinics in Taiwan:
1. **Information Gathering**: Collect clinic details, Facebook page links, public Emails, and Messenger URLs. Extract the clinic's page **Intro (簡介)** and **Latest Posts (最新貼文)**.
2. **AI Personalization**: Use a local LLM (Ollama / llama.cpp) to analyze the clinic's specialty and automatically generate customized, high-converting promotional copies.
3. **Slow Outreach (FB Messenger)**: Simulate human messaging to send these personalized pitches via Facebook Messenger. Setting a strict **5 to 10 minutes randomized delay** protects the outreach account from getting banned by Facebook's anti-spam filters.
4. **Log Tracking**: Record sending status in local logs and update the database CSV files.

---

## ⚙️ Core Parameters & Fingerprint Persistence

To bypass Facebook's automated security filters, the browser fingerprint must remain identical across sessions.
* **Fixed Fingerprint Seed**: You **MUST** ensure that `args=["--fingerprint=88888"]` is passed into `launch_persistent_context()` in all browser script launches (e.g., `setup_session.py`, `send_outreach.py`, `scrape_fb_info.py`, and `post_clinics.py`).
* **Profile Path**: `./browser_profile` (resolves to `/home/hsuyungfeng/DevSoft/doctor-toolbox-post/browser_profile`).
* **Main Database CSV**: `/home/hsuyungfeng/文件/doctor-toolbox-post/clinics西醫.csv`.
* **Outreach Log**: `/home/hsuyungfeng/文件/doctor-toolbox-post/outreach_sent_log.jsonl`.
* **Local LLM Endpoint**: `http://localhost:8080/v1/chat/completions` (llama-qwen36, configured with 128k context size `-c 131072`).

---

## 🚀 Step-by-Step Execution Guide for Hermes Agent

When asked to run or manage the outreach process, follow these exact steps:

### Step 1: Release Browser Locks
Before launching any browser script, check and terminate any lingering Chrome or CloakBrowser processes that might lock the profile directory:
```bash
pkill -f browser_profile
```

### Step 2: Initialize / Verify Session
If you encounter `login_required`, ask the user to run the setup session script:
```bash
python3 setup_session.py
```
*Note to Agent*: This will launch a visual browser with 3 tabs: **Facebook**, **Messenger.com**, and **Google Maps**.
* Instructions for the user:
  1. Log in to Facebook.com, checking **"Remember Me"** (保持登入).
  2. Switch to the Messenger tab, and click **"Continue as [Your Name]"** (or log in manually) to authenticate `messenger.com` as well.
  3. Switch to Google Maps and verify login if needed.
  4. Press `Enter` in the terminal to save session cookies.

### Step 3: Scrape Facebook Intro & Latest Posts
Collect page descriptions and recent posts:
```bash
python3 scrape_fb_info.py
```
*Writes to*: `Intro` and `Latest_Post` columns in `clinics西醫.csv`.

### Step 4: Generate Personalized Copywriting
Ensure `llama-qwen36` is running on `http://localhost:8080` (verify with `curl http://localhost:8080/v1/models`), then run:
```bash
python3 generate_copy_llm.py
```
*Writes to*: `Personalized_Copy` column in `clinics西醫.csv`.

### Step 5: Perform Outreach Dry-Run (Verification)
Verify input box selection, typing logic, and active session without sending a message:
```bash
python3 send_outreach.py --dry-run --limit 2
```
*Action*: Paste the copy, take a screenshot to `/tmp/outreach_dryrun.png`, and close.
*Verification*: Check the saved screenshot using `view_file` to visually verify the input text was pasted.

### Step 6: Start Real Outreach Campaign
Start the slow automated sending loop:
```bash
# Sends to 5 clinics slowly (5-10 mins randomized delays)
python3 send_outreach.py --limit 5 --delay-min 300 --delay-max 600
```

---

## 🔍 Log Schema & Progress Tracking

Progress is logged in `outreach_sent_log.jsonl` with the following status indicators:
* `sent`: Message sent.
* `dry_run`: Pasted text successfully in dry-run mode.
* `textbox_not_found`: Input box could not be located.
* `login_required`: Session expired or needs re-authentication.

---

## 🛠️ Diagnostics & Troubleshooting for Agent

1. **`login_required`**:
   The session cookies for `facebook.com` or `messenger.com` have expired. Instruct the user to re-run `python3 setup_session.py`.

2. **`textbox_not_found`**:
   Can occur due to page layout changes or restricted pages. Look at `/tmp/outreach_textbox_failed.png`:
   * If it shows a banner: **「只有 [專頁名稱] 可以傳送訊息」** (broadcast channel), this is a restricted page. The script will correctly log and skip it.
   * If the text box is there but not selected, check and update the textbox selectors in `send_messenger_message` inside `send_outreach.py`.

3. **`無法傳送` (Message Failed to Deliver)**:
   If screenshots show the message bubble sent but with **「無法傳送」** in red text underneath:
   * **This is an anti-spam restriction flag from Facebook.**
   * **IMMEDIATELY KILL THE CAMPAIGN TASK** using the `manage_task` tool to protect the user's account from a permanent ban.
   * Warn the user to check their account status manually.
