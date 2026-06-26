# Architecture Research

**Domain:** Automated Browser Outreach Pipeline (Anti-Detection, LLM Copy Generation, Social Platform Delivery)
**Researched:** 2026-06-26
**Confidence:** HIGH (brownfield — derived from reading actual source code)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                        │
│  run_taichung_20.py  (batch runner, invokes pipeline stages) │
└──────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼─────────────────────┐
         ▼                    ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Stage 1:       │  │  Stage 2:       │  │  Stage 3:       │
│  Discovery &    │  │  Copy           │  │  Delivery       │
│  Scraping       │  │  Generation     │  │  (Messenger /   │
│                 │  │                 │  │  Maps / FB)     │
│ scrape_fb_info  │  │ generate_copy   │  │ send_outreach   │
│ crawl_links.py  │  │ _llm.py         │  │ post_clinics.py │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Shared Data Layer                          │
│                                                              │
│  clinics西醫.csv  ←────────────────────── primary state     │
│  clinic_links.json  ←──────────────────── FB URL cache      │
│  outreach_sent_log.jsonl  ←────────────── audit trail       │
│  post_log.jsonl  ←─────────────────────── post actions log  │
│                                                              │
│  (all stored at /home/hsuyungfeng/文件/doctor-toolbox-post/) │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│              Infrastructure Dependencies                      │
│                                                              │
│  CloakBrowser (fingerprint=88888, profile=browser_profile/)  │
│  Local LLM Docker  →  localhost:8080/v1/chat/completions     │
│  Facebook (search, pages, Messenger, comments)               │
│  Google (search, Maps)                                       │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `scrape_fb_info.py` | Google→FB discovery, page scraping (Intro/Post/Email/Messenger) | CloakBrowser + JS evaluation |
| `crawl_links.py` | Batch FB + Google Maps URL collection (earlier version) | CloakBrowser |
| `generate_copy_llm.py` | Specialty-aware copy generation via local LLM | urllib → localhost:8080 OpenAI-compat API |
| `generate_generic_copies.py` | Generic fallback copy for clinics without Intro/Post | Same LLM, simpler prompt |
| `send_outreach.py` | Slow-speed Messenger delivery with block detection | CloakBrowser + JS keyboard input |
| `post_clinics.py` | FB comment + Google Maps 5-star review posting | CloakBrowser |
| `run_taichung_20.py` | Orchestrator: syncs cache→CSV then chains stages | subprocess.run chain |
| `setup_session.py` | Manual Facebook login helper (run once) | CloakBrowser interactive |
| `cleanup_not_found.py` | Removes `not_found` rows from CSV | CSV manipulation |
| `outreach_dashboard.html` | Progress visualization | Static HTML, reads CSV via FileReader |

## Recommended Project Structure

```
doctor-toolbox-post/
├── scrape_fb_info.py       # Stage 1: Discovery & FB scraping
├── crawl_links.py          # Stage 1 (legacy): batch link crawler
├── generate_copy_llm.py    # Stage 2: LLM copy generation
├── generate_generic_copies.py  # Stage 2b: fallback for no-data clinics
├── send_outreach.py        # Stage 3a: Messenger delivery
├── post_clinics.py         # Stage 3b: FB comment + Maps review
├── run_taichung_20.py      # Orchestrator: batch pipeline runner
├── setup_session.py        # One-time browser login setup
├── cleanup_not_found.py    # Data maintenance utility
├── outreach_dashboard.html # Local progress dashboard
├── browser_profile/        # CloakBrowser persistent session (git-ignored)
├── assets/                 # Static assets
├── tests/                  # 23 integration tests (live browser)
│   ├── test_fb_*.py        # Facebook-specific tests
│   ├── test_maps*.py       # Google Maps tests
│   └── test_cloakbrowser.py
├── pytest.ini
└── README.md

# External (outside repo, git-excluded):
# /home/hsuyungfeng/文件/doctor-toolbox-post/
#   clinics西醫.csv          ← primary data state + enriched columns
#   clinic_links.json        ← FB URL discovery cache
#   outreach_sent_log.jsonl  ← Messenger audit log
#   post_log.jsonl           ← FB comment / Maps review audit log
#   processed_clinics.json   ← crawl dedup tracker
```

### Structure Rationale

