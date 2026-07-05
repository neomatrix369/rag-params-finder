from server.utils.logger import get_logger

logger = get_logger(__name__)

_SIMILARITY_THRESHOLD = 0.6
_MODEL_NAME = "all-MiniLM-L6-v2"


def _overlap_sentences(flushed: list[str], overlap: int) -> list[str]:
    """Trailing sentences of a flushed group to seed the next chunk.

    Sentence-granular (whole sentences only, never a mid-sentence cut), taking
    as many trailing sentences as fit within `overlap` characters.  At least the
    final sentence is always carried when overlap > 0, so consecutive semantic
    chunks share boundary context.  Returns an empty list when overlap <= 0.
    """
    if overlap <= 0 or not flushed:
        return []

    carried: list[str] = []
    carried_len = 0
    for sentence in reversed(flushed):
        # Always keep the last sentence; add earlier ones only while within budget.
        if carried and carried_len + len(sentence) > overlap:
            break
        carried.insert(0, sentence)
        carried_len += len(sentence) + 1  # +1 for the joining space
    return carried


def chunk_semantic(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Semantic chunking using sentence-level cosine similarity.

    Splits text into sentences, embeds each one with all-MiniLM-L6-v2, then
    groups consecutive sentences into chunks when the cosine similarity between
    adjacent sentence embeddings falls below the threshold (0.6).  chunk_size
    acts as a hard character cap — a group that would exceed it is flushed
    first.

    `overlap` carries the trailing sentence(s) of a flushed group (up to
    `overlap` characters, whole sentences only) into the start of the next
    group, mirroring how the sentence chunker preserves cross-boundary context.
    With overlap=0 the behaviour is unchanged — semantic boundaries alone decide
    splits.

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
            # Seed the next group with trailing sentences for overlap context.
            group = _overlap_sentences(group, overlap)
            group_len = sum(len(s) + 1 for s in group)

        group.append(sentence)
        group_len += sentence_len + 1  # +1 for joining space

    if group:
        chunks.append(" ".join(group))

    return chunks
