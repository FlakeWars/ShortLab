from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import random
from typing import Sequence
from pathlib import Path

from db.models import Idea
from embeddings import EmbeddingService, cosine_similarity
from embeddings.service import EmbeddingResult
from .parser import ParsedIdea, parse_ideas_file


@dataclass(frozen=True)
class IdeaDraft:
    title: str
    summary: str
    source: str
    generation_meta: dict
    content_hash: str


def generate_ideas(
    *,
    source: str,
    ideas_path: str | None = None,
    limit: int | None = None,
    seed: int | None = None,
    prompt: str | None = None,
) -> list[IdeaDraft]:
    if source == "auto":
        try:
            return generate_ideas(
                source="template",
                ideas_path=ideas_path,
                limit=limit,
                seed=seed,
                prompt=prompt,
            )
        except Exception:
            if ideas_path:
                return generate_ideas(
                    source="file",
                    ideas_path=ideas_path,
                    limit=limit,
                    seed=seed,
                    prompt=prompt,
                )
            raise
    if source == "file":
        if not ideas_path:
            raise ValueError("ideas_path is required for file source")
        parsed = parse_ideas_file(Path(ideas_path))
        return _drafts_from_parsed(parsed, source="file", meta={"path": ideas_path}, limit=limit)
    if source == "template":
        rng = random.Random(seed or 0)
        return _template_ideas(rng, limit or 5, prompt)
    raise ValueError(f"Unsupported idea source: {source}")


def save_ideas(
    session,
    ideas: Sequence[IdeaDraft],
    embedder: EmbeddingService,
    similarity_threshold: float | None = 0.97,
) -> list[Idea]:
    existing = session.query(Idea).all()
    existing_hashes = {idea.content_hash for idea in existing if idea.content_hash}
    existing_embeddings = [idea.embedding for idea in existing if idea.embedding]

    to_store = [
        idea
        for idea in ideas
        if idea.content_hash not in existing_hashes and _is_valid(idea)
    ]
    if not to_store:
        return []

    embeddings = embedder.embed([_embed_text(idea) for idea in to_store])
    created: list[Idea] = []
    for idea, result in zip(to_store, embeddings, strict=True):
        similarity = _max_similarity(result, existing_embeddings)
        if similarity_threshold is not None and similarity is not None:
            if similarity >= similarity_threshold:
                continue
        record = Idea(
            title=idea.title,
            summary=idea.summary,
            content_hash=idea.content_hash,
            source=idea.source,
            generation_meta=idea.generation_meta,
            embedding=result.vector,
            embedding_model=result.model,
            embedding_version=result.version,
            similarity=similarity,
            created_at=datetime.utcnow(),
        )
        session.add(record)
        created.append(record)
    session.commit()
    return created


def _embed_text(idea: IdeaDraft) -> str:
    return f"{idea.title}\n{idea.summary}".strip()


def _max_similarity(result: EmbeddingResult, existing_embeddings: Sequence[list[float] | None]) -> float | None:
    if not existing_embeddings:
        return None
    sims = [
        cosine_similarity(result.vector, emb)
        for emb in existing_embeddings
        if emb is not None
    ]
    return max(sims, default=0.0)


def _drafts_from_parsed(
    parsed: Sequence[ParsedIdea],
    *,
    source: str,
    meta: dict,
    limit: int | None,
) -> list[IdeaDraft]:
    out: list[IdeaDraft] = []
    for item in parsed[: limit or len(parsed)]:
        content_hash = _hash_content(item.title, item.summary)
        out.append(
            IdeaDraft(
                title=item.title,
                summary=item.summary,
                source=source,
                generation_meta=meta,
                content_hash=content_hash,
            )
        )
    return out


def _template_ideas(rng: random.Random, count: int, prompt: str | None) -> list[IdeaDraft]:
    motifs = [
        ("Pulsujace jądro", "Czastki orbituja i dziela sie w rytmie uderzen."),
        ("Grawitacyjna zmiana", "Grawitacja odwraca sie cyklicznie, tworząc rytm."),
        ("Wzrost krystaliczny", "Kryształy rosną i blokują przestrzeń."),
        ("Siec napiec", "Punkty lacza sie i pekaja przy nadmiernym napieciu."),
    ]
    out: list[IdeaDraft] = []
    for idx in range(count):
        title, summary = rng.choice(motifs)
        if prompt:
            summary = f"{summary} Prompt: {prompt}"
        content_hash = _hash_content(title, summary)
        out.append(
            IdeaDraft(
                title=f"{title} #{idx + 1}",
                summary=summary,
                source="template",
                generation_meta={"prompt": prompt, "seed": rng.random()},
                content_hash=content_hash,
            )
        )
    return out


def _hash_content(title: str, summary: str) -> str:
    payload = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_valid(idea: IdeaDraft) -> bool:
    if len(idea.title.strip()) < 3:
        return False
    if len(idea.summary.strip()) < 20:
        return False
    return True
