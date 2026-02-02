from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import random
from typing import Sequence
from uuid import UUID
from pathlib import Path

from db.models import Idea, IdeaCandidate, IdeaEmbedding, IdeaSimilarity
from embeddings import EmbeddingService, cosine_similarity
from embeddings.service import EmbeddingResult
from .parser import ParsedIdea, parse_ideas_file


@dataclass(frozen=True)
class IdeaDraft:
    title: str
    summary: str
    what_to_expect: str
    preview: str
    source: str
    generation_meta: dict
    idea_hash: str


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
    *,
    idea_batch_id: UUID,
) -> list[IdeaCandidate]:
    existing = session.query(Idea).all()
    existing_hashes = {idea.idea_hash for idea in existing if idea.idea_hash}

    to_store = [idea for idea in ideas if idea.idea_hash not in existing_hashes and _is_valid(idea)]
    if not to_store:
        return []

    existing_texts = [_embed_text_from_idea(idea) for idea in existing]
    existing_vectors = []
    if existing_texts:
        existing_vectors = [res.vector for res in embedder.embed(existing_texts)]

    embeddings = embedder.embed([_embed_text(idea) for idea in to_store])
    created: list[IdeaCandidate] = []
    for idea, result in zip(to_store, embeddings, strict=True):
        similarity = _max_similarity(result, existing_vectors)
        similarity_status = _similarity_status(similarity, similarity_threshold, existing_vectors)
        record = IdeaCandidate(
            idea_batch_id=idea_batch_id,
            title=idea.title,
            summary=idea.summary,
            what_to_expect=idea.what_to_expect,
            preview=idea.preview,
            generator_source=_map_generator_source(idea.source),
            similarity_status=similarity_status,
            created_at=datetime.utcnow(),
        )
        session.add(record)
        created.append(record)
        record.max_similarity = similarity  # type: ignore[attr-defined]
        session.flush()

        embedding = IdeaEmbedding(
            idea_candidate_id=record.id,
            idea_id=None,
            provider=embedder.config.provider,
            model=result.model,
            version=result.version,
            vector=result.vector,
            created_at=datetime.utcnow(),
        )
        session.add(embedding)

        if existing:
            for compared, vector in zip(existing, existing_vectors, strict=True):
                score = cosine_similarity(result.vector, vector)
                sim = IdeaSimilarity(
                    idea_candidate_id=record.id,
                    compared_idea_id=compared.id,
                    score=score,
                    embedding_version=result.version,
                    created_at=datetime.utcnow(),
                )
                session.add(sim)
    session.commit()
    return created


def _embed_text(idea: IdeaDraft) -> str:
    return f"{idea.title}\n{idea.summary}".strip()

def _embed_text_from_idea(idea: Idea) -> str:
    summary = idea.summary or ""
    return f"{idea.title}\n{summary}".strip()


def _max_similarity(result: EmbeddingResult, existing_embeddings: Sequence[list[float]]) -> float | None:
    if not existing_embeddings:
        return None
    sims = [cosine_similarity(result.vector, emb) for emb in existing_embeddings]
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
                what_to_expect=item.what_to_expect,
                preview=item.preview,
                source=source,
                generation_meta=meta,
                idea_hash=content_hash,
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
                what_to_expect="",
                preview="",
                source="template",
                generation_meta={"prompt": prompt, "seed": rng.random()},
                idea_hash=content_hash,
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


def _map_generator_source(source: str) -> str:
    if source == "file":
        return "fallback"
    if source == "template":
        return "manual"
    return "ai"


def _similarity_status(
    similarity: float | None,
    threshold: float | None,
    existing_vectors: Sequence[list[float]],
) -> str:
    if not existing_vectors:
        return "unknown"
    if threshold is None or similarity is None:
        return "ok"
    return "too_similar" if similarity >= threshold else "ok"
