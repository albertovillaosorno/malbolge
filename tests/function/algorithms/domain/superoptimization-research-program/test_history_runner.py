# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Correctness characterization for the frozen history comparison runner.
# - Must-Not:
#   - Interpret timing, persist a research result, or replace semantic
#     authority.
# - Allows:
#   - Inputs: exact frozen challenge and canonicalization runner.
#   - Outputs: state-count, verifier-work, replay, and semantic-equality
#     evidence.
#   - Side effects: dynamic import and in-memory deterministic comparison only.
# - Split-When:
#   - Measured evidence or another challenge gains independent lifecycle.
# - Merge-When:
#   - Shared comparison tests own this exact correctness characterization.
# - Summary:
#   - Prove state reduction without changing any challenge semantic output.
# - Description:
#   - Locks exact raw/canonical state counts for the preregistered finite
#     corpus.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - These counts are challenge characterization, not performance evidence.
#

"""Correctness evidence for the exact history canonicalization runner."""

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_MODULE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/history_runner.py"
)
_CANDIDATE_COUNT = 10_000
_BASELINE_STATES = 10_000
_CANONICAL_STATES = 6_496
_STATE_REDUCTION = _BASELINE_STATES - _CANONICAL_STATES
_BASELINE_ID = "raw-visit-count-state-v1"
_CANONICAL_ID = "exact-history-residue-state-v1"
_COMPARISON_ID = "classic-history-residue-comparison-v1"
_CHALLENGE_ID = "classic-history-residue-search-v1"
_WORKLOAD_SHA256 = (
    "f300a5adf717027eb11c850b4a8b292bf0bac7fe0cde6bdb9be9d2f7f504d103"
)
_SEMANTIC_SHA256 = (
    "fd3644058b415d3acc091d0b837111948ff640132f7c8093fca562d553bdb527"
)


class _Summary(Protocol):
    strategy_id: str
    unique_search_states: int
    generated_successors: int
    independent_verifier_calls: int
    peak_frontier_states: int
    semantic_sha256: str


class _Comparison(Protocol):
    comparison_id: str
    challenge_id: str
    candidate_count: int
    workload_sha256: str
    baseline: _Summary
    canonicalized: _Summary


class _RunnerModule(Protocol):
    InvalidHistoryComparisonError: type[ValueError]

    def compare_history_states(self) -> _Comparison: ...

    def run_history_strategy(self, strategy_id: str) -> _Summary: ...


def _load_runner() -> _RunnerModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_history_runner_test",
        _MODULE,
    )
    if spec is None or spec.loader is None:
        message = "history comparison runner cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_RunnerModule", cast("object", module))


_RUNNER = _load_runner()


def test_history_runner_reduces_states_without_semantic_drift() -> None:
    """Canonical residue keys reduce state work with identical output."""
    result = _RUNNER.compare_history_states()
    assert result.comparison_id == _COMPARISON_ID
    assert result.challenge_id == _CHALLENGE_ID
    assert result.candidate_count == _CANDIDATE_COUNT
    assert result.workload_sha256 == _WORKLOAD_SHA256
    assert result.baseline.strategy_id == _BASELINE_ID
    assert result.canonicalized.strategy_id == _CANONICAL_ID
    assert result.baseline.unique_search_states == _BASELINE_STATES
    assert result.canonicalized.unique_search_states == _CANONICAL_STATES
    assert (
        result.baseline.unique_search_states
        - result.canonicalized.unique_search_states
        == _STATE_REDUCTION
    )
    assert result.baseline.semantic_sha256 == _SEMANTIC_SHA256
    assert result.canonicalized.semantic_sha256 == _SEMANTIC_SHA256


def test_history_runner_counts_unique_states_as_verifier_work() -> None:
    """Both strategies generate the corpus but verify each unique key once."""
    result = _RUNNER.compare_history_states()
    for summary, expected_states in (
        (result.baseline, _BASELINE_STATES),
        (result.canonicalized, _CANONICAL_STATES),
    ):
        assert summary.generated_successors == _CANDIDATE_COUNT
        assert summary.unique_search_states == expected_states
        assert summary.independent_verifier_calls == expected_states
        assert summary.peak_frontier_states == expected_states


def test_history_runner_replays_identically() -> None:
    """Correctness characterization is deterministic and environment-free."""
    first = _RUNNER.compare_history_states()
    second = _RUNNER.compare_history_states()
    assert first == second


def test_history_runner_exposes_each_registered_strategy_independently(
) -> None:
    """Measurement callers can execute either frozen arm without private API."""
    baseline = _RUNNER.run_history_strategy(_BASELINE_ID)
    canonicalized = _RUNNER.run_history_strategy(_CANONICAL_ID)
    assert baseline.unique_search_states == _BASELINE_STATES
    assert canonicalized.unique_search_states == _CANONICAL_STATES
    assert baseline.semantic_sha256 == _SEMANTIC_SHA256
    assert canonicalized.semantic_sha256 == _SEMANTIC_SHA256


def test_history_runner_rejects_unregistered_strategy_identity() -> None:
    """A measurement cannot silently substitute a third comparison arm."""
    with pytest.raises(
        _RUNNER.InvalidHistoryComparisonError,
        match="history comparison strategy is not registered",
    ):
        _ = _RUNNER.run_history_strategy("different-history-strategy-v1")
