# Feature Research

**Domain:** Automated B2B Outreach Pipeline (Facebook Messenger + Google Maps)
**Researched:** 2026-06-26
**Confidence:** HIGH (brownfield project — features derived from existing codebase + PROJECT.md)

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Clinic discovery from CSV | Without a target list, nothing works | LOW | `clinics西醫.csv` from Taiwan gov open data; already implemented |
| Facebook page scraping | Copy must reference clinic-specific data to avoid spam detection | MEDIUM | Scrapes Intro + Latest_Post + Email + Messenger link; implemented |
| AI copy generation | Manual copy at scale is impossible | MEDIUM | llama-qwen36 local Docker; specialty-aware prompts; 100–150 漢字; implemented |
| Messenger delivery | Core delivery channel | HIGH | CloakBrowser only; random 5–10 min delays; implemented |
| Block signal detection + graceful shutdown | Account survival is the #1 constraint | MEDIUM | Detects "無法傳送" / "暫時被限制"; implemented |
| Dry-run mode with screenshot verification | Must validate targeting before spending account health | LOW | Pre-flight check before live sending; implemented |
| JSONL audit log | Deduplication + post-mortem analysis | LOW | Records all send attempts + outcomes; implemented |
| Deduplication (don't re-send to same clinic) | Spamming the same clinic burns reputation and triggers blocks | LOW | CSV + JSONL state; implemented |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Specialty-aware LLM prompts | Pediatrics/ophthalmology/surgery clinics get hooks relevant to their workflow — higher open/reply rate | MEDIUM | Pending conversion validation; already built, needs A/B data |
| Fixed CloakBrowser fingerprint (`88888`) | Consistent digital identity across sessions reduces detection risk vs. rotating fingerprints | LOW | Key architectural decision; validated as safe |
| Google Maps 5-star review posting | Second touch-point reinforcing social proof outside Messenger | MEDIUM | `post_clinics.py`; implemented; different trust signal than DM |
| Facebook comment posting | Third touch-point on clinic's own posts | MEDIUM | Adds visibility to existing audience before DM |
| Local LLM (zero API cost, offline, private) | Clinic data never leaves the machine; scales to 10k+ clinics at zero marginal cost | LOW | llama-qwen36 at localhost:8080; implemented |
| Adaptive delay backoff | Extends account lifespan when rate-limit signals appear before full block | MEDIUM | Not yet implemented; currently fixed 5–10 min range |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-channel outreach (LINE/WhatsApp/SMS) | More reach vectors = more replies | Multiplies ToS compliance complexity, each channel has different block mechanics, maintenance burden triples | Stay on Messenger + Maps; validate conversion rate before expanding |
| Cloud LLM (OpenAI/Claude API) | Faster, better quality copy | Clinic data (names, specialties, post content) leaves the machine; API cost at 10k scale; offline-incapable | Local llama-qwen36 already sufficient for 100–150 漢字 copy |
| OCR-based CAPTCHA solving | Fully unattended operation | Escalates ToS violation severity; Facebook specifically uses CAPTCHA as human verification gate | Manual intervention for CAPTCHAs; keeps risk classification low |
| Rotating fingerprints per session | Seems like better anonymization | Facebook's ML flags fingerprint churn as bot signal more than a consistent fingerprint | Fixed `88888` across all sessions |
| SaaS / multi-tenant mode | Monetize the tooling | Changes legal liability from personal use to operating an outreach platform; fundamentally different risk profile | Single-operator tool only |
| Real-time reply inbox | Manage inbound interest in-app | Out of scope; clinic replies come to the Facebook account natively; adding inbox integration creates a second surface to maintain | Handle replies manually in Facebook |

## Feature Dependencies

```
[Clinic CSV Data]
    └──requires──> [Discovery / Page Lookup]
                       └──requires──> [FB Page Scraper]
                                          └──requires──> [AI Copy Generator]
                                                             └──requires──> [Messenger Delivery]

[Block Signal Detector] ──guards──> [Messenger Delivery]
[Dry-Run Mode] ──validates──> [Messenger Delivery]
[JSONL Audit Log] ──deduplicates──> [Messenger Delivery]

[Adaptive Delay Backoff] ──enhances──> [Messenger Delivery]
[A/B Copy Testing] ──enhances──> [AI Copy Generator]

[SQLite Backend] ──replaces──> [CSV + JSONL State]
    └──enables──> [Time-Series Dashboard Metrics]
    └──enables──> [10k+ Clinic Scale Queries]

[Generic Fallback Copy] ──extends──> [AI Copy Generator]
    └──required when──> [No Intro/Post Data Available]

[Parallel Browser Instances] ──conflicts with──> [Per-Account Rate Limits]
    └──requires──> [Adaptive Delay Backoff] (to be safe)
```

### Dependency Notes

- **Messenger Delivery requires Block Signal Detector:** Sending without block detection risks permanent account suspension — non-negotiable guard.
- **Adaptive Delay Backoff requires block signal detector:** Backoff only meaningful if we can detect the signal to back off from.
- **Parallel Browser Instances requires Adaptive Backoff first:** Running parallel accounts without mature delay strategy violates per-account rate constraint; defer until backoff is validated.
- **SQLite Backend enables Time-Series Metrics:** CSV cannot efficiently query `sent/day` or `reply_rate` across 10k records; SQLite is the unlock.
- **Generic Fallback Copy must integrate before scaling:** At 10k clinics, a significant fraction will have empty Intro/Post; unhandled case means silent failures.
- **A/B Copy Testing requires SQLite:** CSV cannot reliably track per-variant conversion; needs structured queries.

## MVP Definition

### Already Launched (v1 — Phase 1 Complete)

- [x] Clinic discovery from government CSV
- [x] FB page scraping (Intro, Latest_Post, Email, Messenger link)
- [x] Local LLM copy generation with specialty awareness
- [x] Messenger delivery with 5–10 min delays
- [x] Block signal detection + graceful shutdown
- [x] Dry-run mode + screenshot verification
- [x] Google Maps review + Facebook comment posting
- [x] JSONL audit log
- [x] Web dashboard (CSV-backed)
- [x] Taichung top-20 batch orchestration

### Add After Validation (v1.x — Active Phase)

- [ ] **Generic fallback copy integration** — blocks scaling to clinics with sparse FB data; `generate_generic_copies.py` exists but not wired in
- [ ] **Adaptive delay backoff** — prerequisite for any parallelization; implement before expanding throughput
- [ ] **Time-series dashboard metrics** (sent/day, reply rate, block rate) — needed to measure specialty-prompt A/B results
- [ ] **SQLite backend** — trigger: when CSV queries exceed 2–3 seconds or clinic count crosses 5k

### Future Consideration (v2+)

- [ ] **Parallel browser instances** — only safe after adaptive backoff is proven; doubles throughput but doubles account risk if wrong
- [ ] **A/B copy variant testing with conversion tracking** — requires SQLite + time-series metrics as foundation; high value once baseline conversion rate is known
- [ ] **Geographic expansion beyond Taichung** — Taipei, Kaohsiung batches; same pipeline, different CSV slices

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Generic fallback copy (integrate existing) | HIGH | LOW (code exists, needs wiring) | P1 |
| Adaptive delay backoff | HIGH | MEDIUM | P1 |
| Time-series dashboard metrics | MEDIUM | MEDIUM | P2 |
| SQLite backend | MEDIUM | MEDIUM | P2 |
| A/B copy variant testing | HIGH | HIGH (needs SQLite first) | P2 |
| Parallel browser instances | MEDIUM | HIGH (needs backoff first) | P3 |
| Geographic batch expansion | MEDIUM | LOW (CSV slice + config) | P2 |

**Priority key:**
- P1: Must have for reliable operation at current scale
- P2: Should have, adds measurement and scale capacity
- P3: Nice to have, future throughput optimization

## Competitor Feature Analysis

*No direct competitors identified — this is a bespoke single-operator outreach tool for a specific product (Doctor Toolbox) in a specific market (Taiwan 西醫 clinics). Generic outreach SaaS tools (Apollo, Lemlist, etc.) are inapplicable because:*
- *They don't support CloakBrowser / anti-fingerprint requirements*
- *They target email, not Facebook Messenger*
- *They can't use local LLM for copy generation*
- *They don't integrate Taiwan government clinic CSV data*

| Feature | Generic SaaS (Apollo/Lemlist) | Our Approach |
|---------|-------------------------------|--------------|
| Copy personalization | Template variables, AI via cloud API | Local LLM with clinic specialty context; zero API cost; private |
| Delivery channel | Email primarily | Facebook Messenger + Google Maps reviews |
| Anti-detection | None (email doesn't need it) | CloakBrowser fixed fingerprint + human-paced delays |
| Data source | CRM / CSV upload | Taiwan gov open data CSV + FB page scraping |
| Scale | Thousands/day | 8–10/hour (intentional; account health > throughput) |
| Cost model | $50–500/month SaaS | Zero marginal cost (local LLM + owned FB account) |

## Sources

- `PROJECT.md` — authoritative requirements and validated decisions
- Existing codebase (Phase 1 brownfield survey via git log)
- Facebook anti-spam behavior: observed empirically (block threshold at <1 min intervals)
- CloakBrowser fingerprint behavior: validated in production (`88888` stable)

---
*Feature research for: Doctor Toolbox Post (醫師工具箱推廣系統)*
*Researched: 2026-06-26*
