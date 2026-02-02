"""add idea details fields

Revision ID: 1b9b3c2d9c1a
Revises: 6e3cbd8f7f45
Create Date: 2026-02-02 13:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "1b9b3c2d9c1a"
down_revision = "6e3cbd8f7f45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("what_to_expect", sa.Text(), nullable=False, server_default=""))
    op.add_column("ideas", sa.Column("preview", sa.Text(), nullable=False, server_default=""))
    op.alter_column("ideas", "what_to_expect", server_default=None)
    op.alter_column("ideas", "preview", server_default=None)


def downgrade() -> None:
    op.drop_column("ideas", "preview")
    op.drop_column("ideas", "what_to_expect")
