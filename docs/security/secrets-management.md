# Secrets Management Guide

This guide defines the canonical way to handle Pegasus secrets across deploy targets.

## Scope

Applies to all credentials/tokens used by API, worker, mobile development, CI, and operational scripts.

## Secret inventory

At minimum, treat the following as secrets and never commit them to git:

- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `PLC_WRITE_API_TOKEN`
- `GOOGLE_APPLICATION_CREDENTIALS` content (service account JSON)
- Any private bucket, queue, or provider credentials

## Baseline policy (all environments)

- Do not hardcode secrets in source files, runbooks, or examples.
- Store only placeholders in docs (for example: `your-token-here`).
- Rotate secrets after any suspected leak and at least quarterly for production.
- Use least-privilege service accounts per environment.
- Log redaction: never include auth headers, API keys, or raw credentials in logs.

## Cloud Run / GCP (production + staging)

### Required approach

1. Store app secrets in **Google Secret Manager**.
2. Grant access only to the specific Cloud Run service account.
3. Inject secrets as environment variables at deploy time.
4. Keep non-sensitive settings in plain env vars; keep secrets in Secret Manager.

### Example deployment pattern

```bash
gcloud run deploy pegasus-api \
  --image gcr.io/PROJECT/pegasus-api:TAG \
  --set-secrets "OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --set-secrets "PLC_WRITE_API_TOKEN=PLC_WRITE_API_TOKEN:latest"
```

### Operational controls

- Enable Secret Manager audit logs.
- Use separate secrets/projects for staging and production.
- Rotate by publishing a new secret version, then redeploy.

## GitHub Actions / CI

### Required approach

- Store CI secrets in **GitHub Actions Secrets** at repo/org/environment scope.
- Use environment protection rules for production deploy credentials.
- Prefer short-lived OIDC federation for cloud auth instead of long-lived JSON keys.

### CI hygiene

- Never echo secrets in workflow logs.
- Use masked outputs and avoid writing secrets to artifacts.
- Restrict workflows that can access production secrets (branch + reviewer protections).

## Local development

### Required approach

- Use a local `.env` file that is gitignored.
- Keep only sample placeholders in `.env.example`.
- If real cloud creds are required locally, prefer temporary credentials.

### Developer checklist

- Confirm `.env` is ignored before first commit.
- Do not paste secrets in issues/PRs.
- Rotate immediately if accidentally exposed.

## Mobile app considerations

- Never bundle privileged backend secrets (for example OpenAI keys) in the mobile app.
- Public Expo config values (`EXPO_PUBLIC_*`) are client-visible by design.
- If write auth is enabled, use a backend-issued user/session token model for production; do not hardcode privileged static tokens in the app binary.

## Incident response for secret leaks

1. Revoke/rotate exposed secret.
2. Redeploy affected services.
3. Audit logs for misuse during exposure window.
4. Document incident and remediation in runbook/checklist evidence.

## Verification checklist

- [ ] No plaintext credentials in docs/scripts
- [ ] Production secrets sourced from Secret Manager
- [ ] CI secrets sourced from GitHub secrets or OIDC
- [ ] `.env` files ignored locally
- [ ] Rotation date recorded for critical secrets


## Related security docs

- `docs/security/pii-handling-policy.md`
