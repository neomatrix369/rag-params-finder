"""Tests for DoubleWord batch embedding client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI

from server.core.embedding.doubleword_client import (
    BatchSnapshot,
    build_jsonl,
    cancel_batch,
    create_async_client,
    download_vectors,
    poll_batch,
    submit_batch,
)


class TestBatchSnapshot:
    """Scenario: BatchSnapshot dataclass with dashboard URL."""

    def test_dashboard_url_property(self):
        """
        Scenario: dashboard url property.
        Slice: 48A — DoubleWord batch client.
        Given a BatchSnapshot with batch_id abc123
        When dashboard_url property is accessed
        Then returns https://app.doubleword.ai/batches/abc123.
        """
        ### Given
        snapshot = BatchSnapshot(
            batch_id="abc123",
            status="processing",
            output_file_id=None,
            error_file_id=None,
            completed=0,
            total=100,
            failed=0,
            created_at=1234567890,
            completed_at=None,
        )
        ### When
        url = snapshot.dashboard_url
        ### Then
        assert url == "https://app.doubleword.ai/batches/abc123"


class TestCreateAsyncClient:
    """Scenario: AsyncOpenAI client factory."""

    def test_creates_client_with_api_key(self):
        """
        Scenario: creates client with api key.
        Slice: 48A — DoubleWord batch client.
        Given DOUBLEWORD_API_KEY is set
        When create_async_client is called
        Then returns AsyncOpenAI pointing to DoubleWord base_url.
        """
        ### Given
        mock_settings = MagicMock(
            doubleword_api_key=MagicMock(get_secret_value=MagicMock(return_value="test-key")),
            doubleword_base_url="https://api.doubleword.ai/v1",
        )
        ### When
        with patch("server.core.embedding.doubleword_client.settings", mock_settings):
            client = create_async_client()
        ### Then
        assert isinstance(client, AsyncOpenAI)

    def test_raises_when_api_key_missing(self):
        """
        Scenario: raises when api key missing.
        Slice: 48A — DoubleWord batch client.
        Given DOUBLEWORD_API_KEY is None
        When create_async_client is called
        Then raises ValueError with helpful message.
        """
        ### Given
        mock_settings = MagicMock(doubleword_api_key=None)
        ### When / Then
        with patch("server.core.embedding.doubleword_client.settings", mock_settings):
            with pytest.raises(ValueError, match="DOUBLEWORD_API_KEY not set"):
                create_async_client()


class TestBuildJsonl:
    """Scenario: JSONL payload builder for batch API."""

    def test_builds_correct_json_structure(self):
        """
        Scenario: builds correct json structure.
        Slice: 48A — DoubleWord batch client.
        Given items [(id1, text1)], model, dimensions
        When build_jsonl is called
        Then returns JSONL with custom_id, method, url, body fields.
        """
        ### Given
        items = [("doc-1", "Hello world")]
        ### When
        payload = build_jsonl(items, model="Qwen/Qwen3-Embedding-8B", dimensions=1024)
        ### Then
        lines = payload.decode("utf-8").split("\n")
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["custom_id"] == "doc-1"
        assert obj["method"] == "POST"
        assert obj["url"] == "/v1/embeddings"
        assert obj["body"]["model"] == "Qwen/Qwen3-Embedding-8B"
        assert obj["body"]["input"] == "Hello world"
        assert obj["body"]["dimensions"] == 1024

    def test_multiple_items_newline_separated(self):
        """
        Scenario: multiple items newline separated.
        Slice: 48A — DoubleWord batch client.
        Given 2 items
        When build_jsonl is called
        Then returns JSONL with 2 lines separated by newlines.
        """
        ### Given
        items = [("id1", "text1"), ("id2", "text2")]
        ### When
        payload = build_jsonl(items, model="Qwen/Qwen3-Embedding-8B", dimensions=1024)
        ### Then
        lines = payload.decode("utf-8").split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["custom_id"] == "id1"
        assert json.loads(lines[1])["custom_id"] == "id2"

    def test_raises_when_line_exceeds_5mb(self):
        """
        Scenario: raises when line exceeds 5mb.
        Slice: 48A — DoubleWord batch client.
        Given an item with text > 5 MB
        When build_jsonl is called
        Then raises ValueError with line size exceeded message.
        """
        ### Given
        huge_text = "x" * (10_000_000)  # 10 MB text
        items = [("huge-id", huge_text)]
        ### When / Then
        with pytest.raises(ValueError, match="exceeds 5 MB limit"):
            build_jsonl(items, model="Qwen/Qwen3-Embedding-8B", dimensions=1024)


class TestSubmitBatch:
    """Scenario: Batch submission to DoubleWord API."""

    @pytest.mark.asyncio
    async def test_submits_batch_with_file_and_metadata(self):
        """
        Scenario: submits batch with file and metadata.
        Slice: 48A — DoubleWord batch client.
        Given AsyncOpenAI client, job_key, payload, window
        When submit_batch is called
        Then uploads file, creates batch, returns batch_id.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_file = MagicMock(id="file-123")
        mock_batch = MagicMock(id="batch-456")
        # Make both calls async-compatible
        mock_client.files.create = AsyncMock(return_value=mock_file)
        mock_client.batches.create = AsyncMock(return_value=mock_batch)

        ### When
        batch_id = await submit_batch(
            mock_client,
            "test-job",
            b'{"custom_id": "1"}',
            "1h",
        )

        ### Then
        assert batch_id == "batch-456"
        mock_client.files.create.assert_called_once()
        mock_client.batches.create.assert_called_once()
        create_call_kwargs = mock_client.batches.create.call_args.kwargs
        assert create_call_kwargs["input_file_id"] == "file-123"
        assert create_call_kwargs["endpoint"] == "/v1/embeddings"
        assert create_call_kwargs["completion_window"] == "1h"
        assert create_call_kwargs["metadata"]["job_key"] == "test-job"
        assert create_call_kwargs["metadata"]["source"] == "rag-params-finder"


