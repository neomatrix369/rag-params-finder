from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_sentence(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Sentence-based chunking (deferred to Slice 6).
    Placeholder implementation.
    """
    logger.warning("Sentence chunking not yet implemented")
    raise NotImplementedError("Sentence chunking will be implemented in Slice 6")
