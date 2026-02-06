#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import os

from rq import SimpleWorker, Worker

from db.session import engine
from pipeline.queue import get_queue, get_redis


def main() -> None:
    parser = ArgumentParser(description="Start RQ worker")
    parser.add_argument("--queue", default="default")
    parser.add_argument("--burst", action="store_true", help="Process queued jobs and exit")
    args = parser.parse_args()

    if hasattr(os, "register_at_fork"):
        os.register_at_fork(after_in_child=lambda: engine.dispose())

    queue = get_queue(args.queue)
    worker_cls = SimpleWorker if os.getenv("RQ_SIMPLE_WORKER", "1") == "1" else Worker
    worker = worker_cls([queue], connection=get_redis())
    worker.work(with_scheduler=False, burst=args.burst)


if __name__ == "__main__":
    main()
