# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Differential evidence for primitive-backed candidate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import override
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PreparedPrimitiveBatch
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult
from accelerator.exact_primitives import prepare_primitive_batch
from accelerator.primitive_candidates import CRAZY_EVALUATOR_ID
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_crazy_candidate
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.primitive_candidates import iter_primitive_evidence_values
from accelerator.primitive_candidates import prepare_rotate_candidate_batch
from accelerator.primitive_candidates import primitive_evidence_value_at
from accelerator.primitive_candidates import profile_packed_primitive_result
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
EVIDENCE_WORD_BYTES = 4
ROTATE_ONE = 19_683
BAD_MODE_CAPABILITY = "capability"
BAD_MODE_COUNT = "count"
BAD_MODE_DOMAIN = "domain"
BAD_MODE_NEGATIVE = "negative"
BAD_PACKED_MODE_CAPABILITY = "packed-capability"
BAD_PACKED_MODE_COUNT = "packed-count"
BAD_PACKED_MODE_DOMAIN = "packed-domain"
BAD_PACKED_MODE_HIGH_BITS = "packed-high-bits"
BAD_PACKED_MODE_LATE_DOMAIN = "packed-late-domain"
BAD_PACKED_MODE_LATE_HIGH_BITS = "packed-late-high-bits"
BAD_PACKED_MODE_MUTABLE = "packed-mutable"
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
        capability = BAD_CAPABILITY
        if self.mode == BAD_MODE_CAPABILITY:
            capability = AcceleratorCapability(
                backend_id="other",
                device_arch="bad",
                device_name="bad",
            )
            values = (0,) * count
        elif self.mode == BAD_MODE_COUNT:
            values = ()
        elif self.mode == BAD_MODE_NEGATIVE:
            values = (-1,) * count
        else:
            values = (MAX_WORD + 1,) * count
        return PrimitiveResult(capability=capability, values=values)

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        return self.evaluate(prepared.validated_batch())


@dataclass(frozen=True, slots=True)
class _BadPackedResultAdapter(ExactPrimitiveAdapter):
    mode: str

    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PackedPrimitiveResult:
        capability = BAD_CAPABILITY
        if self.mode == BAD_PACKED_MODE_CAPABILITY:
            capability = AcceleratorCapability(
                backend_id="other",
                device_arch="bad",
                device_name="bad",
            )
        return PackedPrimitiveResult(
            capability=capability,
            words_u32le=_bad_packed_payloads(self.mode, len(batch.data)),
        )

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PackedPrimitiveResult:
        return self.evaluate(prepared.validated_batch())


def _bad_packed_payloads(mode: str, count: int) -> bytes:
    fixed = {
        BAD_PACKED_MODE_COUNT: b"",
        BAD_PACKED_MODE_DOMAIN: (MAX_WORD + 1).to_bytes(4, "little"),
        BAD_PACKED_MODE_HIGH_BITS: (1 << 16).to_bytes(4, "little"),
    }
    late = {
        BAD_PACKED_MODE_LATE_DOMAIN: MAX_WORD + 1,
        BAD_PACKED_MODE_LATE_HIGH_BITS: 1 << 16,
    }
    if mode in fixed:
        payloads = fixed[mode]
    elif mode in late:
        payloads = (b"\0" * (4 * (count - 1))) + late[mode].to_bytes(
            4, "little"
        )
    elif mode == BAD_PACKED_MODE_MUTABLE:
        payloads = cast("bytes", cast("object", bytearray(4 * count)))
    else:
        payloads = b"".join((0).to_bytes(4, "little") for _ in range(count))
    return payloads


def test_cpu_candidate_bridge_preserves_exact_crazy_results() -> None:
    """Candidate evidence matches the exact CPU crazy primitive."""
    batch = _crazy_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.CRAZY,
    )

    result = adapter.evaluate(batch)

    observed = tuple(iter_primitive_evidence_values(result))
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
    assert result.items == ()
    assert result.packed is not None
    assert result.packed.payload_width == EVIDENCE_WORD_BYTES


