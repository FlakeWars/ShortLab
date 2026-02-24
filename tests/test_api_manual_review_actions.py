from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import api.main as api_main
from fastapi import HTTPException
from db.models import Animation, Idea, MetricsDaily, PublishRecord, QCChecklistVersion, QCDecision, Render


class _FakeScalarResult:
    def __init__(self, item=None) -> None:
        self._item = item

    def first(self):
        if isinstance(self._item, list):
            return self._item[0] if self._item else None
        return self._item

    def all(self):
        if isinstance(self._item, list):
            return self._item
        if self._item is None:
            return []
        return [self._item]


class _FakeExecuteResult:
    def __init__(self, item=None) -> None:
        self._item = item

    def scalars(self):
        return _FakeScalarResult(self._item)

    def scalar_one(self):
        return self._item

    def scalar_one_or_none(self):
        return self._item


class _FakeSession:
    def __init__(
        self,
        *,
        idea: Idea | None = None,
        animation: Animation | None = None,
        render: Render | None = None,
        publish_record: PublishRecord | None = None,
    ) -> None:
        self.idea = idea
        self.animation = animation
        self.render = render
        self.publish_record = publish_record
        self.execute_item = None
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def get(self, model, key):
        if model is Idea and self.idea is not None and self.idea.id == key:
            return self.idea
        if model is Animation and self.animation is not None and self.animation.id == key:
            return self.animation
        if model is Render and self.render is not None and self.render.id == key:
            return self.render
        if model is PublishRecord and self.publish_record is not None and self.publish_record.id == key:
            return self.publish_record
        return None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            try:
                obj.id = uuid4()
            except Exception:
                pass
        self.added.append(obj)

    def execute(self, _stmt):
        return _FakeExecuteResult(self.execute_item)

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


def test_ops_publish_record_requires_content_or_url_for_published_status(monkeypatch) -> None:
    now = datetime(2026, 2, 23, 13, 0, tzinfo=UTC)
    animation = Animation(
        id=uuid4(),
        animation_code="anim-003",
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

    try:
        api_main.ops_publish_record(
            api_main.PublishRecordCreateRequest(
                render_id=render.id,
                platform="youtube",
                status="manual_confirmed",
                content_id="",
                url="",
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "content_id_or_url" in str(exc.detail)


def test_ops_godot_compile_gdscript_returns_script_path(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 2, 23, 14, 0, tzinfo=UTC)
    idea = Idea(
        id=uuid4(),
        title="Idea",
        summary="Summary",
        what_to_expect="Expect",
        preview="Preview",
        status="ready_for_gate",
        created_at=now,
    )
    fake_session = _FakeSession(idea=idea)
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        api_main,
        "compile_idea_to_gdscript",
        lambda **kwargs: SimpleNamespace(
            script_hash="hash123",
            compiler_meta={"attempt_count": 1},
            validation_report={"syntax_ok": True, "errors": []},
        ),
    )
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)

    payload = api_main.ops_godot_compile_gdscript(
        api_main.GodotManualCompileRequest(
            idea_id=idea.id,
            out_root=str(tmp_path),
            validate_after_compile=False,
        ),
        _guard=None,
    )

    assert str(payload["idea_id"]) == str(idea.id)
    assert payload["script_hash"] == "hash123"
    assert str(payload["script_path"]).endswith(f"idea-{idea.id}/script.gd")
    assert fake_session.commits == 1
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "godot_manual_compile"]
    assert len(audits) == 1


def test_ops_godot_validate_uses_runner_and_audits(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "script.gd"
    script.write_text("extends Node2D\n")
    fake_session = _FakeSession()
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        api_main,
        "_run_godot_manual_step",
        lambda **kwargs: {
            "ok": True,
            "mode": "validate",
            "script_path": str(script),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": str(tmp_path / "godot.log"),
        },
    )

    payload = api_main.ops_godot_validate(
        api_main.GodotManualRunRequest(script_path=str(script)),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["mode"] == "validate"
    assert payload["script_path"] == str(script)
    assert fake_session.commits == 1
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "godot_manual_validate"]
    assert len(audits) == 1


def test_get_manual_godot_file_restricts_to_manual_root(monkeypatch, tmp_path: Path) -> None:
    manual_root = tmp_path / "manual-godot"
    manual_root.mkdir()
    allowed = manual_root / "preview.mp4"
    allowed.write_bytes(b"fake")
    monkeypatch.setattr(api_main, "_manual_godot_root", lambda: manual_root.resolve())

    response = api_main.get_manual_godot_file(path=str(allowed))
    assert response.path == str(allowed.resolve())

    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"fake")
    try:
        api_main.get_manual_godot_file(path=str(outside))
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403


