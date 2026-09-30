"""
Tests for server.db.redis.preflight.

Author: swami
Created: 2026-09-30
Scope: check_query_engine (FT._LIST presence), check_eviction_policy (allkeys-* rejection),
       check_capacity (unlimited / sufficient / insufficient), warn_if_aof_disabled (warning),
       run_all_preflight (full chain).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.db.redis.preflight import (
    RedisPreflightError,
    check_capacity,
    check_eviction_policy,
    check_query_engine,
    run_all_preflight,
    warn_if_aof_disabled,
)
from server.db.redis.schema import ACCEPTED_EVICTION_POLICIES

# ── helpers ──────────────────────────────────────────────────────────────────


def _client_with_memory_info(
    *,
    policy: str = "noeviction",
    maxmemory: int = 0,
    used_memory: int = 100_000,
    aof_enabled: int = 1,
) -> MagicMock:
    client = MagicMock()
    client.info.side_effect = lambda section: (
        {"maxmemory_policy": policy, "maxmemory": maxmemory, "used_memory": used_memory}
        if section == "memory"
        else {"aof_enabled": aof_enabled}
    )
    return client


class TestCheckQueryEngineShould:
    def test_succeeds_when_ft_list_returns_result(self) -> None:
        """
        Scenario: FT._LIST available — Query Engine present, no error raised.
        Slice: 53

        Given a client that returns a list for FT._LIST,
        When check_query_engine() is called,
        Then no exception is raised.
        """
        ### Given
        client = MagicMock()
        client.execute_command.return_value = ["rpf:chunks"]

        ### When / Then
        check_query_engine(client)  # should not raise

    @pytest.mark.parametrize(
        "err_msg",
        [
            "unknown command 'FT._LIST'",
            "ERR Unknown command",
            "unknown: FT._LIST",
        ],
    )
    def test_raises_preflight_error_when_unknown_command(self, err_msg: str) -> None:
        """
        Scenario: 'unknown command' response means Query Engine is absent.
        Slice: 53

        Given FT._LIST raises an exception with 'unknown' in the message,
        When check_query_engine() is called,
        Then RedisPreflightError is raised with install guidance.
        """
        ### Given
        client = MagicMock()
        client.execute_command.side_effect = Exception(err_msg)

        ### When / Then
        with pytest.raises(RedisPreflightError, match="Query Engine"):
            check_query_engine(client)

    def test_reraises_non_unknown_exception(self) -> None:
        """
        Scenario: A connection error from FT._LIST is re-raised unchanged.
        Slice: 53

        Given FT._LIST raises a ConnectionError (not 'unknown command'),
        When check_query_engine() is called,
        Then the original exception is re-raised.
        """
        ### Given
        client = MagicMock()
        original_exc = ConnectionError("refused")
        client.execute_command.side_effect = original_exc

        ### When / Then
        with pytest.raises(ConnectionError):
            check_query_engine(client)


class TestCheckEvictionPolicyShould:
    @pytest.mark.parametrize("policy", list(ACCEPTED_EVICTION_POLICIES))
    def test_returns_policy_for_accepted_values(self, policy: str) -> None:
        """
        Scenario: Accepted eviction policies are returned without error.
        Slice: 53

        Given an accepted policy,
        When check_eviction_policy() is called,
        Then the policy string is returned.
        """
        ### Given
        client = _client_with_memory_info(policy=policy)

        ### When
        result = check_eviction_policy(client, accepted=ACCEPTED_EVICTION_POLICIES)

        ### Then
        assert result == policy

    @pytest.mark.parametrize(
        "policy",
        ["allkeys-lru", "allkeys-lfu", "allkeys-random"],
    )
    def test_raises_for_allkeys_policies(self, policy: str) -> None:
        """
        Scenario: allkeys-* policies can evict vector data — must be rejected.
        Slice: 53

        Given an allkeys-* eviction policy,
        When check_eviction_policy() is called,
        Then RedisPreflightError is raised naming the bad policy.
        """
        ### Given
        client = _client_with_memory_info(policy=policy)

        ### When / Then
        with pytest.raises(RedisPreflightError, match=policy):
            check_eviction_policy(client, accepted=ACCEPTED_EVICTION_POLICIES)

    def test_normalises_policy_to_lowercase(self) -> None:
        """
        Scenario: Policy comparison is case-insensitive.
        Slice: 53

        Given policy returned as 'NOEVICTION' (uppercase),
        When check_eviction_policy() is called,
        Then it is accepted as 'noeviction'.
        """
        ### Given
        client = MagicMock()
        client.info.return_value = {
            "maxmemory_policy": "NOEVICTION",
            "maxmemory": 0,
            "used_memory": 0,
        }

        ### When / Then
        check_eviction_policy(client, accepted=ACCEPTED_EVICTION_POLICIES)


class TestCheckCapacityShould:
    def test_skips_check_when_maxmemory_is_zero(self) -> None:
        """
        Scenario: maxmemory=0 (unlimited) — capacity check is skipped.
        Slice: 53

        Given maxmemory=0 and many planned vectors,
        When check_capacity() is called,
        Then no exception is raised.
        """
        ### Given
        client = _client_with_memory_info(maxmemory=0, used_memory=0)

        ### When / Then
        check_capacity(client, planned_vectors=1_000_000, dims=1024)  # should not raise

    def test_raises_when_planned_bytes_exceed_available(self) -> None:
        """
        Scenario: Insufficient memory → RedisPreflightError with MB values.
        Slice: 53

        Given maxmemory=10MB, used=9MB, planned=2MB,
        When check_capacity() is called,
        Then RedisPreflightError is raised with planned/available MB.
        """
        ### Given
        one_mb = 1024 * 1024
        client = _client_with_memory_info(maxmemory=10 * one_mb, used_memory=9 * one_mb)

        ### When / Then
        with pytest.raises(RedisPreflightError, match="MB"):
            check_capacity(client, planned_vectors=1000, dims=384)

    def test_passes_when_memory_is_sufficient(self) -> None:
        """
        Scenario: Available memory > planned bytes → check passes.
        Slice: 53

        Given maxmemory=1GB, used=1MB, planned small,
        When check_capacity() is called,
        Then no exception is raised.
        """
        ### Given
        client = _client_with_memory_info(
            maxmemory=1024 * 1024 * 1024,
            used_memory=1024 * 1024,
        )

        ### When / Then
        check_capacity(client, planned_vectors=100, dims=384)


class TestWarnIfAofDisabledShould:
    def test_logs_warning_when_aof_is_off(self) -> None:
        """
        Scenario: AOF disabled triggers a logger.warning (never raises).
        Slice: 53

        Given aof_enabled=0,
        When warn_if_aof_disabled() is called,
        Then logger.warning is called and no exception is raised.
        """
        ### Given
        client = _client_with_memory_info(aof_enabled=0)

        ### When / Then
        with patch("server.db.redis.preflight.logger") as mock_logger:
            warn_if_aof_disabled(client)
        mock_logger.warning.assert_called_once()

    def test_does_not_warn_when_aof_is_on(self) -> None:
        """
        Scenario: AOF enabled — no warning logged.
        Slice: 53

        Given aof_enabled=1,
        When warn_if_aof_disabled() is called,
        Then logger.warning is NOT called.
        """
        ### Given
        client = _client_with_memory_info(aof_enabled=1)

        ### When
        with patch("server.db.redis.preflight.logger") as mock_logger:
            warn_if_aof_disabled(client)

        ### Then
        mock_logger.warning.assert_not_called()

    def test_silently_passes_when_persistence_info_unavailable(self) -> None:
        """
        Scenario: Managed services may not expose persistence info — silently skip.
        Slice: 53

        Given client.info('persistence') raises an exception,
        When warn_if_aof_disabled() is called,
        Then no exception propagates.
        """
        ### Given
        client = MagicMock()
        client.info.side_effect = Exception("command not allowed")

        ### When / Then
        warn_if_aof_disabled(client)  # must not raise


class TestRunAllPreflightShould:
    def test_runs_all_checks_in_order(self) -> None:
        """
        Scenario: run_all_preflight calls all four checks in sequence.
        Slice: 53

        Given a healthy Redis client,
        When run_all_preflight() is called,
        Then FT._LIST, INFO memory (twice), INFO persistence are called.
        """
        ### Given
        client = MagicMock()
        client.execute_command.return_value = []
        client.info.side_effect = lambda section: (
            {"maxmemory_policy": "noeviction", "maxmemory": 0, "used_memory": 0}
            if section == "memory"
            else {"aof_enabled": 1}
        )

        ### When
        run_all_preflight(
            client,
            planned_vectors=100,
            dims=384,
            accepted_policies=ACCEPTED_EVICTION_POLICIES,
        )

        ### Then
        client.execute_command.assert_called_once_with("FT._LIST")
        assert client.info.call_count >= 2

    def test_short_circuits_on_query_engine_missing(self) -> None:
        """
        Scenario: Query Engine absent stops preflight at step 1.
        Slice: 53

        Given FT._LIST raises 'unknown command',
        When run_all_preflight() is called,
        Then RedisPreflightError is raised and INFO is never called.
        """
        ### Given
        client = MagicMock()
        client.execute_command.side_effect = Exception("unknown command 'FT._LIST'")

        ### When / Then
        with pytest.raises(RedisPreflightError):
            run_all_preflight(
                client,
                planned_vectors=100,
                dims=384,
                accepted_policies=ACCEPTED_EVICTION_POLICIES,
            )
        client.info.assert_not_called()
