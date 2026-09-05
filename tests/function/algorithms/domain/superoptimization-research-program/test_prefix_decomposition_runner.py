# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Exhaustive correctness evidence for the prefix-decomposition runner.
# - Must-Not:
#   - Claim timing, broaden suffix independence, or skip final map equality.
# - Allows:
#   - Inputs: frozen challenge, proved `Q` basis, and comparison runner.
#   - Outputs: exact map parity, verifier counts, discharge, and rejection
#     tests.
#   - Side effects: in-memory verifier-call tracing only.
# - Split-When:
#   - Timed protocol or another proved prefix class gains separate evidence.
# - Merge-When:
#   - Shared decomposition tests own this exact runner identity and corpus.
# - Summary:
#   - Prove `Q` reuse saves only its 94 calls and verifies every other prefix.
# - Description:
#   - Instruments the trusted verifier to detect any accidental `Q` invocation.
# - Usage:
#   - Collected before opening prefix-decomposition measurement results.
# - Defaults:
#   - A forged `Q` quality must fail complete final-map equality.
#

"""Exhaustive runner evidence for exact classic prefix decomposition."""

from typing import cast

from algorithms.superoptimization import challenge
from algorithms.superoptimization import prefix_decomposition_runner as runner
import pytest

_RUNNER_ID = "classic-two-word-prefix-decomposition-comparison-v1"
_EQUIVALENCE_ID = "exact-candidate-index-quality-map-v1"
_CHALLENGE_ID = "classic-verified-block-search-v1"
_WORKLOAD_SHA256 = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)
_PROOF_ID = "q-entry-halt-suffix-independence-v1"
_CANDIDATE_COUNT = 8_836
_GRAPHICAL_START = 33
_GRAPHICAL_VALUES = 94
_Q_PREFIX = ord("Q")
_Q_ROW_START = (_Q_PREFIX - _GRAPHICAL_START) * _GRAPHICAL_VALUES
_Q_ROW_END = _Q_ROW_START + _GRAPHICAL_VALUES
_DISCHARGED = _GRAPHICAL_VALUES
_TECHNIQUE_CALLS = _CANDIDATE_COUNT - _DISCHARGED
_ACCEPTED_COUNT = 10
_BEST_QUALITY = 1
_SHA256_LENGTH = 64
_MAP_DRIFT = "candidate-quality map differs from baseline"
_MALFORMED = "verifier quality is malformed"


def _q_candidate(candidate_index: int) -> bool:
    return _Q_ROW_START <= candidate_index < _Q_ROW_END


def test_prefix_decomposition_preserves_complete_quality_map_and_reduces_calls(
) -> None:
    """The sole proved prefix removes exactly 94 full-verifier calls."""
    result = runner.run_comparison(challenge.verified_quality)

    assert result.runner_id == _RUNNER_ID
    assert result.semantic_equivalence_id == _EQUIVALENCE_ID
    assert result.challenge_id == _CHALLENGE_ID
    assert result.workload_sha256 == _WORKLOAD_SHA256
    assert result.proof_ids == (_PROOF_ID,)
    assert result.baseline.candidate_count == _CANDIDATE_COUNT
    assert result.decomposed.candidate_count == _CANDIDATE_COUNT
    assert result.baseline.independent_verifier_calls == _CANDIDATE_COUNT
    assert result.decomposed.independent_verifier_calls == _TECHNIQUE_CALLS
    assert result.baseline.structurally_discharged_candidates == 0
    assert result.decomposed.structurally_discharged_candidates == _DISCHARGED
    assert result.baseline.accepted_candidate_count == _ACCEPTED_COUNT
    assert result.decomposed.accepted_candidate_count == _ACCEPTED_COUNT
    assert result.baseline.best_verified_quality == _BEST_QUALITY
    assert result.decomposed.best_verified_quality == _BEST_QUALITY
    assert result.baseline.quality_map == result.decomposed.quality_map
    assert (
        result.baseline.quality_map_sha256
        == result.decomposed.quality_map_sha256
    )
    assert len(result.baseline.quality_map_sha256) == _SHA256_LENGTH


def test_decomposed_strategy_never_calls_verifier_for_proved_q_row() -> None:
    """Every non-Q candidate verifies once; every Q candidate discharges."""
    calls: list[int] = []

    def tracing_verifier(candidate_index: int) -> int | None:
        assert not _q_candidate(candidate_index)
        calls.append(candidate_index)
        return challenge.verified_quality(candidate_index)

    result = runner.run_decomposed_strategy(tracing_verifier)

    assert len(calls) == _TECHNIQUE_CALLS
    assert len(set(calls)) == _TECHNIQUE_CALLS
    assert all(not _q_candidate(candidate_index) for candidate_index in calls)
    assert result.independent_verifier_calls == _TECHNIQUE_CALLS
    assert result.structurally_discharged_candidates == _DISCHARGED
    expected = tuple(
        challenge.verified_quality(candidate_index)
        for candidate_index in range(_CANDIDATE_COUNT)
    )
    assert result.quality_map == expected


def test_prefix_comparison_rejects_forged_q_quality() -> None:
    """Structural proof cannot silently disagree with the final baseline map."""
    def forged_verifier(candidate_index: int) -> int | None:
        if candidate_index == _Q_ROW_START:
            return 2
        return challenge.verified_quality(candidate_index)

    with pytest.raises(
        runner.PrefixDecompositionComparisonError,
        match=_MAP_DRIFT,
    ):
        _ = runner.run_comparison(forged_verifier)


@pytest.mark.parametrize("malformed", [-1, True, "1"])
def test_prefix_runner_rejects_malformed_verifier_quality(
    malformed: object,
) -> None:
    """A callback cannot smuggle non-quality values into either strategy."""
    def malformed_verifier(candidate_index: int) -> int | None:
        _ = candidate_index
        return cast("int | None", malformed)

    with pytest.raises(
        runner.PrefixDecompositionComparisonError,
        match=_MALFORMED,
    ):
        _ = runner.run_baseline_strategy(malformed_verifier)
