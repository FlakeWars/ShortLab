from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List


def parse_ideas(path: Path) -> list[dict]:
    lines = [ln.rstrip() for ln in path.read_text().splitlines()]
    ideas: list[dict] = []
    current_title = None
    current_lines: list[str] = []
    for line in lines:
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if current_title:
                ideas.append(
                    {
                        "title": current_title.strip(),
                        "summary": " ".join(
                            [
                                ln.strip()
                                for ln in current_lines
                                if not ln.strip().startswith("Co zobaczysz:")
                                and not ln.strip().startswith("Preview/Reguły:")
                            ]
                        ).strip(),
                        "what_to_expect": _extract_field(current_lines, "Co zobaczysz:"),
                        "preview": _extract_field(current_lines, "Preview/Reguły:"),
                    }
                )
            current_title = m.group(1)
            current_lines = []
            continue
        if current_title is not None and line.strip():
            current_lines.append(line)
    if current_title:
        ideas.append(
            {
                "title": current_title.strip(),
                "summary": " ".join(
                    [
                        ln.strip()
                        for ln in current_lines
                        if not ln.strip().startswith("Co zobaczysz:")
                        and not ln.strip().startswith("Preview/Reguły:")
                    ]
                ).strip(),
                "what_to_expect": _extract_field(current_lines, "Co zobaczysz:"),
                "preview": _extract_field(current_lines, "Preview/Reguły:"),
            }
        )
    return ideas


def _extract_field(lines: list[str], label: str) -> str:
    for line in lines:
        if line.startswith(label):
            return line.split(label, 1)[1].strip()
    return ""


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t]


def text_to_vec(text: str, dim: int = 64) -> list[float]:
    vec = [0.0] * dim
    for tok in tokenize(text):
        idx = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16) % dim
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def content_hash(title: str, summary: str) -> str:
    data = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def max_similarity(candidate_vec: list[float], history: List[list[float]]) -> float:
    if not history:
        return 0.0
    return max(cosine(candidate_vec, h) for h in history)
