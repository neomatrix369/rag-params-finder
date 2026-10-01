"""Preflight guard for DoubleWord batch embedding provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import HTTPException

from server.core.model_registry import provider_for_model
from server.models.config import ExperimentConfig
from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

UNAVAILABLE_REGISTRY_PATH = ".rpf_state/doubleword_unavailable.json"


def load_unavailable_models() -> dict[str, str]:
    """Load the registry of unavailable DoubleWord models.

    Returns:
        Dict mapping model_id to reason string. Empty if file doesn't exist.
    """
    if not os.path.exists(UNAVAILABLE_REGISTRY_PATH):
        return {}

    try:
        with open(UNAVAILABLE_REGISTRY_PATH) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "failed to load unavailable models registry: %s",
            e,
            exc_info=True,
        )

    return {}


def save_unavailable_model(model_id: str, reason: str) -> None:
    """Save a model as unavailable to the registry.

    Creates the parent directory if needed. Writes atomically using a temp file.

    Args:
        model_id: The model ID to mark unavailable.
        reason: Human-readable reason for unavailability.
    """
    unavailable = load_unavailable_models()
    unavailable[model_id] = reason

    # Create parent directory if needed
    parent = Path(UNAVAILABLE_REGISTRY_PATH).parent
    parent.mkdir(parents=True, exist_ok=True)

    # Write atomically
    temp_path = f"{UNAVAILABLE_REGISTRY_PATH}.tmp"
    try:
        with open(temp_path, "w") as f:
            json.dump(unavailable, f, indent=2)
        os.replace(temp_path, UNAVAILABLE_REGISTRY_PATH)
        logger.debug("saved unavailable model — model_id=%s reason=%s", model_id, reason)
    except OSError as e:
        logger.error(
            "failed to save unavailable model: %s",
            e,
            exc_info=True,
        )
        raise


def _uses_doubleword(config: ExperimentConfig) -> bool:
    """Check if the config uses any DoubleWord models.

    Args:
        config: Experiment configuration.

    Returns:
        True if any embedding model uses the "doubleword" provider.
    """
    return any(provider_for_model(m) == "doubleword" for m in config.embedding.models)


def validate_doubleword_readiness(config: ExperimentConfig) -> None:
    """Validate that DoubleWord is ready for embedding sweeps.

    Checks:
    1. If any model uses provider="doubleword", DOUBLEWORD_API_KEY must be set.
    2. For each DoubleWord model, check the unavailable registry.

    Args:
        config: Experiment configuration.

    Raises:
        HTTPException(422): If DOUBLEWORD_API_KEY is missing or a model is unavailable.
    """
    if not _uses_doubleword(config):
        return

    # Check API key
    if settings.doubleword_api_key is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "DoubleWord experiment requires DOUBLEWORD_API_KEY. "
                "Set DOUBLEWORD_API_KEY in .env or the environment. "
                "See docs/user-guide/doubleword-setup.md"
            ),
        )

    # Check unavailable models
    unavailable = load_unavailable_models()
    for model_id in config.embedding.models:
        if provider_for_model(model_id) == "doubleword" and model_id in unavailable:
            reason = unavailable[model_id]
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Model {model_id!r} is unavailable: {reason}. "
                    f"To clear: delete its entry from {UNAVAILABLE_REGISTRY_PATH} — "
                    "the server reloads on next submit."
                ),
            )
