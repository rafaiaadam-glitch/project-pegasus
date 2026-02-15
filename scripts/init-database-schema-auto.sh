#!/bin/bash
# Initialize Pegasus database schema (automatic - fetches password from Secret Manager)

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-delta-student-486911-n5}"
INSTANCE_NAME="planwell-db"
DATABASE="pegasus_db"
DB_USER="pegasus_user"

echo "🗄️  Initializing Pegasus Database Schema"
echo ""
echo "Database: ${DATABASE}"
echo "User: ${DB_USER}"
echo "Instance: ${INSTANCE_NAME}"
echo ""

# Get password from Secret Manager
echo "🔑 Fetching database password from Secret Manager..."
DB_PASSWORD=$(gcloud secrets versions access latest \
    --secret=pegasus-db-password \
    --project=${PROJECT_ID} 2>/dev/null || echo "")

if [ -z "$DB_PASSWORD" ]; then
    echo "⚠️  Secret not found. Trying to extract from DATABASE_URL..."
    DATABASE_URL=$(gcloud secrets versions access latest \
        --secret=pegasus-db-url \
        --project=${PROJECT_ID})

    # Extract password from connection string
    # Format: postgresql://user:password@/db or postgresql://user:password@host/db
    DB_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Could not fetch password from Secret Manager"
    echo "Please run: ./scripts/init-database-schema.sh (with interactive password prompt)"
    exit 1
fi

echo "✅ Password retrieved"
echo ""
echo "🔄 Running migrations..."
echo ""

# Run the migration SQL
PGPASSWORD="$DB_PASSWORD" gcloud sql connect ${INSTANCE_NAME} \
    --user=${DB_USER} \
    --database=${DATABASE} \
    --project=${PROJECT_ID} \
    --quiet <<'SQL'
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
