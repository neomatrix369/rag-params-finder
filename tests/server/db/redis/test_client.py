"""
Tests for server.db.redis.client.

Author: swami
Created: 2026-09-30
Scope: import_redis happy/missing path, build_client URL passing, is_connection_failure
       classification, raise_if_unreachable remediation hint routing.
"""

from __future__ import annotations

import sys

import pytest

from server.db.redis.client import (
    INSTALL_EXTRA_MESSAGE,
    RedisClientMissingError,
    RedisUnreachableError,
    build_client,
    import_redis,
    is_connection_failure,
    raise_if_unreachable,
)


class TestImportRedisShould:
    def test_returns_redis_module_when_installed(self, fake_redis_modules: dict) -> None:
        """
        Scenario: import_redis succeeds when redis module is in sys.modules.
        Slice: 53

        Given the redis module is available (mocked in sys.modules),
        When import_redis() is called,
        Then it returns the redis module without raising.
        """
        ### Given
        # fake_redis_modules fixture already installed mock redis

        ### When
        result = import_redis()

        ### Then
        assert result is sys.modules["redis"]

    def test_raises_missing_error_when_redis_absent(self) -> None:
        """
        Scenario: import_redis raises RedisClientMissingError when redis-py not installed.
        Slice: 53

        Given redis is absent from sys.modules (simulated via None sentinel),
        When import_redis() is called,
        Then RedisClientMissingError is raised with install guidance.
        """
        ### Given
        original = sys.modules.get("redis")
        sys.modules["redis"] = None  # type: ignore[assignment]  # None sentinel → ImportError

        ### When / Then
        try:
            with pytest.raises(RedisClientMissingError) as exc_info:
                import_redis()
            assert INSTALL_EXTRA_MESSAGE in str(exc_info.value)
        finally:
            if original is None:
                sys.modules.pop("redis", None)
            else:
                sys.modules["redis"] = original


class TestBuildClientShould:
    def test_passes_url_and_timeouts_to_from_url(self, fake_redis_modules: dict) -> None:
        """
        Scenario: build_client forwards URL and socket timeout params.
        Slice: 53

        Given a redis URL,
        When build_client() is called,
        Then redis.Redis.from_url is called with that URL and socket_timeout=10.
        """
        ### Given
        url = "redis://127.0.0.1:6379"
        redis_mock = fake_redis_modules["redis"]

        ### When
        client = build_client(url)

        ### Then
        redis_mock.Redis.from_url.assert_called_once_with(
            url, socket_timeout=10, socket_connect_timeout=10
        )
        assert client is redis_mock.Redis.from_url.return_value

    def test_uses_provided_url_verbatim(self, fake_redis_modules: dict) -> None:
        """
        Scenario: build_client passes cloud TLS URL as-is.
        Slice: 53

        Given a rediss:// cloud URL with credentials,
        When build_client() is called,
        Then the URL is forwarded unchanged (credentials not logged).
        """
        ### Given
        url = "rediss://:secret@my-redis.cloud.example.com:6380"
        redis_mock = fake_redis_modules["redis"]

        ### When
        build_client(url)

        ### Then
        call_url = redis_mock.Redis.from_url.call_args[0][0]
        assert call_url == url


class TestIsConnectionFailureShould:
    @pytest.mark.parametrize(
        "exc_name",
        ["ConnectionError", "TimeoutError", "BusyLoadingError"],
    )
    def test_returns_true_for_known_connection_exception_names(self, exc_name: str) -> None:
        """
        Scenario: is_connection_failure identifies connection-class exceptions by name.
        Slice: 53

        Given an exception whose type name is a known connection failure,
        When is_connection_failure() is called,
        Then True is returned.
        """
        ### Given
        exc_type = type(exc_name, (Exception,), {})
        exc = exc_type("connect failed")

        ### When / Then
        assert is_connection_failure(exc)

    def test_returns_true_for_os_error(self) -> None:
        """
        Scenario: OSError subclass is a connection failure.
        Slice: 53

        Given an OSError instance,
        When is_connection_failure() is called,
        Then True is returned.
        """
        ### Given
        exc = OSError("broken pipe")

        ### When / Then
        assert is_connection_failure(exc)

    def test_returns_false_for_value_error(self) -> None:
        """
        Scenario: Non-connection exceptions are not classified as connection failures.
        Slice: 53

        Given a ValueError (query / command error),
        When is_connection_failure() is called,
        Then False is returned.
        """
        ### Given
        exc = ValueError("bad query")

        ### When / Then
        assert not is_connection_failure(exc)

    def test_returns_false_for_runtime_error(self) -> None:
        """
        Scenario: RuntimeError is not a connection failure.
        Slice: 53

        Given a RuntimeError,
        When is_connection_failure() is called,
        Then False is returned.
        """
        ### Given
        exc = RuntimeError("unexpected")

        ### When / Then
        assert not is_connection_failure(exc)


class TestRaiseIfUnreachableShould:
    def test_raises_unreachable_for_connection_error(self) -> None:
        """
        Scenario: Connection failures are re-wrapped as RedisUnreachableError.
        Slice: 53

        Given a ConnectionError exception and a local URL,
        When raise_if_unreachable() is called,
        Then RedisUnreachableError is raised with a remediation hint.
        """
        ### Given
        exc_type = type("ConnectionError", (Exception,), {})
        exc = exc_type("connection refused")
        url = "redis://127.0.0.1:6379"

        ### When / Then
        with pytest.raises(RedisUnreachableError) as exc_info:
            raise_if_unreachable(exc, url)
        assert "Redis unreachable" in str(exc_info.value)
        assert "redis-local" in str(exc_info.value)

    def test_raises_unreachable_with_cloud_mode_label(self) -> None:
        """
        Scenario: Cloud URL appears as redis-cloud in remediation hint.
        Slice: 53

        Given a TimeoutError and a cloud TLS URL,
        When raise_if_unreachable() is called,
        Then RedisUnreachableError mentions 'redis-cloud'.
        """
        ### Given
        exc_type = type("TimeoutError", (Exception,), {})
        exc = exc_type("timed out")
        url = "rediss://my.redis.cloud.example.com:6380"

        ### When / Then
        with pytest.raises(RedisUnreachableError) as exc_info:
            raise_if_unreachable(exc, url)
        assert "redis-cloud" in str(exc_info.value)

    def test_does_not_raise_for_non_connection_error(self) -> None:
        """
        Scenario: Non-connection errors pass through raise_if_unreachable unchanged.
        Slice: 53

        Given a ValueError (not a connection error),
        When raise_if_unreachable() is called,
        Then no exception is raised (function returns normally).
        """
        ### Given
        exc = ValueError("bad argument")
        url = "redis://127.0.0.1:6379"

        ### When / Then
        raise_if_unreachable(exc, url)  # should not raise
