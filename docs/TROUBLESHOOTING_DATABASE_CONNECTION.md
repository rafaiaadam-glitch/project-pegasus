# Database Connection Troubleshooting

**Issue:** API returns "Internal Server Error" for database-dependent endpoints

## Symptoms

- ✅ `/health` endpoint works
- ✅ `/presets` endpoint works (no database required)
- ❌ `/lectures` returns "Internal Server Error"
- ❌ `/courses` returns "Internal Server Error"
- ❌ Any endpoint that queries the database fails

## Root Cause

The Cloud Run service cannot connect to Cloud SQL. This is typically due to:

1. **Cloud SQL instance not running**
2. **Cloud SQL connection string misconfigured**
3. **Database credentials (DATABASE_URL secret) incorrect**
4. **Cloud SQL instance name mismatch**
5. **Network/VPC configuration issue**

## Diagnosis Steps

### 1. Check Cloud SQL Instance Status

```bash
PROJECT_ID="delta-student-486911-n5"
REGION="us-west1"

gcloud sql instances list --project=${PROJECT_ID}
```

Expected output: Instance should show `RUNNABLE` status.

### 2. Verify Cloud Run Configuration

```bash
SERVICE_NAME="pegasus-api"

# Check Cloud SQL connection string
gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(spec.template.metadata.annotations['run.googleapis.com/cloudsql-instances'])"
```

Expected: `delta-student-486911-n5:us-west1:planwell-db`

### 3. Check DATABASE_URL Secret

```bash
# View secret value (requires permissions)
gcloud secrets versions access latest \
  --secret=pegasus-db-url \
  --project=${PROJECT_ID}
```

Expected format:
```
postgresql://username:password@/database?host=/cloudsql/delta-student-486911-n5:us-west1:planwell-db
```

### 4. Check Service Logs

```bash
gcloud run services logs read ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --limit=50
```

Look for errors like:
- `could not connect to server`
- `FATAL: database "X" does not exist`
- `FATAL: password authentication failed`
- `connection refused`

## Common Fixes

### Fix 1: Update Cloud SQL Connection String

The deployment script uses `planwell-db` as the instance name. Verify this matches your actual Cloud SQL instance:

```bash
# List actual instances
gcloud sql instances list --project=${PROJECT_ID}

# Update deployment script if needed
# In scripts/deploy-cloud-run-google-stt.sh, line 37:
--add-cloudsql-instances="${PROJECT_ID}:${REGION}:YOUR_ACTUAL_INSTANCE_NAME"
```

### Fix 2: Recreate DATABASE_URL Secret

```bash
# Format: postgresql://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
DATABASE_URL="postgresql://pegasus_user:YOUR_PASSWORD@/pegasus_db?host=/cloudsql/delta-student-486911-n5:us-west1:planwell-db"

# Create or update secret
echo -n "${DATABASE_URL}" | gcloud secrets create pegasus-db-url \
  --data-file=- \
  --project=${PROJECT_ID} \
  --replication-policy="automatic"

# Or update existing
echo -n "${DATABASE_URL}" | gcloud secrets versions add pegasus-db-url \
  --data-file=- \
  --project=${PROJECT_ID}
```

### Fix 3: Grant Cloud Run Service Account Permissions

```bash
# Get the service account email
SERVICE_ACCOUNT=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(spec.template.spec.serviceAccountName)")

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client"
```

### Fix 4: Start Cloud SQL Instance (if stopped)

```bash
INSTANCE_NAME="planwell-db"

gcloud sql instances patch ${INSTANCE_NAME} \
  --activation-policy=ALWAYS \
  --project=${PROJECT_ID}
```

### Fix 5: Update Region Mismatch

**Current Issue:** Documentation says `europe-west1`, but service is in `us-west1`.

**Option A: Update all docs to use us-west1**
```bash
# Already done in mobile/.env
EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-west1.run.app
```

**Option B: Redeploy to europe-west1**
```bash
# Update deployment script region
REGION="europe-west1" ./scripts/deploy-cloud-run-google-stt.sh

# May need to create Cloud SQL instance in europe-west1 first
```

## Quick Test

After applying fixes, test the endpoints:

```bash
API_URL="https://pegasus-api-988514135894.us-west1.run.app"

# Should work (no database)
curl "${API_URL}/health"
curl "${API_URL}/presets"

# Should work after fix (requires database)
curl "${API_URL}/courses?limit=10&offset=0"
curl "${API_URL}/lectures?limit=10&offset=0"
```

## Mobile App Fix

**Issue:** Mobile app was pointing to non-existent europe-west1 deployment.

**Fix:** Updated `mobile/.env` to use us-west1:

```bash
# mobile/.env
EXPO_PUBLIC_API_URL=https://pegasus-api-988514135894.us-west1.run.app
```

**After updating .env:**
1. Stop Expo dev server (`Ctrl+C`)
2. Clear Metro cache: `npx expo start --clear`
3. Restart: `npx expo start`

## Recommended Action Plan

1. **Immediate Fix (Mobile Development)**
   - ✅ Use us-west1 URL (already updated)
   - ⏳ Fix database connection (see steps above)

2. **Production Deployment Decision**
   - Choose one region: `us-west1` OR `europe-west1`
   - Update all documentation to match
   - Ensure Cloud SQL instance exists in chosen region
   - Deploy and verify

3. **Verify Database Connection**
   - Check Cloud SQL instance status
   - Verify DATABASE_URL secret format
   - Test connection from Cloud Run service
   - Check service logs for errors

## Status

- [x] Mobile app pointing to correct region (us-west1)
- [x] API health endpoint working
- [x] Presets endpoint working
- [ ] **Database connection needs fixing**
- [ ] Courses endpoint returning 500 error
- [ ] Lectures endpoint returning 500 error

## Next Steps

1. Check Cloud SQL instance status
2. Verify DATABASE_URL secret
3. Check Cloud Run service logs
4. Fix database connection issue
5. Redeploy if needed
6. Test end-to-end flow
