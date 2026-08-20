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
#   - Differential evidence for candidate-backed verification assistance.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Differential evidence for candidate-backed verification assistance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import override
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.evidence_verification import EvidenceVerificationAssistAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import decode_primitive_evidence
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import VerificationAssistBatch
from accelerator.work_ports import request_verification_hints

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.exact_primitives import PreparedPrimitiveBatch

VERIFIER_ID = "classic-rotate-check-v1"
CUDA_BACKEND = "cuda"
CORPUS_SIZE = 257
BAD_CAPABILITY = AcceleratorCapability(
    backend_id="bad",
    device_arch="bad",
    device_name="bad",
)


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _words(count: int) -> tuple[int, ...]:
    value = 0xA5A5_1F1F
    result: list[int] = []
    for _ in range(count):
        value = (value * 1_103_515_245 + 12_345) & 0xFFFF_FFFF
        result.append(value % (MAX_WORD + 1))
    return tuple(result)


def _batch() -> VerificationAssistBatch:
    return VerificationAssistBatch(
        items=tuple(
            CandidateWorkItem(
                logical_id=f"rotate-{index}",
                payload=encode_rotate_candidate(value),
            )
            for index, value in enumerate(_words(CORPUS_SIZE))
        ),
        verifier_id=VERIFIER_ID,
    )


def _adapter(
    primitive: ExactPrimitiveAdapter,
) -> EvidenceVerificationAssistAdapter:
    evaluator = PrimitiveCandidateEvaluationAdapter(
        primitive,
        PrimitiveKind.ROTATE,
    )
    return EvidenceVerificationAssistAdapter(
        evaluator,
        evaluator_id=ROTATE_EVALUATOR_ID,
        verifier_id=VERIFIER_ID,
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


def test_cpu_verification_assist_matches_exact_primitive_evidence() -> None:
    """CPU primitive evidence traverses the optional hint boundary unchanged."""
    batch = _batch()
    hints = request_verification_hints(
        batch, _adapter(CpuExactPrimitiveAdapter())
    )
    expected = CpuExactPrimitiveAdapter().evaluate(
        PrimitiveBatch(
            accumulators=(),
            data=_words(CORPUS_SIZE),
            kind=PrimitiveKind.ROTATE,
        )
    )

    assert tuple(decode_primitive_evidence(hint.payload) for hint in hints) == (
        expected.values
    )
    assert tuple(hint.logical_id for hint in hints) == tuple(
        item.logical_id for item in batch.items
    )


def test_live_cuda_verification_assist_matches_cpu_reference() -> None:
    """Live CUDA produces identical untrusted hints through the neutral port."""
    batch = _batch()
    cpu_hints = request_verification_hints(
        batch,
        _adapter(CpuExactPrimitiveAdapter()),
    )
    with _cuda() as cuda:
        adapter = _adapter(cuda)
        direct = adapter.assist(batch)
        cuda_hints = request_verification_hints(batch, adapter)

    assert direct.capability.backend_id == CUDA_BACKEND
    assert direct.hints == cpu_hints
    assert cuda_hints == cpu_hints


def test_malformed_optional_evidence_becomes_no_verification_hints() -> None:
    """Malformed accelerator evidence never reaches the trusted verifier."""
    hints = request_verification_hints(
        _batch(),
        _adapter(_MalformedPrimitiveAdapter()),
    )

    assert hints == ()


def test_verifier_identity_mismatch_fails_before_evidence_execution() -> None:
    """Verification assist cannot be silently reused under another identity."""
    batch = VerificationAssistBatch(
        items=_batch().items,
        verifier_id="other-verifier",
    )

    _expect_error(
        InvalidAcceleratorWorkError,
        "verification batch selects a different assist adapter",
        lambda: _adapter(_MalformedPrimitiveAdapter()).assist(batch),
    )


def test_malformed_direct_evidence_fails_closed() -> None:
    """Direct adapter use preserves structural evidence validation."""
    _expect_error(
        InvalidAcceleratorResultError,
        "primitive backend result count does not match candidate batch",
        lambda: _adapter(_MalformedPrimitiveAdapter()).assist(_batch()),
    )
