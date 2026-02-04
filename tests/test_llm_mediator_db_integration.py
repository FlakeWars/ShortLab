from __future__ import annotations

from datetime import date
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import delete, text

import llm.mediator as mediator_module
from db.models import LLMMediatorBudgetDaily, LLMMediatorRouteMetric
from db.session import SessionLocal


def _require_db() -> None:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
            session.query(LLMMediatorBudgetDaily).limit(1).all()
            session.query(LLMMediatorRouteMetric).limit(1).all()
    except Exception as exc:  # pragma: no cover - depends on local env
        pytest.skip(f"DB not ready for integration test: {exc}")


def test_llm_mediator_db_persist_and_reload(monkeypatch, tmp_path) -> None:
    _require_db()
    day = date.today()
    model = "integration-test-model"
    key = f"idea_generate|openai|{model}"
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "db")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(tmp_path / "ignored.json"))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "9")

    with SessionLocal() as session:
        session.execute(
            delete(LLMMediatorRouteMetric).where(
                LLMMediatorRouteMetric.day == day,
                LLMMediatorRouteMetric.model == model,
            )
        )
        session.execute(delete(LLMMediatorBudgetDaily).where(LLMMediatorBudgetDaily.day == day))
        session.commit()

    mediator = mediator_module.LLMMediator()
    mediator._budget_day = day.isoformat()
    mediator._spent_usd_total = 1.23
    mediator._metrics = {
        key: {
            "calls": 4.0,
            "success": 3.0,
            "errors": 1.0,
            "retries": 1.0,
            "latency_ms_total": 44.0,
            "prompt_tokens_total": 400.0,
            "completion_tokens_total": 150.0,
            "estimated_cost_usd_total": 0.42,
        }
    }
    assert mediator._persist_state_db() is True

    reloaded = mediator_module.LLMMediator()
    assert reloaded._load_state_db() is True
    snap = reloaded.get_metrics_snapshot()
    assert snap["state_backend"] == "db"
    assert snap["budget"]["budget_day"] == day.isoformat()
    assert snap["budget"]["spent_usd_total"] >= 0.0
    assert snap["routes"][key]["calls"] == pytest.approx(4.0, abs=1e-6)

    with SessionLocal() as session:
        session.execute(
            delete(LLMMediatorRouteMetric).where(
                LLMMediatorRouteMetric.day == day,
                LLMMediatorRouteMetric.model == model,
            )
        )
        session.execute(delete(LLMMediatorBudgetDaily).where(LLMMediatorBudgetDaily.day == day))
        session.commit()


def test_llm_mediator_db_fallback_to_file_on_session_failure(monkeypatch, tmp_path) -> None:
    today = date.today().isoformat()
    state_path = tmp_path / "fallback-state.json"
    state_path.write_text(
        json.dumps(
            {
                "routes": {
                    "idea_generate|openai|fallback-model": {
                        "calls": 1.0,
                        "success": 1.0,
                        "errors": 0.0,
                        "retries": 0.0,
                        "latency_ms_total": 1.0,
                        "prompt_tokens_total": 1.0,
                        "completion_tokens_total": 1.0,
                        "estimated_cost_usd_total": 0.01,
                    }
                },
                "budget": {"budget_day": today, "spent_usd_total": 0.99, "daily_budget_usd": 5.0},
            }
        )
    )
    monkeypatch.setenv("LLM_MEDIATOR_PERSIST_BACKEND", "db")
    monkeypatch.setenv("LLM_MEDIATOR_STATE_FILE", str(state_path))
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "5")
    monkeypatch.setattr(mediator_module, "SessionLocal", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    mediator = mediator_module.LLMMediator()
    snap = mediator.get_metrics_snapshot()
    assert snap["state_backend"] == "db"
    assert snap["budget"]["spent_usd_total"] == pytest.approx(0.99, abs=1e-6)
    assert "idea_generate|openai|fallback-model" in snap["routes"]


def test_llm_mediator_retention_smoke(monkeypatch) -> None:
    _require_db()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/llm-mediator-retention.py",
            "--metrics-days",
            "30",
            "--budget-days",
            "120",
        ],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "metrics_cutoff=" in result.stdout
    assert "budget_cutoff=" in result.stdout
