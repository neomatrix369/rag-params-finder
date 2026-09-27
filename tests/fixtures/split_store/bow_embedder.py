"""Deterministic bag-of-words test embedder — no model download, no network.

Author: Claude (Stream 1)
Created: 2026-09-27
Scope: Stands in for ``get_embedder("local")`` in the split-store E2E test.
       Builds one fixed vocabulary from the fixture corpus + queries (so the
       vector width is stable across a run), then embeds any text as a
       term-frequency vector over that vocabulary. Deterministic and pure —
       same text always yields the same vector, and the vector width never
       changes mid-test, unlike a real transformer download.
"""

from __future__ import annotations

import re
from collections.abc import Callable

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def build_vocabulary(texts: list[str]) -> dict[str, int]:
    """Assign each distinct token a stable index, in first-seen order."""
    vocabulary: dict[str, int] = {}
    for text in texts:
        for token in tokenize(text):
            if token not in vocabulary:
                vocabulary[token] = len(vocabulary)
    return vocabulary


def embed_text(text: str, vocabulary: dict[str, int]) -> list[float]:
    vector = [0.0] * len(vocabulary)
    for token in tokenize(text):
        index = vocabulary.get(token)
        if index is not None:
            vector[index] += 1.0
    return vector


def make_embedder_pair(
    vocabulary: dict[str, int],
) -> tuple[Callable[..., list[list[float]]], Callable[..., list[float]]]:
    """Build (embed_docs_fn, embed_query_fn) matching ``get_embedder``'s contract.

    ``embed_docs_fn(chunks, model, **kwargs) -> list[list[float]]``
    ``embed_query_fn(query_text, model) -> list[float]``
    Extra keyword args (``cancel_check``, ``parallelism``) are accepted and
    ignored — the orchestrator always passes them for the local provider.
    """

    def embed_docs_fn(chunks: list[str], _model: str, **_kwargs: object) -> list[list[float]]:
        return [embed_text(chunk, vocabulary) for chunk in chunks]

    def embed_query_fn(query_text: str, _model: str) -> list[float]:
        return embed_text(query_text, vocabulary)

    return embed_docs_fn, embed_query_fn