def test_ops_godot_preview_defaults_out_path_to_manual_root(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "example.gd"
    script.write_text("extends Node2D\n")
    manual_root = tmp_path / "manual-godot"
    fake_session = _FakeSession()

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_manual_godot_root", lambda: manual_root.resolve())

    captured: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured.update(kwargs)
        out_path = kwargs.get("out_path")
        return {
            "ok": True,
            "mode": "preview",
            "script_path": str(script),
            "out_path": str(out_path) if out_path else None,
            "out_exists": False,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": None,
        }

    monkeypatch.setattr(api_main, "_run_godot_manual_step", _fake_run)

    payload = api_main.ops_godot_preview(
        api_main.GodotManualRunRequest(script_path=str(script)),
        _guard=None,
    )

    expected_out = manual_root / "example" / "preview.mp4"
    assert payload["out_path"] == str(expected_out.resolve())
    assert str(captured["out_path"]) == str(expected_out.resolve())


def test_ops_godot_validate_persists_manual_history(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "script.gd"
    script.write_text("extends Node2D\n")
    fake_session = _FakeSession()
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    now = datetime(2026, 2, 23, 15, 0, tzinfo=UTC)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)
    monkeypatch.setattr(
        api_main,
        "_run_godot_manual_step",
        lambda **kwargs: {
            "ok": True,
            "mode": "validate",
            "script_path": str(script.resolve()),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": str(tmp_path / "godot.log"),
        },
    )

    api_main.ops_godot_validate(api_main.GodotManualRunRequest(script_path=str(script)), _guard=None)

    lines = history_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = api_main.json.loads(lines[0])
    assert row["step"] == "validate"
    assert row["ok"] is True
    assert row["script_path"] == str(script.resolve())
    assert row["exit_code"] == 0


def test_append_manual_godot_history_rotates_to_max_lines(monkeypatch, tmp_path: Path) -> None:
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)
    monkeypatch.setattr(api_main, "_manual_godot_history_max_lines", lambda: 3)

    for i in range(5):
        api_main._append_manual_godot_history({"id": str(i), "recorded_at": f"2026-02-23T12:00:0{i}+00:00"})

    lines = history_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    ids = [api_main.json.loads(line)["id"] for line in lines]
    assert ids == ["2", "3", "4"]


