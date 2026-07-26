"""Postgres stats and explore helpers, mirroring ``server.db.mongo_stats``.

Postgres-specific aggregation SQL plus the four public query functions
``PostgresStorageBackend`` delegates to. The backend-agnostic assembly maths is
shared with the Mongo adapter via ``server.db.stats_common``.
"""

from __future__ import annotations

from collections.abc import Callable

from server.core.health_check import resolve_storage_mode
from server.db.postgres import fetch_all, fetch_one
from server.db.postgres_docs import (
    experiment_row_to_doc,
    result_row_to_doc,
    run_row_to_doc,
)
from server.db.postgres_uri import parse_postgres_host, postgres_storage_mode
from server.db.stats_common import (
    assemble_experiment_db_stats,
    bytes_to_mb,
    experiment_summary_row,
    finalize_groups,
    merge_group_totals,
    new_vector_db_group,
    normalize_stats_database_provider,
    resolve_experiment_storage_mode,
    vector_db_group_key,
)
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_CHUNKS_TABLE = "chunks"


# ── Postgres-specific helpers ─────────────────────────────────────────────────


def _cluster_host() -> str | None:
    return parse_postgres_host(settings.database_url)


def _cluster_storage_mb() -> dict[str, float | str | None]:
    """Database size split into data and index bytes.

    Neither Supabase nor a local container exposes its storage quota over SQL,
    so the limit-derived fields stay ``None`` and the dashboard renders usage
    without a capacity bar.
    """
    row = fetch_one(
        """
        SELECT pg_database_size(current_database())                    AS total_bytes,
               COALESCE(SUM(pg_indexes_size(c.oid)), 0)                AS index_bytes
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r' AND n.nspname = current_schema()
        """
    ) or {"total_bytes": 0, "index_bytes": 0}
    total_bytes = float(row["total_bytes"] or 0)
    index_bytes = float(row["index_bytes"] or 0)
    mode = postgres_storage_mode(settings.database_url)
    return {
        "database_used_mb": bytes_to_mb(total_bytes),
        "database_data_mb": bytes_to_mb(max(0.0, total_bytes - index_bytes)),
        "database_index_mb": bytes_to_mb(index_bytes),
        "database_storage_limit_mb": None,
        "database_free_mb": None,
        "cluster_tier_type": mode,
        "storage_mode": mode,
    }


def _chunks_index_names() -> list[str]:
    """Indexes currently defined on ``chunks`` — the Postgres analogue of Atlas
    search index names. Read from the catalog so the dashboard reflects what the
    database actually has, including the HNSW indexes Slice 34 adds."""
    rows = fetch_all(
        "SELECT indexname FROM pg_indexes WHERE tablename = %s ORDER BY indexname",
        (_CHUNKS_TABLE,),
    )
    return [row["indexname"] for row in rows]


def _counts_by_key(query: str, params: tuple, key: str) -> dict[str, int]:
    return {str(row[key]): int(row["count"]) for row in fetch_all(query, params) if row[key]}


def _run_breakdown(experiment_id: str) -> list[dict]:
    """Per-run chunk and result counts, full-outer-joined so a run appears when
    it has either."""
    rows = fetch_all(
        """
        SELECT COALESCE(c.run_id, r.run_id)  AS run_id,
               COALESCE(c.chunks, 0)         AS chunks,
               COALESCE(r.results, 0)        AS results
          FROM (SELECT run_id, count(*) AS chunks
                  FROM chunks WHERE experiment_id = %s GROUP BY run_id) c
          FULL OUTER JOIN
               (SELECT run_id, count(*) AS results
                  FROM results WHERE experiment_id = %s GROUP BY run_id) r
            ON c.run_id = r.run_id
         ORDER BY 1
        """,
        (experiment_id, experiment_id),
    )
    return [
        {"run_id": row["run_id"], "chunks": int(row["chunks"]), "results": int(row["results"])}
        for row in rows
    ]


def _assemble(
    experiment: dict | None,
    *,
    total_chunks: int,
    embedding_models: list[str],
    chunking_breakdown: dict[str, int],
    total_results: int,
    unique_queries: int,
    runs_with_data: int,
    run_breakdown: list[dict],
    index_names: list[str],
) -> dict:
    sweep = (experiment or {}).get("sweep_summary") or {}
    return assemble_experiment_db_stats(
        experiment,
        database_provider=normalize_stats_database_provider(
            sweep.get("database_provider"),
            fallback="postgres",
        ),
        collection_name=_CHUNKS_TABLE,
        cluster_host=_cluster_host(),
        index_names=index_names,
        total_chunks=total_chunks,
        embedding_models=embedding_models,
        chunking_breakdown=chunking_breakdown,
        total_results=total_results,
        unique_queries=unique_queries,
        runs_with_data=runs_with_data,
        run_breakdown=run_breakdown,
    )


# ── Public query functions ────────────────────────────────────────────────────


def load_explore_source(experiment_id: str) -> tuple[dict | None, list[dict], list[dict]]:
    """Load experiment, query results, and run statuses for the explore screen."""
    row = fetch_one("SELECT * FROM experiments WHERE experiment_id = %s", (experiment_id,))
    if not row:
        return None, [], []
    results = fetch_all("SELECT * FROM results WHERE experiment_id = %s", (experiment_id,))
    runs = fetch_all("SELECT * FROM run_status WHERE experiment_id = %s", (experiment_id,))
    return (
        experiment_row_to_doc(row),
        [result_row_to_doc(r) for r in results],
        [run_row_to_doc(r) for r in runs],
    )


def list_results_for_experiment(experiment_id: str) -> list[dict]:
    """Return every result document for an experiment, unprojected."""
    rows = fetch_all("SELECT * FROM results WHERE experiment_id = %s", (experiment_id,))
    return [result_row_to_doc(row) for row in rows]


