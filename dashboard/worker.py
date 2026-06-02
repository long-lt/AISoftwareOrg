"""
dashboard.worker
Standalone RQ worker entrypoint for generation jobs.

Run:
    python -m dashboard.worker
"""

from __future__ import annotations

from dashboard.queue_manager import REDIS_URL, RQ_QUEUE_NAME


def main() -> None:
    try:
        from redis import Redis
        from rq import Queue, Worker
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "dashboard.worker requires `redis` and `rq` packages."
        ) from error

    redis_connection = Redis.from_url(REDIS_URL)
    queue = Queue(RQ_QUEUE_NAME, connection=redis_connection)
    worker = Worker([queue], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    main()
