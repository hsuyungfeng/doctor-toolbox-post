# Doctor Toolbox Post (醫師工具箱推廣系統)

## What This Is

An automated outreach pipeline that discovers Taiwan western-medicine (西醫) clinics on Facebook, scrapes their page context, generates AI-personalized Messenger copy via a local LLM, and delivers it at human-paced speeds to avoid Facebook's anti-spam detection. The system promotes **Doctor Toolbox** — an AI SOAP medical-record tool (voice transcription + LINE OA integration, NT$1,000/month) — targeting clinic owners directly through Facebook Messenger and Google Maps reviews.

## Core Value

每一封 Messenger 訊息都要成功送達目標診所，而不觸發 Facebook 的封鎖機制。
*(Every Messenger message must reach its target clinic without triggering Facebook's block detection.)*

## Requirements

### Validated

- ✓ Browser session persistence via CloakBrowser fixed fingerprint (`88888`) — Phase 1
- ✓ Google Search → Facebook page discovery with `site:facebook.com` queries — Phase 1
- ✓ Scrape clinic Intro + Latest_Post + Email + Messenger link from FB pages — Phase 1
- ✓ Local LLM copy generation (llama-qwen36, specialty-aware prompts, 100–150 漢字) — Phase 1
- ✓ Slow-speed Messenger delivery with 5–10 min random delays + failure keyword detection — Phase 1
- ✓ Graceful shutdown on "無法傳送" / "暫時被限制" detection — Phase 1
- ✓ Dry-run mode with screenshot verification before live sending — Phase 1
- ✓ Facebook comment + Google Maps 5-star review posting (`post_clinics.py`) — Phase 1
- ✓ JSONL audit log for all sent messages + post actions — Phase 1
- ✓ Web dashboard (`outreach_dashboard.html`) for CSV-based progress tracking — Phase 1
- ✓ Orchestration script for Taichung top-20 batch (`run_taichung_20.py`) — Phase 1

### Active

- [ ] Adaptive delay backoff when rate-limit signals detected (currently fixed random range)
- [ ] Parallel browser instances for higher throughput while maintaining per-account safety
- [ ] A/B copy variant testing with per-variant conversion tracking
- [ ] SQL or SQLite backend to replace CSV for queries at 10k+ clinic scale
- [ ] Time-series metrics in dashboard (sent/day, reply rate, block rate)
- [ ] Generic fallback copy for clinics with no Intro/Post data (partially done in `generate_generic_copies.py`, needs integration)

### Out of Scope

- WhatsApp / LINE / SMS channels — Facebook Messenger + Google Maps is the validated reach vector for Taiwan clinics; adding channels multiplies compliance complexity
- GDPR / Taiwan PDPA formal compliance audit — system is operated by owner for own promotional use; clinic data is public FB page info
- SaaS / multi-tenant operation — single-operator tool, not a platform product
- OCR-based CAPTCHA solving — manual intervention is intentional to keep risk low and avoid ToS violation escalation
- HIS system integration within this repo — that belongs in the Doctor Toolbox product itself

## Context

- **Product being promoted**: Doctor Toolbox (醫師工具箱) — AI SOAP generator, voice-to-record, LINE OA bridge, NT$1,000/month, free trial at https://doctor-toolbox.com/ai-soap-generator
- **Target market**: Taiwan 西醫 clinics; Taichung (台中市) prioritized as initial test region
- **Data source**: `clinics西醫.csv` from Taiwan government open health data; stored externally at `/home/hsuyungfeng/文件/doctor-toolbox-post/` (outside repo, excluded from git)
- **LLM**: Local `llama-qwen36` via Docker at `http://localhost:8080/v1/chat/completions` — chosen for privacy and zero API cost; 128k context window
- **Browser automation**: CloakBrowser (not Playwright) — provides anti-detection fingerprinting and persistent profile state; all scripts use `--fingerprint=88888`
- **Anti-ban strategy**: fixed fingerprint across sessions + random 5–10 min inter-message delays + immediate shutdown on block signal; current throughput ~8–10 messages/hour safely
- **Testing**: 23 integration tests in `tests/` that run against real Facebook/Google (no mocking); requires live browser session

## Constraints

- **Platform**: CloakBrowser only — Playwright/Selenium would trigger Facebook's bot detection
- **LLM**: Local llama-qwen36 Docker container must be running on `localhost:8080` — no fallback to cloud LLM (privacy requirement)
- **Data storage**: External CSV path (`/home/hsuyungfeng/文件/...`) hardcoded in scripts — changing requires updating all file path references
- **Throughput**: Max ~10–12 Messenger sends/hour without triggering Facebook limits — parallelization must respect per-account rate, not just per-machine
- **Language**: All copy output in Traditional Chinese (繁體中文); all code comments in Chinese
- **Python 3**: No Node.js runtime; CloakBrowser SDK is Python-only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CSV + JSONL over database | Human-readable, git-versionable, no infra setup; adequate for <5k clinics | ✓ Good |
| Local LLM (llama-qwen36) over OpenAI API | Zero cost per message, privacy (clinic data stays local), offline-capable | ✓ Good |
| Fixed fingerprint `88888` for all sessions | Consistent browser identity reduces fingerprint-change detection signals | ✓ Good |
| Random 5–10 min delays between messages | Facebook's per-account block threshold observed at <1 min intervals | ✓ Good |
| Specialty-aware LLM prompts (pediatrics/ophthalmology/surgery) | Generic copy had lower engagement; specialty hook increases relevance | — Pending validation |
| Sequential single-threaded sending | Safest for account health; parallelization deferred until delay strategy matures | ✓ Good |
| External data path (outside repo) | Prevents accidental commit of clinic PII + send logs to git | ✓ Good |

---
*Last updated: 2026-06-26 after initial research phase — brownfield survey of existing codebase*
