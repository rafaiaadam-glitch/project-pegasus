#!/bin/bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-europe-west1}"
DB_INSTANCE="${DB_INSTANCE:-pegasus-db}"
DB_NAME="${DB_NAME:-pegasus}"
DB_USER="${DB_USER:-pegasus}"
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_ID}-pegasus-storage}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "❌ PROJECT_ID is not set. Export PROJECT_ID or run: gcloud config set project <id>"
  exit 1
fi

echo "🚀 Setting up Pegasus on GCP"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

gcloud config set project "${PROJECT_ID}"

echo "📦 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"

echo "🗄️  Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create "${DB_INSTANCE}" \
  --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 \
  --region="${REGION}" \
  --database-flags=max_connections=100 \
  --project="${PROJECT_ID}" \
  || echo "Instance may already exist"

echo "👤 Creating database and user..."
gcloud sql databases create "${DB_NAME}" \
  --instance="${DB_INSTANCE}" \
  --project="${PROJECT_ID}" \
  || echo "Database may already exist"

DB_PASSWORD=$(openssl rand -base64 32)

gcloud sql users create "${DB_USER}" \
  --instance="${DB_INSTANCE}" \
  --password="${DB_PASSWORD}" \
  --project="${PROJECT_ID}" \
  || echo "User may already exist"

echo "🔐 Storing database password in Secret Manager..."
printf "%s" "${DB_PASSWORD}" | gcloud secrets create pegasus-db-password \
  --data-file=- \
  --replication-policy="automatic" \
  --project="${PROJECT_ID}" \
  || echo "Secret may already exist"

echo "💾 Creating Cloud Storage bucket..."
gsutil mb -p "${PROJECT_ID}" -c STANDARD -l "${REGION}" "gs://${BUCKET_NAME}/" \
  || echo "Bucket may already exist"

echo ""
echo "✅ GCP bootstrap complete!"
echo ""
echo "📝 Use these runtime env vars for BOTH API and worker:"
echo "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
echo "STORAGE_MODE=gcs"
echo "GCS_BUCKET=${BUCKET_NAME}"
echo "GCS_PREFIX=pegasus"
echo ""
echo "🔧 Example Cloud Run wiring:"
echo "gcloud run services update pegasus-api --region=${REGION} --project=${PROJECT_ID} \\ "
echo "  --set-env-vars=STORAGE_MODE=gcs,GCS_BUCKET=${BUCKET_NAME},GCS_PREFIX=pegasus"
echo "gcloud run services update pegasus-worker --region=${REGION} --project=${PROJECT_ID} \\ "
echo "  --set-env-vars=STORAGE_MODE=gcs,GCS_BUCKET=${BUCKET_NAME},GCS_PREFIX=pegasus"
