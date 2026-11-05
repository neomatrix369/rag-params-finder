#!/usr/bin/env python3
"""Export bundled demo data for the meetup About box / replay / leaderboard (SLICE-56 Part A).

Reads run state from one or more SQLite files (read-only), picks the Redis runs plus the
same-config runs on every other store, ranks the union with ``analyze_results`` exactly once,
and writes one deterministic JSON file for the frontend to bundle.

Usage:
    uv run python scripts/demo/export_demo_results.py \\
        --db data/run_state.db --db /scratch/volume_run_state.db \\
        --questions configs/questions.example.json \\
        --out docs/about/demo-results.json

    # Docker run state lives in a named volume: copy it out first, never write into the volume
    docker cp rag-params-finder-server:/app/data/run_state.db /scratch/volume_run_state.db

Selection rule (also written to the manifest):
    1. Only runs in phase ``complete`` of experiments with status ``complete`` whose
       ``queries_file`` has the same file name as ``--questions``.
    2. Store = ``run.database_provider``, else the experiment's ``config.database_provider``.
    3. Per (store, config key) the latest completed experiment wins (ties: lowest run id).
    4. Every Redis run is exported, plus every other store's run that shares a Redis config key
       (same dataset, questions file and config; ``database_provider`` is the only difference).
    5. Per store the best / median ``floor((n-1)/2)`` / worst run is marked in ``stores``.

Exit codes: 0 ok, 1 no exportable Redis run (or bad input), 2 over the size cap (nothing is
written and no run is dropped — supply a selection rule or raise the cap).

The exporter reads run state only: it never imports or contacts a vector store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from server.core.results_analyzer import _run_config_key, analyze_results
from server.db.sqlite.sqlite_docs import (
    experiment_row_to_doc,
    result_row_to_doc,
    run_row_to_doc,
)
from server.settings import settings

SCHEMA_VERSION = 1
PRIMARY_STORE = "redis"
DEFAULT_OUT = "docs/about/demo-results.json"
DEFAULT_MAX_RUNS = 600
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
CHUNK_TEXT_MAX = 200
TOP_RESULTS_PER_RUN = 5
STORY_CHUNKS = 3

SELECTION_RULE = (
    "Completed runs of completed experiments whose queries_file name matches --questions; "
    "store = run.database_provider else experiment config.database_provider; per (store, "
    "config key) the latest completed experiment wins (ties: lowest run id); every "
    f"{PRIMARY_STORE} run is exported plus every other store's run sharing a {PRIMARY_STORE} "
    "config key (same dataset, questions file and config); per store the best, median "
    "floor((n-1)/2) and worst run are marked in stores."
)

EXIT_NO_PRIMARY = 1
EXIT_OVER_CAP = 2

R_DUPLICATE_EXPERIMENT = "duplicate experiment id (an earlier --db already supplied it)"
R_EXPERIMENT_STATUS = "experiment status is not complete"
R_QUESTIONS_FILE = "questions file differs from --questions"
R_RUN_PHASE = "run phase is not complete"
R_NO_STORE = "no store recorded on the run or in the experiment config"
R_BAD_CONFIG = "run config is incomplete"
R_NO_RESULTS = "no results recorded for the run"
R_SUPERSEDED = "superseded by a later experiment for the same store and config"
R_NOT_ON_PRIMARY = (
    f"config not run on the primary store ({PRIMARY_STORE}) with the same dataset and questions"
)


class ExportError(Exception):
    """A user-facing export failure carrying the process exit code."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


# ── Reading run state (read-only) ─────────────────────────────────────────────


