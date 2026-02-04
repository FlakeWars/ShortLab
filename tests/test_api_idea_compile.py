from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

import api.main as api_main
from db.models import Idea


class _FakeSession:
    def __init__(self, idea: Idea | None) -> None:
        self.idea = idea
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    def get(self, model, key):
        if model is Idea and self.idea is not None and self.idea.id == key:
            return self.idea
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


def test_compile_idea_dsl_success(monkeypatch, tmp_path: Path) -> None:
    idea = Idea(
        id=uuid4(),
        title="Feasible",
        summary="ok",
        what_to_expect="ok",
        preview="ok",
        status="feasible",
    )
    fake_session = _FakeSession(idea)
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        api_main,
        "compile_idea_to_dsl",
        lambda **kwargs: SimpleNamespace(
            dsl_hash="abc123",
            compiler_meta={"fallback_used": False},
            validation_report={"syntax_ok": True, "semantic_ok": True, "errors": []},
        ),
    )
    monkeypatch.setenv("OPERATOR_TOKEN", "sekret")

    payload = api_main.compile_idea_dsl(
        idea_id=idea.id,
        req=api_main.IdeaCompileRequest(
            dsl_template=".ai/examples/dsl-v1-happy.yaml",
            out_root=str(tmp_path),
            max_attempts=1,
            max_repairs=0,
        ),
        _guard=None,
    )
    assert str(payload["idea_id"]) == str(idea.id)
    assert payload["dsl_hash"] == "abc123"
    assert payload["compiler_meta"]["fallback_used"] is False
    assert payload["validation_report"]["semantic_ok"] is True
    assert idea.status == "compiled"
    assert fake_session.commits == 1


def test_compile_idea_dsl_rejects_non_feasible(monkeypatch, tmp_path: Path) -> None:
    idea = Idea(
        id=uuid4(),
        title="Blocked",
        summary="gap",
        what_to_expect="gap",
        preview="gap",
        status="blocked_by_gaps",
    )
    fake_session = _FakeSession(idea)
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setenv("OPERATOR_TOKEN", "sekret")

    try:
        api_main.compile_idea_dsl(
            idea_id=idea.id,
            req=api_main.IdeaCompileRequest(
                dsl_template=".ai/examples/dsl-v1-happy.yaml",
                out_root=str(tmp_path),
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "idea_not_feasible" in str(exc.detail)
    assert fake_session.rollbacks == 1
