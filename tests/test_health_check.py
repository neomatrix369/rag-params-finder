"""Unit tests for server.core.health_check."""

from unittest.mock import MagicMock, patch

from server.core.health_check import mongodb_health_status


def test_given_empty_mongodb_uri_when_health_checked_then_return_skipped() -> None:
    # given
    with patch("server.core.health_check.settings") as mock_settings:
        mock_settings.mongodb_uri = ""

        # when
        actual_status = mongodb_health_status()

    # then
    assert actual_status == "skipped", "Expected skipped when MONGODB_URI is unset"


def test_given_placeholder_mongodb_uri_when_health_checked_then_return_error() -> None:
    # given
    with patch("server.core.health_check.settings") as mock_settings:
        mock_settings.mongodb_uri = "your_mongodb_atlas_uri_here"

        # when
        actual_status = mongodb_health_status()

    # then
    assert actual_status == "error", "Expected error for placeholder Atlas URI"


def test_given_valid_uri_when_ping_succeeds_then_return_ok() -> None:
    # given
    mock_client = MagicMock()
    with (
        patch("server.core.health_check.settings") as mock_settings,
        patch(
            "server.core.health_check.MongoClient", return_value=mock_client
        ) as mock_mongo_client,
    ):
        mock_settings.mongodb_uri = "mongodb+srv://user:pass@cluster.mongodb.net/db"
        mock_settings.health_check_mongodb_timeout_ms = 5000

        # when
        actual_status = mongodb_health_status()

    # then
    mock_mongo_client.assert_called_once()
    mock_client.admin.command.assert_called_once_with("ping")
    assert actual_status == "ok", "Expected ok when MongoDB ping succeeds"
