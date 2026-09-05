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
#   - Exhaustive correctness evidence for exact verified-result reuse.
# - Must-Not:
#   - Claim timing or allow reuse across different candidate identities.
# - Allows:
#   - Inputs: frozen classic verifier and instrumented verifier callbacks.
#   - Outputs: exact call counts, map parity, reuse, and failure assertions.
#   - Side effects: in-memory verifier-call tracing only.
# - Split-When:
#   - Timed protocol or persistent catalogue reuse gains separate evidence.
# - Merge-When:
#   - Shared reuse tests own this exact two-pass comparison identity.
# - Summary:
#   - Prove the second identical pass reuses all 8,836 verified results.
# - Description:
#   - Every unique candidate verifies once in the reuse arm.
# - Usage:
#   - Collected before opening retained reuse measurement results.
# - Defaults:
#   - Stateful verifier drift must fail complete request-map equality.
#

"""Exhaustive runner evidence for exact repeated-batch verified-result reuse."""

from typing import cast

from algorithms.superoptimization import challenge
from algorithms.superoptimization import verified_block_reuse_runner as runner
import pytest

_REQUESTS = 17_672
_UNIQUE = 8_836
_REUSED = 8_836
_ACCEPTED = 20
_BEST = 1
_RUNNER_ID = "classic-two-pass-verified-block-reuse-comparison-v1"
_WORKLOAD_SHA256 = (
    "d86f190a512b64724b9546c72f2ee56973292e6ef5707378f8c9a9ba2050bbc7"
)
_MAP_DRIFT = "request-quality map differs from baseline"
_MALFORMED = "quality is malformed"


def test_verified_block_reuse_halves_calls_without_map_drift() -> None:
    """Two identical passes need one independent verification per candidate."""
    result = runner.run_comparison(challenge.verified_quality)
    assert result.runner_id == _RUNNER_ID
    assert result.workload_sha256 == _WORKLOAD_SHA256
    assert result.baseline.request_count == _REQUESTS
    assert result.reused.request_count == _REQUESTS
    assert result.baseline.independent_verifier_calls == _REQUESTS
    assert result.reused.independent_verifier_calls == _UNIQUE
    assert result.reused.reused_request_count == _REUSED
    assert result.reused.unique_candidate_count == _UNIQUE
    assert result.baseline.accepted_request_count == _ACCEPTED
    assert result.reused.accepted_request_count == _ACCEPTED
    assert result.reused.best_verified_quality == _BEST
    assert result.baseline.quality_map == result.reused.quality_map
    assert (
        result.baseline.quality_map_sha256
        == result.reused.quality_map_sha256
    )


def test_reuse_strategy_verifies_every_unique_candidate_exactly_once() -> None:
    """Cache identity is the exact frozen candidate index only."""
    calls: list[int] = []

    def traced(candidate: int) -> int | None:
        calls.append(candidate)
        return challenge.verified_quality(candidate)

    result = runner.run_reuse_strategy(traced)
    assert calls == list(range(_UNIQUE))
    assert result.independent_verifier_calls == _UNIQUE
    assert result.reused_request_count == _REUSED


def test_reuse_comparison_rejects_stateful_second_pass_drift() -> None:
    """A changing verifier cannot be hidden by a cached first-pass result."""
    calls: dict[int, int] = {}

    def drifting(candidate: int) -> int | None:
        count = calls.get(candidate, 0)
        calls[candidate] = count + 1
        if candidate == 0 and count > 0:
            return 1
        return challenge.verified_quality(candidate)

    with pytest.raises(
        runner.VerifiedBlockReuseComparisonError,
        match=_MAP_DRIFT,
    ):
        _ = runner.run_comparison(drifting)


@pytest.mark.parametrize("malformed", [-1, True, "1"])
def test_reuse_runner_rejects_malformed_quality(malformed: object) -> None:
    """Cache storage cannot admit malformed verifier quality values."""
    def verifier(candidate: int) -> int | None:
        _ = candidate
        return cast("int | None", malformed)

    with pytest.raises(
        runner.VerifiedBlockReuseComparisonError,
        match=_MALFORMED,
    ):
        _ = runner.run_reuse_strategy(verifier)
