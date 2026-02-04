from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

import ideas.compiler as compiler_module
from db.models import Idea


class _FailingMediator:
    def generate_json(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced-llm-error")


class _FailThenOkMediator:
    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self.calls: list[str] = []

    def generate_json(self, *, task_type: str, **_kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(task_type)
        if len(self.calls) == 1:
            raise RuntimeError("first-failure")
        return {"dsl_yaml": self.template_path.read_text()}, {"provider": "test", "model": "test"}


def _idea(status: str) -> Idea:
    return Idea(
        id=uuid4(),
        title="Test idea",
        summary="Simple summary",
        what_to_expect="Expect motion",
        preview="Preview",
        status=status,
    )


def test_compile_rejects_non_feasible_status(tmp_path: Path) -> None:
    idea = _idea("blocked_by_gaps")
    with pytest.raises(RuntimeError, match="idea_not_feasible"):
        compiler_module.compile_idea_to_dsl(
            idea=idea,
            template_path=Path(".ai/examples/dsl-v1-happy.yaml"),
            target_path=tmp_path / "dsl.yaml",
            animation_code="anim-test",
        )


def test_compile_fallback_to_template_when_llm_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "1")
    monkeypatch.setenv("IDEA_DSL_COMPILER_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("IDEA_DSL_COMPILER_MAX_REPAIRS", "0")
    monkeypatch.setattr(compiler_module, "get_mediator", lambda: _FailingMediator())
    idea = _idea("feasible")
    out_path = tmp_path / "dsl.yaml"

    result = compiler_module.compile_idea_to_dsl(
        idea=idea,
        template_path=Path(".ai/examples/dsl-v1-happy.yaml"),
        target_path=out_path,
        animation_code="anim-test",
        max_attempts=1,
        max_repairs=0,
    )

    assert out_path.exists()
    assert result.compiler_meta["fallback_used"] is True


def test_compile_uses_dsl_repair_task_after_first_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "0")
    mediator = _FailThenOkMediator(Path(".ai/examples/dsl-v1-happy.yaml"))
    monkeypatch.setattr(compiler_module, "get_mediator", lambda: mediator)
    idea = _idea("feasible")
    out_path = tmp_path / "dsl.yaml"

    result = compiler_module.compile_idea_to_dsl(
        idea=idea,
        template_path=Path(".ai/examples/dsl-v1-happy.yaml"),
        target_path=out_path,
        animation_code="anim-test",
        max_attempts=2,
        max_repairs=1,
    )

    assert result.compiler_meta["fallback_used"] is False
    assert mediator.calls == ["idea_compile_dsl", "dsl_repair"]
