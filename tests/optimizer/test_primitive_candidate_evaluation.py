# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Differential evidence for primitive-backed candidate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import override
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult
from accelerator.primitive_candidates import CRAZY_EVALUATOR_ID
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import decode_primitive_evidence
from accelerator.primitive_candidates import encode_crazy_candidate
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import evaluate_candidates

if TYPE_CHECKING:
    from collections.abc import Callable

CUDA_BACKEND = "cuda"
CPU_BACKEND = "cpu-reference"
CORPUS_SIZE = 257
ROTATE_ONE = 19_683
BAD_MODE_CAPABILITY = "capability"
BAD_MODE_COUNT = "count"
BAD_MODE_DOMAIN = "domain"
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


def _words(count: int) -> tuple[int, ...]:
    value = 0x1234_5678
    result: list[int] = []
    for _ in range(count):
        value = (value * 1_664_525 + 1_013_904_223) & 0xFFFF_FFFF
        result.append(value % (MAX_WORD + 1))
    return tuple(result)


def _crazy_batch() -> CandidateEvaluationBatch:
    words = _words(CORPUS_SIZE)
    reversed_words = tuple(reversed(words))
    items = tuple(
        CandidateWorkItem(
            logical_id=f"crazy-{index}",
            payload=encode_crazy_candidate(data, accumulator),
        )
        for index, (data, accumulator) in enumerate(
            zip(words, reversed_words, strict=True)
        )
    )
    return CandidateEvaluationBatch(
        evaluator_id=CRAZY_EVALUATOR_ID,
        items=items,
    )


def _rotate_batch() -> CandidateEvaluationBatch:
    items = tuple(
        CandidateWorkItem(
            logical_id=f"rotate-{index}",
            payload=encode_rotate_candidate(value),
        )
        for index, value in enumerate(_words(CORPUS_SIZE))
    )
    return CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=items,
    )


@dataclass(frozen=True, slots=True)
class _BadResultAdapter(ExactPrimitiveAdapter):
    mode: str

    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        count = len(batch.data)
        if self.mode == BAD_MODE_CAPABILITY:
            capability = AcceleratorCapability(
                backend_id="other",
                device_arch="bad",
                device_name="bad",
            )
            return PrimitiveResult(capability=capability, values=(0,) * count)
        if self.mode == BAD_MODE_COUNT:
            return PrimitiveResult(capability=BAD_CAPABILITY, values=())
        return PrimitiveResult(
            capability=BAD_CAPABILITY,
            values=(MAX_WORD + 1,) * count,
        )


def test_cpu_candidate_bridge_preserves_exact_crazy_results() -> None:
    """Candidate evidence matches the exact CPU crazy primitive."""
    batch = _crazy_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.CRAZY,
    )

    result = adapter.evaluate(batch)

    observed = tuple(
        decode_primitive_evidence(item.payload) for item in result.items
    )
    words = _words(CORPUS_SIZE)
    expected = CpuExactPrimitiveAdapter().evaluate(
        PrimitiveBatch(
            accumulators=tuple(reversed(words)),
            data=words,
            kind=PrimitiveKind.CRAZY,
        )
    )
    assert observed == expected.values
    assert result.capability.backend_id == CPU_BACKEND


def test_cpu_candidate_bridge_preserves_exact_rotate_results() -> None:
    """Candidate evidence matches the exact CPU rotate primitive."""
    batch = _rotate_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )

    result = adapter.evaluate(batch)

    observed = tuple(
        decode_primitive_evidence(item.payload) for item in result.items
    )
    expected = CpuExactPrimitiveAdapter().evaluate(
        PrimitiveBatch(
            accumulators=(),
            data=_words(CORPUS_SIZE),
            kind=PrimitiveKind.ROTATE,
        )
    )
    assert observed == expected.values


def test_malformed_candidate_payload_fails_before_primitive_backend() -> None:
    """Malformed primitive work is rejected before hardware evaluation."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=(CandidateWorkItem(logical_id="bad", payload=b"bad"),),
    )
    adapter = PrimitiveCandidateEvaluationAdapter(
        _BadResultAdapter(BAD_MODE_CAPABILITY),
        PrimitiveKind.ROTATE,
    )

    _expect_error(
        InvalidAcceleratorWorkError,
        "rotate candidate payload must contain exactly one u32 word",
        lambda: adapter.evaluate(batch),
    )


def test_out_of_domain_candidate_is_rejected_before_backend() -> None:
    """Encoded u32 values outside classic word domain fail as work errors."""
    payload = (MAX_WORD + 1).to_bytes(4, "little")
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=(CandidateWorkItem(logical_id="bad", payload=payload),),
    )
    adapter = PrimitiveCandidateEvaluationAdapter(
        _BadResultAdapter(BAD_MODE_CAPABILITY),
        PrimitiveKind.ROTATE,
    )

    _expect_error(
        InvalidAcceleratorWorkError,
        "primitive candidate word outside classic domain",
        lambda: adapter.evaluate(batch),
    )


def test_malformed_primitive_results_fail_closed() -> None:
    """Capability, count, and result-domain drift cannot become evidence."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=(
            CandidateWorkItem(
                logical_id="one",
                payload=encode_rotate_candidate(1),
            ),
        ),
    )
    cases = (
        ("capability", "primitive backend changed capability identity"),
        (
            "count",
            "primitive backend result count does not match candidate batch",
        ),
        ("domain", "primitive backend result outside classic domain"),
    )
    for mode, message in cases:
        adapter = PrimitiveCandidateEvaluationAdapter(
            _BadResultAdapter(mode),
            PrimitiveKind.ROTATE,
        )
        _expect_error(
            InvalidAcceleratorResultError,
            message,
            lambda adapter=adapter: adapter.evaluate(batch),
        )


def test_cuda_candidate_crazy_port_matches_cpu_reference() -> None:
    """Live CUDA matches CPU through the neutral crazy candidate port."""
    batch = _crazy_batch()
    reference = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.CRAZY,
    )
    with _cuda() as cuda:
        preferred = PrimitiveCandidateEvaluationAdapter(
            cuda, PrimitiveKind.CRAZY
        )
        result = evaluate_candidates(batch, reference, preferred)
    expected = reference.evaluate(batch)

    assert result.capability.backend_id == CUDA_BACKEND
    assert result.items == expected.items


def test_cuda_candidate_rotate_port_matches_cpu_reference() -> None:
    """Live CUDA matches CPU through the neutral rotate candidate port."""
    batch = _rotate_batch()
    reference = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    with _cuda() as cuda:
        preferred = PrimitiveCandidateEvaluationAdapter(
            cuda, PrimitiveKind.ROTATE
        )
        result = evaluate_candidates(batch, reference, preferred)
    expected = reference.evaluate(batch)

    assert result.capability.backend_id == CUDA_BACKEND
    assert result.items == expected.items


def test_malformed_preferred_primitive_backend_falls_back_to_cpu() -> None:
    """Malformed optional primitive evidence falls back to CPU reference."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=(
            CandidateWorkItem(
                logical_id="one",
                payload=encode_rotate_candidate(1),
            ),
        ),
    )
    reference = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    preferred = PrimitiveCandidateEvaluationAdapter(
        _BadResultAdapter(BAD_MODE_COUNT),
        PrimitiveKind.ROTATE,
    )

    result = evaluate_candidates(batch, reference, preferred)

    assert result.capability.backend_id == CPU_BACKEND
    assert decode_primitive_evidence(result.items[0].payload) == ROTATE_ONE
