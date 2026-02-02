from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import time
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    version: str


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "fastembed"
    model_name: str = "BAAI/bge-small-en-v1.5"
    max_batch_size: int = 32
    rate_limit_rps: float = 5.0
    cache_ttl_s: int = 3600
    retry_attempts: int = 2
    retry_backoff_s: float = 0.5
    allow_hash_fallback: bool = True


class EmbeddingService:
    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        self.config = config or EmbeddingConfig()
        self._provider = _build_provider(self.config)
        self._cache: dict[str, tuple[EmbeddingResult, float]] = {}
        self._last_call_ts: float = 0.0

    def embed(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        if not texts:
            return []
        results: list[EmbeddingResult] = []
        for batch in _chunk(texts, self.config.max_batch_size):
            results.extend(self._embed_batch(batch))
        return results

    def _embed_batch(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        cached, to_compute = self._split_cached(texts)
        if to_compute:
            computed = self._call_with_retry(to_compute)
            for text, result in zip(to_compute, computed, strict=True):
                self._cache[text] = (result, time.time())
        else:
            computed = []
        return cached + computed

    def _split_cached(self, texts: Sequence[str]) -> tuple[list[EmbeddingResult], list[str]]:
        now = time.time()
        cached: list[EmbeddingResult] = []
        to_compute: list[str] = []
        for text in texts:
            entry = self._cache.get(text)
            if entry and (now - entry[1]) <= self.config.cache_ttl_s:
                cached.append(entry[0])
            else:
                to_compute.append(text)
        return cached, to_compute

    def _call_with_retry(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        attempts = self.config.retry_attempts + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                self._rate_limit()
                return self._provider.embed(texts)
            except Exception as exc:  # noqa: BLE001 - keep provider exceptions visible
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(self.config.retry_backoff_s * (attempt + 1))
        if last_error:
            raise last_error
        raise RuntimeError("Embedding failed without exception")

    def _rate_limit(self) -> None:
        if self.config.rate_limit_rps <= 0:
            return
        min_interval = 1.0 / self.config.rate_limit_rps
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_ts = time.time()


class _Provider:
    def embed(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        raise NotImplementedError


class _FastEmbedProvider(_Provider):
    def __init__(self, model_name: str) -> None:
        from fastembed import TextEmbedding  # type: ignore
        import fastembed  # type: ignore

        self._model_name = model_name
        self._version = getattr(fastembed, "__version__", "unknown")
        self._embedder = TextEmbedding(model_name=model_name)

    def embed(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        vectors = list(self._embedder.embed(texts))
        return [
            EmbeddingResult(vector=list(vec), model=self._model_name, version=self._version)
            for vec in vectors
        ]


class _HashEmbeddingProvider(_Provider):
    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    def embed(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                vector=_hash_embedding(text, self._dim),
                model=f"hash-{self._dim}",
                version="v1",
            )
            for text in texts
        ]


def _build_provider(config: EmbeddingConfig) -> _Provider:
    if config.provider == "fastembed":
        try:
            return _FastEmbedProvider(config.model_name)
        except Exception:
            if config.allow_hash_fallback:
                return _HashEmbeddingProvider()
            raise
    if config.provider == "hash":
        return _HashEmbeddingProvider()
    raise ValueError(f"Unsupported embedding provider: {config.provider}")


def _hash_embedding(text: str, dim: int) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    values = list(digest)
    if dim <= 0:
        return []
    out: list[float] = []
    while len(out) < dim:
        for value in values:
            out.append(value / 255.0)
            if len(out) >= dim:
                break
    return out


def _chunk(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    if size <= 0:
        yield items
        return
    for i in range(0, len(items), size):
        yield items[i : i + size]
