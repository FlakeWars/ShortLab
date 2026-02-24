from __future__ import annotations

from llm.mediator import _load_route, _load_routes


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


def test_iterative_route_override_applies_to_idea_and_gdscript_tasks(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODEL", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_PROVIDERS", raising=False)
    monkeypatch.delenv("LLM_ROUTE_IDEA_GENERATE_MODELS", raising=False)
    monkeypatch.setenv(
        "LLM_ITERATIVE_ROUTE_MODELS",
        "openai:gpt-5.2-codex,openai:gpt-5.1-codex-mini",
    )

    idea_routes = _load_routes("idea_generate")
    gdscript_routes = _load_routes("gdscript_generate")

    assert [r.model for r in idea_routes] == ["gpt-5.2-codex", "gpt-5.1-codex-mini"]
    assert [r.model for r in gdscript_routes] == ["gpt-5.2-codex", "gpt-5.1-codex-mini"]


def test_iterative_route_override_does_not_change_other_tasks(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x-test-key")
    monkeypatch.setenv(
        "LLM_ITERATIVE_ROUTE_MODELS",
        "openai:gpt-5.2-codex,openai:gpt-5.1-codex-mini",
    )
    monkeypatch.setenv("LLM_ROUTE_IDEA_VERIFY_CAPABILITY_PROVIDER", "openai")
    monkeypatch.setenv("LLM_ROUTE_IDEA_VERIFY_CAPABILITY_MODEL", "gpt-5.1-codex-mini")

    route = _load_route("idea_verify_capability")
    assert route.model == "gpt-5.1-codex-mini"
