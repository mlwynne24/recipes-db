"""Create recipe_embeddings virtual table (sqlite-vec)

Revision ID: 002
Revises: 001
Create Date: 2026-03-14
"""

from alembic import op
from sqlalchemy import text

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from src.config.settings import settings

    dim = settings.embedding_dimension
    op.execute(
        text(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS recipe_embeddings "
            f"USING vec0(recipe_id INTEGER PRIMARY KEY, "
            f"embedding float[{dim}] distance_metric=cosine)"
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS recipe_embeddings"))
