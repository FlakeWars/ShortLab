from __future__ import annotations

from llm.mediator import _load_route


def test_route_uses_profile_defaults_when_task_route_missing(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODEL", raising=False)
    monkeypatch.setenv("LLM_TASK_PROFILE_IDEA_GENERATE", "creative")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_MODEL", "openrouter/model-a")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_API_KEY_ENV", "OPENAI_API_KEY")

    route = _load_route("idea_generate")
    assert route.provider == "openrouter"
    assert route.model == "openrouter/model-a"


def test_task_specific_route_overrides_profile(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.setenv("LLM_TASK_PROFILE_IDEA_GENERATE", "creative")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_MODEL", "openrouter/model-a")
    monkeypatch.setenv("LLM_PROFILE_CREATIVE_API_KEY_ENV", "OPENAI_API_KEY")
    monkeypatch.setenv("LLM_ROUTE_IDEA_GENERATE_PROVIDER", "groq")
    monkeypatch.setenv("LLM_ROUTE_IDEA_GENERATE_MODEL", "groq/model-b")

    route = _load_route("idea_generate")
    assert route.provider == "groq"
    assert route.model == "groq/model-b"
