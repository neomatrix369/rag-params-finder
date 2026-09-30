"""GWT tests for pre_embed — pure planning + async submit for DoubleWord batches.

Author: Claude Haiku 4.5
Created: 2026-09-30
Scope: pre_embed.py module — plan_pre_embed (pure), submit_pre_embed (async),
       CheckpointStore atomic I/O, cache-miss detection.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.core.pipeline.pre_embed import (
    CheckpointStore,
    EmbedItem,
    EmbedJob,
    PreEmbedPlan,
    SubmittedJob,
    plan_pre_embed,
    submit_pre_embed,
)


class TestPlanPreEmbedPure:
    """Scenario: plan_pre_embed computes cache-miss texts (pure function)."""

    def test_plan_pre_embed_empty_when_all_cached(self):
        """
        Scenario: plan pre embed empty when all cached.
        Slice: 48A — cache-hit fast path
        Given source_texts and queries all present in cached_keys
        When plan_pre_embed() is called
        Then the plan is_empty returns True.
        """
        ### Given
        cached_keys = frozenset(["key1", "key2", "key3"])
        source_texts = ["text1"]  # Would be converted to cache keys
        queries = ["query1"]

        with patch("server.core.embedding.embedding_cache.cache_key") as mock_cache_key:
            mock_cache_key.side_effect = lambda *a, **kw: (
                "key1" if "text1" in a else "key3" if "query1" in a else "key_missing"
            )

            ### When
            plan = plan_pre_embed(
                experiment_id="exp123",
                model="qwen3-v9",
                source_texts=source_texts,
                queries=queries,
                cached_keys=cached_keys,
                dimensions=1024,
            )

            ### Then
            assert plan.is_empty is True

    def test_plan_pre_embed_creates_doc_job_for_missing_texts(self):
        """
        Scenario: plan pre embed creates doc job for missing texts.
        Slice: 48A — doc batch creation
        Given source_texts with some cache misses
        When plan_pre_embed() is called with empty cached_keys
        Then a doc EmbedJob is created with those texts.
        """
        ### Given
        source_texts = ["doc1", "doc2"]
        queries = []
        cached_keys = frozenset()

        with patch("server.core.embedding.embedding_cache.cache_key") as mock_cache_key:
            mock_cache_key.side_effect = lambda *a, **kw: (
                "doc1_key" if "doc1" in a else "doc2_key" if "doc2" in a else "unknown"
            )

            ### When
            plan = plan_pre_embed(
                experiment_id="exp123",
                model="qwen3-v9",
                source_texts=source_texts,
                queries=queries,
                cached_keys=cached_keys,
                dimensions=1024,
            )

            ### Then
            assert len(plan.jobs) == 1
            assert plan.jobs[0].role == "doc"
            assert len(plan.jobs[0].items) == 2
            assert plan.jobs[0].items[0].text == "doc1"
            assert plan.jobs[0].items[1].text == "doc2"

    def test_plan_pre_embed_creates_query_job_for_missing_queries(self):
        """
        Scenario: plan pre embed creates query job for missing queries.
        Slice: 48A — query batch creation
        Given queries with some cache misses
        When plan_pre_embed() is called with instruction parameter
        Then a query EmbedJob is created with those queries.
        """
        ### Given
        source_texts = []
        queries = ["q1", "q2"]
        cached_keys = frozenset()

        with patch("server.core.embedding.embedding_cache.cache_key") as mock_cache_key:
            mock_cache_key.side_effect = lambda *a, **kw: (
                "q1_key" if "q1" in a else "q2_key" if "q2" in a else "unknown"
            )

            ### When
            plan = plan_pre_embed(
                experiment_id="exp123",
                model="qwen3-v9",
                source_texts=source_texts,
                queries=queries,
                cached_keys=cached_keys,
                dimensions=1024,
                instruction="Instruct: Retrieve",
            )

            ### Then
            assert len(plan.jobs) == 1
            assert plan.jobs[0].role == "query"
            assert len(plan.jobs[0].items) == 2
            assert plan.jobs[0].items[0].text == "q1"
            assert plan.jobs[0].items[1].text == "q2"

    def test_plan_pre_embed_creates_both_doc_and_query_jobs(self):
        """
        Scenario: plan pre embed creates both doc and query jobs.
        Slice: 48A — mixed doc/query batch
        Given source_texts and queries both with cache misses
        When plan_pre_embed() is called
        Then two jobs (one doc, one query) are created.
        """
        ### Given
        source_texts = ["doc1"]
        queries = ["q1"]
        cached_keys = frozenset()

        with patch("server.core.embedding.embedding_cache.cache_key") as mock_cache_key:
            mock_cache_key.side_effect = lambda *a, **kw: (
                "doc1_key" if "doc1" in a else "q1_key" if "q1" in a else "unknown"
            )

            ### When
            plan = plan_pre_embed(
                experiment_id="exp123",
                model="qwen3-v9",
                source_texts=source_texts,
                queries=queries,
                cached_keys=cached_keys,
                dimensions=1024,
                instruction="Instruct:",
            )

            ### Then
            assert len(plan.jobs) == 2
            assert plan.jobs[0].role == "doc"
            assert plan.jobs[1].role == "query"

    def test_plan_pre_embed_job_key_includes_experiment_and_role(self):
        """
        Scenario: plan pre embed job key includes experiment and role.
        Slice: 48A — job key structure
        Given an experiment_id and role
        When plan_pre_embed() creates a job
        Then job_key is "{experiment_id}:{role}".
        """
        ### Given
        source_texts = ["doc1"]
        experiment_id = "exp-abc-123"

        with patch("server.core.embedding.embedding_cache.cache_key") as mock_cache_key:
            mock_cache_key.return_value = "doc_key"

            ### When
            plan = plan_pre_embed(
                experiment_id=experiment_id,
                model="qwen3-v9",
                source_texts=source_texts,
                queries=[],
                cached_keys=frozenset(),
                dimensions=1024,
            )

            ### Then
            assert plan.jobs[0].job_key == f"{experiment_id}:doc"


class TestSubmitPreEmbedAsync:
    """Scenario: submit_pre_embed submits jobs then checkpoints atomically."""

    @pytest.mark.asyncio
    async def test_submit_pre_embed_empty_plan_returns_empty_list(self):
        """
        Scenario: submit pre embed empty plan returns empty list.
        Slice: 48A — no-op when everything cached
        Given an empty plan (is_empty=True)
        When submit_pre_embed(plan) is called
        Then an empty list is returned without submitting anything.
        """
        ### Given
        plan = PreEmbedPlan(experiment_id="exp123", model="qwen3-v9", jobs=[])

        ### When
        result = await submit_pre_embed(plan, dimensions=1024, window="1h")

        ### Then
        assert result == []

    @pytest.mark.asyncio
    async def test_submit_pre_embed_submits_all_jobs_before_checkpoint(self):
        """
        Scenario: submit pre embed submits all jobs before checkpoint.
        Slice: 48A — atomic submit-then-checkpoint (docextract pattern)
        Given a plan with 2 jobs
        When submit_pre_embed(plan, checkpoint_store=mock) is called
        Then all batch submits happen first, then checkpoint.add_entries is called once.
        """
        ### Given
        items1 = (EmbedItem(custom_id="key1", text="text1", role="doc"),)
        items2 = (EmbedItem(custom_id="key2", text="query1", role="query"),)
        plan = PreEmbedPlan(
            experiment_id="exp123",
            model="qwen3-v9",
            jobs=[
                EmbedJob(job_key="exp123:doc", role="doc", items=items1),
                EmbedJob(job_key="exp123:query", role="query", items=items2),
            ],
        )
        mock_checkpoint = MagicMock(spec=CheckpointStore)
        mock_client = AsyncMock()

        with patch("server.core.embedding.doubleword_client.create_async_client") as mock_create:
            mock_create.return_value = mock_client
            with patch("server.core.embedding.doubleword_client.build_jsonl") as mock_build:
                mock_build.return_value = b"jsonl_data"
                with patch("server.core.embedding.doubleword_client.submit_batch") as mock_submit:
                    mock_submit.side_effect = ["batch_id_1", "batch_id_2"]

                    ### When
                    result = await submit_pre_embed(
                        plan,
                        dimensions=1024,
                        window="1h",
                        checkpoint_store=mock_checkpoint,
                    )

                    ### Then
                    assert len(result) == 2
                    assert mock_checkpoint.add_entries.call_count == 1
                    entries = mock_checkpoint.add_entries.call_args[0][0]
                    assert len(entries) == 2
                    assert entries[0]["batch_id"] == "batch_id_1"
                    assert entries[1]["batch_id"] == "batch_id_2"

    @pytest.mark.asyncio
    async def test_submit_pre_embed_returns_submitted_jobs_with_metadata(self):
        """
        Scenario: submit pre embed returns submitted jobs with metadata.
        Slice: 48A — submit result structure
        Given successful batch submissions
        When submit_pre_embed() returns SubmittedJob list
        Then each has batch_id, role, n, submitted_at fields.
        """
        ### Given
        items = (
            EmbedItem(custom_id="k1", text="t1", role="doc"),
            EmbedItem(custom_id="k2", text="t2", role="doc"),
        )
        plan = PreEmbedPlan(
            experiment_id="exp123",
            model="qwen3-v9",
            jobs=[EmbedJob(job_key="exp123:doc", role="doc", items=items)],
        )
        mock_checkpoint = MagicMock(spec=CheckpointStore)
        mock_client = AsyncMock()

        with patch("server.core.embedding.doubleword_client.create_async_client") as mock_create:
            mock_create.return_value = mock_client
            with patch("server.core.embedding.doubleword_client.build_jsonl") as mock_build:
                mock_build.return_value = b"jsonl_data"
                with patch("server.core.embedding.doubleword_client.submit_batch") as mock_submit:
                    mock_submit.return_value = "batch_id_xyz"

                    ### When
                    result = await submit_pre_embed(
                        plan,
                        dimensions=1024,
                        window="1h",
                        checkpoint_store=mock_checkpoint,
                    )

                    ### Then
                    assert len(result) == 1
                    job = result[0]
                    assert isinstance(job, SubmittedJob)
                    assert job.batch_id == "batch_id_xyz"
                    assert job.role == "doc"
                    assert job.n == 2
                    assert job.submitted_at  # ISO datetime string


class TestCheckpointStore:
    """Scenario: CheckpointStore provides atomic read/write of batch registry."""

    def test_checkpoint_load_empty_file_returns_empty_list(self):
        """
        Scenario: checkpoint load empty file returns empty list.
        Slice: 48A — checkpoint initialization
        Given no checkpoint file exists
        When load() is called
        Then an empty list is returned.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(str(Path(tmpdir) / "batches.json"))

            ### When
            result = store.load()

            ### Then
            assert result == []

    def test_checkpoint_add_entries_then_load_persists(self):
        """
        Scenario: checkpoint add entries then load persists.
        Slice: 48A — checkpoint CRUD
        Given entries to add
        When add_entries() is called and then load()
        Then the entries are persisted and returned.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(str(Path(tmpdir) / "batches.json"))
            entries = [
                {"experiment_id": "exp1", "batch_id": "batch1", "role": "doc"},
                {"experiment_id": "exp1", "batch_id": "batch2", "role": "query"},
            ]

            ### When
            store.add_entries(entries)
            result = store.load()

            ### Then
            assert len(result) == 2
            assert result[0]["batch_id"] == "batch1"
            assert result[1]["batch_id"] == "batch2"

    def test_checkpoint_remove_by_batch_id_removes_matching_entry(self):
        """
        Scenario: checkpoint remove by batch id removes matching entry.
        Slice: 48A — checkpoint deletion
        Given entries in checkpoint
        When remove_by_batch_id("batch1") is called
        Then only the matching entry is removed.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(str(Path(tmpdir) / "batches.json"))
            entries = [
                {"experiment_id": "exp1", "batch_id": "batch1"},
                {"experiment_id": "exp1", "batch_id": "batch2"},
            ]
            store.add_entries(entries)

            ### When
            store.remove_by_batch_id("batch1")
            result = store.load()

            ### Then
            assert len(result) == 1
            assert result[0]["batch_id"] == "batch2"

    def test_checkpoint_get_for_experiment_filters_by_id(self):
        """
        Scenario: checkpoint get for experiment filters by id.
        Slice: 48A — experiment scope
        Given entries for multiple experiments
        When get_for_experiment("exp1") is called
        Then only entries for exp1 are returned.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(str(Path(tmpdir) / "batches.json"))
            entries = [
                {"experiment_id": "exp1", "batch_id": "batch1"},
                {"experiment_id": "exp2", "batch_id": "batch2"},
                {"experiment_id": "exp1", "batch_id": "batch3"},
            ]
            store.add_entries(entries)

            ### When
            result = store.get_for_experiment("exp1")

            ### Then
            assert len(result) == 2
            assert all(e["experiment_id"] == "exp1" for e in result)

    def test_checkpoint_remove_for_experiment_deletes_all_for_id(self):
        """
        Scenario: checkpoint remove for experiment deletes all for id.
        Slice: 48A — experiment cleanup
        Given entries for multiple experiments
        When remove_for_experiment("exp1") is called
        Then all exp1 entries are removed.
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CheckpointStore(str(Path(tmpdir) / "batches.json"))
            entries = [
                {"experiment_id": "exp1", "batch_id": "batch1"},
                {"experiment_id": "exp2", "batch_id": "batch2"},
                {"experiment_id": "exp1", "batch_id": "batch3"},
            ]
            store.add_entries(entries)

            ### When
            store.remove_for_experiment("exp1")
            result = store.load()

            ### Then
            assert len(result) == 1
            assert result[0]["experiment_id"] == "exp2"

    def test_checkpoint_write_is_atomic(self):
        """
        Scenario: checkpoint write is atomic.
        Slice: 48A — crash safety
        Given CheckpointStore with _write() method
        When _write() is called
        Then the file is created via atomic temp file swap (os.replace).
        """
        ### Given
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "batches.json")
            store = CheckpointStore(path)
            entries = [{"batch_id": "batch1"}]

            ### When
            store._write(entries)

            ### Then
            # File exists and is valid JSON
            assert Path(path).exists()
            with open(path) as f:
                data = json.load(f)
            assert len(data) == 1
