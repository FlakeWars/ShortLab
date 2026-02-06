from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Any

from db.models import Idea
from dsl.validate import validate_file
from llm import get_mediator
from .prompting import build_idea_context, read_dsl_spec


ALLOWED_IDEA_STATUSES = {"feasible", "ready_for_gate", "picked"}


@dataclass(frozen=True)
class CompileResult:
    dsl_hash: str
    compiler_meta: dict[str, Any]
    validation_report: dict[str, Any]


def compile_idea_to_dsl(
    *,
    idea: Idea,
    template_path: Path,
    target_path: Path,
    animation_code: str,
    max_attempts: int = 3,
    max_repairs: int = 2,
) -> CompileResult:
    if idea.status not in ALLOWED_IDEA_STATUSES:
        raise RuntimeError(f"idea_not_feasible:{idea.id}:{idea.status}")
    if not template_path.exists():
        raise FileNotFoundError(f"DSL template not found: {template_path}")

    template_yaml = template_path.read_text()
    dsl_spec = read_dsl_spec()
    prompt_version = os.getenv("IDEA_DSL_COMPILER_PROMPT_VERSION", "idea-to-dsl-v4")
    repair_version = os.getenv("IDEA_DSL_REPAIR_PROMPT_VERSION", "idea-to-dsl-repair-v4")
    errors: list[str] = []
    repairs = 0

    for attempt in range(1, max_attempts + 1):
        current_task = "dsl_repair" if errors else "idea_compile_dsl"
        user_prompt = _build_compile_prompt(
            idea=idea,
            template_yaml=template_yaml,
            dsl_spec=dsl_spec,
            previous_errors=errors,
            is_repair=bool(errors),
        )
        try:
            payload, route_meta = get_mediator().generate_json(
                task_type=current_task,
                system_prompt=(
                    "You compile one feasible short animation idea into YAML DSL. "
                    "Return JSON only."
                ),
                user_prompt=user_prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "dsl_yaml": {"type": "string"},
                    },
                    "required": ["dsl_yaml"],
                    "additionalProperties": False,
                },
                max_tokens=int(os.getenv("IDEA_DSL_COMPILER_MAX_TOKENS", "2400")),
                temperature=float(os.getenv("IDEA_DSL_COMPILER_TEMPERATURE", "0.2")),
            )
            dsl_yaml = str(payload["dsl_yaml"]).strip()
            if not dsl_yaml:
                raise RuntimeError("empty_dsl_yaml")
            target_path.write_text(dsl_yaml)
            model = validate_file(target_path)
            semantic_errors = _semantic_validate(model)
            if semantic_errors:
                raise RuntimeError("semantic_validation_failed: " + "; ".join(semantic_errors))
            dsl_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
            return CompileResult(
                dsl_hash=dsl_hash,
                compiler_meta={
                    "provider": route_meta.get("provider"),
                    "model": route_meta.get("model"),
                    "compiler_prompt_version": prompt_version,
                    "repair_prompt_version": repair_version,
                    "attempt_count": attempt,
                    "repair_count": repairs,
                    "fallback_used": False,
                },
                validation_report={
                    "syntax_ok": True,
                    "semantic_ok": True,
                    "errors": [],
                },
            )
        except Exception as exc:
            errors = [str(exc)]
            if attempt <= max_repairs:
                repairs += 1
            continue

    if os.getenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "1") == "1":
        target_path.write_text(template_yaml)
        model = validate_file(target_path)
        semantic_errors = _semantic_validate(model)
        if semantic_errors:
            raise RuntimeError("fallback_semantic_validation_failed: " + "; ".join(semantic_errors))
        dsl_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
        return CompileResult(
            dsl_hash=dsl_hash,
            compiler_meta={
                "provider": "fallback",
                "model": "template",
                "compiler_prompt_version": prompt_version,
                "repair_prompt_version": repair_version,
                "attempt_count": max_attempts,
                "repair_count": repairs,
                "fallback_used": True,
                "errors": errors,
            },
            validation_report={
                "syntax_ok": True,
                "semantic_ok": True,
                "errors": [],
            },
        )
    raise RuntimeError(f"idea_compile_failed:{'; '.join(errors)}")


