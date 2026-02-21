from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Database:
    dsn: str

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True)

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
                applied = {row["id"] for row in cur.fetchall()}
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
                        transcript_path, source_type, created_at, updated_at
                    ) values (
                        %(id)s, %(course_id)s, %(preset_id)s, %(title)s, %(status)s,
                        %(audio_path)s, %(transcript_path)s, %(source_type)s, %(created_at)s, %(updated_at)s
                    )
                    on conflict (id) do update set
                        course_id = excluded.course_id,
                        preset_id = excluded.preset_id,
                        title = excluded.title,
                        status = excluded.status,
                        audio_path = excluded.audio_path,
                        transcript_path = excluded.transcript_path,
                        source_type = excluded.source_type,
                        updated_at = excluded.updated_at;
                    """,
                    payload,
                )

    def fetch_lecture(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select * from lectures where id = %s;", (lecture_id,))
                return cur.fetchone()

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
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from lectures{where_clause} order by created_at desc{limit_clause};",
                    params,
                )
                return cur.fetchall()

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
                return int(list(row.values())[0]) if row else 0

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
            with conn.cursor() as cur:
                cur.execute("select * from courses where id = %s;", (course_id,))
                return cur.fetchone()

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
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from courses order by created_at desc{limit_clause};",
                    params,
                )
                return cur.fetchall()

    def count_courses(self) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select count(*) from courses;")
                row = cur.fetchone()
                return int(list(row.values())[0]) if row else 0

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
                        "result": Jsonb(payload.get("result")),
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
            params["result"] = Jsonb(result)
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
            with conn.cursor() as cur:
                cur.execute("select * from jobs where id = %s;", (job_id,))
                return cur.fetchone()

    def fetch_jobs(
        self,
        lecture_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        clauses = []
        params: Dict[str, Any] = {}
        if lecture_id:
            clauses.append("lecture_id = %(lecture_id)s")
            params["lecture_id"] = lecture_id
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from jobs{where_clause} order by created_at desc{limit_clause};",
                    params,
                )
                return cur.fetchall()

    def count_jobs(self, lecture_id: Optional[str] = None) -> int:
        clauses = []
        params: Dict[str, Any] = {}
        if lecture_id:
            clauses.append("lecture_id = %(lecture_id)s")
            params["lecture_id"] = lecture_id
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select count(*) from jobs{where_clause};", params)
                row = cur.fetchone()
                return int(list(row.values())[0]) if row else 0

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
            with conn.cursor() as cur:
                cur.execute(
                    f"select * from artifacts where {where_clause} order by artifact_type{limit_clause};",
                    params,
                )
                return cur.fetchall()

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
                return int(list(row.values())[0]) if row else 0

    def fetch_action_items(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        limit_clause = ""
        params: Dict[str, Any] = {"artifact_type": "action-items"}
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    select a.*, l.title as lecture_title, c.title as course_title
                    from artifacts a
                    join lectures l on a.lecture_id = l.id
                    left join courses c on a.course_id = c.id
                    where a.artifact_type = %(artifact_type)s
                    order by a.created_at desc{limit_clause};
                    """,
                    params,
                )
                return cur.fetchall()

    def upsert_thread(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into threads (
                        id, course_id, title, summary, status, complexity_level,
                        lecture_refs, face, evolution_notes, created_at
                    ) values (
                        %(id)s, %(course_id)s, %(title)s, %(summary)s, %(status)s,
                        %(complexity_level)s, %(lecture_refs)s, %(face)s, %(evolution_notes)s, %(created_at)s
                    )
                    on conflict (id) do update set
                        title = excluded.title,
                        summary = excluded.summary,
                        status = excluded.status,
                        complexity_level = excluded.complexity_level,
                        lecture_refs = excluded.lecture_refs,
                        face = excluded.face,
                        evolution_notes = excluded.evolution_notes;
                    """,
                    {
                        **payload,
                        "lecture_refs": Jsonb(payload.get("lecture_refs")),
                        "face": payload.get("face"),
                        "evolution_notes": Jsonb(payload.get("evolution_notes")) if payload.get("evolution_notes") else None,
                    },
                )

    def fetch_threads(self, lecture_id: str) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select * from threads
                    where lecture_refs @> %s
                    order by created_at desc;
                    """,
                    (Jsonb([lecture_id]),),
                )
                return cur.fetchall()

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
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    select * from threads
                    where course_id = %(course_id)s
                    order by created_at desc{limit_clause};
                    """,
                    params,
                )
                return cur.fetchall()

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
                return int(list(row.values())[0]) if row else 0

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
            with conn.cursor() as cur:
                cur.execute(
                    "select * from exports where lecture_id = %s order by export_type;",
                    (lecture_id,),
                )
                return cur.fetchall()

    def update_thread_lecture_refs(self, thread_id: str, lecture_refs: list[str]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update threads
                    set lecture_refs = %s
                    where id = %s;
                    """,
                    (Jsonb(lecture_refs), thread_id),
                )

    def delete_thread(self, thread_id: str) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from threads where id = %s;", (thread_id,))

    def delete_threads_for_lecture(self, lecture_id: str) -> int:
        """Delete all threads that reference the given lecture. Returns count deleted."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "delete from threads where lecture_refs @> %s returning id;",
                    (Jsonb([lecture_id]),),
                )
                return len(cur.fetchall())

    def fetch_thread_by_id(self, thread_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select * from threads where id = %s;", (thread_id,))
                return cur.fetchone()

    def insert_thread_occurrences(self, occurrences: list[Dict[str, Any]]) -> int:
        if not occurrences:
            return 0
        with self.connect() as conn:
            with conn.cursor() as cur:
                inserted = 0
                for occ in occurrences:
                    cur.execute(
                        """
                        insert into thread_occurrences (
                            id, thread_id, course_id, lecture_id, artifact_id,
                            evidence, confidence, captured_at
                        ) values (
                            %(id)s, %(thread_id)s, %(course_id)s, %(lecture_id)s,
                            %(artifact_id)s, %(evidence)s, %(confidence)s, %(captured_at)s
                        ) on conflict (id) do nothing;
                        """,
                        occ,
                    )
                    inserted += cur.rowcount
                return inserted

    def insert_thread_updates(self, updates: list[Dict[str, Any]]) -> int:
        if not updates:
            return 0
        with self.connect() as conn:
            with conn.cursor() as cur:
                inserted = 0
                for upd in updates:
                    cur.execute(
                        """
                        insert into thread_updates (
                            id, thread_id, course_id, lecture_id, change_type,
                            summary, details, captured_at
                        ) values (
                            %(id)s, %(thread_id)s, %(course_id)s, %(lecture_id)s,
                            %(change_type)s, %(summary)s, %(details)s, %(captured_at)s
                        ) on conflict (id) do nothing;
                        """,
                        {
                            **upd,
                            "details": Jsonb(upd.get("details")) if upd.get("details") else None,
                        },
                    )
                    inserted += cur.rowcount
                return inserted

    def fetch_thread_occurrences(self, thread_id: str) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select o.*, l.title as lecture_title
                    from thread_occurrences o
                    left join lectures l on o.lecture_id = l.id
                    where o.thread_id = %s
                    order by o.captured_at asc;
                    """,
                    (thread_id,),
                )
                return cur.fetchall()

    def fetch_thread_updates_for_thread(self, thread_id: str) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select u.*, l.title as lecture_title
                    from thread_updates u
                    left join lectures l on u.lecture_id = l.id
                    where u.thread_id = %s
                    order by u.captured_at asc;
                    """,
                    (thread_id,),
                )
                return cur.fetchall()

    def delete_thread_occurrences_for_lecture(self, lecture_id: str) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "delete from thread_occurrences where lecture_id = %s;",
                    (lecture_id,),
                )
                return cur.rowcount

    def delete_thread_updates_for_lecture(self, lecture_id: str) -> int:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "delete from thread_updates where lecture_id = %s;",
                    (lecture_id,),
                )
                return cur.rowcount

    def update_lecture_storage_paths(
        self,
        lecture_id: str,
        *,
        audio_path: Optional[str],
        transcript_path: Optional[str],
        updated_at: str,
    ) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update lectures
                    set audio_path = %s,
                        transcript_path = %s,
                        updated_at = %s
                    where id = %s;
                    """,
                    (audio_path, transcript_path, updated_at, lecture_id),
                )

    def delete_lecture_records(self, lecture_id: str) -> dict[str, int]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from thread_occurrences where lecture_id = %s;", (lecture_id,))
                cur.execute("delete from thread_updates where lecture_id = %s;", (lecture_id,))
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

    # =========================================================================
    # Users (Auth)
    # =========================================================================

    def create_user(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, display_name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, email, display_name, created_at, updated_at;
                    """,
                    (user_id, email, password_hash, display_name, now, now),
                )
                return cur.fetchone()

    def fetch_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash, display_name, created_at, updated_at FROM users WHERE email = %s;",
                    (email,),
                )
                return cur.fetchone()

    def fetch_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, display_name, auth_provider, created_at, updated_at FROM users WHERE id = %s;",
                    (user_id,),
                )
                return cur.fetchone()

    def find_or_create_oauth_user(
        self,
        user_id: str,
        email: str,
        auth_provider: str,
        provider_user_id: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, display_name, auth_provider, provider_user_id, created_at, updated_at)
                    VALUES (%s, %s, NULL, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET
                        auth_provider = EXCLUDED.auth_provider,
                        provider_user_id = EXCLUDED.provider_user_id,
                        display_name = COALESCE(NULLIF(EXCLUDED.display_name, ''), users.display_name),
                        updated_at = EXCLUDED.updated_at
                    RETURNING id, email, display_name, auth_provider, created_at, updated_at;
                    """,
                    (user_id, email, display_name, auth_provider, provider_user_id, now, now),
                )
                return cur.fetchone()

    # =========================================================================
    # Credit Ledger
    # =========================================================================

    def insert_credit_entry(
        self,
        entry_id: str,
        user_id: str,
        lecture_id: str,
        job_id: str,
        llm_provider: str,
        llm_model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO credit_ledger (
                        id, user_id, lecture_id, job_id,
                        llm_provider, llm_model,
                        prompt_tokens, completion_tokens, total_tokens,
                        estimated_cost_usd
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        entry_id, user_id, lecture_id, job_id,
                        llm_provider, llm_model,
                        prompt_tokens, completion_tokens, total_tokens,
                        estimated_cost_usd,
                    ),
                )

    def fetch_user_credits_summary(self, user_id: str) -> Dict[str, Any]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Total usage
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(prompt_tokens), 0) AS total_prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) AS total_completion_tokens,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd,
                        COUNT(*) AS generation_count
                    FROM credit_ledger WHERE user_id = %s;
                    """,
                    (user_id,),
                )
                totals = cur.fetchone()

                # Per-model breakdown
                cur.execute(
                    """
                    SELECT
                        llm_model,
                        COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(estimated_cost_usd), 0) AS cost_usd,
                        COUNT(*) AS count
                    FROM credit_ledger WHERE user_id = %s
                    GROUP BY llm_model ORDER BY cost_usd DESC;
                    """,
                    (user_id,),
                )
                per_model = cur.fetchall()

        return {
            "totalPromptTokens": totals["total_prompt_tokens"],
            "totalCompletionTokens": totals["total_completion_tokens"],
            "totalTokens": totals["total_tokens"],
            "totalCostUsd": round(float(totals["total_cost_usd"]), 6),
            "generationCount": totals["generation_count"],
            "perModel": [
                {
                    "model": row["llm_model"],
                    "promptTokens": row["prompt_tokens"],
                    "completionTokens": row["completion_tokens"],
                    "totalTokens": row["total_tokens"],
                    "costUsd": round(float(row["cost_usd"]), 6),
                    "count": row["count"],
                }
                for row in per_model
            ],
        }

    def fetch_user_credit_history(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, lecture_id, job_id, llm_provider, llm_model,
                           prompt_tokens, completion_tokens, total_tokens,
                           estimated_cost_usd, created_at
                    FROM credit_ledger
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (user_id, limit, offset),
                )
                rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "lectureId": row["lecture_id"],
                "jobId": row["job_id"],
                "llmProvider": row["llm_provider"],
                "llmModel": row["llm_model"],
                "promptTokens": row["prompt_tokens"],
                "completionTokens": row["completion_tokens"],
                "totalTokens": row["total_tokens"],
                "estimatedCostUsd": round(float(row["estimated_cost_usd"]), 6),
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    # =========================================================================
    # Token Balance
    # =========================================================================

    FREE_MONTHLY_TOKENS = int(os.getenv("PLC_FREE_MONTHLY_TOKENS", "100000"))

    def _connect_transactional(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, autocommit=False)

    def get_user_token_balance(self, user_id: str) -> Dict[str, Any]:
        with self._connect_transactional() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT free_token_balance, purchased_token_balance, free_tokens_reset_at FROM users WHERE id = %s FOR UPDATE;",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"User {user_id} not found")

                # Lazy monthly reset: if 30+ days since last reset, grant fresh free tokens
                reset_at = row["free_tokens_reset_at"]
                now = datetime.now(timezone.utc)
                if reset_at and (now - reset_at).days >= 30:
                    cur.execute(
                        """
                        UPDATE users
                        SET free_token_balance = %s, free_tokens_reset_at = %s
                        WHERE id = %s;
                        """,
                        (self.FREE_MONTHLY_TOKENS, now, user_id),
                    )
                    # Log the reset
                    txn_id = str(__import__("uuid").uuid4())
                    cur.execute(
                        """
                        INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                            balance_after_free, balance_after_purchased, reference_id, description, created_at)
                        VALUES (%s, %s, 'free_grant', %s, %s, %s, NULL, 'Monthly free token reset', %s);
                        """,
                        (txn_id, user_id, self.FREE_MONTHLY_TOKENS,
                         self.FREE_MONTHLY_TOKENS, row["purchased_token_balance"], now),
                    )
                    conn.commit()
                    return {
                        "freeBalance": self.FREE_MONTHLY_TOKENS,
                        "purchasedBalance": row["purchased_token_balance"],
                        "totalBalance": self.FREE_MONTHLY_TOKENS + row["purchased_token_balance"],
                        "freeResetsAt": (now.isoformat()),
                        "freeMonthlyAllowance": self.FREE_MONTHLY_TOKENS,
                    }

                conn.commit()
                free = row["free_token_balance"]
                purchased = row["purchased_token_balance"]
                return {
                    "freeBalance": free,
                    "purchasedBalance": purchased,
                    "totalBalance": free + purchased,
                    "freeResetsAt": reset_at.isoformat() if reset_at else None,
                    "freeMonthlyAllowance": self.FREE_MONTHLY_TOKENS,
                }

    def check_and_reserve_tokens(self, user_id: str, estimated_tokens: int) -> Dict[str, Any]:
        with self._connect_transactional() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT free_token_balance, purchased_token_balance FROM users WHERE id = %s FOR UPDATE;",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "error": "user_not_found"}

                free = row["free_token_balance"]
                purchased = row["purchased_token_balance"]
                total = free + purchased

                if total < estimated_tokens:
                    conn.rollback()
                    return {
                        "ok": False,
                        "available": total,
                        "required": estimated_tokens,
                    }

                # Deduct free first, then purchased
                deduct_free = min(free, estimated_tokens)
                deduct_purchased = estimated_tokens - deduct_free
                new_free = free - deduct_free
                new_purchased = purchased - deduct_purchased

                cur.execute(
                    """
                    UPDATE users
                    SET free_token_balance = %s, purchased_token_balance = %s
                    WHERE id = %s;
                    """,
                    (new_free, new_purchased, user_id),
                )

                txn_id = str(__import__("uuid").uuid4())
                now = datetime.now(timezone.utc)
                cur.execute(
                    """
                    INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                        balance_after_free, balance_after_purchased, reference_id, description, created_at)
                    VALUES (%s, %s, 'generation_reserve', %s, %s, %s, NULL, 'Token reservation for generation', %s);
                    """,
                    (txn_id, user_id, -estimated_tokens, new_free, new_purchased, now),
                )
                conn.commit()
                return {
                    "ok": True,
                    "reserved": estimated_tokens,
                    "deductedFree": deduct_free,
                    "deductedPurchased": deduct_purchased,
                    "balanceAfterFree": new_free,
                    "balanceAfterPurchased": new_purchased,
                }

    def deduct_tokens(
        self,
        user_id: str,
        actual_tokens: int,
        estimated_tokens: int,
        reference_id: str,
        description: str = "Generation token reconciliation",
    ) -> None:
        refund = estimated_tokens - actual_tokens
        if refund <= 0:
            # Actual usage >= estimate, no refund needed. Log final deduction.
            with self.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT free_token_balance, purchased_token_balance FROM users WHERE id = %s;",
                        (user_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        txn_id = str(__import__("uuid").uuid4())
                        cur.execute(
                            """
                            INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                                balance_after_free, balance_after_purchased, reference_id, description, created_at)
                            VALUES (%s, %s, 'generation_deduct', %s, %s, %s, %s, %s, NOW());
                            """,
                            (txn_id, user_id, -actual_tokens, row["free_token_balance"],
                             row["purchased_token_balance"], reference_id, description),
                        )
            return

        # Refund over-reservation back to purchased_token_balance
        with self._connect_transactional() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET purchased_token_balance = purchased_token_balance + %s
                    WHERE id = %s;
                    """,
                    (refund, user_id),
                )
                cur.execute(
                    "SELECT free_token_balance, purchased_token_balance FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = cur.fetchone()
                txn_id = str(__import__("uuid").uuid4())
                cur.execute(
                    """
                    INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                        balance_after_free, balance_after_purchased, reference_id, description, created_at)
                    VALUES (%s, %s, 'generation_refund', %s, %s, %s, %s, %s, NOW());
                    """,
                    (txn_id, user_id, refund, row["free_token_balance"],
                     row["purchased_token_balance"], reference_id,
                     f"Refund {refund} tokens (estimated {estimated_tokens}, actual {actual_tokens})"),
                )
                conn.commit()

    def refund_reserved_tokens(self, user_id: str, estimated_tokens: int, reference_id: str) -> None:
        with self._connect_transactional() as conn:
            with conn.cursor() as cur:
                # Refund to purchased balance (simplest — user keeps their free tokens priority)
                cur.execute(
                    """
                    UPDATE users
                    SET purchased_token_balance = purchased_token_balance + %s
                    WHERE id = %s;
                    """,
                    (estimated_tokens, user_id),
                )
                cur.execute(
                    "SELECT free_token_balance, purchased_token_balance FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = cur.fetchone()
                txn_id = str(__import__("uuid").uuid4())
                cur.execute(
                    """
                    INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                        balance_after_free, balance_after_purchased, reference_id, description, created_at)
                    VALUES (%s, %s, 'generation_refund', %s, %s, %s, %s, 'Full refund — generation failed', NOW());
                    """,
                    (txn_id, user_id, estimated_tokens, row["free_token_balance"],
                     row["purchased_token_balance"], reference_id),
                )
                conn.commit()

    def fetch_user_token_transactions(
        self, user_id: str, limit: int = 20, offset: int = 0,
    ) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, transaction_type, token_amount, balance_after_free,
                           balance_after_purchased, reference_id, description, created_at
                    FROM token_transactions
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (user_id, limit, offset),
                )
                rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "transactionType": r["transaction_type"],
                "tokenAmount": r["token_amount"],
                "balanceAfterFree": r["balance_after_free"],
                "balanceAfterPurchased": r["balance_after_purchased"],
                "referenceId": r["reference_id"],
                "description": r["description"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]

    # =========================================================================
    # Purchase Receipts
    # =========================================================================

    def insert_purchase_receipt(
        self,
        receipt_id: str,
        user_id: str,
        platform: str,
        product_id: str,
        transaction_id: str,
        receipt_data: str,
        tokens_granted: int,
        price_usd: float,
    ) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO purchase_receipts (id, user_id, platform, product_id,
                        transaction_id, receipt_data, tokens_granted, price_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO NOTHING;
                    """,
                    (receipt_id, user_id, platform, product_id,
                     transaction_id, receipt_data, tokens_granted, price_usd),
                )

    def fetch_purchase_receipt_by_txn_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM purchase_receipts WHERE transaction_id = %s;",
                    (transaction_id,),
                )
                return cur.fetchone()

    def grant_purchased_tokens(self, user_id: str, tokens: int, purchase_id: str) -> Dict[str, Any]:
        with self._connect_transactional() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET purchased_token_balance = purchased_token_balance + %s
                    WHERE id = %s;
                    """,
                    (tokens, user_id),
                )
                cur.execute(
                    "SELECT free_token_balance, purchased_token_balance FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = cur.fetchone()
                txn_id = str(__import__("uuid").uuid4())
                cur.execute(
                    """
                    INSERT INTO token_transactions (id, user_id, transaction_type, token_amount,
                        balance_after_free, balance_after_purchased, reference_id, description, created_at)
                    VALUES (%s, %s, 'purchase', %s, %s, %s, %s, 'In-app purchase token grant', NOW());
                    """,
                    (txn_id, user_id, tokens, row["free_token_balance"],
                     row["purchased_token_balance"], purchase_id),
                )
                conn.commit()
                return {
                    "freeBalance": row["free_token_balance"],
                    "purchasedBalance": row["purchased_token_balance"],
                    "totalBalance": row["free_token_balance"] + row["purchased_token_balance"],
                }

    def fetch_user_purchases(
        self, user_id: str, limit: int = 20, offset: int = 0,
    ) -> list[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, platform, product_id, transaction_id,
                           tokens_granted, price_usd, status, created_at
                    FROM purchase_receipts
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (user_id, limit, offset),
                )
                rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "platform": r["platform"],
                "productId": r["product_id"],
                "transactionId": r["transaction_id"],
                "tokensGranted": r["tokens_granted"],
                "priceUsd": round(float(r["price_usd"]), 2),
                "status": r["status"],
                "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]

    def create_deletion_audit_event(self, payload: Dict[str, Any]) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into deletion_audit_events (
                        id, entity_type, entity_id, actor, request_id,
                        purge_storage, result, created_at
                    ) values (
                        %(id)s, %(entity_type)s, %(entity_id)s, %(actor)s, %(request_id)s,
                        %(purge_storage)s, %(result)s, %(created_at)s
                    );
                    """,
                    {
                        **payload,
                        "result": Jsonb(payload.get("result") or {}),
                    },
                )

    def fetch_deletion_audit_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        clauses = []
        params: Dict[str, Any] = {}
        if entity_type:
            clauses.append("entity_type = %(entity_type)s")
            params["entity_type"] = entity_type
        if entity_id:
            clauses.append("entity_id = %(entity_id)s")
            params["entity_id"] = entity_id

        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if limit is not None:
            limit_clause += " limit %(limit)s"
            params["limit"] = limit
        if offset is not None:
            limit_clause += " offset %(offset)s"
            params["offset"] = offset

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    select * from deletion_audit_events
                    {where_clause}
                    order by created_at desc{limit_clause};
                    """,
                    params,
                )
                return cur.fetchall()

    def count_deletion_audit_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> int:
        clauses = []
        params: Dict[str, Any] = {}
        if entity_type:
            clauses.append("entity_type = %(entity_type)s")
            params["entity_type"] = entity_type
        if entity_id:
            clauses.append("entity_id = %(entity_id)s")
            params["entity_id"] = entity_id
        where_clause = f" where {' and '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select count(*) from deletion_audit_events{where_clause};", params)
                row = cur.fetchone()
                return int(list(row.values())[0]) if row else 0

