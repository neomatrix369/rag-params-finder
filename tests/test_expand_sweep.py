"""Tests for sweep expansion — one retriever per run."""

import pytest
from pydantic import ValidationError

from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    expand_sweep,
)
from server.models.enums import ChunkingMethod, RetrieverType


def _minimal_config(retrievers: list[RetrieverConfig]) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="test-sweep",
        data_paths=["./input_data/pdfs/sample.pdf"],
        queries_file="./configs/questions.example.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[256], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(retrievers=retrievers),
        execution=ExecutionConfig(),
    )


def test_each_retriever_creates_separate_run_with_single_entry() -> None:
    config = _minimal_config(
        [
            RetrieverConfig(type=RetrieverType.DENSE),
            RetrieverConfig(
                type=RetrieverType.CROSS_ENCODER,
                provider="local",
                model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            ),
        ]
    )

    runs = expand_sweep(config)

    assert len(runs) == 2
    assert runs[0].retrievers == [RetrieverConfig(type=RetrieverType.DENSE)]
    assert runs[1].retrievers == [
        RetrieverConfig(
            type=RetrieverType.CROSS_ENCODER,
            provider="local",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )
    ]


def test_reranker_run_does_not_include_dense_in_retrievers_list() -> None:
    config = _minimal_config(
        [
            RetrieverConfig(
                type=RetrieverType.RERANKER,
                provider="voyage",
                model="rerank-2.5-lite",
            )
        ]
    )

    runs = expand_sweep(config)

    assert len(runs) == 1
    assert len(runs[0].retrievers) == 1
    assert runs[0].retrievers[0].type == RetrieverType.RERANKER
    assert runs[0].retrieval_model == "rerank-2.5-lite"


def test_old_config_format_migrates_to_separate_sweep_entries() -> None:
    config = ExperimentConfig(
        experiment_name="legacy",
        data_paths=["./input_data/pdfs/sample.pdf"],
        queries_file="./configs/questions.example.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[256], overlaps=[50]),
        ),
        retrieval=RetrievalConfig(
            methods=["dense", "sparse"],
            retrieval_provider="local",
            retrieval_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
        execution=ExecutionConfig(),
    )

    runs = expand_sweep(config)

    assert len(runs) == 3
    retriever_types = [run.retrievers[0].type for run in runs]
    assert retriever_types == [
        RetrieverType.DENSE,
        RetrieverType.SPARSE,
        RetrieverType.RERANKER,
    ]
    assert all(len(run.retrievers) == 1 for run in runs)


def test_bayesian_requires_fixed_embedding_model() -> None:
    with pytest.raises(ValidationError):
        ExperimentConfig(
            experiment_name="invalid-bayes-embedding",
            data_paths=["./input_data/pdfs/sample.pdf"],
            queries_file="./configs/questions.example.json",
            embedding=EmbeddingConfig(
                provider="local", models=["all-MiniLM-L6-v2", "all-MiniLM-L6-v2"]
            ),
            chunking=ChunkingConfig(
                methods=[ChunkingMethod.RECURSIVE],
                params=ChunkParams(chunk_sizes=[128, 256], overlaps=[50]),
            ),
            retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
            execution=ExecutionConfig(search_strategy="bayesian"),
        )


@pytest.mark.parametrize(
    "invalid_field",
    ["chunking_methods", "retrievers"],
)
def test_bayesian_requires_single_fixed_nonchunk_axes(invalid_field: str) -> None:
    kwargs = {
        "experiment_name": "invalid-bayes-" + invalid_field,
        "data_paths": ["./input_data/pdfs/sample.pdf"],
        "queries_file": "./configs/questions.example.json",
        "embedding": EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        "chunking": ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[128, 256], overlaps=[50]),
        ),
        "retrieval": RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        "execution": ExecutionConfig(search_strategy="bayesian"),
    }

    if invalid_field == "chunking_methods":
        kwargs["chunking"] = ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE, ChunkingMethod.FIXED],
            params=ChunkParams(chunk_sizes=[128, 256], overlaps=[50]),
        )
    if invalid_field == "retrievers":
        kwargs["retrieval"] = RetrievalConfig(
            retrievers=[
                RetrieverConfig(type=RetrieverType.DENSE),
                RetrieverConfig(type=RetrieverType.SPARSE),
            ]
        )

    with pytest.raises(ValidationError):
        ExperimentConfig(**kwargs)


def test_bayesian_accepts_fixed_axes_with_chunking_ranges() -> None:
    config = ExperimentConfig(
        experiment_name="valid-bayes",
        data_paths=["./input_data/pdfs/sample.pdf"],
        queries_file="./configs/questions.example.json",
        embedding=EmbeddingConfig(provider="local", models=["all-MiniLM-L6-v2"]),
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[128, 256], overlaps=[0, 50]),
        ),
        retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        execution=ExecutionConfig(
            search_strategy="bayesian",
            bayesian=ExecutionConfig.BayesianConfig(n_trials=12),
        ),
    )

    assert len(config.chunking.params.chunk_sizes) == 2
    assert len(config.chunking.params.overlaps) == 2
