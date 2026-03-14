"""Create recipes and ingredients tables

Revision ID: 001
Revises:
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("prep_time", sa.String(), nullable=True),
        sa.Column("cook_time", sa.String(), nullable=True),
        sa.Column("serves", sa.String(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recipes_url", "recipes", ["url"])

    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("quantity", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_ingredients_recipe_id", "ingredients", ["recipe_id"])
    op.create_index("ix_ingredients_name", "ingredients", ["name"])


def downgrade() -> None:
    op.drop_table("ingredients")
    op.drop_table("recipes")
