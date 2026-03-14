from unittest.mock import patch

import pytest

from src.db.models import Recipe
from src.db.vec import insert_embedding
from src.scraper.parsers import ScrapedIngredient, ScrapedRecipe
from src.scraper.scrape import upsert_recipe
from src.search.query import SearchResult, hybrid_search, sql_search


def _seed_recipe(session, title, url, tags=None, ingredients=None, vec_index=0) -> Recipe:
    dim = 1024
    scraped = ScrapedRecipe(
        url=url,
        title=title,
        description=f"Description of {title}",
        tags=tags or [],
        ingredients=ingredients or [],
    )
    recipe = upsert_recipe(session, scraped)
    vec = [0.0] * dim
    vec[vec_index] = 1.0
    insert_embedding(session, recipe.id, vec)
    return recipe


@pytest.fixture
def seeded_db(db_session):
    _seed_recipe(
        db_session, "Zesty Lemon Chicken", "https://x.com/1",
        tags=["dinner", "chicken"],
        ingredients=[
            ScrapedIngredient("1 chicken breast", "chicken breast", "1"),
            ScrapedIngredient("1 lemon", "lemon", "1"),
        ],
        vec_index=0,
    )
    _seed_recipe(
        db_session, "Beef Stew", "https://x.com/2",
        tags=["dinner", "beef"],
        ingredients=[
            ScrapedIngredient("500g beef", "beef", "500", "g"),
        ],
        vec_index=1,
    )
    _seed_recipe(
        db_session, "Pasta Carbonara", "https://x.com/3",
        tags=["pasta", "quick"],
        ingredients=[
            ScrapedIngredient("200g pasta", "pasta", "200", "g"),
            ScrapedIngredient("2 eggs", "egg", "2"),
        ],
        vec_index=2,
    )
    return db_session


def _mock_query_vec(index: int):
    vec = [0.0] * 1024
    vec[index] = 1.0
    return vec


def test_hybrid_search_no_filters(seeded_db):
    with patch("src.search.query.embed_query", return_value=_mock_query_vec(0)):
        results = hybrid_search(seeded_db, "lemon chicken", k=3)
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].recipe.title == "Zesty Lemon Chicken"


def test_hybrid_search_ingredient_filter(seeded_db):
    with patch("src.search.query.embed_query", return_value=_mock_query_vec(0)):
        results = hybrid_search(seeded_db, "dinner recipe", ingredient_filter="chicken", k=5)
    titles = [r.recipe.title for r in results]
    assert all("Chicken" in t for t in titles)
    assert "Beef Stew" not in titles
    assert "Pasta Carbonara" not in titles


def test_hybrid_search_tag_filter(seeded_db):
    with patch("src.search.query.embed_query", return_value=_mock_query_vec(2)):
        results = hybrid_search(seeded_db, "quick meal", tag_filter="quick", k=5)
    titles = [r.recipe.title for r in results]
    assert "Pasta Carbonara" in titles
    assert "Beef Stew" not in titles


def test_hybrid_search_returns_ingredients(seeded_db):
    with patch("src.search.query.embed_query", return_value=_mock_query_vec(0)):
        results = hybrid_search(seeded_db, "chicken", k=1)
    assert results[0].ingredients


def test_sql_search_ingredient_filter(seeded_db):
    recipes = sql_search(seeded_db, ingredient_filter="egg")
    titles = [r.title for r in recipes]
    assert "Pasta Carbonara" in titles
    assert "Beef Stew" not in titles


def test_sql_search_tag_filter(seeded_db):
    recipes = sql_search(seeded_db, tag_filter="dinner")
    titles = [r.title for r in recipes]
    assert "Zesty Lemon Chicken" in titles
    assert "Beef Stew" in titles
    assert "Pasta Carbonara" not in titles


def test_sql_search_combined(seeded_db):
    recipes = sql_search(seeded_db, ingredient_filter="lemon", tag_filter="dinner")
    titles = [r.title for r in recipes]
    assert "Zesty Lemon Chicken" in titles
    assert "Beef Stew" not in titles


def test_hybrid_search_empty_results(db_session):
    with patch("src.search.query.embed_query", return_value=_mock_query_vec(0)):
        results = hybrid_search(db_session, "nothing here")
    assert results == []
