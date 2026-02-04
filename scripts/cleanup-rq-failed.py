#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser

from rq import Queue
from rq.registry import FailedJobRegistry

from pipeline.queue import get_redis


def main() -> None:
    parser = ArgumentParser(description="Delete jobs from RQ failed registry")
    parser.add_argument("--queue", default="default")
    parser.add_argument("--all", action="store_true", help="Delete all failed jobs")
    parser.add_argument("--limit", type=int, default=200, help="Max jobs to delete when not using --all")
    args = parser.parse_args()

    queue = Queue(args.queue, connection=get_redis())
    registry = FailedJobRegistry(queue=queue)
    ids = registry.get_job_ids()
    if not ids:
        print("[rq-cleanup] removed 0 failed job(s)")
        return

    selected = ids if args.all else ids[: max(0, args.limit)]
    removed = 0
    for job_id in selected:
        job = queue.fetch_job(job_id)
        if job is not None:
            job.delete(remove_from_queue=True)
            removed += 1
            continue
        registry.remove(job_id, delete_job=True)
        removed += 1

    print(f"[rq-cleanup] removed {removed} failed job(s)")


if __name__ == "__main__":
    main()
