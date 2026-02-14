from __future__ import annotations

import os

from redis import Redis
from rq import Connection, Worker

from backend.runtime_config import validate_runtime_environment


def main() -> None:
    validate_runtime_environment("worker")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    with Connection(connection):
        worker = Worker(["pegasus"])
        worker.work()


if __name__ == "__main__":
    main()
