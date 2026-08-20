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
#   - Exact full-domain multiposition crazy-target benchmark workload.
# - Must-Not:
#   - Alter strategy semantics or use backend output as acceptance authority.
# - Allows:
#   - Inputs: the complete classic word domain and fixed target/accumulator.
#   - Outputs: canonical request, expected proposals, and trusted validation.
#   - Side effects: immutable workload construction only.
# - Split-When:
#   - Split when another multiposition workload needs independent evidence.
# - Merge-When:
#   - Merge when another benchmark owns this exact canonical workload.
# - Summary:
#   - Shared crazy-target workload for CPU/CUDA performance measurements.
# - Description:
#   - Generates all 1,024 exact preimages of the all-one-trit target.
# - Usage:
#   - Imported by crazy-target benchmark programs and validation tests.
# - Defaults:
#   - Full membership and independent CPU admission remain authoritative.
#

"""Shared exact full-domain multiposition crazy-target benchmark workload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING

from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import TRIT_COUNT
from accelerator.primitive_candidates import encode_crazy_candidate
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import CrazyTargetVerifier

if TYPE_CHECKING:
    from accelerator.work_ports import SearchResult

ACCUMULATOR: Final = 0
TARGET: Final = MAX_WORD // 2
SEED: Final = 0
CORPUS_SIZE: Final = MAX_WORD + 1
PREIMAGE_COUNT: Final = 1 << TRIT_COUNT
WORKLOAD_ID: Final = "classic-crazy-target-full-domain-multiposition-v1"
CPU_BACKEND: Final = "cpu-reference"
CUDA_BACKEND: Final = "cuda"


@dataclass(frozen=True, slots=True)
class CrazySearchBenchmarkWorkload:
    """Canonical request and independent verifier for one measured workload."""

    expected_proposals: tuple[CandidateProposal, ...]
    problem: bytes
    request: SearchRequest
    verifier: CrazyTargetVerifier


def full_domain_crazy_target_workload() -> CrazySearchBenchmarkWorkload:
    """Build the complete classic-word multiposition crazy-target workload.

    Returns:
        Canonical problem, request, 1,024 proposals, and trusted verifier.

    Raises:
        RuntimeError: If the exact preimage cardinality drifts.

    """
    candidates = tuple(range(CORPUS_SIZE))
    problem = CrazyTargetProblem(
        accumulator=ACCUMULATOR,
        target=TARGET,
        candidates=candidates,
    ).encode()
    request = SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=CORPUS_SIZE,
        problem=problem,
        seed=SEED,
    ).validated()
    expected = tuple(
        CandidateProposal(
            logical_id=f"corpus-{value}",
            payload=encode_crazy_candidate(value, ACCUMULATOR),
        )
        for value in _exact_preimage_words()
    )
    if len(expected) != PREIMAGE_COUNT:
        message = "crazy benchmark preimage cardinality drifted"
        raise RuntimeError(message)
    return CrazySearchBenchmarkWorkload(
        expected_proposals=expected,
        problem=problem,
        request=request,
        verifier=CrazyTargetVerifier(TARGET, ACCUMULATOR),
    )


def validate_crazy_search_benchmark_result(
    result: SearchResult,
    backend_id: str,
    workload: CrazySearchBenchmarkWorkload,
) -> None:
    """Require exact backend, proposal, and independent admission identity.

    Raises:
        RuntimeError: If backend, proposal, or admission identity changes.

    """
    if result.capability.backend_id != backend_id:
        message = "crazy search benchmark executed an unexpected backend"
        raise RuntimeError(message)
    if result.proposals != workload.expected_proposals:
        message = "crazy search benchmark changed exact proposal identity"
        raise RuntimeError(message)
    accepted = admit_search_result(result, workload.verifier)
    if accepted != workload.expected_proposals:
        message = "crazy search proposals failed independent CPU admission"
        raise RuntimeError(message)


def _exact_preimage_words() -> tuple[int, ...]:
    weights = tuple(3**index for index in range(TRIT_COUNT))
    return tuple(
        _word_from_mask(mask, weights) for mask in range(PREIMAGE_COUNT)
    )


def _word_from_mask(mask: int, weights: tuple[int, ...]) -> int:
    result = 0
    for index in range(TRIT_COUNT):
        if mask & (1 << index):
            result += weights[index]
    return result
