---
phase: 2
slug: reliability-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | pytest.ini |
| **Quick run command** | python3 -m pytest tests/ -k "not integration" |
| **Full suite command** | python3 -m pytest tests/ |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -k "not integration"`
- **After every plan wave:** Run `python3 -m pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | COPY-04 | — | Fallback copies are selected when Intro/Post are missing | unit | `python3 -m pytest tests/test_fallback.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SCRP-05 | — | Row processing handles missing metadata without crashes | unit | `python3 -m pytest tests/test_fallback.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | SEND-05 | — | Backoff delays increase on rate-limit warnings | unit/mock | `python3 -m pytest tests/test_backoff.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | ERR-04 | — | Session block counts trigger warnings and halts | unit/mock | `python3 -m pytest tests/test_backoff.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fallback.py` — test harness for missing metadata fallback routing
- [ ] `tests/test_backoff.py` — unit tests mocking the Facebook warning DOM states and backoff logic
- [ ] `tests/conftest.py` — pytest setup and mock fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Facebook block warning detection in CloakBrowser | SEND-05 | Requires visual browser state and live Facebook page response | Run dry-run mode and inspect generated screenshot under `/tmp/outreach_dryrun.png` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
