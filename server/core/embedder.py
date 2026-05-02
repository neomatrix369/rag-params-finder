import voyageai

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_client: voyageai.Client | None = None


def get_client() -> voyageai.Client:
    """Get Voyage AI client singleton."""
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not set in .env or environment")
        _client = voyageai.Client(api_key=settings.voyage_api_key)
        logger.info("Voyage AI client initialized")
    return _client


def embed_documents(texts: list[str], model: str) -> list[list[float]]:
    """Embed documents using Voyage AI."""
    logger.info(f"Embedding {len(texts)} documents with model={model}")

    client = get_client()
    result = client.embed(texts, model=model, input_type="document")

    embeddings = result.embeddings
    logger.info(f"Generated {len(embeddings)} embeddings, dim={len(embeddings[0])}")

    return embeddings


def embed_query(text: str, model: str) -> list[float]:
    """Embed a single query using Voyage AI."""
    logger.info(f"Embedding query with model={model}")

    client = get_client()
    result = client.embed([text], model=model, input_type="query")

    embedding = result.embeddings[0]
    logger.info(f"Generated query embedding, dim={len(embedding)}")

    return embedding
