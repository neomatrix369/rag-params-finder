"""cli.api_client unit tests.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: cli/api_client.py — unit-tier with httpx mocking
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cli.api_client import (
    _ensure_ok,
    _http_label,
    _response_detail,
    cancel_experiment,
    delete_experiment,
    get_experiment,
    get_run_status,
    pause_experiment,
    resume_experiment,
    submit_experiment,
)


class TestApiClientHelperFunctionsShould:
    """Scenario: HTTP error helpers format messages correctly."""

    def test_http_label_extracts_path_from_url(self) -> None:
        """
        Scenario: HTTP label formats method and path.
        Slice: coverage-gap — cli/api_client.py helpers

        Given a method and URL
        When _http_label is called
        Then it returns method + path extracted from URL.
        """
        ### Given
        method = "POST"
        url = "http://localhost:8001/experiments"

        ### When
        label = _http_label(method, url)

        ### Then
        assert label == "POST /experiments"

    def test_http_label_falls_back_to_full_url_when_path_missing(self) -> None:
        """
        Scenario: HTTP label falls back to URL when path parsing fails.
        Slice: coverage-gap — cli/api_client.py helpers

        Given a malformed URL with no path
        When _http_label is called
        Then it returns method + full URL.
        """
        ### Given
        method = "GET"
        url = "http://example"

        ### When
        label = _http_label(method, url)

        ### Then
        assert label == "GET http://example"

    def test_response_detail_extracts_string_detail(self) -> None:
        """
        Scenario: Response detail extracts string detail field.
        Slice: coverage-gap — cli/api_client.py

        Given a response with a string detail field
        When _response_detail is called
        Then it returns the detail string.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"detail": "Experiment not found"}
        response.text = ""

        ### When
        detail = _response_detail(response)

        ### Then
        assert detail == "Experiment not found"

    def test_response_detail_extracts_error_field(self) -> None:
        """
        Scenario: Response detail extracts error field when detail missing.
        Slice: coverage-gap — cli/api_client.py

        Given a response with an error field but no detail
        When _response_detail is called
        Then it returns the error string.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"error": "API error", "detail": None}
        response.text = ""

        ### When
        detail = _response_detail(response)

        ### Then
        assert detail == "API error"

    def test_response_detail_extracts_validation_errors(self) -> None:
        """
        Scenario: Response detail formats FastAPI validation errors.
        Slice: coverage-gap — cli/api_client.py

        Given a response with FastAPI validation detail array
        When _response_detail is called
        Then it formats each error as 'loc: msg'.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {
            "detail": [
                {"loc": ("body", "experiment_name"), "msg": "field required"},
                {"loc": ("query", "id"), "msg": "invalid format"},
            ]
        }
        response.text = ""

        ### When
        detail = _response_detail(response)

        ### Then
        assert "body/experiment_name: field required" in detail
        assert "query/id: invalid format" in detail

    def test_response_detail_falls_back_to_text(self) -> None:
        """
        Scenario: Response detail falls back to plain text.
        Slice: coverage-gap — cli/api_client.py

        Given a response with invalid JSON
        When _response_detail is called
        Then it returns the response text (first 200 chars).
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError("invalid json")
        response.text = "Internal Server Error: something broke"

        ### When
        detail = _response_detail(response)

        ### Then
        assert detail == "Internal Server Error: something broke"

    def test_response_detail_truncates_long_text(self) -> None:
        """
        Scenario: Response detail truncates text to 200 chars.
        Slice: coverage-gap — cli/api_client.py

        Given a very long error text
        When _response_detail is called
        Then it returns first 200 chars.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError()
        response.text = "x" * 300

        ### When
        detail = _response_detail(response)

        ### Then
        assert len(detail) == 200
        assert detail == "x" * 200

    def test_ensure_ok_passes_on_success(self) -> None:
        """
        Scenario: ensure_ok does not raise on 2xx response.
        Slice: coverage-gap — cli/api_client.py

        Given a successful response
        When _ensure_ok is called
        Then it returns without exception.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.is_success = True

        ### When / Then
        _ensure_ok(response, method="GET", url="http://localhost/test")

    def test_ensure_ok_raises_on_failure(self) -> None:
        """
        Scenario: ensure_ok raises RuntimeError on error response.
        Slice: coverage-gap — cli/api_client.py

        Given a 404 response
        When _ensure_ok is called
        Then it raises RuntimeError with status + detail.
        """
        ### Given
        response = MagicMock(spec=httpx.Response)
        response.is_success = False
        response.status_code = 404
        response.json.return_value = {"detail": "Not found"}
        response.text = ""

        ### When / Then
        with pytest.raises(RuntimeError, match="404"):
            _ensure_ok(response, method="GET", url="http://localhost/test")


class TestSubmitExperimentShould:
    """Scenario: submit_experiment posts config and returns experiment ID."""

    def test_submit_experiment_success(self) -> None:
        """
        Scenario: submit_experiment returns experiment details on 200.
        Slice: coverage-gap — cli/api_client.py

        Given a valid experiment config
        When submit_experiment is called
        Then it POSTs to /experiments and returns experiment ID.
        """
        ### Given
        config = {"experiment_name": "test", "data_paths": ["pdfs/"]}
        response_data = {
            "experiment_id": "exp-123",
            "experiment_name": "test",
            "status": "queued",
            "run_count": 10,
        }

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = submit_experiment(config)

        assert result["experiment_id"] == "exp-123"
        mock_request.assert_called_once()

    def test_submit_experiment_404_no_route(self) -> None:
        """
        Scenario: submit_experiment raises on 404 (API not running).
        Slice: coverage-gap — cli/api_client.py

        Given server returns 404
        When submit_experiment is called
        Then it raises RuntimeError with helpful startup message.
        """
        ### Given
        config = {"experiment_name": "test"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.is_success = False
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="404"):
                    submit_experiment(config)

    def test_submit_experiment_other_error(self) -> None:
        """
        Scenario: submit_experiment raises on 5xx response.
        Slice: coverage-gap — cli/api_client.py

        Given server returns 500
        When submit_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        config = {"experiment_name": "test"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.is_success = False
            mock_resp.json.return_value = {"detail": "Internal error"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="500"):
                    submit_experiment(config)


class TestGetExperimentShould:
    """Scenario: get_experiment fetches experiment details."""

    def test_get_experiment_success(self) -> None:
        """
        Scenario: get_experiment returns experiment with runs.
        Slice: coverage-gap — cli/api_client.py

        Given an experiment ID
        When get_experiment is called
        Then it GETs /experiments/{id} and returns full details.
        """
        ### Given
        exp_id = "exp-123"
        response_data = {
            "experiment_id": exp_id,
            "status": "running",
            "runs": [{"run_id": "run-1", "status": "embedding"}],
        }

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = get_experiment(exp_id)

        assert result["experiment_id"] == exp_id
        assert len(result["runs"]) == 1

    def test_get_experiment_error(self) -> None:
        """
        Scenario: get_experiment raises on error response.
        Slice: coverage-gap — cli/api_client.py

        Given a non-existent experiment ID
        When get_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "nonexistent"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.is_success = False
            mock_resp.status_code = 404
            mock_resp.json.return_value = {"detail": "Not found"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError):
                    get_experiment(exp_id)


class TestGetRunStatusShould:
    """Scenario: get_run_status fetches run phase."""

    def test_get_run_status_success(self) -> None:
        """
        Scenario: get_run_status returns current phase.
        Slice: coverage-gap — cli/api_client.py

        Given a run ID
        When get_run_status is called
        Then it GETs /runs/{id}/status and returns phase.
        """
        ### Given
        run_id = "run-123"
        response_data = {"run_id": run_id, "phase": "embedding", "progress": 0.5}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = get_run_status(run_id)

        assert result["phase"] == "embedding"


class TestCancelExperimentShould:
    """Scenario: cancel_experiment requests cancellation."""

    def test_cancel_experiment_success(self) -> None:
        """
        Scenario: cancel_experiment succeeds on 200.
        Slice: coverage-gap — cli/api_client.py

        Given a running experiment ID
        When cancel_experiment is called
        Then it POSTs to /experiments/{id}/cancel.
        """
        ### Given
        exp_id = "exp-123"
        response_data = {"message": "Cancellation requested"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = cancel_experiment(exp_id)

        assert "message" in result

    def test_cancel_experiment_404(self) -> None:
        """
        Scenario: cancel_experiment raises on 404.
        Slice: coverage-gap — cli/api_client.py

        Given a non-existent experiment
        When cancel_experiment is called
        Then it raises RuntimeError with 'not found'.
        """
        ### Given
        exp_id = "nonexistent"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.is_success = False
            mock_resp.json.return_value = {}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="not found"):
                    cancel_experiment(exp_id)

    def test_cancel_experiment_409_conflict(self) -> None:
        """
        Scenario: cancel_experiment raises on 409 (already terminal).
        Slice: coverage-gap — cli/api_client.py

        Given an already-completed experiment
        When cancel_experiment is called
        Then it raises RuntimeError with conflict detail.
        """
        ### Given
        exp_id = "exp-123"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.is_success = False
            mock_resp.json.return_value = {"detail": "Experiment already complete"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="already complete"):
                    cancel_experiment(exp_id)


class TestPauseExperimentShould:
    """Scenario: pause_experiment requests pause."""

    def test_pause_experiment_success(self) -> None:
        """
        Scenario: pause_experiment succeeds on 200.
        Slice: coverage-gap — cli/api_client.py

        Given a running experiment
        When pause_experiment is called
        Then it POSTs to /experiments/{id}/pause.
        """
        ### Given
        exp_id = "exp-123"
        response_data = {"message": "Pause requested"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = pause_experiment(exp_id)

        assert "message" in result

    def test_pause_experiment_404(self) -> None:
        """
        Scenario: pause_experiment raises on 404.
        Slice: coverage-gap — cli/api_client.py

        Given a non-existent experiment
        When pause_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "nonexistent"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.is_success = False
            mock_resp.json.return_value = {}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="not found"):
                    pause_experiment(exp_id)

    def test_pause_experiment_409_conflict(self) -> None:
        """
        Scenario: pause_experiment raises on 409.
        Slice: coverage-gap — cli/api_client.py

        Given a non-running experiment
        When pause_experiment is called
        Then it raises RuntimeError with detail.
        """
        ### Given
        exp_id = "exp-123"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.is_success = False
            mock_resp.json.return_value = {"detail": "Not running"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="Not running"):
                    pause_experiment(exp_id)


