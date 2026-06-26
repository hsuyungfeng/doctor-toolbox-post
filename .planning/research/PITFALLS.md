# Pitfalls Research

**Domain:** Facebook Messenger automation / browser fingerprinting / LLM outreach pipeline
**Researched:** 2026-06-26
**Confidence:** HIGH (domain-specific operational knowledge; no external verification needed for most items)

---

## Critical Pitfalls

### Pitfall 1: Facebook Account Permanent Ban from Aggressive Rate

**What goes wrong:**
The Facebook account used for sending gets permanently banned, not just temporarily rate-limited. Unlike temporary "暫時被限制," a permanent ban cannot be recovered — all sending history and session state is lost.

**Why it happens:**
Developers see the 5–10 min delay working and gradually reduce it during testing ("just one quick batch"), or implement parallelization before the delay strategy is proven safe at scale. Facebook's ML flagging is cumulative: many near-limit sends stack into a hard ban.

**How to avoid:**
- Treat 5–10 min delay as a floor, not a target. Never reduce below 5 min in production.
- Implement `MAX_DAILY_SENDS` hard cap (suggest ≤80/day per account) enforced in code, not just operator discipline.
- Keep the graceful shutdown on "無法傳送" / "暫時被限制" detection — do NOT add retry logic that re-attempts after block signal.
- Run parallelization only with separate Facebook accounts, never multiple sessions on the same account.

**Warning signs:**
- Strings like "功能已暫時停用" appearing in screenshots
- Reply rate dropping to zero without error signals
- Increasing frequency of "暫時被限制" per batch

**Phase to address:** Phase 1 (already partially implemented); verify hard cap enforcement before Phase 2 parallelization.

---

### Pitfall 2: CloakBrowser Fingerprint Drift Across OS Updates

**What goes wrong:**
CloakBrowser fingerprint `88888` produces different signals after a CloakBrowser version update or system library update, causing Facebook to detect a "new device" and trigger account verification or shadow-ban.

**Why it happens:**
Fixed fingerprint ID `88888` is a profile slot, not a cryptographic identity. The underlying Canvas/WebGL/AudioContext spoofing values depend on CloakBrowser's internal implementation, which changes across versions.

**How to avoid:**
- Pin the CloakBrowser version and never update without first testing fingerprint consistency against a fingerprint-check site (e.g., browserleaks.com).
- Before any CloakBrowser upgrade, run a dry-run batch and check for account verification prompts.
- Document the exact CloakBrowser version in `requirements.txt` or a `VERSIONS.md`.

**Warning signs:**
- Facebook prompting for phone verification after routine session start
- "新的登入" security alerts on the account email

**Phase to address:** Phase 2 (before parallelization increases exposure).

---

### Pitfall 3: LLM Generating Simplified Chinese Instead of Traditional Chinese

**What goes wrong:**
`llama-qwen36` outputs Simplified Chinese (简体字) copy that gets sent to Taiwan clinic owners, appearing unprofessional and reducing conversion. The model defaults to Simplified Chinese in its training distribution.

**Why it happens:**
The base Qwen model is trained predominantly on Simplified Chinese. Without an explicit, enforced Traditional Chinese constraint in the system prompt, output drifts — especially for specialty-specific vocabulary ("眼科" vs. specific terms that differ between variants).

**How to avoid:**
- Add `繁體中文` enforcement in BOTH the system prompt AND user prompt (belt-and-suspenders).
- Post-process LLM output with `opencc` (OpenCC Python library) to force convert to Traditional Chinese before sending.
- Include Traditional Chinese keyword validation in the dry-run screenshot check.

**Warning signs:**
- Characters like "药" (simplified) appearing instead of "藥" (traditional)
- Clinic owners not responding / responding with confusion about "mainland Chinese" tone

**Phase to address:** Phase 1 (active); validate before each new batch campaign.

---

### Pitfall 4: Duplicate Message Sends Due to CSV State Race

**What goes wrong:**
The same clinic receives the Messenger message twice (or more), which marks the sender as spam and can trigger manual reports from the clinic owner — accelerating account ban.

**Why it happens:**
CSV-based state tracking has no atomic write guarantee. If the script crashes after sending but before writing the "sent" status to CSV, the next run re-sends to the same clinic. Also possible when running two terminal sessions against the same CSV simultaneously.