def test_cpu_prepared_rotate_matches_exhaustive_scalar_reference() -> None:
    """Prepared lookup matches scalar rotate over the full domain."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"rotate-{value}",
                payload=encode_rotate_candidate(value),
            )
            for value in range(MAX_WORD + 1)
        ),
    )
    primitive = CpuExactPrimitiveAdapter()
    adapter = PrimitiveCandidateEvaluationAdapter(
        primitive,
        PrimitiveKind.ROTATE,
    )
    prepared = prepare_rotate_candidate_batch(batch)

    ordinary = adapter.evaluate(batch)
    assert primitive.prepared_stats().evaluations == 0
    reused = adapter.evaluate_prepared(prepared)
    stats = primitive.prepared_stats()

    assert reused.packed == ordinary.packed
    assert (stats.evaluations, stats.rotate_table_entries) == (
        1,
        MAX_WORD + 1,
    )
    assert tuple(iter_primitive_evidence_values(reused)) == tuple(
        iter_primitive_evidence_values(ordinary)
    )


def test_cpu_candidate_bridge_preserves_exact_rotate_results() -> None:
    """Candidate evidence matches the exact CPU rotate primitive."""
    batch = _rotate_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )

    result = adapter.evaluate(batch)

    observed = tuple(iter_primitive_evidence_values(result))
    expected = CpuExactPrimitiveAdapter().evaluate(
        PrimitiveBatch(
            accumulators=(),
            data=_words(CORPUS_SIZE),
            kind=PrimitiveKind.ROTATE,
        )
    )
    assert observed == expected.values


def test_packed_primitive_evidence_supports_exact_index_lookup() -> None:
    """Packed primitive evidence exposes bounded request-order word lookup."""
    batch = _rotate_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    result = adapter.evaluate(batch)
    expected = tuple(iter_primitive_evidence_values(result))

    assert primitive_evidence_value_at(result, 0) == expected[0]
    assert primitive_evidence_value_at(result, CORPUS_SIZE - 1) == expected[-1]
    _expect_error(
        InvalidAcceleratorResultError,
        "primitive evidence index outside packed result",
        lambda: primitive_evidence_value_at(result, CORPUS_SIZE),
    )
    _expect_error(
        InvalidAcceleratorResultError,
        "primitive evidence index must be nonnegative integer",
        lambda: primitive_evidence_value_at(result, -1),
    )


def test_prepared_rotate_candidate_state_matches_ordinary_result() -> None:
    """Decoded rotate input is reusable without changing packed evidence."""
    batch = _rotate_batch()
    adapter = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )

    state = prepare_rotate_candidate_batch(batch)
    ordinary = adapter.evaluate(batch)
    prepared = adapter.evaluate_prepared(state)

    assert prepared == ordinary


def test_prepared_primitive_batch_rejects_forged_proof() -> None:
    """Raw dataclass construction cannot forge validated primitive input."""
    batch = PrimitiveBatch(
        accumulators=(),
        data=(1,),
        kind=PrimitiveKind.ROTATE,
    )
    forged = PreparedPrimitiveBatch(batch=batch, _proof=object())

    _expect_error(
        InvalidPrimitiveBatchError,
        "prepared primitive batch was not created by prepare",
        forged.validated_batch,
    )
    prepared = prepare_primitive_batch(batch)
    assert prepared.validated_batch() is batch


def test_prepared_primitive_state_rejects_wrong_type_and_kind() -> None:
    """Prepared primitive state fails closed when forged or cross-operated."""
    rotate = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    crazy = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.CRAZY,
    )
    state = prepare_rotate_candidate_batch(_rotate_batch())

    _expect_error(
        InvalidAcceleratorWorkError,
        "prepared primitive candidate state has wrong type",
        lambda: rotate.evaluate_prepared(object()),
    )
    _expect_error(
        InvalidAcceleratorWorkError,
        "prepared primitive candidate state selects another evaluator",
        lambda: crazy.evaluate_prepared(state),
    )


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
        ("negative", "primitive backend result outside classic domain: -1"),
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


def test_malformed_packed_primitive_results_fail_closed() -> None:
    """Packed capability, count, and domain drift cannot become evidence."""
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
        (
            BAD_PACKED_MODE_CAPABILITY,
            "primitive backend changed capability identity",
        ),
        (
            BAD_PACKED_MODE_COUNT,
            "packed primitive result count does not match candidate batch",
        ),
        (
            BAD_PACKED_MODE_DOMAIN,
            "primitive backend result outside classic domain",
        ),
        (
            BAD_PACKED_MODE_HIGH_BITS,
            "primitive backend result outside classic domain: 65536",
        ),
        (
            BAD_PACKED_MODE_MUTABLE,
            "packed primitive result must use immutable bytes",
        ),
    )
    for mode, message in cases:
        adapter = PrimitiveCandidateEvaluationAdapter(
            _BadPackedResultAdapter(mode),
            PrimitiveKind.ROTATE,
        )
        _expect_error(
            InvalidAcceleratorResultError,
            message,
            lambda adapter=adapter: adapter.evaluate(batch),
        )


def test_profiled_packed_encoding_matches_normal_bridge() -> None:
    """Profiled encoding preserves the ordinary candidate result exactly."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"word-{index}",
                payload=encode_rotate_candidate(index),
            )
            for index in range(3)
        ),
    )
    primitive = PackedPrimitiveResult(
        capability=BAD_CAPABILITY,
        words_u32le=b"\0" * (3 * EVIDENCE_WORD_BYTES),
    )
    expected = PrimitiveCandidateEvaluationAdapter(
        _BadPackedResultAdapter("valid"),
        PrimitiveKind.ROTATE,
    ).evaluate(batch)

    observed, profile = profile_packed_primitive_result(
        batch,
        primitive,
        BAD_CAPABILITY,
    )

    assert observed == expected
    assert profile.diagnostic_ns == 0
    components = (
        profile.contract_ns,
        profile.high_mask_ns,
        profile.int_decode_ns,
        profile.mask_lookup_ns,
        profile.result_build_ns,
        profile.threshold_ns,
    )
    assert all(value >= 0 for value in components)
    assert profile.total_ns >= sum(components)


