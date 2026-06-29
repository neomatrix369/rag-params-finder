"""Settings tests for SIE endpoint configuration."""

from __future__ import annotations

from server.settings import Settings


class TestSIESettings:
    """Scenario: SIE endpoint configuration from environment."""

    def test_sie_endpoint_reads_sie_endpoint_env(self, monkeypatch):
        """
        Given SIE_ENDPOINT is set in the environment
        When Settings is constructed
        Then sie_endpoint uses that value.
        """
        monkeypatch.setenv("SIE_ENDPOINT", "https://remote-sie.example.com")

        settings = Settings()

        assert settings.sie_endpoint == "https://remote-sie.example.com"
