# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Correctness evidence for evaluated CPU/CUDA rotate-target search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import override
from unittest import SkipTest

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveResult
from accelerator.search_selection import SearchAdapterBinding
from accelerator.search_selection import SearchSelection
from accelerator.search_selection import resolve_search_execution
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.rotate_target import InvalidRotateTargetProblemError
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.exact_primitives import PrimitiveBatch

CPU_BACKEND = "cpu-reference"
CUDA_BACKEND = "cuda"
ROTATE_ONE = 19_683
BAD_CAPABILITY = AcceleratorCapability(
    backend_id="bad-search",
    device_arch="bad",
    device_name="bad",
)


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _request(
    problem: RotateTargetProblem,
    *,
    budget: int = 8,
    seed: int = 0,
) -> SearchRequest:
    return SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=budget,
        problem=problem.encode(),
        seed=seed,
    )


def _expect_problem_error(
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except InvalidRotateTargetProblemError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


@dataclass(frozen=True, slots=True)
class _MalformedPrimitiveAdapter(ExactPrimitiveAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        _ = batch.validated()
        return PrimitiveResult(capability=BAD_CAPABILITY, values=())


def test_rotate_target_problem_roundtrips_canonically() -> None:
    """Target/corpus identity is stable across canonical binary roundtrip."""
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 59_048),
    )

    encoded = problem.encode()
    decoded = RotateTargetProblem.decode(encoded)

    assert decoded == problem
    assert decoded.encode() == encoded


def test_problem_rejects_invalid_domain_and_encoding() -> None:
    """Malformed target/corpus bytes fail before any backend execution."""
    _expect_problem_error(
        "rotate target outside classic domain",
        lambda: RotateTargetProblem(target=59_049, candidates=()).validated(),
    )
    _expect_problem_error(
        "invalid magic",
        lambda: RotateTargetProblem.decode(b"wrong"),
    )
    valid = RotateTargetProblem(target=0, candidates=(1,)).encode()
    _expect_problem_error(
        "invalid candidate byte length",
        lambda: RotateTargetProblem.decode(valid[:-1]),
    )


def test_cpu_rotate_target_search_prunes_duplicates_and_finds_matches() -> None:
    """CPU reference proposes exact hits from stable representatives."""
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    adapter = cpu_rotate_target_search_adapter()

    result = adapter.search(_request(problem))

    assert result.capability.backend_id == CPU_BACKEND
    assert result.proposals == (
        CandidateProposal(
            logical_id="corpus-1",
            payload=(1).to_bytes(4, "little"),
        ),
    )


def test_seed_and_budget_bound_evaluated_search_order() -> None:
    """Seed rotates exact representatives while budget limits evaluations."""
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(1, 4, 7, 1),
    )
    adapter = cpu_rotate_target_search_adapter()

    missed = adapter.search(_request(problem, budget=1, seed=1))
    found = adapter.search(_request(problem, budget=1, seed=0))

    assert missed.proposals == ()
    assert tuple(item.logical_id for item in found.proposals) == ("corpus-0",)


def test_live_cuda_search_matches_cpu_and_records_backend_identity() -> None:
    """Live CUDA evaluates candidates inside the neutral search port."""
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=tuple(range(257)),
    )
    request = _request(problem, budget=257, seed=17)
    reference = cpu_rotate_target_search_adapter()
    with _cuda() as cuda:
        preferred = rotate_target_search_adapter(cuda)
        plan = resolve_search_execution(
            (
                SearchAdapterBinding(
                    adapter=reference,
                    algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
                ),
                SearchAdapterBinding(
                    adapter=preferred,
                    algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
                ),
            ),
            SearchSelection(
                algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
                backend_id=CUDA_BACKEND,
            ),
        )
        record = plan.run(request)
    expected = reference.search(request)

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CUDA_BACKEND
    assert record.result.proposals == expected.proposals
    accepted = admit_search_result(
        record.result,
        RotateTargetVerifier(ROTATE_ONE),
    )
    assert accepted == record.result.proposals


def test_malformed_optional_cuda_style_search_falls_back_to_cpu() -> None:
    """Malformed preferred evaluation changes capacity, not search semantics."""
    problem = RotateTargetProblem(target=ROTATE_ONE, candidates=(1, 4, 7))
    request = _request(problem)
    reference = cpu_rotate_target_search_adapter()
    preferred = rotate_target_search_adapter(_MalformedPrimitiveAdapter())
    plan = resolve_search_execution(
        (
            SearchAdapterBinding(
                adapter=reference,
                algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
            ),
            SearchAdapterBinding(
                adapter=preferred,
                algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
            ),
        ),
        SearchSelection(
            algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
            backend_id=BAD_CAPABILITY.backend_id,
        ),
    )

    record = plan.run(request)

    assert record.identity.configured_backend_id == BAD_CAPABILITY.backend_id
    assert record.identity.actual_backend_id == CPU_BACKEND
    assert record.result.proposals == reference.search(request).proposals
