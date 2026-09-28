"""Mongo catalog facts that do not import pymongo."""

from __future__ import annotations

from server.db.mongo.search_index_names import CATALOG_INDEX_NAMES
from server.db.ports.vector_store import VectorCapabilities
from server.models.enums import RetrievalMethod

_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset(
        {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
    ),
    similarity_metrics=frozenset({"cosine"}),
    index_types=frozenset({"vectorSearch", "search"}),
    supported_embedding_dims=frozenset({384, 1024, 30522}),
    supports_metadata_filters=True,
    can_host_run_state=True,
    labels=frozenset({"mongodb", "atlas"}),
)


class MongoCatalog:
    """Classmethods the public store catalog reads without opening Mongo."""

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return {
            "index": "Collection",
            "host": "Atlas host",
            "section": "Cluster & Collection",
        }

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return {"indexes": list(CATALOG_INDEX_NAMES)}
