from pathlib import Path

import pytest
import sqlite_vec
from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine

from src.config.settings import settings
from src.db import models  # noqa: F401 — register models with SQLModel metadata


def _make_test_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def load_ext(dbapi_conn, _):
        sqlite_vec.load(dbapi_conn)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        dim = settings.embedding_dimension
        session.execute(
            text(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS recipe_embeddings "
                f"USING vec0(recipe_id INTEGER PRIMARY KEY, "
                f"embedding float[{dim}] distance_metric=cosine)"
            )
        )
        session.commit()

    return engine


@pytest.fixture
def db_session():
    engine = _make_test_engine()
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_recipe_html():
    fixture = Path(__file__).parent / "fixtures" / "recipe_page.html"
    if fixture.exists():
        return fixture.read_text()
    # Minimal inline fallback with JSON-LD
    return """
    <html><head>
    <script type="application/ld+json">
    {"@type":"Recipe","name":"Spaghetti Carbonara","description":"A classic Roman pasta dish.",
    "recipeIngredient":["200g spaghetti","2 large eggs","100g pancetta"],
    "recipeInstructions":[{"@type":"HowToStep","text":"Cook pasta."},{"@type":"HowToStep","text":"Fry pancetta."}],
    "prepTime":"PT10M","cookTime":"PT20M","recipeYield":"2 servings","keywords":"pasta,italian"}
    </script>
    </head><body><h1>Spaghetti Carbonara</h1></body></html>
    """


@pytest.fixture
def sample_collection_html():
    fixture = Path(__file__).parent / "fixtures" / "collection_page.html"
    if fixture.exists():
        return fixture.read_text()
    return """
    <html><body>
    <a href="/recipes/spaghetti-carbonara">Carbonara</a>
    <a href="/recipes/chicken-tikka-masala">Chicken Tikka</a>
    <a href="/recipes/collection/italian">Italian collection</a>
    </body></html>
    """
