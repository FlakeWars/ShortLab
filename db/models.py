from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Animation(Base):
    __tablename__ = "animations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="new")
    dsl_version: Mapped[str] = mapped_column(String(16))
    dsl_hash: Mapped[str] = mapped_column(String(64), index=True)
    dsl_payload: Mapped[dict] = mapped_column(JSON)
    design_system_version: Mapped[str] = mapped_column(String(32), default="mvp-0")
    seed: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    renders: Mapped[list["Render"]] = relationship(back_populates="animation")
    qc_decisions: Mapped[list["QCDecision"]] = relationship(back_populates="animation")


class Render(Base):
    __tablename__ = "renders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animation_id: Mapped[int] = mapped_column(ForeignKey("animations.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    renderer_version: Mapped[str] = mapped_column(String(32))
    output_path: Mapped[str] = mapped_column(Text)
    render_metadata: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animation: Mapped["Animation"] = relationship(back_populates="renders")


class QCDecision(Base):
    __tablename__ = "qc_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animation_id: Mapped[int] = mapped_column(ForeignKey("animations.id"))
    verdict: Mapped[str] = mapped_column(String(16))  # accepted/rejected
    reasons: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animation: Mapped["Animation"] = relationship(back_populates="qc_decisions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animation_id: Mapped[int | None] = mapped_column(
        ForeignKey("animations.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    what_to_expect: Mapped[str] = mapped_column(Text, default="")
    preview: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    generation_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_too_similar: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rq_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    animation_id: Mapped[int | None] = mapped_column(
        ForeignKey("animations.id"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
