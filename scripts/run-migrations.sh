#!/bin/bash
# Run database migrations for Pegasus
# This script connects to Cloud SQL and runs pending migrations

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
INSTANCE_NAME="${INSTANCE_NAME:-planwell-db}"
DATABASE="${DATABASE:-pegasus_db}"
DB_USER="${DB_USER:-pegasus_user}"

echo "🗄️  Running Pegasus Database Migrations"
echo "Project: ${PROJECT_ID}"
echo "Instance: ${INSTANCE_NAME}"
echo "Database: ${DATABASE}"
echo "User: ${DB_USER}"
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if Cloud SQL Proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "❌ Cloud SQL Proxy not found. Installing..."
    gcloud components install cloud-sql-proxy --quiet
fi

echo "📋 Migration files to run:"
ls -1 backend/migrations/*.sql

echo ""
echo "🔄 Starting Cloud SQL Proxy..."

# Start proxy in background
cloud-sql-proxy --port 5432 "${PROJECT_ID}:us-central1:${INSTANCE_NAME}" &
PROXY_PID=$!

# Give proxy time to start
sleep 3

# Function to cleanup proxy on exit
cleanup() {
    echo ""
    echo "🛑 Stopping Cloud SQL Proxy..."
    kill $PROXY_PID 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "🚀 Running migrations..."
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo "❌ psql not found. Please install PostgreSQL client:"
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

# Prompt for password
echo "Enter password for ${DB_USER}:"
read -s DB_PASSWORD

# Run each migration file
for migration_file in backend/migrations/*.sql; do
    echo "📝 Running: $(basename $migration_file)"

    PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p 5432 \
        -U "$DB_USER" \
        -d "$DATABASE" \
        -f "$migration_file"

    if [ $? -eq 0 ]; then
        echo "✅ Successfully ran: $(basename $migration_file)"
    else
        echo "❌ Failed to run: $(basename $migration_file)"
        exit 1
    fi
    echo ""
done

echo ""
echo "✅ All migrations completed successfully!"
echo ""
echo "🔍 Verifying tables..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h localhost \
    -p 5432 \
    -U "$DB_USER" \
    -d "$DATABASE" \
    -c "\dt"

echo ""
echo "🎉 Database schema is ready!"
