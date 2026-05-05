import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from server.utils.logger import get_logger

logger = get_logger(__name__)

CONFIGS_DIR = Path("configs")


@dataclass(frozen=True)
class Query:
    text: str
    persona_id: str
    focus: str | None


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https")


def _download_queries(url: str) -> Path:
    """Download a queries file from a URL into ./configs/ if not already cached."""
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

    filename = Path(urlparse(url).path).name or "queries.json"
    local_path = CONFIGS_DIR / filename

    if local_path.exists():
        logger.info(f"Queries file already cached: {local_path}")
        return local_path

    logger.info(f"Downloading queries from {url}")
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    local_path.write_bytes(response.content)
    logger.info(f"Saved queries to {local_path}")
    return local_path


def resolve_queries_file(queries_file: str) -> Path:
    """Resolve a queries_file value to a local Path, downloading if it's a URL."""
    if _is_url(queries_file):
        return _download_queries(queries_file)

    path = Path(queries_file)
    if not path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_file}")
    return path


def load_queries(queries_file: str) -> list[Query]:
    """Load all questions from a persona-based queries JSON file (local path or URL)."""
    path = resolve_queries_file(queries_file)
    data = json.loads(path.read_text())
    queries: list[Query] = []

    for persona in data.get("personas", []):
        persona_id = persona["id"]
        for question in persona.get("questions", []):
            queries.append(
                Query(
                    text=question["text"],
                    persona_id=persona_id,
                    focus=question.get("focus"),
                )
            )

    logger.info(f"Loaded {len(queries)} queries from {path}")
    return queries