@dataclass
class Source:
    """One run-state database: its path plus the rows the exporter needs."""

    path: str
    sha256: str
    conn: sqlite3.Connection
    experiments: list[dict[str, Any]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def open_readonly(path: Path) -> sqlite3.Connection:
    """Open a SQLite file read-only (no schema bootstrap, no WAL switch, no writes)."""
    uri = f"file:{quote(str(path.resolve()))}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def read_source(raw_path: str) -> Source:
    path = Path(raw_path)
    if not path.is_file():
        raise ExportError(f"ERROR: --db file not found: {raw_path}", EXIT_NO_PRIMARY)
    conn = open_readonly(path)
    rows = conn.execute("SELECT * FROM experiments ORDER BY experiment_id").fetchall()
    experiments = [experiment_row_to_doc(dict(r)) for r in rows]
    return Source(raw_path, sha256_file(path), conn, experiments)


def read_runs(source: Source, experiment_id: str) -> list[dict[str, Any]]:
    rows = source.conn.execute(
        "SELECT * FROM run_status WHERE experiment_id = ? ORDER BY run_id", (experiment_id,)
    ).fetchall()
    return [run_row_to_doc(dict(r)) for r in rows]


def read_result_counts(source: Source, experiment_id: str) -> dict[str, int]:
    rows = source.conn.execute(
        "SELECT run_id, COUNT(*) FROM results WHERE experiment_id = ? GROUP BY run_id",
        (experiment_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def read_results(source: Source, experiment_id: str, run_ids: set[str]) -> list[dict[str, Any]]:
    rows = source.conn.execute(
        "SELECT * FROM results WHERE experiment_id = ? ORDER BY run_id, query_id", (experiment_id,)
    ).fetchall()
    return [d for d in (result_row_to_doc(dict(r)) for r in rows) if d["run_id"] in run_ids]


def load_questions(path: Path) -> tuple[dict[str, str], str]:
    """Return ({question text: focus}, sha256) for the questions file."""
    if not path.is_file():
        raise ExportError(f"ERROR: --questions file not found: {path}", EXIT_NO_PRIMARY)
    data = json.loads(path.read_text(encoding="utf-8"))
    focus: dict[str, str] = {}
    for persona in data.get("personas", []):
        for question in persona.get("questions", []):
            focus.setdefault(question["text"], question.get("focus", ""))
    return focus, sha256_file(path)


# ── Candidates and exclusions ─────────────────────────────────────────────────


class Exclusions:
    """Collects (scope, reason) -> ids so nothing is dropped without a recorded reason."""

    def __init__(self) -> None:
        self._ids: dict[tuple[str, str], list[str]] = defaultdict(list)

    def add(self, scope: str, reason: str, item_id: str) -> None:
        self._ids[(scope, reason)].append(item_id)

    def as_list(self) -> list[dict[str, Any]]:
        return [
            {"scope": scope, "reason": reason, "count": len(ids), "ids": sorted(ids)}
            for (scope, reason), ids in sorted(self._ids.items())
        ]


@dataclass
class Candidate:
    """A completed run that passed the per-run checks, with its grouping facts."""

    run: dict[str, Any]
    experiment: dict[str, Any]
    source: Source
    store: str
    group_id: str
    pick_key: tuple[float, str]
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def run_id(self) -> str:
        return str(self.run["run_id"])


def _as_utc(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).timestamp()


def _experiment_config(experiment: dict[str, Any]) -> dict[str, Any]:
    config = experiment.get("config")
    return config if isinstance(config, dict) else {}


def provider_less_key(run: dict[str, Any]) -> tuple[Any, ...]:
    """The analyzer's config key without ``database_provider`` (composed, not copied)."""
    return tuple(_run_config_key({**run, "database_provider": ""})[1:])


def group_id_for(run: dict[str, Any], experiment: dict[str, Any], questions_sha: str) -> str:
    """Stable id for 'same dataset + questions + config', ignoring the store."""
    config = _experiment_config(experiment)
    data_paths = config.get("data_paths") or experiment.get("data_paths") or []
    queries_file = config.get("queries_file") or experiment.get("queries_file") or ""
    payload = [list(provider_less_key(run)), list(data_paths), queries_file, questions_sha]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


def _eligible_experiments(
    sources: list[Source], questions_name: str, exclusions: Exclusions
) -> list[tuple[Source, dict[str, Any]]]:
    seen: set[str] = set()
    eligible: list[tuple[Source, dict[str, Any]]] = []
    for source in sources:
        for exp in source.experiments:
            exp_id = str(exp["experiment_id"])
            if exp_id in seen:
                exclusions.add("experiment", R_DUPLICATE_EXPERIMENT, exp_id)
                continue
            seen.add(exp_id)
            queries_file = _experiment_config(exp).get("queries_file") or exp.get("queries_file")
            if exp.get("status") != "complete":
                exclusions.add("experiment", R_EXPERIMENT_STATUS, exp_id)
            elif Path(str(queries_file or "")).name != questions_name:
                exclusions.add("experiment", R_QUESTIONS_FILE, exp_id)
            else:
                eligible.append((source, exp))
    return eligible


def _candidates_for(
    source: Source,
    experiment: dict[str, Any],
    questions_sha: str,
    exclusions: Exclusions,
) -> list[Candidate]:
    exp_id = str(experiment["experiment_id"])
    with_results = read_result_counts(source, exp_id)
    stamp = _as_utc(experiment.get("completed_at") or experiment.get("created_at"))
    found: list[Candidate] = []
    for run in read_runs(source, exp_id):
        run_id = str(run["run_id"])
        store = run.get("database_provider") or _experiment_config(experiment).get(
            "database_provider"
        )
        if run.get("phase") != "complete":
            exclusions.add("run", R_RUN_PHASE, run_id)
        elif not store:
            exclusions.add("run", R_NO_STORE, run_id)
        elif run_id not in with_results:
            exclusions.add("run", R_NO_RESULTS, run_id)
        else:
            run = {**run, "database_provider": str(store)}
            try:
                gid = group_id_for(run, experiment, questions_sha)
            except (KeyError, TypeError, ValueError, IndexError):
                exclusions.add("run", R_BAD_CONFIG, run_id)
                continue
            found.append(Candidate(run, experiment, source, str(store), gid, (-stamp, run_id)))
    return found


def collect_candidates(
    sources: list[Source], questions_name: str, questions_sha: str, exclusions: Exclusions
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for source, experiment in _eligible_experiments(sources, questions_name, exclusions):
        candidates += _candidates_for(source, experiment, questions_sha, exclusions)
    return candidates


def select_candidates(candidates: list[Candidate], exclusions: Exclusions) -> list[Candidate]:
    """Latest experiment per (store, config group), then primary runs + their same-config peers."""
    by_slot: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for cand in candidates:
        by_slot[(cand.store, cand.group_id)].append(cand)
    latest: list[Candidate] = []
    for slot in sorted(by_slot):
        ordered = sorted(by_slot[slot], key=lambda c: c.pick_key)
        latest.append(ordered[0])
        for loser in ordered[1:]:
            exclusions.add("run", R_SUPERSEDED, loser.run_id)
    primary_groups = {c.group_id for c in latest if c.store == PRIMARY_STORE}
    selected: list[Candidate] = []
    for cand in latest:
        if cand.group_id in primary_groups:
            selected.append(cand)
        else:
            exclusions.add("run", R_NOT_ON_PRIMARY, cand.run_id)
    return sorted(selected, key=lambda c: (c.store, c.group_id, c.run_id))


# ── Ranking (one analyze_results call over the union) ─────────────────────────


def _ranked_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    """Rebuild the analyzer config key from a ranked_configs entry."""
    return (
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


def _tie_signature(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry["max_score"],
        entry["query_avg_score"],
        entry["avg_score"],
        entry["chunk_size"],
        entry["overlap"],
        entry["padding"],
    )


def apply_run_id_tiebreak(
    ranked: list[tuple[dict[str, Any], Candidate]],
) -> list[tuple[dict[str, Any], Candidate]]:
    """Order fully tied configs by run id (analyze_results leaves that order to input order)."""
    out: list[tuple[dict[str, Any], Candidate]] = []
    block: list[tuple[dict[str, Any], Candidate]] = []
    for item in ranked:
        if block and _tie_signature(block[0][0]) != _tie_signature(item[0]):
            out += sorted(block, key=lambda pair: pair[1].run_id)
            block = []
        block.append(item)
    return out + sorted(block, key=lambda pair: pair[1].run_id)


def rank_union(selected: list[Candidate]) -> tuple[list[tuple[dict[str, Any], Candidate]], dict]:
    """Call analyze_results once over the union; return (ranked entry, candidate) and analysis."""
    by_exp: dict[str, tuple[Source, set[str]]] = {}
    for cand in selected:
        exp_id = str(cand.experiment["experiment_id"])
        by_exp.setdefault(exp_id, (cand.source, set()))[1].add(cand.run_id)
    query_results: list[dict[str, Any]] = []
    for exp_id in sorted(by_exp):
        source, run_ids = by_exp[exp_id]
        query_results += read_results(source, exp_id, run_ids)
    query_results.sort(key=lambda d: (d["run_id"], d["query_id"]))
    # The analyzer's config key has no dataset. Fold the group id (dataset + questions + config)
    # into the provider slot so same-store, same-config runs on different datasets stay apart.
    run_docs = [{**c.run, "database_provider": f"{c.store}#{c.group_id}"} for c in selected]
    analysis = analyze_results(query_results, run_docs)
    lookup = {tuple(_run_config_key(doc)): c for doc, c in zip(run_docs, selected, strict=True)}
    ranked = [(entry, lookup[_ranked_key(entry)]) for entry in analysis["ranked_configs"]]
    return apply_run_id_tiebreak(ranked), analysis


# ── Output assembly ───────────────────────────────────────────────────────────


def clip_text(text: str) -> str:
    """Collapse whitespace and cut to CHUNK_TEXT_MAX characters (ellipsis included)."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= CHUNK_TEXT_MAX else flat[: CHUNK_TEXT_MAX - 1] + "…"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def rows_by_run(analysis: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in analysis["detailed_results"]:
        grouped[row["run_id"]].append(row)
    return grouped


def top_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best row per question, highest scores first, at most TOP_RESULTS_PER_RUN."""
    seen: set[str] = set()
    picked: list[dict[str, Any]] = []
    for row in rows:
        if row["query_text"] in seen:
            continue
        seen.add(row["query_text"])
        picked.append(
            {
                "query_text": row["query_text"],
                "score": row["score"],
                "raw_score": row["raw_score"],
                "chunk_text": clip_text(row["chunk_text"]),
                "retrieval_method": row["retrieval_method"],
            }
        )
        if len(picked) == TOP_RESULTS_PER_RUN:
            break
    return picked


def store_summary(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per store: run count and best / median floor((n-1)/2) / worst; marks ``roles`` on runs."""
    per_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        per_store[run["store"]].append(run)
    summary: dict[str, dict[str, Any]] = {}
    for store in sorted(per_store):
        ordered = per_store[store]
        picks = {
            "best": ordered[0],
            "median": ordered[(len(ordered) - 1) // 2],
            "worst": ordered[-1],
        }
        for index, run in enumerate(ordered, start=1):
            run["store_rank"] = index
        for role, run in picks.items():
            run["roles"].append(role)
        summary[store] = {
            "is_primary": store == PRIMARY_STORE,
            "run_count": len(ordered),
            **{f"{role}_run_id": run["run_id"] for role, run in picks.items()},
        }
    return summary


def build_runs(
    ranked: list[tuple[dict[str, Any], Candidate]], analysis: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = rows_by_run(analysis)
    runs: list[dict[str, Any]] = []
    for position, (entry, cand) in enumerate(ranked, start=1):
        run = cand.run
        runs.append(
            {
                "run_id": cand.run_id,
                "experiment_id": cand.experiment["experiment_id"],
                "experiment_name": cand.experiment.get("experiment_name"),
                "store": cand.store,
                "group_id": cand.group_id,
                "rank": position,
                "store_rank": 0,
                "roles": [],
                "embedding_provider": entry["embedding_provider"],
                "embedding_model": entry["embedding_model"],
                "chunking_method": entry["chunking_method"],
                "chunk_size": entry["chunk_size"],
                "overlap": entry["overlap"],
                "padding": entry["padding"],
                "retrieval_method": entry["retrieval_method"],
                "rerank_provider": entry["rerank_provider"],
                "retrieval_model": entry["retrieval_model"],
                "max_score": entry["max_score"],
                "avg_score": entry["avg_score"],
                "query_avg_score": entry["query_avg_score"],
                "result_count": entry["result_count"],
                "phase": run.get("phase"),
                "elapsed_ms": run.get("elapsed_ms"),
                "created_at": _iso(run.get("created_at")),
                "updated_at": _iso(run.get("updated_at")),
                "embedding_dimensions": run.get("embedding_dimensions"),
                "top_results": top_results(rows.get(cand.run_id, [])),
            }
        )
    return runs


def _score_line(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "rank": run["rank"],
        "max_score": run["max_score"],
        "query_avg_score": run["query_avg_score"],
        "avg_score": run["avg_score"],
    }


def _top_chunks(rows: list[dict[str, Any]], run_id: str, question: str) -> list[dict[str, Any]]:
    mine = [r for r in rows if r["query_text"] == question]
    return [
        {
            "run_id": run_id,
            "position": i,
            "score": r["score"],
            "raw_score": r["raw_score"],
            "chunk_text": clip_text(r["chunk_text"]),
        }
        for i, r in enumerate(mine[:STORY_CHUNKS], start=1)
    ]


def _top1(rows: list[dict[str, Any]]) -> dict[str, int]:
    best: dict[str, int] = {}
    for row in rows:
        best[row["query_text"]] = max(best.get(row["query_text"], row["score"]), row["score"])
    return best


def build_story(
    runs: list[dict[str, Any]], analysis: dict[str, Any], focus: dict[str, str]
) -> dict[str, Any]:
    """Best vs median vs worst Redis run, plus the question where the top-1 gap is widest."""
    primary = [r for r in runs if r["store"] == PRIMARY_STORE]
    best, median, worst = primary[0], primary[(len(primary) - 1) // 2], primary[-1]
    rows = rows_by_run(analysis)
    best_top1, worst_top1 = _top1(rows[best["run_id"]]), _top1(rows[worst["run_id"]])
    shared = sorted(set(best_top1) & set(worst_top1))
    question: dict[str, Any] | None = None
    best_chunks: list[dict[str, Any]] = []
    worst_chunks: list[dict[str, Any]] = []
    if shared:
        text = min(shared, key=lambda q: (-(best_top1[q] - worst_top1[q]), q))
        question = {
            "text": text,
            "focus": focus.get(text, ""),
            "best_top1": best_top1[text],
            "worst_top1": worst_top1[text],
            "gap": best_top1[text] - worst_top1[text],
        }
        best_chunks = _top_chunks(rows[best["run_id"]], best["run_id"], text)
        worst_chunks = _top_chunks(rows[worst["run_id"]], worst["run_id"], text)
    return {
        "basis": (
            f"{PRIMARY_STORE} runs only; similarity scores normalised across this export; "
            "not a correctness measure"
        ),
        "run_count": len(primary),
        "best": _score_line(best),
        "median": _score_line(median),
        "worst": _score_line(worst),
        "spread": {
            "max_score": best["max_score"] - worst["max_score"],
            "query_avg_score": best["query_avg_score"] - worst["query_avg_score"],
        },
        "question": question,
        "best_top_chunks": best_chunks,
        "worst_top_chunks": worst_chunks,
    }


def build_manifest(
    sources: list[Source],
    questions_path: str,
    questions_sha: str,
    exclusions: Exclusions,
    counts: dict[str, int],
) -> dict[str, Any]:
    avg_field = "query_avg_score" if settings.tiebreaker_metric == "query_avg" else "avg_score"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/demo/export_demo_results.py",
        "inputs": {
            "databases": [{"path": s.path, "sha256": s.sha256} for s in sources],
            "questions": {"path": questions_path, "sha256": questions_sha},
        },
        "ranking": {
            "fields": [
                "max_score DESC",
                f"{avg_field} DESC",
                "chunk_size ASC",
                "overlap ASC",
                "padding ASC",
                "run_id ASC",
            ],
            "source": "server.core.results_analyzer.analyze_results, called once over the export",
            "score": (
                "similarity score (rerank_score if present, else dense_score), min-max "
                "normalised to 0-100 across this export; not a correctness measure"
            ),
            "tiebreak_note": "run_id ASC is the exporter's own final tie-break",
        },
        "selection_rule": SELECTION_RULE,
        "counts": counts,
        "exclusions": exclusions.as_list(),
    }


def build_export(
    db_paths: list[str], questions_path: str, max_runs: int
) -> tuple[dict[str, Any], str]:
    """Return (payload, printed story question line); raises ExportError on stop conditions."""
    focus, questions_sha = load_questions(Path(questions_path))
    sources = [read_source(p) for p in db_paths]
    exclusions = Exclusions()
    candidates = collect_candidates(sources, Path(questions_path).name, questions_sha, exclusions)
    selected = select_candidates(candidates, exclusions)
    if not any(c.store == PRIMARY_STORE for c in selected):
        raise ExportError(
            f"ERROR: no exportable {PRIMARY_STORE} run found in {len(sources)} database(s) "
            f"({len(candidates)} completed runs checked). Run the {PRIMARY_STORE} sweep first, "
            "or pass its run-state file with another --db.",
            EXIT_NO_PRIMARY,
        )
    if len(selected) > max_runs:
        raise ExportError(
            f"STOP: the export would hold {len(selected)} runs (cap {max_runs}). Nothing was "
            "written and no run was dropped. Supply a selection rule (narrow the --db inputs) "
            "or raise --max-runs.",
            EXIT_OVER_CAP,
        )
    ranked, analysis = rank_union(selected)
    runs = build_runs(ranked, analysis)
    stores = store_summary(runs)
    story = build_story(runs, analysis, focus)
    counts = {
        "experiments_read": sum(len(s.experiments) for s in sources),
        "runs_exported": len(runs),
        "stores": len(stores),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "manifest": build_manifest(sources, questions_path, questions_sha, exclusions, counts),
        "stores": stores,
        "runs": runs,
        "story": story,
    }
    for source in sources:
        source.conn.close()
    q = story["question"]
    line = (
        f'Improvement story question (confirm or swap): "{q["text"]}" '
        f"[{q['focus']}] top-1 gap {q['gap']} ({q['worst_top1']} -> {q['best_top1']})"
        if q
        else "Improvement story: best and worst runs share no question; none chosen."
    )
    return payload, line


def serialize(payload: dict[str, Any]) -> str:
    """Deterministic JSON: sorted keys, fixed indent, trailing newline."""
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db",
        action="append",
        required=True,
        help="Run-state SQLite file (repeat for a union, e.g. host DB + docker-cp'd volume DB)",
    )
    parser.add_argument("--questions", required=True, help="Questions JSON used by the sweeps")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output path (default {DEFAULT_OUT})")
    parser.add_argument("--max-runs", type=int, default=DEFAULT_MAX_RUNS, help="Run-count cap")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Output size cap")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload, story_line = build_export(args.db, args.questions, args.max_runs)
        text = serialize(payload)
        size = len(text.encode("utf-8"))
        if size > args.max_bytes:
            raise ExportError(
                f"STOP: the export would be {size} bytes (cap {args.max_bytes}). Nothing was "
                "written and no run was dropped. Supply a selection rule (narrow the --db "
                "inputs) or raise --max-bytes.",
                EXIT_OVER_CAP,
            )
    except ExportError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    per_store = ", ".join(f"{s}={v['run_count']}" for s, v in payload["stores"].items())
    print(f"Wrote {out} ({size} bytes, {len(payload['runs'])} runs: {per_store})")
    print(story_line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
