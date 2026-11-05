"""Verifies the SLICE-65 65A run-state merge script against tiny temp SQLite files.

Author: Mani Sarkar
Created: 2026-11-05
Scope: scripts/migrate/merge_run_state_dbs.py — manifest verification, schema
       parity, whole-experiment merge, collision rules, idempotency, running-status
       refusal, source exclusion and promotion; synthetic DBs only, no live data.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from scripts.migrate.merge_run_state_dbs import (
    MergeError,
    experiment_content_digest,
    is_excluded_source,
    main,
    merge_run_state,
    promote_merged,
    scan_source_dbs,
    verify_backup_manifest,
)
from tests.helpers.repo_paths import repo_root_from

_REPO = repo_root_from(Path(__file__))
_SCHEMA = (_REPO / "server" / "db" / "sqlite" / "schema.sql").read_text()


# ── Synthetic fixtures ───────────────────────────────────────────────────────────


@dataclass
class ExperimentSpec:
    """One experiment to seed into a temp run-state DB."""

    experiment_id: str
    status: str = "complete"
    run_ids: Sequence[str] = field(default_factory=lambda: ["run-1"])
    results_per_run: int = 2
    doc_marker: str = "base"


def _seed(conn: sqlite3.Connection, exp: ExperimentSpec) -> None:
    conn.execute(
        "INSERT INTO experiments (experiment_id, experiment_name, status, created_at, doc)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            exp.experiment_id,
            exp.experiment_id,
            exp.status,
            "2026-11-01T10:00:00+00:00",
            json.dumps({"marker": exp.doc_marker}),
        ),
    )
    for run_id in exp.run_ids:
        # run_id is a global PRIMARY KEY — namespace it to the experiment so specs
        # can reuse short run labels without colliding across experiments.
        full_run_id = f"{exp.experiment_id}:{run_id}"
        conn.execute(
            "INSERT INTO run_status (run_id, experiment_id, phase, created_at, doc)"
            " VALUES (?, ?, ?, ?, ?)",
            (full_run_id, exp.experiment_id, "complete", "2026-11-01T10:00:00+00:00", "{}"),
        )
        for n in range(exp.results_per_run):
            conn.execute(
                "INSERT INTO results (experiment_id, run_id, query_id, query_text, doc)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    exp.experiment_id,
                    full_run_id,
                    f"{full_run_id}-q{n}",
                    f"q{n}",
                    json.dumps({"n": n}),
                ),
            )


def make_db(path: Path, experiments: Sequence[ExperimentSpec], *, schema: str = _SCHEMA) -> Path:
    """Create a run-state SQLite file (real schema) holding the given experiments."""
    conn = sqlite3.connect(path)
    conn.executescript(schema)
    for exp in experiments:
        _seed(conn, exp)
    conn.commit()
    conn.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_backup_folder(
    folder: Path,
    host: Sequence[ExperimentSpec],
    volume: Sequence[ExperimentSpec],
    *,
    corrupt_sum: str | None = None,
    drop_from_sums: str | None = None,
    volume_schema: str = _SCHEMA,
) -> Path:
    """Build a verified backup folder (host + volume DB, MANIFEST.txt, SHA256SUMS)."""
    folder.mkdir(parents=True, exist_ok=True)
    host_db = make_db(folder / "host_run_state.db", host)
    volume_db = make_db(folder / "volume_run_state.db", volume, schema=volume_schema)

    manifest = (
        "taken_at: 2026-11-05T14:35:33Z\n"
        "purpose: SLICE-65 65A test backup\n\n"
        "[volume] file: volume_run_state.db\n"
        "[host] file: host_run_state.db\n"
    )
    manifest_txt = folder / "MANIFEST.txt"
    manifest_txt.write_text(manifest)

    sums = {
        "volume_run_state.db": _sha256(volume_db),
        "host_run_state.db": _sha256(host_db),
        "MANIFEST.txt": _sha256(manifest_txt),
    }
    if corrupt_sum is not None:
        sums[corrupt_sum] = "0" * 64
    if drop_from_sums is not None:
        sums.pop(drop_from_sums, None)
    (folder / "SHA256SUMS").write_text("".join(f"{hexd}  {name}\n" for name, hexd in sums.items()))
    return folder


# ── Manifest verification ────────────────────────────────────────────────────────


def test_given_a_valid_backup_folder_when_verified_then_both_dbs_are_located(
    tmp_path: Path,
) -> None:
    """
    Scenario: A well-formed backup folder verifies and names both DB copies.
    Slice: 65A

    Given a folder with MANIFEST.txt, SHA256SUMS and two matching DB copies,
    When the manifest is verified,
    Then the host and volume DB paths are returned.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("v1")],
    )

    ### When
    manifest = verify_backup_manifest(folder)

    ### Then
    assert manifest.host_db.name == "host_run_state.db"
    assert manifest.volume_db.name == "volume_run_state.db"


