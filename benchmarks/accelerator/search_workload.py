# File:
#   - search_workload.py
# Path:
#   - benchmarks/accelerator/search_workload.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Shared exact full-domain workload for CPU/CUDA search measurements.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Shared exact full-domain workload for CPU/CUDA search measurements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING

from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import ROTATE_HIGH_TRIT_WEIGHT
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier

if TYPE_CHECKING:
    from accelerator.work_ports import SearchResult

SEED: Final = 17
CORPUS_SIZE: Final = MAX_WORD + 1
TARGET: Final = ROTATE_HIGH_TRIT_WEIGHT
WORKLOAD_ID: Final = "classic-rotate-target-full-domain-v1"
CPU_BACKEND: Final = "cpu-reference"
CUDA_BACKEND: Final = "cuda"
EXPECTED_PROPOSALS: Final = (
    CandidateProposal(
        logical_id="corpus-1",
        payload=encode_rotate_candidate(1),
    ),
)


@dataclass(frozen=True, slots=True)
class SearchBenchmarkWorkload:
    """Canonical problem, request, and independent verifier for measurements."""

    problem: bytes
    request: SearchRequest
    verifier: RotateTargetVerifier


def full_domain_rotate_target_workload() -> SearchBenchmarkWorkload:
    """Build the exact complete classic-word rotate-target workload.

    Returns:
        Canonical problem bytes, bounded request, and independent verifier.

    """
    problem = RotateTargetProblem(
        target=TARGET,
        candidates=tuple(range(CORPUS_SIZE)),
    ).encode()
    request = SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=CORPUS_SIZE,
        problem=problem,
        seed=SEED,
    ).validated()
    return SearchBenchmarkWorkload(
        problem=problem,
        request=request,
        verifier=RotateTargetVerifier(TARGET),
    )


def validate_search_benchmark_result(
    result: SearchResult,
    backend_id: str,
    verifier: RotateTargetVerifier,
) -> None:
    """Require exact backend, proposal, and trusted-admission identity.

    Raises:
        RuntimeError: If backend, proposal, or admission identity changes.

    """
    if result.capability.backend_id != backend_id:
        message = "search benchmark executed an unexpected backend"
        raise RuntimeError(message)
    if result.proposals != EXPECTED_PROPOSALS:
        message = "search benchmark changed exact proposal identity"
        raise RuntimeError(message)
    if admit_search_result(result, verifier) != EXPECTED_PROPOSALS:
        message = "search benchmark proposal failed independent CPU admission"
        raise RuntimeError(message)
