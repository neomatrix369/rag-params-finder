"""cli.main unit tests — Typer CLI app commands.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: cli/main.py — unit-tier with CliRunner and mocked API calls
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


class TestRunCommandShould:
    """Scenario: run command submits experiment and optionally watches."""

    def test_run_with_valid_config_detach_mode(self) -> None:
        """
        Scenario: run with --detach submits and exits without watching.
        Slice: coverage-gap — cli/main.py

        Given a valid config file and --detach flag
        When run is invoked
        Then it submits the experiment and exits with code 0 (no watch).
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            with patch("cli.main.submit_experiment") as mock_submit:
                mock_load.return_value = {"experiment_name": "test", "data_paths": ["pdfs/"]}
                mock_submit.return_value = {
                    "experiment_id": "exp-123",
                    "experiment_name": "test",
                    "status": "queued",
                    "run_count": 5,
                }

                ### When
                result = runner.invoke(app, ["run", "--config", "test.yaml", "--detach"])

        ### Then
        assert result.exit_code == 0
        assert "Detached" in result.stdout
        mock_submit.assert_called_once()

    def test_run_with_valid_config_watch_disabled(self) -> None:
        """
        Scenario: run with --no-watch submits and exits with message.
        Slice: coverage-gap — cli/main.py

        Given a valid config and --no-watch flag
        When run is invoked
        Then it submits and suggests dashboard without polling.
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            with patch("cli.main.submit_experiment") as mock_submit:
                mock_load.return_value = {"experiment_name": "test", "data_paths": ["pdfs/"]}
                mock_submit.return_value = {
                    "experiment_id": "exp-123",
                    "experiment_name": "test",
                    "status": "queued",
                    "run_count": 5,
                }

                ### When
                result = runner.invoke(app, ["run", "--config", "test.yaml", "--no-watch"])

        ### Then
        assert result.exit_code == 0
        assert "dashboard" in result.stdout.lower()

    def test_run_config_file_not_found(self) -> None:
        """
        Scenario: run raises on missing config file.
        Slice: coverage-gap — cli/main.py

        Given a non-existent config path
        When run is invoked
        Then it exits with code 1 and error message.
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            mock_load.side_effect = FileNotFoundError("test.yaml not found")

            ### When
            result = runner.invoke(app, ["run", "--config", "nonexistent.yaml"])

        ### Then
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_run_submit_fails_server_down(self) -> None:
        """
        Scenario: run exits on submit failure (server not running).
        Slice: coverage-gap — cli/main.py

        Given submit_experiment raises RuntimeError
        When run is invoked
        Then it exits with code 1.
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            with patch("cli.main.submit_experiment") as mock_submit:
                mock_load.return_value = {"experiment_name": "test", "data_paths": ["pdfs/"]}
                mock_submit.side_effect = RuntimeError("Cannot connect to server")

                ### When
                result = runner.invoke(app, ["run", "--config", "test.yaml"])

        ### Then
        assert result.exit_code == 1
        assert "Failed to submit" in result.stdout

    def test_run_submit_missing_experiment_id(self) -> None:
        """
        Scenario: run exits when response lacks experiment_id.
        Slice: coverage-gap — cli/main.py

        Given submit_experiment returns no experiment_id
        When run is invoked
        Then it logs warning and suggests dashboard.
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            with patch("cli.main.submit_experiment") as mock_submit:
                mock_load.return_value = {"experiment_name": "test", "data_paths": ["pdfs/"]}
                mock_submit.return_value = {
                    "experiment_name": "test",
                    "status": "queued",
                    # missing experiment_id
                }

                ### When
                result = runner.invoke(app, ["run", "--config", "test.yaml", "--watch"])

        ### Then
        assert result.exit_code == 0  # submit succeeded, but no watch
        assert "dashboard" in result.stdout.lower()

    def test_run_unexpected_exception(self) -> None:
        """
        Scenario: run handles unexpected exceptions.
        Slice: coverage-gap — cli/main.py

        Given load_config raises an unexpected error
        When run is invoked
        Then it exits with code 1 and logs exception.
        """
        ### Given
        with patch("cli.main.load_config") as mock_load:
            mock_load.side_effect = ValueError("Unexpected error")

            ### When
            result = runner.invoke(app, ["run", "--config", "test.yaml"])

        ### Then
        assert result.exit_code == 1