def test_list_godot_manual_runs_reads_jsonl_and_filters(monkeypatch, tmp_path: Path) -> None:
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    script_a = str((tmp_path / "a.gd").resolve())
    script_b = str((tmp_path / "b.gd").resolve())
    history_file.write_text(
        "\n".join(
            [
                api_main.json.dumps(
                    {
                        "id": "1",
                        "recorded_at": "2026-02-23T12:00:00+00:00",
                        "step": "preview",
                        "ok": True,
                        "script_path": script_a,
                    }
                ),
                api_main.json.dumps(
                    {
                        "id": "2",
                        "recorded_at": "2026-02-23T13:00:00+00:00",
                        "step": "render",
                        "ok": False,
                        "script_path": script_b,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)

    rows = api_main.list_godot_manual_runs(limit=10, step="render", script_path=script_b, _guard=None)

    assert len(rows) == 1
    assert rows[0]["id"] == "2"
    assert rows[0]["step"] == "render"


def test_list_publish_records_returns_rows(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 9, 0, tzinfo=UTC)
    record = PublishRecord(
        id=uuid4(),
        render_id=uuid4(),
        platform_type="youtube",
        status="published",
        content_id="abc",
        url="https://example.test/abc",
        created_at=now,
        updated_at=now,
    )
    fake_session = _FakeSession()
    fake_session.execute_item = [record]
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)

    rows = api_main.list_publish_records(render_id=record.render_id, limit=10, offset=0)

    assert len(rows) == 1
    assert rows[0]["id"] == str(record.id)
    assert rows[0]["platform_type"] == "youtube"


def test_list_publish_records_allows_global_list_without_render_or_animation(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 10, 0, tzinfo=UTC)
    record = PublishRecord(
        id=uuid4(),
        render_id=uuid4(),
        platform_type="tiktok",
        status="failed",
        content_id=None,
        url=None,
        error_payload={"message": "upload failed"},
        created_at=now,
        updated_at=now,
    )
    fake_session = _FakeSession()
    fake_session.execute_item = [record]
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)

    rows = api_main.list_publish_records(limit=10, offset=0)

    assert len(rows) == 1
    assert rows[0]["status"] == "failed"


def test_planner_settings_roundtrip_and_invalid_timezone(monkeypatch, tmp_path: Path) -> None:
    settings_file = tmp_path / "planner" / "settings.json"
    monkeypatch.setattr(api_main, "_planner_settings_file", lambda: settings_file)

    default_payload = api_main.get_planner_settings()
    assert default_payload["target_per_day"] >= 1

    saved = api_main.set_planner_settings(
        api_main.PlannerSettingsUpdateRequest(
            timezone="UTC",
            daily_publish_hour=19,
            daily_publish_minute=30,
            publish_window_minutes=90,
            target_per_day=1,
        ),
        _guard=None,
    )
    assert saved["daily_publish_hour"] == 19
    assert saved["daily_publish_minute"] == 30
    assert settings_file.exists()

    roundtrip = api_main.get_planner_settings()
    assert roundtrip["daily_publish_hour"] == 19
    assert roundtrip["timezone"] == "UTC"

    try:
        api_main.set_planner_settings(
            api_main.PlannerSettingsUpdateRequest(
                timezone="Not/A_Timezone",
                daily_publish_hour=18,
                daily_publish_minute=0,
                publish_window_minutes=120,
                target_per_day=1,
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "planner_timezone_invalid"


def test_ops_metrics_daily_manual_upsert_creates_and_updates(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 12, 0, tzinfo=UTC)
    render = Render(
        id=uuid4(),
        animation_id=uuid4(),
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
    publish = PublishRecord(
        id=uuid4(),
        render_id=render.id,
        platform_type="youtube",
        status="published",
        content_id="abc123",
        url="https://example.test/watch?v=abc123",
        created_at=now,
        updated_at=now,
    )
    fake_session = _FakeSession(render=render, publish_record=publish)
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)

    payload = api_main.upsert_metrics_daily_manual(
        api_main.MetricsDailyManualUpsertRequest(
            platform_type="youtube",
            content_id="abc123",
            date=now.date(),
            publish_record_id=publish.id,
            render_id=render.id,
            views=100,
            likes=10,
        ),
        _guard=None,
    )

    assert payload["created"] is True
    metrics_objs = [obj for obj in fake_session.added if isinstance(obj, MetricsDaily)]
    assert len(metrics_objs) == 1
    metrics = metrics_objs[0]
    assert metrics.views == 100
    assert metrics.likes == 10
    fake_session.execute_item = metrics

    payload2 = api_main.upsert_metrics_daily_manual(
        api_main.MetricsDailyManualUpsertRequest(
            platform_type="youtube",
            content_id="abc123",
            date=now.date(),
            views=150,
            likes=12,
            comments=3,
        ),
        _guard=None,
    )
    assert payload2["created"] is False
    assert metrics.views == 150
    assert metrics.comments == 3


def test_ops_metrics_daily_manual_upsert_validates_publish_record_ref(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    try:
        api_main.upsert_metrics_daily_manual(
            api_main.MetricsDailyManualUpsertRequest(
                platform_type="youtube",
                content_id="abc",
                date=datetime(2026, 2, 24, tzinfo=UTC).date(),
                publish_record_id=uuid4(),
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "publish_record_not_found"


def test_get_planner_status_uses_snapshot(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        api_main,
        "_planner_status_snapshot",
        lambda _session: {
            "timezone": "UTC",
            "local_day": "2026-02-24",
            "in_window": True,
            "should_enqueue": True,
            "reason": "ready",
        },
    )
    payload = api_main.get_planner_status()
    assert payload["should_enqueue"] is True
    assert payload["reason"] == "ready"


def test_planner_tick_skips_when_not_ready(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        api_main,
        "_planner_status_snapshot",
        lambda _session: {
            "timezone": "UTC",
            "local_day": "2026-02-24",
            "in_window": False,
            "should_enqueue": False,
            "reason": "outside_window",
        },
    )
    payload = api_main.planner_tick(api_main.PlannerTickRequest(), _guard=None)
    assert payload["triggered"] is False
    assert payload["reason"] == "outside_window"


def test_planner_tick_enqueues_when_ready(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)

    calls = {"n": 0}

    def _snapshot(_session):
        calls["n"] += 1
        return {
            "timezone": "UTC",
            "local_day": "2026-02-24",
            "in_window": True,
            "should_enqueue": True,
            "reason": "ready",
        }

    monkeypatch.setattr(api_main, "_planner_status_snapshot", _snapshot)
    import pipeline.queue as queue_mod

    monkeypatch.setattr(
        queue_mod,
        "enqueue_pipeline",
        lambda dsl_template, out_root, idea_gate, idea_id: {
            "animation_id": uuid4(),
            "rq_generate_id": "rq-gen",
            "rq_render_id": "rq-render",
        },
    )
    payload = api_main.planner_tick(api_main.PlannerTickRequest(), _guard=None)
    assert payload["triggered"] is True
    assert payload["reason"] == "enqueued"
    assert payload["enqueue_result"]["rq_generate_id"] == "rq-gen"
