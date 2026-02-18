# Fix Database Connection NOW

## Quick Fix (5 minutes)

Run these commands in your terminal where you're authenticated:

### Step 1: Run the automated fix script

```bash
cd /Users/rafaiaadam/project-pegasus
./scripts/fix-database-connection.sh
```

The script will:
- ✅ Check Cloud SQL instance status
- ✅ Verify connection configuration
- ✅ Fix service account permissions
- ✅ Validate DATABASE_URL secret
- ✅ Provide redeployment commands

### Step 2: If Cloud SQL instance doesn't exist

If you get "No Cloud SQL instances found", create one:

```bash
# Create Cloud SQL instance
gcloud sql instances create pegasus-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-west1 \
  --project=delta-student-486911-n5

# Create database
gcloud sql databases create pegasus_db \
  --instance=pegasus-db \
  --project=delta-student-486911-n5

# Set root password (choose a secure password)
gcloud sql users set-password postgres \
  --instance=pegasus-db \
  --password=YOUR_SECURE_PASSWORD \
  --project=delta-student-486911-n5

# Create application user
gcloud sql users create pegasus_user \
  --instance=pegasus-db \
  --password=YOUR_SECURE_PASSWORD \
  --project=delta-student-486911-n5
```

### Step 3: Create DATABASE_URL secret

```bash
# Get the connection name
CONNECTION_NAME=$(gcloud sql instances describe pegasus-db \
  --project=delta-student-486911-n5 \
  --format="value(connectionName)")

echo "Connection name: ${CONNECTION_NAME}"

# Create the secret
echo -n "postgresql://pegasus_user:YOUR_PASSWORD@/pegasus_db?host=/cloudsql/${CONNECTION_NAME}" | \
  gcloud secrets create pegasus-db-url \
  --data-file=- \
  --replication-policy="automatic" \
  --project=delta-student-486911-n5
```

### Step 4: Grant permissions

```bash
# Grant Cloud SQL Client role to Cloud Run service account
gcloud projects add-iam-policy-binding delta-student-486911-n5 \
  --member="serviceAccount:delta-student-486911-n5@appspot.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Grant Secret Accessor role
gcloud projects add-iam-policy-binding delta-student-486911-n5 \
  --member="serviceAccount:delta-student-486911-n5@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 5: Redeploy Cloud Run service

```bash
# Update the deployment script if needed
# Edit scripts/deploy-cloud-run-google-stt.sh line 37:
# --add-cloudsql-instances="${PROJECT_ID}:${REGION}:pegasus-db"

# Then redeploy
./scripts/deploy-cloud-run-google-stt.sh
```

### Step 6: Run database migrations

```bash
# SSH into Cloud Run or run migrations locally
# You may need to create tables first

# Example: Create tables using SQL
gcloud sql connect pegasus-db --user=pegasus_user --database=pegasus_db

# Or use your migration scripts if they exist
```

---

## Verify It Works

After fixing, test these endpoints:

```bash
# Should return 200 OK
curl https://pegasus-api-988514135894.us-west1.run.app/health

# Should return 200 with data (not 500)
curl https://pegasus-api-988514135894.us-west1.run.app/courses?limit=1

# Should return 200 with data
curl https://pegasus-api-988514135894.us-west1.run.app/lectures?limit=1
```

---

## Alternative: Use SQLite for Development

If you don't want to set up Cloud SQL right now, you can use SQLite:

**Update backend/db.py to use SQLite:**
```python
# Change DATABASE_URL to use SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pegasus.db")
```

**Redeploy:**
```bash
./scripts/deploy-cloud-run-google-stt.sh
```

Note: SQLite is fine for development but not recommended for production.

---

## Quick Status Check

Run this to see current status:

```bash
# Check Cloud SQL instances
gcloud sql instances list --project=delta-student-486911-n5

# Check secrets
gcloud secrets list --project=delta-student-486911-n5 | grep pegasus

# Check Cloud Run env vars
gcloud run services describe pegasus-api \
  --region=us-west1 \
  --project=delta-student-486911-n5 \
  --format="yaml" | grep -A 20 "env:"
```

---

## Once Fixed

1. **Disable mock data in mobile app:**
   ```typescript
   // mobile/src/services/api.ts line 39:
   const USE_MOCK_DATA = false;
   ```

2. **Restart mobile app:**
   ```bash
   npx expo start --clear
   ```

3. **Test full flow:**
   - Record lecture
   - Upload (should work now!)
   - Transcribe
   - Generate artifacts

---

## Need Help?

If the script fails or you get stuck, share:
1. The error message
2. Output from: `gcloud sql instances list`
3. Output from: `gcloud secrets list`

I'll help troubleshoot!
