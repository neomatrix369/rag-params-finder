import time
import uuid
from datetime import datetime

from server.core.chunkers import chunk_text
from server.core.embedder import embed_documents, embed_query
from server.core.pdf_parser import parse_pdf
from server.core.query_loader import load_queries
from server.core.reranker import rerank_results
from server.core.retriever import dense_search
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.config import ExperimentConfig, RunParams, expand_sweep
from server.models.enums import Phase
from server.models.results import QueryResult
from server.models.status import RunStatus
from server.utils.logger import get_logger

logger = get_logger(__name__)


async def run_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Execute all sweep runs for a pre-created experiment."""
    runs = expand_sweep(config)
    run_ids: list[str] = []
    logger.info(f"Experiment {experiment_id}: {len(runs)} runs to execute")

    failed = 0
    for params in runs:
        run_id = str(uuid.uuid4())
        run_ids.append(run_id)
        try:
            await run_single(experiment_id, run_id, params)
        except Exception as e:
            failed += 1
            logger.error(f"Run {run_id} failed: {e}")
            if config.execution.on_error == "stop":
                break

    final_status = "complete" if failed == 0 else "partial" if failed < len(runs) else "failed"
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": {"status": final_status, "run_count": len(runs), "failed_count": failed}},
    )
    logger.info(f"Experiment {experiment_id} finished: {final_status}")

    return {"experiment_id": experiment_id, "run_ids": run_ids, "status": final_status}


async def run_single(experiment_id: str, run_id: str, params: RunParams) -> None:
    """Execute one run of the pipeline for a single parameter combination."""
    logger.info(
        f"Run {run_id}: {params.embedding_model} / {params.chunking_method.value} "
        f"/ {params.chunk_size}+{params.overlap} / {params.retrieval_method.value}"
    )

    run_status = RunStatus(
        run_id=run_id,
        experiment_id=experiment_id,
        phase=Phase.QUEUED,
        embedding_model=params.embedding_model,
        chunking_method=params.chunking_method,
        chunk_size=params.chunk_size,
        overlap=params.overlap,
        retrieval_method=params.retrieval_method,
    )
    get_collection(RUN_STATUS_COLLECTION).insert_one(run_status.model_dump())

    try:
        _update_phase(run_id, Phase.PARSING)
        text = parse_pdf(params.pdf_path)

        _update_phase(run_id, Phase.CHUNKING)
        chunks = chunk_text(text, params.chunking_method, params.chunk_size, params.overlap)

        _update_phase(run_id, Phase.EMBEDDING)
        embeddings = embed_documents(chunks, params.embedding_model)

        _update_phase(run_id, Phase.STORING)
        chunk_docs = [
            {
                "chunk_id": f"{run_id}_{i}",
                "experiment_id": experiment_id,
                "run_id": run_id,
                "text": chunk,
                "index": i,
                "embedding": emb,
                "embedding_model": params.embedding_model,
                "chunk_method": params.chunking_method.value,
                "chunk_size": params.chunk_size,
                "overlap": params.overlap,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        get_collection(CHUNKS_COLLECTION).insert_many(chunk_docs)
        logger.info(f"Stored {len(chunk_docs)} chunks")

        _update_phase(run_id, Phase.QUERYING)
        queries = load_queries(params.queries_file)

        for q in queries:
            query_id = str(uuid.uuid4())
            query_embedding = embed_query(q.text, params.embedding_model)
            search_results = dense_search(
                query_embedding,
                experiment_id,
                params.embedding_model,
                top_k=params.top_k_initial,
            )

            if params.rerank_model:
                _update_phase(run_id, Phase.RERANKING)
                search_results = rerank_results(
                    query=q.text,
                    search_results=search_results,
                    model=params.rerank_model,
                    top_k=params.top_k_final,
                )
            else:
                search_results = search_results[: params.top_k_final]

            query_result = QueryResult(
                query_id=query_id,
                experiment_id=experiment_id,
                run_id=run_id,
                query_text=q.text,
                persona_id=q.persona_id,
                focus=q.focus,
                results=search_results,
                top_k=len(search_results),
            )
            get_collection(RESULTS_COLLECTION).insert_one(query_result.model_dump())

        logger.info(f"Run {run_id}: processed {len(queries)} queries")

        _update_phase(run_id, Phase.COMPLETE)

    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        _update_phase(run_id, Phase.FAILED, error_message=str(e))
        raise


_run_start_times: dict[str, float] = {}


def _update_phase(run_id: str, phase: Phase, error_message: str | None = None) -> None:
    """Update run_status phase and elapsed_ms in MongoDB."""
    now = time.monotonic()
    if run_id not in _run_start_times:
        _run_start_times[run_id] = now

    elapsed_ms = int((now - _run_start_times[run_id]) * 1000)
    logger.info(f"Run {run_id} → {phase.value} ({elapsed_ms}ms)")

    update: dict = {
        "phase": phase.value,
        "updated_at": datetime.utcnow(),
        "elapsed_ms": elapsed_ms,
        "error_message": error_message,
    }
    get_collection(RUN_STATUS_COLLECTION).update_one(
        {"run_id": run_id}, {"$set": update}
    )

    if phase in (Phase.COMPLETE, Phase.FAILED, Phase.INTERRUPTED):
        _run_start_times.pop(run_id, None)
