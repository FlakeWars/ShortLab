from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml

from rq.job import Job as RQJob

from db.models import Animation, Job, Render
from db.session import SessionLocal
from dsl.validate import validate_file
from renderer.render import render_dsl


def _update_job(
    session,
    job_id: int,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise RuntimeError(f"Job not found: {job_id}")
    job.status = status
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    job.updated_at = datetime.utcnow()
    session.add(job)


def rq_on_failure(job: RQJob, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
    session = SessionLocal()
    try:
        job_id = job.args[0] if job.args else None
        if job_id is None:
            return
        _update_job(session, int(job_id), "failed", error=str(exc_value))
        session.commit()
    finally:
        session.close()


def rq_on_success(job: RQJob, connection, result, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    session = SessionLocal()
    try:
        job_id = job.args[0] if job.args else None
        if job_id is None:
            return
        _update_job(session, int(job_id), "succeeded")
        session.commit()
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
    template_path: Path, target_path: Path, animation_uuid: str
) -> None:
    data = _load_template(template_path)
    if not isinstance(data, dict):
        raise ValueError("DSL template must be an object")

    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        raise ValueError("DSL meta must be an object")

    meta.setdefault("id", animation_uuid)
    meta.setdefault("title", "auto-generated")
    if "seed" not in meta:
        seed = int(hashlib.sha256(animation_uuid.encode("utf-8")).hexdigest(), 16) % (
            2**31
        )
        meta["seed"] = seed

    data["meta"] = meta
    target_path.write_text(yaml.safe_dump(data, sort_keys=False))


def generate_dsl_job(
    job_id: int,
    animation_id: int,
    dsl_template: str,
    out_root: str,
) -> dict:
    session = SessionLocal()
    try:
        _update_job(session, job_id, "running")
        session.commit()

        animation = session.get(Animation, animation_id)
        if animation is None:
            raise RuntimeError(f"Animation not found: {animation_id}")

        out_dir = Path(out_root) / animation.uuid
        out_dir.mkdir(parents=True, exist_ok=True)

        template_path = Path(dsl_template)
        if not template_path.exists():
            raise FileNotFoundError(f"DSL template not found: {template_path}")

        target_path = _dsl_path(out_dir)
        _write_dsl_from_template(template_path, target_path, animation.uuid)

        model = validate_file(target_path)
        payload = model.model_dump()
        dsl_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()

        animation.title = model.meta.title
        animation.status = "dsl_ready"
        animation.dsl_version = model.dsl_version
        animation.dsl_hash = dsl_hash
        animation.dsl_payload = payload
        animation.seed = model.meta.seed
        animation.design_system_version = "mvp-0"
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


def render_job(job_id: int, animation_id: int, out_root: str) -> dict:
    session = SessionLocal()
    try:
        _update_job(session, job_id, "running")
        session.commit()

        animation = session.get(Animation, animation_id)
        if animation is None:
            raise RuntimeError(f"Animation not found: {animation_id}")

        out_dir = Path(out_root) / animation.uuid
        dsl_path = _dsl_path(out_dir)
        if not dsl_path.exists():
            raise FileNotFoundError(f"DSL not found for render: {dsl_path}")

        out_video = out_dir / "render.mp4"
        render_dsl(dsl_path, out_dir, out_video)

        metadata_path = out_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        render = Render(
            animation_id=animation.id,
            status="succeeded",
            renderer_version=metadata.get("renderer_version", "cairo-mvp-0"),
            output_path=str(out_video),
            render_metadata=metadata,
        )
        session.add(render)

        animation.status = "rendered"
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