**How to avoid:**
- Write a "pending" status to CSV *before* attempting the send, then update to "sent" or "failed" after. This prevents re-send on crash.
- Add a startup deduplication check: load all rows with status "sent" or "pending" into a set and skip them before starting any sends.
- Use file locking (`fcntl.flock`) when reading/writing the CSV in any parallelization scenario.
- Consider migrating to SQLite for atomic updates before enabling parallelization (already on Active list).

**Warning signs:**
- Clinic owners responding "你已經傳過了" (you already sent this)
- JSONL audit log showing two entries for the same clinic within a short window

**Phase to address:** Phase 1 (critical); must be resolved before Phase 2 parallelization.

---

### Pitfall 5: LLM Docker Container Silent Failure Mid-Batch

**What goes wrong:**
The local `llama-qwen36` Docker container runs out of memory (OOM) or crashes mid-batch. The script either hangs waiting for a response, generates empty copy, or sends a blank/malformed message to a clinic.

**Why it happens:**
128k context window + multiple concurrent requests (or very long scraped clinic pages) can push Docker container memory past limits. OOM kills are silent from the Python process's perspective — the HTTP connection just drops.

**How to avoid:**
- Add a health check call to `http://localhost:8080/v1/models` at script startup and fail fast if LLM is not available.
- Set explicit HTTP timeout (30–60 seconds) on all LLM API calls — never block indefinitely.
- Validate LLM response length (>50 漢字, <200 漢字) before sending; abort and log if invalid.
- Set Docker memory limit (`--memory=16g` or appropriate) to get explicit OOM errors instead of silent hangs.

**Warning signs:**
- LLM API calls taking >60 seconds
- Generated copy shorter than 50 characters
- Docker `docker stats` showing memory near container limit

**Phase to address:** Phase 1 (active); add health check before each batch run.

---

### Pitfall 6: Google Maps 5-Star Reviews Triggering Spam Detection

**What goes wrong:**
Google Maps detects the review account as a bot and removes the reviews, or worse, flags the reviewed clinic's GMB listing as suspicious — harming the clinic's reputation and creating a support burden.

**Why it happens:**
Review posting via browser automation has consistent timing signatures. Google Maps also correlates: same account posting reviews for many unrelated clinics in a short window is a strong spam signal.

**Why it matters here:**
Unlike Messenger (direct private outreach), Google Maps reviews are public. A clinic owner who receives an obviously automated 5-star review may report it, triggering Google investigation of the account.

**How to avoid:**
- Apply the same 5–10 min delay discipline to review posting as to Messenger sends.
- Vary review text meaningfully (not just specialty-swap templates) — identical review structure across clinics is detected.
- Limit reviews per account per day to ≤10; use separate Google accounts for review posting vs. search/scraping.
- Consider whether the ROI of Google Maps reviews justifies the account risk — Messenger is the primary channel.

**Warning signs:**
- Reviews being removed within 24 hours of posting
- "這則評論已標記為不符合我們的政策" appearing in the account

**Phase to address:** Phase 1 (active `post_clinics.py`); audit before scaling beyond Taichung test.

---

### Pitfall 7: Hardcoded External Data Path Breaking Cross-Machine Operation

**What goes wrong:**
Scripts fail immediately on any machine that is not the original development machine because `/home/hsuyungfeng/文件/doctor-toolbox-post/` doesn't exist.

**Why it happens:**
Path was hardcoded for convenience during initial development. The constraint is documented but not enforced — no error message tells the user what to configure.

**How to avoid:**
- Move the external data path to a config file (`.env` or `config.yaml`) at repo root, with a clear error message when the path doesn't exist.
- Add a startup validation function that checks all required external paths and fails with actionable error messages before doing any work.
- Document the required directory structure in README.

**Warning signs:**
- `FileNotFoundError` on `clinics西醫.csv` path
- Script silently operating on empty data

**Phase to address:** Phase 1 (tech debt); low urgency for single-operator use but blocks any handoff.

---

### Pitfall 8: Scraping Returning Stale FB Page Data

**What goes wrong:**
The scraper captures an old "Latest Post" from weeks ago because the clinic's Facebook page has no recent activity, and the LLM generates copy referencing outdated context — appearing out of touch and reducing credibility.

**Why it happens:**
Many Taiwan 西醫 clinics have inactive Facebook pages (no posts in 6+ months). The scraper returns whatever the last post is without date-checking.

