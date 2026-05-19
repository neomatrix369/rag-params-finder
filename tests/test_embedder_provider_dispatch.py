"""Regression tests for explicit embedding provider dispatch (local / voyage / kimchi)."""

from __future__ import annotations

import pytest

from server.core import embedder


def test_embed_documents_routes_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str], str]] = []

    def fake_local(texts: list[str], model: str) -> list[list[float]]:
        calls.append(("local", texts, model))
        return [[0.1, 0.2]]

    monkeypatch.setattr(
        "server.core.local_embedder.embed_documents_local",
        fake_local,
    )

    result = embedder.embed_documents(["chunk"], "all-MiniLM-L6-v2", provider="local")

    assert calls == [("local", ["chunk"], "all-MiniLM-L6-v2")]
    assert result == [[0.1, 0.2]]


def test_embed_query_routes_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_local(text: str, model: str) -> list[float]:
        calls.append(("local", text, model))
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("server.core.local_embedder.embed_query_local", fake_local)

    result = embedder.embed_query("question", "all-MiniLM-L6-v2", provider="local")

    assert calls == [("local", "question", "all-MiniLM-L6-v2")]
    assert result == [0.1, 0.2, 0.3]


def test_embed_documents_routes_voyage_standard_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_voyage(texts: list[str], model: str) -> list[list[float]]:
        calls.append(f"voyage:{model}:{len(texts)}")
        return [[1.0]]

    def fail_context(texts: list[str], model: str) -> list[list[float]]:
        raise AssertionError("contextualized path should not run for voyage-3.5-lite")

    monkeypatch.setattr(embedder, "_embed_documents_voyage", fake_voyage)
    monkeypatch.setattr(embedder, "_embed_documents_voyage_context", fail_context)

    result = embedder.embed_documents(["a", "b"], "voyage-3.5-lite", provider="voyage")

    assert calls == ["voyage:voyage-3.5-lite:2"]
    assert result == [[1.0]]


def test_embed_query_routes_voyage_contextualized_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fail_standard(text: str, model: str) -> list[float]:
        raise AssertionError("standard voyage path should not run for voyage-context-3")

    def fake_context(text: str, model: str) -> list[float]:
        calls.append(f"context:{model}")
        return [0.5, 0.6]

    monkeypatch.setattr(embedder, "_embed_query_voyage", fail_standard)
    monkeypatch.setattr(embedder, "_embed_query_voyage_context", fake_context)

    result = embedder.embed_query("long doc", "voyage-context-3", provider="voyage")

    assert calls == ["context:voyage-context-3"]
    assert result == [0.5, 0.6]


def test_embed_documents_routes_kimchi_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_kimchi(texts: list[str], model: str) -> list[list[float]]:
        calls.append((texts, model))
        return [[9.0, 8.0]]

    monkeypatch.setattr(
        "server.core.kimchi_embedder.embed_documents_kimchi",
        fake_kimchi,
    )

    result = embedder.embed_documents(
        ["kimchi-chunk"],
        "openai/text-embedding-3-large",
        provider="kimchi",
    )

    assert calls == [(["kimchi-chunk"], "openai/text-embedding-3-large")]
    assert result == [[9.0, 8.0]]


@pytest.mark.parametrize("provider", ["", "azure", "unknown"])
def test_embed_documents_rejects_unsupported_provider(provider: str) -> None:
    with pytest.raises(ValueError, match=f"Unsupported embedding provider '{provider}'"):
        embedder.embed_documents(["text"], "any-model", provider=provider)


@pytest.mark.parametrize("provider", ["", "azure"])
def test_embed_query_rejects_unsupported_provider(provider: str) -> None:
    with pytest.raises(ValueError, match=f"Unsupported embedding provider '{provider}'"):
        embedder.embed_query("text", "any-model", provider=provider)
