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
#   - Exact baseline-versus-prefix-decomposition comparison for the frozen
#     two-word superoptimization challenge.
# - Must-Not:
#   - Generalize suffix independence, write measurement evidence, or replace
#     independent verifier authority.
# - Allows:
#   - Inputs: the frozen challenge and one caller-supplied trusted verifier.
#   - Outputs: complete quality-map parity plus exact verifier/discharge counts.
#   - Side effects: invokes only the caller-supplied verifier callback.
# - Split-When:
#   - Another proved prefix class or timed protocol gains independent policy.
# - Merge-When:
#   - A shared decomposition runner owns this exact finite comparison contract.
# - Summary:
#   - Reuse only the separately proved suffix-independent `Q` prefix class.
# - Description:
#   - Fully verifies every unproved prefix and compares the complete final map.
# - Usage:
#   - Run after the prefix-decomposition plan and `Q` structural proof exist.
# - Defaults:
#   - Any quality-map drift or malformed verifier result fails closed.
#

"""Exact first-step prefix-decomposition runner for the frozen classic pilot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from algorithms.superoptimization import challenge

from verifier import emitted_malbolge_classic as classic

RUNNER_ID: Final = "classic-two-word-prefix-decomposition-comparison-v1"
BASELINE_ID: Final = "full-candidate-independent-verification-v1"
TECHNIQUE_ID: Final = "exact-first-step-prefix-decomposition-v1"
SEMANTIC_EQUIVALENCE_ID: Final = "exact-candidate-index-quality-map-v1"
Q_PREFIX_PROOF_ID: Final = "q-entry-halt-suffix-independence-v1"

_GRAPHICAL_START: Final = 33
_GRAPHICAL_VALUES: Final = 94
_Q_PREFIX: Final = ord("Q")
_HALT: Final = ord("v")
_Q_QUALITY: Final = 1
_ALLOWED_LOAD_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_NULL_QUALITY: Final = "null"
_MAX_U64: Final = (1 << 64) - 1

type CandidateVerifier = Callable[[int], int | None]
type QualityMap = tuple[int | None, ...]


class PrefixDecompositionComparisonError(ValueError):
    """Prefix decomposition violated the frozen exact comparison contract."""


@dataclass(frozen=True, slots=True)
class PrefixDecompositionStrategyRun:
    """Complete quality-map and exact work counts for one comparison arm."""

    strategy_id: str
    candidate_count: int
    independent_verifier_calls: int
    full_candidate_verifications: int
    structurally_discharged_candidates: int
    accepted_candidate_count: int
    best_verified_quality: int | None
    quality_map_sha256: str
    quality_map: QualityMap


@dataclass(frozen=True, slots=True)
class PrefixDecompositionComparison:
    """Exact baseline and proved-prefix results over the frozen corpus."""

    runner_id: str
    semantic_equivalence_id: str
    challenge_id: str
    workload_sha256: str
    proof_ids: tuple[str, ...]
    baseline: PrefixDecompositionStrategyRun
    decomposed: PrefixDecompositionStrategyRun


def _quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted prefix-decomposition verifier quality is malformed"
        raise PrefixDecompositionComparisonError(message)
    return value


def _quality_map_digest(qualities: QualityMap) -> str:
    payload = "".join(
        f"{candidate}:{_NULL_QUALITY if quality is None else quality}\n"
        for candidate, quality in enumerate(qualities)
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _strategy_run(
    strategy_id: str,
    qualities: QualityMap,
    *,
    verifier_calls: int,
    discharged: int,
) -> PrefixDecompositionStrategyRun:
    accepted = tuple(quality for quality in qualities if quality is not None)
    return PrefixDecompositionStrategyRun(
        strategy_id=strategy_id,
        candidate_count=len(qualities),
        independent_verifier_calls=verifier_calls,
        full_candidate_verifications=verifier_calls,
        structurally_discharged_candidates=discharged,
        accepted_candidate_count=len(accepted),
        best_verified_quality=min(accepted, default=None),
        quality_map_sha256=_quality_map_digest(qualities),
        quality_map=qualities,
    )


def _q_prefix_quality(candidate_index: int) -> int | None:
    source = challenge.candidate_source(candidate_index)
    if source[0] != _Q_PREFIX:
        message = "structural discharge attempted outside the proved Q prefix"
        raise PrefixDecompositionComparisonError(message)
    first = classic.decode(source[0], 0)
    second = classic.decode(source[1], 1)
    if first != _HALT:
        message = "proved Q prefix no longer decodes to entry halt"
        raise PrefixDecompositionComparisonError(message)
    admitted = (
        first in _ALLOWED_LOAD_INSTRUCTIONS
        and second in _ALLOWED_LOAD_INSTRUCTIONS
    )
    return _Q_QUALITY if admitted else None


def _has_proved_q_prefix(candidate_index: int) -> bool:
    return challenge.candidate_source(candidate_index)[0] == _Q_PREFIX


def run_baseline_strategy(
    verifier: CandidateVerifier,
) -> PrefixDecompositionStrategyRun:
    """Fully verify every candidate in the frozen two-word corpus.

    Returns:
        Complete baseline quality map and exact verifier-call accounting.

    """
    qualities = tuple(
        _quality(verifier(candidate_index))
        for candidate_index in range(
            challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
        )
    )
    return _strategy_run(
        BASELINE_ID,
        qualities,
        verifier_calls=len(qualities),
        discharged=0,
    )


def run_decomposed_strategy(
    verifier: CandidateVerifier,
) -> PrefixDecompositionStrategyRun:
    """Structurally discharge proved `Q` candidates and verify all others.

    Returns:
        Complete quality map with exact structural and verifier work counts.

    """
    qualities: list[int | None] = []
    verifier_calls = 0
    discharged = 0
    for candidate_index in range(
        challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
    ):
        if _has_proved_q_prefix(candidate_index):
            quality = _q_prefix_quality(candidate_index)
            discharged += 1
        else:
            quality = _quality(verifier(candidate_index))
            verifier_calls += 1
        qualities.append(quality)
    return _strategy_run(
        TECHNIQUE_ID,
        tuple(qualities),
        verifier_calls=verifier_calls,
        discharged=discharged,
    )


def run_comparison(
    verifier: CandidateVerifier,
) -> PrefixDecompositionComparison:
    """Compare complete verification with proved first-prefix decomposition.

    Returns:
        Exact full-corpus quality-map equality and per-arm work accounting.

    Raises:
        PrefixDecompositionComparisonError: If structural reuse changes any
            candidate quality or fails to reduce independent verifier calls.

    """
    baseline = run_baseline_strategy(verifier)
    decomposed = run_decomposed_strategy(verifier)
    if baseline.quality_map != decomposed.quality_map:
        message = (
            "prefix decomposition candidate-quality map differs from baseline"
        )
        raise PrefixDecompositionComparisonError(message)
    if (
        decomposed.independent_verifier_calls
        >= baseline.independent_verifier_calls
    ):
        message = (
            "prefix decomposition did not reduce independent verifier calls"
        )
        raise PrefixDecompositionComparisonError(message)
    return PrefixDecompositionComparison(
        runner_id=RUNNER_ID,
        semantic_equivalence_id=SEMANTIC_EQUIVALENCE_ID,
        challenge_id=challenge.CLASSIC_BLOCK_SEARCH_CHALLENGE_ID,
        workload_sha256=challenge.workload_sha256(),
        proof_ids=(Q_PREFIX_PROOF_ID,),
        baseline=baseline,
        decomposed=decomposed,
    )
