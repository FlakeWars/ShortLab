"""add jobs table

Revision ID: 4b2c7f0a0c51
Revises: ea724f50b0a2
Create Date: 2026-02-02 11:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "4b2c7f0a0c51"
down_revision = "ea724f50b0a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rq_id", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("animation_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["animation_id"], ["animations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_rq_id"), "jobs", ["rq_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_rq_id"), table_name="jobs")
    op.drop_table("jobs")
