# recipes-db

A BBC Good Food recipe scraper and semantic search system. Scrapes recipes using Playwright, stores them in SQLite, generates embeddings via VoyageAI, and supports hybrid semantic + SQL search.

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Install Playwright browsers

```bash
uv run playwright install chromium
```

### 3. Configure environment

Create a `.env` file in the project root:

```bash
DATABASE_PATH=data/recipes.db
VOYAGE_API_KEY=your-key-here
```

All other settings have sensible defaults. See `src/config/settings.py` for the full list.

### 4. Run database migrations

```bash
alembic upgrade head
```

## CLI Commands

### Scrape recipes

Scrape a single recipe:

```bash
uv run scripts/scrape.py --url <recipe-url>
```

Scrape all recipes in a collection (paginated):

```bash
uv run scripts/scrape.py --collection <collection-url> [--max-pages N]
```

### Generate embeddings

Backfill embeddings for any recipes not yet embedded (requires `VOYAGE_API_KEY`):

```bash
uv run scripts/embed.py [--batch-size N]
```

### Search recipes

Semantic search:

```bash
uv run scripts/search.py "quick pasta dishes" [--k 10]
```

Filter by ingredient and/or tag:

```bash
uv run scripts/search.py "comfort food" --ingredient chicken --tag "dinner"
```

SQL-only (no embeddings required):

```bash
uv run scripts/search.py --ingredient salmon --sql-only
```

## Configuration

| Setting | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `data/recipes.db` | SQLite database location |
| `VOYAGE_API_KEY` | *(empty)* | VoyageAI API key — required for embedding and search |
| `VOYAGE_MODEL` | `voyage-3.5-lite` | Embedding model |
| `EMBEDDING_DIMENSION` | `1024` | Embedding vector size |
| `SCRAPE_DELAY_SECONDS` | `1.5` | Delay between page requests |
| `HEADLESS` | `true` | Run Playwright in headless mode |
| `DEFAULT_SEARCH_K` | `10` | Default number of search results |
| `BROAD_SEARCH_K` | `200` | KNN candidate pool size before SQL filtering |

## Running tests

```bash
uv run pytest                    # Unit tests only
uv run pytest -m e2e             # End-to-end tests (hits live BBC site)
```

## Architecture

```
scripts/        CLI entry points (scrape, embed, search)
src/
  config/       Pydantic settings
  db/           SQLModel models, engine, sqlite-vec KNN
  embeddings/   VoyageAI client
  scraper/      Playwright browser, HTML parsers, scraping logic
  search/       Hybrid search (vector + SQL)
alembic/        Database migrations
docs/           Development notes, known issues, plans
```

Recipes are stored relationally (`recipes` + `ingredients` tables). Embeddings live in a `recipe_embeddings` sqlite-vec virtual table (cosine distance). Hybrid search runs a broad KNN pass then applies SQL filters to the candidates.
