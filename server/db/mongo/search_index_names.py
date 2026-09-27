"""Atlas search index names shared by the catalog and the Mongo index builder.

Kept out of ``indexes.py`` so a catalog read does not import pymongo.
"""

from __future__ import annotations

VECTOR_INDEX_1024 = "vector_index_1024"
VECTOR_INDEX_384 = "vector_index_384"
VECTOR_INDEX_30522 = "vector_index_30522"
TEXT_SEARCH_INDEX_NAME = "text_search_index"

# Order matches the dashboard index summary: vector indexes, then text.
CATALOG_INDEX_NAMES: tuple[str, ...] = (
    VECTOR_INDEX_1024,
    VECTOR_INDEX_384,
    VECTOR_INDEX_30522,
    TEXT_SEARCH_INDEX_NAME,
)
