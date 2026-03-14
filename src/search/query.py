from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session, select

from src.config.settings import settings
from src.db.models import Ingredient, Recipe
from src.db.vec import knn_search, serialize_float32
from src.embeddings.voyage import embed_query


@dataclass
class SearchResult:
    recipe: Recipe
    distance: float
    ingredients: list[Ingredient]


def hybrid_search(
    session: Session,
    query_text: str,
    ingredient_filter: str | None = None,
    tag_filter: str | None = None,
    k: int | None = None,
) -> list[SearchResult]:
    """Embed query, run broad KNN, then apply SQL filters and return top-k."""
    k = k or settings.default_search_k
    broad_k = settings.broad_search_k

    query_vec = embed_query(query_text)
    candidates = knn_search(session, query_vec, broad_k)

    if not candidates:
        return []

    # Build filtered result from candidates
    candidate_map = {recipe_id: dist for recipe_id, dist in candidates}

    # Build SQL to filter candidates
    placeholders = ",".join(str(rid) for rid in candidate_map)
    conditions = [f"r.id IN ({placeholders})"]
    params: dict = {}

    if ingredient_filter:
        conditions.append("EXISTS (SELECT 1 FROM ingredients i WHERE i.recipe_id = r.id AND i.name LIKE :ingredient)")
        params["ingredient"] = f"%{ingredient_filter.lower()}%"

    if tag_filter:
        conditions.append("r.tags LIKE :tag")
        params["tag"] = f"%{tag_filter}%"

    where_clause = " AND ".join(conditions)
    sql = text(f"SELECT id FROM recipes r WHERE {where_clause}")  # noqa: S608

    rows = session.execute(sql, params).fetchall()
    filtered_ids = {row[0] for row in rows}

    results = []
    for recipe_id, distance in sorted(candidates, key=lambda x: x[1]):
        if recipe_id not in filtered_ids:
            continue
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            continue
        ingredients = list(session.exec(select(Ingredient).where(Ingredient.recipe_id == recipe_id)).all())
        results.append(SearchResult(recipe=recipe, distance=distance, ingredients=ingredients))
        if len(results) >= k:
            break

    return results


def sql_search(
    session: Session,
    ingredient_filter: str | None = None,
    tag_filter: str | None = None,
    limit: int = 20,
) -> list[Recipe]:
    """Pure SQL search without vector ranking."""
    conditions = []
    params: dict = {}

    if ingredient_filter:
        conditions.append(
            "EXISTS (SELECT 1 FROM ingredients i WHERE i.recipe_id = r.id AND i.name LIKE :ingredient)"
        )
        params["ingredient"] = f"%{ingredient_filter.lower()}%"

    if tag_filter:
        conditions.append("r.tags LIKE :tag")
        params["tag"] = f"%{tag_filter}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = text(f"SELECT id FROM recipes r {where_clause} LIMIT :limit")  # noqa: S608
    params["limit"] = limit

    rows = session.execute(sql, params).fetchall()
    return [session.get(Recipe, row[0]) for row in rows if session.get(Recipe, row[0])]
