"""Elasticsearch catalog facts that do not import the Elasticsearch client."""

from __future__ import annotations

from server.db.elasticsearch.mapping import SUPPORTED_DIMS, VECTOR_FIELDS, index_name_for
from server.db.ports.vector_store import VectorCapabilities
from server.models.enums import RetrievalMethod
from server.settings import settings

_PROVIDER = "elasticsearch"
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


class ElasticsearchCatalog:
    """Classmethods the public store catalog reads without the ES client extra."""

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return {"index": "Index", "host": "Host", "section": "Index & Host"}

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return {
            "index": index_name_for(settings.elasticsearch_index_prefix),
            "fields": sorted(VECTOR_FIELDS.values()),
            "index_type": "hnsw",
        }
