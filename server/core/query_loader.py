import json
from pathlib import Path
from dataclasses import dataclass

from server.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Query:
    text: str
    persona_id: str
    focus: str | None


def load_queries(queries_file: str) -> list[Query]:
    """Load all questions from a persona-based queries JSON file."""
    path = Path(queries_file)
    if not path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_file}")

    data = json.loads(path.read_text())
    queries: list[Query] = []

    for persona in data.get("personas", []):
        persona_id = persona["id"]
        for question in persona.get("questions", []):
            queries.append(Query(
                text=question["text"],
                persona_id=persona_id,
                focus=question.get("focus"),
            ))

    logger.info(f"Loaded {len(queries)} queries from {queries_file}")
    return queries
