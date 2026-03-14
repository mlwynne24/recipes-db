"""Add tried_on date column to recipes

Revision ID: 004
Revises: 003
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("tried_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipes", "tried_on")
