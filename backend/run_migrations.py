#!/usr/bin/env python3
"""
Run database migrations for Pegasus
Can be executed as a Cloud Run job or locally
"""

import os
import sys
from pathlib import Path

import psycopg2


def get_database_url() -> str:
    """Get database URL from environment or Secret Manager"""
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        # Try to get from Secret Manager
        try:
            from google.cloud import secretmanager

            project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0822836147")
            client = secretmanager.SecretManagerServiceClient()
            secret_name = f"projects/{project_id}/secrets/pegasus-db-url/versions/latest"
            response = client.access_secret_version(request={"name": secret_name})
            db_url = response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"❌ Failed to get database URL: {e}")
            sys.exit(1)

    return db_url


def run_migration(cursor, migration_file: Path):
    """Run a single migration file"""
    print(f"📝 Running: {migration_file.name}")

    try:
        sql = migration_file.read_text()
        cursor.execute(sql)
        print(f"✅ Successfully ran: {migration_file.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to run {migration_file.name}: {e}")
        return False


def main():
    print("🗄️  Running Pegasus Database Migrations")
    print("")

    # Get database URL
    db_url = get_database_url()
    print(f"📡 Connecting to database...")

    # Connect to database
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Connected successfully")
        print("")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Find migration files
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("⚠️  No migration files found")
        sys.exit(0)

    print(f"📋 Found {len(migration_files)} migration(s):")
    for f in migration_files:
        print(f"  - {f.name}")
    print("")

    # Run migrations
    success_count = 0
    for migration_file in migration_files:
        if run_migration(cursor, migration_file):
            success_count += 1
            conn.commit()
        else:
            conn.rollback()
            print("❌ Migration failed, rolling back...")
            sys.exit(1)
        print("")

    # Verify tables
    print("🔍 Verifying tables...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()

    if tables:
        print("✅ Tables created:")
        for (table_name,) in tables:
            print(f"  - {table_name}")
    else:
        print("⚠️  No tables found")

    cursor.close()
    conn.close()

    print("")
    print(f"🎉 Successfully ran {success_count}/{len(migration_files)} migration(s)!")
    print("✅ Database schema is ready!")


if __name__ == "__main__":
    main()
