from pathlib import Path
from typing import Any

import yaml

from server.core.model_registry import (
    EMBEDDING_MODELS,
    RERANKER_MODELS,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: str) -> dict[str, Any]:
    """Load and validate YAML configuration file."""
    path = Path(config_path)
    logger.debug("config resolve — path=%s", path.resolve())

    if not path.exists():
        logger.error("config load failed — file not found: %s", config_path)
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        config: dict[str, Any] = yaml.safe_load(f)

    logger.info("config load OK — %s (%s top-level keys)", config_path, len(config))
    _validate_models(config)
    return config


def _validate_models(config: dict) -> None:
    """Validate embedding and reranker models against declared providers."""
    embedding_cfg = config.get("embedding", {})
    declared_provider = embedding_cfg.get("provider", "local")
    embedding_models = embedding_cfg.get("models", [])

    for model_id in embedding_models:
        info = EMBEDDING_MODELS.get(model_id)
        if info is None:
            known = ", ".join(EMBEDDING_MODELS)
            raise ValueError(f"Unknown embedding model '{model_id}' in config. Known: {known}")
        if info["provider"] != declared_provider:
            raise ValueError(
                f"Embedding model '{model_id}' belongs to provider "
                f"'{info['provider']}', but config declares provider '{declared_provider}'"
            )
        logger.info(
            "config validate — embedding model %s → provider=%s dim=%s",
            model_id,
            declared_provider,
            info["dimensions"],
        )

    retrieval_cfg = config.get("retrieval", {})
    rerank_provider = retrieval_cfg.get("rerank_provider", "local")
    rerank_model = retrieval_cfg.get("rerank_model")

    if rerank_model:
        rerank_info = RERANKER_MODELS.get(rerank_model)
        if rerank_info is None:
            known = ", ".join(RERANKER_MODELS)
            raise ValueError(f"Unknown reranker model '{rerank_model}' in config. Known: {known}")
        if rerank_info["provider"] != rerank_provider:
            raise ValueError(
                f"Reranker model '{rerank_model}' belongs to provider "
                f"'{rerank_info['provider']}', but config declares "
                f"rerank_provider '{rerank_provider}'"
            )
        logger.info(
            "config validate — reranker model %s → provider=%s",
            rerank_model,
            rerank_provider,
        )
