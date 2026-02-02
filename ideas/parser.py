from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedIdea:
    title: str
    summary: str


def parse_ideas_file(path: Path) -> list[ParsedIdea]:
    text = path.read_text().splitlines()
    ideas: list[ParsedIdea] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title is None:
            return
        summary = " ".join(line.strip() for line in current_lines if line.strip())
        if summary:
            ideas.append(ParsedIdea(title=current_title.strip(), summary=summary.strip()))
        current_title = None
        current_lines = []

    for line in text:
        if _is_title_line(line):
            flush()
            current_title = _extract_title(line)
            continue
        if current_title is not None:
            current_lines.append(line)

    flush()
    return ideas


def _is_title_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if not stripped[0].isdigit():
        return False
    return ". " in stripped


def _extract_title(line: str) -> str:
    stripped = line.strip()
    return stripped.split(". ", 1)[1]
