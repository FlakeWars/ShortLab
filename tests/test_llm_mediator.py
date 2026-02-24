from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import llm.mediator as mediator_module
from llm.mediator import LLMMediator


class _DBFallbackMediator(LLMMediator):
    def _load_state_db(self) -> bool:
        return False

    def _persist_state_db(self) -> bool:
        return False


class _DBOnlyMediator(LLMMediator):
    def __init__(self) -> None:
        self.db_persist_calls = 0
        super().__init__()

    def _load_state_db(self) -> bool:
        self._metrics = {}
        self._spent_usd_total = 0.0
        self._budget_day = self._today_utc()
        return True

    def _persist_state_db(self) -> bool:
        self.db_persist_calls += 1
        return True


class _FakeQuery:
    def __init__(self, model, storage: dict[type, list[object]]) -> None:
        self._model = model
        self._storage = storage
        self._filters: dict[str, object] = {}
        self._limit: int | None = None

    def order_by(self, *_args):
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    def filter(self, *criteria):
        for criterion in criteria:
            key = criterion.left.key
            value = getattr(criterion.right, "value", None)
            self._filters[key] = value
        return self

    def all(self):
        rows = self._apply_filters()
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def one_or_none(self):
        rows = self._apply_filters()
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows[0] if rows else None

    def _apply_filters(self):
        rows = list(self._storage.get(self._model, []))
        if not self._filters and self._model.__name__ == "LLMMediatorBudgetDaily":
            rows = sorted(rows, key=lambda row: row.day, reverse=True)
            return rows
        for key, value in self._filters.items():
            rows = [row for row in rows if getattr(row, key) == value]
        return rows


class _FakeSession:
    def __init__(self, storage: dict[type, list[object]]) -> None:
        self._storage = storage

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def query(self, model):
        return _FakeQuery(model, self._storage)

    def get(self, model, key):
        for row in self._storage.get(model, []):
            if getattr(row, "day", None) == key:
                return row
        return None

    def add(self, obj):
        bucket = self._storage.setdefault(type(obj), [])
        if obj not in bucket:
            bucket.append(obj)

    def commit(self):
        return None


def test_file_backend_persists_and_loads(monkeypatch, tmp_path: Path) -> None:
    state_path = tmp_path / "mediator-state.json"
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "file")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(state_path))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "12.5")

    first = LLMMediator()
    first._metrics = {
        "idea_generate|openai|gpt-4o-mini": {
            "calls": 1.0,
            "success": 1.0,
            "errors": 0.0,
            "retries": 0.0,
            "latency_ms_total": 10.0,
            "prompt_tokens_total": 100.0,
            "completion_tokens_total": 50.0,
            "estimated_cost_usd_total": 0.01,
        }
    }
    first._spent_usd_total = 0.5
    first._persist_state()

    second = LLMMediator()
    snap = second.get_metrics_snapshot()
    assert snap["state_backend"] == "file"
    assert snap["budget"]["spent_usd_total"] == 0.5
    assert "idea_generate|openai|gpt-4o-mini" in snap["routes"]
    assert state_path.exists()


def test_db_backend_falls_back_to_file_when_db_unavailable(monkeypatch, tmp_path: Path) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    state_path = tmp_path / "mediator-state.json"
    state_path.write_text(
        json.dumps(
            {
                "routes": {
                    "idea_generate|openai|gpt-4o-mini": {
                        "calls": 2.0,
                        "success": 2.0,
                        "errors": 0.0,
                        "retries": 0.0,
                        "latency_ms_total": 20.0,
                        "prompt_tokens_total": 120.0,
                        "completion_tokens_total": 80.0,
                        "estimated_cost_usd_total": 0.02,
                    }
                },
                "budget": {"budget_day": today, "spent_usd_total": 1.25, "daily_budget_usd": 5.0},
            }
        )
    )
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "db")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(state_path))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "5")

    mediator = _DBFallbackMediator()
    snap = mediator.get_metrics_snapshot()
    assert snap["state_backend"] == "db"
    assert snap["budget"]["spent_usd_total"] == 1.25
    assert "idea_generate|openai|gpt-4o-mini" in snap["routes"]


def test_db_backend_does_not_write_state_file_when_db_persist_succeeds(monkeypatch, tmp_path: Path) -> None:
    state_path = tmp_path / "mediator-state.json"
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "db")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(state_path))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "0")

    mediator = _DBOnlyMediator()
    mediator._metrics = {
        "idea_generate|openai|gpt-4o-mini": {
            "calls": 1.0,
            "success": 1.0,
            "errors": 0.0,
            "retries": 0.0,
            "latency_ms_total": 1.0,
            "prompt_tokens_total": 1.0,
            "completion_tokens_total": 1.0,
            "estimated_cost_usd_total": 0.0,
        }
    }
    mediator._persist_state()
    assert mediator.db_persist_calls == 1
    assert not state_path.exists()


