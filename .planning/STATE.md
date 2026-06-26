# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-26)

**Core value:** 每一封 Messenger 訊息都要成功送達目標診所，而不觸發 Facebook 的封鎖機制。
**Current focus:** Phase 2 — Reliability Hardening

## Current Position

Phase: 2 of 3 (Reliability Hardening)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-06-26 — Roadmap created; Phase 1 brownfield survey complete; 7 v1 requirements pending across Phase 2 and Phase 3

Progress: [███░░░░░░░] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (Phase 2+ not yet started)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Core Pipeline | — | — | — |

**Recent Trend:** N/A

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: Fixed fingerprint `88888` — do not rotate; fingerprint churn is a stronger bot signal than consistent identity
- [Phase 1]: CSV+JSONL preferred over database for <5k clinics; SQLite upgrade triggers at 5k (DATA-03)
- [Phase 1]: Sequential single-threaded sending; parallelization deferred until adaptive backoff validated on single account

### Pending Todos

- Audit Google Maps review survival rate at 72h (research gap — `post_clinics.py` implemented but not validated)
- Pin CloakBrowser version via `pip show cloakbrowser` before Phase 3 parallelization
- Add `docker stats` monitoring + `--memory` limit for llama-qwen36 OOM prevention

### Blockers/Concerns

- [Research]: Facebook account permanent ban is irreversible — SEND-05 (adaptive backoff) must ship before any throughput expansion
- [Research]: CSV race condition on duplicate sends at scale — must be resolved in Phase 2 before 200-clinic batches

## Session Continuity

Last session: 2026-06-26
Stopped at: Roadmap created; ready to plan Phase 2
Resume file: None
