"""MongoDB URI helper tests."""

from __future__ import annotations

from server.db.mongodb_uri import is_atlas_uri, mongo_client_kwargs


def test_is_atlas_uri_true_for_cloud_srv() -> None:
    assert is_atlas_uri("mongodb+srv://user:pass@cluster.mongodb.net/db")


def test_is_atlas_uri_false_for_local_host() -> None:
    assert not is_atlas_uri("mongodb://localhost:27017/rag_params_finder?directConnection=true")


def test_mongo_client_kwargs_adds_tls_for_atlas_only() -> None:
    cloud = mongo_client_kwargs("mongodb+srv://c.mongodb.net/db")
    local = mongo_client_kwargs("mongodb://mongodb-local:27017/rag_params_finder")

    assert "tlsCAFile" in cloud
    assert "tlsCAFile" not in local
