# File:
#   - test_accelerator_work_ports.py
# Path:
#   - tests/optimizer/test_accelerator_work_ports.py
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
#   - Contract tests for candidate/search/verification accelerator ports.
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

"""Contract tests for candidate/search/verification accelerator ports."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cpu import CpuCandidateEvaluationAdapter
from accelerator.cpu import CpuSearchExecutionAdapter
from accelerator.cpu.work_ports import CPU_WORK_CAPABILITY
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.work_ports import CandidateEvaluationAdapter
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateEvidence
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import PackedCandidateEvidence
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import SearchResult
from accelerator.work_ports import TrustedCandidateVerifier
from accelerator.work_ports import VerificationAssistAdapter
from accelerator.work_ports import VerificationAssistBatch
from accelerator.work_ports import VerificationAssistResult
from accelerator.work_ports import VerificationHint
from accelerator.work_ports import admit_search_result
from accelerator.work_ports import evaluate_candidates
from accelerator.work_ports import execute_search
from accelerator.work_ports import indexed_candidate_items_id
from accelerator.work_ports import request_verification_hints

if TYPE_CHECKING:
    from collections.abc import Callable

INDEXED_FIRST_LOGICAL_INDEX = 7
EXPECTED_INDEXED_CANDIDATE_ITEMS_ID = (
    "u32-index-fixed-width-payloads-rotation-v1"
)
INDEXED_ITEM_COUNT = 2

TEST_CAPABILITY = AcceleratorCapability(
    backend_id="test-optional",
    device_arch="test",
    device_name="test-device",
)


def _reverse(payload: bytes) -> bytes:
    return bytes(reversed(payload))


def _search(request: SearchRequest) -> tuple[CandidateProposal, ...]:
    count = min(request.evaluation_budget, 2)
    return tuple(
        CandidateProposal(
            logical_id=f"candidate-{index}",
            payload=request.problem + bytes((index,)),
        )
        for index in range(count)
    )


def _expect_error(
    exception: type[Exception],
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except exception as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


@final
class _FailingCandidateBackend(CandidateEvaluationAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return TEST_CAPABILITY

    @override
    def evaluate(
        self, batch: CandidateEvaluationBatch
    ) -> CandidateEvaluationResult:
        _ = batch.validated()
        message = "optional candidate backend failed"
        raise AcceleratorExecutionError(message)


@final
class _MalformedCandidateBackend(CandidateEvaluationAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return TEST_CAPABILITY

    @override
    def evaluate(
        self, batch: CandidateEvaluationBatch
    ) -> CandidateEvaluationResult:
        return CandidateEvaluationResult(
            capability=TEST_CAPABILITY,
            evaluator_id=batch.evaluator_id,
            items=(CandidateEvidence(logical_id="wrong", payload=b"bad"),),
        )


@final
class _FailingSearchBackend(SearchExecutionAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return TEST_CAPABILITY

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        _ = request.validated()
        message = "optional search backend failed"
        raise AcceleratorExecutionError(message)


@final
class _HintBackend(VerificationAssistAdapter):
    def __init__(self, *, malformed: bool = False) -> None:
        self._malformed = malformed

    @override
    def capability(self) -> AcceleratorCapability:
        return TEST_CAPABILITY

    @override
    def assist(
        self, batch: VerificationAssistBatch
    ) -> VerificationAssistResult:
        hints = tuple(
            VerificationHint(
                logical_id=("wrong" if self._malformed else item.logical_id),
                payload=item.payload[::-1],
            )
            for item in batch.items
        )
        return VerificationAssistResult(
            capability=TEST_CAPABILITY,
            hints=hints,
            verifier_id=batch.verifier_id,
        )


@final
class _TrustedVerifier(TrustedCandidateVerifier):
    @override
    def accepts(
        self,
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        expected_hint = candidate.payload[::-1]
        return hint is not None and hint.payload == expected_hint


def test_indexed_candidate_items_have_stable_identity() -> None:
    """Benchmark provenance names the exact candidate storage algorithm."""
    assert indexed_candidate_items_id() == EXPECTED_INDEXED_CANDIDATE_ITEMS_ID


def test_indexed_candidate_items_preserve_request_order_and_identity() -> None:
    """Packed indexes and payloads materialize the exact candidate surface."""
    items = IndexedCandidateWorkItems(
        logical_id_prefix="corpus-",
        logical_indices_u32le=(7).to_bytes(4, "little")
        + (2).to_bytes(4, "little"),
        payload_width=2,
        payloads=b"AABB",
    )

    assert items.validated() is items
    assert len(items) == INDEXED_ITEM_COUNT
    assert tuple(items) == (
        CandidateWorkItem(logical_id="corpus-7", payload=b"AA"),
        CandidateWorkItem(logical_id="corpus-2", payload=b"BB"),
    )
    assert items[-1] == CandidateWorkItem(
        logical_id="corpus-2",
        payload=b"BB",
    )
    assert items[:1] == (
        CandidateWorkItem(logical_id="corpus-7", payload=b"AA"),
    )
    assert items.parse_logical_id("corpus-7") == INDEXED_FIRST_LOGICAL_INDEX
    assert items.parse_logical_id("corpus-07") is None
    assert items.parse_logical_id("other-7") is None
    assert items.payload_matches(1, b"BB")
    assert not items.payload_matches(1, b"B")


def test_indexed_candidate_items_reject_malformed_storage() -> None:
    """Indexed item shape and logical uniqueness fail closed."""
    cases = (
        (
            IndexedCandidateWorkItems(
                logical_id_prefix="",
                logical_indices_u32le=b"",
                payload_width=1,
                payloads=b"",
            ),
            "candidate logical ID prefix must not be empty",
        ),
        (
            IndexedCandidateWorkItems(
                logical_id_prefix="candidate-",
                logical_indices_u32le=b"bad",
                payload_width=1,
                payloads=b"",
            ),
            "logical indexes must contain complete u32s",
        ),
        (
            IndexedCandidateWorkItems(
                logical_id_prefix="candidate-",
                logical_indices_u32le=(1).to_bytes(4, "little"),
                payload_width=2,
                payloads=b"A",
            ),
            "payload size does not match logical indexes",
        ),
        (
            IndexedCandidateWorkItems(
                logical_id_prefix="candidate-",
                logical_indices_u32le=(1).to_bytes(4, "little") * 2,
                payload_width=1,
                payloads=b"AB",
            ),
            "duplicate candidate logical ID",
        ),
        (
            IndexedCandidateWorkItems(
                logical_id_prefix="candidate-",
                logical_indices_u32le=(1).to_bytes(4, "little")
                + (2).to_bytes(4, "little"),
                payload_width=1,
                payloads=b"AB",
                logical_rotation_pivot=1,
            ),
            "rotation pivot does not match logical order",
        ),
    )
    for items, message in cases:
        _expect_error(
            InvalidAcceleratorWorkError,
            message,
            items.validated,
        )


def test_candidate_evaluation_falls_back_to_cpu_reference() -> None:
    """Optional backend failure cannot remove the CPU candidate baseline."""
    batch = CandidateEvaluationBatch(
        evaluator_id="reverse-bytes-v1",
        items=(
            CandidateWorkItem(logical_id="a", payload=b"abc"),
            CandidateWorkItem(logical_id="b", payload=b"xyz"),
        ),
    )
    reference = CpuCandidateEvaluationAdapter("reverse-bytes-v1", _reverse)

    result = evaluate_candidates(batch, reference, _FailingCandidateBackend())

    assert tuple(item.payload for item in result.items) == (b"cba", b"zyx")
    assert result.capability == CPU_WORK_CAPABILITY


def test_malformed_candidate_backend_shape_falls_back() -> None:
    """Malformed optional evidence never changes the reference path."""
    batch = CandidateEvaluationBatch(
        evaluator_id="reverse-bytes-v1",
        items=(CandidateWorkItem(logical_id="a", payload=b"abc"),),
    )
    reference = CpuCandidateEvaluationAdapter("reverse-bytes-v1", _reverse)

    result = evaluate_candidates(batch, reference, _MalformedCandidateBackend())

    assert result.items == (CandidateEvidence(logical_id="a", payload=b"cba"),)


def test_packed_candidate_evidence_restores_request_identities() -> None:
    """Packed payloads inherit exact logical identity from validated order."""
    batch = CandidateEvaluationBatch(
        evaluator_id="packed-v1",
        items=(
            CandidateWorkItem(logical_id="a", payload=b"input-a"),
            CandidateWorkItem(logical_id="b", payload=b"input-b"),
        ),
    )
    result = CandidateEvaluationResult(
        capability=TEST_CAPABILITY,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=2,
            payloads=b"AABB",
        ),
    )

    items = result.materialized_items_against(batch, TEST_CAPABILITY)

    assert items == (
        CandidateEvidence(logical_id="a", payload=b"AA"),
        CandidateEvidence(logical_id="b", payload=b"BB"),
    )


def test_packed_candidate_evidence_rejects_malformed_shapes() -> None:
    """Packed results fail closed on width, size, storage, or mixed forms."""
    batch = CandidateEvaluationBatch(
        evaluator_id="packed-v1",
        items=(CandidateWorkItem(logical_id="a", payload=b"input"),),
    )
    cases = (
        (
            PackedCandidateEvidence(payload_width=0, payloads=b""),
            (),
            "width must be positive",
        ),
        (
            PackedCandidateEvidence(payload_width=2, payloads=b"A"),
            (),
            "size does not match request",
        ),
        (
            PackedCandidateEvidence(payload_width=1, payloads=b"A"),
            (CandidateEvidence(logical_id="a", payload=b"A"),),
            "cannot mix packed and item forms",
        ),
    )
    for packed, items, message in cases:
        result = CandidateEvaluationResult(
            capability=TEST_CAPABILITY,
            evaluator_id=batch.evaluator_id,
            items=items,
            packed=packed,
        )
        _expect_error(
            InvalidAcceleratorResultError,
            message,
            lambda result=result: result.validated_against(
                batch,
                TEST_CAPABILITY,
            ),
        )


def test_candidate_request_rejects_duplicate_identity_before_execution() -> (
    None
):
    """Duplicate logical IDs fail before either backend receives work."""
    batch = CandidateEvaluationBatch(
        evaluator_id="reverse-bytes-v1",
        items=(
            CandidateWorkItem(logical_id="same", payload=b"a"),
            CandidateWorkItem(logical_id="same", payload=b"b"),
        ),
    )
    reference = CpuCandidateEvaluationAdapter("reverse-bytes-v1", _reverse)

    _expect_error(
        InvalidAcceleratorWorkError,
        "duplicate candidate logical ID",
        lambda: evaluate_candidates(batch, reference),
    )


def test_search_fallback_preserves_algorithm_seed_and_budget() -> None:
    """Search hardware failure changes capacity rather than search identity."""
    request = SearchRequest(
        algorithm_id="deterministic-enumeration-v1",
        evaluation_budget=2,
        problem=b"problem",
        seed=17,
    )
    reference = CpuSearchExecutionAdapter(
        "deterministic-enumeration-v1",
        _search,
    )

    result = execute_search(request, reference, _FailingSearchBackend())

    assert result.algorithm_id == request.algorithm_id
    assert result.seed == request.seed
    assert tuple(item.logical_id for item in result.proposals) == (
        "candidate-0",
        "candidate-1",
    )


def test_search_result_cannot_exceed_declared_budget() -> None:
    """An adapter cannot smuggle extra proposals beyond the work budget."""
    request = SearchRequest(
        algorithm_id="deterministic-enumeration-v1",
        evaluation_budget=1,
        problem=b"problem",
        seed=17,
    )
    result = SearchResult(
        algorithm_id=request.algorithm_id,
        capability=TEST_CAPABILITY,
        proposals=(
            CandidateProposal(logical_id="a", payload=b"a"),
            CandidateProposal(logical_id="b", payload=b"b"),
        ),
        seed=request.seed,
    )

    _expect_error(
        InvalidAcceleratorResultError,
        "search result exceeds declared evaluation budget",
        lambda: result.validated_against(request, TEST_CAPABILITY),
    )


def test_verification_assist_failure_is_equivalent_to_no_hints() -> None:
    """Verification assistance is optional and cannot become authority."""
    batch = VerificationAssistBatch(
        items=(CandidateWorkItem(logical_id="a", payload=b"abc"),),
        verifier_id="trusted-check-v1",
    )
    malformed = _HintBackend(malformed=True)

    assert request_verification_hints(batch) == ()
    assert request_verification_hints(batch, malformed) == ()


def test_only_trusted_verifier_admits_search_proposals() -> None:
    """Accelerator search and hints cannot mark their own proposals accepted."""
    request = SearchRequest(
        algorithm_id="deterministic-enumeration-v1",
        evaluation_budget=2,
        problem=b"problem",
        seed=17,
    )
    reference = CpuSearchExecutionAdapter(
        "deterministic-enumeration-v1",
        _search,
    )
    result = execute_search(request, reference)
    assist_batch = VerificationAssistBatch(
        items=tuple(
            CandidateWorkItem(
                logical_id=proposal.logical_id,
                payload=proposal.payload,
            )
            for proposal in result.proposals
        ),
        verifier_id="trusted-check-v1",
    )
    hints = request_verification_hints(assist_batch, _HintBackend())

    accepted = admit_search_result(result, _TrustedVerifier(), hints)

    assert accepted == result.proposals
    bad_hint = replace(hints[0], payload=b"wrong")
    accepted_bad = admit_search_result(
        result,
        _TrustedVerifier(),
        (bad_hint, *hints[1:]),
    )
    assert accepted_bad == result.proposals[1:]


def test_admission_rejects_duplicate_proposal_identity() -> None:
    """Trusted admission rejects malformed search identity."""
    result = SearchResult(
        algorithm_id="deterministic-enumeration-v1",
        capability=TEST_CAPABILITY,
        proposals=(
            CandidateProposal(logical_id="same", payload=b"a"),
            CandidateProposal(logical_id="same", payload=b"b"),
        ),
        seed=17,
    )

    _expect_error(
        InvalidAcceleratorResultError,
        "duplicate search candidate logical ID",
        lambda: admit_search_result(result, _TrustedVerifier()),
    )
