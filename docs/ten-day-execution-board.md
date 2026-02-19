# 10-Day Execution Board (17/36 → 22/36)

This board converts the **19 unchecked launch items** into an execution plan that reaches the next milestone at **22/36** without adding non-goal scope.

Primary product guardrail during execution:
**Course → Preset → Record/Upload → Auto-process → Review/Export**.

## Milestone target (next 5 closures)

Choose these five checklist items first (highest leverage, lowest scope, aligned to `docs/next-steps.md`):

1. **Add alerting for sustained failure spikes and queue backlogs**
2. **Add dashboards for per-stage pipeline timings**
3. **Add backup/restore procedure for Postgres and object storage** (close by adding staging drill evidence)
4. **Add migration rollback guidance for production incidents** (close by adding staging rollback drill evidence)
5. **Add secrets management guidance for each deploy target**

Rationale:
- Matches stated priority order: observability first, then reliability drills, then security baseline.
- Produces operational evidence quickly without introducing new UX architecture.

---

## Definition of evidence (required per checklist item)

For each item, include exactly three proof lines:

- **Endpoint/UI:** what exists.
- **Test:** one automated test, script, or exact command.
- **Proof:** screenshot, dashboard link, or terminal output snippet.

Rule: if it cannot be proven in <2 minutes by an on-call reviewer, it is not done.

---

## 10-day board

| Day | Owner | Focus | Deliverable | Evidence expected |
|---|---|---|---|---|
| 1 | Agent | Alerting policy draft | Alert policy config for queue backlog + failure spike thresholds | Policy JSON/YAML + dry-run output |
| 2 | Agent | Alert route verification | End-to-end alert fires to route (email/webhook/on-call) | Trigger command + received alert proof |
| 3 | Agent | Pipeline timing dashboard | Dashboard for ingest/transcribe/generate/export durations | Dashboard URL + screenshot |
| 4 | Agent | Queue and retry dashboard overlays | Queue depth, retries, failure-rate panels in same dashboard | Panel screenshot + query definitions |
| 5 | You + Agent | Backup/restore drill run | Staging restore drill executed for Postgres + storage | Run log (commands + timings + integrity checks) |
| 6 | You + Agent | Rollback drill run | Staging migration rollback executed and validated | Rollback commands + before/after schema check |
| 7 | Agent | Secrets guide skeleton | Canonical secrets-management doc per deploy target | New doc with env var matrix + rotation notes |
| 8 | You + Agent | Secrets guide hardening | Finalized guidance for local/staging/prod + break-glass notes | Reviewed doc + checklist cross-link |
| 9 | Agent | Checklist evidence pass | Update launch checklist evidence map with links/artifacts | PR diff showing added evidence lines |
| 10 | You | Go/no-go rehearsal | 30-minute dry-run: identify failing stage in <5 minutes | Incident drill notes + timestamps |

---

## Mapping for all 19 unchecked items

Use this as the execution backlog after the first 5 closures.

### Data & storage reliability

1. **Add backup/restore procedure for Postgres and object storage**
   - Endpoint/UI: runbook + scripted staging drill entry.
   - Test: `scripts/verify-backup-restore.sh` (or exact documented command set).
   - Proof: dated drill log with integrity verification.

2. **Add migration rollback guidance for production incidents**
   - Endpoint/UI: rollback runbook with decision tree.
   - Test: staging rollback execution against latest migration.
   - Proof: before/after schema + successful app health check.

### Mobile product completion (MVP UX)

3. **Replace scaffold-only flow with production navigation and error states**
4. **Add upload/record progress indicators and retry UX**
5. **Add per-lecture status timeline and stage-level failure messaging**
6. **Add artifact review screens tuned for revision workflows**
7. **Add export download/open/share affordances**

Evidence format for each mobile item:
- Endpoint/UI: screen path + navigation route.
- Test: one e2e or component test command.
- Proof: screenshot/video of the specific flow.

### Observability & SLOs

8. **Add alerting for sustained failure spikes and queue backlogs**
9. **Add dashboards for per-stage pipeline timings**

Evidence format:
- Endpoint/UI: monitoring config + dashboard/policy identifiers.
- Test: synthetic failure + queue saturation trigger.
- Proof: fired alert + dashboard panel screenshot.

### Security, privacy, compliance baseline

10. **Add secrets management guidance for each deploy target**
11. **Add dependency and container vulnerability scanning in CI**

Evidence format:
- Endpoint/UI: docs section and CI workflow file.
- Test: CI run for dependency + container scan.
- Proof: passing/blocked scan report artifact.

### Deployment readiness

12. **Publish one canonical deployment guide for API + worker + storage**
13. **Add health/readiness checks to platform configs with sane thresholds**
14. **Add staging environment parity checklist**
15. **Add release checklist with rollback procedure**

Evidence format:
- Endpoint/UI: docs + config files.
- Test: deploy to staging using canonical guide.
- Proof: readiness endpoints green + rollback rehearsal log.

### v1 launch gating checklist

16. **Critical-path integration tests pass (ingest → transcribe → generate → export)**
17. **API and worker deploy from main with reproducible config**
18. **At least one mobile build (iOS/Android) validated end-to-end against staging**
19. **Monitoring + alerting verified by synthetic canary jobs**

Evidence format:
- Endpoint/UI: CI/CD pipeline + build artifacts.
- Test: one command per gate.
- Proof: CI run URL / build ID / canary pass-fail log.

---

## Exit criteria for this board

Board is successful when all are true:
- Checklist rises from **17/36 to at least 22/36**.
- All five selected items include evidence lines in checklist or linked runbooks.
- On-call can identify failing stage within 5 minutes using dashboard + alerts.
- No changes introduce chat-first or non-MVP scope.
