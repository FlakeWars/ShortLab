"""add idea embedding metadata

Revision ID: 1d7b9a2f6c3e
Revises: 4b2c7f0a0c51
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1d7b9a2f6c3e"
down_revision = "4b2c7f0a0c51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("embedding_model", sa.String(length=128), nullable=True))
    op.add_column("ideas", sa.Column("embedding_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("ideas", "embedding_version")
    op.drop_column("ideas", "embedding_model")
