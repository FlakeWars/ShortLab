"""add dsl version metadata and gap resolution fields

Revision ID: 6b8d0f2b4c3a
Revises: 8980ce8917df
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6b8d0f2b4c3a"
down_revision = "8980ce8917df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dsl_version", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("dsl_version", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "dsl_version",
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dsl_version_created_by_user",
        "dsl_version",
        "user_account",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("dsl_gap", sa.Column("implemented_in_version", sa.Text(), nullable=True))
    op.add_column("dsl_gap", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "dsl_gap",
        sa.Column("resolved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dsl_gap_resolved_by_user",
        "dsl_gap",
        "user_account",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_dsl_gap_resolved_by_user", "dsl_gap", type_="foreignkey")
    op.drop_column("dsl_gap", "resolved_by")
    op.drop_column("dsl_gap", "resolved_at")
    op.drop_column("dsl_gap", "implemented_in_version")

    op.drop_constraint("fk_dsl_version_created_by_user", "dsl_version", type_="foreignkey")
    op.drop_column("dsl_version", "created_by")
    op.drop_column("dsl_version", "notes")
    op.drop_column("dsl_version", "is_active")
