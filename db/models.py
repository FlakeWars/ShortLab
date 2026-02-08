from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UserAccount(Base):
    __tablename__ = "user_account"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(CITEXT(), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class DslVersion(Base):
    __tablename__ = "dsl_version"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    version: Mapped[str] = mapped_column(Text, unique=True)
    schema_json: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DesignSystemVersion(Base):
    __tablename__ = "design_system_version"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    version: Mapped[str] = mapped_column(Text, unique=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class IdeaBatch(Base):
    __tablename__ = "idea_batch"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    run_date: Mapped[date] = mapped_column(Date)
    window_id: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    candidates: Mapped[list["IdeaCandidate"]] = relationship(back_populates="idea_batch")

    __table_args__ = (
        CheckConstraint("source in ('schedule', 'manual')", name="ck_idea_batch_source"),
        UniqueConstraint("run_date", "window_id", name="uq_idea_batch_run_window"),
    )


class IdeaCandidate(Base):
    __tablename__ = "idea_candidate"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_batch.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    what_to_expect: Mapped[str | None] = mapped_column(Text)
    preview: Mapped[str | None] = mapped_column(Text)
    generator_source: Mapped[str] = mapped_column(Text)
    similarity_status: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="new")
    capability_status: Mapped[str] = mapped_column(Text, default="unverified")
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    selected_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    idea_batch: Mapped["IdeaBatch"] = relationship(back_populates="candidates")
    idea: Mapped["Idea | None"] = relationship(back_populates="idea_candidate", uselist=False)
    gap_links: Mapped[list["IdeaCandidateGapLink"]] = relationship(
        back_populates="idea_candidate",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "generator_source in ('ai', 'fallback', 'manual')",
            name="ck_idea_candidate_generator_source",
        ),
        CheckConstraint(
            "similarity_status in ('ok', 'too_similar', 'unknown')",
            name="ck_idea_candidate_similarity_status",
        ),
        CheckConstraint(
            "status in ('new', 'later', 'picked', 'rejected')",
            name="ck_idea_candidate_status",
        ),
        CheckConstraint(
            "capability_status in ('unverified', 'feasible', 'blocked_by_gaps')",
            name="ck_idea_candidate_capability_status",
        ),
    )


class Idea(Base):
    __tablename__ = "idea"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_candidate_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_candidate.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    what_to_expect: Mapped[str | None] = mapped_column(Text)
    preview: Mapped[str | None] = mapped_column(Text)
    idea_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    idea_candidate: Mapped["IdeaCandidate | None"] = relationship(back_populates="idea")
    animations: Mapped[list["Animation"]] = relationship(back_populates="idea")
    gap_links: Mapped[list["IdeaGapLink"]] = relationship(back_populates="idea", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status in ('unverified', 'feasible', 'blocked_by_gaps', 'ready_for_gate', 'picked', 'compiled')",
            name="ck_idea_status",
        ),
    )


class DslGap(Base):
    __tablename__ = "dsl_gap"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    gap_key: Mapped[str] = mapped_column(Text)
    dsl_version: Mapped[str] = mapped_column(Text)
    feature: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="new")
    implemented_in_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    idea_links: Mapped[list["IdeaGapLink"]] = relationship(back_populates="dsl_gap", cascade="all, delete-orphan")
    candidate_links: Mapped[list["IdeaCandidateGapLink"]] = relationship(
        back_populates="dsl_gap",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("gap_key", name="uq_dsl_gap_gap_key"),
        CheckConstraint(
            "status in ('new', 'accepted', 'in_progress', 'implemented', 'rejected')",
            name="ck_dsl_gap_status",
        ),
    )


class IdeaGapLink(Base):
    __tablename__ = "idea_gap_link"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea.id", ondelete="CASCADE"),
    )
    dsl_gap_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dsl_gap.id", ondelete="CASCADE"),
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    idea: Mapped["Idea"] = relationship(back_populates="gap_links")
    dsl_gap: Mapped["DslGap"] = relationship(back_populates="idea_links")

    __table_args__ = (
        UniqueConstraint("idea_id", "dsl_gap_id", name="uq_idea_gap_link_idea_gap"),
    )


