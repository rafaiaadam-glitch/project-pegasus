#!/bin/bash
# Initialize database schema for Pegasus
# Runs migrations on Cloud Run service with Cloud SQL access

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
REGION="${REGION:-us-west1}"
SERVICE_NAME="${SERVICE_NAME:-pegasus-api}"

echo "🗄️  Initializing Pegasus Database Schema"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo "📡 Service URL: ${SERVICE_URL}"
echo ""

# Deploy the migration script to the service
echo "📦 Building image with migration script..."

# Create a temporary Dockerfile that includes the migration runner
cat > /tmp/Dockerfile.migrate <<'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY pipeline /app/pipeline
COPY schemas /app/schemas

ENV PORT=8080
EXPOSE 8080

# Default: Run migrations then start server
CMD python -m backend.run_migrations && \
    uvicorn backend.app:app --host 0.0.0.0 --port $PORT
EOF

# Build and deploy with migration runner
IMAGE_NAME="us-west1-docker.pkg.dev/${PROJECT_ID}/pegasus/api:migrate"

echo "Building image..."
gcloud builds submit \
    --tag="${IMAGE_NAME}" \
    --project="${PROJECT_ID}" \
    --dockerfile=/tmp/Dockerfile.migrate \
    --timeout=15m

echo ""
echo "🚀 Deploying service with migrations..."

gcloud run deploy "${SERVICE_NAME}-migrate" \
    --image="${IMAGE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --platform=managed \
    --no-allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION}" \
    --set-secrets="DATABASE_URL=pegasus-db-url:latest" \
    --add-cloudsql-instances="${PROJECT_ID}:us-central1:planwell-db" \
    --memory=512Mi \
    --cpu=1 \
    --max-instances=1 \
    --timeout=300 \
    --no-traffic

echo ""
echo "🔄 Running migrations..."

# Trigger the service to run migrations
gcloud run services update-traffic "${SERVICE_NAME}-migrate" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --to-latest

echo ""
echo "🧹 Cleaning up temporary service..."
gcloud run services delete "${SERVICE_NAME}-migrate" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet

rm /tmp/Dockerfile.migrate

echo ""
echo "✅ Database schema initialized!"
echo ""
echo "🔍 You can verify by checking the tables:"
echo "  curl ${SERVICE_URL}/courses"
echo "  curl ${SERVICE_URL}/lectures"
