"""Provider dispatch factory for embedding functions.

Returns a (embed_docs_fn, embed_query_fn) pair for the given provider string.
The orchestrator calls get_embedder(provider) once per run and uses the returned
functions directly — no if/elif chains in the pipeline code.

Design decision (DECISIONS.md #10): factory function preferred over Protocol/ABC
at current scale — YAGNI + Simple Design.
"""

from __future__ import annotations

from collections.abc import Callable

EmbedDocsFn = Callable[..., list[list[float]]]
EmbedQueryFn = Callable[[str, str], list[float]]


def get_embedder(provider: str) -> tuple[EmbedDocsFn, EmbedQueryFn]:
    """Return (embed_documents_fn, embed_query_fn) for the given provider.

    Args:
        provider: One of "voyage", "local", "sie".

    Returns:
        Pair of callables with signatures:
          embed_docs(texts: list[str], model_id: str) -> list[list[float]]
          embed_query(text: str, model_id: str) -> list[float]

    Raises:
        ValueError: If provider is not recognised.
    """
    if provider == "voyage":
        from server.core.embedder import embed_documents_voyage, embed_query_voyage

        return embed_documents_voyage, embed_query_voyage

    if provider == "local":
        from server.core.local_embedder import embed_documents_local, embed_query_local

        return embed_documents_local, embed_query_local

    if provider == "sie":
        from server.core.sie_embedder import embed_documents_sie, embed_query_sie

        return embed_documents_sie, embed_query_sie

    raise ValueError(
        f"Unknown embedding provider '{provider}'. Supported: 'voyage', 'local', 'sie'."
    )
