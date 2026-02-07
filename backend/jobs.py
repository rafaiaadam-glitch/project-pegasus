from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass
class Job:
    id: str
    status: str = "queued"
    result: Dict[str, Any] | None = None
    error: str | None = None


class JobQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[Job, Callable[[], Dict[str, Any]]]] = queue.Queue()
        self._jobs: Dict[str, Job] = {}
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def submit(self, func: Callable[[], Dict[str, Any]]) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id)
        self._jobs[job_id] = job
        self._queue.put((job, func))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _run(self) -> None:
        while True:
            job, func = self._queue.get()
            job.status = "running"
            try:
                job.result = func()
                job.status = "completed"
            except Exception as exc:  # pragma: no cover - runtime job errors
                job.error = str(exc)
                job.status = "failed"
            finally:
                self._queue.task_done()


JOB_QUEUE = JobQueue()
