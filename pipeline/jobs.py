from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
import os
from random import Random
from pathlib import Path
from uuid import UUID

import yaml

from rq.job import Job as RQJob

from db.models import (
    Animation,
    Artifact,
    AuditEvent,
    DesignSystemVersion,
    DslVersion,
    Idea,
    IdeaBatch,
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
        _update_job(session, job_id, "failed", error=str(exc_value))
        session.commit()
    finally:
        session.close()


def rq_on_success(job: RQJob, connection, result, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    session = SessionLocal()
    try:
        job_id = job.args[0] if job.args else None
        if job_id is None:
            return
        _update_job(session, job_id, "succeeded")
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
    template_path: Path,
    target_path: Path,
    animation_code: str,
    title: str | None = None,
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
    if "seed" not in meta:
        seed = int(hashlib.sha256(animation_code.encode("utf-8")).hexdigest(), 16) % (
            2**31
        )
        meta["seed"] = seed

    data["meta"] = meta
    target_path.write_text(yaml.safe_dump(data, sort_keys=False))


def generate_dsl_job(
    job_id: UUID | str,
    animation_id: UUID | str,
    dsl_template: str,
    out_root: str,
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

        if use_idea_gate:
            from embeddings import EmbeddingConfig, EmbeddingService
            from ideas.generator import generate_ideas, save_ideas

            count = int(os.getenv("IDEA_GATE_COUNT", "3"))
            threshold = float(os.getenv("IDEA_GATE_THRESHOLD", "0.85"))
            rng = Random(
                int(hashlib.sha256(animation.animation_code.encode("utf-8")).hexdigest(), 16)
                % (2**31)
            )

            drafts = generate_ideas(
                source="auto",
                ideas_path=".ai/ideas.md",
                limit=max(1, count),
                seed=rng.randint(0, 10**6),
            )
            if not drafts:
                raise RuntimeError("Idea Gate enabled but no ideas found")

            rng.shuffle(drafts)
            pool = drafts[: max(1, min(count, len(drafts)))]

            embedder = EmbeddingService(EmbeddingConfig(provider="sklearn-hash"))
            idea_batch = IdeaBatch(
                run_date=date.today(),
                window_id=f"pipeline-{animation.animation_code}",
                source="manual",
                created_at=datetime.utcnow(),
            )
            session.add(idea_batch)
            session.flush()

            saved = save_ideas(
                session,
                pool,
                embedder,
                similarity_threshold=threshold,
                idea_batch_id=idea_batch.id,
            )
            if not saved:
                raise RuntimeError("Idea Gate saved no ideas (dedupe/validation)")

            candidates = [i for i in saved if i.similarity_status != "too_similar"]
            selected = (
                min(candidates, key=lambda i: getattr(i, "max_similarity", 0.0) or 0.0)
                if candidates
                else min(saved, key=lambda i: getattr(i, "max_similarity", 0.0) or 0.0)
            )
            title = selected.title
            selected.selected = True
            selected.selected_at = datetime.utcnow()
            idea = Idea(
                idea_candidate_id=selected.id,
                title=selected.title,
                summary=selected.summary,
                what_to_expect=selected.what_to_expect,
                preview=selected.preview,
                idea_hash=_hash_idea(selected.title, selected.summary or ""),
                created_at=datetime.utcnow(),
            )
            session.add(idea)
            session.flush()
            animation.idea_id = idea.id

            audit = AuditEvent(
                event_type="idea_selected",
                source="worker",
                occurred_at=datetime.utcnow(),
                payload={
                    "idea_id": idea.id,
                    "selection_mode": "pipeline",
                    "threshold": threshold,
                },
            )
            session.add(audit)
            session.commit()
        else:
            title = "auto-generated"
            summary = ""

        target_path = _dsl_path(out_dir)
        _write_dsl_from_template(template_path, target_path, animation.animation_code, title=title)

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
