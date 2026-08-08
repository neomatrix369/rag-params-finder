"""server.core.atlas_storage unit tests — MongoDB Atlas storage quota.

Author: nWave acceptance-designer
Created: 2026-08-07
Scope: server/core/atlas_storage.py — unit-tier with httpx mocking
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from server.core.atlas_storage import (
    resolve_storage_limit_mb,
    resolve_tier_specs,
)


class TestResolveStorageLimitMbShould:
    """Scenario: resolve_storage_limit_mb returns cluster quota."""

    def test_returns_override_when_set(self) -> None:
        """
        Scenario: resolve_storage_limit_mb returns override if configured.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given mongodb_storage_limit_mb override > 0 in settings
        When resolve_storage_limit_mb is called
        Then it returns the override value.
        """
        ### Given / When
        with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 1024.0):
            with patch("server.core.atlas_storage.settings.mongodb_uri", "mongodb://localhost"):
                result = resolve_storage_limit_mb()

        ### Then
        assert result == 1024.0

    def test_returns_none_for_local_uri(self) -> None:
        """
        Scenario: resolve_storage_limit_mb returns None for local MongoDB.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given a local MongoDB connection string
        When resolve_storage_limit_mb is called
        Then it returns None (quota unknown for local).
        """
        ### Given / When
        with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
            with patch(
                "server.core.atlas_storage.settings.mongodb_uri", "mongodb://localhost:27017"
            ):
                with patch("server.core.atlas_storage.is_atlas_uri", return_value=False):
                    result = resolve_storage_limit_mb()

        ### Then
        assert result is None

    def test_returns_none_when_api_not_configured(self) -> None:
        """
        Scenario: resolve_storage_limit_mb returns None when API credentials missing.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given Atlas URI but missing API credentials
        When resolve_storage_limit_mb is called
        Then it returns None.
        """
        ### Given / When
        with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
            with patch("server.core.atlas_storage.settings.mongodb_uri", "mongodb+srv://cloud"):
                with patch("server.core.atlas_storage.is_atlas_uri", return_value=True):
                    with patch("server.core.atlas_storage.settings.atlas_public_key", ""):
                        result = resolve_storage_limit_mb()

        ### Then
        assert result is None

    def test_caches_result(self) -> None:
        """
        Scenario: resolve_storage_limit_mb caches result for 300 seconds.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given a quota lookup
        When resolve_storage_limit_mb is called twice within TTL
        Then it returns cached value on second call.
        """
        ### Given
        with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
            with patch("server.core.atlas_storage.is_atlas_uri", return_value=True):
                with patch("server.core.atlas_storage._atlas_api_configured", return_value=True):
                    with patch(
                        "server.core.atlas_storage._cached_atlas_storage_limit_mb",
                        return_value=2048.0,
                    ):
                        result1 = resolve_storage_limit_mb()
                        result2 = resolve_storage_limit_mb()

        ### Then
        assert result1 == result2


class TestResolveTierSpecsShould:
    """Scenario: resolve_tier_specs returns cluster tier information."""

    def test_returns_override_specs_when_storage_set(self) -> None:
        """
        Scenario: resolve_tier_specs returns manual tier when storage override set.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given mongodb_storage_limit_mb override configured
        When resolve_tier_specs is called
        Then it returns spec dict with manual tier type.
        """
        ### Given / When
        with patch("server.core.atlas_storage._tier_cache", None):
            with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 1024.0):
                with patch("server.core.atlas_storage.is_atlas_uri", return_value=False):
                    result = resolve_tier_specs()

        ### Then
        assert result is not None
        assert result["tier_type"] == "manual"
        assert result["storage_mb"] == 1024.0

    def test_returns_none_for_local_uri(self) -> None:
        """
        Scenario: resolve_tier_specs returns None for local MongoDB.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given a local connection string
        When resolve_tier_specs is called
        Then it returns None.
        """
        ### Given / When
        with patch("server.core.atlas_storage._tier_cache", None):
            with patch("server.core.atlas_storage.settings.mongodb_uri", "mongodb://localhost"):
                with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
                    with patch("server.core.atlas_storage.is_atlas_uri", return_value=False):
                        result = resolve_tier_specs()

        ### Then
        assert result is None

    def test_returns_none_when_api_not_configured(self) -> None:
        """
        Scenario: resolve_tier_specs returns None when API credentials missing.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given Atlas URI but missing credentials
        When resolve_tier_specs is called
        Then it returns None.
        """
        ### Given / When
        with patch("server.core.atlas_storage._tier_cache", None):
            with patch("server.core.atlas_storage.settings.mongodb_uri", "mongodb+srv://cloud"):
                with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
                    with patch("server.core.atlas_storage.is_atlas_uri", return_value=True):
                        with patch(
                            "server.core.atlas_storage._atlas_api_configured", return_value=False
                        ):  # noqa: E501
                            result = resolve_tier_specs()

        ### Then
        assert result is None

    def test_fetches_from_atlas_api(self) -> None:
        """
        Scenario: resolve_tier_specs calls Atlas API to fetch tier.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given valid Atlas URI + credentials
        When resolve_tier_specs is called
        Then it calls _fetch_atlas_tier_specs.
        """
        ### Given / When
        with patch("server.core.atlas_storage._tier_cache", None):
            with patch("server.core.atlas_storage.settings.mongodb_uri", "mongodb+srv://cloud"):
                with patch("server.core.atlas_storage.settings.mongodb_storage_limit_mb", 0):
                    with patch("server.core.atlas_storage.is_atlas_uri", return_value=True):
                        with patch(
                            "server.core.atlas_storage._atlas_api_configured", return_value=True
                        ):  # noqa: E501
                            with patch(
                                "server.core.atlas_storage._fetch_atlas_tier_specs"
                            ) as mock_fetch:  # noqa: E501
                                mock_fetch.return_value = {
                                    "instance_size": "M10",
                                    "storage_mb": 10240.0,
                                    "tier_type": "dedicated",
                                    "provider": "AWS",
                                    "region": "US_EAST_1",
                                }
                                result = resolve_tier_specs()

        ### Then
        mock_fetch.assert_called_once()
        assert result["instance_size"] == "M10"


class TestFetchAtlasStorageLimitShould:
    """Scenario: _fetch_atlas_storage_limit_mb calls Atlas Admin API."""

    def test_fetch_succeeds_on_200(self) -> None:
        """
        Scenario: fetch returns storage limit from cluster API response.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given Atlas Admin API returns cluster info with diskSizeGB
        When _fetch_atlas_storage_limit_mb is called
        Then it returns storage in MB.
        """
        ### Given
        cluster_response = {
            "diskSizeGB": 50,
            "providerSettings": {"instanceSizeName": "M10"},
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = cluster_response
        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_resp
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch(
                            "server.core.atlas_storage.settings.mongodb_uri", "mongodb+srv://..."
                        ):
                            with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                                from server.core.atlas_storage import _fetch_atlas_storage_limit_mb

                                result = _fetch_atlas_storage_limit_mb()

        ### Then
        assert result == 50 * 1024  # diskSizeGB to MB

    def test_fetch_returns_none_on_api_error(self) -> None:
        """
        Scenario: _fetch_atlas_storage_limit_mb returns None on API error.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given Atlas API raises HTTPError
        When _fetch_atlas_storage_limit_mb is called
        Then it returns None (logs warning).
        """
        ### Given
        mock_http_client = MagicMock()
        mock_http_client.get.side_effect = httpx.HTTPError("Connection refused")
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                            from server.core.atlas_storage import _fetch_atlas_storage_limit_mb

                            result = _fetch_atlas_storage_limit_mb()

        ### Then
        assert result is None

    def test_fetch_returns_none_when_cluster_name_missing(self) -> None:
        """
        Scenario: _fetch_atlas_storage_limit_mb returns None when cluster name unknown.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given cluster name cannot be derived from URI
        When _fetch_atlas_storage_limit_mb is called
        Then it returns None.
        """
        ### Given
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", ""):
            with patch("server.core.atlas_storage.parse_atlas_cluster_name", return_value=None):
                from server.core.atlas_storage import _fetch_atlas_storage_limit_mb

                result = _fetch_atlas_storage_limit_mb()

        ### Then
        assert result is None


class TestFetchAtlasTierSpecsShould:
    """Scenario: _fetch_atlas_tier_specs fetches and extracts tier info."""

    def test_fetch_dedicated_tier(self) -> None:
        """
        Scenario: fetch returns dedicated tier specs with diskSizeGB.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given a dedicated cluster response from Atlas
        When _fetch_atlas_tier_specs is called
        Then it returns tier specs including storage.
        """
        ### Given
        cluster_response = {
            "providerSettings": {
                "instanceSizeName": "M10",
                "providerName": "AWS",
                "backingProviderName": "AWS",
                "regionName": "US_EAST_1",
            },
            "diskSizeGB": 50,
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = cluster_response
        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_resp
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                            from server.core.atlas_storage import _fetch_atlas_tier_specs

                            result = _fetch_atlas_tier_specs()

        ### Then
        assert result["instance_size"] == "M10"
        assert result["tier_type"] == "dedicated"
        assert result["storage_mb"] == 50 * 1024

    def test_fetch_shared_tier_with_fallback(self) -> None:
        """
        Scenario: fetch uses TIER_STORAGE_LIMIT_MB fallback for shared tier.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given an M0 (shared) cluster without diskSizeGB
        When _fetch_atlas_tier_specs is called
        Then it uses fallback storage from TIER_STORAGE_LIMIT_MB.
        """
        ### Given
        cluster_response = {
            "providerSettings": {
                "instanceSizeName": "M0",
                "providerName": "TENANT",
                "backingProviderName": "AWS",
                "regionName": "US_EAST_1",
            },
            "diskSizeGB": None,
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = cluster_response
        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_resp
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                            from server.core.atlas_storage import _fetch_atlas_tier_specs

                            result = _fetch_atlas_tier_specs()

        ### Then
        assert result["instance_size"] == "M0"
        assert result["tier_type"] == "shared"
        assert result["storage_mb"] == 512.0  # M0 fallback

    def test_fetch_returns_none_on_missing_instance_size(self) -> None:
        """
        Scenario: _fetch_atlas_tier_specs returns None if instance size missing.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given cluster response without instance size
        When _fetch_atlas_tier_specs is called
        Then it returns None.
        """
        ### Given
        cluster_response = {
            "providerSettings": {
                "instanceSizeName": None,
                "providerName": "AWS",
            },
            "diskSizeGB": 50,
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = cluster_response
        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_resp
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                            from server.core.atlas_storage import _fetch_atlas_tier_specs

                            result = _fetch_atlas_tier_specs()

        ### Then
        assert result is None

    def test_fetch_returns_none_on_api_error(self) -> None:
        """
        Scenario: _fetch_atlas_tier_specs returns None on HTTPError.
        Slice: coverage-gap — server/core/atlas_storage.py

        Given Atlas API raises error
        When _fetch_atlas_tier_specs is called
        Then it returns None.
        """
        ### Given
        mock_http_client = MagicMock()
        mock_http_client.get.side_effect = httpx.HTTPError("API error")
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        ### When
        with patch("server.core.atlas_storage.settings.atlas_cluster_name", "cluster-1"):
            with patch("server.core.atlas_storage.settings.atlas_group_id", "group-1"):
                with patch("server.core.atlas_storage.settings.atlas_public_key", "key"):
                    with patch("server.core.atlas_storage.settings.atlas_private_key", "secret"):
                        with patch("server.core.atlas_storage.httpx.Client", mock_client_cls):
                            from server.core.atlas_storage import _fetch_atlas_tier_specs

                            result = _fetch_atlas_tier_specs()

        ### Then
        assert result is None