def test_packed_domain_validation_checks_late_lanes() -> None:
    """Repeated masks reject threshold and high-bit drift in the final lane."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"word-{index}",
                payload=encode_rotate_candidate(index),
            )
            for index in range(3)
        ),
    )
    cases = (
        (
            BAD_PACKED_MODE_LATE_DOMAIN,
            "primitive backend result outside classic domain: 59049",
        ),
        (
            BAD_PACKED_MODE_LATE_HIGH_BITS,
            "primitive backend result outside classic domain: 65536",
        ),
    )
    for mode, message in cases:
        adapter = PrimitiveCandidateEvaluationAdapter(
            _BadPackedResultAdapter(mode),
            PrimitiveKind.ROTATE,
        )
        _expect_error(
            InvalidAcceleratorResultError,
            message,
            lambda adapter=adapter: adapter.evaluate(batch),
        )


def test_live_cuda_profiled_prepared_matches_normal_result() -> None:
    """Profiled resident CUDA preserves exact packed output and counters."""
    values = _words(CORPUS_SIZE)
    prepared = prepare_primitive_batch(
        PrimitiveBatch(
            accumulators=(),
            data=values,
            kind=PrimitiveKind.ROTATE,
        )
    )
    with _cuda() as cuda:
        ordinary = cuda.evaluate_prepared(prepared)
        profiled, phases = cuda.profile_prepared(prepared)
        stats = cuda.prepared_stats()

    assert isinstance(ordinary, PackedPrimitiveResult)
    assert profiled == ordinary
    assert (
        stats.builds,
        stats.evaluations,
        stats.packed_evaluations,
        stats.reuses,
        stats.resident_count,
        stats.resident_kind,
    ) == (1, 2, 2, 1, CORPUS_SIZE, PrimitiveKind.ROTATE)
    components = (
        phases.download_ns,
        phases.immutable_bytes_ns,
        phases.launch_sync_ns,
    )
    assert all(value >= 0 for value in components)
    assert phases.total_ns >= sum(components)


def test_live_cuda_prepared_session_reuses_exact_input() -> None:
    """Ordinary stays one-shot while prepared CUDA reuses resident input."""
    batch = _rotate_batch()
    state = prepare_rotate_candidate_batch(batch)
    expected = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    ).evaluate(batch)

    with _cuda() as cuda:
        adapter = PrimitiveCandidateEvaluationAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        ordinary = adapter.evaluate(batch)
        assert cuda.prepared_stats().builds == 0
        first = adapter.evaluate_prepared(state)
        first_stats = cuda.prepared_stats()
        second = adapter.evaluate_prepared(state)
        second_stats = cuda.prepared_stats()

    assert ordinary.packed == expected.packed
    assert first.packed == expected.packed
    assert second.packed == expected.packed
    assert (
        first_stats.builds,
        first_stats.evaluations,
        first_stats.packed_evaluations,
        first_stats.reuses,
        first_stats.resident_count,
        first_stats.resident_kind,
    ) == (1, 1, 1, 0, CORPUS_SIZE, PrimitiveKind.ROTATE)
    assert (
        second_stats.builds,
        second_stats.evaluations,
        second_stats.packed_evaluations,
        second_stats.reuses,
    ) == (1, 2, 2, 1)


def test_live_cuda_prepared_session_rebuilds_new_proof() -> None:
    """Equal content under another proof replaces resident CUDA input."""
    batch = _rotate_batch()
    first = prepare_rotate_candidate_batch(batch)
    replacement = prepare_rotate_candidate_batch(batch)

    with _cuda() as cuda:
        adapter = PrimitiveCandidateEvaluationAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        first_result = adapter.evaluate_prepared(first)
        replacement_result = adapter.evaluate_prepared(replacement)
        stats = cuda.prepared_stats()

    assert replacement_result.packed == first_result.packed
    assert (
        stats.builds,
        stats.evaluations,
        stats.packed_evaluations,
        stats.reuses,
    ) == (2, 2, 2, 0)


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
    assert result.packed == expected.packed
    assert tuple(iter_primitive_evidence_values(result)) == tuple(
        iter_primitive_evidence_values(expected)
    )


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
    assert result.packed == expected.packed
    assert tuple(iter_primitive_evidence_values(result)) == tuple(
        iter_primitive_evidence_values(expected)
    )


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
    assert tuple(iter_primitive_evidence_values(result)) == (ROTATE_ONE,)