def get_experiment_db_stats(experiment_id: str) -> dict:
    """Compute per-experiment chunk/result/storage statistics."""
    logger.debug("computing db stats — experiment %s", experiment_id)
    try:
        row = fetch_one("SELECT * FROM experiments WHERE experiment_id = %s", (experiment_id,))
        experiment = experiment_row_to_doc(row) if row else None

        chunk_row = fetch_one(
            """
            SELECT count(*)                                  AS total_chunks,
                   COALESCE(array_agg(DISTINCT embedding_model), '{}') AS embedding_models
              FROM chunks WHERE experiment_id = %s
            """,
            (experiment_id,),
        ) or {"total_chunks": 0, "embedding_models": []}
        chunking_breakdown = _counts_by_key(
            "SELECT chunk_method, count(*) AS count FROM chunks "
            "WHERE experiment_id = %s GROUP BY chunk_method",
            (experiment_id,),
            "chunk_method",
        )
        result_row = fetch_one(
            """
            SELECT count(*) AS total_results, count(DISTINCT query_id) AS unique_queries
              FROM results WHERE experiment_id = %s
            """,
            (experiment_id,),
        ) or {"total_results": 0, "unique_queries": 0}
        run_breakdown = _run_breakdown(experiment_id)

        stats = _assemble(
            experiment,
            total_chunks=int(chunk_row["total_chunks"] or 0),
            embedding_models=list(chunk_row["embedding_models"] or []),
            chunking_breakdown=chunking_breakdown,
            total_results=int(result_row["total_results"] or 0),
            unique_queries=int(result_row["unique_queries"] or 0),
            runs_with_data=len(run_breakdown),
            run_breakdown=run_breakdown,
            index_names=_chunks_index_names(),
        )
    except Exception:
        logger.error("db stats compute failed — experiment %s", experiment_id, exc_info=True)
        raise
    logger.debug(
        "db stats ready — experiment %s chunks=%s est_mb=%s",
        experiment_id,
        stats["total_chunks"],
        stats["estimated_storage_mb"],
    )
    return stats


def _bulk_chunk_aggregates() -> dict[str, dict]:
    rows = fetch_all(
        """
        SELECT experiment_id,
               count(*)                              AS total_chunks,
               array_agg(DISTINCT embedding_model)   AS embedding_models,
               count(DISTINCT run_id)                AS runs_with_data
          FROM chunks GROUP BY experiment_id
        """
    )
    return {
        str(row["experiment_id"]): {
            "total_chunks": int(row["total_chunks"]),
            "embedding_models": list(row["embedding_models"] or []),
            "runs_with_data": int(row["runs_with_data"]),
        }
        for row in rows
    }


def _bulk_result_aggregates() -> dict[str, dict]:
    rows = fetch_all(
        """
        SELECT experiment_id,
               count(*)                  AS total_results,
               count(DISTINCT query_id)  AS unique_queries
          FROM results GROUP BY experiment_id
        """
    )
    return {
        str(row["experiment_id"]): {
            "total_results": int(row["total_results"]),
            "unique_queries": int(row["unique_queries"]),
        }
        for row in rows
    }


def _bulk_chunking_breakdown() -> dict[str, dict[str, int]]:
    rows = fetch_all(
        "SELECT experiment_id, chunk_method, count(*) AS count "
        "FROM chunks GROUP BY experiment_id, chunk_method"
    )
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        out.setdefault(str(row["experiment_id"]), {})[str(row["chunk_method"])] = int(row["count"])
    return out


def get_vector_db_stats_grouped(find_all_experiments: Callable[[], list[dict]]) -> dict:
    """Compute grouped vector-db statistics across all experiments.

    ``find_all_experiments`` is injected to avoid a circular dependency on
    ``PostgresStorageBackend``.
    """
    logger.debug("computing grouped vector db stats — all experiments")
    try:
        experiments = find_all_experiments()
        chunk_by_exp = _bulk_chunk_aggregates()
        result_by_exp = _bulk_result_aggregates()
        chunking_by_exp = _bulk_chunking_breakdown()
        cluster_storage = _cluster_storage_mb()
        index_names = _chunks_index_names()
        groups: dict[str, dict] = {}

        for experiment in experiments:
            experiment_id = str(experiment["experiment_id"])
            chunk_row = chunk_by_exp.get(experiment_id) or {}
            result_row = result_by_exp.get(experiment_id) or {}
            stats = _assemble(
                experiment,
                total_chunks=int(chunk_row.get("total_chunks") or 0),
                embedding_models=list(chunk_row.get("embedding_models") or []),
                chunking_breakdown=chunking_by_exp.get(experiment_id, {}),
                total_results=int(result_row.get("total_results") or 0),
                unique_queries=int(result_row.get("unique_queries") or 0),
                runs_with_data=int(chunk_row.get("runs_with_data") or 0),
                run_breakdown=[],
                index_names=index_names,
            )
            group_key = vector_db_group_key(
                resolve_experiment_storage_mode(
                    experiment,
                    fallback_mode=resolve_storage_mode(),
                ),
                stats["cluster_host"],
            )
            if group_key not in groups:
                groups[group_key] = new_vector_db_group(group_key, stats)
            merge_group_totals(groups[group_key], stats)
            groups[group_key]["experiments"].append(
                experiment_summary_row(experiment, experiment_id, stats)
            )

        grouped = finalize_groups(groups, cluster_storage)
    except Exception:
        logger.error("grouped vector db stats failed — aggregation error", exc_info=True)
        raise
    logger.debug(
        "grouped vector db stats ready — %s group(s), %s experiment(s)",
        len(grouped),
        len(experiments),
    )
    return {"groups": grouped}
