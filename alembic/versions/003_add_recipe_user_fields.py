"""Add tried, review, and comments columns to recipes

Revision ID: 003
Revises: 002
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("tried", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "recipes",
        sa.Column("review", sa.Float(), nullable=True),
    )
    op.add_column(
        "recipes",
        sa.Column("comments", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipes", "comments")
    op.drop_column("recipes", "review")
    op.drop_column("recipes", "tried")
