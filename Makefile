DB_PATH := data/recipes.db

db-shell:
	uv run python -m sqlite3 $(DB_PATH)
