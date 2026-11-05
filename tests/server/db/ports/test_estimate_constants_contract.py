"""
Contract: the dashboard's storage-estimate wording mirrors the server's constants.

Author: RAG Params Finder contributors
Created: 2026-11-05
Scope: Slice 67D - frontend/src/components/stats/estimateLabels.ts hardcodes the bytes-per-dimension
       and metadata-bytes-per-chunk numbers that server/db/ports/stats_common.py uses for estimates.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.db.ports import stats_common

LABELS = Path(__file__).resolve().parents[4] / "frontend/src/components/stats/estimateLabels.ts"


def _frontend_constant(name: str) -> int:
    match = re.search(rf"export const {name} = (\d+);", LABELS.read_text())
    assert match, f"{name} not found in estimateLabels.ts"
    return int(match.group(1))


class TestEstimateConstantsContractShould:
    def test_bytes_per_dimension_match_the_server_float32_size(self) -> None:
        """
        Scenario: the "est." formula uses the server's vector byte size.
        Slice: 67D - estimate formula contract.
        """
        ### Given
        server_value = stats_common._BYTES_PER_FLOAT32

        ### When
        frontend_value = _frontend_constant("BYTES_PER_DIMENSION")

        ### Then
        assert frontend_value == server_value

    def test_metadata_bytes_per_chunk_match_the_server_estimate(self) -> None:
        """
        Scenario: the "est." formula uses the server's metadata size.
        Slice: 67D - estimate formula contract.
        """
        ### Given
        server_value = stats_common._METADATA_BYTES_PER_CHUNK

        ### When
        frontend_value = _frontend_constant("METADATA_BYTES_PER_CHUNK")

        ### Then
        assert frontend_value == server_value
