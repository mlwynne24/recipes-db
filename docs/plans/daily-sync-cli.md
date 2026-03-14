# Plan: Daily Recipe Sync CLI

## Context
The user wants a CLI (`scripts/sync.py`) runnable via a daily CRON job that discovers new/updated BBC Good Food recipes and stores them in the database. The solution must be free — no paid discovery services.

**Discovery mechanism**: BBC Good Food publishes public quarterly sitemap XMLs at:
`https://www.bbcgoodfood.com/sitemaps/{YEAR}-Q{Q}-recipe.xml`
Each entry has a `<loc>` (recipe URL) and `<lastmod>` (ISO timestamp). This is perfect for efficient daily syncing — check the current quarter's sitemap, compare against `scraped_at` in the DB, and only scrape what's new or updated. No cost, no API needed.

Note: `/premium/` URLs require a paid subscription and must be filtered out.

## New files

### `src/scraper/sitemap.py` (~60 lines)
Parses quarterly recipe sitemaps using stdlib only (`urllib.request` + `xml.etree.ElementTree`).

```
def current_quarter_sitemap_url() -> str
    → "https://www.bbcgoodfood.com/sitemaps/2026-Q1-recipe.xml"

def fetch_sitemap_entries(sitemap_url: str) -> list[tuple[str, datetime]]
    → [(url, lastmod), ...] — filters out /premium/ URLs
```

### `scripts/sync.py` (~100 lines)
Daily sync CLI. Reuses existing functions from the codebase:
- `src.scraper.scrape.scrape_url()` — scrapes individual recipe pages
- `src.db.engine.engine` — DB connection
- `src.db.models.Recipe` — model to query existing URLs + `scraped_at`
- `src.db.vec.recipe_ids_with_embeddings` + `src.embeddings.voyage.embed_documents` + `src.db.vec.insert_embedding` — for optional embed step

**Args:**
- `--lookback-quarters N` (default 1): check N previous quarters too (useful for first-time setup or catching quarter boundaries)
- `--embed` flag: run embedding for newly scraped recipes after sync (off by default since Voyage API key may not always be set)
- `--dry-run` flag: print what would be scraped without actually scraping

**Logic:**
1. Build list of sitemap URLs for current quarter + any lookback quarters
2. Fetch + parse each sitemap → `(url, lastmod)` list
3. Query DB: map `{url → scraped_at}` for all existing recipes
4. Classify each sitemap entry:
   - **new**: URL not in DB → scrape
   - **updated**: `lastmod > scraped_at` → scrape
   - **current**: `lastmod <= scraped_at` → skip
5. Scrape all new/updated with existing `scrape_url()` (respects `settings.scrape_delay_seconds`)
6. If `--embed`: embed newly scraped recipes using existing embed logic
7. Print summary: N new, N updated, N skipped, N failed

## Files to modify
None — purely additive.

## Verification
```bash
# Dry run to see what would be scraped today
uv run python scripts/sync.py --dry-run

# Normal daily sync (no embeddings)
uv run python scripts/sync.py

# Full sync with embeddings
uv run python scripts/sync.py --embed

# First-time backfill (check last 2 quarters)
uv run python scripts/sync.py --lookback-quarters 2 --embed
```
