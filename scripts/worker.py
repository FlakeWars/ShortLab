#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser

from rq import Worker

from pipeline.queue import get_queue, get_redis


def main() -> None:
    parser = ArgumentParser(description="Start RQ worker")
    parser.add_argument("--queue", default="default")
    args = parser.parse_args()

    queue = get_queue(args.queue)
    worker = Worker([queue], connection=get_redis())
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
