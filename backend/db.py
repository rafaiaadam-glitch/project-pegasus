from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor


@dataclass(frozen=True)
class Database:
    dsn: str

    def connect(self):
        return psycopg2.connect(self.dsn)

    def migrate(self) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
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
                    """
                )
                cur.execute(
                    """
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
                    """
                )

    def upsert_lecture(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into lectures (
                        id, course_id, preset_id, title, status, audio_path,
                        transcript_path, created_at, updated_at
                    ) values (
                        %(id)s, %(course_id)s, %(preset_id)s, %(title)s, %(status)s,
                        %(audio_path)s, %(transcript_path)s, %(created_at)s, %(updated_at)s
                    )
                    on conflict (id) do update set
                        course_id = excluded.course_id,
                        preset_id = excluded.preset_id,
                        title = excluded.title,
                        status = excluded.status,
                        audio_path = excluded.audio_path,
                        transcript_path = excluded.transcript_path,
                        updated_at = excluded.updated_at;
                    """,
                    payload,
                )

    def fetch_lecture(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("select * from lectures where id = %s;", (lecture_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def create_job(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into jobs (
                        id, lecture_id, job_type, status, result, error,
                        created_at, updated_at
                    ) values (
                        %(id)s, %(lecture_id)s, %(job_type)s, %(status)s, %(result)s,
                        %(error)s, %(created_at)s, %(updated_at)s
                    );
                    """,
                    {
                        **payload,
                        "result": Json(payload.get("result")),
                    },
                )

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> None:
        updates = []
        params: Dict[str, Any] = {"id": job_id}
        if status is not None:
            updates.append("status = %(status)s")
            params["status"] = status
        if result is not None:
            updates.append("result = %(result)s")
            params["result"] = Json(result)
        if error is not None:
            updates.append("error = %(error)s")
            params["error"] = error
        if updated_at is not None:
            updates.append("updated_at = %(updated_at)s")
            params["updated_at"] = updated_at
        if not updates:
            return
        set_clause = ", ".join(updates)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"update jobs set {set_clause} where id = %(id)s;", params)

    def fetch_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("select * from jobs where id = %s;", (job_id,))
                row = cur.fetchone()
                return dict(row) if row else None


def get_database() -> Database:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL must be set for database access.")
    db = Database(dsn=dsn)
    db.migrate()
    return db
