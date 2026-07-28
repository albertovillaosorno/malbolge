# File:
#   - test_rotate_target_search.py
# Path:
#   - tests/optimizer/test_rotate_target_search.py
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
#   - Correctness evidence for evaluated CPU/CUDA rotate-target search.
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
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.rotate_target import InvalidRotateTargetProblemError
from optimizer.rotate_target import PreparedRotateTargetSelection
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import build_rotate_target_batch
from optimizer.rotate_target import count_prepared_rotate_target_positions
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.exact_primitives import PreparedPrimitiveBatch
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


def _expect_work_error(
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except InvalidAcceleratorWorkError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


def _expect_result_error(
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except InvalidAcceleratorResultError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


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
class _ZeroPrimitiveAdapter(ExactPrimitiveAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        validated = batch.validated()
        return PrimitiveResult(
            capability=BAD_CAPABILITY,
            values=(0,) * len(validated.data),
        )

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        return self.evaluate(prepared.validated_batch())


@dataclass(frozen=True, slots=True)
class _MalformedPrimitiveAdapter(ExactPrimitiveAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        _ = batch.validated()
        return PrimitiveResult(capability=BAD_CAPABILITY, values=())

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        return self.evaluate(prepared.validated_batch())


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
    assert RotateTargetProblem.decode_target(encoded) == ROTATE_ONE


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
    _expect_problem_error(
        "invalid candidate byte length",
        lambda: RotateTargetProblem.decode_target(valid[:-1]),
    )
    invalid_target = (
        b"MBRTS1\0" + (59_049).to_bytes(4, "little") + (0).to_bytes(4, "little")
    )
    _expect_problem_error(
        "rotate target outside classic domain",
        lambda: RotateTargetProblem.decode_target(invalid_target),
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


def test_prepared_rotate_selection_tracks_seed_budget_and_absence() -> None:
    """Prepared inverse positions match ordinary exact search cases."""
    cases = (
        (
            RotateTargetProblem(
                target=ROTATE_ONE,
                candidates=(0, 1, 2, 1, 4),
            ),
            8,
            0,
            1,
        ),
        (RotateTargetProblem(target=ROTATE_ONE, candidates=(0, 2, 4)), 8, 0, 0),
        (
            RotateTargetProblem(target=ROTATE_ONE, candidates=(1, 4, 7, 1)),
            1,
            1,
            0,
        ),
    )
    adapter = cpu_rotate_target_search_adapter()
    for problem, budget, seed, expected_count in cases:
        request = _request(problem, budget=budget, seed=seed)
        prepared = adapter.prepare(request)
        assert adapter.prepared_selection_count(prepared) == expected_count
        assert adapter.search_prepared(prepared) == adapter.search(request)


def test_prepared_rotate_selection_rejects_wrong_exact_evidence() -> None:
    """Prepared search rejects in-domain evidence differing from CPU truth."""
    problem = RotateTargetProblem(target=ROTATE_ONE, candidates=(1, 4, 7))
    adapter = rotate_target_search_adapter(_ZeroPrimitiveAdapter())
    prepared = adapter.prepare(_request(problem))

    assert adapter.prepared_selection_count(prepared) == 1
    _expect_result_error(
        "trusted CPU reference at word 0: expected 19683, observed 0",
        lambda: adapter.search_prepared(prepared),
    )


def test_prepared_rotate_selection_rejects_forged_state() -> None:
    """Raw rotate selector state construction cannot forge prepared identity."""
    request = _request(RotateTargetProblem(target=ROTATE_ONE, candidates=(1,)))
    batch = build_rotate_target_batch(request)
    forged = PreparedRotateTargetSelection(
        request=request,
        batch=batch,
        target=ROTATE_ONE,
        positions=(0,),
        _proof=object(),
    )

    _expect_work_error(
        "prepared rotate selection state is forged",
        lambda: count_prepared_rotate_target_positions(forged),
    )
    _expect_work_error(
        "prepared rotate selection state has wrong type",
        lambda: count_prepared_rotate_target_positions(object()),
    )


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


def test_prepared_cpu_state_executes_unchanged_on_live_cuda() -> None:
    """Hardware-neutral prepared state crosses exact CPU/CUDA capacity."""
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=tuple(range(257)),
    )
    request = _request(problem, budget=257, seed=17)
    reference = cpu_rotate_target_search_adapter()
    prepared = reference.prepare(request)
    assert reference.prepared_selection_count(prepared) == 1
    expected = reference.search_prepared(prepared)

    with _cuda() as cuda:
        observed = rotate_target_search_adapter(cuda).search_prepared(prepared)

    assert observed.capability.backend_id == CUDA_BACKEND
    assert observed.proposals == expected.proposals
    assert (
        admit_search_result(
            observed,
            RotateTargetVerifier(ROTATE_ONE),
        )
        == observed.proposals
    )


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
