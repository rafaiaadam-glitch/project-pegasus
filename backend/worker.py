from __future__ import annotations

import os

from redis import Redis
from rq import Connection, Worker


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    with Connection(connection):
        worker = Worker(["pegasus"])
        worker.work()


if __name__ == "__main__":
    main()
