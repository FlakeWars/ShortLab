from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Any

import yaml

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
    prompt_version = os.getenv("IDEA_DSL_COMPILER_PROMPT_VERSION", "idea-to-dsl-v5")
    repair_version = os.getenv("IDEA_DSL_REPAIR_PROMPT_VERSION", "idea-to-dsl-repair-v5")
    errors: list[str] = []
    repairs = 0
    last_dsl_yaml: str | None = None

    for attempt in range(1, max_attempts + 1):
        current_task = "dsl_repair" if errors else "idea_compile_dsl"
        user_prompt = _build_compile_prompt(
            idea=idea,
            previous_errors=errors,
            previous_dsl=last_dsl_yaml,
            is_repair=bool(errors),
        )
        try:
            system_prompt = _build_compiler_system_prompt(dsl_spec=dsl_spec)
            payload, route_meta = get_mediator().generate_json(
                task_type=current_task,
                system_prompt=system_prompt,
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
            last_dsl_yaml = dsl_yaml
            target_path.write_text(dsl_yaml)
            _ensure_background_in_palette(target_path)
            _ensure_duration_range(target_path)
            _ensure_unique_rule_ids(target_path)
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
        _ensure_background_in_palette(target_path)
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
    previous_errors: list[str],
    previous_dsl: str | None,
    is_repair: bool,
) -> str:
    mode = "repair" if is_repair else "compile"
    previous_block = ""
    if previous_dsl:
        previous_block = (
            "PREVIOUS DSL (BEGIN):\n"
            "<<<PREVIOUS_DSL_BEGIN>>>\n"
            f"{previous_dsl}\n"
            "<<<PREVIOUS_DSL_END>>>\n\n"
        )
    return (
        f"MODE: {mode}\n\n"
        "IDEA (BEGIN):\n"
        "<<<IDEA_BEGIN>>>\n"
        f"{build_idea_context(title=idea.title, summary=idea.summary, what_to_expect=idea.what_to_expect, preview=idea.preview)}"
        "<<<IDEA_END>>>\n\n"
        f"{previous_block}"
        f"Previous validation errors: {previous_errors}\n\n"
        "If MODE=repair, fix the previous DSL with minimal changes and return the full corrected DSL.\n"
        "Return JSON only. Do not wrap YAML in markdown or backticks."
    )


