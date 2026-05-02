from server.models.enums import ChunkingMethod
from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str,
    method: ChunkingMethod,
    chunk_size: int = 512,
    overlap: int = 50
) -> list[str]:
    """Dispatch to appropriate chunking method."""

    logger.info(f"Chunking with method={method.value}, size={chunk_size}, overlap={overlap}")

    if method == ChunkingMethod.RECURSIVE:
        from server.core.chunkers.recursive import chunk_recursive
        return chunk_recursive(text, chunk_size, overlap)
    elif method == ChunkingMethod.FIXED:
        from server.core.chunkers.fixed import chunk_fixed
        return chunk_fixed(text, chunk_size, overlap)
    elif method == ChunkingMethod.TOKEN:
        from server.core.chunkers.token import chunk_token
        return chunk_token(text, chunk_size, overlap)
    elif method == ChunkingMethod.SENTENCE:
        from server.core.chunkers.sentence import chunk_sentence
        return chunk_sentence(text, chunk_size, overlap)
    elif method == ChunkingMethod.SEMANTIC:
        from server.core.chunkers.semantic import chunk_semantic
        return chunk_semantic(text, chunk_size)
    else:
        raise ValueError(f"Unknown chunking method: {method}")
