#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pprint import pprint

from db.session import SessionLocal
from embeddings import EmbeddingConfig, EmbeddingService
from ideas.generator import generate_ideas, save_ideas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ideas and store in DB")
    parser.add_argument(
        "--source",
        default="file",
        choices=["auto", "file", "template"],
        help="Idea source provider",
    )
    parser.add_argument("--ideas-path", default=".ai/ideas.md", help="Path to ideas file")
    parser.add_argument("--limit", type=int, default=5, help="Limit ideas count")
    parser.add_argument("--seed", type=int, default=0, help="Seed for template source")
    parser.add_argument("--prompt", default="", help="Optional prompt for template source")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.97,
        help="Skip ideas with cosine similarity above this threshold",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print ideas without DB")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    drafts = generate_ideas(
        source=args.source,
        ideas_path=args.ideas_path,
        limit=args.limit,
        seed=args.seed,
        prompt=args.prompt or None,
    )

    if args.dry_run:
        for item in drafts:
            pprint(item)
        return

    embedder = EmbeddingService(EmbeddingConfig(provider="sklearn-hash"))
    session = SessionLocal()
    try:
        created = save_ideas(
            session,
            drafts,
            embedder,
            similarity_threshold=args.similarity_threshold,
        )
        print(f"[idea-generate] stored={len(created)} skipped={len(drafts) - len(created)}")
        for idea in created:
            print(f"[idea-generate] id={idea.id} title={idea.title}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
