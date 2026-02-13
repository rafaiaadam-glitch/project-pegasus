from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor


@dataclass(frozen=True)
class Database:
    dsn: str

    def connect(self):
        return psycopg2.connect(self.dsn)

    def healthcheck(self) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select 1;")
                cur.fetchone()

    def migrate(self) -> None:
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        migrations = sorted(migrations_dir.glob("*.sql"))
        if not migrations:
            return
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists schema_migrations (
                        id text primary key,
                        applied_at timestamptz not null default now()
                    );
                    """
                )
                cur.execute("select id from schema_migrations order by id;")
                applied = {row[0] for row in cur.fetchall()}
                for migration in migrations:
                    migration_id = migration.name
                    if migration_id in applied:
                        continue
                    sql = migration.read_text(encoding="utf-8")
                    cur.execute(sql)
                    cur.execute(
                        "insert into schema_migrations (id) values (%s);",
                        (migration_id,),
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

    def fetch_lectures(
        self,
        course_id: Optional[str] = None,
        status: Optional[str] = None,
        preset_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        clauses = []
        params: Dict[str, Any] = {}
        if course_id:
            clauses.append("course_id = %(course_id)s")
            params["course_id"] = course_id
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        if preset_id:
            clauses.append("preset_id = %(preset_id)s")
            params["preset_id"] = preset_id
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"select * from lectures{where_clause} order by created_at desc{limit_clause};",
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_lectures(
        self,
        course_id: Optional[str] = None,
        status: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> int:
        clauses = []
        params: Dict[str, Any] = {}
        if course_id:
            clauses.append("course_id = %(course_id)s")
            params["course_id"] = course_id
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        if preset_id:
            clauses.append("preset_id = %(preset_id)s")
            params["preset_id"] = preset_id
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select count(*) from lectures{where_clause};", params)
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def upsert_course(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into courses (
                        id, title, created_at, updated_at
                    ) values (
                        %(id)s, %(title)s, %(created_at)s, %(updated_at)s
                    )
                    on conflict (id) do update set
                        title = excluded.title,
                        updated_at = excluded.updated_at;
                    """,
                    payload,
                )

    def fetch_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("select * from courses where id = %s;", (course_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def fetch_courses(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        limit_clause = ""
        params: Dict[str, Any] = {}
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"select * from courses order by created_at desc{limit_clause};",
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_courses(self) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select count(*) from courses;")
                row = cur.fetchone()
                return int(row[0]) if row else 0

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

    def fetch_jobs(
        self,
        lecture_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        clauses = []
        params: Dict[str, Any] = {}
        if lecture_id:
            clauses.append("lecture_id = %(lecture_id)s")
            params["lecture_id"] = lecture_id
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"select * from jobs{where_clause} order by created_at desc{limit_clause};",
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_jobs(self, lecture_id: Optional[str] = None, status: Optional[str] = None) -> int:
        clauses = []
        params: Dict[str, Any] = {}
        if lecture_id:
            clauses.append("lecture_id = %(lecture_id)s")
            params["lecture_id"] = lecture_id
        if status:
            clauses.append("status = %(status)s")
            params["status"] = status
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select count(*) from jobs{where_clause};", params)
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def upsert_artifact(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into artifacts (
                        id, lecture_id, course_id, preset_id, artifact_type,
                        storage_path, summary_overview, summary_section_count, created_at
                    ) values (
                        %(id)s, %(lecture_id)s, %(course_id)s, %(preset_id)s,
                        %(artifact_type)s, %(storage_path)s, %(summary_overview)s,
                        %(summary_section_count)s, %(created_at)s
                    )
                    on conflict (id) do update set
                        storage_path = excluded.storage_path,
                        summary_overview = excluded.summary_overview,
                        summary_section_count = excluded.summary_section_count;
                    """,
                    payload,
                )

    def fetch_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        clauses = ["lecture_id = %(lecture_id)s"]
        params: Dict[str, Any] = {"lecture_id": lecture_id}
        if artifact_type:
            clauses.append("artifact_type = %(artifact_type)s")
            params["artifact_type"] = artifact_type
        if preset_id:
            clauses.append("preset_id = %(preset_id)s")
            params["preset_id"] = preset_id
        where_clause = " and ".join(clauses)
        limit_clause = ""
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"select * from artifacts where {where_clause} order by artifact_type{limit_clause};",
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> int:
        clauses = ["lecture_id = %(lecture_id)s"]
        params: Dict[str, Any] = {"lecture_id": lecture_id}
        if artifact_type:
            clauses.append("artifact_type = %(artifact_type)s")
            params["artifact_type"] = artifact_type
        if preset_id:
            clauses.append("preset_id = %(preset_id)s")
            params["preset_id"] = preset_id
        where_clause = " and ".join(clauses)
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select count(*) from artifacts where {where_clause};", params)
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def upsert_thread(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into threads (
                        id, course_id, title, summary, status, complexity_level,
                        lecture_refs, created_at
                    ) values (
                        %(id)s, %(course_id)s, %(title)s, %(summary)s, %(status)s,
                        %(complexity_level)s, %(lecture_refs)s, %(created_at)s
                    )
                    on conflict (id) do update set
                        title = excluded.title,
                        summary = excluded.summary,
                        status = excluded.status,
                        complexity_level = excluded.complexity_level,
                        lecture_refs = excluded.lecture_refs;
                    """,
                    {
                        **payload,
                        "lecture_refs": Json(payload.get("lecture_refs")),
                    },
                )

    def fetch_threads(self, lecture_id: str) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    select * from threads
                    where lecture_refs @> %s
                    order by created_at desc;
                    """,
                    (Json([lecture_id]),),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def fetch_threads_for_course(
        self,
        course_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        limit_clause = ""
        params: Dict[str, Any] = {"course_id": course_id}
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    select * from threads
                    where course_id = %(course_id)s
                    order by created_at desc{limit_clause};
                    """,
                    params,
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def count_threads_for_course(self, course_id: str) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select count(*) from threads
                    where course_id = %s;
                    """,
                    (course_id,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def upsert_export(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into exports (
                        id, lecture_id, export_type, storage_path, created_at
                    ) values (
                        %(id)s, %(lecture_id)s, %(export_type)s, %(storage_path)s,
                        %(created_at)s
                    )
                    on conflict (id) do update set
                        storage_path = excluded.storage_path;
                    """,
                    payload,
                )

    def fetch_exports(self, lecture_id: str) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "select * from exports where lecture_id = %s order by export_type;",
                    (lecture_id,),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def update_thread_lecture_refs(self, thread_id: str, lecture_refs: list[str]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update threads
                    set lecture_refs = %s
                    where id = %s;
                    """,
                    (Json(lecture_refs), thread_id),
                )

    def delete_thread(self, thread_id: str) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from threads where id = %s;", (thread_id,))

    def delete_lecture_records(self, lecture_id: str) -> dict[str, int]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from artifacts where lecture_id = %s;", (lecture_id,))
                artifacts_deleted = cur.rowcount
                cur.execute("delete from exports where lecture_id = %s;", (lecture_id,))
                exports_deleted = cur.rowcount
                cur.execute("delete from jobs where lecture_id = %s;", (lecture_id,))
                jobs_deleted = cur.rowcount
                cur.execute("delete from lectures where id = %s;", (lecture_id,))
                lectures_deleted = cur.rowcount
                return {
                    "artifacts": artifacts_deleted,
                    "exports": exports_deleted,
                    "jobs": jobs_deleted,
                    "lectures": lectures_deleted,
                }

    def delete_course(self, course_id: str) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from courses where id = %s;", (course_id,))
                return cur.rowcount


def get_database() -> Database:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL must be set for database access.")
    db = Database(dsn=dsn)
    db.migrate()
    return db