**How to avoid:**
- Check post date during scraping; if latest post is >90 days old, flag clinic as "inactive FB" and use generic copy instead of post-referencing copy.
- The `generate_generic_copies.py` integration (already on Active list) directly addresses this — prioritize that integration.
- Add post-date to the scraped data schema so the LLM prompt can conditionally reference it.

**Warning signs:**
- LLM-generated copy referencing clinic posts about Chinese New Year in July
- Clinic owners responding with confusion about the referenced post

**Phase to address:** Phase 1 → Phase 2 (integrate `generate_generic_copies.py` first).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| CSV for all state | No DB setup, human-readable | Race conditions at parallel scale, slow queries at 10k+ rows | Until >5k clinics or parallelization |
| Hardcoded external data path | Works immediately on dev machine | Breaks on any other machine, blocks handoff | Never — move to config file |
| Fixed random delay (5–10 min) | Simple, safe | Cannot adapt to block signals; sub-optimal throughput | Until adaptive backoff is implemented |
| No LLM output validation | Faster iteration | Risk of blank/malformed messages being sent | Never — add length + language check |
| Integration tests against real FB/Google | Tests actual behavior | Fragile, slow, requires live session | Acceptable given no good mock exists |
| Single Facebook account for all sends | Simple auth | Single point of failure; account ban = full stop | Until parallelization phase |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CloakBrowser SDK | Starting new fingerprint each session to "stay fresh" | Keep fingerprint `88888` fixed across all sessions — change = new device signal |
| CloakBrowser SDK | Running multiple sessions on same fingerprint simultaneously | One active session per fingerprint at a time — concurrent use corrupts session state |
| llama-qwen36 API | Sending full clinic page HTML as context | Pre-extract only Intro + Latest_Post text; HTML inflates token count and confuses model |
| llama-qwen36 API | No timeout on LLM call | Always set `timeout=60` in `requests.post()` — silent hang on OOM kills batch |
| Facebook Messenger | Navigating directly to `m.me/` links | Use scraped Messenger link from FB page; `m.me/` links may redirect to different flow on CloakBrowser |
| Facebook Messenger | Sending immediately after page load | Wait for Messenger input field to be fully interactive; premature send = empty message |
| Google Maps Reviews | Using same account for Search + Reviews | Separate accounts: GMB review account should have organic-looking history |
| JSONL audit log | Appending without flush | Use `file.flush()` after each append — crash during buffered write loses the record |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| CSV linear scan for "already sent" check | Startup gets slower as sent list grows | Load sent set into memory at startup; use set lookup not row scan | >2k sent records |
| LLM generating copy for all clinics upfront | Memory spikes; OOM on large batches | Generate copy per-clinic just before sending | >500 clinics in single batch |
| Screenshot storage accumulating unbounded | Disk fills up; dry-run mode stops working | Prune screenshots older than 7 days in batch startup | >30 days of dry runs |
| JSONL log scan for deduplication | Log read time grows linearly | Build a sent-ID set in memory at startup | >5k log entries |
| Google Search rate-limiting scrape phase | Discovery slows, then fails with CAPTCHA | Add 10–30 second delays between Google searches; use site:facebook.com queries not Maps API | >50 searches in 1 hour |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing clinic CSV or JSONL logs to git | Exposes clinic PII and send history publicly | Keep data path external to repo; verify `.gitignore` covers all CSV/JSONL/screenshot outputs |
| Hardcoding Facebook session cookies in scripts | Account takeover if repo is shared or leaked | Session cookies live in CloakBrowser profile only — never extract/log them |
| Logging full Messenger message content to stdout | Terminal history or CI logs leak copy content | Log only clinic ID + status, not full message text |
| Docker container running as root | Container escape = host compromise | Run llama-qwen36 Docker with `--user 1000:1000` |
| No input sanitization on scraped FB page content | Prompt injection: clinic page containing LLM instruction overrides | Wrap scraped content in explicit "DATA:" delimiters in LLM prompt; validate output doesn't contain system prompt fragments |

---

## UX Pitfalls (Operator Experience)

| Pitfall | Operator Impact | Better Approach |
|---------|----------------|-----------------|
| No progress ETA during batch run | Operator doesn't know if batch will finish before they need the machine | Print estimated completion time at batch start: `(remaining_clinics × avg_delay) / 60` minutes |
| Dry-run screenshots not date-stamped | Can't tell which screenshots are from which run | Prefix screenshot filenames with `YYYYMMDD_HHMMSS_` |
| Dashboard requires manual CSV refresh | Stale data; operator doesn't see real-time status | Add auto-refresh meta tag (60s) to `outreach_dashboard.html` |
| Batch stops silently on block signal | Operator returns to find nothing sent for 3 hours | Send desktop notification or write to a `BLOCKED` sentinel file that's easy to detect |
| No summary report at batch end | Operator must manually count JSONL entries | Print `BATCH COMPLETE: X sent, Y failed, Z skipped` to stdout at end of every batch |

