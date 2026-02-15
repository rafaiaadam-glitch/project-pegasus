# Secrets Management Guidance (v1 baseline)

This document defines the canonical secrets-management approach for Project Pegasus across local development, CI, and hosted deployments.

## Scope

Applies to API, worker, and mobile companion configuration.

## Secret inventory

The following values are **secrets** and must never be committed to git:

- `DATABASE_URL`
- `REDIS_URL`
- `PLC_WRITE_API_TOKEN`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- Any cloud provider credential JSON/private keys
- Any storage access keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)

The following values are typically non-secret configuration:

- `PLC_LLM_PROVIDER`
- `STORAGE_MODE`
- `GCS_BUCKET` / `S3_BUCKET` names
- `PLC_GCP_STT_MODEL`, language defaults, rate-limit knobs

## Rules (all environments)

1. Never hardcode secrets in source code, scripts, or documentation examples.
2. Never store production secrets in `.env` files that are committed.
3. Rotate any secret immediately if exposed in logs, screenshots, or commit history.
4. Scope secrets by environment (dev/staging/prod) and by service (api/worker) where possible.
5. Grant least privilege (minimal DB/storage permissions needed).

## Local development

- Use a local `.env` file that is gitignored.
- Use synthetic/non-production credentials whenever possible.
- Keep local credentials separate from staging/prod credentials.

Recommended workflow:

```bash
cp .env.example .env
# fill local-only secret values
```

## CI (GitHub Actions / equivalent)

- Store secrets in the CI provider secret manager.
- Inject via environment at runtime only for required jobs.
- Mask secret output in logs (default in most CI systems; verify masking is on).
- Do not echo environment variables in build logs.

Minimum CI secret policy:

- PR validation jobs should not require production secrets.
- Deploy jobs must use environment-scoped secrets with restricted write permissions.

## Cloud Run + GCP deployment

Preferred order:

1. Store secrets in Secret Manager.
2. Bind runtime service accounts with only required access.
3. Mount/inject secrets into API and worker separately.
4. Keep API and worker aligned for shared config (`DATABASE_URL`, `REDIS_URL`, storage mode/provider credentials).

Operational controls:

- Rotate write API token and provider keys on a regular cadence (e.g., every 90 days).
- Audit who can read/update secrets.
- Use separate projects or environments for staging vs production when feasible.

## Mobile app considerations

- `EXPO_PUBLIC_*` values are public at build/runtime and must not contain server secrets.
- Do not embed privileged backend tokens in mobile binaries.
- If mobile write auth is enabled, use scoped tokens and server-side revocation strategy.

## Rotation runbook (quick)

1. Create new secret value in secret manager.
2. Update API deployment to use new version.
3. Update worker deployment to use new version.
4. Verify health + one synthetic ingest/transcribe/generate flow.
5. Revoke old secret value.
6. Record rotation date/owner in ops notes.

## Verification checklist

- [ ] No secrets in repository history for recent changes.
- [ ] API and worker both receive required secrets via platform secret manager.
- [ ] CI jobs that need secrets use provider-managed secret storage.
- [ ] Rotation procedure tested at least once in staging.
