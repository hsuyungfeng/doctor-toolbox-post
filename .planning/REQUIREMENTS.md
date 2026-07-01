# Requirements: Doctor Toolbox Post (醫師工具箱推廣系統)

**Defined:** 2026-06-26
**Core Value:** 每一封 Messenger 訊息都要成功送達目標診所，而不觸發 Facebook 的封鎖機制。

## v1 Requirements

### Clinic Discovery (DISC)

- [x] **DISC-01**: System reads Taiwan 西醫 clinic list from `clinics西醫.csv` (government open data) and produces a deduplicated target list
- [x] **DISC-02**: System performs Google Search with `site:facebook.com` queries to resolve each clinic's Facebook page URL
- [x] **DISC-03**: System skips clinics already present in the JSONL audit log (no re-send to same clinic)
- [x] **DISC-04**: System handles clinics not found on Facebook without crashing the pipeline

### Facebook Page Scraping (SCRP)

- [x] **SCRP-01**: System extracts clinic Intro text from the Facebook page
- [x] **SCRP-02**: System extracts the Latest Post text from the Facebook page
- [x] **SCRP-03**: System extracts the clinic's email address from the Facebook page (when present)
- [x] **SCRP-04**: System extracts the direct Messenger link from the Facebook page
- [ ] **SCRP-05**: System handles pages with no Intro or Latest Post (sparse FB data) without failing copy generation — falls back to generic copy

### AI Copy Generation (COPY)

- [x] **COPY-01**: System sends clinic context (Intro, Latest Post, specialty) to local llama-qwen36 at `http://localhost:8080/v1/chat/completions` to generate outreach message
- [x] **COPY-02**: Generated copy is in Traditional Chinese (繁體中文), 100–150 漢字
- [x] **COPY-03**: Prompts include clinic specialty context (pediatrics / ophthalmology / surgery / general) to increase relevance
- [ ] **COPY-04**: When Intro and Latest Post are both empty, system uses a pre-approved generic fallback copy (wires `generate_generic_copies.py` into main pipeline)
- [x] **COPY-05**: System does not call any cloud LLM API; all copy generation runs on the local Docker container

### Messenger Delivery (SEND)

- [x] **SEND-01**: System sends Messenger message via CloakBrowser with fingerprint `88888`
- [x] **SEND-02**: System applies random 5–10 minute delay between consecutive messages
- [x] **SEND-03**: System detects block signals ("無法傳送", "暫時被限制") and shuts down gracefully before the next send attempt
- [x] **SEND-04**: Dry-run mode renders copy and captures a screenshot without submitting the message, for human verification
- [ ] **SEND-05**: System applies adaptive backoff (increasing delay) when rate-limit signals are detected, before a full block occurs

### Multi-Channel Posting (POST)

- [x] **POST-01**: System can post a Facebook comment on a clinic's existing post via `post_clinics.py`
- [x] **POST-02**: System can post a Google Maps 5-star review for a clinic via `post_clinics.py`
- [x] **POST-03**: Both comment and review actions are recorded in the JSONL audit log

### Audit & Deduplication (AUDIT)

- [x] **AUDIT-01**: Every send attempt (success or failure) is appended to a JSONL audit log with clinic ID, timestamp, copy text, channel, and outcome
- [x] **AUDIT-02**: Pipeline checks audit log before each send to prevent duplicate outreach to the same clinic
- [x] **AUDIT-03**: Audit log is stored at the external path outside the git repo to prevent committing clinic PII

### Dashboard & Observability (DASH)

- [x] **DASH-01**: Web dashboard (`outreach_dashboard.html`) reads CSV and displays per-clinic send status
- [x] **DASH-02**: Dashboard shows total sent count, pending count, and blocked/failed count
- [ ] **DASH-03**: Dashboard displays time-series metrics: messages sent per day, reply rate, block rate

### Orchestration & Batch Execution (ORCH)

- [x] **ORCH-01**: Orchestration script (`run_taichung_20.py`) runs discovery → scrape → generate → send for a named batch (Taichung top-20)
- [x] **ORCH-02**: Operator can specify dry-run flag at batch invocation without modifying source code
- [ ] **ORCH-03**: Batch script accepts a CSV slice / region parameter to run geographic batches (e.g., Taipei, Kaohsiung) without code changes

### Error Handling & Resilience (ERR)

- [x] **ERR-01**: Any single clinic failure (scrape error, LLM timeout, send error) is logged and skipped without aborting the entire batch
- [x] **ERR-02**: LLM unavailability (Docker container down) surfaces a clear error message rather than sending empty or malformed copy
- [x] **ERR-03**: CloakBrowser session loss is detected and reported; pipeline does not silently skip clinics
- [ ] **ERR-04**: Operator is notified (CLI output + log entry) when the total block count in a session exceeds a configurable threshold

### Data & Storage (DATA)

