"""Redis preflight checks — run before any vector sweep.

Uses ``INFO memory`` / ``INFO persistence`` (not ``CONFIG GET`` — blocked on
managed services, DECISIONS #253). AOF off is a warning, not a 422.
"""

from __future__ import annotations

from typing import Any

from server.utils.logger import get_logger

logger = get_logger(__name__)

_QUERY_ENGINE_MISSING = (
    "Redis Query Engine is not available on this server. "
    "The vector index (FT.CREATE / FT.SEARCH) requires the Redis Query Engine "
    "(built into Redis 8+) or the valkey-search module. "
    "See docs/user-guide/redis-setup.md for installation instructions."
)

_EVICTION_POLICY_ERROR_TEMPLATE = (
    "Redis eviction policy {policy!r} can silently evict vector data. "
    "Accepted policies: {accepted}. "
    "Change maxmemory-policy to one of the accepted values and restart Redis "
    "(./start-services.sh --redis-local for the local profile). "
    "See docs/user-guide/redis-setup.md for guidance."
)

_CAPACITY_ERROR_TEMPLATE = (
    "Insufficient Redis memory for this sweep. "
    "Planned: {planned_mb:.1f} MB, available: {available_mb:.1f} MB. "
    "Increase --maxmemory or reduce the sweep size."
)

_AOF_WARNING_TEMPLATE = (
    "Redis persistence (AOF) is disabled on this server. "
    "Vector data will be lost if Redis restarts before the sweep is complete. "
    "Set 'appendonly yes' in your Redis configuration or use "
    "--appendonly yes on the command line. "
    "See docs/user-guide/redis-setup.md § Backup & Recovery for guidance."
)

# Bytes per float32 vector element; meta-overhead per chunk key.
_BYTES_PER_FLOAT32 = 4
_BYTES_PER_CHUNK_OVERHEAD = 600  # TAG fields + key + overhead


class RedisPreflightError(ValueError):
    """Raised by preflight when the server is unsuitable for a vector sweep."""


def check_query_engine(client: Any) -> None:
    """Verify FT._LIST works — absent = Query Engine not available.

    Raises ``RedisPreflightError`` with install guidance when the command is
    unknown (Redis without Query Engine or Valkey without valkey-search).
    """
    try:
        client.execute_command("FT._LIST")
    except Exception as exc:
        msg = str(exc).lower()
        if "unknown command" in msg or "err unknown" in msg or "unknown" in msg:
            raise RedisPreflightError(_QUERY_ENGINE_MISSING) from exc
        # Other errors (connection) are re-raised as-is.
        raise


def check_eviction_policy(client: Any, *, accepted: frozenset[str]) -> str:
    """Raise ``RedisPreflightError`` when the eviction policy would delete vectors.

    Returns the active policy string on success.
    """
    memory_info = client.info("memory")
    policy = str(memory_info.get("maxmemory_policy") or "noeviction").lower().strip()
    if policy not in accepted:
        raise RedisPreflightError(
            _EVICTION_POLICY_ERROR_TEMPLATE.format(
                policy=policy,
                accepted=", ".join(sorted(accepted)),
            )
        )
    return policy


def check_capacity(
    client: Any,
    *,
    planned_vectors: int,
    dims: int,
) -> None:
    """Raise ``RedisPreflightError`` when Redis lacks memory for the sweep.

    Estimates planned bytes as ``planned_vectors × (dims × 4 + overhead)``.
    Skips the check when ``maxmemory`` is 0 (unlimited).
    """
    memory_info = client.info("memory")
    maxmemory = int(memory_info.get("maxmemory") or 0)
    if maxmemory == 0:
        return  # no limit configured; skip capacity check.
    used_memory = int(memory_info.get("used_memory") or 0)
    available = maxmemory - used_memory
    bytes_per_vector = dims * _BYTES_PER_FLOAT32 + _BYTES_PER_CHUNK_OVERHEAD
    planned_bytes = planned_vectors * bytes_per_vector
    if planned_bytes > available:
        planned_mb = planned_bytes / (1024 * 1024)
        available_mb = available / (1024 * 1024)
        raise RedisPreflightError(
            _CAPACITY_ERROR_TEMPLATE.format(
                planned_mb=planned_mb,
                available_mb=available_mb,
            )
        )


def warn_if_aof_disabled(client: Any) -> None:
    """Log a warning when AOF persistence is off — vectors survive a restart if off.

    AOF-disabled is not a 422; it is a durability advisory.
    """
    try:
        persistence_info = client.info("persistence")
        aof_enabled = int(persistence_info.get("aof_enabled") or 0)
        if not aof_enabled:
            logger.warning(_AOF_WARNING_TEMPLATE)
    except Exception:
        # Persistence info unavailable on some managed services — skip.
        pass


def run_all_preflight(
    client: Any,
    *,
    planned_vectors: int,
    dims: int,
    accepted_policies: frozenset[str],
) -> None:
    """Run all preflight checks in order.

    Order:
    1. Query Engine present (FT._LIST)
    2. Eviction policy (INFO memory)
    3. Capacity (INFO memory)
    4. AOF warning (INFO persistence) — warning only, never raises
    """
    check_query_engine(client)
    check_eviction_policy(client, accepted=accepted_policies)
    check_capacity(client, planned_vectors=planned_vectors, dims=dims)
    warn_if_aof_disabled(client)
