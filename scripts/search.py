"""CLI for semantic + SQL recipe search."""

import argparse

from sqlmodel import Session

from src.db.engine import engine
from src.search.query import hybrid_search, sql_search


def main() -> None:
    parser = argparse.ArgumentParser(description="Search recipes")
    parser.add_argument("query", nargs="?", help="Semantic search query")
    parser.add_argument("--ingredient", help="Filter by ingredient name")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--k", type=int, default=10, help="Number of results")
    parser.add_argument("--sql-only", action="store_true", help="Skip vector search")
    args = parser.parse_args()

    with Session(engine) as session:
        if args.sql_only or not args.query:
            recipes = sql_search(
                session, ingredient_filter=args.ingredient, tag_filter=args.tag, limit=args.k
            )
            for r in recipes:
                print(f"{r.title}")
                print(f"  {r.url}")
                if r.description:
                    print(f"  {r.description[:120]}...")
                print()
        else:
            results = hybrid_search(
                session,
                query_text=args.query,
                ingredient_filter=args.ingredient,
                tag_filter=args.tag,
                k=args.k,
            )
            if not results:
                print("No results found.")
                return
            for sr in results:
                r = sr.recipe
                print(f"[{sr.distance:.4f}] {r.title}")
                print(f"  {r.url}")
                if r.description:
                    print(f"  {r.description[:120]}...")
                if sr.ingredients:
                    top_ingredients = ", ".join(i.name for i in sr.ingredients[:5])
                    print(f"  Ingredients: {top_ingredients}")
                print()


if __name__ == "__main__":
    main()
