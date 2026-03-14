import asyncio
import logging

from sqlmodel import Session, select

from src.config.settings import settings
from src.db.models import Ingredient, Recipe
from src.scraper.browser import fetch_html, get_page
from src.scraper.parsers import (
    ScrapedRecipe,
    parse_collection_page,
    parse_next_page,
    parse_recipe_page,
)

logger = logging.getLogger(__name__)


def upsert_recipe(session: Session, scraped: ScrapedRecipe) -> Recipe:
    """Insert or update a recipe by URL. Replaces ingredients on update."""
    existing = session.exec(select(Recipe).where(Recipe.url == scraped.url)).first()

    if existing:
        recipe = existing
        recipe.title = scraped.title
        recipe.description = scraped.description
        recipe.method = scraped.method
        recipe.tag_list = scraped.tags
        recipe.prep_time = scraped.prep_time
        recipe.cook_time = scraped.cook_time
        recipe.serves = scraped.serves
        # Replace ingredients
        for ing in session.exec(select(Ingredient).where(Ingredient.recipe_id == recipe.id)).all():
            session.delete(ing)
    else:
        recipe = Recipe(
            url=scraped.url,
            title=scraped.title,
            description=scraped.description,
            method=scraped.method,
            tags=None,
            prep_time=scraped.prep_time,
            cook_time=scraped.cook_time,
            serves=scraped.serves,
        )
        recipe.tag_list = scraped.tags
        session.add(recipe)

    session.flush()

    for si in scraped.ingredients:
        session.add(Ingredient(
            recipe_id=recipe.id,
            name=si.name,
            quantity=si.quantity,
            unit=si.unit,
            original_text=si.original_text,
        ))

    session.commit()
    session.refresh(recipe)
    return recipe


async def scrape_url(url: str, session: Session) -> Recipe | None:
    async with get_page() as page:
        html = await fetch_html(page, url)

    scraped = parse_recipe_page(html, url)
    if not scraped:
        logger.warning("Could not parse recipe at %s", url)
        return None

    recipe = upsert_recipe(session, scraped)
    logger.info("Saved: %s", recipe.title)
    return recipe


async def scrape_collection(
    collection_url: str, session: Session, max_pages: int = 50
) -> list[Recipe]:
    """Paginate through a collection URL, scraping all recipes found."""
    recipe_urls: list[str] = []
    page_url: str | None = collection_url
    pages_fetched = 0

    async with get_page() as page:
        while page_url and pages_fetched < max_pages:
            logger.info("Fetching collection page: %s", page_url)
            html = await fetch_html(page, page_url)
            new_urls = parse_collection_page(html)
            recipe_urls.extend(u for u in new_urls if u not in recipe_urls)
            page_url = parse_next_page(html)
            pages_fetched += 1
            if page_url:
                await asyncio.sleep(settings.scrape_delay_seconds)

    logger.info("Found %d recipe URLs across %d pages", len(recipe_urls), pages_fetched)

    recipes: list[Recipe] = []
    async with get_page() as page:
        for i, url in enumerate(recipe_urls):
            try:
                html = await fetch_html(page, url)
                scraped = parse_recipe_page(html, url)
                if scraped:
                    recipe = upsert_recipe(session, scraped)
                    recipes.append(recipe)
                    logger.info("[%d/%d] Saved: %s", i + 1, len(recipe_urls), recipe.title)
            except Exception as e:
                logger.error("Failed %s: %s", url, e)
            if i < len(recipe_urls) - 1:
                await asyncio.sleep(settings.scrape_delay_seconds)

    return recipes
