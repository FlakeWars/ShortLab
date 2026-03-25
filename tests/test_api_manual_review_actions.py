from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import api.main as api_main
import pytest
from fastapi import HTTPException
from db.models import AuditEvent, Animation, Idea, IdeaCandidate, MetricsDaily, PublishRecord, QCChecklistVersion, QCDecision, Render


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
        idea_candidate: IdeaCandidate | None = None,
        animation: Animation | None = None,
        render: Render | None = None,
        publish_record: PublishRecord | None = None,
    ) -> None:
        self.idea = idea
        self.idea_candidate = idea_candidate
        self.animation = animation
        self.render = render
        self.publish_record = publish_record
        self.execute_item = None
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def get(self, model, key):
        if model is Idea and self.idea is not None and self.idea.id == key:
            return self.idea
        if model is IdeaCandidate and self.idea_candidate is not None and self.idea_candidate.id == key:
            return self.idea_candidate
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

    def delete(self, obj):
        self.deleted.append(obj)

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
            decision_payload={
                "idea_intent_ok": True,
                "intro_readability_ok": True,
                "audio_quality_ok": True,
            },
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


def test_ops_qc_decide_rejects_accept_without_required_quality_flags(monkeypatch) -> None:
    now = datetime(2026, 3, 24, 12, 0, tzinfo=UTC)
    animation = Animation(
        id=uuid4(),
        animation_code="anim-qc-002",
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

    try:
        api_main.ops_qc_decide(
            api_main.QcDecisionCreateRequest(
                animation_id=animation.id,
                result="accepted",
                decision_payload={"idea_intent_ok": True, "intro_readability_ok": False},
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "qc_accept_requires_true_flags" in str(exc.detail)


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


def test_ops_publish_record_rejects_url_platform_mismatch(monkeypatch) -> None:
    now = datetime(2026, 3, 24, 13, 0, tzinfo=UTC)
    animation = Animation(
        id=uuid4(),
        animation_code="anim-003b",
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

    try:
        api_main.ops_publish_record(
            api_main.PublishRecordCreateRequest(
                render_id=render.id,
                platform="youtube",
                status="published",
                url="https://www.tiktok.com/@creator/video/123",
            ),
            _guard=None,
        )
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "platform_mismatch" in str(exc.detail)


def test_delete_candidate_hard_delete(monkeypatch) -> None:
    now = datetime(2026, 3, 24, 15, 0, tzinfo=UTC)
    candidate = IdeaCandidate(
        id=uuid4(),
        idea_batch_id=uuid4(),
        title="Candidate to trash",
        summary="summary",
        what_to_expect="expectation",
        preview="preview",
        generator_source="manual",
        similarity_status="ok",
        capability_status="feasible",
        status="later",
        selected=False,
        created_at=now,
    )
    fake_session = _FakeSession(idea_candidate=candidate)
    fake_session.execute_item = 0

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)

    payload = api_main.delete_candidate(candidate_id=candidate.id, _guard=None)

    assert str(payload["id"]) == str(candidate.id)
    assert payload["status"] == "deleted"
    assert candidate in fake_session.deleted
    assert fake_session.commits == 1
    assert fake_session.rollbacks == 0

    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "idea_candidate_delete"]
    assert len(audits) == 1
    assert audits[0].payload["action"] == "hard_delete"


def test_cleanup_later_candidates_deletes_only_expired(monkeypatch) -> None:
    now = datetime(2026, 3, 24, 14, 0, tzinfo=UTC)
    old_candidate = IdeaCandidate(
        id=uuid4(),
        idea_batch_id=uuid4(),
        title="Old later",
        summary="summary",
        what_to_expect="expectation",
        preview="preview",
        generator_source="manual",
        similarity_status="ok",
        capability_status="feasible",
        status="later",
        selected=False,
        decision_at=now - timedelta(days=45),
        created_at=now - timedelta(days=60),
    )
    fresh_candidate = IdeaCandidate(
        id=uuid4(),
        idea_batch_id=uuid4(),
        title="Fresh later",
        summary="summary",
        what_to_expect="expectation",
        preview="preview",
        generator_source="manual",
        similarity_status="ok",
        capability_status="feasible",
        status="later",
        selected=False,
        decision_at=now - timedelta(days=5),
        created_at=now - timedelta(days=10),
    )

    fake_session = _FakeSession()
    fake_session.execute_item = [old_candidate, fresh_candidate]

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)

    payload = api_main.cleanup_later_candidates(
        api_main.LaterCleanupRequest(max_age_days=30, dry_run=False),
        _guard=None,
    )

    assert payload["expired_count"] == 1
    assert payload["deleted_count"] == 1
    assert str(old_candidate.id) in payload["deleted_ids"]
    assert old_candidate in fake_session.deleted
    assert fresh_candidate not in fake_session.deleted
    assert fake_session.commits == 1


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


def test_godot_manual_run_request_allows_60s_runtime() -> None:
    req = api_main.GodotManualRunRequest(script_path="/tmp/example.gd", seconds=60.0)
    assert req.seconds == 60.0


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


def test_ops_godot_estimate_duration_returns_recommendation(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "script.gd"
    script.write_text("extends Node2D\n")
    fake_session = _FakeSession()
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    now = datetime(2026, 2, 24, 10, 0, tzinfo=UTC)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)
    monkeypatch.setattr(
        api_main,
        "_run_godot_manual_step",
        lambda **kwargs: {
            "ok": True,
            "mode": "estimate",
            "script_path": str(script.resolve()),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": str(tmp_path / "godot.log"),
            "estimate": {
                "reached": True,
                "effect_time_s": 18.0,
                "threshold": 0.85,
                "hold_s": 2.0,
                "progress": 0.91,
                "support": True,
            },
        },
    )

    payload = api_main.ops_godot_estimate_duration(
        api_main.GodotEstimateDurationRequest(
            script_path=str(script),
            target_duration_s=30.0,
            scout_seconds=60.0,
            tail_seconds=3.0,
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["method"] == "progress_threshold"
    assert payload["recommended_sim_duration_s"] == 21.0
    assert payload["recommended_speed_factor"] == 0.7
    assert payload["intent_reached"] is True
    assert payload["intent_reached_at_s"] == 18.0
    assert payload["target_runtime_s"] == 60.0
    assert fake_session.commits == 1
    lines = history_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = api_main.json.loads(lines[0])
    assert row["step"] == "estimate"
    assert row["recommended_sim_duration_s"] == 21.0


def test_ops_godot_intent_check_returns_pass_with_runtime_override(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "script.gd"
    script.write_text("extends Node2D\n")
    fake_session = _FakeSession()
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    now = datetime(2026, 3, 24, 9, 0, tzinfo=UTC)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)
    monkeypatch.setattr(
        api_main,
        "_run_godot_manual_step",
        lambda **kwargs: {
            "ok": True,
            "mode": "estimate",
            "script_path": str(script.resolve()),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": str(tmp_path / "godot.log"),
            "estimate": {
                "reached": True,
                "effect_time_s": 20.0,
                "threshold": 0.85,
                "hold_s": 2.0,
                "progress": 0.93,
                "support": True,
            },
        },
    )

    payload = api_main.ops_godot_intent_check(
        api_main.GodotIntentCheckRequest(
            script_path=str(script),
            runtime_override_s=75.0,
            scout_seconds=90.0,
            tail_seconds=2.0,
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["mode"] == "intent_check"
    assert payload["target_runtime_s"] == 75.0
    assert payload["intent_status"] == "pass"
    assert payload["recommended_sim_duration_s"] == 22.0
    assert payload["recommended_speed_factor"] == 22.0 / 75.0
    assert payload["blocking_reason"] is None
    assert fake_session.commits == 1
    lines = history_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = api_main.json.loads(lines[0])
    assert row["step"] == "intent_check"
    assert row["intent_status"] == "pass"


def test_ops_godot_intent_check_returns_blocked_when_not_reached(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "script.gd"
    script.write_text("extends Node2D\n")
    fake_session = _FakeSession()
    history_file = tmp_path / "manual-godot" / "_history" / "manual-runs.jsonl"
    now = datetime(2026, 3, 24, 9, 30, tzinfo=UTC)

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_manual_godot_history_file", lambda: history_file)
    monkeypatch.setattr(
        api_main,
        "_run_godot_manual_step",
        lambda **kwargs: {
            "ok": True,
            "mode": "estimate",
            "script_path": str(script.resolve()),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "log_file": str(tmp_path / "godot.log"),
            "estimate": {
                "reached": False,
                "effect_time_s": -1.0,
                "threshold": 0.85,
                "hold_s": 2.0,
                "progress": 0.41,
                "support": True,
            },
        },
    )

    payload = api_main.ops_godot_intent_check(
        api_main.GodotIntentCheckRequest(
            script_path=str(script),
            scout_seconds=40.0,
            runtime_override_s=60.0,
            tail_seconds=2.0,
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["intent_reached"] is False
    assert payload["intent_status"] == "blocked"
    assert payload["blocking_reason"] == "intent_not_reached_in_scout_horizon"
    assert payload["recommended_sim_duration_s"] == 40.0
    assert payload["recommended_speed_factor"] == 40.0 / 60.0
    lines = history_file.read_text(encoding="utf-8").splitlines()
    row = api_main.json.loads(lines[0])
    assert row["step"] == "intent_check"
    assert row["blocking_reason"] == "intent_not_reached_in_scout_horizon"


def test_ops_overlay_intro_generates_output(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 0, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.mp4"
    out_path = tmp_path / "final.intro.mp4"
    input_path.write_bytes(b"fake")

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(
        api_main,
        "_run_intro_overlay_ffmpeg",
        lambda **kwargs: {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
        },
    )

    payload = api_main.ops_overlay_intro(
        api_main.IntroOverlayRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            intro_text="Animation rule: dots split on collision",
            duration_s=1.5,
            font_size=48,
            language="en",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["input_path"] == str(input_path.resolve())
    assert payload["out_path"] == str(out_path)
    assert payload["intro_text"] == "Animation rule: dots split on collision"
    assert payload["language"] == "en"
    assert fake_session.commits == 1
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "intro_overlay_generate"]
    assert len(audits) == 1
    assert payload["translation_meta"] is not None


def test_ops_overlay_intro_uses_llm_translation_when_available(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 0, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.mp4"
    out_path = tmp_path / "final.intro.mp4"
    input_path.write_bytes(b"fake")

    class _FakeMediator:
        def generate_json(self, **kwargs):
            assert kwargs["task_type"] == "intro_translate"
            return (
                {"intro_text_en": "Animation rule: circles split on collision."},
                {"provider": "openai", "model": "gpt-4o-mini"},
            )

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "get_mediator", lambda: _FakeMediator())
    monkeypatch.setattr(
        api_main,
        "_run_intro_overlay_ffmpeg",
        lambda **kwargs: {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
        },
    )

    payload = api_main.ops_overlay_intro(
        api_main.IntroOverlayRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            intro_text="Zasada animacji: kółka dzielą się po zderzeniu",
            duration_s=1.5,
            font_size=48,
            language="en",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["intro_text"] == "Animation rule: circles split on collision."
    assert payload["translation_meta"]["status"] == "translated"
    assert payload["translation_meta"]["provider"] == "openai"


def test_ops_overlay_intro_translation_fallback_to_sanitize(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 0, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.mp4"
    out_path = tmp_path / "final.intro.mp4"
    input_path.write_bytes(b"fake")

    class _FailingMediator:
        def generate_json(self, **kwargs):
            raise RuntimeError("translate_error")

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "get_mediator", lambda: _FailingMediator())
    monkeypatch.setattr(
        api_main,
        "_run_intro_overlay_ffmpeg",
        lambda **kwargs: {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
        },
    )

    payload = api_main.ops_overlay_intro(
        api_main.IntroOverlayRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            intro_text="Zasada animacji: kółka dzielą się po zderzeniu",
            duration_s=1.5,
            font_size=48,
            language="en",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["intro_text"].startswith("Animation rule:")
    assert payload["translation_meta"]["status"] == "fallback"


def test_ops_overlay_intro_translation_disabled_by_env(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 0, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.mp4"
    out_path = tmp_path / "final.intro.mp4"
    input_path.write_bytes(b"fake")

    class _FailIfCalledMediator:
        def generate_json(self, **kwargs):
            raise AssertionError("LLM should not be called when translation is disabled")

    monkeypatch.setenv("INTRO_EN_TRANSLATE_ENABLED", "0")
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "get_mediator", lambda: _FailIfCalledMediator())
    monkeypatch.setattr(
        api_main,
        "_run_intro_overlay_ffmpeg",
        lambda **kwargs: {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
        },
    )

    payload = api_main.ops_overlay_intro(
        api_main.IntroOverlayRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            intro_text="Zasada animacji: kółka dzielą się po zderzeniu",
            duration_s=1.5,
            font_size=48,
            language="en",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["intro_text"].startswith("Animation rule:")
    assert payload["translation_meta"]["attempted"] is False
    assert payload["translation_meta"]["reason"] == "disabled_by_env"


def test_ops_overlay_intro_translation_empty_result_falls_back(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 0, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.mp4"
    out_path = tmp_path / "final.intro.mp4"
    input_path.write_bytes(b"fake")

    class _EmptyMediator:
        def generate_json(self, **kwargs):
            return ({"intro_text_en": ""}, {"provider": "openai", "model": "gpt-4o-mini"})

    monkeypatch.delenv("INTRO_EN_TRANSLATE_ENABLED", raising=False)
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "get_mediator", lambda: _EmptyMediator())
    monkeypatch.setattr(
        api_main,
        "_run_intro_overlay_ffmpeg",
        lambda **kwargs: {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
        },
    )

    payload = api_main.ops_overlay_intro(
        api_main.IntroOverlayRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            intro_text="Zasada animacji: kółka dzielą się po zderzeniu",
            duration_s=1.5,
            font_size=48,
            language="en",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["intro_text"].startswith("Animation rule:")
    assert payload["translation_meta"]["status"] == "empty_result"


def test_run_intro_overlay_ffmpeg_uses_magick_fallback_when_drawtext_missing(
    monkeypatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "in.mp4"
    out_path = tmp_path / "out.mp4"
    input_path.write_bytes(b"fake")

    called: dict[str, object] = {}

    monkeypatch.setattr(api_main, "_ffmpeg_has_filter", lambda name: False)
    monkeypatch.setattr(api_main.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)

    def _fake_fallback(**kwargs):
        called.update(kwargs)
        return {
            "ok": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "out_exists": True,
            "out_path": str(out_path),
            "fallback": "magick_overlay",
        }

    monkeypatch.setattr(api_main, "_run_intro_overlay_ffmpeg_image_fallback", _fake_fallback)

    payload = api_main._run_intro_overlay_ffmpeg(
        input_path=input_path,
        out_path=out_path,
        text="Animation rule: blue ball collects red dots.",
        duration_s=1.5,
        font_size=48,
    )

    assert payload["ok"] is True
    assert payload["fallback"] == "magick_overlay"
    assert called["input_path"] == input_path
    assert called["out_path"] == out_path


def test_run_intro_overlay_ffmpeg_reports_error_when_drawtext_missing_and_no_magick(
    monkeypatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "in.mp4"
    out_path = tmp_path / "out.mp4"
    input_path.write_bytes(b"fake")

    monkeypatch.setattr(api_main, "_ffmpeg_has_filter", lambda name: False)
    monkeypatch.setattr(
        api_main.shutil,
        "which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )

    payload = api_main._run_intro_overlay_ffmpeg(
        input_path=input_path,
        out_path=out_path,
        text="Animation rule: blue ball collects red dots.",
        duration_s=1.5,
        font_size=48,
    )

    assert payload["ok"] is False
    assert payload["error"] == "drawtext_missing_and_magick_not_found"


def test_sanitize_intro_text_maps_polish_prefix_to_english() -> None:
    value = api_main._sanitize_intro_text(
        text="Zasada animacji: Kółka zderzają się i dzielą",
        language="en",
        max_chars=80,
    )
    assert value == "Animation rule: Kolka zderzaja sie i dziela"


def test_sanitize_intro_text_en_fallback_when_text_strips_to_empty() -> None:
    value = api_main._sanitize_intro_text(text="żźćń", language="en", max_chars=80)
    assert value == "A short animation with a clear rule."


def test_ops_audio_mix_generates_output(monkeypatch, tmp_path: Path) -> None:
    now = datetime(2026, 3, 24, 11, 30, tzinfo=UTC)
    fake_session = _FakeSession()
    input_path = tmp_path / "final.intro.mp4"
    music_path = tmp_path / "music.mp3"
    out_path = tmp_path / "final.audio.mp4"
    input_path.write_bytes(b"fake")
    music_path.write_bytes(b"fake")
    captured: dict[str, object] = {}

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(
        api_main,
        "_run_audio_mix_ffmpeg",
        lambda **kwargs: (
            captured.update(kwargs)
            or {
                "ok": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "out_exists": True,
                "out_path": str(out_path),
            }
        ),
    )

    payload = api_main.ops_audio_mix(
        api_main.AudioMixRequest(
            input_path=str(input_path),
            out_path=str(out_path),
            music_path=str(music_path),
            keep_source_audio=False,
            music_gain_db=-18.0,
            sfx_gain_db=-6.0,
            audio_profile="speech",
        ),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["input_path"] == str(input_path.resolve())
    assert payload["out_path"] == str(out_path)
    assert payload["music_path"] == str(music_path.resolve())
    assert payload["keep_source_audio"] is False
    assert payload["normalize_loudness"] is True
    assert payload["target_lufs"] == -16.0
    assert payload["true_peak_db"] == -1.0
    assert payload["audio_profile"] == "speech"
    assert fake_session.commits == 1
    assert captured["normalize_loudness"] is True
    assert captured["target_lufs"] == -16.0
    assert captured["true_peak_db"] == -1.0
    audits = [obj for obj in fake_session.added if getattr(obj, "event_type", None) == "audio_mix_generate"]
    assert len(audits) == 1


def test_build_insights_summary_rolls_up_windows_and_recommendation() -> None:
    now = datetime(2026, 3, 24, 12, 0, tzinfo=UTC)
    metrics_rows = [
        MetricsDaily(
            id=uuid4(),
            platform_type="youtube",
            content_id="yt-1",
            date=date(2026, 3, 24),
            views=1000,
            likes=30,
            comments=10,
            shares=10,
            watch_time_seconds=22000,
            avg_view_percentage=42.0,
            created_at=now,
        ),
        MetricsDaily(
            id=uuid4(),
            platform_type="tiktok",
            content_id="tt-1",
            date=date(2026, 3, 23),
            views=700,
            likes=15,
            comments=4,
            shares=6,
            watch_time_seconds=12000,
            avg_view_percentage=39.0,
            created_at=now,
        ),
    ]
    publish_rows = [
        PublishRecord(
            id=uuid4(),
            render_id=uuid4(),
            platform_type="youtube",
            status="published",
            content_id="yt-1",
            created_at=now - timedelta(hours=6),
            updated_at=now,
        ),
        PublishRecord(
            id=uuid4(),
            render_id=uuid4(),
            platform_type="tiktok",
            status="manual_confirmed",
            content_id="tt-1",
            created_at=now - timedelta(days=2),
            updated_at=now,
        ),
    ]

    payload = api_main._build_insights_summary(metrics_rows=metrics_rows, publish_rows=publish_rows, now=now)

    assert payload["windows"]["24h"]["views"] == 1000
    assert payload["windows"]["72h"]["views"] == 1700
    assert payload["windows"]["7d"]["published_count"] >= 2
    assert isinstance(payload["top_content_14d"], list)
    assert payload["recommendation_code"] in {
        "improve_pacing",
        "improve_hook",
        "increase_distribution",
        "keep_iteration",
    }


def test_build_insights_summary_handles_empty_data() -> None:
    now = datetime(2026, 3, 24, 13, 0, tzinfo=UTC)
    payload = api_main._build_insights_summary(metrics_rows=[], publish_rows=[], now=now)

    assert payload["windows"]["24h"]["views"] == 0
    assert payload["windows"]["14d"]["published_count"] == 0
    assert payload["recommendation_code"] == "insufficient_data"


def test_build_insights_summary_audio_profiles_rollup() -> None:
    now = datetime(2026, 3, 24, 13, 0, tzinfo=UTC)
    metrics_rows = [
        MetricsDaily(
            id=uuid4(),
            platform_type="youtube",
            content_id="yt-1",
            date=date(2026, 3, 24),
            views=1000,
            likes=30,
            comments=10,
            shares=10,
            watch_time_seconds=22000,
            avg_view_percentage=42.0,
            avg_view_duration_seconds=22,
            extra_metrics={"audio_profile": "speech"},
            created_at=now,
        ),
        MetricsDaily(
            id=uuid4(),
            platform_type="youtube",
            content_id="yt-2",
            date=date(2026, 3, 23),
            views=500,
            likes=10,
            comments=4,
            shares=5,
            watch_time_seconds=9000,
            avg_view_percentage=40.0,
            avg_view_duration_seconds=18,
            extra_metrics={"audio_profile": "speech"},
            created_at=now,
        ),
        MetricsDaily(
            id=uuid4(),
            platform_type="tiktok",
            content_id="tt-1",
            date=date(2026, 3, 23),
            views=700,
            likes=15,
            comments=4,
            shares=6,
            watch_time_seconds=12000,
            avg_view_percentage=39.0,
            avg_view_duration_seconds=17,
            extra_metrics={"audio_profile": "music"},
            created_at=now,
        ),
    ]

    payload = api_main._build_insights_summary(metrics_rows=metrics_rows, publish_rows=[], now=now)

    assert "audio_profiles_14d" in payload
    rows = payload["audio_profiles_14d"]
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["audio_profile"] == "speech"
    assert rows[0]["views"] == 1500
    assert rows[0]["watch_time_seconds"] == 31000
    assert rows[0]["rows"] == 2


def test_build_insights_summary_intro_translate_rollup() -> None:
    now = datetime(2026, 3, 24, 13, 0, tzinfo=UTC)
    intro_audit_rows = [
        AuditEvent(
            id=uuid4(),
            event_type="intro_overlay_generate",
            source="api",
            actor_user_id=None,
            payload={"translation_meta": {"attempted": True, "status": "translated"}},
            occurred_at=now - timedelta(days=1),
        ),
        AuditEvent(
            id=uuid4(),
            event_type="intro_overlay_generate",
            source="api",
            actor_user_id=None,
            payload={"translation_meta": {"attempted": True, "status": "fallback"}},
            occurred_at=now - timedelta(days=2),
        ),
        AuditEvent(
            id=uuid4(),
            event_type="intro_overlay_generate",
            source="api",
            actor_user_id=None,
            payload={"translation_meta": {"attempted": True, "status": "empty_result"}},
            occurred_at=now - timedelta(days=3),
        ),
        AuditEvent(
            id=uuid4(),
            event_type="intro_overlay_generate",
            source="api",
            actor_user_id=None,
            payload={"translation_meta": {"attempted": False, "reason": "disabled_by_env"}},
            occurred_at=now - timedelta(days=4),
        ),
    ]

    payload = api_main._build_insights_summary(
        metrics_rows=[],
        publish_rows=[],
        intro_audit_rows=intro_audit_rows,
        now=now,
    )

    assert payload["intro_translate_14d"]["rows_total"] == 4
    assert payload["intro_translate_14d"]["attempted"] == 3
    assert payload["intro_translate_14d"]["translated"] == 1
    assert payload["intro_translate_14d"]["fallback"] == 1
    assert payload["intro_translate_14d"]["empty_result"] == 1
    assert payload["intro_translate_14d"]["disabled"] == 1
    assert payload["intro_translate_14d"]["fallback_share_attempted"] == pytest.approx(2 / 3, rel=1e-6)


def test_publish_connector_status_reflects_env_keys(monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("YOUTUBE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TIKTOK_REFRESH_TOKEN", raising=False)

    status = api_main._publish_connector_status()
    assert status["youtube"]["ready"] is False
    assert status["tiktok"]["ready"] is False

    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "x")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "y")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "z")
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "a")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "b")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "c")

    status_ready = api_main._publish_connector_status()
    assert status_ready["youtube"]["ready"] is True
    assert status_ready["youtube"]["mode"] == "api"
    assert status_ready["tiktok"]["ready"] is True
    assert status_ready["tiktok"]["mode"] == "api"


def test_system_status_cache_ttl_defaults_and_bounds(monkeypatch) -> None:
    monkeypatch.delenv("SYSTEM_STATUS_CACHE_TTL_S", raising=False)
    assert api_main._system_status_cache_ttl_s() == 5

    monkeypatch.setenv("SYSTEM_STATUS_CACHE_TTL_S", "0")
    assert api_main._system_status_cache_ttl_s() == 0

    monkeypatch.setenv("SYSTEM_STATUS_CACHE_TTL_S", "-10")
    assert api_main._system_status_cache_ttl_s() == 0

    monkeypatch.setenv("SYSTEM_STATUS_CACHE_TTL_S", "999")
    assert api_main._system_status_cache_ttl_s() == 60

    monkeypatch.setenv("SYSTEM_STATUS_CACHE_TTL_S", "abc")
    assert api_main._system_status_cache_ttl_s() == 5


def test_publish_readiness_summary_reads_latest_report(monkeypatch, tmp_path: Path) -> None:
    summary_file = tmp_path / "reports" / "publish-readiness-summary-latest.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        api_main.json.dumps(
            {
                "generated_at": "2026-03-24T16:00:00+00:00",
                "overall_pass": False,
                "components": {
                    "mcp_publish_audit": {"pass": True, "reason": "ok"},
                    "mcp_compliance_check": {"pass": False, "reason": "pending"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_main, "_publish_readiness_summary_file", lambda: summary_file)

    payload = api_main.publish_readiness_summary(_guard=None)

    assert payload["overall_pass"] is False
    assert payload["components"]["mcp_publish_audit"]["pass"] is True
    assert payload["source_file"] == str(summary_file)


def test_publish_readiness_summary_raises_when_missing(monkeypatch, tmp_path: Path) -> None:
    summary_file = tmp_path / "reports" / "publish-readiness-summary-latest.json"
    monkeypatch.setattr(api_main, "_publish_readiness_summary_file", lambda: summary_file)

    try:
        api_main.publish_readiness_summary(_guard=None)
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "publish_readiness_summary_missing"
    else:
        raise AssertionError("Expected HTTPException for missing summary file")


def test_publish_readiness_summary_raises_when_invalid(monkeypatch, tmp_path: Path) -> None:
    summary_file = tmp_path / "reports" / "publish-readiness-summary-latest.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(api_main, "_publish_readiness_summary_file", lambda: summary_file)

    try:
        api_main.publish_readiness_summary(_guard=None)
    except HTTPException as exc:
        assert exc.status_code == 500
        assert exc.detail == "publish_readiness_summary_invalid"
    else:
        raise AssertionError("Expected HTTPException for invalid summary file")


def test_ops_publish_readiness_refresh_runs_scripts_and_writes_audit(monkeypatch) -> None:
    fake_session = _FakeSession()
    now = datetime(2026, 3, 24, 16, 10, tzinfo=UTC)
    actor = uuid4()
    calls: list[tuple[str, tuple[str, ...], int]] = []

    def _fake_run_local_script(script_name: str, args: list[str], timeout_s: int = 120) -> dict:
        calls.append((script_name, tuple(args), timeout_s))
        return {
            "ok": True,
            "script": script_name,
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
        }

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_run_local_script", _fake_run_local_script)
    monkeypatch.setattr(
        api_main,
        "_read_publish_readiness_summary",
        lambda: ({"overall_pass": True, "components": {}}, None),
    )

    payload = api_main.ops_publish_readiness_refresh(
        api_main.PublishReadinessRefreshRequest(actor=actor),
        _guard=None,
    )

    assert payload["ok"] is True
    assert payload["overall_pass"] is True
    assert payload["summary_available"] is True
    assert len(payload["script_results"]) == 4
    assert len(calls) == 4
    assert calls[-1][0] == "publish-readiness-summary.py"
    assert fake_session.commits == 1
    audit_events = [obj for obj in fake_session.added if isinstance(obj, api_main.AuditEvent)]
    assert len(audit_events) == 1
    assert audit_events[0].event_type == "publish_readiness_refresh"
    assert audit_events[0].actor_user_id == actor


def test_ops_publish_readiness_refresh_reports_script_failure(monkeypatch) -> None:
    fake_session = _FakeSession()
    now = datetime(2026, 3, 24, 16, 12, tzinfo=UTC)

    def _fake_run_local_script(script_name: str, args: list[str], timeout_s: int = 120) -> dict:
        if script_name == "mcp-compliance-check.py":
            return {
                "ok": False,
                "script": script_name,
                "exit_code": 2,
                "stdout": "",
                "stderr": "failed",
            }
        return {
            "ok": True,
            "script": script_name,
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
        }

    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(api_main, "_utc_now", lambda: now)
    monkeypatch.setattr(api_main, "_run_local_script", _fake_run_local_script)
    monkeypatch.setattr(
        api_main,
        "_read_publish_readiness_summary",
        lambda: ({"overall_pass": False, "components": {}}, None),
    )

    payload = api_main.ops_publish_readiness_refresh(
        api_main.PublishReadinessRefreshRequest(),
        _guard=None,
    )

    assert payload["ok"] is False
    assert payload["scripts_ok"] is False
    assert payload["overall_pass"] is False
    failed = [row for row in payload["script_results"] if row.get("ok") is False]
    assert any(row.get("script") == "mcp-compliance-check.py" for row in failed)


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


def test_list_publish_records_accepts_platform_and_status_filters(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 10, 30, tzinfo=UTC)
    record = PublishRecord(
        id=uuid4(),
        render_id=uuid4(),
        platform_type="youtube",
        status="manual_confirmed",
        content_id="xyz",
        url="https://example.test/xyz",
        created_at=now,
        updated_at=now,
    )
    fake_session = _FakeSession()
    fake_session.execute_item = [record]
    monkeypatch.setattr(api_main, "SessionLocal", lambda: fake_session)

    rows = api_main.list_publish_records(
        platform_type="youtube",
        status="manual_confirmed",
        limit=10,
        offset=0,
    )

    assert len(rows) == 1
    assert rows[0]["platform_type"] == "youtube"
    assert rows[0]["status"] == "manual_confirmed"


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
            audio_profile="speech",
        ),
        _guard=None,
    )

    assert payload["created"] is True
    metrics_objs = [obj for obj in fake_session.added if isinstance(obj, MetricsDaily)]
    assert len(metrics_objs) == 1
    metrics = metrics_objs[0]
    assert metrics.views == 100
    assert metrics.likes == 10
    assert isinstance(metrics.extra_metrics, dict)
    assert metrics.extra_metrics.get("audio_profile") == "speech"
    assert payload["audio_profile"] == "speech"
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
    assert payload2["audio_profile"] == "speech"


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
