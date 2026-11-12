"""DoubleWord pre-embedding: plan (pure) + submit (effectful)."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from server.utils.logger import get_logger

if TYPE_CHECKING:
    from server.models.config import ExperimentConfig

logger = get_logger(__name__)

CHECKPOINT_PATH = ".rpf_state/doubleword_batches.json"
DASHBOARD_URL_TEMPLATE = "https://app.doubleword.ai/batches/{batch_id}"
_CHECKPOINT_LOCK = threading.Lock()


@dataclass(frozen=True)
class EmbedItem:
    custom_id: str
    text: str
    role: str  # "doc" | "query"


@dataclass(frozen=True)
class EmbedJob:
    job_key: str
    role: str
    items: tuple[EmbedItem, ...]  # use tuple for immutability


@dataclass
class PreEmbedPlan:
    experiment_id: str
    model: str
    jobs: list[EmbedJob]  # jobs with cache-miss items only

    @property
    def is_empty(self) -> bool:
        return not any(job.items for job in self.jobs)


@dataclass
class SubmittedJob:
    job_key: str
    batch_id: str
    role: str
    n: int
    submitted_at: str  # ISO

    @property
    def dashboard_url(self) -> str:
        """DoubleWord dashboard URL for this batch."""
        return DASHBOARD_URL_TEMPLATE.format(batch_id=self.batch_id)


@dataclass(frozen=True)
class PreparedEmbeddings:
    """Outcome of preparing embeddings for an experiment.

    `ready_to_run` is True when the sweep may start immediately (no DoubleWord
    model, or every text already cached). When it is False the experiment has
    been marked `pre_embed.state = "waiting"` and the watcher resumes it.
    """

    ready_to_run: bool
    submitted: tuple[SubmittedJob, ...] = ()


class CheckpointStore:
    """Atomic read/write of .rpf_state/doubleword_batches.json."""

    def __init__(self, path: str = CHECKPOINT_PATH):
        self._path = path

    def load(self) -> list[dict]:
        try:
            with open(self._path) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, entries: list[dict]) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=Path(self._path).parent, delete=False, suffix=".tmp"
        ) as f:
            json.dump(entries, f)
            tmp = f.name
        os.replace(tmp, self._path)

    def add_entries(self, new_entries: list[dict]) -> None:
        with _CHECKPOINT_LOCK:
            existing = self.load()
            existing.extend(new_entries)
            self._write(existing)

    def remove_by_batch_id(self, batch_id: str) -> None:
        with _CHECKPOINT_LOCK:
            entries = self.load()
            filtered = [e for e in entries if e.get("batch_id") != batch_id]
            self._write(filtered)

    def get_for_experiment(self, experiment_id: str) -> list[dict]:
        return [e for e in self.load() if e.get("experiment_id") == experiment_id]

    def remove_for_experiment(self, experiment_id: str) -> None:
        with _CHECKPOINT_LOCK:
            entries = self.load()
            filtered = [e for e in entries if e.get("experiment_id") != experiment_id]
            self._write(filtered)


def plan_pre_embed(
    experiment_id: str,
    model: str,
    source_texts: list[str],
    queries: list[str],
    cached_keys: frozenset,
    *,
    dimensions: int = 1024,
    instruction: str = "",
) -> PreEmbedPlan:
    """Pure: compute which texts need embedding (cache misses only).

    The job_key is derived from (experiment_id, role) so the same texts
    submitted under different experiments get separate batch jobs.
    """
    from server.core.embedding.embedding_cache import cache_key

    doc_items = []
    for i, text in enumerate(source_texts):
        key = cache_key(
            text,
            provider="doubleword",
            model=model,
            dim=dimensions,
            instruction="",
            role="doc",
        )
        if key not in cached_keys:
            doc_items.append(EmbedItem(custom_id=key, text=text, role="doc"))

    query_items = []
    for text in queries:
        key = cache_key(
            text,
            provider="doubleword",
            model=model,
            dim=dimensions,
            instruction=instruction,
            role="query",
        )
        if key not in cached_keys:
            query_items.append(EmbedItem(custom_id=key, text=text, role="query"))

    jobs = []
    if doc_items:
        jobs.append(
            EmbedJob(
                job_key=f"{experiment_id}:doc",
                role="doc",
                items=tuple(doc_items),
            )
        )
    if query_items:
        jobs.append(
            EmbedJob(
                job_key=f"{experiment_id}:query",
                role="query",
                items=tuple(query_items),
            )
        )

    return PreEmbedPlan(experiment_id=experiment_id, model=model, jobs=jobs)


async def submit_pre_embed(
    plan: PreEmbedPlan,
    *,
    dimensions: int = 1024,
    window: str = "1h",
    checkpoint_store: CheckpointStore | None = None,
) -> list[SubmittedJob]:
    """Effectful: submit all batch jobs first, THEN checkpoint.

    Returns list of SubmittedJob (one per non-empty job).
    """
    from server.core.embedding.doubleword_client import (
        build_jsonl,
        create_async_client,
        submit_batch,
    )

    if checkpoint_store is None:
        checkpoint_store = CheckpointStore()

    if plan.is_empty:
        return []

    client = create_async_client()
    submitted: list[SubmittedJob] = []

    # Phase 1: submit ALL jobs first (docextract pattern)
    batch_ids: list[tuple[EmbedJob, str]] = []
    for job in plan.jobs:
        if not job.items:
            continue
        items = [(item.custom_id, item.text) for item in job.items]
        payload = build_jsonl(items, model=plan.model, dimensions=dimensions)
        batch_id = await submit_batch(client, job.job_key, payload, window)
        batch_ids.append((job, batch_id))

    # Phase 2: checkpoint ALL after all submissions succeed
    checkpoint_entries = []
    now = datetime.now(UTC).isoformat()
    for job, batch_id in batch_ids:
        entry = {
            "experiment_id": plan.experiment_id,
            "job_key": job.job_key,
            "batch_id": batch_id,
            "role": job.role,
            "n": len(job.items),
            "submitted_at": now,
        }
        checkpoint_entries.append(entry)
        submitted.append(
            SubmittedJob(
                job_key=job.job_key,
                batch_id=batch_id,
                role=job.role,
                n=len(job.items),
                submitted_at=now,
            )
        )

    if checkpoint_entries:
        await asyncio.to_thread(checkpoint_store.add_entries, checkpoint_entries)

    return submitted


async def prepare_embeddings(experiment_id: str, config: ExperimentConfig) -> PreparedEmbeddings:
    """Decide whether an experiment can run now, pre-embedding with DoubleWord first.

    Owns the whole DoubleWord decision: whether the config uses a DoubleWord
    model, which texts are still uncached, batch submission, and marking the
    experiment `pre_embed.state = "waiting"`. Callers only act on
    `ready_to_run`.
    """
    from server.core.data_loader import load_all_files
    from server.core.embedding.embedder_factory import QWEN3_QUERY_INSTRUCTION
    from server.core.embedding.embedding_cache import cache_key, get_embedding_cache
    from server.core.model_registry import get_dimensions, provider_for_model
    from server.core.query_loader import load_queries
    from server.db.ports.store_factory import get_storage_backend
    from server.settings import settings

    dw_models = [m for m in config.embedding.models if provider_for_model(m) == "doubleword"]
    if not dw_models:
        return PreparedEmbeddings(ready_to_run=True)

    dw_model = dw_models[0]  # one doubleword model per S1 design
    dim = get_dimensions(dw_model)

    # Load data to compute cache keys
    source_texts_str = await asyncio.to_thread(load_all_files, config.data_paths)
    # Split on double newlines to get individual text chunks
    source_texts = [t.strip() for t in source_texts_str.split("\n\n") if t.strip()]

    queries_data = await asyncio.to_thread(load_queries, config.queries_file)
    queries = [q.text for q in queries_data]

    # Check cache
    cache = get_embedding_cache()
    doc_keys = [
        cache_key(
            t,
            provider="doubleword",
            model=dw_model,
            dim=dim,
            instruction="",
            role="doc",
        )
        for t in source_texts
    ]
    query_keys = [
        cache_key(
            t,
            provider="doubleword",
            model=dw_model,
            dim=dim,
            instruction=QWEN3_QUERY_INSTRUCTION,
            role="query",
        )
        for t in queries
    ]
    all_keys = doc_keys + query_keys
    cached = cache.cached_keys(all_keys)

    plan = plan_pre_embed(
        experiment_id,
        dw_model,
        source_texts,
        queries,
        cached,
        dimensions=dim,
        instruction=QWEN3_QUERY_INSTRUCTION,
    )

    if plan.is_empty:
        # Everything cached — proceed immediately
        return PreparedEmbeddings(ready_to_run=True)

    # Submit batches and set pre_embed.state = "waiting"
    submitted = await submit_pre_embed(
        plan, dimensions=dim, window=settings.doubleword_completion_window
    )
    batch_records = [
        {
            "batch_id": j.batch_id,
            "role": j.role,
            "status": "in_progress",
            "completed": 0,
            "total": j.n,
            "dashboard_url": j.dashboard_url,
        }
        for j in submitted
    ]

    get_storage_backend().update_experiment(
        experiment_id, {"pre_embed": {"state": "waiting", "batches": batch_records}}
    )

    logger.info(
        "experiment pre_embed waiting — experiment=%s batches=%s",
        experiment_id,
        len(submitted),
    )

    return PreparedEmbeddings(ready_to_run=False, submitted=tuple(submitted))
