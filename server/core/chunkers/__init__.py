from server.models.enums import ChunkingMethod
from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str, method: ChunkingMethod, chunk_size: int = 512, overlap: int = 50
) -> list[str]:
    """Dispatch to appropriate chunking method."""

    logger.info(
        "chunk dispatch — chars=%s method=%s size=%s overlap=%s",
        len(text),
        method.value,
        chunk_size,
        overlap,
    )

    if method == ChunkingMethod.RECURSIVE:
        from server.core.chunkers.recursive import chunk_recursive

        chunks = chunk_recursive(text, chunk_size, overlap)
    elif method == ChunkingMethod.FIXED:
        from server.core.chunkers.fixed import chunk_fixed

        chunks = chunk_fixed(text, chunk_size, overlap)
    elif method == ChunkingMethod.TOKEN:
        from server.core.chunkers.token import chunk_token

        chunks = chunk_token(text, chunk_size, overlap)
    elif method == ChunkingMethod.SENTENCE:
        from server.core.chunkers.sentence import chunk_sentence

        chunks = chunk_sentence(text, chunk_size, overlap)
    elif method == ChunkingMethod.SEMANTIC:
        from server.core.chunkers.semantic import chunk_semantic

        chunks = chunk_semantic(text, chunk_size, overlap)
    else:
        raise ValueError(f"Unknown chunking method: {method}")

    logger.info("chunk dispatch OK — %s chunks produced", len(chunks))
    return chunks