class TestCancelCommandShould:
    """Scenario: cancel command requests experiment cancellation."""

    def test_cancel_success(self) -> None:
        """
        Scenario: cancel succeeds on valid experiment ID.
        Slice: coverage-gap — cli/main.py

        Given an experiment ID
        When cancel is invoked
        Then it calls cancel_experiment and exits with 0.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.cancel_experiment") as mock_cancel:
            mock_cancel.return_value = {"message": "Cancellation requested"}

            result = runner.invoke(app, ["cancel", exp_id])

        ### Then
        assert result.exit_code == 0
        assert "Cancel requested" in result.stdout
        mock_cancel.assert_called_once_with(exp_id)

    def test_cancel_experiment_not_found(self) -> None:
        """
        Scenario: cancel exits when experiment not found.
        Slice: coverage-gap — cli/main.py

        Given a non-existent experiment ID
        When cancel is invoked
        Then it exits with code 1 and error message.
        """
        ### Given
        exp_id = "nonexistent"

        ### When
        with patch("cli.main.cancel_experiment") as mock_cancel:
            mock_cancel.side_effect = RuntimeError("Experiment exp-abc not found")

            result = runner.invoke(app, ["cancel", exp_id])

        ### Then
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_cancel_unexpected_exception(self) -> None:
        """
        Scenario: cancel handles unexpected exceptions.
        Slice: coverage-gap — cli/main.py

        Given cancel_experiment raises unexpected error
        When cancel is invoked
        Then it exits with code 1.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.cancel_experiment") as mock_cancel:
            mock_cancel.side_effect = RuntimeError("Network error")

            result = runner.invoke(app, ["cancel", exp_id])

        ### Then
        assert result.exit_code == 1


class TestPauseCommandShould:
    """Scenario: pause command requests pause."""

    def test_pause_success(self) -> None:
        """
        Scenario: pause succeeds on valid experiment ID.
        Slice: coverage-gap — cli/main.py

        Given an experiment ID
        When pause is invoked
        Then it calls pause_experiment and exits with 0.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.pause_experiment") as mock_pause:
            mock_pause.return_value = {"message": "Pause requested"}

            result = runner.invoke(app, ["pause", exp_id])

        ### Then
        assert result.exit_code == 0
        assert "Pause requested" in result.stdout
        mock_pause.assert_called_once_with(exp_id)

    def test_pause_experiment_not_found(self) -> None:
        """
        Scenario: pause exits when experiment not found.
        Slice: coverage-gap — cli/main.py

        Given a non-existent experiment
        When pause is invoked
        Then it exits with code 1.
        """
        ### Given
        exp_id = "nonexistent"

        ### When
        with patch("cli.main.pause_experiment") as mock_pause:
            mock_pause.side_effect = RuntimeError("Experiment not found")

            result = runner.invoke(app, ["pause", exp_id])

        ### Then
        assert result.exit_code == 1

    def test_pause_not_running(self) -> None:
        """
        Scenario: pause exits when experiment not running.
        Slice: coverage-gap — cli/main.py

        Given a completed experiment
        When pause is invoked
        Then it exits with code 1 and conflict message.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.pause_experiment") as mock_pause:
            mock_pause.side_effect = RuntimeError("Not running")

            result = runner.invoke(app, ["pause", exp_id])

        ### Then
        assert result.exit_code == 1
        assert "Error" in result.stdout


class TestResumeCommandShould:
    """Scenario: resume command resumes paused experiment."""

    def test_resume_success(self) -> None:
        """
        Scenario: resume succeeds on valid experiment ID.
        Slice: coverage-gap — cli/main.py

        Given a paused experiment ID
        When resume is invoked
        Then it calls resume_experiment and exits with 0.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.resume_experiment") as mock_resume:
            mock_resume.return_value = {"message": "Resume requested"}

            result = runner.invoke(app, ["resume", exp_id])

        ### Then
        assert result.exit_code == 0
        assert "Resume requested" in result.stdout
        mock_resume.assert_called_once_with(exp_id)

    def test_resume_experiment_not_found(self) -> None:
        """
        Scenario: resume exits when experiment not found.
        Slice: coverage-gap — cli/main.py

        Given a non-existent experiment
        When resume is invoked
        Then it exits with code 1.
        """
        ### Given
        exp_id = "nonexistent"

        ### When
        with patch("cli.main.resume_experiment") as mock_resume:
            mock_resume.side_effect = RuntimeError("Experiment not found")

            result = runner.invoke(app, ["resume", exp_id])

        ### Then
        assert result.exit_code == 1

    def test_resume_not_paused(self) -> None:
        """
        Scenario: resume exits when experiment not paused.
        Slice: coverage-gap — cli/main.py

        Given a running experiment
        When resume is invoked
        Then it exits with code 1 and error.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.resume_experiment") as mock_resume:
            mock_resume.side_effect = RuntimeError("Not paused")

            result = runner.invoke(app, ["resume", exp_id])

        ### Then
        assert result.exit_code == 1


