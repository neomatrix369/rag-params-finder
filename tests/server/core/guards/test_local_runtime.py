"""Local store image pins stay aligned with docker-compose.yml.

Author: RAG Params Finder contributors
Created: 2026-09-27
Scope: local_runtime image and container defaults
"""

from __future__ import annotations

from pathlib import Path

from server.core.guards.local_runtime import LOCAL_STORE_IMAGES, local_runtime_fields

_COMPOSE = Path(__file__).resolve().parents[4] / "docker-compose.yml"


def test_local_store_images_match_compose_pins() -> None:
    """
    Scenario: Dashboard image labels use the Compose pins.

    Given docker-compose.yml pins each local store image,
    When the health runtime map is read,
    Then each image line is present in that file.
    """
    ### Given
    text = _COMPOSE.read_text(encoding="utf-8")

    ### When / Then
    for provider, image in LOCAL_STORE_IMAGES.items():
        assert f"image: {image}" in text
        assert f"rag-params-finder-{provider}-local" in text


def test_cloud_mode_has_no_local_runtime_fields() -> None:
    """
    Scenario: Cloud mode does not invent a container.

    Given a cloud storage mode,
    When local runtime fields are requested,
    Then the result is empty.
    """
    ### Given / When
    fields = local_runtime_fields("elasticsearch", "elasticsearch-cloud")

    ### Then
    assert fields == {}
