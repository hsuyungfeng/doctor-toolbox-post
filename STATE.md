# 🩺 Doctor Toolbox Outreach Loop State

This file acts as the persistent, long-term state memory for background AI agents (e.g. Hermes, Antigravity) running automated loops on this project.

---

## 🚦 System Status

- **System State**: `RUNNING`
- **Active Campaign**: 彰化 (博元婦產科診所 [3/5] 處理中)
- **Active Process ID**: `proc_10ad008317aa`
- **Active Cron Job ID**: `8b84abc2ddd0`
- **Last Sync / CSV Export**: `2026-07-02 10:22:30` (Synced 11870 rows back to CSV successfully)

---

## 🎯 Campaign Queue (Central Taiwan targeting sequence)

| County/City | Limit | Status | Progress (SQLite) | Process ID |
| :--- | :--- | :--- | :--- | :--- |
| **台中** | 5 | `COMPLETED` | 5/5 sent / fb_commented | Completed on 2026-07-01 |
| **彰化** | 20 | `IN_PROGRESS` | Processing candidate list | `proc_10ad008317aa` |
| **南投** | 20 | `PENDING` | - | - |
| **苗栗** | 20 | `PENDING` | - | - |
| **雲林** | 20 | `PENDING` | - | - |

---

## 🔧 Loop Audit & Readiness Checklist

- [x] **Database website caching (`website_url` column)**: Skip Google Search for cached clinics to avoid CAPTCHA blocks.
- [x] **Humanized Playwright actions (Mouse trajectory)**: Simulate human mouse accelerations and scroll actions to prevent FB spam bans.
- [x] **SMTP email outreach with inline CID images**: Pre-configured using secure Gmail App Passwords.
- [x] **Automatic database-to-CSV synchronization**: Pipeline automatically runs `sync_db_to_csv.py` on completion or shutdown.
- [x] **Circuit Breaker safety shutdown**: Halts process after 3 consecutive failures.
- [ ] **Automated CSS Selectors Auto-fix Loop**: Hermes triages DOM screenshots and updates selectors automatically (documented below).

---

## 🤖 Autonomous Maintenance & Auto-Fix Protocol

When running autonomously, if Hermes encounters a loop failure or pipeline crash (e.g. `Circuit Breaker Triggered` or `textbox_not_found`):

### 1. Auto-Triage Steps
1. Locate `/tmp/pipeline_textbox_failed.png` and read `/tmp/pipeline_dom_failed.html` (if generated) to inspect Facebook's current webpage markup.
2. Find the new classes, roles, or attributes of:
   - The Messenger input text box.
   - The FB Page "Comment" button.
3. Update the selectors inside `run_city_pipeline.py` or `post_clinics.py`.

### 2. Verify and Re-test
1. Run syntax verification: `python3 -m py_compile run_city_pipeline.py`
2. Run the unit test suite: `pytest tests/`
3. If tests pass, stage and commit the fix to git:
   ```bash
   git commit -am "Auto-fix Facebook CSS selector following DOM update" && git push
   ```
4. Restart the campaign pipeline using `xvfb-run python3 run_city_pipeline.py`.
