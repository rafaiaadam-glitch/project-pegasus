# Staging Environment Parity Checklist

Use this checklist before accepting staging as representative of production.

## Infrastructure parity

- [ ] Same major Postgres version as production
- [ ] Same Redis engine/version family as production
- [ ] Same storage backend class (`s3` vs `gcs`) as production
- [ ] Same service split (API + worker) and queue topology

## Runtime configuration parity

- [ ] Same required env var set as production
- [ ] Same `PLC_LLM_PROVIDER` and default model family
- [ ] Same `STORAGE_MODE` and bucket/prefix strategy
- [ ] Same auth/rate limit settings for write endpoints

## Deployment/parsing parity

- [ ] Same Dockerfile (`backend/Dockerfile`) for API and worker
- [ ] Same migration path (`backend/migrations`) applied at startup
- [ ] Same readiness endpoint contract (`/health/ready`)

## Operational parity

- [ ] Alerting routes enabled for staging drills
- [ ] Dashboard queries render staging metrics correctly
- [ ] Dead-letter replay workflow verified in staging
- [ ] Backup/restore rehearsal runs against staging data

## Validation commands

- `pytest backend/tests/test_readiness.py`
- `pytest backend/tests/test_platform_health_checks.py`
- `python -m backend.run_migrations`
- `curl <staging-api>/health/ready`

## Sign-off template

- Environment: `<staging-name>`
- Reviewer(s): `<name>`
- Date:
- Gaps found:
- Follow-up issues:
