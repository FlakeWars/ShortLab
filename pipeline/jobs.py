from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import yaml

from rq.job import Job as RQJob

from db.models import (
    Animation,
    Artifact,
    DesignSystemVersion,
    DslVersion,
    Idea,
    Job,
    Render,
)
from sqlalchemy import select
from db.session import SessionLocal
from dsl.validate import validate_file
from dsl.schema import DSL
from renderer.render import render_dsl


def _update_job(
    session,
    job_id: UUID | str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    job = session.get(Job, _coerce_uuid(job_id))
    if job is None:
        raise RuntimeError(f"Job not found: {job_id}")
    job.status = status
    now = datetime.utcnow()
    if status == "running" and job.started_at is None:
        job.started_at = now
    if status in {"succeeded", "failed"}:
        job.finished_at = now
    if result is not None:
        payload = job.payload or {}
        payload["result"] = result
        job.payload = payload
    if error is not None:
        job.error_payload = {"message": error}
    job.updated_at = now
    session.add(job)


def rq_on_failure(job: RQJob, connection, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
    session = SessionLocal()
    try:
        job_id = job.args[0] if job.args else None
        if job_id is None:
            return
        try:
            _update_job(session, job_id, "failed", error=str(exc_value))
            session.commit()
        except Exception:
            # Guard: callback errors must never crash worker maintenance loops.
            session.rollback()
    finally:
        session.close()


def rq_on_success(job: RQJob, connection, result, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    session = SessionLocal()
    try:
        job_id = job.args[0] if job.args else None
        if job_id is None:
            return
        try:
            _update_job(session, job_id, "succeeded")
            session.commit()
        except Exception:
            # Guard: callback errors must never crash worker maintenance loops.
            session.rollback()
    finally:
        session.close()


def _dsl_path(out_dir: Path) -> Path:
    return out_dir / "dsl.yaml"


def _load_template(template_path: Path) -> dict:
    if template_path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(template_path.read_text())
    if template_path.suffix.lower() == ".json":
        return json.loads(template_path.read_text())
    raise ValueError("DSL template must be .yaml/.yml/.json")


def _write_dsl_from_template(
    template_path: Path,
    target_path: Path,
    animation_code: str,
    title: str | None = None,
    idea: Idea | None = None,
) -> None:
    data = _load_template(template_path)
    if not isinstance(data, dict):
        raise ValueError("DSL template must be an object")

    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        raise ValueError("DSL meta must be an object")

    meta.setdefault("id", animation_code)
    if title:
        meta["title"] = title
    meta.setdefault("title", "auto-generated")
    if idea is not None:
        meta["seed"] = _idea_seed(idea)
    if "seed" not in meta:
        meta["seed"] = int(hashlib.sha256(animation_code.encode("utf-8")).hexdigest(), 16) % (
            2**31
        )

    data["meta"] = meta
    if idea is not None:
        _apply_idea_mapping(data, idea)
    target_path.write_text(yaml.safe_dump(data, sort_keys=False))


def _idea_seed(idea: Idea) -> int:
    payload = f"{idea.title}\n{idea.summary or ''}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest(), 16) % (2**31)


def _apply_idea_mapping(data: dict, idea: Idea) -> None:
    idea_hash = _hash_idea(idea.title, idea.summary or "")
    idea_num = int(idea_hash[:8], 16)
    meta = data.get("meta") or {}
    meta["seed"] = _idea_seed(idea)
    data["meta"] = meta

    palettes = [
        ["#0B0D0E", "#F2F4F5", "#4CC3FF", "#FFB84C"],
        ["#0F172A", "#F8FAFC", "#38BDF8", "#F43F5E"],
        ["#0B0F1A", "#F1F5F9", "#22C55E", "#F97316"],
        ["#111827", "#E5E7EB", "#A855F7", "#22D3EE"],
        ["#0B0D0E", "#F8FAFC", "#F59E0B", "#10B981"],
    ]
    palette = palettes[idea_num % len(palettes)]

    scene = data.get("scene") or {}
    canvas = scene.get("canvas") or {}
    base_duration = float(canvas.get("duration_s", 12))
    duration_delta = (idea_num % 9) - 4  # -4..+4
    duration = max(8.0, min(30.0, base_duration + duration_delta))
    canvas["duration_s"] = duration
    scene["canvas"] = canvas
    scene["palette"] = palette
    scene["background"] = palette[0]
    data["scene"] = scene

    systems = data.get("systems") or {}
    entities = systems.get("entities") or []
    if entities:
        core_color = palette[2]
        particle_color = palette[1]
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("id") == "core":
                ent["color"] = core_color
                ent["shape"] = "circle" if idea_num % 2 == 0 else "square"
                if "size" in ent and isinstance(ent["size"], (int, float)):
                    ent["size"] = max(60, min(180, int(ent["size"] * (0.8 + (idea_num % 4) * 0.1))))
            if ent.get("id") == "particle":
                ent["color"] = particle_color
                if "size" in ent and isinstance(ent["size"], (int, float)):
                    ent["size"] = max(8, min(26, int(ent["size"] * (0.8 + (idea_num % 3) * 0.1))))
    systems["entities"] = entities
    spawns = systems.get("spawns") or []
    count_factor = 0.8 + (idea_num % 5) * 0.1  # 0.8..1.2
    for spawn in spawns:
        if not isinstance(spawn, dict):
            continue
        if "count" in spawn and isinstance(spawn["count"], (int, float)):
            spawn["count"] = max(1, int(round(spawn["count"] * count_factor)))
        dist = spawn.get("distribution")
        if isinstance(dist, dict) and dist.get("type") == "orbit":
            params = dist.get("params") or {}
            if "radius" in params and isinstance(params["radius"], (int, float)):
                params["radius"] = max(120, min(420, int(params["radius"] * (0.7 + (idea_num % 6) * 0.1))))
            if "speed" in params and isinstance(params["speed"], (int, float)):
                params["speed"] = max(0.2, min(2.0, float(params["speed"]) * (0.7 + (idea_num % 6) * 0.1)))
            dist["params"] = params
            spawn["distribution"] = dist
    systems["spawns"] = spawns

    rules = systems.get("rules") or []
    speed_factor = 0.7 + (idea_num % 7) * 0.1  # 0.7..1.3
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        params = rule.get("params")
        if isinstance(params, dict) and "speed" in params:
            try:
                params["speed"] = max(0.1, float(params["speed"]) * speed_factor)
            except (TypeError, ValueError):
                pass
        if isinstance(params, dict) and rule.get("type") == "split":
            if "into" in params and isinstance(params["into"], (int, float)):
                params["into"] = max(2, min(6, int(params["into"] + (idea_num % 3) - 1)))
            if "speed_multiplier" in params and isinstance(params["speed_multiplier"], (int, float)):
                params["speed_multiplier"] = max(
                    0.8, min(2.2, float(params["speed_multiplier"]) * (0.8 + (idea_num % 4) * 0.1))
                )
    systems["rules"] = rules
    data["systems"] = systems


def generate_dsl_job(
    job_id: UUID | str,
    animation_id: UUID | str,
    dsl_template: str,
    out_root: str,
    idea_id: UUID | str | None = None,
    use_idea_gate: bool = False,
) -> dict:
    session = SessionLocal()
    try:
        _update_job(session, job_id, "running")
        session.commit()

        animation = session.get(Animation, _coerce_uuid(animation_id))
        if animation is None:
            raise RuntimeError(f"Animation not found: {animation_id}")

        out_dir = Path(out_root) / animation.animation_code
        out_dir.mkdir(parents=True, exist_ok=True)

        template_path = Path(dsl_template)
        if not template_path.exists():
            raise FileNotFoundError(f"DSL template not found: {template_path}")

        title = "auto-generated"
        idea = None
        if idea_id:
            idea = session.get(Idea, _coerce_uuid(idea_id))
            if idea is None:
                raise RuntimeError(f"Idea not found: {idea_id}")
            title = idea.title
            animation.idea_id = idea.id
        if use_idea_gate:
            raise RuntimeError("idea_selection_required")

        target_path = _dsl_path(out_dir)
        _write_dsl_from_template(
            template_path,
            target_path,
            animation.animation_code,
            title=title,
            idea=idea,
        )

        validate_file(target_path)
        dsl_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()

        animation.status = "queued"
        animation.pipeline_stage = "render"
        animation.updated_at = datetime.utcnow()
        session.add(animation)

        result = {"dsl_path": str(target_path), "dsl_hash": dsl_hash}
        _update_job(session, job_id, "succeeded", result=result)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _update_job(session, job_id, "failed", error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def render_job(job_id: UUID | str, animation_id: UUID | str, out_root: str) -> dict:
    session = SessionLocal()
    try:
        _update_job(session, job_id, "running")
        session.commit()

        animation = session.get(Animation, _coerce_uuid(animation_id))
        if animation is None:
            raise RuntimeError(f"Animation not found: {animation_id}")

        out_dir = Path(out_root) / animation.animation_code
        dsl_path = _dsl_path(out_dir)
        if not dsl_path.exists():
            raise FileNotFoundError(f"DSL not found for render: {dsl_path}")

        out_video = out_dir / "render.mp4"
        render_dsl(dsl_path, out_dir, out_video)

        metadata_path = out_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        model = validate_file(dsl_path)
        dsl_version = _get_or_create_dsl_version(session, model)
        design_version = _get_or_create_design_system_version(
            session, metadata.get("design_system_version", "mvp-0")
        )

        canvas = metadata.get("canvas", {})
        duration_ms = int(float(canvas.get("duration_s", 0)) * 1000)
        render = Render(
            animation_id=animation.id,
            status="succeeded",
            seed=int(metadata.get("seed", model.meta.seed)),
            dsl_version_id=dsl_version.id,
            design_system_version_id=design_version.id,
            renderer_version=metadata.get("renderer_version", "cairo-mvp-0"),
            duration_ms=duration_ms,
            width=int(canvas.get("width", 0)),
            height=int(canvas.get("height", 0)),
            fps=float(canvas.get("fps", 0)),
            params_json=model.model_dump(),
            metadata_json=metadata or None,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(render)
        session.flush()

        artifacts = [
            Artifact(
                render_id=render.id,
                artifact_type="video",
                storage_path=str(out_video),
                size_bytes=out_video.stat().st_size if out_video.exists() else None,
                created_at=datetime.utcnow(),
            ),
            Artifact(
                render_id=render.id,
                artifact_type="metadata",
                storage_path=str(metadata_path),
                size_bytes=metadata_path.stat().st_size if metadata_path.exists() else None,
                created_at=datetime.utcnow(),
            ),
            Artifact(
                render_id=render.id,
                artifact_type="dsl",
                storage_path=str(dsl_path),
                size_bytes=dsl_path.stat().st_size if dsl_path.exists() else None,
                created_at=datetime.utcnow(),
            ),
        ]
        session.add_all(artifacts)

        animation.status = "review"
        animation.pipeline_stage = "qc"
        animation.updated_at = datetime.utcnow()
        session.add(animation)

        result = {
            "video_path": str(out_video),
            "metadata_path": str(metadata_path),
        }
        _update_job(session, job_id, "succeeded", result=result)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _update_job(session, job_id, "failed", error=str(exc))
        session.commit()
        raise
    finally:
        session.close()


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _hash_idea(title: str, summary: str) -> str:
    payload = f"{title}\n{summary}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _get_or_create_dsl_version(session, model: DSL) -> DslVersion:
    stmt = select(DslVersion).where(DslVersion.version == model.dsl_version)
    found = session.execute(stmt).scalars().first()
    if found:
        return found
    schema_json = _dsl_schema_json()
    record = DslVersion(
        version=model.dsl_version,
        schema_json=schema_json,
        created_at=datetime.utcnow(),
    )
    session.add(record)
    session.flush()
    return record


def _get_or_create_design_system_version(session, version: str) -> DesignSystemVersion:
    stmt = select(DesignSystemVersion).where(DesignSystemVersion.version == version)
    found = session.execute(stmt).scalars().first()
    if found:
        return found
    record = DesignSystemVersion(
        version=version,
        meta=None,
        created_at=datetime.utcnow(),
    )
    session.add(record)
    session.flush()
    return record


def _dsl_schema_json() -> dict:
    if hasattr(DSL, "model_json_schema"):
        return DSL.model_json_schema()  # type: ignore[no-any-return]
    if hasattr(DSL, "schema"):
        return DSL.schema()  # type: ignore[no-any-return]
    return {"note": "schema unavailable"}
