# Secrets management guide (local, staging, production)

This guide closes launch checklist item:

- "Add secrets management guidance for each deploy target"

## Scope

This policy applies to all sensitive runtime values used by Pegasus API, worker, mobile, and CI pipelines.

### Secrets in scope

- API keys (`OPENAI_API_KEY` and equivalent provider tokens)
- Database credentials (`DATABASE_URL`)
- Queue credentials (`REDIS_URL`)
- Object storage credentials (`AWS_*`, `GCP_*`, signed URL keys)
- Signing keys and webhook shared secrets

### Explicitly not secrets

- Feature flags
- Public URLs/endpoints
- Non-sensitive tuning values (timeouts, batch sizes)

## Baseline rules (all environments)

1. Never hardcode secrets in source files, tests, Dockerfiles, or mobile bundles.
2. Never commit `.env` files containing real values.
3. Inject secrets at runtime from platform secret stores.
4. Use least privilege (separate keys for API vs worker where possible).
5. Rotate high-impact secrets at least every 90 days.
6. Revoke and replace immediately after suspected exposure.

## Deploy-target guidance

### Local development

- Use local `.env` files that are gitignored.
- Keep only developer-scoped non-production credentials.
- Bootstrap from `.env.example` and fill manually.
- If a local key is exposed, rotate before next push.

### Render (`render.yaml`)

- Store all sensitive values in Render Environment Groups or service-level secret variables.
- Do not place secret values in `render.yaml`; only reference variable names.
- Limit dashboard access to least privilege and enable org MFA.

### Railway (`railway.toml`, `railway.worker.toml`)

- Configure variables in Railway project/service settings, not in TOML files.
- Separate API and worker secret scopes when supported.
- Use Railway audit history for change tracking after each rotation.

### Fly.io (`fly.toml`)

- Set secrets through `fly secrets set` (or managed secrets backend) per app.
- Do not place secret literals in `fly.toml`.
- Re-deploy after secret rotation and verify readiness endpoints.

### GCP / Cloud Build (`cloudbuild.yaml`)

- Source secrets from Secret Manager with IAM-bound service accounts.
- Restrict secret accessor roles to deploy/runtime identities only.
- Enable audit logging for secret access and rotation events.

## Environment variable ownership matrix

| Variable | API | Worker | Mobile | CI | Notes |
|---|---|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | ✅ | ❌ | ✅ (tests only) | separate prod/staging keys |
| `DATABASE_URL` | ✅ | ✅ | ❌ | ✅ | production DB creds never used locally |
| `REDIS_URL` | ✅ | ✅ | ❌ | ✅ | isolate by environment |
| `PLC_STORAGE_DIR` | ✅ | ✅ | ❌ | ✅ | non-secret path; keep env-specific |
| `JWT_SECRET` / signing keys | ✅ | ❌ | ❌ | ❌ | rotate with overlap window |

## Rotation runbook (minimum)

1. Create replacement secret value in provider store.
2. Update staging first; validate `/health/ready` and one ingest→generate flow.
3. Update production with staggered rollout.
4. Revoke previous secret immediately after rollout verification.
5. Record operator, timestamp, and impacted services in operations log.

## Break-glass procedure

Use only for confirmed leak or active abuse.

1. Freeze deploys.
2. Rotate affected credentials immediately in secret store.
3. Restart API and worker services.
4. Validate readiness + critical-path smoke checks.
5. Open incident record with impact window and remediation timeline.

## Evidence required for checklist closure

Record these three proof lines:

- **Endpoint/UI:** Secret-store configuration exists for each deploy target (Render/Railway/Fly/GCP/local policy).
- **Test:** One secret rotation rehearsal in staging with health and pipeline smoke checks.
- **Proof:** Dated change log or screenshot of secret version update plus successful readiness output.
