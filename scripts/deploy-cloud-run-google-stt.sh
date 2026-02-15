#!/bin/bash
# Deploy Pegasus to Cloud Run with Google Speech-to-Text
# This script builds and deploys the updated Docker image with ffmpeg support

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
REGION="${REGION:-us-west1}"
SERVICE_NAME="${SERVICE_NAME:-pegasus-api}"
IMAGE_NAME="us-west1-docker.pkg.dev/${PROJECT_ID}/pegasus/api:latest"

echo "🚀 Deploying Pegasus with Google Speech-to-Text support"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "📦 Building Docker image with ffmpeg..."
gcloud builds submit \
  --tag="${IMAGE_NAME}" \
  --project="${PROJECT_ID}" \
  --timeout=15m

echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="PLC_LLM_PROVIDER=gemini,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},STORAGE_MODE=gcs,GCS_BUCKET=${PROJECT_ID}-pegasus-storage,GCS_PREFIX=pegasus,PLC_INLINE_JOBS=1,PLC_GCP_STT_MODEL=latest_long,PLC_STT_LANGUAGE=en-US" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=pegasus-db-url:latest" \
  --add-cloudsql-instances="${PROJECT_ID}:${REGION}:planwell-db" \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --timeout=300

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔍 Testing deployment..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

echo "Service URL: ${SERVICE_URL}"

# Test health endpoint
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health" || echo "")
if echo "${HEALTH_RESPONSE}" | grep -q '"status":"ok"'; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed"
  echo "Response: ${HEALTH_RESPONSE}"
  exit 1
fi

echo ""
echo "🎯 Google Speech-to-Text is now the default transcription provider!"
echo ""
echo "📝 Configuration:"
echo "  • Transcription: Google Speech-to-Text (default)"
echo "  • Model: latest_long (high accuracy)"
echo "  • M4A Support: Yes (automatic conversion to MP3)"
echo "  • LLM: Gemini (fast and cost-effective)"
echo "  • Storage: Google Cloud Storage"
echo ""
echo "📚 Usage:"
echo "  # Transcribe with Google STT (default)"
echo "  POST ${SERVICE_URL}/lectures/{id}/transcribe"
echo ""
echo "  # Or use Whisper (native M4A support, no conversion)"
echo "  POST ${SERVICE_URL}/lectures/{id}/transcribe?provider=whisper"
echo ""
echo "✅ Ready for production! 🚀"
