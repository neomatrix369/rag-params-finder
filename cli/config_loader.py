import yaml
from pathlib import Path

from server.utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    path = Path(config_path)
    logger.debug(f"Resolving config path: {path.resolve()}")

    if not path.exists():
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded config from {config_path} ({len(config)} top-level keys)")
    return config
