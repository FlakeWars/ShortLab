from __future__ import annotations

from pathlib import Path


DSL_SPEC_PATH = Path(".ai/dsl-v1.md")


def read_dsl_spec(max_chars: int = 16000) -> str:
    try:
        text = DSL_SPEC_PATH.read_text()
    except Exception:
        return ""
    return text[:max_chars]


def build_idea_context(
    *,
    title: str,
    summary: str | None,
    what_to_expect: str | None,
    preview: str | None,
) -> str:
    return (
        f"Idea title: {title}\n"
        f"Idea summary: {summary or ''}\n"
        f"Idea what_to_expect: {what_to_expect or ''}\n"
        f"Idea preview: {preview or ''}\n"
    )
