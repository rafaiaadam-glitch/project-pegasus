#!/bin/bash
set -e

PROJECT_ID="delta-student-486911-n5"
REGION="us-central1"
DB_INSTANCE="pegasus-db"
DB_NAME="pegasus"
DB_USER="pegasus"
BUCKET_NAME="${PROJECT_ID}-pegasus-storage"

echo "🚀 Setting up Pegasus on GCP"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📦 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# Create Cloud SQL instance
echo "🗄️  Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create $DB_INSTANCE \
  --database-version=POSTGRES_16 \
  --tier=db-n1-standard-1 \
  --region=$REGION \
  --database-flags=max_connections=100 \
  --project=$PROJECT_ID \
  || echo "Instance may already exist"

# Create database and user
echo "👤 Creating database and user..."
gcloud sql databases create $DB_NAME \
  --instance=$DB_INSTANCE \
  --project=$PROJECT_ID \
  || echo "Database may already exist"

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32)

gcloud sql users create $DB_USER \
  --instance=$DB_INSTANCE \
  --password=$DB_PASSWORD \
  --project=$PROJECT_ID \
  || echo "User may already exist"

# Store database password in Secret Manager
echo "🔐 Storing database password in Secret Manager..."
echo -n "$DB_PASSWORD" | gcloud secrets create pegasus-db-password \
  --data-file=- \
  --replication-policy="automatic" \
  --project=$PROJECT_ID \
  || echo "Secret may already exist"

# Create Cloud Storage bucket
echo "💾 Creating Cloud Storage bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/ \
  || echo "Bucket may already exist"

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME \
  || echo "Permissions may already be set"

# Build and deploy to Cloud Run
echo "🏗️  Building and deploying to Cloud Run..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=$PROJECT_ID

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Environment Variables:"
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@/pegasus?host=/cloudsql/$PROJECT_ID:$REGION:$DB_INSTANCE"
echo "STORAGE_MODE=gcs"
echo "GCS_BUCKET=$BUCKET_NAME"
echo ""
echo "🌐 Your API will be available at:"
gcloud run services describe pegasus-api --region=$REGION --project=$PROJECT_ID --format='value(status.url)' || echo "Deploy pending..."
