from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_path: str = "data/recipes.db"

    voyage_api_key: str = ""
    voyage_model: str = "voyage-3.5-lite"
    embedding_dimension: int = 1024

    scrape_delay_seconds: float = 1.5
    scrape_batch_size: int = 50
    headless: bool = True

    default_search_k: int = 10
    broad_search_k: int = 200


settings = Settings()
