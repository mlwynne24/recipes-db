import pytest
from sqlmodel import select

from src.db.models import Ingredient, Recipe
from src.scraper.parsers import ScrapedIngredient, ScrapedRecipe
from src.scraper.scrape import upsert_recipe


@pytest.fixture
def sample_scraped():
    return ScrapedRecipe(
        url="https://www.bbcgoodfood.com/recipes/test-recipe",
        title="Test Recipe",
        description="A test recipe description.",
        method="Step 1. Do this.",
        tags=["quick", "vegetarian"],
        prep_time="10 mins",
        cook_time="20 mins",
        serves="4",
        ingredients=[
            ScrapedIngredient(original_text="200g pasta", name="pasta", quantity="200", unit="g"),
            ScrapedIngredient(original_text="2 eggs", name="egg", quantity="2"),
        ],
    )


def test_upsert_inserts_new_recipe(db_session, sample_scraped):
    recipe = upsert_recipe(db_session, sample_scraped)
    assert recipe.id is not None
    assert recipe.title == "Test Recipe"
    assert recipe.tag_list == ["quick", "vegetarian"]

    ingredients = db_session.exec(select(Ingredient).where(Ingredient.recipe_id == recipe.id)).all()
    assert len(ingredients) == 2
    names = {i.name for i in ingredients}
    assert "pasta" in names
    assert "egg" in names


def test_upsert_updates_existing_recipe(db_session, sample_scraped):
    recipe1 = upsert_recipe(db_session, sample_scraped)

    sample_scraped.title = "Updated Recipe"
    sample_scraped.ingredients = [
        ScrapedIngredient(original_text="300g pasta", name="pasta", quantity="300", unit="g"),
    ]
    recipe2 = upsert_recipe(db_session, sample_scraped)

    assert recipe2.id == recipe1.id
    assert recipe2.title == "Updated Recipe"

    ingredients = db_session.exec(
        select(Ingredient).where(Ingredient.recipe_id == recipe2.id)
    ).all()
    assert len(ingredients) == 1
    assert ingredients[0].quantity == "300"


def test_no_duplicate_on_same_url(db_session, sample_scraped):
    upsert_recipe(db_session, sample_scraped)
    upsert_recipe(db_session, sample_scraped)
    recipes = db_session.exec(select(Recipe)).all()
    assert len(recipes) == 1


def test_tag_list_property(db_session, sample_scraped):
    recipe = upsert_recipe(db_session, sample_scraped)
    assert recipe.tag_list == ["quick", "vegetarian"]
    recipe.tag_list = ["new", "tags"]
    assert recipe.tag_list == ["new", "tags"]
