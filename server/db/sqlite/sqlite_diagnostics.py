"""Boot and /healthz diagnostics for the single SQLite run-state file (Slice 65B).

Read-only inspection of the one run-state DB — resolved path, inode, journal
mode, file sizes, ``quick_check``, and row counts — surfaced in the boot log and
in ``/healthz`` ``stores.run_state.diagnostics`` so operators can confirm every
component reads and writes the same file. Plus a shutdown checkpoint helper that
runs ``wal_checkpoint(TRUNCATE)`` on a fresh connection so SIGTERM folds the WAL
back into the main DB before the container stops.

The collector never creates the file: callers that must not create a second DB
guard on existence, and the collector returns an ``exists=False`` record when the
file is absent instead of opening (and thereby creating) it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

from server.utils.logger import get_logger

logger = get_logger(__name__)

# Run-state tables (ADR-008). A missing table reports a ``-1`` count sentinel —
# e.g. a brand-new file inspected at boot before schema bootstrap has run.
_RUN_STATE_TABLES: tuple[str, ...] = ("experiments", "run_status", "results")
_MISSING_TABLE_COUNT = -1


class RunStateDiagnostics(TypedDict):
    """Read-only snapshot of the SQLite run-state file for boot log / healthz."""

    path: str
    exists: bool
    inode: int | None
    journal_mode: str | None
    db_size_bytes: int | None
    wal_size_bytes: int | None
    quick_check: str | None
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


def collect_run_state_diagnostics(db_path: str) -> RunStateDiagnostics:
    """Inspect the SQLite run-state file read-only; never create it.

    Returns an ``exists=False`` record (all optional fields ``None``, counts 0)
    when the file is absent. Opens a dedicated read-only connection for the live
    file so it never disturbs the per-thread store connections (WAL allows
    concurrent readers). Any driver error degrades to a partial record rather
    than raising — diagnostics must never break boot or ``/healthz``.
    """
    path = Path(db_path)
    resolved = str(path.resolve())
    counts: dict[str, int] = dict.fromkeys(_RUN_STATE_TABLES, 0)

    if not path.exists():
        return RunStateDiagnostics(
            path=resolved,
            exists=False,
            inode=None,
            journal_mode=None,
            db_size_bytes=None,
            wal_size_bytes=None,
            quick_check=None,
            counts=counts,
        )

    stat = path.stat()
    wal = _wal_path(path)
    wal_size = wal.stat().st_size if wal.exists() else None

    journal_mode: str | None = None
    quick_check: str | None = None
    try:
        conn = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    except sqlite3.Error as exc:  # pragma: no cover - driver-level failure
        logger.warning("run-state diagnostics — cannot open %s read-only: %s", resolved, exc)
    else:
        try:
            journal_mode = _pragma_scalar(conn, "PRAGMA journal_mode")
            quick_check = _pragma_scalar(conn, "PRAGMA quick_check")
            for table in _RUN_STATE_TABLES:
                try:
                    row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()  # nosec B608
                    counts[table] = int(row[0]) if row else 0
                except sqlite3.Error:
                    counts[table] = _MISSING_TABLE_COUNT
        finally:
            conn.close()

    return RunStateDiagnostics(
        path=resolved,
        exists=True,
        inode=stat.st_ino,
        journal_mode=journal_mode,
        db_size_bytes=stat.st_size,
        wal_size_bytes=wal_size,
        quick_check=quick_check,
        counts=counts,
    )


def checkpoint_truncate(db_path: str) -> str | None:
    """Run ``wal_checkpoint(TRUNCATE)`` on a fresh connection; return mode or None.

    Used by the lifespan shutdown hook so a clean SIGTERM (compose
    ``stop_grace_period: 30s``) folds the WAL back into the main DB and truncates
    the ``-wal`` file. No-op (returns None) when the file does not exist. Never
    raises — a failed checkpoint is logged and swallowed so shutdown continues.
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
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        conn.commit()
        logger.info("shutdown — wal_checkpoint(TRUNCATE) result=%s path=%s", result, path)
        return "ok"
    except sqlite3.Error as exc:
        logger.warning("shutdown — wal_checkpoint(TRUNCATE) failed for %s: %s", path, exc)
        return None
    finally:
        conn.close()
