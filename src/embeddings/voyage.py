import voyageai

from src.config.settings import settings

_client: voyageai.Client | None = None


def get_client() -> voyageai.Client:
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            raise RuntimeError("VOYAGE_API_KEY is not set in .env")
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents (e.g. recipe descriptions)."""
    result = get_client().embed(
        texts,
        model=settings.voyage_model,
        input_type="document",
        output_dimension=settings.embedding_dimension,
    )
    return result.embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    result = get_client().embed(
        [text],
        model=settings.voyage_model,
        input_type="query",
        output_dimension=settings.embedding_dimension,
    )
    return result.embeddings[0]
