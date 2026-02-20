# Staging Environment Parity Checklist

Ensure the staging environment mirrors production configuration to catch issues before they reach users.

---

## Environment Variable Alignment

| Variable | Production | Staging | Notes |
|---|---|---|---|
| `STORAGE_MODE` | `gcs` | `gcs` | Must match |
| `GCS_BUCKET` | `...-pegasus-storage-eu` | `...-pegasus-storage-eu-staging` | Separate bucket |
| `GCS_PREFIX` | `pegasus` | `pegasus` | Same prefix structure |
| `PLC_LLM_PROVIDER` | `openai` | `openai` | Same provider |
| `PLC_INLINE_JOBS` | `1` | `1` | Same execution mode |
| `GCP_REGION` | `europe-west1` | `europe-west1` | Same region |
| `DATABASE_URL` | (prod secret) | (staging secret) | Separate DB instance |
| `OPENAI_API_KEY` | (prod key) | (staging key) | Can share key; separate for cost tracking |

### Verification

```bash
# Compare env vars between prod and staging
gcloud run services describe pegasus-api --region=europe-west1 --format='yaml(spec.template.spec.containers[0].env)' --project=delta-student-486911-n5
gcloud run services describe pegasus-api-staging --region=europe-west1 --format='yaml(spec.template.spec.containers[0].env)' --project=delta-student-486911-n5
```

---

## Secret Rotation Parity

| Secret | Production | Staging | Rotation cadence |
|---|---|---|---|
| `pegasus-db-url` | Secret Manager | Secret Manager | On credential change |
| `openai-api-key` | Secret Manager | Secret Manager | On key rotation |

- [ ] Both environments reference the latest secret version (or a pinned version with matching rotation schedule)
- [ ] `DATABASE_URL` values have no trailing newline in either environment
- [ ] Secrets are accessible by the respective Cloud Run service accounts

---

## Cloud SQL Instance Parity

| Property | Production | Staging |
|---|---|---|
| Instance | `pegasus-db-eu` | `pegasus-db-eu-staging` |
| Region | `europe-west1` | `europe-west1` |
| Postgres version | 14 | 14 |
| DB user | `pegasus_user` | `pegasus_user` |
| Extensions | (list from prod) | Must match prod |
| Migrations | Applied on startup | Applied on startup |

### Verification

```bash
# Compare Postgres versions
gcloud sql instances describe pegasus-db-eu --format='value(databaseVersion)'
gcloud sql instances describe pegasus-db-eu-staging --format='value(databaseVersion)'

# Compare applied migrations (connect to each DB)
psql "$DATABASE_URL" -c "SELECT * FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

---

## GCS Bucket Parity

| Property | Production | Staging |
|---|---|---|
| Bucket | `delta-student-486911-n5-pegasus-storage-eu` | `delta-student-486911-n5-pegasus-storage-eu-staging` |
| Prefix | `pegasus/` | `pegasus/` |
| Location | `europe-west1` | `europe-west1` |
| Lifecycle rules | Same retention policy | Same retention policy |
| Service account access | `pegasus-api@...` | `pegasus-api@...` (or staging SA) |

- [ ] Staging bucket has the same lifecycle/retention rules as production
- [ ] Service account has `storage.objects.create` and `storage.objects.get` on staging bucket

---

## Cloud Run Service Config Parity

| Property | Production | Staging |
|---|---|---|
| Memory | 2 Gi | 2 Gi |
| CPU | 2 | 2 |
| Min instances | 0 | 0 |
| Max instances | 4 | 2 (can be lower for staging) |
| Timeout | 300s | 300s |
| Concurrency | 80 | 80 |
| Startup probe | `/health`, 60s | `/health`, 60s |
| Liveness probe | `/health/live`, 30s interval | `/health/live`, 30s interval |
| Startup CPU boost | Enabled | Enabled |
| Cloud SQL connection | `...:europe-west1:pegasus-db-eu` | `...:europe-west1:pegasus-db-eu-staging` |

### Verification

```bash
# Compare service configs
gcloud run services describe pegasus-api --region=europe-west1 --format=yaml --project=delta-student-486911-n5 > /tmp/prod.yaml
gcloud run services describe pegasus-api-staging --region=europe-west1 --format=yaml --project=delta-student-486911-n5 > /tmp/staging.yaml
diff /tmp/prod.yaml /tmp/staging.yaml
```

---

## Smoke Test Procedure

After verifying parity, run the smoke test against staging:

```bash
API_BASE_URL=https://pegasus-api-staging-....europe-west1.run.app \
  ./scripts/smoke_worker_queue.sh
```

This validates:
1. `/health` returns 200
2. Lecture ingest succeeds
3. Transcription job completes (or fails with expected error for test audio)
4. Artifact generation and export paths work

See `docs/deploy.md` for detailed smoke test steps.

---

## Related Documentation

- Deployment guide: `docs/deployment-guide.md`
- Release checklist: `docs/release-checklist.md`
- Secrets management: `docs/runbooks/secrets-management.md`