def can_use_llm_compiler() -> bool:
    return os.getenv("IDEA_DSL_COMPILER_ENABLED", "0") == "1"


def _build_compile_prompt(
    *,
    idea: Idea,
    template_yaml: str,
    dsl_spec: str,
    previous_errors: list[str],
    is_repair: bool,
) -> str:
    mode = "repair" if is_repair else "compile"
    return (
        f"MODE: {mode}\n\n"
        "IDEA (BEGIN):\n"
        "<<<IDEA_BEGIN>>>\n"
        f"{build_idea_context(title=idea.title, summary=idea.summary, what_to_expect=idea.what_to_expect, preview=idea.preview)}"
        "<<<IDEA_END>>>\n\n"
        f"Previous validation errors: {previous_errors}\n\n"
        "GOAL:\n"
        "We want short, deterministic 2D animations based on simple geometric primitives.\n"
        "Target a visually engaging, rhythmic, somewhat hypnotic result.\n"
        "Avoid trivial motion and aim for interesting interactions or evolving structures.\n\n"
        "DSL SPEC (BEGIN):\n"
        "<<<DSL_SPEC_BEGIN>>>\n"
        f"{dsl_spec[:8000]}\n"
        "<<<DSL_SPEC_END>>>\n\n"
        "CREATIVE FRAME:\n"
        "- Use simple geometric primitives.\n"
        "- Motion is deterministic (physics-like forces, parametric paths, or rule-based behaviors).\n"
        "- No external assets, characters, dialog, camera cuts, or photorealism.\n\n"
        "SCHEMA TRAPS (IMPORTANT):\n"
        "- entities.size object MUST include min and max; do not use size.value.\n"
        "- spawns do NOT accept params at top-level; params are only under distribution.\n"
        "- distribution.params must be omitted when not required (e.g., center).\n"
        "- grid requires cols+rows; orbit requires radius (speed optional).\n\n"
        "- scene.background MUST be one of scene.palette colors.\n\n"
        "ALGORITHM:\n"
        "1) Identify visual elements, motion rules, forces, timing, interactions.\n"
        "2) Map them to DSL concepts.\n"
        "3) Choose concrete parameter values (no placeholders).\n"
        "4) Assemble a complete DSL YAML document.\n\n"
        "REQUIREMENTS:\n"
        "- Build DSL YAML FROM SCRATCH (do NOT copy any template).\n"
        "- Include all required sections for a valid DSL document.\n"
        "- Ensure entities/spawns/rules are coherent.\n"
        "- Keep output concise but faithful to the idea.\n\n"
        "LANGUAGE:\n"
        "Use the same language as the idea text for any human-readable fields.\n\n"
        "RESPONSE FORMAT EXAMPLE (BEGIN):\n"
        "<<<RESPONSE_EXAMPLE>>>\n"
        "{\n"
        '  "dsl_yaml": "dsl_version: \'1.0\'\\nmeta:\\n  id: \'idea-001\'\\n  title: \'...\'\\n"\n'
        "}\n"
        "<<<RESPONSE_FORMAT_END>>>\n\n"
        "Return JSON only. Do not wrap YAML in markdown or backticks."
    )


def _semantic_validate(model) -> list[str]:
    errors: list[str] = []

    entities = list(model.systems.entities)
    spawns = list(model.systems.spawns)
    rules = list(model.systems.rules)
    emitters = list(model.systems.emitters or [])

    if not entities:
        errors.append("systems.entities must not be empty")
    if not spawns and not emitters:
        errors.append("systems.spawns or systems.emitters must define at least one source")
    if not rules:
        errors.append("systems.rules must not be empty")

    entity_ids = [e.id for e in entities]
    if len(entity_ids) != len(set(entity_ids)):
        errors.append("systems.entities contains duplicate ids")

    if len(model.scene.palette) < 3:
        errors.append("scene.palette must contain at least 3 colors")

    duration = float(model.scene.canvas.duration_s)
    if duration < 6.0 or duration > 60.0:
        errors.append("scene.canvas.duration_s must be in range 6..60")

    if model.termination.time is not None:
        t = float(model.termination.time)
        if t <= 0:
            errors.append("termination.time must be > 0")
        if t > duration:
            errors.append("termination.time cannot exceed scene.canvas.duration_s")

    return errors
