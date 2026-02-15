# PLC 2-Week Execution Plan (36% → ~60%)

This plan is designed to move launch checklist completion from **13/36 (36%)** to at least **22/36 (61%)** in 10 working days by prioritizing high-leverage, unblock-heavy work first.

Source baseline: `docs/mvp-launch-checklist.md`.

---

## 0) Target math and completion criteria

- **Starting point:** 13/36 complete
- **Target point (~60%):** 22/36 complete (61.1%)
- **Net new items to close in 2 weeks:** **9 checklist items**

### Checklist items targeted for closure (9)

1. Data reliability: backup/restore procedure + staging restore drill evidence
2. Data reliability: migration rollback guidance + staging rollback drill evidence
3. Observability: define SLOs
4. Observability: emit metrics for queue depth/job latency/failure/retries
5. Observability: alerting for sustained failures/backlogs
6. Observability: dashboards for per-stage timing
7. Security: secrets management guidance per deploy target
8. Security: dependency/container vulnerability scanning in CI
9. Launch gate: monitoring + alerting verified by synthetic canary jobs

> Why these 9: they are operationally critical, mostly backend/ops-owned, and can be completed without blocking on full mobile UX completion.

---

## 1) Owners and responsibilities

Use DRI (directly responsible individual) per stream. If specific names are available, replace role labels.

- **EM / PM (Owner: Delivery Lead)**
  - Daily sequencing, unblock decisions, checklist status updates.
- **Backend Lead (Owner: API/Worker Engineer)**
  - Metrics instrumentation, canary jobs, endpoint-level operational hooks.
- **Platform/SRE Lead (Owner: DevOps Engineer)**
  - Dashboards, alerts, drill execution, release safety evidence.
- **Security Lead (Owner: Security Engineer)**
  - Secrets policy + CI vulnerability scanning implementation.
- **QA Lead (Owner: Test Engineer)**
  - Verification scripts/evidence, sign-off checklist per item.

---

## 2) Exact task order (10 working days)

## Week 1

### Day 1 (Mon) — Planning lock + SLO definitions

1. **EM/PM:** Freeze scope to the 9 target items listed above.
2. **Platform/SRE + Backend:** Draft and approve SLOs:
   - ingest success rate
   - generation success rate
   - p95 end-to-end processing time
3. **QA:** Create evidence template (screenshots/logs/command outputs) for “definition-of-done proof”.

**Exit criteria:** SLO doc merged; all 9 items have DRI + due date.

---

### Day 2 (Tue) — Metrics instrumentation foundation

4. **Backend:** Instrument metrics in API/worker for:
   - queue depth
   - job latency per stage
   - failure rate
   - retry counts
5. **QA:** Validate metric emission in local/staging smoke run.

**Exit criteria:** Metrics visible in chosen backend (Cloud Monitoring/Prometheus) with stable labels.

---

### Day 3 (Wed) — Dashboard implementation

6. **Platform/SRE:** Build dashboard views:
   - pipeline stage durations
   - throughput + failures
   - retry trends + queue backlog
7. **EM/PM:** Review for on-call usability (<5 min to identify failing stage).

**Exit criteria:** Dashboard links published in runbook.

---

### Day 4 (Thu) — Alerting implementation

8. **Platform/SRE:** Add alerts:
   - sustained generation failure spike
   - queue backlog threshold breach
   - p95 processing time regression
9. **QA:** Trigger synthetic failure/backlog to verify alert firing + routing.

**Exit criteria:** Alert policies active; test notifications captured.

---

### Day 5 (Fri) — Data reliability drills

10. **Platform/SRE:** Execute staging backup/restore drill and capture evidence.
11. **Backend + Platform/SRE:** Execute migration rollback drill and capture evidence.
12. **QA:** Validate recovery timing and data integrity post-drill.

**Exit criteria:** Both runbooks updated with dated drill evidence and timings.

---

## Week 2

### Day 6 (Mon) — Secrets management hardening

13. **Security + Platform/SRE:** Publish secrets management guidance per deploy target (Cloud Run, CI, local dev).
14. **Backend:** Remove any residual implicit secret assumptions in startup docs/config.

**Exit criteria:** One canonical secrets doc linked from deployment guide/checklist.

---

### Day 7 (Tue) — CI vulnerability scanning

15. **Security:** Add dependency scanning (e.g., pip/npm audit or SCA tool) in CI.
16. **Security + Platform/SRE:** Add container image vulnerability scanning gate.
17. **QA:** Verify CI fails on intentionally vulnerable test case (or policy threshold breach).

**Exit criteria:** CI checks mandatory on main PR path.

---

### Day 8 (Wed) — Synthetic canary jobs

18. **Backend:** Implement scheduled synthetic canary job(s) for ingest→transcribe→generate health checks.
19. **Platform/SRE:** Wire canary outcomes into dashboards + alerts.

**Exit criteria:** Canary runs automatically and produces pass/fail telemetry.

---

### Day 9 (Thu) — Launch gate verification + evidence pass

20. **QA:** Run verification pass for all 9 target items.
21. **EM/PM:** Update checklist checkboxes and evidence map links.
22. **All DRIs:** Fix any gaps detected by QA.

**Exit criteria:** 9/9 targeted items demonstrably closed.

---

### Day 10 (Fri) — Buffer + risk burn-down

23. **Team:** Use buffer for spillover/high-risk fixes from Days 6–9.
24. **EM/PM:** Publish end-of-sprint readout:
   - before/after completion %
   - unresolved risks
   - next 2-week focus (mobile UX + critical-path integration tests)

**Exit criteria:** Confirmed movement to **≥22/36 complete (~61%)**.

---

## 3) Deliverables by owner

### EM / PM
- Daily status board with 9 targeted items and RAG state
- Checklist updates in `docs/mvp-launch-checklist.md`
- End-of-sprint progress report

### Backend Lead
- Metrics instrumentation PR(s)
- Synthetic canary job implementation
- Any supporting operational hooks/tests

### Platform/SRE Lead
- Dashboards + alert policies
- Backup/restore + rollback drill execution records
- Monitoring integration for canary jobs

### Security Lead
- Secrets management guidance
- CI vulnerability scanning enforcement

### QA Lead
- Evidence pack for each closed checklist item
- Verification commands and pass/fail report

---

## 4) Daily operating cadence

- **09:00–09:15:** Standup (blockers + dependency handoffs)
- **13:00:** Async checkpoint update in shared channel
- **16:30–17:00:** DRI verification + checklist evidence update
- **Friday:** 30-min risk review against target 22/36

---

## 5) Risk controls

- **Risk:** Observability work slips into platform complexity.
  - **Control:** Limit v1 to essential metrics/alerts listed in this plan.
- **Risk:** Security scan introduces noisy CI failures.
  - **Control:** Set severity threshold and one-time baseline waiver process.
- **Risk:** Drill evidence incomplete/unreproducible.
  - **Control:** QA-owned evidence template required before marking complete.
- **Risk:** Canary flaky due to external providers.
  - **Control:** Add retry + failure classification and alert on sustained failure, not single run.

---

## 6) Definition of success at end of 2 weeks

- Checklist completion moved from **36% to at least 61% (22/36)**.
- All 9 target items are closed with linked evidence.
- On-call can identify failing stage quickly via dashboards + alerts.
- Next cycle is free to focus on **mobile UX completion + final integration gates**.
