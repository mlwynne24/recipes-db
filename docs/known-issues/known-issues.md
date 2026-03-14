# Known Issues

## sqlite-vec: wrong binary on Raspberry Pi (piwheels)

**Status:** Worked around
**Affects:** All Raspberry Pi / aarch64 Linux installs

`sqlite-vec 0.1.6` on piwheels ships a 32-bit ARM (`ELFCLASS32`) shared library inside the `manylinux_aarch64` wheel. Loading it on a 64-bit Python raises:

```
sqlite3.OperationalError: vec0.so: wrong ELF class: ELFCLASS32
```

**Workaround:** Pinned to `sqlite-vec>=0.1.7a10` with `[tool.uv.sources] sqlite-vec = { index = "pypi" }` in `pyproject.toml`, which forces the correct 64-bit binary from PyPI rather than piwheels.

**Upstream:** The 0.1.6 wheel packaging bug should be fixed in future stable releases.

---

## sqlite-vec: `vec0` virtual tables don't support `INSERT OR REPLACE`

**Status:** Fixed
**Affects:** `src/db/vec.py`

`INSERT OR REPLACE INTO recipe_embeddings ...` raises `UNIQUE constraint failed on recipe_embeddings primary key` even though the primary key already exists (i.e. the REPLACE branch never executes).

**Fix:** Use `DELETE` then `INSERT`:
```python
session.execute(text("DELETE FROM recipe_embeddings WHERE recipe_id = :id"), {"id": recipe_id})
session.execute(text("INSERT INTO recipe_embeddings ..."), {...})
```

---

## SQLAlchemy: string type annotation `"Recipe | None"` not resolvable

**Status:** Fixed
**Affects:** `src/db/models.py` `Ingredient.recipe` relationship

Using a quoted string annotation `"Recipe | None"` on a SQLModel `Relationship` fails at mapper configuration time because SQLAlchemy tries to `eval()` the string in the module scope and `Recipe | None` (as a string) doesn't resolve.

**Fix:** Use the unquoted form `Recipe | None` — since `Recipe` is defined before `Ingredient` in the same file, no forward reference is needed.

---

## BBC Good Food: Sourcepoint consent popup (Playwright only)

**Status:** Handled
**Affects:** Playwright-based scraping only

BBC Good Food uses Sourcepoint (CMP account 1742) for GDPR consent. The modal is **fully JS-rendered** and only appears in browser sessions — `requests`/`httpx` scraping is unaffected.

When using Playwright, the consent button must be clicked before content is usable. The correct selector is `button[title="Accept all"]` (Sourcepoint standard).

**Note:** Static HTTP scraping (no browser) is preferred where possible — it avoids the consent modal entirely and is faster.

---

## BBC Good Food: collection pages have no pagination

**Status:** Known behaviour
**Affects:** `parse_collection_page`, `scrape_collection`

Collection pages (e.g. `/recipes/collection/chicken-recipes`) serve all ~64 recipes at once on a single page — there is no "next page" link.

For exhaustive crawling across many recipes, use the search API: `/search?q={term}&page={n}`. The `__NEXT_DATA__` blob on search results pages contains `totalItems` and `limit` (30 per page) to compute total pages.

---

## pydantic-settings: `voyage_api_key` defaults to empty string

**Status:** By design
**Affects:** `src/config/settings.py`

`voyage_api_key` has a default of `""` (empty string) rather than being required. This allows `alembic upgrade head` and other non-embedding operations to run without a `.env` file.

A `RuntimeError` is raised only when `src/embeddings/voyage.py::get_client()` is actually called with an empty key.

**Action required:** Set `VOYAGE_API_KEY=<your-key>` in `.env` before running `scripts/embed.py` or `scripts/search.py`.
