from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Fixed-size chunking (deferred to Slice 6).
    Placeholder implementation.
    """
    logger.warning("Fixed chunking not yet implemented")
    raise NotImplementedError("Fixed chunking will be implemented in Slice 6")