class IdeaCandidateGapLink(Base):
    __tablename__ = "idea_candidate_gap_link"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_candidate.id", ondelete="CASCADE"),
    )
    dsl_gap_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dsl_gap.id", ondelete="CASCADE"),
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    idea_candidate: Mapped["IdeaCandidate"] = relationship(back_populates="gap_links")
    dsl_gap: Mapped["DslGap"] = relationship(back_populates="candidate_links")

    __table_args__ = (
        UniqueConstraint(
            "idea_candidate_id",
            "dsl_gap_id",
            name="uq_idea_candidate_gap_link_candidate_gap",
        ),
    )


class IdeaSimilarity(Base):
    __tablename__ = "idea_similarity"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_candidate.id", ondelete="CASCADE"),
    )
    compared_idea_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea.id", ondelete="CASCADE"),
    )
    score: Mapped[float] = mapped_column(Numeric(5, 4))
    embedding_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("idea_candidate_id", "compared_idea_id", name="uq_idea_similarity_pair"),
    )


class IdeaEmbedding(Base):
    __tablename__ = "idea_embedding"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_candidate.id", ondelete="CASCADE"),
    )
    idea_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    vector: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("idea_candidate_id", "version", name="uq_idea_embedding_candidate_version"),
    )


class Animation(Base):
    __tablename__ = "animation"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    animation_code: Mapped[str] = mapped_column(Text, unique=True)
    idea_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_animation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("animation.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(Text)
    pipeline_stage: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    soft_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    idea: Mapped["Idea | None"] = relationship(back_populates="animations")
    renders: Mapped[list["Render"]] = relationship(back_populates="animation")

    __table_args__ = (
        UniqueConstraint("animation_code", name="uq_animation_animation_code"),
        CheckConstraint(
            "status in ('draft', 'queued', 'running', 'review', 'accepted', 'rejected', 'published', 'archived')",
            name="ck_animation_status",
        ),
        CheckConstraint(
            "pipeline_stage in ('idea', 'render', 'qc', 'publish', 'metrics', 'done')",
            name="ck_animation_pipeline_stage",
        ),
    )


class Render(Base):
    __tablename__ = "render"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    animation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("animation.id", ondelete="CASCADE"),
    )
    source_render_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("render.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(BigInteger)
    dsl_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dsl_version.id"),
    )
    design_system_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("design_system_version.id"),
    )
    renderer_version: Mapped[str] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    fps: Mapped[float] = mapped_column(Numeric(6, 3))
    params_json: Mapped[dict] = mapped_column(JSONB)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    animation: Mapped["Animation"] = relationship(back_populates="renders")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="render")

    __table_args__ = (
        CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_render_status"),
        CheckConstraint("duration_ms >= 0", name="ck_render_duration_non_negative"),
    )


class Artifact(Base):
    __tablename__ = "artifact"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    render_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("render.id", ondelete="CASCADE"),
    )
    artifact_type: Mapped[str] = mapped_column(Text)
    storage_path: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    render: Mapped["Render"] = relationship(back_populates="artifacts")

    __table_args__ = (
        CheckConstraint(
            "artifact_type in ('video', 'preview', 'thumbnail', 'dsl', 'metadata', 'other')",
            name="ck_artifact_type",
        ),
    )


class QCChecklistVersion(Base):
    __tablename__ = "qc_checklist_version"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_qc_checklist_version_name_version"),
    )


class QCChecklistItem(Base):
    __tablename__ = "qc_checklist_item"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    checklist_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qc_checklist_version.id", ondelete="CASCADE"),
    )
    item_key: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("severity in ('hard', 'soft')", name="ck_qc_checklist_item_severity"),
        UniqueConstraint("checklist_version_id", "item_key", name="uq_qc_checklist_item_key"),
    )