def test_given_a_tampered_db_when_verified_then_it_refuses(tmp_path: Path) -> None:
    """
    Scenario: A checksum mismatch refuses the merge.
    Slice: 65A

    Given a backup folder whose SHA256SUMS does not match a DB,
    When the manifest is verified,
    Then a MergeError about a checksum mismatch is raised.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("v1")],
        corrupt_sum="host_run_state.db",
    )

    ### When / Then
    with pytest.raises(MergeError, match="checksum mismatch"):
        verify_backup_manifest(folder)


def test_given_a_missing_sha256sums_when_verified_then_it_refuses(tmp_path: Path) -> None:
    """
    Scenario: A folder without SHA256SUMS refuses the merge.
    Slice: 65A

    Given a backup folder with no SHA256SUMS file,
    When the manifest is verified,
    Then a MergeError about the missing SHA256SUMS is raised.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk", host=[ExperimentSpec("h1")], volume=[ExperimentSpec("v1")]
    )
    (folder / "SHA256SUMS").unlink()

    ### When / Then
    with pytest.raises(MergeError, match="SHA256SUMS"):
        verify_backup_manifest(folder)


@pytest.mark.parametrize(
    "bad_line",
    ["abc123  host_run_state.db", "0" * 64],
    ids=["wrong-hex-length", "missing-name"],
)
def test_given_a_malformed_sha256sums_line_when_verified_then_it_refuses(
    tmp_path: Path, bad_line: str
) -> None:
    """
    Scenario: A malformed SHA256SUMS line refuses the merge.
    Slice: 65A

    Given a SHA256SUMS file with a short hex digest or a digest without a name,
    When the manifest is verified,
    Then a MergeError about the malformed line is raised.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk", host=[ExperimentSpec("h1")], volume=[ExperimentSpec("v1")]
    )
    sha_file = folder / "SHA256SUMS"
    sha_file.write_text(sha_file.read_text() + bad_line + "\n")

    ### When / Then
    with pytest.raises(MergeError, match="malformed SHA256SUMS line"):
        verify_backup_manifest(folder)


# ── Dry-run ────────────────────────────────────────────────────────────────────────


def test_given_disjoint_dbs_when_dry_run_then_it_plans_moves_without_writing(
    tmp_path: Path,
) -> None:
    """
    Scenario: Dry-run reports the planned moves and writes nothing.
    Slice: 65A

    Given a host with two experiments and a volume with one new experiment,
    When a dry-run merge runs,
    Then it reports three total experiments and creates no merged file.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1"), ExperimentSpec("h2")],
        volume=[ExperimentSpec("v1")],
    )
    manifest = verify_backup_manifest(folder)
    merged = tmp_path / "run_state.merged.db"

    ### When
    report = merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=True)

    ### Then
    assert report.dry_run is True
    assert report.moved == ["v1"]
    assert report.total_experiments == 3
    assert not merged.exists()


# ── Execute ──────────────────────────────────────────────────────────────────────


def test_given_disjoint_dbs_when_executed_then_merged_holds_all_experiments(
    tmp_path: Path,
) -> None:
    """
    Scenario: Executed merge copies whole experiments into the host base.
    Slice: 65A

    Given a host with two experiments and a volume with one new experiment,
    When the merge executes,
    Then the merged file holds all three with matching per-experiment counts.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1"), ExperimentSpec("h2")],
        volume=[ExperimentSpec("v1", run_ids=["r1", "r2"], results_per_run=3)],
    )
    manifest = verify_backup_manifest(folder)
    merged = tmp_path / "run_state.merged.db"

    ### When
    report = merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=False)

    ### Then
    assert report.total_experiments == 3
    assert sorted(report.per_experiment_counts["v1"].items()) == [
        ("results", 6),
        ("run_status", 2),
    ]
    conn = sqlite3.connect(merged)
    try:
        assert conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 3
        # Volume rows for v1 are present and FK-consistent.
        assert (
            conn.execute("SELECT COUNT(*) FROM results WHERE experiment_id='v1'").fetchone()[0] == 6
        )
    finally:
        conn.close()


def test_given_an_experiment_without_runs_when_executed_then_it_merges_with_zero_counts(
    tmp_path: Path,
) -> None:
    """
    Scenario: An experiment with no runs or results still merges cleanly.
    Slice: 65A

    Given a volume experiment with zero runs and zero results,
    When the merge executes,
    Then it is moved and reports zero run_status and results counts.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("empty", run_ids=[], results_per_run=0)],
    )
    manifest = verify_backup_manifest(folder)
    merged = tmp_path / "run_state.merged.db"

    ### When
    report = merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=False)

    ### Then
    assert report.moved == ["empty"]
    assert report.per_experiment_counts["empty"] == {"run_status": 0, "results": 0}