- **Flat scripts:** Single-file pipeline stages are intentional — operator runs them manually or via orchestrator, no daemon/service needed.
- **External data dir:** Prevents accidental git commit of PII (clinic CSV + send logs).
- **browser_profile/ inside repo dir:** CloakBrowser requires absolute path to persistent profile; keeping it here avoids path configuration overhead.

## Architectural Patterns

### Pattern 1: Sequential Pipeline with Idempotent Stages

**What:** Each script reads the CSV, processes only rows missing its output column, writes results back, then stops. Running the same script twice is safe.

**When to use:** Always — this is the core pattern for the whole system.

**Trade-offs:** Simple and crash-safe. No parallelism within a stage. Each restart re-reads the full CSV (acceptable at <5k rows).

**Example:**
```python
# Pattern used in generate_copy_llm.py and send_outreach.py
to_process = [i for i, row in enumerate(csv_rows)
              if (row[idx_intro] or row[idx_post]) and not row[idx_copy]]
```

### Pattern 2: Atomic CSV Write (tmp-rename)

**What:** All CSV saves go to `.tmp` first, then `os.rename()` replaces the live file atomically.

**When to use:** Every CSV save — avoids corrupt state if interrupted mid-write.

**Trade-offs:** Adds one file op per save, but safe against power loss / Ctrl+C. Essential because these scripts run for hours unattended.

**Example:**
```python
temp_csv = CSV_PATH + ".tmp"
with open(temp_csv, 'w', ...) as f: writer.writerows(...)
os.remove(CSV_PATH)
os.rename(temp_csv, CSV_PATH)
```

### Pattern 3: SIGINT-safe Graceful Shutdown

**What:** All long-running scripts register `signal.signal(signal.SIGINT, handle_signal)`, set a global `interrupted` flag, and check it in the main loop. Browser and CSV are closed/saved in `finally:` blocks.

**When to use:** Any script that opens a browser or writes to CSV in a loop.

**Trade-offs:** Adds ~10 lines per script. Without it, Ctrl+C mid-send leaves browser orphaned and CSV unsaved. Worth it.

### Pattern 4: Dual-Layer Caching (CSV + JSON)

**What:** Scraping results are written to both the CSV (primary truth) and `clinic_links.json` (secondary cache keyed by clinic name). On resume, JSON cache fills CSV gaps before re-scraping.

**When to use:** In `scrape_fb_info.py` and `crawl_links.py`.

**Trade-offs:** Dual-write adds complexity. Benefit: faster resume after interruption (skip already-scraped clinics without hitting Facebook again).

### Pattern 5: Block Detection → Immediate Abort

**What:** After each Messenger send, JS evaluates `document.body.innerText` for block keywords (`無法傳送`, `暫時被限制`, etc.). On detection, the script breaks the send loop entirely (not just skips one).

**When to use:** In `send_outreach.py` delivery loop.

**Trade-offs:** Aggressive — one false positive stops the whole run. Conservative but correct: a real block signal means the account is at risk; continuing would worsen it.

## Data Flow

### Full Pipeline Flow

```
clinics西醫.csv (gov open data)
         │
         ▼
[scrape_fb_info.py]
  Google Search site:facebook.com
         │
         ▼  FB_URL, Email, Messenger, Intro, Latest_Post  →  written to CSV + JSON cache
         │
         ▼
[generate_copy_llm.py]
  Build specialty prompt → POST localhost:8080/v1/chat/completions
         │
         ▼  Personalized_Copy (100-150 漢字)  →  written to CSV
         │
         ├─→ [send_outreach.py]
         │     Open m.me/URL in CloakBrowser
         │     JS-type copy into textbox → Enter
         │     Verify no block keywords
         │     Write Messenger_Status + Outreach_Time to CSV
         │     Append to outreach_sent_log.jsonl
         │     Wait 5-10 min random delay
         │
         └─→ [post_clinics.py]
               Search Google Maps → post 5★ review
               Search FB page → post comment
               Append to post_log.jsonl
```

### State Machine: Per-Clinic Row in CSV

```
[raw]
  │  scrape_fb_info.py
  ▼
[FB_URL=found, Intro/Post/Messenger filled]
  │  generate_copy_llm.py
  ▼
[Personalized_Copy=filled]
  │  send_outreach.py
  ▼
[Messenger_Status=sent|dry_run|textbox_not_found]
[Outreach_Time=ISO timestamp]

Dead ends:
  FB_URL=not_found → skip all downstream
  delivery_failed  → abort entire run (account safety)
  login_required   → abort entire run
```

### Key Data Flows