- [x] **DATA-01**: Clinic state is tracked in CSV + JSONL (no database required for <5k clinics)
- [x] **DATA-02**: All external data files live outside the git repo at `/home/hsuyungfeng/文件/doctor-toolbox-post/`
- [ ] **DATA-03**: System supports migration to SQLite backend when clinic count exceeds 5k, replacing CSV-based deduplication and status queries

### Testing (TEST)

- [x] **TEST-01**: Integration test suite (`tests/`) covers discovery, scraping, copy generation, and delivery flows
- [x] **TEST-02**: Tests run against real Facebook/Google (no mocking); requires live CloakBrowser session
- [x] **TEST-03**: Dry-run mode serves as pre-flight acceptance check before each live batch

## v2 Requirements

### Parallel Throughput (PARA)

- **PARA-01**: System supports multiple simultaneous CloakBrowser instances (different FB accounts) with per-account rate enforcement
- **PARA-02**: Parallelization respects per-account message rate (max 10–12/hour); does not simply multiply machine throughput

### A/B Copy Testing (AB)

- **AB-01**: System assigns each generated copy to a named variant (e.g., "specialty-hook-v1", "generic-v1")
- **AB-02**: System tracks per-variant delivery count, reply rate, and block rate in SQLite
- **AB-03**: Dashboard surfaces per-variant conversion comparison

### Geographic Expansion (GEO)

- **GEO-01**: Pipeline can target Taipei (台北市) and Kaohsiung (高雄市) clinic batches using same code with different CSV slices
- **GEO-02**: Batch configuration (region name, CSV filter, target count) is driven by a config file, not hardcoded values

## Out of Scope

| Feature | Reason |
|---------|--------|
| WhatsApp / LINE / SMS outreach | Multiplies channel compliance complexity; Messenger + Google Maps validated as sufficient reach vector for Taiwan clinics |
| Cloud LLM (OpenAI / Claude API) | Clinic data (names, posts, specialties) must not leave the machine; API cost at 10k scale is prohibitive; local llama-qwen36 is sufficient for 100–150 漢字 copy |
| OCR-based CAPTCHA solving | Escalates ToS violation severity; manual CAPTCHA intervention keeps risk classification low |
| Rotating browser fingerprints | Facebook ML flags fingerprint churn as a stronger bot signal than a consistent identity; fixed `88888` is the validated approach |
| SaaS / multi-tenant operation | Changes legal liability from personal use to operating an outreach platform; fundamentally different risk and compliance profile |
| Real-time reply inbox | Inbound replies arrive natively in Facebook; adding an inbox integration creates a second surface with no proportional value |
| GDPR / Taiwan PDPA formal compliance audit | System is single-operator promotional use; clinic data is public Facebook page information |
| HIS system integration | Belongs in the Doctor Toolbox product itself, not in this outreach pipeline |
| WhatsApp Business API | See multi-channel exclusion above |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 1 | Complete |
| DISC-02 | Phase 1 | Complete |
| DISC-03 | Phase 1 | Complete |
| DISC-04 | Phase 1 | Complete |
| SCRP-01 | Phase 1 | Complete |
| SCRP-02 | Phase 1 | Complete |
| SCRP-03 | Phase 1 | Complete |
| SCRP-04 | Phase 1 | Complete |
| SCRP-05 | Phase 2 | Pending |
| COPY-01 | Phase 1 | Complete |
| COPY-02 | Phase 1 | Complete |
| COPY-03 | Phase 1 | Complete |
| COPY-04 | Phase 2 | Pending |
| COPY-05 | Phase 1 | Complete |
| SEND-01 | Phase 1 | Complete |
| SEND-02 | Phase 1 | Complete |
| SEND-03 | Phase 1 | Complete |
| SEND-04 | Phase 1 | Complete |
| SEND-05 | Phase 2 | Pending |
| POST-01 | Phase 1 | Complete |
| POST-02 | Phase 1 | Complete |
| POST-03 | Phase 1 | Complete |
| AUDIT-01 | Phase 1 | Complete |
| AUDIT-02 | Phase 1 | Complete |
| AUDIT-03 | Phase 1 | Complete |
| DASH-01 | Phase 1 | Complete |
| DASH-02 | Phase 1 | Complete |
| DASH-03 | Phase 3 | Pending |
| ORCH-01 | Phase 1 | Complete |
| ORCH-02 | Phase 1 | Complete |
| ORCH-03 | Phase 3 | Complete |
| ERR-01 | Phase 1 | Complete |
| ERR-02 | Phase 1 | Complete |
| ERR-03 | Phase 1 | Complete |
| ERR-04 | Phase 2 | Complete |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 3 | Complete |
| TEST-01 | Phase 1 | Complete |
| TEST-02 | Phase 1 | Complete |
| TEST-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 41 total
- Phase 1 complete: 34
- Phase 2 complete: 4 (SCRP-05, COPY-04, SEND-05, ERR-04)
- Phase 3 complete: 2 (ORCH-03, DATA-03)
- Phase 3 pending: 1 (DASH-03)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-27 after Phase 3 SQLite database migration and A/B copywriting implementation*
