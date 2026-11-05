"""Boot and /healthz diagnostics for the single SQLite run-state file (Slice 65B).

Read-only inspection of the one run-state DB — resolved path, inode, journal
mode, file sizes, ``quick_check``, and row counts — surfaced in the boot log and
in ``/healthz`` ``stores.run_state.diagnostics`` so operators can confirm every
component reads and writes the same file. Plus a shutdown checkpoint helper that
runs ``wal_checkpoint(TRUNCATE)`` on a fresh connection so SIGTERM folds the WAL
back into the main DB before the container stops.

Cost split (B1): ``quick_check`` and ``count(*)`` are full table scans — on a
~600MB DB they are slow enough to blow the 10s Docker healthcheck timeout and
block the event loop if run on every ``/healthz`` call. So they run exactly once
at boot (``prime_boot_diagnostics``) and are cached module-level with the time
taken; ``collect_run_state_diagnostics`` (the per-call ``/healthz`` collector)
reports those cached values and only reads cheap fields live (filesystem stat,
inode, sizes, and ``PRAGMA journal_mode``, which returns the mode without a scan).

The collector never creates the file: callers that must not create a second DB
guard on existence, and the collector returns an ``exists=False`` record when the
file is absent instead of opening (and thereby creating) it.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import TypedDict

from server.utils.logger import get_logger

logger = get_logger(__name__)

# Run-state tables (ADR-008). These names are hard-coded module constants — never
# user or request input — so the f-string ``count(*)`` query below is not a SQL
# injection vector (hence ``# nosec B608`` on that execute). A missing table
# reports a ``-1`` count sentinel — e.g. a brand-new file inspected at boot
# before schema bootstrap has run.
_RUN_STATE_TABLES: tuple[str, ...] = ("experiments", "run_status", "results")
_MISSING_TABLE_COUNT = -1

# Boot-time cache (B1). ``prime_boot_diagnostics`` runs the slow scans once and
# stores them here; ``collect_run_state_diagnostics`` reports them without
# re-scanning. ``None`` means boot priming has not run yet (quick_check/counts
# are then reported as unknown rather than re-computed on the event loop).
_boot_quick_check: str | None = None
_boot_quick_check_at: float | None = None
_boot_counts: dict[str, int] | None = None


class RunStateDiagnostics(TypedDict):
    """Read-only snapshot of the SQLite run-state file for boot log / healthz."""

    path: str
    exists: bool
    inode: int | None
    journal_mode: str | None
    db_size_bytes: int | None
    wal_size_bytes: int | None
    quick_check: str | None
    quick_check_at: float | None
    counts: dict[str, int]


def _wal_path(path: Path) -> Path:
    """Sibling ``-wal`` file for a SQLite DB path."""
    return path.with_name(path.name + "-wal")


def _pragma_scalar(conn: sqlite3.Connection, pragma: str) -> str | None:
    """Return the first column of a single-row PRAGMA, or None when empty."""
    row = conn.execute(pragma).fetchone()
    if row is None:
        return None
    return str(row[0])


def _open_readonly(resolved: str) -> sqlite3.Connection | None:
    """Open a dedicated read-only connection for the live file, or None on error.

    WAL allows concurrent readers, so this never disturbs the per-thread store
    connections. A driver error degrades to None (logged) rather than raising —
    diagnostics must never break boot or ``/healthz``.
    """
    try:
        return sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    except sqlite3.Error as exc:  # pragma: no cover - driver-level failure
        logger.warning("run-state diagnostics — cannot open %s read-only: %s", resolved, exc)
        return None


def _run_quick_check(conn: sqlite3.Connection) -> str | None:
    """Full ``PRAGMA quick_check`` — a table scan. Boot-only, never per /healthz."""
    return _pragma_scalar(conn, "PRAGMA quick_check")


def _collect_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """``count(*)`` per run-state table — a full scan on ``results``. Boot-only."""
    counts: dict[str, int] = dict.fromkeys(_RUN_STATE_TABLES, 0)
    for table in _RUN_STATE_TABLES:
        try:
            row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()  # nosec B608 - table names are module constants
            counts[table] = int(row[0]) if row else 0
        except sqlite3.Error:
            counts[table] = _MISSING_TABLE_COUNT
    return counts


def _absent_record(resolved: str) -> RunStateDiagnostics:
    """The ``exists=False`` snapshot returned when the file is not on disk."""
    return RunStateDiagnostics(
        path=resolved,
        exists=False,
        inode=None,
        journal_mode=None,
        db_size_bytes=None,
        wal_size_bytes=None,
        quick_check=None,
        quick_check_at=None,
        counts=dict.fromkeys(_RUN_STATE_TABLES, 0),
    )


def collect_run_state_diagnostics(db_path: str) -> RunStateDiagnostics:
    """Cheap, per-call run-state snapshot for ``/healthz``; never creates the file.

    Reads only cheap fields live — filesystem stat (inode, sizes) and
    ``PRAGMA journal_mode`` (a mode read, not a scan). The potentially slow
    fields — ``quick_check`` and row counts, both full scans on a large DB — are
    taken once at boot by ``prime_boot_diagnostics`` and reported here from the
    module cache (with ``quick_check_at`` recording when they were taken). They
    are ``None`` / 0 until boot priming has run. Returns an ``exists=False``
    record when the file is absent.
    """
    path = Path(db_path)
    resolved = str(path.resolve())
    if not path.exists():
        return _absent_record(resolved)

    stat = path.stat()
    wal = _wal_path(path)
    wal_size = wal.stat().st_size if wal.exists() else None

    journal_mode: str | None = None
    conn = _open_readonly(resolved)
    if conn is not None:
        try:
            journal_mode = _pragma_scalar(conn, "PRAGMA journal_mode")
        finally:
            conn.close()

    counts = dict(_boot_counts) if _boot_counts is not None else dict.fromkeys(_RUN_STATE_TABLES, 0)
    return RunStateDiagnostics(
        path=resolved,
        exists=True,
        inode=stat.st_ino,
        journal_mode=journal_mode,
        db_size_bytes=stat.st_size,
        wal_size_bytes=wal_size,
        quick_check=_boot_quick_check,
        quick_check_at=_boot_quick_check_at,
        counts=counts,
    )


def prime_boot_diagnostics(db_path: str) -> RunStateDiagnostics:
    """Run the full diagnostics once at boot and cache the slow fields.

    Runs ``quick_check`` and the per-table row counts (full scans) a single time,
    stores them — plus the time taken — in the module cache so ``/healthz`` can
    report them cheaply, and returns the complete snapshot for the boot log.
    Never creates the file (returns an ``exists=False`` record when absent).
    """
    global _boot_quick_check, _boot_quick_check_at, _boot_counts

    path = Path(db_path)
    resolved = str(path.resolve())
    if not path.exists():
        return _absent_record(resolved)

    stat = path.stat()
    wal = _wal_path(path)
    wal_size = wal.stat().st_size if wal.exists() else None

    journal_mode: str | None = None
    quick_check: str | None = None
    counts: dict[str, int] = dict.fromkeys(_RUN_STATE_TABLES, 0)
    conn = _open_readonly(resolved)
    if conn is not None:
        try:
            journal_mode = _pragma_scalar(conn, "PRAGMA journal_mode")
            quick_check = _run_quick_check(conn)
            counts = _collect_counts(conn)
        finally:
            conn.close()

    taken_at = time.time()
    _boot_quick_check = quick_check
    _boot_quick_check_at = taken_at
    _boot_counts = counts

    return RunStateDiagnostics(
        path=resolved,
        exists=True,
        inode=stat.st_ino,
        journal_mode=journal_mode,
        db_size_bytes=stat.st_size,
        wal_size_bytes=wal_size,
        quick_check=quick_check,
        quick_check_at=taken_at,
        counts=counts,
    )


def _parse_checkpoint_row(row: object) -> tuple[int, int, int]:
    """Parse ``PRAGMA wal_checkpoint``'s ``(busy, log, checkpointed)`` row.

    Returns ``(-1, -1, -1)`` for a missing or unexpected shape so the caller
    treats it as non-success rather than crashing shutdown.
    """
    if not isinstance(row, (tuple, list)) or len(row) < 3:
        return (-1, -1, -1)
    try:
        return (int(row[0]), int(row[1]), int(row[2]))
    except (TypeError, ValueError):
        return (-1, -1, -1)


def checkpoint_truncate(db_path: str) -> str | None:
    """Run ``wal_checkpoint(TRUNCATE)`` on a fresh connection; return outcome.

    Used by the lifespan shutdown hook so a clean SIGTERM (compose
    ``stop_grace_period: 30s``) folds the WAL back into the main DB and truncates
    the ``-wal`` file. Returns ``"ok"`` only when the pragma reports ``busy=0``
    (checkpoint completed). When ``busy=1`` the checkpoint was blocked and the
    WAL is not fully folded: this logs a WARNING and returns ``"busy"`` so the
    caller does not read success. No-op (returns None) when the file does not
    exist or the pragma result is unusable. Never raises — a failed checkpoint is
    logged and swallowed so shutdown continues.
    """
    path = Path(db_path)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path))
    except sqlite3.Error as exc:  # pragma: no cover - driver-level failure
        logger.warning("shutdown — cannot open %s for WAL checkpoint: %s", path, exc)
        return None
    try:
        row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        conn.commit()
        busy, log_frames, checkpointed = _parse_checkpoint_row(row)
        if busy == 0:
            logger.info(
                "shutdown — wal_checkpoint(TRUNCATE) ok (log=%s checkpointed=%s) path=%s",
                log_frames,
                checkpointed,
                path,
            )
            return "ok"
        logger.warning(
            "shutdown — wal_checkpoint(TRUNCATE) did not complete (busy=%s) path=%s row=%s; "
            "WAL not fully folded back into the main DB",
            busy,
            path,
            row,
        )
        return "busy" if busy == 1 else None
    except sqlite3.Error as exc:
        logger.warning("shutdown — wal_checkpoint(TRUNCATE) failed for %s: %s", path, exc)
        return None
    finally:
        conn.close()
