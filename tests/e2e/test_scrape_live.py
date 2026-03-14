"""End-to-end tests against the live BBC Good Food website. Run with:
    pytest tests/e2e/ -m e2e
"""

import asyncio

import pytest

from src.scraper.browser import fetch_html, get_page
from src.scraper.parsers import parse_collection_page, parse_recipe_page

RECIPE_URL = "https://www.bbcgoodfood.com/recipes/ultimate-spaghetti-carbonara-recipe"
COLLECTION_URL = "https://www.bbcgoodfood.com/recipes/collection/chicken-recipes"


@pytest.mark.e2e
def test_scrape_single_recipe():
    async def run():
        async with get_page() as page:
            html = await fetch_html(page, RECIPE_URL)
        return parse_recipe_page(html, RECIPE_URL)

    recipe = asyncio.run(run())
    assert recipe is not None
    assert recipe.title
    assert recipe.description
    assert len(recipe.ingredients) > 0
    assert recipe.method


@pytest.mark.e2e
def test_scrape_collection_page():
    async def run():
        async with get_page() as page:
            html = await fetch_html(page, COLLECTION_URL)
        return parse_collection_page(html)

    urls = asyncio.run(run())
    assert len(urls) >= 5
    assert all(u.startswith("https://www.bbcgoodfood.com/recipes/") for u in urls)
