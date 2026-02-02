"""add idea generation fields

Revision ID: 2e3b4d7a91c2
Revises: 1d7b9a2f6c3e
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2e3b4d7a91c2"
down_revision = "1d7b9a2f6c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("ideas", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column("ideas", sa.Column("generation_meta", sa.JSON(), nullable=True))
    op.create_index("ix_ideas_content_hash", "ideas", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_ideas_content_hash", table_name="ideas")
    op.drop_column("ideas", "generation_meta")
    op.drop_column("ideas", "source")
    op.drop_column("ideas", "content_hash")
