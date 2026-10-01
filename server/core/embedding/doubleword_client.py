"""DoubleWord batch embedding client — port of docextract llm_doubleword.py."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from server.settings import settings
from server.utils.logger import get_logger

if TYPE_CHECKING:
    from openai.types.batch import Batch

logger = get_logger(__name__)


@dataclass
class BatchSnapshot:
    """Snapshot of a DoubleWord batch status."""

    batch_id: str
    status: str
    output_file_id: str | None
    error_file_id: str | None
    completed: int
    total: int
    failed: int
    created_at: int | None
    completed_at: int | None

    @property
    def dashboard_url(self) -> str:
        """DoubleWord dashboard URL for this batch."""
        return f"https://app.doubleword.ai/batches/{self.batch_id}"


def create_async_client() -> AsyncOpenAI:
    """Create AsyncOpenAI client pointing to DoubleWord API.

    Raises:
        ValueError: If DOUBLEWORD_API_KEY is not set.
    """
    if settings.doubleword_api_key is None:
        raise ValueError(
            "DOUBLEWORD_API_KEY not set. Required for DoubleWord batch embeddings. "
            "See docs/user-guide/doubleword-setup.md"
        )

    api_key = settings.doubleword_api_key.get_secret_value()
    return AsyncOpenAI(
        api_key=api_key,
        base_url=settings.doubleword_base_url,
    )


def build_jsonl(
    items: list[tuple[str, str]],
    *,
    model: str,
    dimensions: int,
) -> bytes:
    """Build JSONL payload for DoubleWord batch API.

    Each line is a JSON request: custom_id, method, url, body.

    Args:
        items: List of (custom_id, text) tuples.
        model: Embedding model ID.
        dimensions: Embedding dimensions (e.g., 1024).

    Returns:
        Bytes representing the JSONL payload.

    Raises:
        ValueError: If any line exceeds 5 MB.
    """
    lines: list[bytes] = []
    for custom_id, text in items:
        request_obj = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {
                "model": model,
                "input": text,
                "dimensions": dimensions,
            },
        }
        line = json.dumps(request_obj, separators=(",", ":"))
        line_bytes = line.encode("utf-8")
        if len(line_bytes) > 5_242_880:  # 5 MB
            raise ValueError(
                f"JSONL line for item {custom_id!r} exceeds 5 MB limit ({len(line_bytes)} bytes)"
            )
        lines.append(line_bytes)

    return b"\n".join(lines)


async def submit_batch(
    client: AsyncOpenAI,
    job_key: str,
    payload: bytes,
    window: str,
) -> str:
    """Submit a batch to DoubleWord API.

    Args:
        client: AsyncOpenAI client.
        job_key: Unique job identifier for metadata.
        payload: JSONL payload as bytes.
        window: Completion window ("1h" or "24h").

    Returns:
        Batch ID string.
    """
    # Upload the JSONL file
    file_response = await client.files.create(
        file=("batch.jsonl", payload, "application/jsonl"),
        purpose="batch",
    )
    input_file_id = file_response.id

    logger.debug("batch uploaded — file_id=%s job_key=%s", input_file_id, job_key)

    # Create the batch
    # Note: completion_window must be "24h" per OpenAI API (not "1h" yet)
    batch = await client.batches.create(
        input_file_id=input_file_id,
        endpoint="/v1/embeddings",
        completion_window=window,  # type: ignore[arg-type]
        metadata={"source": "rag-params-finder", "job_key": job_key},
    )

    logger.info(
        "batch submitted — batch_id=%s job_key=%s window=%s",
        batch.id,
        job_key,
        window,
    )
    assert isinstance(batch.id, str), f"expected str batch id, got {type(batch.id)}"
    return batch.id


async def poll_batch(
    client: AsyncOpenAI,
    batch_id: str,
) -> BatchSnapshot:
    """Retrieve the current status of a batch.

    Args:
        client: AsyncOpenAI client.
        batch_id: DoubleWord batch ID.

    Returns:
        BatchSnapshot with current counts and status.
    """
    batch: Batch = await client.batches.retrieve(batch_id)

    output_file_id = None
    error_file_id = None
    if batch.output_file_id:
        output_file_id = batch.output_file_id
    if batch.error_file_id:
        error_file_id = batch.error_file_id

    # request_counts is always present in a batch response
    assert batch.request_counts is not None
    completed = batch.request_counts.completed
    total = batch.request_counts.total
    failed = batch.request_counts.failed

    snapshot = BatchSnapshot(
        batch_id=batch.id,
        status=batch.status,
        output_file_id=output_file_id,
        error_file_id=error_file_id,
        completed=completed,
        total=total,
        failed=failed,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
    )

    logger.debug(
        "batch polled — batch_id=%s status=%s completed=%d/%d failed=%d",
        batch_id,
        batch.status,
        completed,
        total,
        failed,
    )

    return snapshot


async def download_vectors(
    client: AsyncOpenAI,
    output_file_id: str | None,
    error_file_id: str | None,
) -> tuple[dict[str, list[float]], set[str], int]:
    """Download and parse batch results.

    Processes both the output file (successful embeddings) and error file
    (pre-processing or embedding failures).

    Args:
        client: AsyncOpenAI client.
        output_file_id: File ID for successful responses (may be None).
        error_file_id: File ID for error responses (may be None).

    Returns:
        Tuple of (vectors_dict, error_ids_set, total_prompt_tokens).
        vectors_dict maps custom_id → embedding list.
        error_ids_set contains custom_ids that failed.
        total_prompt_tokens sums all prompt_tokens from output.
    """
    vectors: dict[str, list[float]] = {}
    error_ids: set[str] = set()
    total_prompt_tokens = 0

    if output_file_id:
        logger.debug("downloading output file — file_id=%s", output_file_id)
        try:
            content = await client.files.content(output_file_id)
            lines = content.text.split("\n")
            for line in lines:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    custom_id = obj["custom_id"]
                    embedding = obj["response"]["body"]["data"][0]["embedding"]
                    prompt_tokens = obj["response"]["body"]["usage"]["prompt_tokens"]
                    vectors[custom_id] = embedding
                    total_prompt_tokens += prompt_tokens
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    logger.warning("failed to parse output line: %s", line, exc_info=e)
        except Exception as e:
            logger.warning("failed to download output file: %s", e, exc_info=True)

    if error_file_id:
        logger.debug("downloading error file — file_id=%s", error_file_id)
        try:
            content = await client.files.content(error_file_id)
            lines = content.text.split("\n")
            for line in lines:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    custom_id = obj["custom_id"]
                    error_ids.add(custom_id)
                except (KeyError, json.JSONDecodeError) as e:
                    logger.warning("failed to parse error line: %s", line, exc_info=e)
        except Exception as e:
            logger.warning("failed to download error file: %s", e, exc_info=True)

    logger.info(
        "batch results downloaded — vectors=%d errors=%d tokens=%d",
        len(vectors),
        len(error_ids),
        total_prompt_tokens,
    )

    return vectors, error_ids, total_prompt_tokens


async def cancel_batch(
    client: AsyncOpenAI,
    batch_id: str,
) -> None:
    """Cancel a batch on DoubleWord.

    Args:
        client: AsyncOpenAI client.
        batch_id: DoubleWord batch ID.
    """
    await client.batches.cancel(batch_id)
    logger.info("batch cancelled — batch_id=%s", batch_id)
