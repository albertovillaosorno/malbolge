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
#   - Exact two-pass baseline-versus-verified-result-reuse comparison.
# - Must-Not:
#   - Infer equivalence across candidate identities, retain timing, or persist
#     cache entries outside one comparison run.
# - Allows:
#   - Inputs: frozen classic candidate indices and one trusted verifier
#     callback.
#   - Outputs: complete request-quality maps and exact verifier/reuse counts.
#   - Side effects: invokes only the caller-supplied verifier callback.
# - Split-When:
#   - Persistent catalogue reuse or another workload gains separate policy.
# - Merge-When:
#   - A shared verified-result reuse runner owns this exact finite comparison.
# - Summary:
#   - Reuse a verified result only for the identical frozen candidate index.
# - Description:
#   - Two full corpus passes preserve every request result exactly.
# - Usage:
#   - Run after classic-two-pass-verified-block-reuse-v1 preregistration.
# - Defaults:
#   - Map drift, malformed quality, or absent verifier-work reduction fails.
#

"""Exact repeated-batch verified-result reuse for the classic pilot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Final

from algorithms.superoptimization import challenge

RUNNER_ID: Final = "classic-two-pass-verified-block-reuse-comparison-v1"
BASELINE_ID: Final = "per-request-independent-verification-v1"
TECHNIQUE_ID: Final = "exact-candidate-verified-result-reuse-v1"
SEMANTIC_EQUIVALENCE_ID: Final = "exact-request-index-quality-map-v1"
WORKLOAD_ID: Final = "classic-two-pass-verified-block-reuse-v1"
WORKLOAD_SHA256: Final = (
    "d86f190a512b64724b9546c72f2ee56973292e6ef5707378f8c9a9ba2050bbc7"
)
_PASSES: Final = 2
_NULL_QUALITY: Final = "null"
_MAX_U64: Final = (1 << 64) - 1

type CandidateVerifier = Callable[[int], int | None]
type QualityMap = tuple[int | None, ...]


class VerifiedBlockReuseComparisonError(ValueError):
    """Exact verified-result reuse violated the frozen comparison contract."""


@dataclass(frozen=True, slots=True)
class VerifiedBlockReuseStrategyRun:
    """Complete request-map and exact work counts for one comparison arm."""

    strategy_id: str
    request_count: int
    unique_candidate_count: int
    independent_verifier_calls: int
    reused_request_count: int
    accepted_request_count: int
    best_verified_quality: int | None
    quality_map_sha256: str
    quality_map: QualityMap


@dataclass(frozen=True, slots=True)
class VerifiedBlockReuseComparison:
    """Exact baseline and reuse results over the repeated frozen corpus."""

    runner_id: str
    semantic_equivalence_id: str
    workload_id: str
    workload_sha256: str
    base_workload_sha256: str
    baseline: VerifiedBlockReuseStrategyRun
    reused: VerifiedBlockReuseStrategyRun


def _quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted verified-block-reuse quality is malformed"
        raise VerifiedBlockReuseComparisonError(message)
    return value


def _requests() -> tuple[int, ...]:
    corpus = tuple(range(challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT))
    return corpus * _PASSES


def _workload_sha256() -> str:
    document = {
        "base_candidate_count": challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT,
        "base_workload_sha256": challenge.workload_sha256(),
        "passes": _PASSES,
        "request_encoding": "two-complete-lexicographic-passes-v1",
    }
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _map_digest(qualities: QualityMap) -> str:
    payload = "".join(
        f"{request}:{_NULL_QUALITY if quality is None else quality}\n"
        for request, quality in enumerate(qualities)
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _summary(
    strategy_id: str,
    qualities: QualityMap,
    *,
    verifier_calls: int,
    reused_requests: int,
) -> VerifiedBlockReuseStrategyRun:
    accepted = tuple(quality for quality in qualities if quality is not None)
    return VerifiedBlockReuseStrategyRun(
        strategy_id=strategy_id,
        request_count=len(qualities),
        unique_candidate_count=challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT,
        independent_verifier_calls=verifier_calls,
        reused_request_count=reused_requests,
        accepted_request_count=len(accepted),
        best_verified_quality=min(accepted, default=None),
        quality_map_sha256=_map_digest(qualities),
        quality_map=qualities,
    )


def _require_workload_identity() -> None:
    if _workload_sha256() != WORKLOAD_SHA256:
        message = "verified-block-reuse workload identity drifted"
        raise VerifiedBlockReuseComparisonError(message)


def run_baseline_strategy(
    verifier: CandidateVerifier,
) -> VerifiedBlockReuseStrategyRun:
    """Independently verify every request in both complete corpus passes.

    Returns:
        Complete request map with one verifier call per request.

    """
    _require_workload_identity()
    requests = _requests()
    qualities = tuple(_quality(verifier(candidate)) for candidate in requests)
    return _summary(
        BASELINE_ID,
        qualities,
        verifier_calls=len(requests),
        reused_requests=0,
    )


def run_reuse_strategy(
    verifier: CandidateVerifier,
) -> VerifiedBlockReuseStrategyRun:
    """Verify each candidate once and reuse only identical later requests.

    Returns:
        Complete request map with exact unique-candidate verifier accounting.

    """
    _require_workload_identity()
    cache: dict[int, int | None] = {}
    qualities: list[int | None] = []
    verifier_calls = 0
    reused_requests = 0
    for candidate in _requests():
        if candidate in cache:
            quality = cache[candidate]
            reused_requests += 1
        else:
            quality = _quality(verifier(candidate))
            cache[candidate] = quality
            verifier_calls += 1
        qualities.append(quality)
    return _summary(
        TECHNIQUE_ID,
        tuple(qualities),
        verifier_calls=verifier_calls,
        reused_requests=reused_requests,
    )


def run_comparison(
    verifier: CandidateVerifier,
) -> VerifiedBlockReuseComparison:
    """Compare per-request verification with exact candidate-result reuse.

    Returns:
        Exact baseline and reuse summaries after complete map equality.

    Raises:
        VerifiedBlockReuseComparisonError: If map equality or work reduction
            fails.

    """
    baseline = run_baseline_strategy(verifier)
    reused = run_reuse_strategy(verifier)
    if baseline.quality_map != reused.quality_map:
        message = (
            "verified-block-reuse request-quality map differs from baseline"
        )
        raise VerifiedBlockReuseComparisonError(message)
    if (
        reused.independent_verifier_calls
        >= baseline.independent_verifier_calls
    ):
        message = (
            "verified-block-reuse did not reduce independent verifier calls"
        )
        raise VerifiedBlockReuseComparisonError(message)
    return VerifiedBlockReuseComparison(
        runner_id=RUNNER_ID,
        semantic_equivalence_id=SEMANTIC_EQUIVALENCE_ID,
        workload_id=WORKLOAD_ID,
        workload_sha256=WORKLOAD_SHA256,
        base_workload_sha256=challenge.workload_sha256(),
        baseline=baseline,
        reused=reused,
    )
