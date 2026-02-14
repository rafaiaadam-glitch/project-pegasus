# GCP Deployment Guide

## Prerequisites

1. **GCP Account** with billing enabled
2. **gcloud CLI** installed and configured
3. **Project ID**: `delta-student-486911-n5`

## Quick Deploy

Run the automated setup script:

```bash
cd /Users/rafaiaadam/project-pegasus
./scripts/setup-gcp.sh
```

This will:
- Enable required GCP APIs
- Create Cloud SQL PostgreSQL instance
- Create Cloud Storage bucket
- Build and deploy to Cloud Run
- Set up secrets and environment variables

## Manual Setup (if needed)

### 1. Authenticate

```bash
gcloud auth login
gcloud config set project delta-student-486911-n5
```

### 2. Enable APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Create Cloud SQL Instance

```bash
gcloud sql instances create pegasus-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --network=default
```

### 4. Create Database

```bash
gcloud sql databases create pegasus \
  --instance=pegasus-db
```

### 5. Create User

```bash
gcloud sql users create pegasus \
  --instance=pegasus-db \
  --password=YOUR_PASSWORD
```

### 6. Create Cloud Storage Bucket

```bash
gsutil mb -p delta-student-486911-n5 \
  -c STANDARD \
  -l us-central1 \
  gs://delta-student-486911-n5-pegasus-storage/
```

### 7. Store Secrets

```bash
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy="automatic"

echo -n "YOUR_DB_PASSWORD" | gcloud secrets create pegasus-db-password \
  --data-file=- \
  --replication-policy="automatic"
```

### 8. Deploy to Cloud Run

```bash
gcloud builds submit --config=cloudbuild.yaml
```

## Environment Variables

The Cloud Run service needs these environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `STORAGE_MODE`: Set to `gcs`
- `GCS_BUCKET`: Your Cloud Storage bucket name
- `OPENAI_API_KEY`: Your OpenAI API key
- `PLC_INLINE_JOBS`: Set to `true` for inline job processing
- `REDIS_URL`: Optional, for distributed job queue

## Update Deployment

After making code changes:

```bash
gcloud builds submit --config=cloudbuild.yaml
```

## View Logs

```bash
gcloud run services logs read pegasus-api --region=us-central1 --limit=50
```

## Get Service URL

```bash
gcloud run services describe pegasus-api \
  --region=us-central1 \
  --format='value(status.url)'
```

## Connect Mobile App

Update `mobile/src/services/api.ts`:

```typescript
const API_BASE_URL = "YOUR_CLOUD_RUN_URL";
const USE_MOCK_DATA = false;
```

## Cost Estimates

**Cloud Run** (f1-micro):
- Free tier: 2 million requests/month
- After: ~$0.00002 per request

**Cloud SQL** (db-f1-micro):
- ~$7.67/month

**Cloud Storage**:
- $0.02/GB/month
- $0.004 per 10,000 operations

**Total**: ~$10-20/month for moderate usage

## Troubleshooting

### Cloud SQL Connection Issues

Check connection name:
```bash
gcloud sql instances describe pegasus-db \
  --format='value(connectionName)'
```

### Storage Permissions

Grant Cloud Run service account access:
```bash
gcloud projects add-iam-policy-binding delta-student-486911-n5 \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

### View Build Logs

```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

## Cleanup

To delete all resources:

```bash
gcloud run services delete pegasus-api --region=us-central1
gcloud sql instances delete pegasus-db
gsutil rm -r gs://delta-student-486911-n5-pegasus-storage/
```
