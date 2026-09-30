"""
Tests for server.db.redis.uri.

Author: swami
Created: 2026-09-30
Scope: redis_storage_mode classification (local vs cloud), cluster_host extraction,
       redact_url password masking.  All pure functions — no mocking required.
"""

from __future__ import annotations

import pytest

from server.db.redis.uri import (
    STORAGE_MODE_REDIS_CLOUD,
    STORAGE_MODE_REDIS_LOCAL,
    cluster_host,
    redact_url,
    redis_storage_mode,
)


class TestRedisStorageModeShould:
    @pytest.mark.parametrize(
        "url",
        [
            "redis://localhost:6379",
            "redis://127.0.0.1:6379",
            "redis://::1:6379",
            "redis://redis-local:6379",
            "",
            "   ",
        ],
    )
    def test_returns_local_for_loopback_and_compose_hostnames(self, url: str) -> None:
        """
        Scenario: Local hostnames and empty URLs map to redis-local.
        Slice: 53

        Given a URL with a loopback address, Compose service name, or empty string,
        When redis_storage_mode() is called,
        Then STORAGE_MODE_REDIS_LOCAL is returned.
        """
        ### Given / When
        result = redis_storage_mode(url)

        ### Then
        assert result == STORAGE_MODE_REDIS_LOCAL

    @pytest.mark.parametrize(
        "url",
        [
            "rediss://my-redis.upstash.io:6380",
            "rediss://:password@redis.cloud.example.com:6380",
        ],
    )
    def test_returns_cloud_for_tls_scheme(self, url: str) -> None:
        """
        Scenario: TLS scheme (rediss://) always signals a managed cloud endpoint.
        Slice: 53

        Given a URL with rediss:// scheme,
        When redis_storage_mode() is called,
        Then STORAGE_MODE_REDIS_CLOUD is returned.
        """
        ### Given / When
        result = redis_storage_mode(url)

        ### Then
        assert result == STORAGE_MODE_REDIS_CLOUD

    @pytest.mark.parametrize(
        "url",
        [
            "redis://my-redis.cloud.example.com:6379",
            "redis://redis.some-managed-service.io:6379",
        ],
    )
    def test_returns_cloud_for_non_local_hostname_with_dots(self, url: str) -> None:
        """
        Scenario: External hostname containing dots is treated as cloud.
        Slice: 53

        Given a non-TLS URL with a hostname that has dots (not loopback),
        When redis_storage_mode() is called,
        Then STORAGE_MODE_REDIS_CLOUD is returned.
        """
        ### Given / When
        result = redis_storage_mode(url)

        ### Then
        assert result == STORAGE_MODE_REDIS_CLOUD

    def test_no_dots_short_name_is_local(self) -> None:
        """
        Scenario: Short hostname without dots treated as local (Compose / LAN).
        Slice: 53

        Given a URL with a hostname that has no dots,
        When redis_storage_mode() is called,
        Then STORAGE_MODE_REDIS_LOCAL is returned.
        """
        ### Given
        url = "redis://redis-service:6379"

        ### When
        result = redis_storage_mode(url)

        ### Then
        assert result == STORAGE_MODE_REDIS_LOCAL


class TestClusterHostShould:
    def test_returns_hostname_from_url(self) -> None:
        """
        Scenario: cluster_host extracts the hostname for display.
        Slice: 53

        Given a redis URL with a hostname,
        When cluster_host() is called,
        Then the hostname string is returned.
        """
        ### Given
        url = "redis://my-redis.example.com:6379"

        ### When
        result = cluster_host(url)

        ### Then
        assert result == "my-redis.example.com"

    def test_returns_none_for_empty_url(self) -> None:
        """
        Scenario: Empty URL yields None — no host to display.
        Slice: 53

        Given an empty URL,
        When cluster_host() is called,
        Then None is returned.
        """
        ### Given
        url = ""

        ### When
        result = cluster_host(url)

        ### Then
        assert result is None

    def test_returns_loopback_host(self) -> None:
        """
        Scenario: Local URL returns loopback address.
        Slice: 53

        Given redis://127.0.0.1:6379,
        When cluster_host() is called,
        Then '127.0.0.1' is returned.
        """
        ### Given / When
        result = cluster_host("redis://127.0.0.1:6379")

        ### Then
        assert result == "127.0.0.1"


class TestRedactUrlShould:
    def test_replaces_password_with_stars(self) -> None:
        """
        Scenario: Passwords in URLs are masked before logging.
        Slice: 53

        Given a URL with a password,
        When redact_url() is called,
        Then the password is replaced with ***.
        """
        ### Given
        url = "redis://:supersecret@my-redis.example.com:6380"

        ### When
        result = redact_url(url)

        ### Then
        assert "supersecret" not in result
        assert "***" in result

    def test_leaves_url_without_password_unchanged(self) -> None:
        """
        Scenario: URLs without passwords are returned unchanged.
        Slice: 53

        Given a URL with no password component,
        When redact_url() is called,
        Then the URL is returned as-is.
        """
        ### Given
        url = "redis://127.0.0.1:6379"

        ### When
        result = redact_url(url)

        ### Then
        assert result == url

    def test_returns_empty_string_for_empty_input(self) -> None:
        """
        Scenario: Empty URL returns empty string.
        Slice: 53

        Given an empty string,
        When redact_url() is called,
        Then an empty string is returned.
        """
        ### Given / When / Then
        assert redact_url("") == ""

    def test_handles_url_with_username_and_password(self) -> None:
        """
        Scenario: URL with both user and password masks only the password.
        Slice: 53

        Given a URL with username 'user' and password 'pass',
        When redact_url() is called,
        Then 'pass' is masked but 'user' remains.
        """
        ### Given
        url = "redis://user:pass@host:6379"

        ### When
        result = redact_url(url)

        ### Then
        assert "pass" not in result
        assert "user" in result
