from server.utils.logger import get_logger

logger = get_logger(__name__)

_NLTK_READY = False


def _ensure_nltk() -> None:
    global _NLTK_READY
    if _NLTK_READY:
        return
    import nltk  # type: ignore[import-untyped]

    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    _NLTK_READY = True


def chunk_sentence(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Sentence-aware chunking with character-budget grouping.

    Groups sentences greedily until chunk_size characters are reached, then
    starts a new chunk.  The overlap is expressed in characters: the tail of
    the previous chunk (up to `overlap` chars) is prepended to the next chunk
    to preserve cross-boundary context.
    """
    _ensure_nltk()
    from nltk.tokenize import sent_tokenize  # type: ignore[import-untyped]

    sentences = sent_tokenize(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence would exceed the budget, flush the current chunk.
        if current_sentences and current_len + sentence_len > chunk_size:
            chunk_text = " ".join(current_sentences)
            chunks.append(chunk_text)

            # Build overlap: take the tail of the flushed chunk up to `overlap` chars.
            if overlap > 0:
                overlap_text = chunk_text[-overlap:]
                current_sentences = [overlap_text]
                current_len = len(overlap_text)
            else:
                current_sentences = []
                current_len = 0

        current_sentences.append(sentence)
        current_len += sentence_len + 1  # +1 for the joining space

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks
