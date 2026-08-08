"""server.db.mongo.indexes unit tests.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: server/db/mongo/indexes.py — unit-tier with pymongo mocking
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.db.mongo.indexes import (
    create_text_search_index,
    create_vector_index,
    create_vector_indexes,
    drop_search_index_at,
    ensure_required_search_indexes,
    known_search_index_names,
    list_cluster_search_indexes,
    prune_unknown_search_indexes,
    reconcile_chunks_search_indexes,
    reset_chunks_search_indexes,
)


class TestKnownSearchIndexNamesShould:
    """Scenario: known_search_index_names returns managed index names."""

    def test_known_search_index_names_includes_vector_indexes(self) -> None:
        """
        Scenario: known_search_index_names includes all vector indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given no arguments
        When known_search_index_names is called
        Then it returns frozenset with vector_index_1024, vector_index_384, vector_index_30522.
        """
        ### Given / When
        names = known_search_index_names()

        ### Then
        assert "vector_index_1024" in names
        assert "vector_index_384" in names
        assert "vector_index_30522" in names
        assert "text_search_index" in names
        assert len(names) == 4


class TestListClusterSearchIndexesShould:
    """Scenario: list_cluster_search_indexes queries all databases."""

    def test_list_cluster_search_indexes_empty_cluster(self) -> None:
        """
        Scenario: list_cluster_search_indexes returns empty list on empty cluster.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given an empty MongoDB cluster
        When list_cluster_search_indexes is called
        Then it returns empty list.
        """
        ### Given
        mock_client = MagicMock()
        mock_client.list_database_names.return_value = []

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            result = list_cluster_search_indexes()

        ### Then
        assert result == []

    def test_list_cluster_search_indexes_marks_known_indexes(self) -> None:
        """
        Scenario: list_cluster_search_indexes marks known vs unknown indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given a database with known and unknown search indexes
        When list_cluster_search_indexes is called
        Then it marks known=True/False per index name.
        """
        ### Given
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_coll = MagicMock()

        mock_client.list_database_names.return_value = ["rag_params_finder"]
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = ["chunks"]
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.list_search_indexes.return_value = [
            {"name": "vector_index_1024", "type": "vectorSearch", "status": "READY"},
            {"name": "unknown_index", "type": "vectorSearch", "status": "READY"},
        ]

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            result = list_cluster_search_indexes()

        ### Then
        assert len(result) == 2
        known = [r for r in result if r["known"]]
        unknown = [r for r in result if not r["known"]]
        assert len(known) == 1
        assert known[0]["name"] == "vector_index_1024"
        assert len(unknown) == 1
        assert unknown[0]["name"] == "unknown_index"

    def test_list_cluster_search_indexes_skips_on_error(self) -> None:
        """
        Scenario: list_cluster_search_indexes skips collections with errors.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given a collection that raises on list_search_indexes
        When list_cluster_search_indexes is called
        Then it skips that collection and continues.
        """
        ### Given
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_coll = MagicMock()

        mock_client.list_database_names.return_value = ["rag_params_finder"]
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = ["chunks"]
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.list_search_indexes.side_effect = Exception("Connection failed")

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            result = list_cluster_search_indexes()

        ### Then
        assert result == []


class TestDropSearchIndexAtShould:
    """Scenario: drop_search_index_at drops a named index."""

    def test_drop_search_index_at_calls_drop(self) -> None:
        """
        Scenario: drop_search_index_at calls collection.drop_search_index.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given database, collection, and index names
        When drop_search_index_at is called
        Then it calls drop_search_index on the collection.
        """
        ### Given
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_coll = MagicMock()

        mock_client.__getitem__.side_effect = (
            lambda name: mock_db if name == "rag_db" else mock_coll
        )  # noqa: E501
        mock_db.__getitem__.return_value = mock_coll

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            drop_search_index_at("rag_db", "chunks", "vector_index_1024")

        ### Then
        mock_coll.drop_search_index.assert_called_once_with("vector_index_1024")


class TestPruneUnknownSearchIndexesShould:
    """Scenario: prune_unknown_search_indexes drops unmanaged indexes."""

    def test_prune_unknown_drops_surplus_indexes(self) -> None:
        """
        Scenario: prune_unknown_search_indexes drops indexes not in known set.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given a cluster with known and unknown indexes
        When prune_unknown_search_indexes is called
        Then it drops only unknown indexes and returns list of dropped paths.
        """
        ### Given
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_coll = MagicMock()

        mock_client.list_database_names.return_value = ["rag_params_finder"]
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = ["chunks"]
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.list_search_indexes.return_value = [
            {"name": "vector_index_1024", "type": "vectorSearch", "status": "READY"},
            {"name": "random_index", "type": "vectorSearch", "status": "READY"},
        ]
        mock_coll.drop_search_index = MagicMock()

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            dropped = prune_unknown_search_indexes()

        ### Then
        assert len(dropped) == 1
        assert "random_index" in dropped[0]
        mock_coll.drop_search_index.assert_called_once_with("random_index")

    def test_prune_unknown_does_not_drop_known_indexes(self) -> None:
        """
        Scenario: prune_unknown_search_indexes keeps known indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given only known indexes exist
        When prune_unknown_search_indexes is called
        Then it does not drop anything.
        """
        ### Given
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_coll = MagicMock()

        mock_client.list_database_names.return_value = ["rag_params_finder"]
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = ["chunks"]
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.list_search_indexes.return_value = [
            {"name": "vector_index_1024", "type": "vectorSearch", "status": "READY"},
        ]
        mock_coll.drop_search_index = MagicMock()

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            dropped = prune_unknown_search_indexes()

        ### Then
        assert dropped == []
        mock_coll.drop_search_index.assert_not_called()


class TestResetChunksSearchIndexesShould:
    """Scenario: reset_chunks_search_indexes recreates search indexes."""

    def test_reset_drops_existing_indexes(self) -> None:
        """
        Scenario: reset_chunks_search_indexes drops all existing indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given chunks collection has search indexes
        When reset_chunks_search_indexes is called
        Then it drops all indexes.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = [
            {"name": "vector_index_1024"},
            {"name": "text_search_index"},
        ]
        mock_coll.drop_search_index = MagicMock()

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            with patch("server.db.mongo.indexes.create_vector_indexes"):
                with patch("server.db.mongo.indexes.create_text_search_index"):
                    reset_chunks_search_indexes()

        ### Then
        assert mock_coll.drop_search_index.call_count == 2

    def test_reset_recreates_indexes_after_drop(self) -> None:
        """
        Scenario: reset_chunks_search_indexes recreates indexes after drop.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given chunks collection
        When reset_chunks_search_indexes is called
        Then it calls create_vector_indexes and create_text_search_index.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = []

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            with patch("server.db.mongo.indexes.create_vector_indexes") as mock_vec:
                with patch("server.db.mongo.indexes.create_text_search_index") as mock_text:
                    reset_chunks_search_indexes()

        ### Then
        mock_vec.assert_called_once()
        mock_text.assert_called_once()


class TestCreateVectorIndexShould:
    """Scenario: create_vector_index creates or skips existing index."""

    def test_create_vector_index_already_exists(self) -> None:
        """
        Scenario: create_vector_index returns True if index exists.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given index already exists on collection
        When create_vector_index is called
        Then it returns True without recreating.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = [{"name": "vector_index_1024"}]

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            result = create_vector_index("vector_index_1024", 1024)

        ### Then
        assert result is True
        mock_coll.create_search_indexes.assert_not_called()

    def test_create_vector_index_creates_missing(self) -> None:
        """
        Scenario: create_vector_index creates index if missing.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given index does not exist
        When create_vector_index is called
        Then it calls create_search_indexes.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.side_effect = [
            [],
            [{"name": "vector_index_1024", "status": "READY"}],
        ]  # noqa: E501
        mock_coll.create_search_indexes = MagicMock()

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            with patch("server.db.mongo.indexes._wait_for_indexes_ready", return_value=True):
                result = create_vector_index("vector_index_1024", 1024)

        ### Then
        mock_coll.create_search_indexes.assert_called_once()
        assert result is True

    def test_create_vector_index_handles_unavailable_error(self) -> None:
        """
        Scenario: create_vector_index returns False on M0 quota limit.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given M0 free tier with index quota reached
        When create_vector_index is called
        Then it returns False (not raises).
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = []
        mock_coll.create_search_indexes.side_effect = Exception(
            "maximum number of fts indexes reached"
        )

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            result = create_vector_index("vector_index_1024", 1024)

        ### Then
        assert result is False


