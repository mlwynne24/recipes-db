"""Daily sync CLI — discover and scrape new/updated BBC Good Food recipes via sitemap."""
import argparse
import asyncio
import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from src.config.settings import settings
from src.db.engine import engine
from src.db.models import Recipe
from src.db.vec import insert_embedding, recipe_ids_with_embeddings
from src.embeddings.voyage import embed_documents
from src.scraper.scrape import scrape_url
from src.scraper.sitemap import fetch_sitemap_entries, sitemap_url_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _quarters_to_check(lookback: int) -> list[tuple[int, int]]:
    now = datetime.now(UTC)
    year, quarter = now.year, (now.month - 1) // 3 + 1
    quarters = [(year, quarter)]
    for _ in range(lookback):
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1
        quarters.append((year, quarter))
    return quarters


def _fetch_all_entries(lookback: int) -> list[tuple[str, datetime]]:
    entries: dict[str, datetime] = {}
    for year, quarter in _quarters_to_check(lookback):
        url = sitemap_url_for(year, quarter)
        logger.info("Fetching sitemap: %s", url)
        try:
            for loc, lastmod in fetch_sitemap_entries(url):
                if loc not in entries or lastmod > entries[loc]:
                    entries[loc] = lastmod
        except Exception as e:
            logger.warning("Could not fetch sitemap %s: %s", url, e)
    return list(entries.items())


def _classify(
    entries: list[tuple[str, datetime]],
    existing: dict[str, datetime],
) -> tuple[list[str], list[str], int]:
    to_scrape_new, to_scrape_updated = [], []
    skipped = 0
    for url, lastmod in entries:
        if url not in existing:
            to_scrape_new.append(url)
        elif lastmod > existing[url]:
            to_scrape_updated.append(url)
        else:
            skipped += 1
    return to_scrape_new, to_scrape_updated, skipped


async def _run_sync(urls: list[str], session: Session) -> tuple[int, int]:
    """Scrape a list of URLs, returning (succeeded, failed) counts."""
    succeeded, failed = 0, 0
    for i, url in enumerate(urls):
        try:
            recipe = await scrape_url(url, session)
            if recipe:
                recipe.scraped_at = datetime.now(UTC)
                session.add(recipe)
                session.commit()
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            logger.error("Failed %s: %s", url, e)
            failed += 1
        if i < len(urls) - 1:
            await asyncio.sleep(settings.scrape_delay_seconds)
    return succeeded, failed


def _embed_new(session: Session) -> None:
    embedded_ids = recipe_ids_with_embeddings(session)
    pending = session.exec(select(Recipe)).all()
    pending = [r for r in pending if r.id not in embedded_ids and r.description]
    if not pending:
        logger.info("No recipes need embedding.")
        return
    logger.info("Embedding %d recipes", len(pending))
    batch_size = 128
    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        embeddings = embed_documents([r.description for r in batch])
        for recipe, embedding in zip(batch, embeddings):
            insert_embedding(session, recipe.id, embedding)
        logger.info("Embedded %d/%d", min(i + batch_size, len(pending)), len(pending))


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily sync of BBC Good Food recipes via sitemap")
    parser.add_argument(
        "--lookback-quarters",
        type=int,
        default=1,
        metavar="N",
        help="Check N previous quarters in addition to current (default: 1)",
    )
    parser.add_argument("--embed", action="store_true", help="Embed newly scraped recipes")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be scraped")
    args = parser.parse_args()

    entries = _fetch_all_entries(args.lookback_quarters)
    logger.info("Found %d sitemap entries", len(entries))

    with Session(engine) as session:
        rows = session.exec(select(Recipe)).all()
        existing: dict[str, datetime] = {
            r.url: r.scraped_at.replace(tzinfo=UTC) if r.scraped_at.tzinfo is None else r.scraped_at
            for r in rows
        }

    new_urls, updated_urls, skipped = _classify(entries, existing)
    all_to_scrape = new_urls + updated_urls

    logger.info(
        "Classification — new: %d, updated: %d, skipped: %d",
        len(new_urls),
        len(updated_urls),
        skipped,
    )

    if args.dry_run:
        for url in new_urls:
            print(f"[NEW]     {url}")
        for url in updated_urls:
            print(f"[UPDATED] {url}")
        print(f"\nDry run: {len(new_urls)} new, {len(updated_urls)} updated, {skipped} skipped")
        return

    if not all_to_scrape:
        logger.info("Nothing to scrape.")
        return

    with Session(engine) as session:
        succeeded, failed = asyncio.run(_run_sync(all_to_scrape, session))
        if args.embed:
            _embed_new(session)

    print(
        f"\nSync complete — new: {len(new_urls)}, updated: {len(updated_urls)}, "
        f"skipped: {skipped}, failed: {failed}"
    )


if __name__ == "__main__":
    main()
