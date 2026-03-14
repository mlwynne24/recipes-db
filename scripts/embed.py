"""CLI to backfill VoyageAI embeddings for un-embedded recipes."""

import argparse
import logging

from sqlmodel import Session, select

from src.db.engine import engine
from src.db.models import Recipe
from src.db.vec import insert_embedding, recipe_ids_with_embeddings
from src.embeddings.voyage import embed_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_MAX_BATCH = 128  # VoyageAI limit per call


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embeddings for recipes")
    parser.add_argument("--batch-size", type=int, default=_MAX_BATCH)
    args = parser.parse_args()

    with Session(engine) as session:
        embedded_ids = recipe_ids_with_embeddings(session)
        all_recipes = session.exec(select(Recipe)).all()
        pending = [r for r in all_recipes if r.id not in embedded_ids and r.description]

        if not pending:
            logger.info("No recipes need embedding.")
            return

        logger.info("%d recipes to embed", len(pending))
        batch_size = min(args.batch_size, _MAX_BATCH)

        for i in range(0, len(pending), batch_size):
            batch = pending[i : i + batch_size]
            texts = [r.description for r in batch]
            embeddings = embed_documents(texts)
            for recipe, embedding in zip(batch, embeddings):
                insert_embedding(session, recipe.id, embedding)
            logger.info("Embedded %d/%d", min(i + batch_size, len(pending)), len(pending))

    logger.info("Done.")


if __name__ == "__main__":
    main()
