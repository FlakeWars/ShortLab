from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import api.main as api_main
from db.models import Animation, PublishRecord, QCChecklistVersion, QCDecision, Render


class _FakeScalarResult:
    def __init__(self, item=None) -> None:
        self._item = item

    def first(self):
        return self._item


class _FakeExecuteResult:
    def __init__(self, item=None) -> None:
        self._item = item

    def scalars(self):
        return _FakeScalarResult(self._item)


class _FakeSession:
    def __init__(self, *, animation: Animation | None = None, render: Render | None = None) -> None:
        self.animation = animation
        self.render = render
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def get(self, model, key):
        if model is Animation and self.animation is not None and self.animation.id == key:
            return self.animation
        if model is Render and self.render is not None and self.render.id == key:
            return self.render
        return None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass
        self.added.append(obj)

    def execute(self, _stmt):
        return _FakeExecuteResult(None)

    def flush(self):
        self.flushes += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                try:
                    obj.id = uuid4()
                except Exception:
                    pass

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


def test_ops_qc_decide_updates_animation_status_and_writes_audit(monkeypatch) -> None:
    now = datetime(2026, 2, 23, 12, 0, tzinfo=UTC)
    animation = Animation(
        id=uuid4(),
        animation_code="anim-001",
        status="review",
        pipeline_stage="qc",
        created_at=now,
        updated_at=now,
    )
    fake_session = _FakeSession(animation=animation)
    checklist = QCChecklistVersion(id=uuid4(), name="mvp", version="v1", is_active=True, created_at=now)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_get_or_create_qc_checklist", lambda _session: checklist)

    payload = api_main.ops_qc_decide(
        api_main.QcDecisionCreateRequest(
            animation_id=animation.id,
            result="accepted",
            notes="looks good",
        ),
        _guard=None,
    )

    assert str(payload["animation_id"]) == str(animation.id)
    assert payload["result"] == "accepted"
    assert payload["animation_status"] == "accepted"
    assert payload["pipeline_stage"] == "publish"
    assert animation.status == "accepted"
    assert animation.pipeline_stage == "publish"
    assert fake_session.commits == 1
    assert fake_session.rollbacks == 0

    decisions = [obj for obj in fake_session.added if isinstance(obj, QCDecision)]
    assert len(decisions) == 1
    assert decisions[0].notes == "looks good"
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "qc_decision"]
    assert len(audits) == 1
    assert audits[0].payload["result"] == "accepted"


def test_ops_publish_record_manual_confirmed_marks_animation_published(monkeypatch) -> None:
    now = datetime(2026, 2, 23, 13, 0, tzinfo=UTC)
    animation = Animation(
        id=uuid4(),
        animation_code="anim-002",
        status="accepted",
        pipeline_stage="publish",
        created_at=now,
        updated_at=now,
    )
    render = Render(
        id=uuid4(),
        animation_id=animation.id,
        status="succeeded",
        seed=1,
        dsl_version_id=uuid4(),
        design_system_version_id=uuid4(),
        renderer_version="test",
        duration_ms=1000,
        width=1080,
        height=1920,
        fps=12,
        params_json={},
        created_at=now,
    )
    fake_session = _FakeSession(animation=animation, render=render)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)

    payload = api_main.ops_publish_record(
        api_main.PublishRecordCreateRequest(
            render_id=render.id,
            platform="youtube",
            status="manual_confirmed",
            content_id="abc123",
            url="https://example.test/watch?v=abc123",
        ),
        _guard=None,
    )

    assert str(payload["render_id"]) == str(render.id)
    assert payload["status"] == "manual_confirmed"
    assert payload["animation_status"] == "published"
    assert payload["pipeline_stage"] == "metrics"
    assert animation.status == "published"
    assert animation.pipeline_stage == "metrics"
    assert fake_session.commits == 1

    records = [obj for obj in fake_session.added if isinstance(obj, PublishRecord)]
    assert len(records) == 1
    assert records[0].platform_type == "youtube"
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "publish_record"]
    assert len(audits) == 1
    assert audits[0].payload["status"] == "manual_confirmed"