def test_given_originals_when_executed_then_they_are_never_mutated(tmp_path: Path) -> None:
    """
    Scenario: The merge never deletes or overwrites the backup originals.
    Slice: 65A

    Given a verified backup folder,
    When the merge executes,
    Then the host and volume backup copies keep their original checksums.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk", host=[ExperimentSpec("h1")], volume=[ExperimentSpec("v1")]
    )
    manifest = verify_backup_manifest(folder)
    host_before = _sha256(manifest.host_db)
    volume_before = _sha256(manifest.volume_db)

    ### When
    merge_run_state(manifest.host_db, manifest.volume_db, tmp_path / "m.db", dry_run=False)

    ### Then
    assert _sha256(manifest.host_db) == host_before
    assert _sha256(manifest.volume_db) == volume_before


def test_given_results_when_executed_then_result_id_is_not_copied(tmp_path: Path) -> None:
    """
    Scenario: result_id is a local autoincrement, never carried across.
    Slice: 65A

    Given a volume whose results have high result_id values,
    When the merge executes,
    Then merged result_ids are freshly assigned, not the volume's originals.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1", results_per_run=5)],
        volume=[ExperimentSpec("v1", results_per_run=2)],
    )
    manifest = verify_backup_manifest(folder)
    merged = tmp_path / "m.db"

    ### When
    merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=False)

    ### Then
    conn = sqlite3.connect(merged)
    try:
        ids = [r[0] for r in conn.execute("SELECT result_id FROM results ORDER BY result_id")]
    finally:
        conn.close()
    # Contiguous autoincrement over all 7 rows — not a union of two id spaces.
    assert ids == list(range(1, 8))


# ── Idempotency ──────────────────────────────────────────────────────────────────


def test_given_a_prior_merge_when_rerun_then_the_result_is_identical(tmp_path: Path) -> None:
    """
    Scenario: A second merge with the same inputs yields identical content.
    Slice: 65A

    Given a completed merge,
    When the merge runs again into the same path,
    Then the experiment set and per-experiment counts are unchanged.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("v1")],
    )
    manifest = verify_backup_manifest(folder)
    merged = tmp_path / "m.db"
    first = merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=False)

    ### When
    second = merge_run_state(manifest.host_db, manifest.volume_db, merged, dry_run=False)

    ### Then
    assert second.total_experiments == first.total_experiments == 2
    assert second.per_experiment_counts == first.per_experiment_counts
    assert second.moved == ["v1"]


# ── Collision rules ──────────────────────────────────────────────────────────────


def test_given_identical_shared_experiment_when_merged_then_it_is_skipped(
    tmp_path: Path,
) -> None:
    """
    Scenario: An experiment present in both with identical content is skipped.
    Slice: 65A

    Given the same experiment id with identical content in host and volume,
    When the merge executes,
    Then it is skipped and the total stays at the host count.
    """
    ### Given
    shared = ExperimentSpec("shared", run_ids=["r1"], results_per_run=2, doc_marker="same")
    folder = make_backup_folder(
        tmp_path / "bk", host=[shared], volume=[shared, ExperimentSpec("v1")]
    )
    manifest = verify_backup_manifest(folder)

    ### When
    report = merge_run_state(manifest.host_db, manifest.volume_db, tmp_path / "m.db", dry_run=False)

    ### Then
    assert report.skipped == ["shared"]
    assert report.moved == ["v1"]
    assert report.total_experiments == 2


def test_given_differing_shared_experiment_when_merged_then_it_aborts(tmp_path: Path) -> None:
    """
    Scenario: A shared experiment id with differing content is a hard stop.
    Slice: 65A

    Given the same experiment id with different content in host and volume,
    When the merge runs,
    Then a MergeError about a collision with differing content is raised.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("shared", doc_marker="host-version")],
        volume=[ExperimentSpec("shared", doc_marker="volume-version")],
    )
    manifest = verify_backup_manifest(folder)

    ### When / Then
    with pytest.raises(MergeError, match="collision with differing content"):
        merge_run_state(manifest.host_db, manifest.volume_db, tmp_path / "m.db", dry_run=False)