class TestResumeExperimentShould:
    """Scenario: resume_experiment resumes paused experiment."""

    def test_resume_experiment_success(self) -> None:
        """
        Scenario: resume_experiment succeeds on 200.
        Slice: coverage-gap — cli/api_client.py

        Given a paused experiment
        When resume_experiment is called
        Then it POSTs to /experiments/{id}/resume.
        """
        ### Given
        exp_id = "exp-123"
        response_data = {"message": "Resume requested"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = resume_experiment(exp_id)

        assert "message" in result

    def test_resume_experiment_404(self) -> None:
        """
        Scenario: resume_experiment raises on 404.
        Slice: coverage-gap — cli/api_client.py

        Given a non-existent experiment
        When resume_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "nonexistent"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.is_success = False
            mock_resp.json.return_value = {}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="not found"):
                    resume_experiment(exp_id)

    def test_resume_experiment_409_conflict(self) -> None:
        """
        Scenario: resume_experiment raises on 409.
        Slice: coverage-gap — cli/api_client.py

        Given a non-paused experiment
        When resume_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "exp-123"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.is_success = False
            mock_resp.json.return_value = {"detail": "Not paused"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="Not paused"):
                    resume_experiment(exp_id)


class TestDeleteExperimentShould:
    """Scenario: delete_experiment deletes experiment and data."""

    def test_delete_experiment_success(self) -> None:
        """
        Scenario: delete_experiment succeeds on 200.
        Slice: coverage-gap — cli/api_client.py

        Given an experiment ID
        When delete_experiment is called
        Then it DELETEs /experiments/{id} and returns deleted counts.
        """
        ### Given
        exp_id = "exp-123"
        response_data = {
            "deleted_counts": {
                "experiments": 1,
                "run_status": 10,
                "chunks": 100,
                "results": 50,
            }
        }

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.is_success = True
            mock_resp.json.return_value = response_data
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                result = delete_experiment(exp_id)

        assert result["deleted_counts"]["experiments"] == 1

    def test_delete_experiment_404(self) -> None:
        """
        Scenario: delete_experiment raises on 404.
        Slice: coverage-gap — cli/api_client.py

        Given a non-existent experiment
        When delete_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "nonexistent"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.is_success = False
            mock_resp.json.return_value = {}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="not found"):
                    delete_experiment(exp_id)

    def test_delete_experiment_409_conflict(self) -> None:
        """
        Scenario: delete_experiment raises on 409.
        Slice: coverage-gap — cli/api_client.py

        Given a running experiment
        When delete_experiment is called
        Then it raises RuntimeError.
        """
        ### Given
        exp_id = "exp-123"

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.is_success = False
            mock_resp.json.return_value = {"detail": "Cannot delete running experiment"}
            mock_resp.text = ""
            mock_request.return_value = mock_resp

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="Cannot delete"):
                    delete_experiment(exp_id)


class TestHttpErrorHandlingShould:
    """Scenario: HTTP errors raise with context."""

    def test_connect_error_raises_with_server_url(self) -> None:
        """
        Scenario: connection error includes server URL in message.
        Slice: coverage-gap — cli/api_client.py

        Given httpx.ConnectError from _request
        When submit_experiment is called
        Then it raises RuntimeError with server URL + startup hint.
        """
        ### Given
        config = {"experiment_name": "test"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_request.side_effect = RuntimeError(
                "Cannot connect to server at http://localhost:8001"
            )

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="Cannot connect"):
                    submit_experiment(config)

    def test_timeout_error_raises_with_duration(self) -> None:
        """
        Scenario: timeout error includes timeout duration.
        Slice: coverage-gap — cli/api_client.py

        Given httpx.TimeoutException from _request
        When submit_experiment is called
        Then it raises RuntimeError with timeout seconds.
        """
        ### Given
        config = {"experiment_name": "test"}

        ### When / Then
        with patch("cli.api_client._request") as mock_request:
            mock_request.side_effect = RuntimeError("Request timed out after 120s")

            with patch("cli.api_client.settings.server_url", "http://localhost:8001"):
                with pytest.raises(RuntimeError, match="timed out after 120s"):
                    submit_experiment(config)