def get_database() -> Database:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL must be set for database access.")
    db = Database(dsn=dsn)
    db.migrate()
    return db


def insert_thread_metrics(
    conn,
    metrics_id: str,
    lecture_id: str,
    course_id: str,
    detected_at: str,
    new_threads_detected: int,
    existing_threads_updated: int,
    total_threads_after: int,
    avg_complexity_level: float,
    complexity_distribution: dict,
    change_type_distribution: dict,
    avg_evidence_length: float,
    threads_with_evidence: int,
    detection_method: str,
    api_response_time_ms: float | None,
    token_usage: dict | None,
    retry_count: int,
    model_name: str | None,
    llm_provider: str | None,
    success: bool,
    error_message: str | None,
    quality_score: float,
):
    """Insert thread detection metrics into the database."""
    import json

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO thread_metrics (
                id, lecture_id, course_id, detected_at,
                new_threads_detected, existing_threads_updated, total_threads_after,
                avg_complexity_level, complexity_distribution, change_type_distribution,
                avg_evidence_length, threads_with_evidence,
                detection_method, api_response_time_ms, token_usage, retry_count,
                model_name, llm_provider, success, error_message, quality_score
            ) VALUES (
                %(id)s, %(lecture_id)s, %(course_id)s, %(detected_at)s,
                %(new_threads_detected)s, %(existing_threads_updated)s, %(total_threads_after)s,
                %(avg_complexity_level)s, %(complexity_distribution)s, %(change_type_distribution)s,
                %(avg_evidence_length)s, %(threads_with_evidence)s,
                %(detection_method)s, %(api_response_time_ms)s, %(token_usage)s, %(retry_count)s,
                %(model_name)s, %(llm_provider)s, %(success)s, %(error_message)s, %(quality_score)s
            )
            """,
            {
                "id": metrics_id,
                "lecture_id": lecture_id,
                "course_id": course_id,
                "detected_at": detected_at,
                "new_threads_detected": new_threads_detected,
                "existing_threads_updated": existing_threads_updated,
                "total_threads_after": total_threads_after,
                "avg_complexity_level": avg_complexity_level,
                "complexity_distribution": json.dumps(complexity_distribution),
                "change_type_distribution": json.dumps(change_type_distribution),
                "avg_evidence_length": avg_evidence_length,
                "threads_with_evidence": threads_with_evidence,
                "detection_method": detection_method,
                "api_response_time_ms": api_response_time_ms,
                "token_usage": json.dumps(token_usage) if token_usage else None,
                "retry_count": retry_count,
                "model_name": model_name,
                "llm_provider": llm_provider,
                "success": success,
                "error_message": error_message,
                "quality_score": quality_score,
            },
        )
    # conn.commit()


def fetch_thread_metrics_by_lecture(conn, lecture_id: str):
    """Fetch thread metrics for a specific lecture."""
    import json

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id, lecture_id, course_id, detected_at,
                new_threads_detected, existing_threads_updated, total_threads_after,
                avg_complexity_level, complexity_distribution, change_type_distribution,
                avg_evidence_length, threads_with_evidence,
                detection_method, api_response_time_ms, token_usage, retry_count,
                model_name, llm_provider, success, error_message, quality_score,
                created_at
            FROM thread_metrics
            WHERE lecture_id = %(lecture_id)s
            ORDER BY detected_at DESC
            """,
            {"lecture_id": lecture_id},
        )
        rows = cur.fetchall()

    return [
        {
            "id": row["id"],
            "lectureId": row["lecture_id"],
            "courseId": row["course_id"],
            "detectedAt": row["detected_at"].isoformat() if row["detected_at"] else None,
            "newThreadsDetected": row["new_threads_detected"],
            "existingThreadsUpdated": row["existing_threads_updated"],
            "totalThreadsAfter": row["total_threads_after"],
            "avgComplexityLevel": float(row["avg_complexity_level"]) if row["avg_complexity_level"] else None,
            "complexityDistribution": json.loads(row["complexity_distribution"]) if row["complexity_distribution"] else {},
            "changeTypeDistribution": json.loads(row["change_type_distribution"]) if row["change_type_distribution"] else {},
            "avgEvidenceLength": float(row["avg_evidence_length"]) if row["avg_evidence_length"] else None,
            "threadsWithEvidence": row["threads_with_evidence"],
            "detectionMethod": row["detection_method"],
            "apiResponseTimeMs": float(row["api_response_time_ms"]) if row["api_response_time_ms"] else None,
            "tokenUsage": json.loads(row["token_usage"]) if row["token_usage"] else None,
            "retryCount": row["retry_count"],
            "modelName": row["model_name"],
            "llmProvider": row["llm_provider"],
            "success": row["success"],
            "errorMessage": row["error_message"],
            "qualityScore": float(row["quality_score"]) if row["quality_score"] else None,
            "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


def fetch_thread_metrics_by_course(conn, course_id: str, limit: int = 50):
    """Fetch thread metrics for all lectures in a course."""
    import json

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id, lecture_id, course_id, detected_at,
                new_threads_detected, existing_threads_updated, total_threads_after,
                avg_complexity_level, complexity_distribution, change_type_distribution,
                avg_evidence_length, threads_with_evidence,
                detection_method, api_response_time_ms, token_usage, retry_count,
                model_name, llm_provider, success, error_message, quality_score,
                created_at
            FROM thread_metrics
            WHERE course_id = %(course_id)s
            ORDER BY detected_at DESC
            LIMIT %(limit)s
            """,
            {"course_id": course_id, "limit": limit},
        )
        rows = cur.fetchall()

    return [
        {
            "id": row["id"],
            "lectureId": row["lecture_id"],
            "courseId": row["course_id"],
            "detectedAt": row["detected_at"].isoformat() if row["detected_at"] else None,
            "newThreadsDetected": row["new_threads_detected"],
            "existingThreadsUpdated": row["existing_threads_updated"],
            "totalThreadsAfter": row["total_threads_after"],
            "avgComplexityLevel": float(row["avg_complexity_level"]) if row["avg_complexity_level"] else None,
            "complexityDistribution": json.loads(row["complexity_distribution"]) if row["complexity_distribution"] else {},
            "changeTypeDistribution": json.loads(row["change_type_distribution"]) if row["change_type_distribution"] else {},
            "avgEvidenceLength": float(row["avg_evidence_length"]) if row["avg_evidence_length"] else None,
            "threadsWithEvidence": row["threads_with_evidence"],
            "detectionMethod": row["detection_method"],
            "apiResponseTimeMs": float(row["api_response_time_ms"]) if row["api_response_time_ms"] else None,
            "tokenUsage": json.loads(row["token_usage"]) if row["token_usage"] else None,
            "retryCount": row["retry_count"],
            "modelName": row["model_name"],
            "llmProvider": row["llm_provider"],
            "success": row["success"],
            "errorMessage": row["error_message"],
            "qualityScore": float(row["quality_score"]) if row["quality_score"] else None,
            "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


def fetch_thread_metrics_summary(conn, course_id: str | None = None):
    """Fetch aggregated thread metrics summary."""
    with conn.cursor(row_factory=dict_row) as cur:
        where_clause = "WHERE course_id = %(course_id)s" if course_id else ""
        cur.execute(
            f"""
            SELECT
                COUNT(*) as total_detections,
                AVG(new_threads_detected) as avg_new_threads,
                AVG(existing_threads_updated) as avg_updates,
                AVG(quality_score) as avg_quality_score,
                AVG(api_response_time_ms) as avg_response_time,
                SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_detections,
                COUNT(DISTINCT detection_method) as methods_used,
                AVG(CASE WHEN detection_method = 'openai' THEN quality_score ELSE NULL END) as openai_avg_quality,
                AVG(CASE WHEN detection_method = 'fallback' THEN quality_score ELSE NULL END) as fallback_avg_quality
            FROM thread_metrics
            {where_clause}
            """,
            {"course_id": course_id} if course_id else {},
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "totalDetections": row["total_detections"],
        "avgNewThreads": float(row["avg_new_threads"]) if row["avg_new_threads"] else 0,
        "avgUpdates": float(row["avg_updates"]) if row["avg_updates"] else 0,
        "avgQualityScore": float(row["avg_quality_score"]) if row["avg_quality_score"] else 0,
        "avgResponseTimeMs": float(row["avg_response_time"]) if row["avg_response_time"] else 0,
        "successfulDetections": row["successful_detections"],
        "methodsUsed": row["methods_used"],
        "openaiAvgQuality": float(row["openai_avg_quality"]) if row["openai_avg_quality"] else None,
        "fallbackAvgQuality": float(row["fallback_avg_quality"]) if row["fallback_avg_quality"] else None,
        "successRate": round((row["successful_detections"] / row["total_detections"] * 100) if row["total_detections"] > 0 else 0, 1),
    }


# Context Files CRUD
def insert_context_file(
    conn,
    file_id: str,
    course_id: str,
    filename: str,
    file_path: str,
    file_size: int,
    file_type: str,
    tag: str,
    extracted_text: str | None,
    created_at: str,
):
    """Insert a context file record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO context_files (
                id, course_id, filename, file_path, file_size, file_type,
                tag, extracted_text, created_at, updated_at
            ) VALUES (
                %(id)s, %(course_id)s, %(filename)s, %(file_path)s, %(file_size)s, %(file_type)s,
                %(tag)s, %(extracted_text)s, %(created_at)s, %(updated_at)s
            )
            """,
            {
                "id": file_id,
                "course_id": course_id,
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": file_type,
                "tag": tag,
                "extracted_text": extracted_text,
                "created_at": created_at,
                "updated_at": created_at,
            },
        )
    # conn.commit()


def fetch_context_files(conn, course_id: str | None = None, tag: str | None = None):
    """Fetch context files, optionally filtered."""
    with conn.cursor(row_factory=dict_row) as cur:
        where_clauses = []
        params = {}

        if course_id:
            where_clauses.append("course_id = %(course_id)s")
            params["course_id"] = course_id

        if tag:
            where_clauses.append("tag = %(tag)s")
            params["tag"] = tag

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cur.execute(
            f"""
            SELECT id, course_id, filename, file_path, file_size, file_type,
                   tag, created_at, updated_at
            FROM context_files
            {where_sql}
            ORDER BY created_at DESC
            """,
            params,
        )
        rows = cur.fetchall()

    return [
        {
            "id": row["id"],
            "courseId": row["course_id"],
            "filename": row["filename"],
            "filePath": row["file_path"],
            "fileSize": row["file_size"],
            "fileType": row["file_type"],
            "tag": row["tag"],
            "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


def fetch_context_file_by_id(conn, file_id: str):
    """Fetch a single context file by ID."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, course_id, filename, file_path, file_size, file_type,
                   tag, extracted_text, created_at, updated_at
            FROM context_files
            WHERE id = %(file_id)s
            """,
            {"file_id": file_id},
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "courseId": row["course_id"],
        "filename": row["filename"],
        "filePath": row["file_path"],
        "fileSize": row["file_size"],
        "fileType": row["file_type"],
        "tag": row["tag"],
        "extractedText": row["extracted_text"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def fetch_context_text_for_course(conn, course_id: str):
    """
    Fetch all extracted text for a course, organized by tag.
    Used by Thread Engine for contextual awareness.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tag, filename, extracted_text
            FROM context_files
            WHERE course_id = %(course_id)s
              AND extracted_text IS NOT NULL
            ORDER BY
                CASE WHEN tag = 'SYLLABUS' THEN 0 ELSE 1 END,
                created_at ASC
            """,
            {"course_id": course_id},
        )
        rows = cur.fetchall()

    syllabus_texts = []
    notes_texts = []

    for row in rows:
        tag, filename, text = row # tuple unpacking works on default cursor too
        if tag == "SYLLABUS":
            syllabus_texts.append(f"=== {filename} ===\n{text}")
        else:
            notes_texts.append(f"=== {filename} ===\n{text}")

    return {
        "syllabus": "\n\n".join(syllabus_texts) if syllabus_texts else None,
        "notes": "\n\n".join(notes_texts) if notes_texts else None,
    }


def delete_context_file(conn, file_id: str):
    """Delete a context file record."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM context_files WHERE id = %(file_id)s",
            {"file_id": file_id},
        )
    # conn.commit()


# =========================================================================
# Dice Rotation State
# =========================================================================


def upsert_dice_rotation_state(conn, rotation_state: Dict[str, Any]):
    """
    Insert or update dice rotation state for a lecture.
    """
    with conn.cursor() as cur:
        # Extract facet scores
        scores = rotation_state.get("scores", {})

        # Determine dominant facet
        dominant_facet = None
        dominant_score = 0.0
        if scores:
            # Find facet with highest score
            facet_map = {
                "RED": ("how", scores.get("RED", 0.0)),
                "ORANGE": ("what", scores.get("ORANGE", 0.0)),
                "YELLOW": ("when", scores.get("YELLOW", 0.0)),
                "GREEN": ("where", scores.get("WHERE", 0.0)),
                "BLUE": ("who", scores.get("BLUE", 0.0)),
                "PURPLE": ("why", scores.get("PURPLE", 0.0)),
            }
            dominant_facet, dominant_score = max(facet_map.values(), key=lambda x: x[1])

        cur.execute(
            """
            INSERT INTO dice_rotation_states (
                id, lecture_id, course_id,
                iterations_completed, max_iterations, status,
                score_how, score_what, score_when, score_where, score_who, score_why,
                entropy, equilibrium_gap, collapsed,
                dominant_facet, dominant_score,
                full_state,
                created_at, updated_at
            )
            VALUES (
                %(id)s, %(lecture_id)s, %(course_id)s,
                %(iterations_completed)s, %(max_iterations)s, %(status)s,
                %(score_how)s, %(score_what)s, %(score_when)s,
                %(score_where)s, %(score_who)s, %(score_why)s,
                %(entropy)s, %(equilibrium_gap)s, %(collapsed)s,
                %(dominant_facet)s, %(dominant_score)s,
                %(full_state)s,
                NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                iterations_completed = EXCLUDED.iterations_completed,
                status = EXCLUDED.status,
                score_how = EXCLUDED.score_how,
                score_what = EXCLUDED.score_what,
                score_when = EXCLUDED.score_when,
                score_where = EXCLUDED.score_where,
                score_who = EXCLUDED.score_who,
                score_why = EXCLUDED.score_why,
                entropy = EXCLUDED.entropy,
                equilibrium_gap = EXCLUDED.equilibrium_gap,
                collapsed = EXCLUDED.collapsed,
                dominant_facet = EXCLUDED.dominant_facet,
                dominant_score = EXCLUDED.dominant_score,
                full_state = EXCLUDED.full_state,
                updated_at = NOW()
            """,
            {
                "id": rotation_state.get("id"),
                "lecture_id": rotation_state.get("lectureId"),
                "course_id": rotation_state.get("courseId"),
                "iterations_completed": rotation_state.get("iterationsCompleted", 0),
                "max_iterations": rotation_state.get("maxIterations", 6),
                "status": rotation_state.get("status", "in_progress"),
                "score_how": scores.get("RED", 0.0),
                "score_what": scores.get("ORANGE", 0.0),
                "score_when": scores.get("YELLOW", 0.0),
                "score_where": scores.get("GREEN", 0.0),
                "score_who": scores.get("BLUE", 0.0),
                "score_why": scores.get("PURPLE", 0.0),
                "entropy": rotation_state.get("entropy", 0.0),
                "equilibrium_gap": rotation_state.get("equilibriumGap", 1.0),
                "collapsed": rotation_state.get("collapsed", False),
                "dominant_facet": dominant_facet,
                "dominant_score": dominant_score,
                "full_state": Jsonb(rotation_state.get("fullState", rotation_state)),
            },
        )
    # conn.commit()


def fetch_dice_rotation_state_by_lecture(conn, lecture_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch dice rotation state for a lecture.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, lecture_id, course_id,
                   iterations_completed, max_iterations, status,
                   score_how, score_what, score_when, score_where, score_who, score_why,
                   entropy, equilibrium_gap, collapsed,
                   dominant_facet, dominant_score,
                   full_state,
                   created_at, updated_at
            FROM dice_rotation_states
            WHERE lecture_id = %(lecture_id)s
            """,
            {"lecture_id": lecture_id},
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "lectureId": row["lecture_id"],
        "courseId": row["course_id"],
        "iterationsCompleted": row["iterations_completed"],
        "maxIterations": row["max_iterations"],
        "status": row["status"],
        "scores": {
            "RED": row["score_how"],
            "ORANGE": row["score_what"],
            "YELLOW": row["score_when"],
            "GREEN": row["score_where"],
            "BLUE": row["score_who"],
            "PURPLE": row["score_why"],
        },
        "entropy": row["entropy"],
        "equilibriumGap": row["equilibrium_gap"],
        "collapsed": row["collapsed"],
        "dominantFacet": row["dominant_facet"],
        "dominantScore": row["dominant_score"],
        "fullState": row["full_state"],
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def fetch_dice_rotation_states_by_course(conn, course_id: str) -> list[Dict[str, Any]]:
    """
    Fetch all dice rotation states for a course.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, lecture_id, course_id,
                   iterations_completed, max_iterations, status,
                   score_how, score_what, score_when, score_where, score_who, score_why,
                   entropy, equilibrium_gap, collapsed,
                   dominant_facet, dominant_score,
                   created_at, updated_at
            FROM dice_rotation_states
            WHERE course_id = %(course_id)s
            ORDER BY created_at DESC
            """,
            {"course_id": course_id},
        )
        rows = cur.fetchall()

    return [
        {
            "id": row["id"],
            "lectureId": row["lecture_id"],
            "courseId": row["course_id"],
            "iterationsCompleted": row["iterations_completed"],
            "maxIterations": row["max_iterations"],
            "status": row["status"],
            "scores": {
                "RED": row["score_how"],
                "ORANGE": row["score_what"],
                "YELLOW": row["score_when"],
                "GREEN": row["score_where"],
                "BLUE": row["score_who"],
                "PURPLE": row["score_why"],
            },
            "entropy": row["entropy"],
            "equilibriumGap": row["equilibrium_gap"],
            "collapsed": row["collapsed"],
            "dominantFacet": row["dominant_facet"],
            "dominantScore": row["dominant_score"],
            "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]
