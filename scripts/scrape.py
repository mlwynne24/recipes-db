"""CLI for scraping BBC Good Food recipes."""

import argparse
import asyncio
import logging

from sqlmodel import Session

from src.db.engine import engine
from src.scraper.scrape import scrape_collection, scrape_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape BBC Good Food recipes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Scrape a single recipe URL")
    group.add_argument("--collection", help="Scrape all recipes from a collection URL")
    parser.add_argument("--max-pages", type=int, default=50, help="Max collection pages to fetch")
    args = parser.parse_args()

    with Session(engine) as session:
        if args.url:
            recipe = asyncio.run(scrape_url(args.url, session))
            if recipe:
                print(f"Saved: {recipe.title}")
        else:
            recipes = asyncio.run(scrape_collection(args.collection, session, args.max_pages))
            print(f"Saved {len(recipes)} recipes")


if __name__ == "__main__":
    main()
