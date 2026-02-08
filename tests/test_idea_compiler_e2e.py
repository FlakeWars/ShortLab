from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

import ideas.compiler as compiler_module
from db.models import Idea


class _TemplateMediator:
    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path

    def generate_json(self, *, user_prompt: str, **_kwargs):  # type: ignore[no-untyped-def]
        title = _extract_line(user_prompt, "Idea title:")
        summary = _extract_line(user_prompt, "Idea summary:")
        data = yaml.safe_load(self.template_path.read_text())
        idea_hash = int(hashlib.sha256(f"{title}|{summary}".encode("utf-8")).hexdigest()[:8], 16)
        palette = [
            ["#0B0D0E", "#F2F4F5", "#4CC3FF", "#FFB84C"],
            ["#0F172A", "#F8FAFC", "#38BDF8", "#F43F5E"],
            ["#0B0F1A", "#F1F5F9", "#22C55E", "#F97316"],
            ["#111827", "#E5E7EB", "#A855F7", "#22D3EE"],
            ["#0B0D0E", "#F8FAFC", "#F59E0B", "#10B981"],
        ][idea_hash % 5]
        data["meta"]["title"] = title or "generated"
        data["meta"]["seed"] = idea_hash % (2**31)
        data["scene"]["palette"] = palette
        data["scene"]["background"] = palette[0]
        for entity in data["systems"]["entities"]:
            if entity.get("id") == "core":
                entity["color"] = palette[2]
            if entity.get("id") == "particle":
                entity["color"] = palette[1]
        for rule in data["systems"].get("rules", []):
            if rule.get("type") == "color_animation":
                rule_params = rule.setdefault("params", {})
                rule_params["colors"] = palette[1:4]
        for spawn in data["systems"]["spawns"]:
            spawn["count"] = max(1, int(spawn["count"]) + (idea_hash % 3))
        return {"dsl_yaml": yaml.safe_dump(data, sort_keys=False)}, {"provider": "test", "model": "template"}


def _extract_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "", 1).strip()
    return ""


def _idea(title: str) -> Idea:
    return Idea(
        id=uuid4(),
        title=title,
        summary=f"summary: {title}",
        what_to_expect=f"expect: {title}",
        preview=f"preview: {title}",
        status="feasible",
    )


def test_compiler_e2e_five_ideas_generate_different_dsls(monkeypatch, tmp_path: Path) -> None:
    template = Path(".ai/examples/dsl-v1-happy.yaml")
    mediator = _TemplateMediator(template)
    monkeypatch.setattr(compiler_module, "get_mediator", lambda: mediator)
    monkeypatch.setenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "0")

    hashes: list[str] = []
    for idx in range(5):
        idea = _idea(f"Idea {idx}")
        out_path = tmp_path / f"dsl-{idx}.yaml"
        result = compiler_module.compile_idea_to_dsl(
            idea=idea,
            template_path=template,
            target_path=out_path,
            animation_code=f"anim-{idx}",
            max_attempts=1,
            max_repairs=0,
        )
        assert result.validation_report["syntax_ok"] is True
        assert result.validation_report["semantic_ok"] is True
        hashes.append(result.dsl_hash)

    assert len(set(hashes)) == 5


def test_compiler_semantic_gate_blocks_invalid_yaml(monkeypatch, tmp_path: Path) -> None:
    template = Path(".ai/examples/dsl-v1-happy.yaml")

    class _BadMediator:
        def generate_json(self, **_kwargs):  # type: ignore[no-untyped-def]
            data = yaml.safe_load(template.read_text())
            data["systems"]["rules"] = []
            return {"dsl_yaml": yaml.safe_dump(data, sort_keys=False)}, {"provider": "test", "model": "bad"}

    monkeypatch.setattr(compiler_module, "get_mediator", lambda: _BadMediator())
    monkeypatch.setenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "0")

    with pytest.raises(RuntimeError, match="idea_compile_failed"):
        compiler_module.compile_idea_to_dsl(
            idea=_idea("Broken"),
            template_path=template,
            target_path=tmp_path / "broken.yaml",
            animation_code="anim-bad",
            max_attempts=1,
            max_repairs=0,
        )