class TestPollBatch:
    """Scenario: Batch status polling."""

    @pytest.mark.asyncio
    async def test_polls_and_returns_snapshot(self):
        """
        Scenario: polls and returns snapshot.
        Slice: 48A — DoubleWord batch client.
        Given a batch_id
        When poll_batch is called
        Then returns BatchSnapshot with status, counts, file IDs.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_batch = MagicMock(
            id="batch-123",
            status="processing",
            output_file_id="output-456",
            error_file_id="error-789",
            request_counts=MagicMock(completed=50, total=100, failed=0),
            created_at=1000,
            completed_at=None,
        )
        mock_client.batches.retrieve = AsyncMock(return_value=mock_batch)

        ### When
        snapshot = await poll_batch(mock_client, "batch-123")

        ### Then
        assert snapshot.batch_id == "batch-123"
        assert snapshot.status == "processing"
        assert snapshot.output_file_id == "output-456"
        assert snapshot.error_file_id == "error-789"
        assert snapshot.completed == 50
        assert snapshot.total == 100
        assert snapshot.failed == 0


class TestDownloadVectors:
    """Scenario: Vector result parsing from batch output."""

    @pytest.mark.asyncio
    async def test_downloads_and_parses_output_file(self):
        """
        Scenario: downloads and parses output file.
        Slice: 48A — DoubleWord batch client.
        Given output_file_id
        When download_vectors is called
        Then extracts embeddings and token counts.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        json_line_1 = (
            '{"custom_id": "id1", "response": {"body": '
            '{"data": [{"embedding": [0.1, 0.2]}], '
            '"usage": {"prompt_tokens": 10}}}}\n'
        )
        json_line_2 = (
            '{"custom_id": "id2", "response": {"body": '
            '{"data": [{"embedding": [0.3, 0.4]}], '
            '"usage": {"prompt_tokens": 12}}}}\n'
        )
        output_content = MagicMock(text=json_line_1 + json_line_2)
        mock_client.files.content = AsyncMock(return_value=output_content)

        ### When
        vectors, errors, tokens = await download_vectors(
            mock_client,
            "output-123",
            None,
        )

        ### Then
        assert len(vectors) == 2
        assert vectors["id1"] == [0.1, 0.2]
        assert vectors["id2"] == [0.3, 0.4]
        assert len(errors) == 0
        assert tokens == 22  # 10 + 12

    @pytest.mark.asyncio
    async def test_downloads_and_parses_error_file(self):
        """
        Scenario: downloads and parses error file.
        Slice: 48A — DoubleWord batch client.
        Given error_file_id
        When download_vectors is called
        Then extracts error custom_ids.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        error_content = MagicMock(text=('{"custom_id": "bad-id1"}\n{"custom_id": "bad-id2"}\n'))
        mock_client.files.content = AsyncMock(return_value=error_content)

        ### When
        vectors, errors, tokens = await download_vectors(
            mock_client,
            None,
            "error-456",
        )

        ### Then
        assert len(vectors) == 0
        assert errors == {"bad-id1", "bad-id2"}
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_handles_none_file_ids_gracefully(self):
        """
        Scenario: handles none file ids gracefully.
        Slice: 48A — DoubleWord batch client.
        Given output_file_id=None, error_file_id=None
        When download_vectors is called
        Then returns empty results without crashing.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)

        ### When
        vectors, errors, tokens = await download_vectors(
            mock_client,
            None,
            None,
        )

        ### Then
        assert vectors == {}
        assert errors == set()
        assert tokens == 0
        mock_client.files.content.assert_not_called()

    @pytest.mark.asyncio
    async def test_combines_output_and_error_files(self):
        """
        Scenario: combines output and error files.
        Slice: 48A — DoubleWord batch client.
        Given both output and error files
        When download_vectors is called
        Then returns both vectors and errors combined.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        json_output = (
            '{"custom_id": "id1", "response": {"body": '
            '{"data": [{"embedding": [0.1]}], '
            '"usage": {"prompt_tokens": 10}}}}\n'
        )
        output_content = MagicMock(text=json_output)
        error_content = MagicMock(text='{"custom_id": "bad-id1"}\n')
        # Mock returns different content based on call
        mock_client.files.content = AsyncMock(side_effect=[output_content, error_content])

        ### When
        vectors, errors, tokens = await download_vectors(
            mock_client,
            "output-123",
            "error-456",
        )

        ### Then
        assert len(vectors) == 1
        assert vectors["id1"] == [0.1]
        assert errors == {"bad-id1"}
        assert tokens == 10


class TestCancelBatch:
    """Scenario: Batch cancellation."""

    @pytest.mark.asyncio
    async def test_cancels_batch(self):
        """
        Scenario: cancels batch.
        Slice: 48A — DoubleWord batch client.
        Given a batch_id
        When cancel_batch is called
        Then calls client.batches.cancel.
        """
        ### Given
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.batches.cancel = AsyncMock()

        ### When
        await cancel_batch(mock_client, "batch-123")

        ### Then
        mock_client.batches.cancel.assert_called_once_with("batch-123")
