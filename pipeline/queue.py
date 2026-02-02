import os
from uuid import uuid4

from redis import Redis
from rq import Queue

from datetime import datetime

from db.models import Animation, Job
from db.session import SessionLocal
from pipeline.jobs import (
    generate_dsl_job,
    render_job,
    rq_on_failure,
    rq_on_success,
)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _timeout_seconds(kind: str) -> int:
    if kind == "render":
        return int(os.getenv("RQ_RENDER_TIMEOUT", "600"))
    return int(os.getenv("RQ_JOB_TIMEOUT", "120"))


def get_redis() -> Redis:
    return Redis.from_url(_redis_url())


def get_queue(name: str = "default") -> Queue:
    return Queue(name, connection=get_redis())


def enqueue_pipeline(
    dsl_template: str,
    out_root: str,
    use_idea_gate: bool = False,
) -> dict:
    session = SessionLocal()
    try:
        animation = Animation(
            animation_code=uuid4().hex,
            status="queued",
            pipeline_stage="idea",
        )
        session.add(animation)
        session.commit()
        session.refresh(animation)

        gen_job = Job(
            job_type="generate_dsl",
            status="queued",
            payload={
                "animation_id": str(animation.id),
                "dsl_template": dsl_template,
                "out_root": out_root,
                "use_idea_gate": use_idea_gate,
            },
            queued_at=datetime.utcnow(),
        )
        session.add(gen_job)
        session.commit()
        session.refresh(gen_job)

        queue = get_queue()
        rq_gen = queue.enqueue(
            generate_dsl_job,
            gen_job.id,
            animation.id,
            dsl_template,
            out_root,
            use_idea_gate,
            job_timeout=_timeout_seconds("generate"),
            on_failure=rq_on_failure,
            on_success=rq_on_success,
        )
        gen_payload = gen_job.payload or {}
        gen_payload["rq_id"] = rq_gen.id
        gen_job.payload = gen_payload
        session.commit()

        render_db_job = Job(
            job_type="render",
            status="queued",
            payload={"out_root": out_root, "animation_id": str(animation.id)},
            queued_at=datetime.utcnow(),
        )
        session.add(render_db_job)
        session.commit()
        session.refresh(render_db_job)

        rq_render = queue.enqueue(
            render_job,
            render_db_job.id,
            animation.id,
            out_root,
            depends_on=rq_gen,
            job_timeout=_timeout_seconds("render"),
            on_failure=rq_on_failure,
            on_success=rq_on_success,
        )
        render_payload = render_db_job.payload or {}
        render_payload["rq_id"] = rq_render.id
        render_db_job.payload = render_payload
        session.commit()

        return {
            "animation_id": animation.id,
            "rq_generate_id": rq_gen.id,
            "rq_render_id": rq_render.id,
        }
    finally:
        session.close()


def enqueue_render(animation_id: str, out_root: str) -> dict:
    session = SessionLocal()
    try:
        animation = session.get(Animation, animation_id)
        if animation is None:
            raise RuntimeError(f"Animation not found: {animation_id}")

        render_db_job = Job(
            job_type="render",
            status="queued",
            payload={"out_root": out_root, "rerun": True, "animation_id": str(animation.id)},
            queued_at=datetime.utcnow(),
        )
        session.add(render_db_job)
        session.commit()
        session.refresh(render_db_job)

        queue = get_queue()
        rq_render = queue.enqueue(
            render_job,
            render_db_job.id,
            animation.id,
            out_root,
            job_timeout=_timeout_seconds("render"),
            on_failure=rq_on_failure,
            on_success=rq_on_success,
        )
        render_payload = render_db_job.payload or {}
        render_payload["rq_id"] = rq_render.id
        render_db_job.payload = render_payload
        session.commit()

        return {
            "animation_id": animation.id,
            "rq_render_id": rq_render.id,
        }
    finally:
        session.close()
