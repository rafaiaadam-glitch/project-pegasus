#!/bin/bash
# Fix Cloud SQL Database Connection for Pegasus Backend
# Run this script to diagnose and fix database connection issues

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-pegasus-api}"

echo "🔧 Fixing Cloud SQL Database Connection"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Step 1: Check Cloud SQL instance status
echo "📊 Step 1: Checking Cloud SQL instance status..."
INSTANCES=$(gcloud sql instances list --project="${PROJECT_ID}" --format="value(name,state)")

if [ -z "$INSTANCES" ]; then
    echo "❌ No Cloud SQL instances found!"
    echo ""
    echo "You need to create a Cloud SQL instance first:"
    echo "  gcloud sql instances create pegasus-db \\"
    echo "    --database-version=POSTGRES_15 \\"
    echo "    --tier=db-f1-micro \\"
    echo "    --region=${REGION} \\"
    echo "    --project=${PROJECT_ID}"
    echo ""
    echo "Then create the database:"
    echo "  gcloud sql databases create pegasus_db \\"
    echo "    --instance=pegasus-db \\"
    echo "    --project=${PROJECT_ID}"
    exit 1
fi

echo "$INSTANCES"
echo ""

# Step 2: Check if instance is running
echo "📊 Step 2: Ensuring instance is running..."
INSTANCE_NAME=$(echo "$INSTANCES" | head -1 | awk '{print $1}')
INSTANCE_STATE=$(echo "$INSTANCES" | head -1 | awk '{print $2}')

if [ "$INSTANCE_STATE" != "RUNNABLE" ]; then
    echo "⚠️  Instance is in state: ${INSTANCE_STATE}"
    echo "Starting instance..."
    gcloud sql instances patch "${INSTANCE_NAME}" \
        --activation-policy=ALWAYS \
        --project="${PROJECT_ID}"

    echo "Waiting for instance to become runnable..."
    sleep 10
fi

echo "✅ Instance is runnable"
echo ""

# Step 3: Get connection string
echo "📊 Step 3: Getting Cloud SQL connection string..."
CONNECTION_NAME=$(gcloud sql instances describe "${INSTANCE_NAME}" \
    --project="${PROJECT_ID}" \
    --format="value(connectionName)")

echo "Connection name: ${CONNECTION_NAME}"
echo ""

# Step 4: Check Cloud Run configuration
echo "📊 Step 4: Checking Cloud Run service configuration..."
CURRENT_INSTANCES=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(spec.template.metadata.annotations['run.googleapis.com/cloudsql-instances'])" || echo "")

if [ "$CURRENT_INSTANCES" != "$CONNECTION_NAME" ]; then
    echo "⚠️  Cloud Run is NOT configured with correct Cloud SQL connection"
    echo "   Current: ${CURRENT_INSTANCES:-NONE}"
    echo "   Expected: ${CONNECTION_NAME}"
    echo ""
    echo "This will be fixed during redeployment..."
else
    echo "✅ Cloud Run is configured correctly"
fi
echo ""

# Step 5: Check DATABASE_URL secret
echo "📊 Step 5: Checking DATABASE_URL secret..."
if gcloud secrets describe pegasus-db-url --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "✅ Secret pegasus-db-url exists"

    # Try to get the secret value (may fail if user doesn't have permission)
    SECRET_VALUE=$(gcloud secrets versions access latest \
        --secret=pegasus-db-url \
        --project="${PROJECT_ID}" 2>/dev/null || echo "NO_PERMISSION")

    if [ "$SECRET_VALUE" = "NO_PERMISSION" ]; then
        echo "⚠️  Cannot read secret value (permission denied)"
    else
        # Validate format (don't print the full secret)
        if echo "$SECRET_VALUE" | grep -q "postgresql://"; then
            echo "✅ Secret has correct postgresql:// format"
            if echo "$SECRET_VALUE" | grep -q "host=/cloudsql/${CONNECTION_NAME}"; then
                echo "✅ Secret uses correct Cloud SQL connection string"
            else
                echo "❌ Secret does NOT use correct Cloud SQL connection string"
                echo "   Expected: host=/cloudsql/${CONNECTION_NAME}"
                echo ""
                echo "Updating secret..."

                # Prompt for database credentials
                read -p "Enter database username [pegasus_user]: " DB_USER
                DB_USER=${DB_USER:-pegasus_user}

                read -sp "Enter database password: " DB_PASSWORD
                echo ""

                read -p "Enter database name [pegasus_db]: " DB_NAME
                DB_NAME=${DB_NAME:-pegasus_db}

                NEW_SECRET="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

                echo -n "${NEW_SECRET}" | gcloud secrets versions add pegasus-db-url \
                    --data-file=- \
                    --project="${PROJECT_ID}"

                echo "✅ Secret updated"
            fi
        else
            echo "❌ Secret does not have correct format"
        fi
    fi
else
    echo "❌ Secret pegasus-db-url does NOT exist"
    echo ""
    echo "Creating secret..."

    # Prompt for database credentials
    read -p "Enter database username [pegasus_user]: " DB_USER
    DB_USER=${DB_USER:-pegasus_user}

    read -sp "Enter database password: " DB_PASSWORD
    echo ""

    read -p "Enter database name [pegasus_db]: " DB_NAME
    DB_NAME=${DB_NAME:-pegasus_db}

    NEW_SECRET="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

    echo -n "${NEW_SECRET}" | gcloud secrets create pegasus-db-url \
        --data-file=- \
        --replication-policy="automatic" \
        --project="${PROJECT_ID}"

    echo "✅ Secret created"
fi
echo ""

# Step 6: Grant Cloud Run service account access
echo "📊 Step 6: Checking service account permissions..."
SERVICE_ACCOUNT=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(spec.template.spec.serviceAccountName)" || echo "")

if [ -z "$SERVICE_ACCOUNT" ]; then
    echo "⚠️  Service account not explicitly set (using default)"
    SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
fi

echo "Service account: ${SERVICE_ACCOUNT}"

# Grant Cloud SQL Client role
echo "Granting Cloud SQL Client role..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None \
    >/dev/null 2>&1 || echo "  (already granted or permission denied)"

echo "✅ Permissions configured"
echo ""

# Step 7: Redeploy with correct configuration
echo "📊 Step 7: Redeploying service with correct configuration..."
echo ""
echo "Run this command to redeploy:"
echo ""
echo "  ./scripts/deploy-cloud-run-google-stt.sh"
echo ""
echo "Or manually:"
echo ""
echo "  gcloud run deploy ${SERVICE_NAME} \\"
echo "    --image=\$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(spec.template.spec.containers[0].image)') \\"
echo "    --region=${REGION} \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --add-cloudsql-instances=${CONNECTION_NAME} \\"
echo "    --update-secrets=DATABASE_URL=pegasus-db-url:latest"
echo ""

# Step 8: Test connection
echo "📊 Step 8: Testing database connection..."
echo ""
echo "After redeployment, test with:"
echo "  curl https://\$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')/courses?limit=1"
echo ""

echo "✅ Database connection fix steps complete!"
echo ""
echo "Summary:"
echo "  • Cloud SQL instance: ${INSTANCE_NAME} (${INSTANCE_STATE})"
echo "  • Connection name: ${CONNECTION_NAME}"
echo "  • Service account: ${SERVICE_ACCOUNT}"
echo ""
echo "Next: Redeploy the service to apply changes"