---

## "Looks Done But Isn't" Checklist

- [ ] **Messenger send:** Verify the message text actually appears in the conversation thread (screenshot after send), not just that the send button was clicked
- [ ] **Graceful shutdown:** Verify that on "暫時被限制" detection, the script writes current clinic status as "failed" to CSV before exiting — not just exits
- [ ] **Dry-run mode:** Verify dry-run screenshots show the *actual message text* that would be sent, not just the input field
- [ ] **Generic copy fallback:** Verify `generate_generic_copies.py` is actually called in the main pipeline, not just exists as a standalone script
- [ ] **JSONL deduplication:** Verify that restarting after a crash does NOT re-attempt clinics already in JSONL with "sent" status
- [ ] **LLM output validation:** Verify that a blank LLM response causes the clinic to be skipped (logged as "failed"), not sent as an empty message
- [ ] **Block detection keywords:** Verify the keyword list covers all current Facebook error strings — these change with FB UI updates; test at least once per month
- [ ] **Google Maps review:** Verify the 5-star rating was actually saved and visible in incognito before considering a review "posted"

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Facebook account temporarily banned | MEDIUM | Wait 24–48 hours; do not attempt sends; run dry-run first after restriction lifts |
| Facebook account permanently banned | HIGH | Create new account with fresh identity; rebuild CloakBrowser profile with new fingerprint; restart send campaign from last JSONL checkpoint |
| LLM Docker container OOM | LOW | `docker restart llama-qwen36`; re-run from last checkpoint (CSV/JSONL prevents re-send) |
| CSV duplicate sends discovered | MEDIUM | Audit JSONL for duplicate clinic IDs; add affected clinics to manual blocklist; apologize if clinic contacts you |
| Scraped data is stale/wrong | LOW | Re-scrape clinic; regenerate copy; update JSONL with corrected entry |
| CloakBrowser fingerprint flagged | HIGH | Create new fingerprint profile; test with non-promotional browsing for 48h before resuming outreach |
| Google Maps reviews removed | LOW | Accept loss; reduce review frequency; do not attempt to re-post removed reviews (triggers deeper flag) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Facebook permanent ban from rate | Phase 1 (enforce `MAX_DAILY_SENDS` cap) | Run 1-week batch, confirm account health |
| CloakBrowser fingerprint drift | Phase 2 (pin version before parallelization) | Post-upgrade fingerprint check on browserleaks.com |
| LLM generating Simplified Chinese | Phase 1 (add OpenCC post-processing) | Spot-check 10 generated messages per batch for traditional characters |
| Duplicate sends from CSV race | Phase 1 (add "pending" pre-write) + Phase 3 (SQLite migration) | Simulate crash mid-send, verify no duplicate on restart |
| LLM Docker silent failure | Phase 1 (add health check + timeout) | Kill Docker mid-batch, verify graceful skip |
| Google Maps spam detection | Phase 1 (audit `post_clinics.py` delays) | Check review survival rate after 72 hours |
| Hardcoded external path | Phase 2 (config file refactor) | Run from fresh directory, verify actionable error |
| Stale FB page data in copy | Phase 1→2 (integrate generic fallback) | Test with clinic with no posts in 90 days |

---

## Sources

- Project context: `.planning/PROJECT.md` — brownfield survey of existing codebase
- Domain knowledge: Facebook Messenger automation anti-ban patterns (operational knowledge, HIGH confidence)
- Domain knowledge: CloakBrowser fingerprinting behavior (operational knowledge, MEDIUM confidence — no public docs on internal fingerprint slot implementation)
- Domain knowledge: Qwen model language default behavior (HIGH confidence — well-documented training distribution)
- Domain knowledge: Google Maps review spam detection patterns (MEDIUM confidence — based on known GMB spam patterns)
- Domain knowledge: CSV race conditions under concurrent access (HIGH confidence — standard file I/O behavior)

---
*Pitfalls research for: Facebook Messenger outreach automation / Taiwan clinic targeting pipeline*
*Researched: 2026-06-26*
