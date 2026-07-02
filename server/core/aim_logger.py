"""Thin Aim experiment-run logging wrapper.

Isolates the `aim` dependency so that:
  1. Aim can be swapped for MLflow or another tracker without touching the orchestrator.
  2. If Aim initialisation fails (no repo, wrong version, etc.) the logger degrades
     to a no-op and the sweep continues uninterrupted.

Usage:
    AimLogger.log_run({
        "model_name": "bge-m3",
        "model_source": "sie",
        "retrieval_method": "dense",
        "score": 0.87,
        "latency_ms": 1234,
        "topic": "machine learning",
        "experiment_id": "abc-123",
    })
"""

from __future__ import annotations

import os
from pathlib import Path

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)


def _ensure_aim_repo() -> Path:
    """Create the Aim repo directory and set AIM_REPO for the aim SDK."""
    repo = Path(settings.aim_repo).expanduser().resolve()
    repo.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AIM_REPO", str(repo))
    return repo


class AimLogger:
    """Wrapper around aim.Run — no-op if Aim init fails."""

    @staticmethod
    def log_run(params: dict) -> None:
        """Log a sweep run to Aim.

        If Aim is not available or its repository is not initialised, the call
        is silently skipped so the sweep is never blocked by logging failures.

        Args:
            params: Dict of run parameters and metrics to record.
                Expected keys: model_name, model_source, retrieval_method,
                score, latency_ms, topic, experiment_id.
        """
        try:
            from aim import Run  # type: ignore[import-untyped]

            _ensure_aim_repo()
            run = Run()
            for key, value in params.items():
                if isinstance(value, int | float | str | bool):
                    run[key] = value
            run.close()
            logger.info(
                "aim log OK — experiment_id=%s model=%s score=%s",
                params.get("experiment_id"),
                params.get("model_name"),
                params.get("score"),
            )
        except Exception as exc:
            logger.warning("aim log skipped (non-fatal): %s", exc)
