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


class DoublewordCacheMissError(Exception):
    """Raised when doubleword run-time embedder finds uncached texts."""

    pass


def get_embedder(provider: str) -> tuple[EmbedDocsFn, EmbedQueryFn]:
    """Return (embed_documents_fn, embed_query_fn) for the given provider.

    Args:
        provider: One of "voyage", "local", "sie", "doubleword".

    Returns:
        Pair of callables with signatures:
          embed_docs(texts: list[str], model_id: str) -> list[list[float]]
          embed_query(text: str, model_id: str) -> list[float]

    Raises:
        ValueError: If provider is not recognised.
        DoublewordCacheMissError: If doubleword provider encounters uncached texts at run-time.
    """
    if provider == "voyage":
        from server.core.embedding.embedder import embed_documents_voyage, embed_query_voyage

        return embed_documents_voyage, embed_query_voyage

    if provider == "local":
        from server.core.embedding.local_embedder import embed_documents_local, embed_query_local

        return embed_documents_local, embed_query_local

    if provider == "sie":
        from server.core.embedding.sie_embedder import embed_documents_sie, embed_query_sie

        return embed_documents_sie, embed_query_sie

    if provider == "doubleword":
        from server.core.embedding.embedding_cache import cache_key, get_embedding_cache
        from server.core.model_registry import get_dimensions

        def embed_documents_doubleword(texts: list[str], model_id: str) -> list[list[float]]:
            cache = get_embedding_cache()
            dim = get_dimensions(model_id)
            keys = [
                cache_key(
                    t,
                    provider="doubleword",
                    model=model_id,
                    dim=dim,
                    instruction="",
                    role="doc",
                )
                for t in texts
            ]
            cached = cache.get_many(keys)
            missing = [k for k in keys if k not in cached]
            if missing:
                raise DoublewordCacheMissError(
                    f"Missing {len(missing)} texts from embedding cache — "
                    "pre_embed must complete before run"
                )
            return [cached[k] for k in keys]

        def embed_query_doubleword(text: str, model_id: str) -> list[float]:
            cache = get_embedding_cache()
            dim = get_dimensions(model_id)
            # Query prefix is fixed for Qwen3 (V9)
            instruction = "Instruct: Retrieve relevant passages for the query.\nQuery: "
            key = cache_key(
                text,
                provider="doubleword",
                model=model_id,
                dim=dim,
                instruction=instruction,
                role="query",
            )
            cached = cache.get_many([key])
            if key not in cached:
                raise DoublewordCacheMissError("Missing 1 text from embedding cache")
            return cached[key]

        return embed_documents_doubleword, embed_query_doubleword

    raise ValueError(
        f"Unknown embedding provider '{provider}'. "
        "Supported: 'voyage', 'local', 'sie', 'doubleword'."
    )
