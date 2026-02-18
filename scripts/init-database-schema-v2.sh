#!/bin/bash
# Initialize Pegasus database schema (uses Cloud SQL Proxy + psql directly)

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:us-central1:pegasus-db"
DATABASE="pegasus_db"
DB_USER="pegasus_user"
PROXY_PORT=5433

echo "🗄️  Initializing Pegasus Database Schema"
echo ""
echo "Database: ${DATABASE}"
echo "User: ${DB_USER}"
echo ""

# Get password from Secret Manager
echo "🔑 Fetching database password from Secret Manager..."
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

# Start Cloud SQL Proxy in background
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
echo ""
echo "🔄 Running migrations..."
echo ""

# Run the migration SQL
PGPASSWORD="$DB_PASSWORD" psql \
    -h localhost \
    -p ${PROXY_PORT} \
    -U ${DB_USER} \
    -d ${DATABASE} <<'SQL'
-- Create tables
create table if not exists courses (
    id text primary key,
    title text not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists lectures (
    id text primary key,
    course_id text not null,
    preset_id text not null,
    title text not null,
    status text not null,
    audio_path text,
    transcript_path text,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists jobs (
    id text primary key,
    lecture_id text,
    job_type text not null,
    status text not null,
    result jsonb,
    error text,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists artifacts (
    id text primary key,
    lecture_id text not null,
    course_id text not null,
    preset_id text not null,
    artifact_type text not null,
    storage_path text not null,
    summary_overview text,
    summary_section_count integer,
    created_at timestamptz not null
);

create table if not exists threads (
    id text primary key,
    course_id text not null,
    title text not null,
    summary text not null,
    status text not null,
    complexity_level integer not null,
    lecture_refs jsonb not null,
    created_at timestamptz not null
);

create table if not exists exports (
    id text primary key,
    lecture_id text not null,
    export_type text not null,
    storage_path text not null,
    created_at timestamptz not null
);

-- Create indexes
create index if not exists jobs_lecture_id_idx on jobs (lecture_id);
create index if not exists artifacts_lecture_id_idx on artifacts (lecture_id);
create index if not exists threads_course_id_idx on threads (course_id);
create index if not exists exports_lecture_id_idx on exports (lecture_id);

-- Verify tables
\dt

-- Show success message
SELECT 'Database schema initialized successfully!' as status;
SQL

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database schema initialized successfully!"
    echo ""
    echo "📋 Tables created:"
    echo "  - courses"
    echo "  - lectures"
    echo "  - jobs"
    echo "  - artifacts"
    echo "  - threads"
    echo "  - exports"
    echo ""
    echo "🎉 Your database is ready to use!"
    echo ""
    echo "🔍 Test it:"
    echo "  curl https://pegasus-api-988514135894.us-west1.run.app/courses"
else
    echo ""
    echo "❌ Failed to initialize database schema"
    exit 1
fi
