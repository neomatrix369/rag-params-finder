from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_token(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Token-based chunking (deferred to Slice 6).
    Placeholder implementation.
    """
    logger.warning("Token chunking not yet implemented")
    raise NotImplementedError("Token chunking will be implemented in Slice 6")
