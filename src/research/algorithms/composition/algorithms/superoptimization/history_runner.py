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
#   - Deterministic raw-versus-residue comparison for the frozen history corpus.
# - Must-Not:
#   - Define Malbolge semantics, write measurements, or infer runtime speedup.
# - Allows:
#   - Inputs: the frozen challenge and exact history canonicalizer.
#   - Outputs: in-memory state counts, verifier work, and semantic digests.
#   - Side effects: invokes only repository-owned pure semantic verification.
# - Split-When:
#   - Timed measurement, another challenge, or persistent evidence gains policy.
# - Merge-When:
#   - A shared canonicalization experiment harness owns this exact comparison.
# - Summary:
#   - Exact finite deduplication comparison below independent semantics.
# - Description:
#   - Reuses a verified value only when an exact canonical state key repeats.
# - Usage:
#   - Execute for correctness characterization before any measured experiment.
# - Defaults:
#   - Any raw/canonical semantic digest mismatch fails closed.
#

"""Deterministic history-state canonicalization comparison substrate."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from src.research.algorithms.composition.algorithms.superoptimization import (
    history,
)
from src.research.algorithms.composition.algorithms.superoptimization import (
    history_challenge as challenge,
)

HISTORY_COMPARISON_ID: Final = "classic-history-residue-comparison-v1"
RAW_HISTORY_STATE_ID: Final = "raw-visit-count-state-v1"
CANONICAL_HISTORY_STATE_ID: Final = history.HISTORY_CANONICALIZATION_ID

_ADMITTED = history.HistoryApplicability(
    same_address_identity=True,
    intervening_write=False,
)

type HistoryStateKey = tuple[str, int, int]


class InvalidHistoryComparisonError(ValueError):
    """The frozen comparison encountered semantic or identity drift."""


@dataclass(frozen=True, slots=True)
class HistoryStrategySummary:
    """Exact in-memory evidence for one state identity strategy."""

    strategy_id: str
    unique_search_states: int
    generated_successors: int
    independent_verifier_calls: int
    peak_frontier_states: int
    semantic_sha256: str


@dataclass(frozen=True, slots=True)
class HistoryComparisonResult:
    """Raw and canonicalized results for the exact frozen history corpus."""

    comparison_id: str
    challenge_id: str
    candidate_count: int
    workload_sha256: str
    baseline: HistoryStrategySummary
    canonicalized: HistoryStrategySummary


def _raw_state_key(
    observation: challenge.HistoryObservation,
) -> HistoryStateKey:
    return (observation.kind, observation.subject, observation.visits)


def _canonical_state_key(
    observation: challenge.HistoryObservation,
) -> HistoryStateKey:
    if observation.kind == challenge.KIND_ENCRYPTION:
        visits = history.canonical_encryption_visits(
            observation.subject,
            observation.visits,
            applicability=_ADMITTED,
            successor=challenge.encryption_successor,
        )
    elif observation.kind == challenge.KIND_ROTATE:
        visits = history.canonical_rotate_visits(
            observation.visits,
            _ADMITTED,
        )
    else:
        message = "history challenge produced an unknown operation kind"
        raise InvalidHistoryComparisonError(message)
    return (observation.kind, observation.subject, visits)


def _run_strategy(
    strategy_id: str,
    key_builder: object,
) -> HistoryStrategySummary:
    if key_builder is _raw_state_key:
        build_key = _raw_state_key
    elif key_builder is _canonical_state_key:
        build_key = _canonical_state_key
    else:
        message = "history comparison key builder is not registered"
        raise InvalidHistoryComparisonError(message)
    verified_states: dict[HistoryStateKey, int] = {}
    semantic_digest = sha256()
    for candidate_index in range(challenge.HISTORY_CANDIDATE_COUNT):
        observation = challenge.candidate_observation(candidate_index)
        state_key = build_key(observation)
        value = verified_states.get(state_key)
        if value is None:
            value = challenge.semantic_value(observation)
            verified_states[state_key] = value
        semantic_digest.update(f"{candidate_index}:{value}\n".encode("ascii"))
    unique_states = len(verified_states)
    return HistoryStrategySummary(
        strategy_id=strategy_id,
        unique_search_states=unique_states,
        generated_successors=challenge.HISTORY_CANDIDATE_COUNT,
        independent_verifier_calls=unique_states,
        peak_frontier_states=unique_states,
        semantic_sha256=semantic_digest.hexdigest(),
    )


def compare_history_states() -> HistoryComparisonResult:
    """Compare raw visit-count state with exact residue canonicalization.

    Returns:
        In-memory correctness characterization for the frozen 10,000-item
        challenge. This function records no wall-clock evidence.

    Raises:
        InvalidHistoryComparisonError: If canonical reuse changes any exact
            per-candidate semantic value.

    """
    baseline = _run_strategy(RAW_HISTORY_STATE_ID, _raw_state_key)
    canonicalized = _run_strategy(
        CANONICAL_HISTORY_STATE_ID,
        _canonical_state_key,
    )
    if baseline.semantic_sha256 != canonicalized.semantic_sha256:
        message = "history canonicalization changed exact challenge semantics"
        raise InvalidHistoryComparisonError(message)
    return HistoryComparisonResult(
        comparison_id=HISTORY_COMPARISON_ID,
        challenge_id=challenge.HISTORY_CHALLENGE_ID,
        candidate_count=challenge.HISTORY_CANDIDATE_COUNT,
        workload_sha256=challenge.workload_sha256(),
        baseline=baseline,
        canonicalized=canonicalized,
    )