def test_db_backend_roundtrip_with_fake_session(monkeypatch, tmp_path: Path) -> None:
    storage: dict[type, list[object]] = {}

    def _session_factory():
        return _FakeSession(storage)

    monkeypatch.setattr(mediator_module, "SessionLocal", _session_factory)
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "db")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(tmp_path / "ignored.json"))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "7")

    first = LLMMediator()
    first._metrics = {
        "idea_generate|openai|gpt-4o-mini": {
            "calls": 3.0,
            "success": 2.0,
            "errors": 1.0,
            "retries": 1.0,
            "latency_ms_total": 42.0,
            "prompt_tokens_total": 300.0,
            "completion_tokens_total": 120.0,
            "estimated_cost_usd_total": 0.21,
        }
    }
    first._spent_usd_total = 1.75
    first._persist_state()

    second = LLMMediator()
    snap = second.get_metrics_snapshot()
    assert snap["state_backend"] == "db"
    assert snap["budget"]["spent_usd_total"] == 1.75
    assert snap["routes"]["idea_generate|openai|gpt-4o-mini"]["calls"] == 3.0


def test_iterative_token_budget_overrides_loaded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "file")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv(
        "LLM_ITERATIVE_MODEL_TOKEN_LIMITS",
        '{"openai:gpt-5.2-codex":200000,"openai:gpt-5.1-codex-mini":2000000}',
    )
    mediator = LLMMediator()
    assert mediator._token_budget_models["openai:gpt-5.2-codex"] == 200000
    assert mediator._token_budget_models["openai:gpt-5.1-codex-mini"] == 2000000


def test_generate_json_falls_back_on_token_budget_exceeded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "file")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv(
        "LLM_ITERATIVE_ROUTE_MODELS",
        "openai:gpt-5.2-codex,openai:gpt-5.1-codex-mini",
    )
    monkeypatch.setenv("LLM_ITERATIVE_MODEL_TOKEN_LIMITS", '{"openai:gpt-5.2-codex":1}')
    monkeypatch.setenv("LLM_ROUTE_IDEA_GENERATE_API_KEY_ENV", "OPENAI_API_KEY")
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODEL", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDERS", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODELS", raising=False)
    mediator = LLMMediator()
    mediator._metrics = {
        "idea_generate|openai|gpt-5.2-codex": {
            "calls": 1.0,
            "success": 1.0,
            "errors": 0.0,
            "retries": 0.0,
            "latency_ms_total": 0.0,
            "prompt_tokens_total": 1.0,
            "completion_tokens_total": 0.0,
            "estimated_cost_usd_total": 0.0,
        }
    }

    def _fake_call(task_type, route, payload):
        if route.model == "gpt-5.2-codex":
            raise AssertionError("primary route should be skipped after token budget check")
        return {
            "id": "resp-1",
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    monkeypatch.setattr(mediator, "_call_with_retries", _fake_call)
    parsed, meta = mediator.generate_json(
        task_type="idea_generate",
        system_prompt="sys",
        user_prompt="usr",
        json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        max_tokens=100,
        temperature=0,
    )
    assert parsed["ok"] is True
    assert meta["model"] == "gpt-5.1-codex-mini"


def test_generate_json_skips_primary_when_reservation_would_exceed_limit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "file")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv(
        "LLM_ITERATIVE_ROUTE_MODELS",
        "openai:gpt-5.2-codex,openai:gpt-5.1-codex-mini",
    )
    monkeypatch.setenv("LLM_ITERATIVE_MODEL_TOKEN_LIMITS", '{"openai:gpt-5.2-codex":50}')
    monkeypatch.setenv("LLM_TOKEN_BUDGET_RESERVATION_MARGIN", "0")
    monkeypatch.setenv("LLM_ROUTE_IDEA_GENERATE_API_KEY_ENV", "OPENAI_API_KEY")
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODEL", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDERS", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODELS", raising=False)
    mediator = LLMMediator()

    seen_models: list[str] = []

    def _fake_call(task_type, route, payload):
        seen_models.append(route.model)
        return {
            "id": "resp-1",
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        }

    monkeypatch.setattr(mediator, "_call_with_retries", _fake_call)
    parsed, meta = mediator.generate_json(
        task_type="idea_generate",
        system_prompt="s",
        user_prompt="u",
        json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        max_tokens=200,  # reservation > model cap, should skip primary route
        temperature=0,
    )
    assert parsed["ok"] is True
    assert meta["model"] == "gpt-5.1-codex-mini"
    assert seen_models == ["gpt-5.1-codex-mini"]
