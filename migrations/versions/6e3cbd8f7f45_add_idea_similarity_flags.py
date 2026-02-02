"""add idea similarity flags

Revision ID: 6e3cbd8f7f45
Revises: 4b2c7f0a0c51
Create Date: 2026-02-02 12:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "6e3cbd8f7f45"
down_revision = "4b2c7f0a0c51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("ideas", sa.Column("is_too_similar", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_ideas_content_hash"), "ideas", ["content_hash"], unique=False)
    op.execute("UPDATE ideas SET content_hash = '' WHERE content_hash IS NULL")
    op.alter_column("ideas", "content_hash", nullable=False)
    op.alter_column("ideas", "is_too_similar", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_ideas_content_hash"), table_name="ideas")
    op.drop_column("ideas", "is_too_similar")
    op.drop_column("ideas", "content_hash")
