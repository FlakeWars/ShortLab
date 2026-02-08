"""add rejected candidate status

Revision ID: 8f4c3d2b1a9e
Revises: 2c5d3a4f1a2b
Create Date: 2026-02-08 12:00:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8f4c3d2b1a9e"
down_revision = "2c5d3a4f1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE idea_candidate DROP CONSTRAINT IF EXISTS ck_idea_candidate_status")
    op.execute(
        "ALTER TABLE idea_candidate ADD CONSTRAINT ck_idea_candidate_status "
        "CHECK (status in ('new', 'later', 'picked', 'rejected'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE idea_candidate DROP CONSTRAINT IF EXISTS ck_idea_candidate_status")
    op.execute(
        "ALTER TABLE idea_candidate ADD CONSTRAINT ck_idea_candidate_status "
        "CHECK (status in ('new', 'later', 'picked'))"
    )