class TestCreateVectorIndexesShould:
    """Scenario: create_vector_indexes creates all missing indexes."""

    def test_create_vector_indexes_all_missing(self) -> None:
        """
        Scenario: create_vector_indexes creates all missing indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given no vector indexes exist
        When create_vector_indexes is called
        Then it creates all three standard indexes.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = []

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            with patch(
                "server.db.mongo.indexes.create_vector_index", return_value=True
            ) as mock_create:
                result = create_vector_indexes()

        ### Then
        assert result is True
        assert mock_create.call_count == 3

    def test_create_vector_indexes_all_exist(self) -> None:
        """
        Scenario: create_vector_indexes returns True if all exist.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given all vector indexes exist
        When create_vector_indexes is called
        Then it returns True without creating.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = [
            {"name": "vector_index_1024"},
            {"name": "vector_index_384"},
            {"name": "vector_index_30522"},
        ]

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            result = create_vector_indexes()

        ### Then
        assert result is True


class TestCreateTextSearchIndexShould:
    """Scenario: create_text_search_index creates BM25 index."""

    def test_create_text_search_index_already_exists(self) -> None:
        """
        Scenario: create_text_search_index returns True if exists.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given text_search_index already exists
        When create_text_search_index is called
        Then it returns True without recreating.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = [{"name": "text_search_index"}]

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            result = create_text_search_index()

        ### Then
        assert result is True
        mock_coll.create_search_indexes.assert_not_called()

    def test_create_text_search_index_creates_missing(self) -> None:
        """
        Scenario: create_text_search_index creates if missing.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given index does not exist
        When create_text_search_index is called
        Then it calls create_search_indexes.
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.side_effect = [
            [],
            [{"name": "text_search_index", "status": "READY"}],
        ]  # noqa: E501

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            with patch("server.db.mongo.indexes._wait_for_indexes_ready", return_value=True):
                result = create_text_search_index()

        ### Then
        mock_coll.create_search_indexes.assert_called_once()
        assert result is True

    def test_create_text_search_index_handles_quota_error(self) -> None:
        """
        Scenario: create_text_search_index returns False on quota error.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given M0 index quota reached
        When create_text_search_index is called
        Then it returns False (logs but does not raise).
        """
        ### Given
        mock_coll = MagicMock()
        mock_coll.list_search_indexes.return_value = []
        mock_coll.create_search_indexes.side_effect = Exception(
            "maximum number of fts indexes exceeded"
        )

        ### When
        with patch("server.db.mongo.indexes.get_collection", return_value=mock_coll):
            result = create_text_search_index()

        ### Then
        assert result is False


