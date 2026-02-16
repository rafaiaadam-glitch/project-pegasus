#!/bin/bash
# Run the dice rotation migration specifically

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:us-west1:planwell-db"
DATABASE="pegasus_db"
DB_USER="pegasus_user"
PROXY_PORT=5433

echo "🎲 Running Dice Rotation Migration"
echo ""

# Get password from Secret Manager
echo "🔑 Fetching database password..."
DATABASE_URL=$(gcloud secrets versions access latest \
    --secret=pegasus-db-url \
    --project=${PROJECT_ID})

# Extract password from connection string
DB_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Could not extract password from DATABASE_URL"
    exit 1
fi

echo "✅ Password retrieved"
echo ""

# Check if proxy is already running
if lsof -Pi :${PROXY_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ Cloud SQL Proxy already running on port ${PROXY_PORT}"
else
    echo "🔄 Starting Cloud SQL Proxy..."
    cloud-sql-proxy --port ${PROXY_PORT} ${INSTANCE_CONNECTION_NAME} &
    PROXY_PID=$!

    # Function to cleanup proxy on exit
    cleanup() {
        echo ""
        echo "🛑 Stopping Cloud SQL Proxy..."
        kill $PROXY_PID 2>/dev/null || true
    }
    trap cleanup EXIT

    # Give proxy time to start
    sleep 3
    echo "✅ Proxy started"
fi

echo ""
echo "🔄 Running migration: 005_add_dice_rotation.sql"
echo ""

# Run the dice rotation migration
PGPASSWORD="$DB_PASSWORD" psql \
    -h localhost \
    -p ${PROXY_PORT} \
    -U ${DB_USER} \
    -d ${DATABASE} \
    -f backend/migrations/005_add_dice_rotation.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dice rotation migration applied successfully!"
    echo ""
    echo "🔍 Verifying table..."
    PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost \
        -p ${PROXY_PORT} \
        -U ${DB_USER} \
        -d ${DATABASE} \
        -c "\d dice_rotation_states"
    echo ""
    echo "🎉 Migration complete!"
else
    echo ""
    echo "❌ Failed to apply migration"
    exit 1
fi
