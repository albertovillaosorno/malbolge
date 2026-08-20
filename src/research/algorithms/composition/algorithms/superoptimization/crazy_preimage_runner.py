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
#   - Structural comparison of full-domain and production exact-preimage work.
# - Must-Not:
#   - Own crazy semantics, collect timing, or admit measurement conclusions.
# - Allows:
#   - Inputs: frozen challenge and one injected independent classic crazy
#     oracle.
#   - Outputs: exact per-problem/aggregate evaluation counts and semantic
#     digests.
#   - Side effects: CPU reference search evaluation only.
# - Split-When:
#   - Timed measurement or another profile width needs a separate protocol.
# - Merge-When:
#   - Another runner owns this exact challenge/technique/baseline comparison.
# - Summary:
#   - Exact structural crazy-preimage pruning comparison runner.
# - Description:
#   - Verifies production projected preimages against independent full-domain
#     sets.
# - Usage:
#   - Consumed after the finite cardinality-spanning challenge is registered.
# - Defaults:
#   - Seed zero, complete classic data domain, and no wall-clock interpretation.
#

"""Structural runner for exact classic crazy preimage pruning."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Final
from typing import TYPE_CHECKING

from accelerator.work_ports import SearchRequest
from algorithms.superoptimization.crazy_preimage_challenge import challenge
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import cpu_crazy_target_search_adapter
from optimizer.crazy_target import crazy_target_selection_preparer_id

if TYPE_CHECKING:
    from algorithms.superoptimization.crazy_preimage_challenge import (
        CrazyPreimageChallengeProblem,
    )

RUNNER_ID: Final = "classic-crazy-preimage-structural-comparison-v1"
BASELINE_ID: Final = "classic-crazy-full-domain-data-enumeration-v1"
TECHNIQUE_ID: Final = "classic-crazy-digitwise-exact-preimage-v1"
_FULL_DOMAIN_WORDS: Final = 59_049
_SEED: Final = 0
_LITTLE_ENDIAN: Final = "little"
_WORD_BYTES: Final = 4
_FULL_DOMAIN: Final = tuple(range(_FULL_DOMAIN_WORDS))

type CrazySemanticOracle = Callable[[int, int], int]


class CrazyPreimageComparisonError(ValueError):
    """Structural comparison or independent semantic evidence drifted."""


@dataclass(frozen=True, slots=True)
class CrazyPreimageStrategyRun:
    """One separately callable structural strategy result."""

    strategy_id: str
    evaluations: int
    preimage_count: int
    semantic_sha256: str


@dataclass(frozen=True, slots=True)
class CrazyPreimageProblemResult:
    """Exact structural evidence for one fixed accumulator/target problem."""

    accumulator: int
    target: int
    expected_preimages: int
    baseline_evaluations: int
    exact_evaluations: int
    preimage_sha256: str


@dataclass(frozen=True, slots=True)
class CrazyPreimageComparison:
    """Aggregate structural comparison over the frozen challenge."""

    runner_id: str
    baseline_id: str
    technique_id: str
    challenge_id: str
    workload_sha256: str
    baseline_evaluations: int
    exact_evaluations: int
    results: tuple[CrazyPreimageProblemResult, ...]


def _baseline_preimages(
    problem: CrazyPreimageChallengeProblem,
    oracle: CrazySemanticOracle,
) -> tuple[int, ...]:
    return tuple(
        data
        for data in _FULL_DOMAIN
        if oracle(data, problem.accumulator) == problem.target
    )


def _preimage_digest(preimages: tuple[int, ...]) -> str:
    payload = b"".join(
        value.to_bytes(_WORD_BYTES, _LITTLE_ENDIAN) for value in preimages
    )
    return sha256(payload).hexdigest()


def _strategy_digest(preimage_sets: tuple[tuple[int, ...], ...]) -> str:
    digest = sha256()
    for preimages in preimage_sets:
        digest.update(len(preimages).to_bytes(_WORD_BYTES, _LITTLE_ENDIAN))
        for value in preimages:
            digest.update(value.to_bytes(_WORD_BYTES, _LITTLE_ENDIAN))
    return digest.hexdigest()


def _request(problem: CrazyPreimageChallengeProblem) -> SearchRequest:
    encoded = CrazyTargetProblem(
        accumulator=problem.accumulator,
        target=problem.target,
        candidates=_FULL_DOMAIN,
    ).encode()
    return SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=_FULL_DOMAIN_WORDS,
        problem=encoded,
        seed=_SEED,
    )


def _proposal_data(payload: bytes, accumulator: int) -> int:
    if len(payload) != 2 * _WORD_BYTES:
        message = "crazy preimage proposal payload has unexpected width"
        raise CrazyPreimageComparisonError(message)
    data = int.from_bytes(payload[:_WORD_BYTES], _LITTLE_ENDIAN)
    observed_accumulator = int.from_bytes(
        payload[_WORD_BYTES:], _LITTLE_ENDIAN
    )
    if observed_accumulator != accumulator:
        message = "crazy preimage proposal changed fixed accumulator"
        raise CrazyPreimageComparisonError(message)
    return data


def _validated_baseline_preimages(
    problem: CrazyPreimageChallengeProblem,
    oracle: CrazySemanticOracle,
) -> tuple[int, ...]:
    baseline = _baseline_preimages(problem, oracle)
    if len(baseline) != problem.expected_preimages:
        message = (
            "independent baseline differs from declared challenge cardinality"
        )
        raise CrazyPreimageComparisonError(message)
    return baseline


def _exact_preimages(
    problem: CrazyPreimageChallengeProblem,
    oracle: CrazySemanticOracle,
) -> tuple[tuple[int, ...], int]:
    adapter = cpu_crazy_target_search_adapter()
    prepared = adapter.prepare(_request(problem))
    evaluations = adapter.prepared_candidate_state_count(prepared)
    proposals = adapter.search_prepared(prepared).proposals
    exact = tuple(
        sorted(
            _proposal_data(proposal.payload, problem.accumulator)
            for proposal in proposals
        )
    )
    if len(exact) != len(set(exact)):
        message = "production exact preimage proposals contain duplicates"
        raise CrazyPreimageComparisonError(message)
    if len(exact) != problem.expected_preimages:
        message = "production exact preimage cardinality differs from challenge"
        raise CrazyPreimageComparisonError(message)
    if any(
        oracle(data, problem.accumulator) != problem.target for data in exact
    ):
        message = (
            "production exact preimage proposal failed independent semantics"
        )
        raise CrazyPreimageComparisonError(message)
    if evaluations != len(exact):
        message = "production exact preimage evaluation count drifted"
        raise CrazyPreimageComparisonError(message)
    return exact, evaluations


def run_baseline_strategy(
    oracle: CrazySemanticOracle,
) -> CrazyPreimageStrategyRun:
    """Run complete-domain independent enumeration for the frozen challenge.

    Returns:
        Baseline work count and canonical semantic preimage digest.

    """
    frozen = challenge()
    preimage_sets = tuple(
        _validated_baseline_preimages(problem, oracle)
        for problem in frozen.problems
    )
    return CrazyPreimageStrategyRun(
        strategy_id=BASELINE_ID,
        evaluations=len(frozen.problems) * _FULL_DOMAIN_WORDS,
        preimage_count=sum(len(preimages) for preimages in preimage_sets),
        semantic_sha256=_strategy_digest(preimage_sets),
    )


def run_exact_strategy(
    oracle: CrazySemanticOracle,
) -> CrazyPreimageStrategyRun:
    """Run production exact projection with independent semantic verification.

    Returns:
        Exact projected work count and canonical semantic preimage digest.

    Raises:
        CrazyPreimageComparisonError: If production or semantic evidence drifts.

    """
    if crazy_target_selection_preparer_id() != TECHNIQUE_ID:
        message = "production crazy preimage preparer identity drifted"
        raise CrazyPreimageComparisonError(message)
    frozen = challenge()
    resolved = tuple(
        _exact_preimages(problem, oracle) for problem in frozen.problems
    )
    preimage_sets = tuple(preimages for preimages, _evaluations in resolved)
    return CrazyPreimageStrategyRun(
        strategy_id=TECHNIQUE_ID,
        evaluations=sum(evaluations for _preimages, evaluations in resolved),
        preimage_count=sum(len(preimages) for preimages in preimage_sets),
        semantic_sha256=_strategy_digest(preimage_sets),
    )


def _compare_problem(
    problem: CrazyPreimageChallengeProblem,
    oracle: CrazySemanticOracle,
) -> CrazyPreimageProblemResult:
    baseline = _validated_baseline_preimages(problem, oracle)
    exact, exact_evaluations = _exact_preimages(problem, oracle)
    if exact != baseline:
        message = (
            "production exact preimage set differs from independent baseline"
        )
        raise CrazyPreimageComparisonError(message)
    return CrazyPreimageProblemResult(
        accumulator=problem.accumulator,
        target=problem.target,
        expected_preimages=problem.expected_preimages,
        baseline_evaluations=_FULL_DOMAIN_WORDS,
        exact_evaluations=exact_evaluations,
        preimage_sha256=_preimage_digest(baseline),
    )


def run_comparison(oracle: CrazySemanticOracle) -> CrazyPreimageComparison:
    """Compare full-domain and production exact-preimage structural work.

    Returns:
        Exact counts and semantic preimage digests over the frozen challenge.

    Raises:
        CrazyPreimageComparisonError: If challenge, production, or independent
        semantic evidence differs.

    """
    if crazy_target_selection_preparer_id() != TECHNIQUE_ID:
        message = "production crazy preimage preparer identity drifted"
        raise CrazyPreimageComparisonError(message)
    frozen = challenge()
    results = tuple(
        _compare_problem(problem, oracle) for problem in frozen.problems
    )
    return CrazyPreimageComparison(
        runner_id=RUNNER_ID,
        baseline_id=BASELINE_ID,
        technique_id=TECHNIQUE_ID,
        challenge_id=frozen.challenge_id,
        workload_sha256=frozen.workload_sha256,
        baseline_evaluations=sum(item.baseline_evaluations for item in results),
        exact_evaluations=sum(item.exact_evaluations for item in results),
        results=results,
    )
