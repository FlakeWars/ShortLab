from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Any

from db.models import Idea
from llm import LLMError, get_mediator
from .prompting import build_idea_context, read_godot_contract, read_godot_guidelines


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
    guidelines = read_godot_guidelines()
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
            system_prompt = _build_system_prompt(contract=contract, guidelines=guidelines)
            route_meta: dict[str, Any] = {"provider": None, "model": None}
            try:
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
                    max_tokens=int(os.getenv("IDEA_GDSCRIPT_MAX_TOKENS", "5000")),
                    temperature=float(os.getenv("IDEA_GDSCRIPT_TEMPERATURE", "0.2")),
                )
                gdscript = _extract_gdscript_field(payload)
            except LLMError as exc:
                gdscript = _extract_gdscript_from_raw_llm_content(getattr(exc, "raw_content", "") or "")
                if not gdscript:
                    raise
                route_meta = {
                    "provider": getattr(exc, "provider", None),
                    "model": None,
                    "raw_content_fallback": True,
                }
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
                if not validation_errors:
                    validation_errors = _validate_gdscript_quality(
                        script_path=target_path,
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


def _validate_gdscript_quality(*, script_path: Path, max_nodes: int) -> list[str]:
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin or not ffprobe_bin:
        return []

    preview_seconds = max(2.0, float(os.getenv("IDEA_GDSCRIPT_PREVIEW_QC_SECONDS", "8")))
    preview_fps = max(6, int(os.getenv("IDEA_GDSCRIPT_PREVIEW_QC_FPS", "12")))
    min_bitrate = max(0, int(os.getenv("IDEA_GDSCRIPT_PREVIEW_QC_MIN_BITRATE_BPS", "16000")))

    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="gdscript-preview-qc-") as tmpdir:
        preview_out = Path(tmpdir) / "preview.mp4"
        cmd = [
            sys.executable,
            str(repo_root / "scripts" / "godot-run.py"),
            "--mode",
            "preview",
            "--script",
            str(script_path),
            "--seconds",
            str(preview_seconds),
            "--fps",
            str(preview_fps),
            "--max-nodes",
            str(max_nodes),
            "--scale",
            "0.5",
            "--out",
            str(preview_out),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            msg = stderr or stdout or "preview_qc_failed"
            return [f"preview_qc_failed:{msg[:500]}"]
        if not preview_out.exists():
            return ["preview_qc_missing_output"]

        duration_s = _probe_duration_seconds(preview_out, ffprobe_bin)
        if duration_s <= 0.0:
            return ["preview_qc_invalid_duration"]
        start_hash = _extract_frame_hash(preview_out, 0.0, ffmpeg_bin)
        mid_hash = _extract_frame_hash(preview_out, duration_s / 2.0, ffmpeg_bin)
        end_hash = _extract_frame_hash(preview_out, max(0.0, duration_s - 0.25), ffmpeg_bin)
        if not start_hash or not mid_hash or not end_hash:
            return ["preview_qc_frame_hash_failed"]
        if start_hash == mid_hash == end_hash:
            return ["preview_qc_static_all_frames"]
        if mid_hash == end_hash:
            return ["preview_qc_frozen_tail"]

        bitrate = _probe_video_bitrate(preview_out, ffprobe_bin)
        if bitrate is not None and bitrate < min_bitrate:
            return [f"preview_qc_low_bitrate:{bitrate}<{min_bitrate}"]
    return []


def _probe_duration_seconds(video_path: Path, ffprobe_bin: str) -> float:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return 0.0
    raw = (result.stdout or "").strip().splitlines()
    if not raw:
        return 0.0
    try:
        return float(raw[0].strip())
    except Exception:
        return 0.0


def _probe_video_bitrate(video_path: Path, ffprobe_bin: str) -> int | None:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=bit_rate",
        "-of",
        "default=nw=1:nk=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip().splitlines()
    if not value or not value[0].strip():
        return None
    try:
        return int(float(value[0].strip()))
    except Exception:
        return None


def _extract_frame_hash(video_path: Path, timestamp_s: float, ffmpeg_bin: str) -> str:
    with tempfile.NamedTemporaryFile(prefix="gdscript-frame-", suffix=".png", delete=False) as handle:
        frame_path = Path(handle.name)
    try:
        cmd = [
            ffmpeg_bin,
            "-v",
            "error",
            "-ss",
            f"{max(0.0, timestamp_s):.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-y",
            str(frame_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not frame_path.exists():
            return ""
        return hashlib.sha256(frame_path.read_bytes()).hexdigest()
    finally:
        try:
            frame_path.unlink(missing_ok=True)
        except Exception:
            pass


def _extract_gdscript_field(payload: dict[str, Any]) -> str:
    for key in ("gdscript", "script", "code"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    keys = ", ".join(sorted(str(k) for k in payload.keys())) if isinstance(payload, dict) else "non-dict"
    raise RuntimeError(f"missing_gdscript_field:{keys}")


def _extract_gdscript_from_raw_llm_content(content: str) -> str:
    raw = (content or "").strip()
    if not raw:
        return ""
    fenced = _extract_fenced_code(raw)
    if fenced:
        return fenced
    for key in ('"gdscript"', '"script"', '"code"'):
        idx = raw.find(key)
        if idx == -1:
            continue
        colon_idx = raw.find(":", idx + len(key))
        if colon_idx == -1:
            continue
        fragment = raw[colon_idx + 1 :].lstrip()
        if fragment.startswith('"'):
            decoded = _decode_json_string_fragment(fragment[1:])
            if decoded:
                return decoded
    if "extends " in raw:
        return raw
    return ""


def _extract_fenced_code(content: str) -> str:
    begin = content.find("```")
    if begin == -1:
        return ""
    end = content.find("```", begin + 3)
    if end == -1:
        return ""
    body = content[begin + 3 : end]
    lines = body.splitlines()
    if lines and lines[0].strip().lower() in {"gdscript", "script", "code"}:
        lines = lines[1:]
    return "\n".join(lines).strip()


def _decode_json_string_fragment(fragment: str) -> str:
    text = fragment
    for suffix in ('"}', '",', '" ]', '" }'):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    text = text.strip()
    if not text:
        return ""
    text = text.replace("\\r\\n", "\n")
    text = text.replace("\\n", "\n")
    text = text.replace("\\t", "\t")
    text = text.replace('\\"', '"')
    text = text.replace("\\\\", "\\")
    return text.strip()


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


def _build_system_prompt(*, contract: str, guidelines: str) -> str:
    return (
        "You write one Godot 4.6 GDScript file for a 2D animation. "
        "Return JSON only.\n\n"
        "GOAL:\n"
        "Create short 2D animations with physics (gravity, collisions) and simple geometry.\n"
        "Keep code minimal and deterministic when possible, but correctness > determinism.\n"
        "Animation must stay visibly dynamic across the whole run and should never freeze before the end.\n"
        "Do not stop physics/process based on elapsed time (no early set_physics_process(false)).\n"
        "Use high visual contrast and clear moving elements so the frame is not perceived as empty.\n\n"
        "SHORT FORMAT REQUIREMENTS:\n"
        "- Target frame is vertical 9:16 (1080x1920).\n"
        "- Keep primary action in safe center area (about 70% width, 80% height).\n"
        "- Avoid putting crucial events near left/right edges where crop/UI overlays can hide them.\n\n"
        "CONTRACT (BEGIN):\n"
        "<<<CONTRACT_BEGIN>>>\n"
        f"{contract}\n"
        "<<<CONTRACT_END>>>\n"
        "\nGUIDELINES (BEGIN):\n"
        "<<<GUIDELINES_BEGIN>>>\n"
        f"{guidelines}\n"
        "<<<GUIDELINES_END>>>\n"
    )
