"""Cross-store compare: group like-for-like runs and rank each group (Slice 66).

Pure logic, no I/O. A *group* is "same dataset + same questions + same config, ignoring the
vector store", so a Redis run and a MongoDB run of the same config land together. Each group is
scored by one ``analyze_results`` call, so scores are min-max normalised **within** the group and
never compared across different datasets or question sets.

The grouping rule is the one used by ``scripts/walkthru/export_walkthru_results.py``; Slice 65C
retires that script in favour of this module.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from server.core.results_analyzer import _run_config_key, analyze_results

ELIGIBLE_STATUSES = ("complete", "partial")

# (experiment doc, its run_status docs, its result docs)
ExperimentBundle = tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class _Candidate:
    run: dict[str, Any]
    experiment: dict[str, Any]
    store: str
    group_id: str
    stamp: float

    @property
    def run_id(self) -> str:
        return str(self.run["run_id"])


def _config(experiment: dict[str, Any]) -> dict[str, Any]:
    config = experiment.get("config")
    return config if isinstance(config, dict) else {}


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None


def _stamp(experiment: dict[str, Any]) -> float:
    value = experiment.get("completed_at") or experiment.get("created_at")
    return value.timestamp() if isinstance(value, datetime) else 0.0


def group_id_for(run: dict[str, Any], experiment: dict[str, Any], questions_sha: str) -> str:
    """Stable id for 'same dataset + questions + config', ignoring the store."""
    config = _config(experiment)
    data_paths = config.get("data_paths") or experiment.get("data_paths") or []
    queries_file = config.get("queries_file") or experiment.get("queries_file") or ""
    config_key = list(_run_config_key({**run, "database_provider": ""})[1:])
    payload = [config_key, list(data_paths), queries_file, questions_sha]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


def _candidates(bundle: ExperimentBundle, sha_of: Callable[[str], str]) -> list[_Candidate]:
    experiment, runs, results = bundle
    if experiment.get("status") not in ELIGIBLE_STATUSES:
        return []
    with_results = {str(r.get("run_id")) for r in results}
    queries_file = str(
        _config(experiment).get("queries_file") or experiment.get("queries_file") or ""
    )
    questions_sha = sha_of(queries_file) if queries_file else ""
    found: list[_Candidate] = []
    for run in runs:
        store = run.get("database_provider") or _config(experiment).get("database_provider")
        if run.get("phase") != "complete" or not store or str(run["run_id"]) not in with_results:
            continue
        run = {**run, "database_provider": str(store)}
        try:
            gid = group_id_for(run, experiment, questions_sha)
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        found.append(_Candidate(run, experiment, str(store), gid, _stamp(experiment)))
    return found


def _latest_per_store_and_group(candidates: Iterable[_Candidate]) -> list[_Candidate]:
    """One run per (store, group): the most recent experiment's (ties: lowest run id).

    Runs in one slot share the same config key, so keeping more than one would merge their scores.
    """
    slots: dict[tuple[str, str], list[_Candidate]] = defaultdict(list)
    for cand in candidates:
        slots[(cand.store, cand.group_id)].append(cand)
    return [min(members, key=lambda c: (-c.stamp, c.run_id)) for members in slots.values()]


def count_duplicates_collapsed(slot_keys: Iterable[tuple[str, str]]) -> int:
    """Rows removed by the one-run-per-(store, group) rule: total keys minus distinct keys."""
    keys = list(slot_keys)
    return len(keys) - len(set(keys))


def _rank_group(
    members: list[_Candidate], results_by_run: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """One analyze_results call over a group; returns its runs best first."""
    members = sorted(members, key=lambda c: c.run_id)  # deterministic tie order
    run_docs = [c.run for c in members]
    query_results = [qr for c in members for qr in results_by_run[c.run_id]]
    ranked = analyze_results(query_results, run_docs)["ranked_configs"]
    by_key = {tuple(_run_config_key(c.run)): c for c in members}
    runs: list[dict[str, Any]] = []
    per_store: dict[str, int] = defaultdict(int)
    for position, entry in enumerate(ranked, start=1):
        cand = by_key[
            (
                entry["database_provider"],
                entry["embedding_provider"],
                entry["embedding_model"],
                entry["chunking_method"],
                entry["chunk_size"],
                entry["overlap"],
                entry["padding"],
                entry["retrieval_method"],
                entry["rerank_provider"],
                entry["retrieval_model"] or "",
            )
        ]
        per_store[cand.store] += 1
        run = cand.run
        runs.append(
            {
                "run_id": cand.run_id,
                "experiment_id": cand.experiment["experiment_id"],
                "experiment_name": cand.experiment.get("experiment_name"),
                "store": cand.store,
                "group_id": cand.group_id,
                "rank": position,
                "store_rank": per_store[cand.store],
                "roles": [],
                "embedding_provider": entry["embedding_provider"],
                "embedding_model": entry["embedding_model"],
                "embedding_dimensions": run.get("embedding_dimensions"),
                "chunking_method": entry["chunking_method"],
                "chunk_size": entry["chunk_size"],
                "overlap": entry["overlap"],
                "padding": entry["padding"],
                "retrieval_method": entry["retrieval_method"],
                "retrieval_model": entry["retrieval_model"],
                "rerank_provider": entry["rerank_provider"],
                "max_score": entry["max_score"],
                "avg_score": entry["avg_score"],
                "query_avg_score": entry["query_avg_score"],
                "result_count": entry["result_count"],
                "phase": run.get("phase"),
                "elapsed_ms": run.get("elapsed_ms") or 0,
                "created_at": _iso(run.get("created_at")),
                "updated_at": _iso(run.get("updated_at")),
                "top_results": [],
            }
        )
    return runs


def build_compare(
    bundles: Iterable[ExperimentBundle], sha_of: Callable[[str], str] = lambda _path: ""
) -> dict[str, Any]:
    """Group, dedupe and rank. Groups come back best first (by their top run's max_score)."""
    bundle_list = list(bundles)
    results_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for _experiment, _runs, results in bundle_list:
        for qr in results:
            results_by_run[str(qr.get("run_id"))].append(qr)
    candidates = [c for b in bundle_list for c in _candidates(b, sha_of)]
    duplicates_collapsed = count_duplicates_collapsed((c.store, c.group_id) for c in candidates)
    by_group: dict[str, list[_Candidate]] = defaultdict(list)
    for cand in _latest_per_store_and_group(candidates):
        by_group[cand.group_id].append(cand)
    ranked_groups = [(gid, _rank_group(m, results_by_run)) for gid, m in by_group.items()]
    # A run whose queries retrieved nothing has no score, so it never reaches the ranking.
    groups: list[dict[str, Any]] = [
        {"group_id": gid, "runs": runs} for gid, runs in ranked_groups if runs
    ]
    groups.sort(key=lambda g: (-g["runs"][0]["max_score"], g["group_id"]))
    stores = sorted({run["store"] for g in groups for run in g["runs"]})
    return {
        "groups": groups,
        "stores": stores,
        "group_count": len(groups),
        "run_count": sum(len(g["runs"]) for g in groups),
        "cross_store_group_count": sum(
            1 for g in groups if len({r["store"] for r in g["runs"]}) > 1
        ),
        "duplicates_collapsed": duplicates_collapsed,
    }
