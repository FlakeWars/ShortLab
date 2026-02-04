from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import delete, text

from db.models import Animation, Artifact, Idea, Job, Render
from db.session import SessionLocal
import pipeline.jobs as pipeline_jobs
import ideas.compiler as compiler_module


def _require_db() -> None:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
            required = {
                "idea": {"status"},
                "animation": {"pipeline_stage"},
                "job": {"job_type"},
            }
            for table_name, required_cols in required.items():
                rows = session.execute(
                    text(
                        """
                        select column_name
                        from information_schema.columns
                        where table_schema='public' and table_name=:table_name
                        """
                    ),
                    {"table_name": table_name},
                ).all()
                present = {row[0] for row in rows}
                if not required_cols.issubset(present):
                    missing = ",".join(sorted(required_cols - present))
                    raise RuntimeError(
                        f"DB schema drift for table '{table_name}' (missing: {missing}); "
                        "run make test-idea-compiler-pipeline-e2e"
                    )
    except RuntimeError:
        raise
    except Exception as exc:  # pragma: no cover - depends on local env
        pytest.skip(f"DB not ready for pipeline e2e test: {exc}")


class _TemplateMediator:
    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path

    def generate_json(self, *, user_prompt: str, **_kwargs):  # type: ignore[no-untyped-def]
        title = _extract_line(user_prompt, "Idea title:")
        summary = _extract_line(user_prompt, "Idea summary:")
        payload = yaml.safe_load(self.template_path.read_text())
        seed = int.from_bytes(f"{title}|{summary}".encode("utf-8"), "little", signed=False) % (2**31)
        palette = [
            ["#0B0D0E", "#F2F4F5", "#4CC3FF", "#FFB84C"],
            ["#0F172A", "#F8FAFC", "#38BDF8", "#F43F5E"],
            ["#0B0F1A", "#F1F5F9", "#22C55E", "#F97316"],
            ["#111827", "#E5E7EB", "#A855F7", "#22D3EE"],
            ["#0B0D0E", "#F8FAFC", "#F59E0B", "#10B981"],
        ][seed % 5]
        payload["meta"]["title"] = title
        payload["meta"]["seed"] = seed
        payload["scene"]["palette"] = palette
        payload["scene"]["background"] = palette[0]
        for entity in payload["systems"]["entities"]:
            if entity["id"] == "core":
                entity["color"] = palette[2]
            if entity["id"] == "particle":
                entity["color"] = palette[1]
        return {"dsl_yaml": yaml.safe_dump(payload, sort_keys=False)}, {"provider": "test", "model": "template"}


def _extract_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "", 1).strip()
    return ""


def test_pipeline_generate_and_render_for_five_ideas(monkeypatch, tmp_path: Path) -> None:
    _require_db()
    template = Path(".ai/examples/dsl-v1-happy.yaml")
    monkeypatch.setenv("IDEA_DSL_COMPILER_ENABLED", "1")
    monkeypatch.setenv("IDEA_DSL_COMPILER_FALLBACK_TEMPLATE", "0")
    monkeypatch.setattr(compiler_module, "get_mediator", lambda: _TemplateMediator(template))

    def _fake_render_dsl(dsl_path: Path, out_dir: Path, out_video: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_video.write_bytes(b"fake-video")
        dsl_data = yaml.safe_load(Path(dsl_path).read_text())
        meta = dsl_data.get("meta", {})
        canvas = dsl_data.get("scene", {}).get("canvas", {})
        metadata = {
            "seed": int(meta.get("seed", 0)),
            "renderer_version": "fake-renderer-test",
            "design_system_version": "mvp-0",
            "canvas": {
                "width": int(canvas.get("width", 1080)),
                "height": int(canvas.get("height", 1920)),
                "fps": int(canvas.get("fps", 30)),
                "duration_s": float(canvas.get("duration_s", 12)),
            },
        }
        (out_dir / "metadata.json").write_text(json.dumps(metadata))

    monkeypatch.setattr(pipeline_jobs, "render_dsl", _fake_render_dsl)

    created_ids: dict[str, list] = {"ideas": [], "animations": [], "jobs": [], "renders": [], "artifacts": []}
    hashes: list[str] = []
    out_root = tmp_path / "pipeline-e2e"

    try:
        for idx in range(5):
            with SessionLocal() as session:
                idea = Idea(
                    id=uuid4(),
                    title=f"Pipeline idea {idx}",
                    summary=f"summary {idx}",
                    what_to_expect=f"expect {idx}",
                    preview=f"preview {idx}",
                    status="feasible",
                )
                animation = Animation(
                    id=uuid4(),
                    animation_code=f"idea-e2e-{idx}-{uuid4().hex[:8]}",
                    status="queued",
                    pipeline_stage="idea",
                    idea_id=idea.id,
                )
                gen_job = Job(id=uuid4(), job_type="generate_dsl", status="queued", payload={}, max_attempts=1, attempt=1)
                render_job = Job(id=uuid4(), job_type="render", status="queued", payload={}, max_attempts=1, attempt=1)
                session.add_all([idea, animation, gen_job, render_job])
                session.commit()
                created_ids["ideas"].append(idea.id)
                created_ids["animations"].append(animation.id)
                created_ids["jobs"].extend([gen_job.id, render_job.id])

            gen_result = pipeline_jobs.generate_dsl_job(
                job_id=gen_job.id,
                animation_id=animation.id,
                dsl_template=str(template),
                out_root=str(out_root),
                idea_id=idea.id,
                use_idea_gate=False,
            )
            hashes.append(gen_result["dsl_hash"])
            assert gen_result["validation_report"]["semantic_ok"] is True

            render_result = pipeline_jobs.render_job(
                job_id=render_job.id,
                animation_id=animation.id,
                out_root=str(out_root),
            )
            assert "video_path" in render_result

        assert len(set(hashes)) == 5
    finally:
        with SessionLocal() as session:
            render_ids = session.execute(select_ids(Render.id, created_ids["animations"], Render.animation_id)).all()
            created_ids["renders"] = [row[0] for row in render_ids]
            if created_ids["renders"]:
                artifact_ids = session.execute(select_ids(Artifact.id, created_ids["renders"], Artifact.render_id)).all()
                created_ids["artifacts"] = [row[0] for row in artifact_ids]

            if created_ids["artifacts"]:
                session.execute(delete(Artifact).where(Artifact.id.in_(created_ids["artifacts"])))
            if created_ids["renders"]:
                session.execute(delete(Render).where(Render.id.in_(created_ids["renders"])))
            if created_ids["jobs"]:
                session.execute(delete(Job).where(Job.id.in_(created_ids["jobs"])))
            if created_ids["animations"]:
                session.execute(delete(Animation).where(Animation.id.in_(created_ids["animations"])))
            if created_ids["ideas"]:
                session.execute(delete(Idea).where(Idea.id.in_(created_ids["ideas"])))
            session.commit()


def select_ids(column, ids, fk_column):
    from sqlalchemy import select

    return select(column).where(fk_column.in_(ids))