1. **Discovery:** Google search result links → FB URL extracted via regex → stored in CSV + JSON cache
2. **Copy gen:** CSV row (Intro + Latest_Post + 診療科別) → LLM prompt → copy string → written back to CSV
3. **Delivery:** CSV row (Messenger URL + Personalized_Copy) → browser navigation → JS DOM injection → Enter key → block keyword check → JSONL log append

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–500 clinics/run | Current sequential single-threaded: fine |
| 500–2000 clinics | Add SQLite to replace CSV for indexed queries; keep single browser instance |
| 2000–5000 clinics | Multiple FB accounts, each with own CloakBrowser fingerprint + profile; coordinator tracks per-account send counts |
| 5000+ clinics | Separate discovery workers (no rate limit) from delivery workers (rate-limited); message queue between stages |

### Scaling Priorities

1. **First bottleneck:** CSV read/write time and in-memory list scan — replace with SQLite (`SELECT * WHERE Messenger_Status IS NULL`) at 2k+ rows.
2. **Second bottleneck:** Facebook per-account send rate (10–12/hour hard limit) — only parallelizable via multiple accounts, not faster hardware. Each account must maintain its own browser profile + fingerprint.

## Anti-Patterns

### Anti-Pattern 1: Sharing One Browser Instance Across Pipeline Stages

**What people do:** Refactor all stages to share a single long-lived `browser_context` object passed between functions.

**Why it's wrong:** CloakBrowser sessions can become stale or logged out. Each script starting fresh validates session state on launch, and crashes are isolated to one stage.

**Do this instead:** Keep each script as an independent process. `run_taichung_20.py` calls them via `subprocess.run()` — session validation happens naturally at each stage startup.

### Anti-Pattern 2: Global Mutable State for CSV Rows

**What people do:** Use module-level `csv_header` and `csv_rows` lists mutated in-place by every function.

**Why it's wrong:** Already present in the codebase — it works but makes testing hard and causes subtle bugs when functions add columns mid-run.

**Do this instead (Phase 2):** Wrap CSV I/O in a `ClinicStore` class with typed row accessors. Enables unit tests without real files.

### Anti-Pattern 3: Polling for Block Status After Every Send

**What people do:** Add more keywords to the block detection list, trusting JS `innerText` evaluation completely.

**Why it's wrong:** Facebook renders block warnings asynchronously; `time.sleep(5)` after send may not be enough. False negatives let the session continue at risk.

**Do this instead:** After send, also check for network-level signals (HTTP status of Messenger API calls via browser console logs) and implement exponential backoff on consecutive failures, not just abort.

### Anti-Pattern 4: Hardcoded External Data Path

**What people do:** Expand hardcoded paths further as new log files are added.

**Why it's wrong:** `/home/hsuyungfeng/文件/...` is hardcoded in 5+ scripts — changing the operator's home directory or machine requires search-and-replace across all files.

**Do this instead:** Centralize in a `config.py` with `DATA_DIR = Path(os.environ.get("DTP_DATA_DIR", Path.home() / "文件/doctor-toolbox-post"))`. Each script imports `from config import DATA_DIR`.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Facebook pages/Messenger | CloakBrowser page navigation + JS DOM eval | No API — browser simulation only |
| Google Search | CloakBrowser navigate to google.com/search | CAPTCHA triggers require manual resolution |
| Google Maps | CloakBrowser navigate to google.com/maps | Star rating via JS click sequence |
| Local LLM (llama-qwen36) | HTTP POST to localhost:8080/v1/chat/completions via urllib | Must have Docker container running; no retry on failure |
| Taiwan Gov Health CSV | Manual download, placed at external data path | Not fetched at runtime |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Stage 1 → Stage 2 | CSV file (Intro/Latest_Post columns) | JSON cache is supplementary |
| Stage 2 → Stage 3 | CSV file (Personalized_Copy column) | Status tracked in Messenger_Status |
| Any stage → audit | JSONL append | Separate log files per action type |
| Orchestrator → stages | `subprocess.run([sys.executable, script])` | Each stage runs as child process |

## Sources

- Codebase brownfield survey: `scrape_fb_info.py`, `generate_copy_llm.py`, `send_outreach.py`, `post_clinics.py`, `run_taichung_20.py`
- `.planning/PROJECT.md` — architecture decisions table

---
*Architecture research for: Doctor Toolbox Post (醫師工具箱推廣系統)*
*Researched: 2026-06-26*
