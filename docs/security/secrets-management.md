# Secrets Management Guide (by deploy target)

This is the canonical reference for how Project Pegasus stores, rotates, and audits secrets.

## Scope

Applies to:
- API service (`backend.app`)
- Worker service (`backend.worker`)
- CI workflows (`.github/workflows/*.yml`)
- Local development

## Required secret classes

At minimum, treat these as secrets:
- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- Storage credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, service-account JSON)
- `PLC_WRITE_API_TOKEN`

## Core rules

1. Never commit plaintext secrets to Git.
2. Never place secrets in `.env.example` with real values.
3. API and worker must receive the same runtime values for queue/database/storage/LLM settings.
4. Rotate all production secrets on a 90-day cadence (or sooner after incidents).
5. Keep least-privilege IAM on service accounts and CI principals.

## Local development

Use a local `.env` file for developer machines only:

```bash
cp .env.example .env
# Fill in local values only; do not commit .env
```

For GCP credentials, prefer ADC (`gcloud auth application-default login`) in development over long-lived key files when possible.

## Cloud Run (recommended production target)

Store secrets in Google Secret Manager and inject into Cloud Run at deploy time.

Example (API):

```bash
gcloud run deploy pegasus-api \
  --image us-west1-docker.pkg.dev/PROJECT/pegasus/api:latest \
  --set-secrets DATABASE_URL=pegasus-db-url:latest \
  --set-secrets REDIS_URL=pegasus-redis-url:latest \
  --set-secrets GEMINI_API_KEY=pegasus-gemini-key:latest \
  --set-secrets PLC_WRITE_API_TOKEN=pegasus-write-token:latest
```

Apply the same secret names/versions to the worker deployment.

Operational checks:
- Confirm runtime service account has `roles/secretmanager.secretAccessor`.
- Confirm secrets are versioned and not overwritten in place.
- Record rotation date + operator in incident/change log.

## Render

Use Render encrypted environment variables for both API and worker services.

Checklist:
- Set the same `DATABASE_URL`/`REDIS_URL` across API + worker.
- Set LLM provider key only for the active provider.
- Restrict dashboard access with MFA and role-based access.

## Fly.io

Use `fly secrets set` per app/process group.

Example:

```bash
fly secrets set DATABASE_URL=... REDIS_URL=... GEMINI_API_KEY=...
```

If API and worker run as separate apps/process groups, repeat secret sync for both.

## Railway

Use project/service-level variables with least scope needed.

Checklist:
- Keep secret values in Railway Variables only.
- Mirror required secrets to the worker service.
- Re-run smoke test after each credential rotation.

## CI (GitHub Actions)

Store external credentials in GitHub Actions secrets (repository or environment scoped).

Rules:
- Do not echo secrets in logs.
- Use OIDC + short-lived cloud credentials where available.
- Protect main branch and require CI checks before merge.

## Rotation and incident response

When rotating a secret:
1. Create new secret version.
2. Deploy API + worker with new version reference.
3. Run smoke flow (`scripts/smoke_worker_queue.sh`).
4. Revoke old version.
5. Record evidence in change log.

If secret leakage is suspected:
- rotate immediately,
- invalidate outstanding tokens/keys,
- audit logs for misuse window,
- open incident report and attach remediation evidence.