class TestEnsureRequiredSearchIndexesShould:
    """Scenario: ensure_required_search_indexes creates only needed indexes."""

    def test_ensure_required_indexes_subset(self) -> None:
        """
        Scenario: ensure_required_search_indexes creates only required ones.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given required indexes: {vector_index_1024, text_search_index}
        When ensure_required_search_indexes is called
        Then it creates only those two, not vector_index_384.
        """
        ### Given
        required = frozenset(["vector_index_1024", "text_search_index"])

        ### When
        with patch("server.db.mongo.indexes._ensure_standard_indexes"):
            with patch("server.db.mongo.indexes.create_vector_index") as mock_vec:
                with patch("server.db.mongo.indexes.create_text_search_index") as mock_text:
                    ensure_required_search_indexes(required)

        ### Then
        mock_vec.assert_called_once()
        mock_text.assert_called_once()

    def test_ensure_required_indexes_skips_unknown(self) -> None:
        """
        Scenario: ensure_required_search_indexes skips unknown index names.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given required indexes includes unknown name
        When ensure_required_search_indexes is called
        Then it skips the unknown name without error.
        """
        ### Given
        required = frozenset(["vector_index_1024", "unknown_index_name"])

        ### When
        with patch("server.db.mongo.indexes._ensure_standard_indexes"):
            with patch("server.db.mongo.indexes.create_vector_index") as mock_vec:
                ensure_required_search_indexes(required)

        ### Then
        # Only one vector index call, unknown_index_name is skipped
        mock_vec.assert_called_once()