class QCDecision(Base):
    __tablename__ = "qc_decision"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    animation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("animation.id", ondelete="CASCADE"),
    )
    checklist_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qc_checklist_version.id"),
    )
    result: Mapped[str] = mapped_column(Text)
    decision_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("result in ('accepted', 'rejected', 'regenerate')", name="ck_qc_decision_result"),
    )


class PublishRecord(Base):
    __tablename__ = "publish_record"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    render_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("render.id", ondelete="CASCADE"),
    )
    platform_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    content_id: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_publish_record_platform_type"),
        CheckConstraint(
            "status in ('queued', 'uploading', 'published', 'failed', 'manual_confirmed')",
            name="ck_publish_record_status",
        ),
        UniqueConstraint("platform_type", "content_id", name="uq_publish_record_platform_content"),
    )


class MetricsPullRun(Base):
    __tablename__ = "metrics_pull_run"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    platform_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_metrics_pull_run_platform_type"),
        CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_metrics_pull_run_status"),
        CheckConstraint("source in ('api', 'manual')", name="ck_metrics_pull_run_source"),
    )


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    platform_type: Mapped[str] = mapped_column(Text)
    content_id: Mapped[str] = mapped_column(Text)
    publish_record_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("publish_record.id", ondelete="SET NULL"),
        nullable=True,
    )
    render_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("render.id", ondelete="SET NULL"),
        nullable=True,
    )
    date: Mapped[date] = mapped_column(Date)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_seconds: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_view_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    avg_view_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_metrics_daily_platform_type"),
        UniqueConstraint("platform_type", "content_id", "date", name="uq_metrics_daily_content_date"),
    )


class LLMMediatorRouteMetric(Base):
    __tablename__ = "llm_mediator_route_metric"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    day: Mapped[date] = mapped_column(Date)
    task_type: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms_total: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    prompt_tokens_total: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_tokens_total: Mapped[int] = mapped_column(BigInteger, default=0)
    estimated_cost_usd_total: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "day",
            "task_type",
            "provider",
            "model",
            name="uq_llm_mediator_route_metric_day_route",
        ),
    )


class LLMMediatorBudgetDaily(Base):
    __tablename__ = "llm_mediator_budget_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    spent_usd_total: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    daily_budget_usd: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, unique=True)
    tag_type: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("tag_type in ('canonical', 'experimental')", name="ck_tag_type"),
    )


class AnimationTag(Base):
    __tablename__ = "animation_tag"

    animation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("animation.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TagEvent(Base):
    __tablename__ = "tag_event"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    animation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("animation.id", ondelete="CASCADE"),
    )
    tag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tag.id", ondelete="CASCADE"),
    )
    action: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("action in ('added', 'removed', 'edited')", name="ck_tag_event_action"),
        CheckConstraint("source in ('ui', 'system')", name="ck_tag_event_source"),
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_run"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    idea_batch_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("idea_batch.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_date: Mapped[date] = mapped_column(Date)
    window_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('scheduled', 'running', 'succeeded', 'failed', 'canceled')",
            name="ck_pipeline_run_status",
        ),
        UniqueConstraint("run_date", "window_id", name="uq_pipeline_run_run_window"),
    )


class Job(Base):
    __tablename__ = "job"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    job_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    parent_job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_job_status"),
    )


class JobStageRun(Base):
    __tablename__ = "job_stage_run"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pipeline_run.id", ondelete="CASCADE"),
    )
    stage: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "stage in ('generate', 'idea_gate', 'render', 'qc', 'publish', 'metrics')",
            name="ck_job_stage_run_stage",
        ),
        CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_job_stage_run_status"),
    )


class PlatformConfig(Base):
    __tablename__ = "platform_config"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    platform_type: Mapped[str] = mapped_column(Text)
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary)
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_platform_config_platform_type"),
        UniqueConstraint("platform_type", name="uq_platform_config_platform_type"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("source in ('ui', 'system', 'worker')", name="ck_audit_event_source"),
    )
