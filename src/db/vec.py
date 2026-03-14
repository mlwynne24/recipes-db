import sqlite_vec
from sqlalchemy import text
from sqlmodel import Session

from src.config.settings import settings


def serialize_float32(vec: list[float]) -> bytes:
    return sqlite_vec.serialize_float32(vec)


def insert_embedding(session: Session, recipe_id: int, embedding: list[float]) -> None:
    serialized = serialize_float32(embedding)
    session.execute(
        text(
            "INSERT OR REPLACE INTO recipe_embeddings(recipe_id, embedding) "
            "VALUES (:recipe_id, :embedding)"
        ),
        {"recipe_id": recipe_id, "embedding": serialized},
    )
    session.commit()


def knn_search(
    session: Session, query_embedding: list[float], k: int
) -> list[tuple[int, float]]:
    serialized = serialize_float32(query_embedding)
    result = session.execute(
        text(
            "SELECT recipe_id, distance FROM recipe_embeddings "
            "WHERE embedding MATCH :embedding AND k = :k "
            "ORDER BY distance"
        ),
        {"embedding": serialized, "k": k},
    )
    return [(row[0], row[1]) for row in result]


def delete_embedding(session: Session, recipe_id: int) -> None:
    session.execute(
        text("DELETE FROM recipe_embeddings WHERE recipe_id = :id"),
        {"id": recipe_id},
    )
    session.commit()


def recipe_ids_with_embeddings(session: Session) -> set[int]:
    result = session.execute(text("SELECT recipe_id FROM recipe_embeddings"))
    return {row[0] for row in result}


def create_vec_table(session: Session) -> None:
    """Create the virtual table if it doesn't exist (for testing with in-memory DBs)."""
    dim = settings.embedding_dimension
    session.execute(
        text(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS recipe_embeddings "
            f"USING vec0(recipe_id INTEGER PRIMARY KEY, "
            f"embedding float[{dim}] distance_metric=cosine)"
        )
    )
    session.commit()
