"""add candidate capability status + gap links

Revision ID: 7b6d4a2c0f31
Revises: 2c5d3a4f1a2b
Create Date: 2026-02-05 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "7b6d4a2c0f31"
down_revision = "2c5d3a4f1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "idea_candidate",
        sa.Column(
            "capability_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
    )
    op.create_check_constraint(
        "ck_idea_candidate_capability_status",
        "idea_candidate",
        "capability_status in ('unverified', 'feasible', 'blocked_by_gaps')",
    )

    op.create_table(
        "idea_candidate_gap_link",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("idea_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dsl_gap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_candidate_id"], ["idea_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dsl_gap_id"], ["dsl_gap.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "idea_candidate_id",
            "dsl_gap_id",
            name="uq_idea_candidate_gap_link_candidate_gap",
        ),
    )


def downgrade() -> None:
    op.drop_table("idea_candidate_gap_link")
    op.drop_constraint("ck_idea_candidate_capability_status", "idea_candidate", type_="check")
    op.drop_column("idea_candidate", "capability_status")
