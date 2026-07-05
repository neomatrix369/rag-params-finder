from server.models.enums import ChunkingMethod
from server.utils.logger import get_logger

logger = get_logger(__name__)


def _apply_padding(chunks: list[str], padding: int) -> list[str]:
    """Merge undersized chunks forward to guarantee a minimum chunk length.

    Padding enforces a minimum chunk character length: any chunk shorter than
    `padding` is merged with the following chunk(s) until it reaches the
    threshold. This avoids low-signal fragment chunks (e.g. a trailing partial
    sentence) that embed poorly. A final undersized chunk with nothing after it
    is left as-is. `padding <= 0` is a no-op and returns chunks unchanged.

    Method-agnostic by design: applied uniformly after every chunker so padding
    means the same thing across fixed/recursive/token/sentence/semantic.
    """
    if padding <= 0 or len(chunks) <= 1:
        return chunks

    merged: list[str] = []
    buffer = ""
    for chunk in chunks:
        buffer = f"{buffer} {chunk}".strip() if buffer else chunk
        if len(buffer) >= padding:
            merged.append(buffer)
            buffer = ""
    if buffer:
        # Trailing remainder below threshold — attach to the last chunk if one
        # exists, otherwise keep it as the sole chunk.
        if merged:
            merged[-1] = f"{merged[-1]} {buffer}".strip()
        else:
            merged.append(buffer)
    return merged


def chunk_text(
    text: str,
    method: ChunkingMethod,
    chunk_size: int = 512,
    overlap: int = 50,
    padding: int = 0,
) -> list[str]:
    """Dispatch to appropriate chunking method, then apply padding post-processing."""

    logger.info(
        "chunk dispatch — chars=%s method=%s size=%s overlap=%s padding=%s",
        len(text),
        method.value,
        chunk_size,
        overlap,
        padding,
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

    chunks = _apply_padding(chunks, padding)

    logger.info("chunk dispatch OK — %s chunks produced", len(chunks))
    return chunks