# ── Schema parity ────────────────────────────────────────────────────────────────


def test_given_a_volume_missing_a_column_when_merged_then_it_fails_clearly(
    tmp_path: Path,
) -> None:
    """
    Scenario: An older volume missing a column fails with a clear message.
    Slice: 65A

    Given a volume DB whose experiments table lacks vector_store_snapshot,
    When the merge runs,
    Then a MergeError naming the missing column on 'experiments' is raised.
    """
    ### Given
    old_schema = _SCHEMA.replace("    vector_store_snapshot TEXT,\n", "")
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("v1")],
        volume_schema=old_schema,
    )
    manifest = verify_backup_manifest(folder)

    ### When / Then
    with pytest.raises(MergeError, match="schema parity failure on table 'experiments'"):
        merge_run_state(manifest.host_db, manifest.volume_db, tmp_path / "m.db", dry_run=True)


# ── Running precondition ─────────────────────────────────────────────────────────


def test_given_a_running_experiment_when_merged_then_it_refuses(tmp_path: Path) -> None:
    """
    Scenario: A running experiment stops the merge.
    Slice: 65A

    Given a volume with an experiment whose status is 'running',
    When the merge runs,
    Then a MergeError telling the operator to stop the server is raised.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1")],
        volume=[ExperimentSpec("v1", status="running")],
    )
    manifest = verify_backup_manifest(folder)

    ### When / Then
    with pytest.raises(MergeError, match="running experiments"):
        merge_run_state(manifest.host_db, manifest.volume_db, tmp_path / "m.db", dry_run=True)


# ── Source exclusion ─────────────────────────────────────────────────────────────


def test_given_backup_artifacts_when_scanned_then_they_are_excluded(tmp_path: Path) -> None:
    """
    Scenario: Backup and merged artifacts are never offered as a source.
    Slice: 65A

    Given a directory with a real DB plus a *_backup* and a *.merged.db file,
    When the sources are scanned,
    Then only the real DB is returned.
    """
    ### Given
    (tmp_path / "run_state.db").write_bytes(b"")
    (tmp_path / "run_state_backup_20261101.db").write_bytes(b"")
    (tmp_path / "run_state.merged.db").write_bytes(b"")

    ### When
    found = scan_source_dbs(tmp_path)

    ### Then
    assert [p.name for p in found] == ["run_state.db"]
    assert is_excluded_source(tmp_path / "x.merged.db") is True
    assert is_excluded_source(tmp_path / "x_backup1.db") is True
    assert is_excluded_source(tmp_path / "run_state.db") is False


# ── Digest ───────────────────────────────────────────────────────────────────────


def test_given_identical_experiments_when_digested_then_hashes_match(tmp_path: Path) -> None:
    """
    Scenario: The content digest ignores the backing file, only the content.
    Slice: 65A

    Given the same experiment seeded into two separate DB files,
    When each is digested,
    Then the digests are equal.
    """
    ### Given
    spec = ExperimentSpec("e1", run_ids=["r1", "r2"], results_per_run=3)
    a = sqlite3.connect(make_db(tmp_path / "a.db", [spec]))
    b = sqlite3.connect(make_db(tmp_path / "b.db", [spec]))

    ### When
    try:
        digest_a = experiment_content_digest(a, "e1")
        digest_b = experiment_content_digest(b, "e1")
    finally:
        a.close()
        b.close()

    ### Then
    assert digest_a == digest_b


# ── Promotion ────────────────────────────────────────────────────────────────────


def test_given_a_merged_file_when_promoted_then_old_triplet_is_archived(
    tmp_path: Path,
) -> None:
    """
    Scenario: Promotion archives the old .db/-wal/-shm and moves the merged in.
    Slice: 65A

    Given a merged file and a live DB with a -wal and -shm sidecar,
    When promotion executes,
    Then the old triplet is archived and the merged file becomes the target.
    """
    ### Given
    target = tmp_path / "run_state.db"
    make_db(target, [ExperimentSpec("old")])
    Path(str(target) + "-wal").write_bytes(b"wal")
    Path(str(target) + "-shm").write_bytes(b"shm")
    merged = make_db(tmp_path / "run_state.merged.db", [ExperimentSpec("new")])

    ### When
    report = promote_merged(merged, target, dry_run=False)

    ### Then
    assert sorted(report.archived) == ["run_state.db", "run_state.db-shm", "run_state.db-wal"]
    assert report.archive_dir is not None and report.archive_dir.is_dir()
    assert not merged.exists()
    conn = sqlite3.connect(target)
    try:
        assert conn.execute("SELECT experiment_id FROM experiments").fetchone()[0] == "new"
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        conn.close()


def test_given_a_full_old_triplet_when_promoted_then_no_stale_sidecars_remain(
    tmp_path: Path,
) -> None:
    """
    Scenario: The old -wal/-shm never survive next to the promoted DB.
    Slice: 65A

    Given a live DB with -wal and -shm sidecars and a merged file,
    When promotion executes,
    Then no sidecar sits next to the new target and both are in the archive.
    """
    ### Given
    target = tmp_path / "run_state.db"
    make_db(target, [ExperimentSpec("old")])
    Path(str(target) + "-wal").write_bytes(b"wal")
    Path(str(target) + "-shm").write_bytes(b"shm")
    merged = make_db(tmp_path / "run_state.merged.db", [ExperimentSpec("new")])

    ### When
    report = promote_merged(merged, target, dry_run=False)

    ### Then
    assert not Path(str(target) + "-wal").exists()
    assert not Path(str(target) + "-shm").exists()
    assert report.archive_dir is not None
    assert (report.archive_dir / "run_state.db-wal").read_bytes() == b"wal"
    assert (report.archive_dir / "run_state.db-shm").read_bytes() == b"shm"


def test_given_only_the_db_file_when_promoted_then_only_it_is_archived(
    tmp_path: Path,
) -> None:
    """
    Scenario: Promotion copes with an old DB that has no -wal/-shm sidecars.
    Slice: 65A

    Given a live DB with no sidecars and a merged file,
    When promotion executes,
    Then only the .db is archived, the merged file becomes the target and
         nothing is deleted.
    """
    ### Given
    target = tmp_path / "run_state.db"
    make_db(target, [ExperimentSpec("old")])
    merged = make_db(tmp_path / "run_state.merged.db", [ExperimentSpec("new")])

    ### When
    report = promote_merged(merged, target, dry_run=False)

    ### Then
    assert report.archived == ["run_state.db"]
    assert report.archive_dir is not None
    assert sorted(p.name for p in report.archive_dir.iterdir()) == ["run_state.db"]
    assert not merged.exists()
    conn = sqlite3.connect(target)
    try:
        assert conn.execute("SELECT experiment_id FROM experiments").fetchone()[0] == "new"
    finally:
        conn.close()
    archived = sqlite3.connect(report.archive_dir / "run_state.db")
    try:
        assert archived.execute("SELECT experiment_id FROM experiments").fetchone()[0] == "old"
    finally:
        archived.close()


def test_given_no_merged_file_when_promoted_then_it_refuses(tmp_path: Path) -> None:
    """
    Scenario: Promotion refuses when the merged file is absent.
    Slice: 65A

    Given a target path but no merged file,
    When promotion runs,
    Then a MergeError about the missing merged file is raised.
    """
    ### Given / When / Then
    with pytest.raises(MergeError, match="merged file not found"):
        promote_merged(tmp_path / "absent.merged.db", tmp_path / "run_state.db", dry_run=False)


# ── CLI ──────────────────────────────────────────────────────────────────────────


def test_given_no_manifest_when_merge_invoked_then_it_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Scenario: The merge CLI refuses without a backup manifest.
    Slice: 65A

    Given no --backup-manifest argument,
    When main runs in merge mode,
    Then it returns a non-zero code and explains the manifest requirement.
    """
    ### Given / When
    code = main(["--merged-path", str(tmp_path / "m.db")])

    ### Then
    assert code == 1
    assert "backup manifest" in capsys.readouterr().err


def test_given_a_valid_manifest_when_cli_dry_run_then_it_reports_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Scenario: The merge CLI dry-run reports the plan and exits cleanly.
    Slice: 65A

    Given a verified backup folder,
    When main runs in the default dry-run merge mode,
    Then it exits zero and prints the planned total of experiments.
    """
    ### Given
    folder = make_backup_folder(
        tmp_path / "bk",
        host=[ExperimentSpec("h1"), ExperimentSpec("h2")],
        volume=[ExperimentSpec("v1")],
    )

    ### When
    code = main(
        [
            "--backup-manifest",
            str(folder),
            "--merged-path",
            str(tmp_path / "m.db"),
        ]
    )

    ### Then
    assert code == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "total experiments: 3" in out
    assert not (tmp_path / "m.db").exists()
