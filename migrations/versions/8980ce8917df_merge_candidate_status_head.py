"""merge candidate status head

Revision ID: 8980ce8917df
Revises: 7b6d4a2c0f31, 8f4c3d2b1a9e
Create Date: 2026-02-08 13:37:51.499828
"""

from alembic import op
import sqlalchemy as sa

revision = '8980ce8917df'
down_revision = ('7b6d4a2c0f31', '8f4c3d2b1a9e')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
