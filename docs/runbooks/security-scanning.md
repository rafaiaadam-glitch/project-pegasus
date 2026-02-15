# Security Scanning Runbook

This runbook documents the CI vulnerability scanning gates for Pegasus.

## Scope

The CI pipeline now blocks merges on high/critical findings from:

1. Python dependency audit (`pip-audit`) for backend requirements.
2. JavaScript dependency audit (`npm audit`) for root, backend, and mobile packages.
3. Repository scan (`trivy`) for vulnerabilities, config issues, and secrets.

Workflow location: `.github/workflows/ci.yml` (`security_scan` job).

## What fails the build

- Any `pip-audit` finding in `backend/requirements.txt`.
- Any `npm audit --audit-level=high` finding in root/backend/mobile.
- Any Trivy finding with `HIGH` or `CRITICAL` severity.

## Triage process

1. Reproduce locally (same commands as CI).
2. Patch/upgrade dependencies or container/config issues.
3. If a fix is unavailable:
   - document risk and mitigation,
   - track issue with owner + due date,
   - only then consider scoped exception handling.

## Local reproduction commands

```bash
python -m pip install --upgrade pip
pip install pip-audit
pip-audit -r backend/requirements.txt

npm ci
npm ci --prefix backend
npm ci --prefix mobile
npm audit --audit-level=high
npm audit --prefix backend --audit-level=high
npm audit --prefix mobile --audit-level=high
```

For Trivy (if installed locally):

```bash
trivy fs --severity HIGH,CRITICAL --ignore-unfixed .
```

## Checklist mapping

This runbook and CI gate support `docs/mvp-launch-checklist.md` item:

- "Add dependency and container vulnerability scanning in CI"
