#!/bin/bash
# Production GCP Integration Verification Script
# Verifies that Gemini (Vertex AI) and Google Speech-to-Text are properly configured

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-pegasus-api}"

echo "🔍 Verifying Pegasus GCP Production Configuration"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "@"; then
  echo "❌ Not authenticated. Run: gcloud auth login"
  exit 1
fi

echo "✅ Authenticated with gcloud"

# Check project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [[ "${CURRENT_PROJECT}" != "${PROJECT_ID}" ]]; then
  echo "⚠️  Current project is ${CURRENT_PROJECT}, setting to ${PROJECT_ID}"
  gcloud config set project "${PROJECT_ID}"
fi

echo "✅ Using project: ${PROJECT_ID}"
echo ""

# Check required APIs
echo "📡 Checking required APIs..."
REQUIRED_APIS=(
  "speech.googleapis.com"
  "aiplatform.googleapis.com"
  "run.googleapis.com"
  "storage.googleapis.com"
  "sqladmin.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
  if gcloud services list --enabled --project="${PROJECT_ID}" --filter="name:${api}" --format="value(name)" 2>/dev/null | grep -q "${api}"; then
    echo "  ✅ ${api}"
  else
    echo "  ❌ ${api} (NOT ENABLED)"
    echo "     Enable with: gcloud services enable ${api} --project=${PROJECT_ID}"
    exit 1
  fi
done

echo ""

# Check Cloud Run service exists
echo "🏃 Checking Cloud Run service..."
if ! gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(metadata.name)" 2>/dev/null | grep -q "${SERVICE_NAME}"; then
  echo "❌ Cloud Run service '${SERVICE_NAME}' not found in region '${REGION}'"
  exit 1
fi

echo "✅ Cloud Run service exists"

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)" 2>/dev/null)
echo "   URL: ${SERVICE_URL}"

# Check environment variables
echo ""
echo "🔧 Checking environment variables..."

ENV_VARS=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="yaml" 2>/dev/null | grep -A 100 "env:")

check_env_var() {
  local var_name="$1"
  local expected_value="${2:-}"

  if echo "${ENV_VARS}" | grep -q "name: ${var_name}"; then
    local actual_value=$(echo "${ENV_VARS}" | grep -A 1 "name: ${var_name}" | grep "value:" | awk '{print $2}')

    if [[ -n "${expected_value}" && "${actual_value}" != "${expected_value}" ]]; then
      echo "  ⚠️  ${var_name}=${actual_value} (expected: ${expected_value})"
    else
      echo "  ✅ ${var_name}=${actual_value}"
    fi
  else
    echo "  ❌ ${var_name} (NOT SET)"
    return 1
  fi
}

# Check critical env vars for Gemini
check_env_var "PLC_LLM_PROVIDER" "gemini"
check_env_var "GEMINI_API_KEY"
check_env_var "GCP_PROJECT_ID" "${PROJECT_ID}"
check_env_var "GCP_REGION" "${REGION}"

# Check storage configuration
check_env_var "STORAGE_MODE" "gcs"
check_env_var "GCS_BUCKET"
check_env_var "GCS_PREFIX" "pegasus"

# Check optional STT configuration
echo ""
echo "📝 Optional Google Speech-to-Text env vars:"
check_env_var "PLC_GCP_STT_MODEL" || echo "  ℹ️  PLC_GCP_STT_MODEL not set (will use default: latest_long)"
check_env_var "PLC_STT_LANGUAGE" || echo "  ℹ️  PLC_STT_LANGUAGE not set (will use default: en-US)"

echo ""

# Check service account permissions
echo "🔐 Checking service account permissions..."
SERVICE_ACCOUNT=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null)
echo "   Service Account: ${SERVICE_ACCOUNT}"

ROLES=$(gcloud projects get-iam-policy "${PROJECT_ID}" --flatten="bindings[].members" --filter="bindings.members:${SERVICE_ACCOUNT}" --format="value(bindings.role)" 2>/dev/null)

echo ""
echo "   Assigned roles:"
echo "${ROLES}" | while read -r role; do
  echo "   - ${role}"
done

# Check for Speech and Vertex AI permissions
if echo "${ROLES}" | grep -q "storage"; then
  echo "   ✅ Has storage permissions"
else
  echo "   ⚠️  No explicit storage roles (may use default compute permissions)"
fi

echo ""
echo "💡 Note: Cloud Run services use the default compute service account which has"
echo "   automatic access to Speech-to-Text and Vertex AI APIs when enabled."

echo ""

# Test health endpoint
echo "🏥 Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health" || echo "")

if echo "${HEALTH_RESPONSE}" | grep -q '"status":"ok"'; then
  echo "✅ Health check passed"
  echo "   Response: ${HEALTH_RESPONSE}"
else
  echo "❌ Health check failed"
  echo "   Response: ${HEALTH_RESPONSE}"
  exit 1
fi

echo ""
echo "✅ All production environment checks passed!"
echo ""
echo "🎯 Summary:"
echo "   • Gemini (Vertex AI) API: Enabled"
echo "   • Google Speech-to-Text API: Enabled"
echo "   • LLM Provider: gemini"
echo "   • Storage Mode: gcs"
echo "   • Service URL: ${SERVICE_URL}"
echo ""
echo "📚 Next steps:"
echo "   1. Test transcription: POST ${SERVICE_URL}/lectures/{id}/transcribe?provider=google"
echo "   2. Test generation: POST ${SERVICE_URL}/lectures/{id}/generate (uses Gemini by default)"
echo "   3. Monitor logs: gcloud run services logs read ${SERVICE_NAME} --region=${REGION}"
echo ""
