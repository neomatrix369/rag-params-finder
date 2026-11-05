#!/usr/bin/env python3
"""Merge two SQLite run-state DBs into one (Slice 65A, DECISIONS #301, option b).

Two run-state files exist today: the host file ``data/run_state.db`` (base) and
the Docker named-volume copy. This script merges whole experiments from the
volume copy *into* a copy of the host DB, producing a single file-to-file
``run_state.merged.db``. Nothing operates on live data — both inputs are the
verified backup copies named by a backup manifest; the originals are never
deleted or overwritten.

Usage:
    # Dry-run (default): report what would move, write nothing
    uv run python scripts/migrate/merge_run_state_dbs.py \
        --backup-manifest ~/backups/rag-params-finder-run-state-YYYYMMDD-HHMMSS

    # Execute the merge into run_state.merged.db
    uv run python scripts/migrate/merge_run_state_dbs.py \
        --backup-manifest ~/backups/... --execute

    # Promote the merged file into place (separate, explicit step)
    uv run python scripts/migrate/merge_run_state_dbs.py --promote --execute

Design (per SLICE-65 65A):
    - Host DB is the base: copied to the merged file with the SQLite backup API.
    - The verified volume copy is ``ATTACH``-ed; whole experiments move in one
      transaction with ``foreign_keys=ON`` via ``INSERT ... SELECT`` (explicit
      column lists, never ``SELECT *``, never the autoincrement ``result_id``).
    - Collision on an ``experiment_id`` present in both: identical content digest
      skips; differing content aborts (uuid4 collisions are impossible, so any
      genuine collision is a hard stop).
    - ``PRAGMA table_info`` parity is asserted for all three tables across host,
      volume and target; an older volume missing a column fails with a clear
      message instead of silently skipping it.
    - Refuses to run without a verified backup manifest (manifest + SHA256SUMS in
      the same folder must verify) and refuses if any experiment is ``running``.
    - Idempotent: the merged file is rebuilt from the host base each execute, so a
      second run with the same inputs yields identical content.
    - No ``--drop-source`` flag; nothing from the existing migrate script's
      source-dropping helpers is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# ── Schema constants ────────────────────────────────────────────────────────────

TABLES: tuple[str, ...] = ("experiments", "run_status", "results")

# Explicit column lists — never SELECT *, and results never carries result_id
# (an autoincrement PK with no natural key, so it must not be copied).
EXPERIMENTS_COLUMNS: tuple[str, ...] = (
    "experiment_id",
    "experiment_name",
    "status",
    "created_at",
    "started_at",
    "completed_at",
    "vector_store_snapshot",
    "doc",
)
RUN_STATUS_COLUMNS: tuple[str, ...] = (
    "run_id",
    "experiment_id",
    "phase",
    "created_at",
    "updated_at",
    "embedding_dimensions",
    "doc",
)
RESULTS_COLUMNS: tuple[str, ...] = (
    "experiment_id",
    "run_id",
    "query_id",
    "query_text",
    "doc",
)

_CHILD_COLUMNS: dict[str, tuple[str, ...]] = {
    "run_status": RUN_STATUS_COLUMNS,
    "results": RESULTS_COLUMNS,
}

# Backup artifacts must never be treated as a merge source.
_EXCLUDED_SOURCE_SUFFIXES: tuple[str, ...] = (".merged.db",)
_EXCLUDED_SOURCE_SUBSTRINGS: tuple[str, ...] = ("_backup",)


class MergeError(RuntimeError):
    """Raised on any precondition failure that must stop the merge."""


# ── Backup manifest verification ─────────────────────────────────────────────────


@dataclass(frozen=True)
class BackupManifest:
    """A verified backup folder: both DB copies hashed and identified."""

    folder: Path
    host_db: Path
    volume_db: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_sha256sums(text: str) -> dict[str, str]:
    """Parse ``<hex>  <name>`` lines into {name: hex}."""
    sums: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        hexd, name = line[:64], line[64:].strip()
        if len(hexd) != 64 or not name:
            raise MergeError(f"malformed SHA256SUMS line: {line!r}")
        sums[name] = hexd
    return sums


def _manifest_db_name(manifest_text: str, section: str) -> str:
    """Read the ``[section] file: <name>`` line from MANIFEST.txt."""
    marker = f"[{section}] file:"
    for line in manifest_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(marker):
            return stripped[len(marker) :].strip()
    raise MergeError(f"MANIFEST.txt has no '{marker}' line")


def verify_backup_manifest(folder: Path) -> BackupManifest:
    """Verify MANIFEST.txt + SHA256SUMS in ``folder`` and locate both DB copies.

    Every file listed in SHA256SUMS must exist in the folder and hash to the
    recorded value, or a MergeError is raised. The host DB is the merge base and
    the volume DB is the source whose experiments are merged in.

    This checks the manifest, SHA256SUMS and file hashes only. It does NOT re-run
    ``PRAGMA integrity_check``: the backups are assumed to have been
    integrity-checked by the backup step (SLICE-65 B1/B2).
    """
    folder = folder.resolve()
    manifest_txt = folder / "MANIFEST.txt"
    sha_file = folder / "SHA256SUMS"
    if not manifest_txt.is_file():
        raise MergeError(f"no MANIFEST.txt in backup folder: {folder}")
    if not sha_file.is_file():
        raise MergeError(f"no SHA256SUMS in backup folder: {folder}")

    sums = _parse_sha256sums(sha_file.read_text())
    if not sums:
        raise MergeError(f"SHA256SUMS is empty: {sha_file}")
    for name, expected in sums.items():
        target = folder / name
        if not target.is_file():
            raise MergeError(f"SHA256SUMS lists a missing file: {name}")
        actual = _sha256_file(target)
        if actual != expected:
            raise MergeError(f"checksum mismatch for {name}: expected {expected}, got {actual}")

    manifest_text = manifest_txt.read_text()
    host_name = _manifest_db_name(manifest_text, "host")
    volume_name = _manifest_db_name(manifest_text, "volume")
    host_db = folder / host_name
    volume_db = folder / volume_name
    for role, path in (("host", host_db), ("volume", volume_db)):
        if not path.is_file():
            raise MergeError(f"manifest {role} DB not found: {path}")
        if path.name not in sums:
            raise MergeError(f"manifest {role} DB {path.name} is not in SHA256SUMS")
        if is_excluded_source(path):
            raise MergeError(f"manifest {role} DB {path.name} is an excluded backup artifact")
    return BackupManifest(folder=folder, host_db=host_db, volume_db=volume_db)


# ── Source scanning helpers ───────────────────────────────────────────────────────


def is_excluded_source(path: Path) -> bool:
    """True when ``path`` is a backup/merged artifact that must not be a source."""
    name = path.name
    if any(name.endswith(suffix) for suffix in _EXCLUDED_SOURCE_SUFFIXES):
        return True
    return any(token in name for token in _EXCLUDED_SOURCE_SUBSTRINGS)


def scan_source_dbs(directory: Path) -> list[Path]:
    """List ``*.db`` files in ``directory`` excluding ``*_backup*`` / ``*.merged.db``."""
    return sorted(
        path for path in directory.glob("*.db") if path.is_file() and not is_excluded_source(path)
    )


# ── SQLite helpers ─────────────────────────────────────────────────────────────────


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Open ``path`` read-only (the originals are never mutated)."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _backup_copy(src: Path, dst: Path) -> None:
    """Copy ``src`` to ``dst`` with the SQLite backup API (safe if src is open)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    source = _connect_ro(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _table_info(conn: sqlite3.Connection, table: str) -> tuple[tuple, ...]:
    """Return the column signature (name, type, notnull, default, pk) for ``table``."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return tuple((r[1], r[2], r[3], r[4], r[5]) for r in rows)


def assert_schema_parity(sources: dict[str, sqlite3.Connection]) -> None:
    """Assert every connection exposes identical columns for all three tables.

    ``sources`` maps a human label (e.g. 'host', 'volume') to a connection.
    Raises MergeError naming the differing columns on the first mismatch.
    Foreign keys and indexes are not compared (FKs are enforced at runtime by
    the merge transaction).
    """
    labels = list(sources)
    reference_label = labels[0]
    for table in TABLES:
        reference = _table_info(sources[reference_label], table)
        ref_names = {col[0] for col in reference}
        for label in labels[1:]:
            other = _table_info(sources[label], table)
            if other == reference:
                continue
            other_names = {col[0] for col in other}
            missing = sorted(ref_names - other_names)
            extra = sorted(other_names - ref_names)
            detail = []
            if missing:
                detail.append(f"missing in {label}: {missing}")
            if extra:
                detail.append(f"extra in {label}: {extra}")
            if not detail:
                detail.append("column type/order/default differs")
            raise MergeError(
                f"schema parity failure on table '{table}' "
                f"({reference_label} vs {label}): {'; '.join(detail)}"
            )


def _experiment_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT experiment_id FROM experiments ORDER BY experiment_id").fetchall()
    return [r[0] for r in rows]


def assert_no_running(conn: sqlite3.Connection, label: str) -> None:
    """Raise MergeError if any experiment in ``conn`` has status='running'."""
    rows = conn.execute(
        "SELECT experiment_id FROM experiments WHERE status = 'running' ORDER BY experiment_id"
    ).fetchall()
    if rows:
        ids = ", ".join(r[0] for r in rows)
        raise MergeError(f"{label} has running experiments (stop the server first): {ids}")


def experiment_content_digest(conn: sqlite3.Connection, experiment_id: str) -> str:
    """Stable content hash of one experiment and its runs/results (no result_id)."""
    digest = hashlib.sha256()
    exp_cols = ", ".join(EXPERIMENTS_COLUMNS)
    exp_row = conn.execute(
        f"SELECT {exp_cols} FROM experiments WHERE experiment_id = ?",  # nosec B608 - columns are module constants
        (experiment_id,),
    ).fetchone()
    digest.update(repr(exp_row).encode())

    run_cols = ", ".join(RUN_STATUS_COLUMNS)
    for row in conn.execute(
        f"SELECT {run_cols} FROM run_status WHERE experiment_id = ? ORDER BY run_id",  # nosec B608 - columns are module constants
        (experiment_id,),
    ):
        digest.update(repr(row).encode())

    res_cols = ", ".join(RESULTS_COLUMNS)
    for row in conn.execute(
        f"SELECT {res_cols} FROM results WHERE experiment_id = ? "  # nosec B608 - columns are module constants
        "ORDER BY run_id, query_id, query_text, doc",
        (experiment_id,),
    ):
        digest.update(repr(row).encode())
    return digest.hexdigest()


def _child_counts(conn: sqlite3.Connection, experiment_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in ("run_status", "results"):
        counts[table] = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE experiment_id = ?",  # noqa: S608  # nosec B608 - columns are module constants
            (experiment_id,),
        ).fetchone()[0]
    return counts


# ── Merge planning + execution ──────────────────────────────────────────────────


@dataclass
class MergeReport:
    """Structured outcome of a merge (dry-run or executed)."""

    dry_run: bool
    merged_path: Path
    host_experiments: list[str]
    moved: list[str]
    skipped: list[str]
    total_experiments: int
    per_experiment_counts: dict[str, dict[str, int]] = field(default_factory=dict)


def _plan_moves(
    base: sqlite3.Connection, volume: sqlite3.Connection
) -> tuple[list[str], list[str]]:
    """Return (to_move, to_skip) comparing volume experiments against the base.

    Collision (same experiment_id in both): an identical content digest means a
    duplicate copy of the same experiment, so it is skipped; a differing digest
    is a genuine collision and a hard stop (ids are uuid4, so this should never
    happen by chance).
    """
    base_ids = set(_experiment_ids(base))
    to_move: list[str] = []
    to_skip: list[str] = []
    for eid in _experiment_ids(volume):
        if eid not in base_ids:
            to_move.append(eid)
            continue
        if experiment_content_digest(base, eid) == experiment_content_digest(volume, eid):
            to_skip.append(eid)
        else:
            raise MergeError(
                f"experiment_id collision with differing content: {eid} "
                "(present in both host and volume with different data) — aborting"
            )
    return to_move, to_skip


def _move_experiments(merged: sqlite3.Connection, volume_path: Path, to_move: list[str]) -> None:
    """Copy whole experiments from the attached volume in one FK-checked transaction."""
    merged.isolation_level = None  # explicit BEGIN/COMMIT control the transaction
    merged.execute("PRAGMA foreign_keys=ON")
    merged.execute("ATTACH DATABASE ? AS vol", (str(volume_path),))
    exp_cols = ", ".join(EXPERIMENTS_COLUMNS)
    try:
        merged.execute("BEGIN")
        for eid in to_move:
            merged.execute(
                f"INSERT INTO experiments ({exp_cols}) "  # noqa: S608  # nosec B608 - columns are module constants
                f"SELECT {exp_cols} FROM vol.experiments WHERE experiment_id = ?",
                (eid,),
            )
            for table, columns in _CHILD_COLUMNS.items():
                cols = ", ".join(columns)
                merged.execute(
                    f"INSERT INTO {table} ({cols}) "  # noqa: S608  # nosec B608 - columns are module constants
                    f"SELECT {cols} FROM vol.{table} WHERE experiment_id = ?",
                    (eid,),
                )
        merged.execute("COMMIT")
    except Exception:
        merged.execute("ROLLBACK")
        raise
    finally:
        merged.execute("DETACH DATABASE vol")


def merge_run_state(
    host_db: Path, volume_db: Path, merged_path: Path, *, dry_run: bool
) -> MergeReport:
    """Merge volume experiments into a copy of the host DB (or report a dry-run).

    The host DB is the base. In execute mode it is copied to ``merged_path`` with
    the backup API, the volume is attached, and whole experiments move in one
    transaction. In dry-run mode nothing is written; the base is read directly.
    """
    for role, path in (("host", host_db), ("volume", volume_db)):
        if is_excluded_source(path):
            raise MergeError(f"{role} source is an excluded backup artifact: {path.name}")

    volume = _connect_ro(volume_db)
    try:
        if dry_run:
            base = _connect_ro(host_db)
            try:
                assert_schema_parity({"host": base, "volume": volume})
                assert_no_running(base, "host")
                assert_no_running(volume, "volume")
                to_move, to_skip = _plan_moves(base, volume)
                host_ids = _experiment_ids(base)
                per_counts = {eid: _child_counts(base, eid) for eid in host_ids}
                per_counts.update({eid: _child_counts(volume, eid) for eid in to_move})
            finally:
                base.close()
            return MergeReport(
                dry_run=True,
                merged_path=merged_path,
                host_experiments=host_ids,
                moved=to_move,
                skipped=to_skip,
                total_experiments=len(host_ids) + len(to_move),
                per_experiment_counts=per_counts,
            )

        _backup_copy(host_db, merged_path)
        merged = sqlite3.connect(merged_path)
        try:
            assert_schema_parity({"host": merged, "volume": volume})
            assert_no_running(merged, "host")
            assert_no_running(volume, "volume")
            host_ids = _experiment_ids(merged)
            to_move, to_skip = _plan_moves(merged, volume)
            if to_move:
                _move_experiments(merged, volume_db, to_move)
            total = merged.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            per_counts = {eid: _child_counts(merged, eid) for eid in _experiment_ids(merged)}
        finally:
            merged.close()
        return MergeReport(
            dry_run=False,
            merged_path=merged_path,
            host_experiments=host_ids,
            moved=to_move,
            skipped=to_skip,
            total_experiments=total,
            per_experiment_counts=per_counts,
        )
    finally:
        volume.close()


# ── Promotion ─────────────────────────────────────────────────────────────────────


@dataclass
class PromoteReport:
    """Structured outcome of a promotion (dry-run or executed)."""

    dry_run: bool
    merged_path: Path
    target_db: Path
    archive_dir: Path | None
    archived: list[str]


def promote_merged(merged_path: Path, target_db: Path, *, dry_run: bool) -> PromoteReport:
    """Promote ``merged_path`` to ``target_db``, archiving the old triplet.

    Checkpoints and switches the merged file to a DELETE journal, then moves the
    old ``.db``/``-wal``/``-shm`` together into a timestamped folder before moving
    the merged file into place. Nothing is deleted.

    Assumes the server is stopped and the target DB is not open. The moves are
    not atomic: a crash between them leaves files split across the archive
    folder and the target directory.
    """
    if not merged_path.is_file():
        raise MergeError(f"merged file not found (run the merge first): {merged_path}")

    triplet = [Path(str(target_db) + suffix) for suffix in ("", "-wal", "-shm")]
    present = [p for p in triplet if p.exists()]
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive_dir = target_db.parent / f"run_state_pre_promote_{ts}"

    if dry_run:
        return PromoteReport(
            dry_run=True,
            merged_path=merged_path,
            target_db=target_db,
            archive_dir=archive_dir,
            archived=[p.name for p in present],
        )

    conn = sqlite3.connect(merged_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()

    archive_dir.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for path in present:
        shutil.move(str(path), str(archive_dir / path.name))
        archived.append(path.name)
    shutil.move(str(merged_path), str(target_db))
    for suffix in ("-wal", "-shm"):
        if Path(str(target_db) + suffix).exists():
            raise MergeError(f"stale {target_db.name}{suffix} remains next to the promoted DB")
    return PromoteReport(
        dry_run=False,
        merged_path=merged_path,
        target_db=target_db,
        archive_dir=archive_dir,
        archived=archived,
    )


# ── CLI ─────────────────────────────────────────────────────────────────────────


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_target_db() -> Path:
    import os

    override = os.environ.get("SQLITE_DB_PATH")
    if override:
        return Path(override).resolve()
    return _repo_root() / "data" / "run_state.db"


def _default_merged_path(target_db: Path) -> Path:
    return target_db.parent / "run_state.merged.db"


def _print_merge_report(report: MergeReport) -> None:
    mode = "DRY-RUN" if report.dry_run else "EXECUTED"
    print(f"[merge {mode}] target: {report.merged_path}")
    print(f"  host experiments:  {len(report.host_experiments)}")
    print(f"  moved from volume: {len(report.moved)} {report.moved}")
    print(f"  skipped (same):    {len(report.skipped)} {report.skipped}")
    print(f"  total experiments: {report.total_experiments}")
    for eid in report.moved:
        counts = report.per_experiment_counts.get(eid, {})
        print(f"    + {eid}: run_status={counts.get('run_status')} results={counts.get('results')}")


def _print_promote_report(report: PromoteReport) -> None:
    mode = "DRY-RUN" if report.dry_run else "EXECUTED"
    print(f"[promote {mode}] {report.merged_path} -> {report.target_db}")
    print(f"  archive folder: {report.archive_dir}")
    print(f"  archived:       {report.archived}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--execute", action="store_true", help="Write (default: dry-run)")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promote the merged file into place instead of merging",
    )
    parser.add_argument(
        "--backup-manifest",
        type=Path,
        help="Folder with a verified MANIFEST.txt + SHA256SUMS (required to merge)",
    )
    parser.add_argument("--merged-path", type=Path, help="Where to write run_state.merged.db")
    parser.add_argument("--target-db", type=Path, help="Live run-state DB path (for --promote)")
    args = parser.parse_args(argv)

    dry_run = not args.execute
    target_db = args.target_db.resolve() if args.target_db else _default_target_db()
    merged_path = (
        args.merged_path.resolve() if args.merged_path else _default_merged_path(target_db)
    )

    try:
        if args.promote:
            promote_report = promote_merged(merged_path, target_db, dry_run=dry_run)
            _print_promote_report(promote_report)
            return 0

        if args.backup_manifest is None:
            raise MergeError(
                "--backup-manifest is required: the merge refuses to run without a "
                "verified backup manifest for both DBs"
            )
        manifest = verify_backup_manifest(args.backup_manifest)
        merge_report = merge_run_state(
            manifest.host_db, manifest.volume_db, merged_path, dry_run=dry_run
        )
        _print_merge_report(merge_report)
        return 0
    except MergeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
