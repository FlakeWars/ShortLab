from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedIdea:
    title: str
    summary: str
    what_to_expect: str
    preview: str


def parse_ideas_text(text: str) -> list[ParsedIdea]:
    lines = text.splitlines()
    ideas: list[ParsedIdea] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title is None:
            return
        summary = _collapse_summary(current_lines)
        if summary:
            ideas.append(
                ParsedIdea(
                    title=current_title.strip(),
                    summary=summary.strip(),
                    what_to_expect=_extract_field(current_lines, "Co zobaczysz:"),
                    preview=_extract_field(current_lines, "Preview/Reguły:"),
                )
            )
        current_title = None
        current_lines = []

    for line in lines:
        if _is_title_line(line):
            flush()
            current_title = _extract_title(line)
            continue
        if current_title is not None:
            current_lines.append(line)

    flush()
    return ideas


def parse_ideas_file(path: Path) -> list[ParsedIdea]:
    return parse_ideas_text(path.read_text())


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


def _collapse_summary(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Co zobaczysz:") or stripped.startswith("Preview/Reguły:"):
            continue
        out.append(stripped)
    return " ".join(out)


def _extract_field(lines: list[str], label: str) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(label):
            return stripped.split(label, 1)[1].strip()
    return ""
