# Roadmap: Doctor Toolbox Post (醫師工具箱推廣系統)

## Overview

Three-phase journey. Phase 1 (core pipeline) is already live and validated with the Taichung 20-clinic batch. Phase 2 closes reliability gaps before scale — silent failure paths and race conditions that would cause irreversible harm (account ban, duplicate sends) at 200-clinic scale. Phase 3 adds observability and storage that enable data-driven copy optimization and full Taiwan geographic coverage.

## Phases

- [x] **Phase 1: Core Pipeline** — Full outreach pipeline: discovery → scrape → AI copy → Messenger delivery + Google Maps review, with audit log and web dashboard (Taichung 20-clinic batch validated)
- [ ] **Phase 2: Reliability Hardening** — Close silent-failure paths and race conditions so pipeline runs unattended at 200-clinic scale
- [ ] **Phase 3: Measurement & Scale** — Time-series observability, geographic batch parameterization, and SQLite backend for 5k+ clinic scale

## Phase Details

### Phase 1: Core Pipeline
**Goal**: Full outreach pipeline operational for Taiwan 西醫 clinic promotion via Messenger and Google Maps
**Depends on**: Nothing (delivered)
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04, SCRP-01, SCRP-02, SCRP-03, SCRP-04, COPY-01, COPY-02, COPY-03, COPY-05, SEND-01, SEND-02, SEND-03, SEND-04, POST-01, POST-02, POST-03, AUDIT-01, AUDIT-02, AUDIT-03, DASH-01, DASH-02, ORCH-01, ORCH-02, ERR-01, ERR-02, ERR-03, DATA-01, DATA-02, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Operator can run batch script and have messages delivered to clinic Messenger inboxes without manual intervention
  2. Pipeline detects and halts on Facebook block signals before account damage occurs
  3. Every send attempt (success or failure) is recorded in the JSONL audit log with clinic ID, timestamp, copy, channel, and outcome
  4. Dry-run mode produces screenshots for human verification before live send
  5. Web dashboard shows per-clinic send status, total sent count, pending count, and failed count
**Plans**: Complete

### Phase 2: Reliability Hardening
**Goal**: Pipeline handles all clinic data shapes and rate signals without silent failures or irreversible account harm
**Depends on**: Phase 1
**Requirements**: SCRP-05, COPY-04, SEND-05, ERR-04
**Success Criteria** (what must be TRUE):
  1. Clinics with no Facebook Intro or Latest Post receive a pre-approved generic copy instead of being silently skipped
  2. Pipeline automatically increases delay intervals when rate-limit signals appear, before a full block occurs
  3. Operator receives CLI notification and log entry when session block count exceeds a configurable threshold
  4. A 200-clinic batch completes without manual supervision and without producing duplicate sends
**Plans**: 2 plans

### Phase 3: Measurement & Scale
**Goal**: Observable, queryable system supporting full Taiwan geographic coverage and data-driven copy optimization
**Depends on**: Phase 2
**Requirements**: DASH-03, ORCH-03, DATA-03
**Success Criteria** (what must be TRUE):
  1. Dashboard displays messages-sent-per-day, reply rate, and block rate as time-series charts
  2. Operator can target any geographic batch (Taipei, Kaohsiung) by passing a region parameter to the batch script — no code changes required
  3. System functions correctly after migrating from CSV to SQLite for clinic counts exceeding 5,000 records
**Plans**: TBD

## Progress

**Execution Order:** 1 (complete) → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline | — | Complete | 2026-06-26 |
| 2. Reliability Hardening | 0/TBD | Not started | - |
| 3. Measurement & Scale | 0/TBD | Not started | - |
