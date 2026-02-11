from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from db.models import Idea
from llm import get_mediator
from .prompting import build_idea_context, read_godot_contract


ALLOWED_IDEA_STATUSES = {"feasible", "ready_for_gate", "picked"}


@dataclass(frozen=True)
class CompileResult:
    script_hash: str
    compiler_meta: dict[str, Any]
    validation_report: dict[str, Any]


def compile_idea_to_gdscript(
    *,
    idea: Idea,
    target_path: Path,
    max_attempts: int = 3,
    max_repairs: int = 2,
    validate: bool = True,
    validate_seconds: float = 2.0,
    max_nodes: int = 200,
) -> CompileResult:
    if idea.status not in ALLOWED_IDEA_STATUSES:
        raise RuntimeError(f"idea_not_feasible:{idea.id}:{idea.status}")

    contract = read_godot_contract()
    prompt_version = os.getenv("IDEA_GDSCRIPT_PROMPT_VERSION", "idea-to-gdscript-v1")
    repair_version = os.getenv("IDEA_GDSCRIPT_REPAIR_PROMPT_VERSION", "idea-to-gdscript-repair-v1")
    errors: list[str] = []
    repairs = 0
    last_script: str | None = None

    for attempt in range(1, max_attempts + 1):
        current_task = "gdscript_repair" if errors else "gdscript_generate"
        user_prompt = _build_compile_prompt(
            idea=idea,
            previous_errors=errors,
            previous_script=last_script,
            is_repair=bool(errors),
        )
        try:
            system_prompt = _build_system_prompt(contract=contract)
            payload, route_meta = get_mediator().generate_json(
                task_type=current_task,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema={
                    "type": "object",
                    "properties": {
                        "gdscript": {"type": "string"},
                    },
                    "required": ["gdscript"],
                    "additionalProperties": False,
                },
                max_tokens=int(os.getenv("IDEA_GDSCRIPT_MAX_TOKENS", "2400")),
                temperature=float(os.getenv("IDEA_GDSCRIPT_TEMPERATURE", "0.2")),
            )
            gdscript = str(payload["gdscript"]).strip()
            if not gdscript:
                raise RuntimeError("empty_gdscript")
            last_script = gdscript
            target_path.write_text(gdscript)
            validation_errors: list[str] = []
            if validate:
                validation_errors = _validate_gdscript(
                    script_path=target_path,
                    seconds=validate_seconds,
                    max_nodes=max_nodes,
                )
            if validation_errors:
                raise RuntimeError("validation_failed: " + "; ".join(validation_errors))
            script_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
            return CompileResult(
                script_hash=script_hash,
                compiler_meta={
                    "provider": route_meta.get("provider"),
                    "model": route_meta.get("model"),
                    "compiler_prompt_version": prompt_version,
                    "repair_prompt_version": repair_version,
                    "attempt_count": attempt,
                    "repair_count": repairs,
                },
                validation_report={
                    "syntax_ok": True,
                    "errors": [],
                },
            )
        except Exception as exc:
            errors = [str(exc)]
            if attempt <= max_repairs:
                repairs += 1
            continue

    raise RuntimeError(f"idea_gdscript_compile_failed:{'; '.join(errors)}")


def _validate_gdscript(*, script_path: Path, seconds: float, max_nodes: int) -> list[str]:
    script = Path(script_path)
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "godot-run.py"),
        "--mode",
        "validate",
        "--script",
        str(script),
        "--seconds",
        str(seconds),
        "--max-nodes",
        str(max_nodes),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return []
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    msg = stderr or stdout or "unknown_godot_error"
    return [msg[:8000]]


def _build_compile_prompt(
    *,
    idea: Idea,
    previous_errors: list[str],
    previous_script: str | None,
    is_repair: bool,
) -> str:
    mode = "repair" if is_repair else "compile"
    previous_block = ""
    if previous_script:
        previous_block = (
            "PREVIOUS SCRIPT (BEGIN):\n"
            "<<<PREVIOUS_SCRIPT_BEGIN>>>\n"
            f"{previous_script}\n"
            "<<<PREVIOUS_SCRIPT_END>>>\n\n"
        )
    return (
        f"MODE: {mode}\n\n"
        "IDEA (BEGIN):\n"
        "<<<IDEA_BEGIN>>>\n"
        f"{build_idea_context(title=idea.title, summary=idea.summary, what_to_expect=idea.what_to_expect, preview=idea.preview)}"
        "<<<IDEA_END>>>\n\n"
        f"{previous_block}"
        f"Previous validation errors: {previous_errors}\n\n"
        "If MODE=repair, fix the previous GDScript with minimal changes and return the full corrected script.\n"
        "Return JSON only. Do not wrap code in markdown or backticks."
    )


def _build_system_prompt(*, contract: str) -> str:
    return (
        "You write one Godot 4.6 GDScript file for a 2D animation. "
        "Return JSON only.\n\n"
        "GOAL:\n"
        "Create short 2D animations with physics (gravity, collisions) and simple geometry.\n"
        "Keep code minimal and deterministic when possible, but correctness > determinism.\n\n"
        "CONTRACT (BEGIN):\n"
        "<<<CONTRACT_BEGIN>>>\n"
        f"{contract}\n"
        "<<<CONTRACT_END>>>\n"
    )
