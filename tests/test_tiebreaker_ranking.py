"""Test tiebreaker logic for ranked configurations.

When multiple configurations achieve the same max score, verify they are ranked by:
1. max_score (DESC) — primary quality metric
2. avg_score (DESC) — consistency across queries
3. chunk_size (ASC) — smaller = faster processing + less storage
4. overlap (ASC) — smaller = fewer duplicate chunks
5. padding (ASC) — smaller = less merge-forward padding
"""

from server.core.results_analyzer import analyze_results


def test_tiebreaker_when_multiple_configs_have_same_max_score():
    """Verify tiebreaker logic when configs tie on max score."""
    # Setup: 3 configs with 100% max score but different avg scores and chunk sizes
    run_statuses = [
        {
            "run_id": "run1",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 100,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
        {
            "run_id": "run2",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 1024,
            "overlap": 50,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
        {
            "run_id": "run3",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 1024,
            "overlap": 100,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
    ]

    # All configs achieve perfect scores (normalized to 0-100)
    # run1: 512/100, avg 62%
    # run2: 1024/50, avg 62%
    # run3: 1024/100, avg 62%
    query_results = [
        {
            "run_id": "run1",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk1"}}],
        },
        {
            "run_id": "run2",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk2"}}],
        },
        {
            "run_id": "run3",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk3"}}],
        },
    ]

    result = analyze_results(query_results, run_statuses)

    # Verify ranking (when avg scores are tied, prefer smaller chunk size, then smaller overlap)
    assert len(result["ranked_configs"]) == 3

    # #1 should be 512/100 (smallest chunk size)
    assert result["ranked_configs"][0]["rank"] == 1
    assert result["ranked_configs"][0]["chunk_size"] == 512
    assert result["ranked_configs"][0]["overlap"] == 100

    # #2 should be 1024/50 (same chunk size as #3, but smaller overlap)
    assert result["ranked_configs"][1]["rank"] == 2
    assert result["ranked_configs"][1]["chunk_size"] == 1024
    assert result["ranked_configs"][1]["overlap"] == 50

    # #3 should be 1024/100 (largest overlap)
    assert result["ranked_configs"][2]["rank"] == 3
    assert result["ranked_configs"][2]["chunk_size"] == 1024
    assert result["ranked_configs"][2]["overlap"] == 100

    # Verify best_params includes tied_count
    assert result["best_params"]["tied_count"] == 3
    assert result["best_params"]["chunk_size"] == 512


def test_no_tied_count_when_unique_max_scores():
    """When configs have different max scores, tied_count should reflect only #1."""
    run_statuses = [
        {
            "run_id": "run1",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 100,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
        {
            "run_id": "run2",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 1024,
            "overlap": 100,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
    ]

    # Different scores: run1 gets 100, run2 gets 80
    query_results = [
        {
            "run_id": "run1",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk1"}}],
        },
        {
            "run_id": "run2",
            "query_text": "query1",
            "results": [{"dense_score": 0.8, "chunk": {"text": "chunk2"}}],
        },
    ]

    result = analyze_results(query_results, run_statuses)

    # Only 1 config achieves max score
    assert result["best_params"]["tied_count"] == 1
    assert result["best_params"]["max_score"] == 100
    assert result["ranked_configs"][1]["max_score"] < 100


def test_weighted_avg_vs_unweighted_avg():
    """Verify weighted (query-level) avg differs from unweighted (chunk-level) avg.

    When one query returns more chunks than another, the weighted avg should
    give each query equal weight, while unweighted avg gives each chunk equal weight.
    """
    run_statuses = [
        {
            "run_id": "run1",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 100,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
    ]

    # Query 1: 5 chunks with scores [100, 100, 95, 90, 85] → query avg = 94%
    # Query 2: 3 chunks with scores [80, 75, 70] → query avg = 75%
    #
    # Unweighted avg: (100+100+95+90+85+80+75+70) / 8 = 695 / 8 = 86.875% → rounds to 87%
    # Weighted avg: (94 + 75) / 2 = 84.5% → rounds to 84% or 85%
    query_results = [
        {
            "run_id": "run1",
            "query_text": "query1",
            "results": [
                {"dense_score": 1.0, "chunk": {"text": "chunk1"}},
                {"dense_score": 1.0, "chunk": {"text": "chunk2"}},
                {"dense_score": 0.95, "chunk": {"text": "chunk3"}},
                {"dense_score": 0.90, "chunk": {"text": "chunk4"}},
                {"dense_score": 0.85, "chunk": {"text": "chunk5"}},
            ],
        },
        {
            "run_id": "run1",
            "query_text": "query2",
            "results": [
                {"dense_score": 0.80, "chunk": {"text": "chunk6"}},
                {"dense_score": 0.75, "chunk": {"text": "chunk7"}},
                {"dense_score": 0.70, "chunk": {"text": "chunk8"}},
            ],
        },
    ]

    result = analyze_results(query_results, run_statuses)
    config = result["ranked_configs"][0]

    # Verify both metrics are present
    assert "avg_score" in config
    assert "query_avg_score" in config

    # After normalization (min=0.70, max=1.0, range=0.30):
    # Query 1 scores: [100, 100, 83, 67, 50] → avg = 80%
    # Query 2 scores: [33, 17, 0] → avg = 16.67%
    #
    # Unweighted avg: (100+100+83+67+50+33+17+0) / 8 = 450/8 = 56.25% → rounds to 56%
    # Weighted avg: (80 + 16.67) / 2 = 48.33% → rounds to 48%

    # Verify the calculated values (normalized scores)
    assert config["avg_score"] == 56  # Unweighted (chunk-level)
    assert config["query_avg_score"] == 48  # Weighted (query-level)

    # Key insight: weighted avg is LOWER because Query 2's low scores
    # get equal weight (not drowned out by Query 1's high scores)
    assert config["query_avg_score"] < config["avg_score"]


def test_same_padding_collapses_to_one_ranked_config():
    """Runs that differ only by run_id but share padding merge into one config."""
    run_statuses = [
        {
            "run_id": "run-a",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 50,
            "padding": 0,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
        {
            "run_id": "run-b",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 50,
            "padding": 0,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
    ]

    query_results = [
        {
            "run_id": "run-a",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk-a"}}],
        },
        {
            "run_id": "run-b",
            "query_text": "query1",
            "results": [{"dense_score": 0.9, "chunk": {"text": "chunk-b"}}],
        },
    ]

    result = analyze_results(query_results, run_statuses)

    assert len(result["ranked_configs"]) == 1
    assert result["ranked_configs"][0]["padding"] == 0


def test_padding_distinguishes_ranked_configs():
    """Two runs identical except padding produce two distinct ranked configs."""
    run_statuses = [
        {
            "run_id": "run-padding-0",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 50,
            "padding": 0,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
        {
            "run_id": "run-padding-50",
            "database_provider": "mongodb",
            "embedding_provider": "local",
            "embedding_model": "all-MiniLM-L6-v2",
            "chunking_method": "semantic",
            "chunk_size": 512,
            "overlap": 50,
            "padding": 50,
            "retrieval_method": "sparse",
            "retrieval_provider": "local",
            "retrievers": [{"type": "sparse"}],
        },
    ]

    query_results = [
        {
            "run_id": "run-padding-0",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk-a"}}],
        },
        {
            "run_id": "run-padding-50",
            "query_text": "query1",
            "results": [{"dense_score": 1.0, "chunk": {"text": "chunk-b"}}],
        },
    ]

    result = analyze_results(query_results, run_statuses)

    assert len(result["ranked_configs"]) == 2
    paddings = sorted(c["padding"] for c in result["ranked_configs"])
    assert paddings == [0, 50]
    assert {d["padding"] for d in result["detailed_results"]} == {0, 50}
