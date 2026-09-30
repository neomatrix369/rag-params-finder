"""Redis catalog facts that do not import the redis-py client."""

from __future__ import annotations

from server.db.ports.vector_store import VectorCapabilities
from server.db.redis.schema import SUPPORTED_DIMS, index_name_for
from server.models.enums import RetrievalMethod
from server.settings import settings

_PROVIDER = "redis"
_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset(
        {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
    ),
    similarity_metrics=frozenset({"cosine"}),
    index_types=frozenset({"hnsw"}),
    supported_embedding_dims=SUPPORTED_DIMS,
    supports_metadata_filters=True,
    can_host_run_state=False,
    labels=frozenset({_PROVIDER}),
)


class RedisCatalog:
    """Classmethods the public store catalog reads without the redis-py extra."""

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return {"index": "Index", "host": "Host", "section": "Index & Host"}

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return {
            "index": index_name_for(getattr(settings, "redis_index_prefix", "rpf")),
            "fields": sorted(["embedding_384", "embedding_1024"]),
            "index_type": "hnsw",
        }
