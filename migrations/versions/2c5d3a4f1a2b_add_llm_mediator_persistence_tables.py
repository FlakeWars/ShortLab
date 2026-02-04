"""add llm mediator persistence tables

Revision ID: 2c5d3a4f1a2b
Revises: 9f3a2c7d8b1e
Create Date: 2026-02-04 11:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "2c5d3a4f1a2b"
down_revision = "9f3a2c7d8b1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_mediator_route_metric",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms_total", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("prompt_tokens_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("completion_tokens_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd_total", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "day",
            "task_type",
            "provider",
            "model",
            name="uq_llm_mediator_route_metric_day_route",
        ),
    )
    op.create_index(
        "ix_llm_mediator_route_metric_day",
        "llm_mediator_route_metric",
        ["day"],
        unique=False,
    )
    op.create_table(
        "llm_mediator_budget_daily",
        sa.Column("day", sa.Date(), primary_key=True, nullable=False),
        sa.Column("spent_usd_total", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("daily_budget_usd", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("llm_mediator_budget_daily")
    op.drop_index("ix_llm_mediator_route_metric_day", table_name="llm_mediator_route_metric")
    op.drop_table("llm_mediator_route_metric")
