from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character-window slicing with configurable overlap.

    Each chunk is exactly chunk_size characters (or less for the final chunk).
    The window advances by (chunk_size - overlap) characters each step.
    """
    step = max(1, chunk_size - overlap)
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), step)]
    # Drop any empty tails (can happen when text length is a multiple of step)
    return [c for c in chunks if c]