def _build_compiler_system_prompt(*, dsl_spec: str) -> str:
    return (
        "You compile one feasible short animation idea into YAML DSL. "
        "Return JSON only.\n\n"
        "GOAL:\n"
        "We want short, deterministic 2D animations based on simple geometric primitives.\n"
        "Target a visually engaging, rhythmic, somewhat hypnotic result.\n"
        "Avoid trivial motion and aim for interesting interactions or evolving structures.\n\n"
        "DSL SPEC (BEGIN):\n"
        "<<<DSL_SPEC_BEGIN>>>\n"
        f"{dsl_spec}\n"
        "<<<DSL_SPEC_END>>>\n\n"
        "EXAMPLES (BEGIN):\n"
        "<<<EXAMPLE_SIMPLE_BEGIN>>>\n"
        "Idea:\n"
        "- title: Orbitujące iskry\n"
        "- summary: Kilkanaście punktów krąży wokół centrum, tworząc hipnotyczny pierścień.\n"
        "- what_to_expect: Stałe tempo, łagodna pulsacja kolorów, brak kolizji.\n"
        "- preview: Pierścień punktów obraca się, a kolory przechodzą między ciepłymi barwami.\n"
        "DSL:\n"
        "dsl_version: \"1.4\"\n"
        "meta:\n"
        "  id: \"idea-001\"\n"
        "  title: \"Orbitujące iskry\"\n"
        "  seed: 1234\n"
        "  tags: [\"orbit\", \"circle\"]\n"
        "scene:\n"
        "  canvas:\n"
        "    width: 1080\n"
        "    height: 1920\n"
        "    fps: 30\n"
        "    duration_s: 20\n"
        "  palette: [\"#0b0d17\", \"#f7d046\", \"#ff6b6b\"]\n"
        "  background: \"#0b0d17\"\n"
        "systems:\n"
        "  entities:\n"
        "    - id: spark\n"
        "      shape: circle\n"
        "      size: { min: 10, max: 18, distribution: uniform }\n"
        "      color: \"#f7d046\"\n"
        "      render: { opacity: 0.9 }\n"
        "  spawns:\n"
        "    - entity_id: spark\n"
        "      count: 24\n"
        "      distribution:\n"
        "        type: orbit\n"
        "        params: { radius: 260, speed: 18 }\n"
        "  rules:\n"
        "    - id: orbit_core\n"
        "      type: orbit\n"
        "      applies_to: spark\n"
        "      params: { center: { x: 540, y: 960 }, speed: 18, radius: 260 }\n"
        "termination:\n"
        "  time: { at_s: 20 }\n"
        "output:\n"
        "  format: mp4\n"
        "  resolution: \"1080x1920\"\n"
        "  codec: h264\n"
        "  bitrate: \"8M\"\n"
        "<<<EXAMPLE_SIMPLE_END>>>\n\n"
        "<<<EXAMPLE_COMPLEX_BEGIN>>>\n"
        "Idea:\n"
        "- title: Fale w siatce\n"
        "- summary: Siatka punktów pulsuje i falowo rozchodzi się od środka.\n"
        "- what_to_expect: Rytmiczne fale, lekkie przyciąganie do centrum.\n"
        "- preview: Kolor punktów zmienia się wraz z ruchem, tworząc efekt pulsacji.\n"
        "DSL:\n"
        "dsl_version: \"1.4\"\n"
        "meta:\n"
        "  id: \"idea-002\"\n"
        "  title: \"Fale w siatce\"\n"
        "  seed: 2307\n"
        "  tags: [\"grid\", \"wave\"]\n"
        "scene:\n"
        "  canvas:\n"
        "    width: 1080\n"
        "    height: 1920\n"
        "    fps: 30\n"
        "    duration_s: 28\n"
        "  palette: [\"#0f172a\", \"#38bdf8\", \"#f97316\", \"#e2e8f0\"]\n"
        "  background: \"#0f172a\"\n"
        "systems:\n"
        "  entities:\n"
        "    - id: node\n"
        "      shape: circle\n"
        "      size: { min: 8, max: 14, distribution: uniform }\n"
        "      color: \"#38bdf8\"\n"
        "      render: { opacity: 0.85 }\n"
        "  spawns:\n"
        "    - entity_id: node\n"
        "      count: 96\n"
        "      distribution:\n"
        "        type: grid\n"
        "        params: { cols: 12, rows: 8 }\n"
        "  rules:\n"
        "    - id: slow_orbit\n"
        "      type: orbit\n"
        "      applies_to: node\n"
        "      params: { center: { x: 540, y: 960 }, speed: 6, radius: 320 }\n"
        "    - id: center_pull\n"
        "      type: attract\n"
        "      applies_to: node\n"
        "      params: { target: { x: 540, y: 960 }, strength: 0.4, radius: 520 }\n"
        "termination:\n"
        "  time: { at_s: 28 }\n"
        "output:\n"
        "  format: mp4\n"
        "  resolution: \"1080x1920\"\n"
        "  codec: h264\n"
        "  bitrate: \"8M\"\n"
        "<<<EXAMPLE_COMPLEX_END>>>\n\n"
        "EXAMPLES (END)\n\n"
        "CREATIVE FRAME:\n"
        "- Use simple geometric primitives.\n"
        "- Motion is deterministic (physics-like forces, parametric paths, or rule-based behaviors).\n"
        "- No external assets, characters, dialog, camera cuts, or photorealism.\n\n"
        "SCHEMA TRAPS (IMPORTANT):\n"
        "- entities.size object MUST include min and max; do not use size.value.\n"
        "- spawns do NOT accept params at top-level; params are only under distribution.\n"
        "- distribution.params must be omitted when not required (e.g., center).\n"
        "- grid requires cols+rows; orbit requires radius (speed optional).\n"
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
        '  "dsl_yaml": "dsl_version: \'1.4\'\\nmeta:\\n  id: \'idea-001\'\\n  title: \'...\'\\n"\n'
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
        try:
            t = float(model.termination.time.at_s)
        except (TypeError, ValueError) as exc:
            errors.append(f"termination.time.at_s must be numeric ({exc})")
        else:
            if t <= 0:
                errors.append("termination.time.at_s must be > 0")
            if t > duration:
                errors.append("termination.time.at_s cannot exceed scene.canvas.duration_s")

    return errors


def _ensure_background_in_palette(target_path: Path) -> None:
    try:
        payload = yaml.safe_load(target_path.read_text())
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(payload, dict):
        return
    scene = payload.get("scene")
    if not isinstance(scene, dict):
        return
    palette = scene.get("palette")
    background = scene.get("background")
    if not isinstance(background, str) or not background.strip():
        return
    if palette is None:
        scene["palette"] = [background]
        target_path.write_text(yaml.safe_dump(payload, sort_keys=False))
        return
    if isinstance(palette, list):
        if background not in palette:
            palette.append(background)
            scene["palette"] = palette
            target_path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _ensure_duration_range(target_path: Path, *, min_s: float = 6.0, max_s: float = 60.0) -> None:
    try:
        payload = yaml.safe_load(target_path.read_text())
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(payload, dict):
        return
    scene = payload.get("scene")
    if not isinstance(scene, dict):
        return
    canvas = scene.get("canvas")
    if not isinstance(canvas, dict):
        return
    duration = canvas.get("duration_s")
    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return
    if duration_value < min_s:
        canvas["duration_s"] = min_s
    elif duration_value > max_s:
        canvas["duration_s"] = max_s
    else:
        return
    scene["canvas"] = canvas
    payload["scene"] = scene
    target_path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _ensure_unique_rule_ids(target_path: Path) -> None:
    try:
        payload = yaml.safe_load(target_path.read_text())
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(payload, dict):
        return
    systems = payload.get("systems")
    if not isinstance(systems, dict):
        return
    rules = systems.get("rules")
    if not isinstance(rules, list):
        return
    seen: set[str] = set()
    changed = False
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        base = str(rule.get("id") or f"rule_{idx+1}").strip() or f"rule_{idx+1}"
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}_{suffix}"
            suffix += 1
        if candidate != rule.get("id"):
            rule["id"] = candidate
            changed = True
        seen.add(candidate)
    if changed:
        systems["rules"] = rules
        payload["systems"] = systems
        target_path.write_text(yaml.safe_dump(payload, sort_keys=False))