class TestDeleteCommandShould:
    """Scenario: delete command deletes experiment."""

    def test_delete_with_force_flag(self) -> None:
        """
        Scenario: delete with --force skips confirmation.
        Slice: coverage-gap — cli/main.py

        Given an experiment ID and --force flag
        When delete is invoked
        Then it skips the prompt and calls delete_experiment.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.delete_experiment") as mock_delete:
            mock_delete.return_value = {
                "deleted_counts": {
                    "experiments": 1,
                    "run_status": 5,
                    "chunks": 50,
                    "results": 20,
                }
            }

            result = runner.invoke(app, ["delete", exp_id, "--force"])

        ### Then
        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        mock_delete.assert_called_once_with(exp_id)

    def test_delete_shows_count_breakdown(self) -> None:
        """
        Scenario: delete displays deleted document counts.
        Slice: coverage-gap — cli/main.py

        Given a successful delete response
        When delete is invoked
        Then it displays counts of deleted documents.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.delete_experiment") as mock_delete:
            mock_delete.return_value = {
                "deleted_counts": {
                    "experiments": 1,
                    "run_status": 10,
                    "chunks": 100,
                    "results": 50,
                }
            }

            result = runner.invoke(app, ["delete", exp_id, "--force"])

        ### Then
        assert result.exit_code == 0
        assert "Experiments:  1" in result.stdout
        assert "Run statuses: 10" in result.stdout
        assert "Chunks:       100" in result.stdout
        assert "Results:      50" in result.stdout

    def test_delete_experiment_not_found(self) -> None:
        """
        Scenario: delete exits when experiment not found.
        Slice: coverage-gap — cli/main.py

        Given a non-existent experiment
        When delete is invoked with --force
        Then it exits with code 1.
        """
        ### Given
        exp_id = "nonexistent"

        ### When
        with patch("cli.main.delete_experiment") as mock_delete:
            mock_delete.side_effect = RuntimeError("Experiment not found")

            result = runner.invoke(app, ["delete", exp_id, "--force"])

        ### Then
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_delete_confirms_prompt_when_force_absent(self) -> None:
        """
        Scenario: delete prompts for confirmation when --force missing.
        Slice: coverage-gap — cli/main.py

        Given no --force flag
        When delete is invoked
        Then it displays confirmation prompt.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        result = runner.invoke(app, ["delete", exp_id], input="n\n")

        ### Then
        assert result.exit_code == 0
        assert "Are you sure" in result.stdout or "Warning" in result.stdout
        # Confirmed "no", so deletion should not happen

    def test_delete_cancelled_by_user(self) -> None:
        """
        Scenario: delete exits cleanly when user cancels.
        Slice: coverage-gap — cli/main.py

        Given user responds 'n' to confirmation
        When delete is invoked
        Then it exits with code 0 without deleting.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.delete_experiment") as mock_delete:
            result = runner.invoke(app, ["delete", exp_id], input="n\n")

        ### Then
        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()
        mock_delete.assert_not_called()

    def test_delete_unexpected_exception(self) -> None:
        """
        Scenario: delete handles unexpected exceptions.
        Slice: coverage-gap — cli/main.py

        Given delete_experiment raises unexpected error
        When delete is invoked with --force
        Then it exits with code 1.
        """
        ### Given
        exp_id = "exp-123"

        ### When
        with patch("cli.main.delete_experiment") as mock_delete:
            mock_delete.side_effect = RuntimeError("Network error")

            result = runner.invoke(app, ["delete", exp_id, "--force"])

        ### Then
        assert result.exit_code == 1


class TestVersionCommandShould:
    """Scenario: version command prints package version."""

    def test_version_prints_version_string(self) -> None:
        """
        Scenario: version prints installed package version.
        Slice: coverage-gap — cli/main.py

        Given the version command
        When invoked
        Then it prints the version string.
        """
        ### Given / When
        result = runner.invoke(app, ["version"])

        ### Then
        assert result.exit_code == 0
        # version should be a version string like "0.1.0" or similar
        assert len(result.stdout.strip()) > 0


class TestCommandLineInterfaceShould:
    """Scenario: CLI app structure and help."""

    def test_main_app_has_commands(self) -> None:
        """
        Scenario: main Typer app includes expected commands.
        Slice: coverage-gap — cli/main.py

        Given the CLI app
        When help is invoked
        Then it lists run, cancel, pause, resume, delete, indexes, version.
        """
        ### Given / When
        result = runner.invoke(app, ["--help"])

        ### Then
        assert result.exit_code == 0
        assert "run" in result.stdout
        assert "cancel" in result.stdout
        assert "pause" in result.stdout
        assert "resume" in result.stdout
        assert "delete" in result.stdout
        assert "indexes" in result.stdout
        assert "version" in result.stdout

    def test_run_requires_config_option(self) -> None:
        """
        Scenario: run command requires --config option.
        Slice: coverage-gap — cli/main.py

        Given run invoked without --config
        When command is parsed
        Then it exits with error.
        """
        ### Given / When
        result = runner.invoke(app, ["run"])

        ### Then
        assert result.exit_code != 0

    def test_cancel_requires_experiment_id_argument(self) -> None:
        """
        Scenario: cancel command requires experiment ID argument.
        Slice: coverage-gap — cli/main.py

        Given cancel invoked without argument
        When command is parsed
        Then it exits with error.
        """
        ### Given / When
        result = runner.invoke(app, ["cancel"])

        ### Then
        assert result.exit_code != 0
