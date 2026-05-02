import uuid
from datetime import datetime
from server.core.pdf_parser import parse_pdf
from server.core.chunkers import chunk_text
from server.core.embedder import embed_documents, embed_query
from server.core.retriever import dense_search
from server.models.config import ExperimentConfig
from server.models.enums import Phase, ChunkingMethod, RetrievalMethod
from server.models.status import RunStatus
from server.models.results import QueryResult
from server.db.atlas import (
    get_collection,
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    RESULTS_COLLECTION,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)


async def run_experiment(config: ExperimentConfig) -> dict:
    """
    Orchestrate a single experiment run.
    For Slice 1: one run only (no sweep expansion).
    """

    experiment_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    logger.info(f"Starting experiment {experiment_id}, run {run_id}")

    # Extract config (single values for Slice 1)
    embedding_model = config.embedding.models[0]
    chunking_method = config.chunking.methods[0]
    chunk_size = config.chunking.params.chunk_sizes[0]
    overlap = config.chunking.params.overlaps[0]
    retrieval_method = config.retrieval.methods[0]

    # Create experiment doc
    experiment_doc = {
        "_id": experiment_id,
        "experiment_id": experiment_id,
        "experiment_name": config.experiment_name,
        "config": config.model_dump(),
        "created_at": datetime.utcnow(),
        "status": "running"
    }
    get_collection(EXPERIMENTS_COLLECTION).insert_one(experiment_doc)

    # Create run_status doc
    run_status = RunStatus(
        run_id=run_id,
        experiment_id=experiment_id,
        phase=Phase.QUEUED,
        embedding_model=embedding_model,
        chunking_method=chunking_method,
        chunk_size=chunk_size,
        overlap=overlap,
        retrieval_method=retrieval_method
    )
    get_collection(RUN_STATUS_COLLECTION).insert_one(run_status.model_dump())

    try:
        # PHASE: PARSING
        update_phase(run_id, Phase.PARSING)
        text = parse_pdf(config.pdf_path)

        # PHASE: CHUNKING
        update_phase(run_id, Phase.CHUNKING)
        chunks = chunk_text(text, chunking_method, chunk_size, overlap)

        # PHASE: EMBEDDING
        update_phase(run_id, Phase.EMBEDDING)
        embeddings = embed_documents(chunks, embedding_model)

        # PHASE: STORING
        update_phase(run_id, Phase.STORING)
        chunk_docs = []
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_doc = {
                "chunk_id": f"{run_id}_{i}",
                "experiment_id": experiment_id,
                "run_id": run_id,
                "text": chunk_text,
                "index": i,
                "embedding": embedding,
                "embedding_model": embedding_model,
                "chunk_method": chunking_method.value,
                "chunk_size": chunk_size,
                "overlap": overlap
            }
            chunk_docs.append(chunk_doc)

        get_collection(CHUNKS_COLLECTION).insert_many(chunk_docs)
        logger.info(f"Stored {len(chunk_docs)} chunks in Atlas")

        # PHASE: QUERYING
        update_phase(run_id, Phase.QUERYING)

        # For Slice 1: hardcoded single query
        query_text = "What is the main topic of this document?"
        query_id = str(uuid.uuid4())

        query_embedding = embed_query(query_text, embedding_model)
        search_results = dense_search(
            query_embedding,
            experiment_id,
            embedding_model,
            top_k=config.retrieval.top_k_final
        )

        # Store query result
        query_result = QueryResult(
            query_id=query_id,
            experiment_id=experiment_id,
            run_id=run_id,
            query_text=query_text,
            persona_id=None,
            focus=None,
            results=search_results,
            top_k=len(search_results)
        )
        get_collection(RESULTS_COLLECTION).insert_one(query_result.model_dump())
        logger.info(f"Stored query results: {len(search_results)} results")

        # PHASE: COMPLETE
        update_phase(run_id, Phase.COMPLETE)
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {"$set": {"status": "complete"}}
        )

        logger.info(f"Experiment {experiment_id} completed successfully")

        return {
            "experiment_id": experiment_id,
            "run_ids": [run_id],
            "status": "submitted"
        }

    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}")
        update_phase(run_id, Phase.FAILED, error_message=str(e))
        get_collection(EXPERIMENTS_COLLECTION).update_one(
            {"_id": experiment_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise


def update_phase(run_id: str, phase: Phase, error_message: str | None = None):
    """Update run_status phase."""
    logger.info(f"Run {run_id} → {phase.value}")
    get_collection(RUN_STATUS_COLLECTION).update_one(
        {"run_id": run_id},
        {
            "$set": {
                "phase": phase.value,
                "updated_at": datetime.utcnow(),
                "error_message": error_message
            }
        }
    )
