from server.utils.logger import get_logger

logger = get_logger(__name__)

_SIMILARITY_THRESHOLD = 0.6
_MODEL_NAME = "all-MiniLM-L6-v2"


def chunk_semantic(text: str, chunk_size: int) -> list[str]:
    """Semantic chunking using sentence-level cosine similarity.

    Splits text into sentences, embeds each one with all-MiniLM-L6-v2, then
    groups consecutive sentences into chunks when the cosine similarity between
    adjacent sentence embeddings falls below the threshold (0.6).  chunk_size
    acts as a hard character cap — a group that would exceed it is flushed
    first.  The `overlap` parameter is intentionally unused: semantic boundaries
    determine splits, not a fixed character offset.

    Trade-off: always uses the local model regardless of the experiment's
    embedding provider, keeping the chunker provider-agnostic while adding a
    small CPU embedding step per run.
    """
    import nltk  # type: ignore[import-untyped]
    import numpy as np
    from nltk.tokenize import sent_tokenize  # type: ignore[import-untyped]
    from sentence_transformers import SentenceTransformer

    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)

    sentences = sent_tokenize(text)
    if not sentences:
        return []

    model = SentenceTransformer(_MODEL_NAME)
    embeddings = model.encode(sentences, show_progress_bar=False, convert_to_numpy=True)

    chunks: list[str] = []
    group: list[str] = [sentences[0]]
    group_len = len(sentences[0])

    for i in range(1, len(sentences)):
        sentence = sentences[i]
        sentence_len = len(sentence)

        # Cosine similarity between consecutive sentence embeddings.
        prev_emb = embeddings[i - 1]
        curr_emb = embeddings[i]
        norm_prev = np.linalg.norm(prev_emb)
        norm_curr = np.linalg.norm(curr_emb)
        if norm_prev > 0 and norm_curr > 0:
            similarity = float(np.dot(prev_emb, curr_emb) / (norm_prev * norm_curr))
        else:
            similarity = 0.0

        # Flush current group on semantic break or character cap overflow.
        should_flush = similarity < _SIMILARITY_THRESHOLD or (group_len + sentence_len > chunk_size)

        if should_flush and group:
            chunks.append(" ".join(group))
            group = []
            group_len = 0

        group.append(sentence)
        group_len += sentence_len + 1  # +1 for joining space

    if group:
        chunks.append(" ".join(group))

    return chunks