class TestReconcileChunksSearchIndexesShould:
    """Scenario: reconcile_chunks_search_indexes drops failed/surplus indexes."""

    def test_reconcile_drops_failed_indexes(self) -> None:
        """
        Scenario: reconcile drops indexes with FAILED status.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given a failed vector index
        When reconcile_chunks_search_indexes is called
        Then it drops the failed index.
        """
        ### Given
        required = frozenset(["vector_index_1024"])

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.name = "rag_params_finder"

        mock_client.list_database_names.return_value = ["rag_params_finder"]
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names.return_value = ["chunks"]
        mock_db.__getitem__.return_value = MagicMock()

        mock_db.__getitem__.return_value.list_search_indexes.return_value = [
            {"name": "vector_index_1024", "status": "READY"},
            {"name": "vector_index_384", "status": "FAILED"},
        ]
        mock_db.__getitem__.return_value.drop_search_index = MagicMock()

        ### When
        with patch("server.db.mongo.indexes.get_mongo_client", return_value=mock_client):
            with patch("server.db.mongo.indexes.get_database", return_value=mock_db):
                with patch("server.db.mongo.indexes.list_cluster_search_indexes") as mock_list:
                    mock_list.return_value = [
                        {
                            "database": "rag_params_finder",
                            "collection": "chunks",
                            "name": "vector_index_1024",
                            "status": "READY",
                            "known": True,
                        },
                        {
                            "database": "rag_params_finder",
                            "collection": "chunks",
                            "name": "vector_index_384",
                            "status": "FAILED",
                            "known": True,
                        },
                    ]
                    dropped = reconcile_chunks_search_indexes(required)

        ### Then
        assert len(dropped) == 1
        assert "vector_index_384" in dropped[0]
        assert "failed" in dropped[0].lower()

    def test_reconcile_drops_surplus_indexes(self) -> None:
        """
        Scenario: reconcile drops known but unrequired indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given vector_index_384 not required but exists
        When reconcile_chunks_search_indexes is called
        Then it drops vector_index_384.
        """
        ### Given
        required = frozenset(["vector_index_1024"])

        mock_db = MagicMock()
        mock_db.name = "rag_params_finder"

        ### When
        with patch("server.db.mongo.indexes.get_database", return_value=mock_db):
            with patch("server.db.mongo.indexes.list_cluster_search_indexes") as mock_list:
                mock_list.return_value = [
                    {
                        "database": "rag_params_finder",
                        "collection": "chunks",
                        "name": "vector_index_1024",
                        "status": "READY",
                        "known": True,
                    },
                    {
                        "database": "rag_params_finder",
                        "collection": "chunks",
                        "name": "vector_index_384",
                        "status": "READY",
                        "known": True,
                    },
                ]
                with patch("server.db.mongo.indexes.drop_search_index_at"):
                    dropped = reconcile_chunks_search_indexes(required)

        ### Then
        assert len(dropped) == 1
        assert "vector_index_384" in dropped[0]
        assert "surplus" in dropped[0].lower()

    def test_reconcile_keeps_required_indexes(self) -> None:
        """
        Scenario: reconcile keeps required indexes.
        Slice: coverage-gap — server/db/mongo/indexes.py

        Given required indexes
        When reconcile_chunks_search_indexes is called
        Then it does not drop them.
        """
        ### Given
        required = frozenset(["vector_index_1024", "vector_index_384"])

        mock_db = MagicMock()
        mock_db.name = "rag_params_finder"

        ### When
        with patch("server.db.mongo.indexes.get_database", return_value=mock_db):
            with patch("server.db.mongo.indexes.list_cluster_search_indexes") as mock_list:
                mock_list.return_value = [
                    {
                        "database": "rag_params_finder",
                        "collection": "chunks",
                        "name": "vector_index_1024",
                        "status": "READY",
                        "known": True,
                    },
                    {
                        "database": "rag_params_finder",
                        "collection": "chunks",
                        "name": "vector_index_384",
                        "status": "READY",
                        "known": True,
                    },
                ]
                dropped = reconcile_chunks_search_indexes(required)

        ### Then
        assert dropped == []
