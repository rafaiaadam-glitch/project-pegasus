from __future__ import annotations

import os
from dataclasses import dataclass
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
                        "lecture_refs": Jsonb(payload.get("lecture_refs")),
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
                AVG(CASE WHEN detection_method = 'gemini' THEN quality_score ELSE NULL END) as gemini_avg_quality,
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
        "geminiAvgQuality": float(row["gemini_avg_quality"]) if row["gemini_avg_quality"] else None,
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
