import struct

import pytest

from src.config.settings import settings
from src.db.models import Recipe
from src.db.vec import (
    delete_embedding,
    insert_embedding,
    knn_search,
    recipe_ids_with_embeddings,
    serialize_float32,
)


def _make_recipe(session, title: str, url: str) -> Recipe:
    recipe = Recipe(title=title, url=url)
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


def _unit_vec(index: int, dim: int | None = None) -> list[float]:
    dim = dim or settings.embedding_dimension
    vec = [0.0] * dim
    vec[index % dim] = 1.0
    return vec


def test_serialize_float32_round_trip():
    vec = [1.0, 2.0, 3.0]
    b = serialize_float32(vec)
    unpacked = list(struct.unpack("3f", b))
    assert unpacked == pytest.approx(vec)


def test_insert_and_knn_search(db_session):
    r1 = _make_recipe(db_session, "Recipe A", "https://x.com/a")
    r2 = _make_recipe(db_session, "Recipe B", "https://x.com/b")

    insert_embedding(db_session, r1.id, _unit_vec(0))
    insert_embedding(db_session, r2.id, _unit_vec(1))

    results = knn_search(db_session, _unit_vec(0), k=2)
    assert len(results) == 2
    assert results[0][0] == r1.id
    assert results[0][1] < results[1][1]


def test_delete_embedding(db_session):
    r = _make_recipe(db_session, "Recipe X", "https://x.com/x")
    insert_embedding(db_session, r.id, _unit_vec(5))

    assert r.id in recipe_ids_with_embeddings(db_session)
    delete_embedding(db_session, r.id)
    assert r.id not in recipe_ids_with_embeddings(db_session)


def test_insert_replace(db_session):
    r = _make_recipe(db_session, "Recipe Y", "https://x.com/y")
    insert_embedding(db_session, r.id, _unit_vec(0))
    insert_embedding(db_session, r.id, _unit_vec(1))  # Should replace, not duplicate
    assert r.id in recipe_ids_with_embeddings(db_session)


def test_recipe_ids_with_embeddings(db_session):
    r1 = _make_recipe(db_session, "E1", "https://x.com/e1")
    r2 = _make_recipe(db_session, "E2", "https://x.com/e2")
    insert_embedding(db_session, r1.id, _unit_vec(0))

    ids = recipe_ids_with_embeddings(db_session)
    assert r1.id in ids
    assert r2.id not in ids
