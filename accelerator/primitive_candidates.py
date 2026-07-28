# File:
#   - primitive_candidates.py
# Path:
#   - accelerator/primitive_candidates.py
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
#   - Candidate-evaluation bridge for exact classic ternary primitives.
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

"""Candidate-evaluation bridge for exact classic ternary primitives."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from functools import lru_cache
import sys
from time import perf_counter_ns
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cpu.exact_primitives import CpuExactPrimitiveAdapter
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_primitive_batch
from accelerator.work_ports import CandidateEvaluationAdapter
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import PackedCandidateEvidence

if TYPE_CHECKING:
    from collections.abc import Iterator

    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.exact_primitives import ExactPrimitiveAdapter
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveExecutionResult
    from accelerator.work_ports import CandidateEvaluationBatch

CRAZY_EVALUATOR_ID = "classic-crazy-u32le-v1"
ROTATE_EVALUATOR_ID = "classic-rotate-u32le-v1"
PACKED_PRIMITIVE_VALIDATION_ID = "u32le-broadword-domain-v1"
PREPARED_PRIMITIVE_VALIDATION_ID = "cpu-reference-packed-equality-v1"
_WORD_BYTES = 4
_CRAZY_PAYLOAD_BYTES = 8
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"
_PREPARED_PRIMITIVE_PROOF = object()
_PACKED_LANE_BITS = 32
_PACKED_LANE_MAX = (1 << 16) - 1
_PACKED_DOMAIN_DELTA = _PACKED_LANE_MAX - MAX_WORD
_PACKED_HIGH_MASK = 0xFFFF_0000
_PACKED_CARRY_MASK = 0x0001_0000


@dataclass(frozen=True, slots=True)
class PackedPrimitiveEncodingPhaseProfile:
    """Diagnostic phases for validating and encoding packed primitive words."""

    contract_ns: int
    diagnostic_ns: int
    high_mask_ns: int
    int_decode_ns: int
    mask_lookup_ns: int
    result_build_ns: int
    threshold_ns: int
    total_ns: int


@dataclass(frozen=True, slots=True)
class PreparedPrimitiveEncodingPhaseProfile:
    """Diagnostic phases for exact prepared-reference evidence validation."""

    contract_ns: int
    diagnostic_ns: int
    exact_compare_ns: int
    result_build_ns: int
    total_ns: int


@dataclass(frozen=True, slots=True)
class _PreparedProfileMeasurement:
    contract_ns: int
    exact_compare_ns: int
    result: CandidateEvaluationResult
    result_build_ns: int


@dataclass(frozen=True, slots=True)
class _PackedWordPhaseProfile:
    high_mask_ns: int
    int_decode_ns: int
    mask_lookup_ns: int
    threshold_ns: int


@dataclass(frozen=True, slots=True)
class _DecodedBatch:
    accumulators: tuple[int, ...]
    data: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PreparedPrimitiveCandidateEvaluation:
    """Decoded primitive input reusable by matching exact backends."""

    batch: CandidateEvaluationBatch
    primitive: PreparedPrimitiveBatch
    evaluator_id: str
    expected_words_u32le: bytes | None
    kind: PrimitiveKind
    _proof: object

    def for_adapter(
        self,
        evaluator_id: str,
        kind: PrimitiveKind,
    ) -> tuple[CandidateEvaluationBatch, PreparedPrimitiveBatch, bytes | None]:
        """Return decoded state only to a matching primitive strategy.

        Returns:
            Original candidate batch, validated primitive batch, and optional
            trusted prepared-reference words.

        Raises:
            InvalidAcceleratorWorkError: If state is forged or mismatched.

        """
        if self._proof is not _PREPARED_PRIMITIVE_PROOF:
            message = "prepared primitive candidate state is forged"
            raise InvalidAcceleratorWorkError(message)
        if self.evaluator_id != evaluator_id or self.kind is not kind:
            message = (
                "prepared primitive candidate state selects another evaluator"
            )
            raise InvalidAcceleratorWorkError(message)
        if self.batch.evaluator_id != evaluator_id:
            message = "prepared primitive candidate batch identity changed"
            raise InvalidAcceleratorWorkError(message)
        return (self.batch, self.primitive, self.expected_words_u32le)


@final
class PrimitiveCandidateEvaluationAdapter(CandidateEvaluationAdapter):
    """Expose one exact primitive backend through candidate-evaluation work."""

    def __init__(
        self,
        adapter: ExactPrimitiveAdapter,
        kind: PrimitiveKind,
    ) -> None:
        """Bind one exact primitive kind to hardware-neutral candidate work."""
        self._adapter = adapter
        self._evaluator_id = _evaluator_id(kind)
        self._kind = kind

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the wrapped primitive backend identity.

        Returns:
            Exact capability reported by the wrapped adapter.

        """
        return self._adapter.capability()

    @override
    def evaluate(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationResult:
        """Evaluate encoded primitive candidates through the wrapped backend.

        Returns:
            Ordered four-byte little-endian exact evidence per candidate.

        """
        prepared = _prepare_primitive_candidate_batch(
            batch,
            self._kind,
            include_reference=False,
        )
        candidate_batch, primitive_batch, _ = prepared.for_adapter(
            self._evaluator_id,
            self._kind,
        )
        primitive = self._adapter.evaluate(
            primitive_batch.validated_batch(),
        )
        return _encode_result(
            candidate_batch,
            primitive,
            self.capability(),
        )

    def evaluate_prepared(
        self,
        state: object,
    ) -> CandidateEvaluationResult:
        """Evaluate already decoded primitive candidate state.

        Returns:
            Ordered fixed-width exact evidence in request order.

        Raises:
            InvalidAcceleratorWorkError: If state is forged or mismatched.

        """
        if not isinstance(state, PreparedPrimitiveCandidateEvaluation):
            message = "prepared primitive candidate state has wrong type"
            raise InvalidAcceleratorWorkError(message)
        batch, primitive_batch, expected_words = state.for_adapter(
            self._evaluator_id,
            self._kind,
        )
        if expected_words is None:
            message = (
                "prepared primitive candidate state has no trusted reference"
            )
            raise InvalidAcceleratorWorkError(message)
        primitive = self._adapter.evaluate_prepared(primitive_batch)
        return _encode_prepared_result(
            batch,
            primitive,
            self.capability(),
            expected_words_u32le=expected_words,
        )


def prepare_crazy_candidate_batch(
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare decoded crazy inputs for matching CPU/CUDA execution.

    Returns:
        Hardware-neutral immutable primitive candidate state.

    """
    return _prepare_primitive_candidate_batch(
        batch,
        PrimitiveKind.CRAZY,
        include_reference=True,
    )


def packed_primitive_validation_id() -> str:
    """Return the active packed primitive validation identity.

    Returns:
        Stable validation algorithm identifier for benchmark provenance.

    """
    return PACKED_PRIMITIVE_VALIDATION_ID


def prepared_primitive_validation_id() -> str:
    """Return the active exact prepared-result validation identity.

    Returns:
        Stable trusted-reference equality algorithm identifier.

    """
    return PREPARED_PRIMITIVE_VALIDATION_ID


def prepared_primitive_reference_word_count(state: object) -> int:
    """Return the proof-bound prepared CPU reference cardinality.

    Returns:
        Number of exact u32le reference words retained by preparation.

    """
    prepared = _prepared_candidate_state(state)
    expected = _required_expected_words(prepared)
    return len(expected) // _WORD_BYTES


def profile_prepared_primitive_result(
    state: object,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
) -> tuple[CandidateEvaluationResult, PreparedPrimitiveEncodingPhaseProfile]:
    """Validate one prepared result against its exact trusted CPU reference.

    Returns:
        Candidate evidence plus immutable exact-comparison phase diagnostics.

    """
    total_start = perf_counter_ns()
    measured = _profile_prepared_result(state, primitive, capability)
    return measured.result, PreparedPrimitiveEncodingPhaseProfile(
        contract_ns=measured.contract_ns,
        diagnostic_ns=0,
        exact_compare_ns=measured.exact_compare_ns,
        result_build_ns=measured.result_build_ns,
        total_ns=perf_counter_ns() - total_start,
    )


def _profile_prepared_result(
    state: object,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
) -> _PreparedProfileMeasurement:
    prepared = _prepared_candidate_state(state)
    expected = _required_expected_words(prepared)
    payloads, contract_ns = _timed_prepared_payloads(
        prepared,
        primitive,
        capability,
    )
    matches, exact_compare_ns = _timed_exact_compare(payloads, expected)
    if not matches:
        message = _prepared_mismatch_message(payloads, expected)
        raise InvalidAcceleratorResultError(message)
    result_start = perf_counter_ns()
    result = _candidate_result(prepared.batch, capability, payloads)
    return _PreparedProfileMeasurement(
        contract_ns=contract_ns,
        exact_compare_ns=exact_compare_ns,
        result=result,
        result_build_ns=perf_counter_ns() - result_start,
    )


def _timed_prepared_payloads(
    prepared: PreparedPrimitiveCandidateEvaluation,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
) -> tuple[bytes, int]:
    start = perf_counter_ns()
    payloads = _validated_primitive_payloads(
        prepared.batch,
        primitive,
        capability,
        validate_domain=False,
    )
    return payloads, perf_counter_ns() - start


def _timed_exact_compare(observed: bytes, expected: bytes) -> tuple[bool, int]:
    start = perf_counter_ns()
    matches = observed == expected
    return matches, perf_counter_ns() - start


def profile_packed_primitive_result(
    batch: CandidateEvaluationBatch,
    primitive: PackedPrimitiveResult,
    capability: AcceleratorCapability,
) -> tuple[CandidateEvaluationResult, PackedPrimitiveEncodingPhaseProfile]:
    """Encode one packed result while recording exact validation phases.

    Returns:
        Candidate evidence plus immutable per-phase timing diagnostics.

    """
    total_start = perf_counter_ns()
    contract_start = perf_counter_ns()
    payloads = _profile_validated_packed_payloads(
        batch,
        primitive,
        capability,
    )
    contract_ns = perf_counter_ns() - contract_start
    words = _profile_packed_words(payloads)
    result_start = perf_counter_ns()
    result = CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=_WORD_BYTES,
            payloads=payloads,
        ),
    )
    result_build_ns = perf_counter_ns() - result_start
    return result, PackedPrimitiveEncodingPhaseProfile(
        contract_ns=contract_ns,
        diagnostic_ns=0,
        high_mask_ns=words.high_mask_ns,
        int_decode_ns=words.int_decode_ns,
        mask_lookup_ns=words.mask_lookup_ns,
        result_build_ns=result_build_ns,
        threshold_ns=words.threshold_ns,
        total_ns=perf_counter_ns() - total_start,
    )


def _profile_validated_packed_payloads(
    batch: CandidateEvaluationBatch,
    primitive: PackedPrimitiveResult,
    capability: AcceleratorCapability,
) -> bytes:
    if primitive.capability != capability:
        message = "primitive backend changed capability identity"
        raise InvalidAcceleratorResultError(message)
    if type(primitive.words_u32le) is not bytes:
        message = "packed primitive result must use immutable bytes"
        raise InvalidAcceleratorResultError(message)
    if len(primitive.words_u32le) != len(batch.items) * _WORD_BYTES:
        message = "packed primitive result count does not match candidate batch"
        raise InvalidAcceleratorResultError(message)
    return primitive.words_u32le


def _profile_packed_words(payloads: bytes) -> _PackedWordPhaseProfile:
    if not payloads:
        return _PackedWordPhaseProfile(0, 0, 0, 0)
    masks, mask_lookup_ns = _timed_packed_masks(len(payloads) // _WORD_BYTES)
    packed, int_decode_ns = _timed_packed_decode(payloads)
    high_valid, high_mask_ns = _timed_high_mask(packed, masks[0])
    threshold_valid, threshold_ns = _timed_threshold(
        packed,
        masks[1],
        masks[2],
    )
    if not high_valid or not threshold_valid:
        maximum = max(_iter_u32le_words(payloads), default=0)
        message = f"primitive backend result outside classic domain: {maximum}"
        raise InvalidAcceleratorResultError(message)
    return _PackedWordPhaseProfile(
        high_mask_ns=high_mask_ns,
        int_decode_ns=int_decode_ns,
        mask_lookup_ns=mask_lookup_ns,
        threshold_ns=threshold_ns,
    )


def _timed_packed_masks(word_count: int) -> tuple[tuple[int, int, int], int]:
    start = perf_counter_ns()
    masks = _packed_domain_masks(word_count)
    return masks, perf_counter_ns() - start


def _timed_packed_decode(payloads: bytes) -> tuple[int, int]:
    start = perf_counter_ns()
    packed = int.from_bytes(payloads, _LITTLE_ENDIAN)
    return packed, perf_counter_ns() - start


def _timed_high_mask(packed: int, high_mask: int) -> tuple[bool, int]:
    start = perf_counter_ns()
    valid = not packed & high_mask
    return valid, perf_counter_ns() - start


def _timed_threshold(
    packed: int,
    delta_lanes: int,
    carry_mask: int,
) -> tuple[bool, int]:
    start = perf_counter_ns()
    valid = not (packed + delta_lanes) & carry_mask
    return valid, perf_counter_ns() - start


def prepare_rotate_candidate_batch(
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare decoded rotate inputs for matching CPU/CUDA execution.

    Returns:
        Hardware-neutral immutable primitive candidate state.

    """
    return _prepare_primitive_candidate_batch(
        batch,
        PrimitiveKind.ROTATE,
        include_reference=True,
    )


def encode_crazy_candidate(data: int, accumulator: int) -> bytes:
    """Encode one classic crazy candidate payload.

    Returns:
        Eight-byte little-endian data/accumulator payload.

    """
    _validate_word(data)
    _validate_word(accumulator)
    return b"".join((_encode_word(data), _encode_word(accumulator)))


def encode_rotate_candidate(data: int) -> bytes:
    """Encode one classic rotate candidate payload.

    Returns:
        Four-byte little-endian classic word payload.

    """
    _validate_word(data)
    return _encode_word(data)


def decode_primitive_evidence(payload: bytes) -> int:
    """Decode one exact primitive evidence payload.

    Returns:
        Classic-domain primitive result word.

    Raises:
        InvalidAcceleratorResultError: If evidence encoding/domain is invalid.

    """
    if len(payload) != _WORD_BYTES:
        message = "primitive candidate evidence must contain exactly one u32"
        raise InvalidAcceleratorResultError(message)
    value = int.from_bytes(payload, "little")
    _validate_evidence_word(value)
    return value


def primitive_evidence_value_at(
    result: CandidateEvaluationResult,
    index: int,
) -> int:
    """Read one exact primitive word by request-order index.

    Returns:
        Classic-domain primitive result word at ``index``.

    Raises:
        InvalidAcceleratorResultError: If index or evidence encoding is invalid.

    """
    if type(index) is not int or index < 0:
        message = "primitive evidence index must be nonnegative integer"
        raise InvalidAcceleratorResultError(message)
    if result.packed is not None:
        return _packed_primitive_value_at(result.packed, index)
    if index >= len(result.items):
        message = "primitive evidence index outside item result"
        raise InvalidAcceleratorResultError(message)
    return decode_primitive_evidence(result.items[index].payload)


def iter_primitive_evidence_values(
    result: CandidateEvaluationResult,
) -> Iterator[int]:
    """Iterate exact primitive words without materializing per-item payloads.

    Yields:
        Classic-domain primitive result words in request order.

    """
    if result.packed is not None:
        yield from _iter_packed_primitive_values(result.packed)
        return
    for item in result.items:
        yield decode_primitive_evidence(item.payload)


def _packed_primitive_value_at(
    packed: PackedCandidateEvidence,
    index: int,
) -> int:
    if packed.payload_width != _WORD_BYTES:
        message = "primitive packed evidence must use four-byte payloads"
        raise InvalidAcceleratorResultError(message)
    if len(packed.payloads) % _WORD_BYTES != 0:
        message = "primitive packed evidence has incomplete word payload"
        raise InvalidAcceleratorResultError(message)
    count = len(packed.payloads) // _WORD_BYTES
    if index >= count:
        message = "primitive evidence index outside packed result"
        raise InvalidAcceleratorResultError(message)
    start = index * _WORD_BYTES
    payload = memoryview(packed.payloads)[start : start + _WORD_BYTES]
    value = int.from_bytes(payload, _LITTLE_ENDIAN)
    _validate_evidence_word(value)
    return value


def _iter_packed_primitive_values(
    packed: PackedCandidateEvidence,
) -> Iterator[int]:
    if packed.payload_width != _WORD_BYTES:
        message = "primitive packed evidence must use four-byte payloads"
        raise InvalidAcceleratorResultError(message)
    if sys.byteorder == _LITTLE_ENDIAN:
        values = memoryview(packed.payloads).cast(_NATIVE_WORD_FORMAT)
        for value in values:
            _validate_evidence_word(value)
            yield value
        return
    for offset in range(0, len(packed.payloads), _WORD_BYTES):
        value = int.from_bytes(
            packed.payloads[offset : offset + _WORD_BYTES],
            _LITTLE_ENDIAN,
        )
        _validate_evidence_word(value)
        yield value


def _prepare_primitive_candidate_batch(
    batch: CandidateEvaluationBatch,
    kind: PrimitiveKind,
    *,
    include_reference: bool,
) -> PreparedPrimitiveCandidateEvaluation:
    validated = batch.validated()
    evaluator_id = _evaluator_id(kind)
    if validated.evaluator_id != evaluator_id:
        message = "candidate batch selects a different primitive evaluator"
        raise InvalidAcceleratorWorkError(message)
    decoded = _decode_batch(validated, kind)
    primitive = prepare_primitive_batch(
        PrimitiveBatch(
            accumulators=decoded.accumulators,
            data=decoded.data,
            kind=kind,
        )
    )
    expected_words = (
        _trusted_reference_words(primitive) if include_reference else None
    )
    return PreparedPrimitiveCandidateEvaluation(
        batch=validated,
        primitive=primitive,
        evaluator_id=evaluator_id,
        expected_words_u32le=expected_words,
        kind=kind,
        _proof=_PREPARED_PRIMITIVE_PROOF,
    )


def _prepared_candidate_state(
    state: object,
) -> PreparedPrimitiveCandidateEvaluation:
    if not isinstance(state, PreparedPrimitiveCandidateEvaluation):
        message = "prepared primitive candidate state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    _ = state.for_adapter(state.evaluator_id, state.kind)
    return state


def _required_expected_words(
    state: PreparedPrimitiveCandidateEvaluation,
) -> bytes:
    expected = state.expected_words_u32le
    if expected is None:
        message = "prepared primitive candidate state has no trusted reference"
        raise InvalidAcceleratorWorkError(message)
    if len(expected) != len(state.batch.items) * _WORD_BYTES:
        message = "prepared primitive trusted reference count changed"
        raise InvalidAcceleratorWorkError(message)
    return expected


def _trusted_reference_words(prepared: PreparedPrimitiveBatch) -> bytes:
    reference = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    _validate_primitive_values(reference.values)
    return _pack_words(reference.values)


def _decode_batch(
    batch: CandidateEvaluationBatch,
    kind: PrimitiveKind,
) -> _DecodedBatch:
    data: list[int] = []
    accumulators: list[int] = []
    for item in batch.items:
        if kind is PrimitiveKind.CRAZY:
            word, accumulator = _decode_crazy(item.payload)
            accumulators.append(accumulator)
        else:
            word = _decode_rotate(item.payload)
        data.append(word)
    return _DecodedBatch(
        accumulators=tuple(accumulators),
        data=tuple(data),
    )


def _decode_crazy(payload: bytes) -> tuple[int, int]:
    if len(payload) != _CRAZY_PAYLOAD_BYTES:
        message = "crazy candidate payload must contain exactly two u32 words"
        raise InvalidAcceleratorWorkError(message)
    data = int.from_bytes(payload[:_WORD_BYTES], "little")
    accumulator = int.from_bytes(payload[_WORD_BYTES:], "little")
    _validate_word(data)
    _validate_word(accumulator)
    return (data, accumulator)


def _decode_rotate(payload: bytes) -> int:
    if len(payload) != _WORD_BYTES:
        message = "rotate candidate payload must contain exactly one u32 word"
        raise InvalidAcceleratorWorkError(message)
    value = int.from_bytes(payload, "little")
    _validate_word(value)
    return value


def _encode_prepared_result(
    batch: CandidateEvaluationBatch,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
    *,
    expected_words_u32le: bytes,
) -> CandidateEvaluationResult:
    payloads = _validated_primitive_payloads(
        batch,
        primitive,
        capability,
        validate_domain=False,
    )
    if payloads != expected_words_u32le:
        message = _prepared_mismatch_message(payloads, expected_words_u32le)
        raise InvalidAcceleratorResultError(message)
    return _candidate_result(batch, capability, payloads)


def _validated_primitive_payloads(
    batch: CandidateEvaluationBatch,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
    *,
    validate_domain: bool,
) -> bytes:
    if primitive.capability != capability:
        message = "primitive backend changed capability identity"
        raise InvalidAcceleratorResultError(message)
    if isinstance(primitive, PackedPrimitiveResult):
        return _validated_packed_payloads(
            batch,
            primitive.words_u32le,
            validate_domain=validate_domain,
        )
    return _validated_tuple_payloads(batch, primitive.values)


def _validated_packed_payloads(
    batch: CandidateEvaluationBatch,
    payloads: bytes,
    *,
    validate_domain: bool,
) -> bytes:
    if type(payloads) is not bytes:
        message = "packed primitive result must use immutable bytes"
        raise InvalidAcceleratorResultError(message)
    if len(payloads) != len(batch.items) * _WORD_BYTES:
        message = "packed primitive result count does not match candidate batch"
        raise InvalidAcceleratorResultError(message)
    if validate_domain:
        _validate_packed_primitive_words(payloads)
    return payloads


def _validated_tuple_payloads(
    batch: CandidateEvaluationBatch,
    values: tuple[int, ...],
) -> bytes:
    if len(values) != len(batch.items):
        message = (
            "primitive backend result count does not match candidate batch"
        )
        raise InvalidAcceleratorResultError(message)
    _validate_primitive_values(values)
    return _pack_words(values)


def _candidate_result(
    batch: CandidateEvaluationBatch,
    capability: AcceleratorCapability,
    payloads: bytes,
) -> CandidateEvaluationResult:
    return CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=_WORD_BYTES,
            payloads=payloads,
        ),
    )


def _prepared_mismatch_message(observed: bytes, expected: bytes) -> str:
    for index in range(0, len(expected), _WORD_BYTES):
        observed_word = int.from_bytes(
            observed[index : index + _WORD_BYTES],
            _LITTLE_ENDIAN,
        )
        expected_word = int.from_bytes(
            expected[index : index + _WORD_BYTES],
            _LITTLE_ENDIAN,
        )
        if observed_word != expected_word:
            word_index = index // _WORD_BYTES
            return (
                "prepared primitive result differs from trusted CPU reference "
                f"at word {word_index}: expected {expected_word}, "
                f"observed {observed_word}"
            )
    return "prepared primitive result differs from trusted CPU reference"


def _encode_result(
    batch: CandidateEvaluationBatch,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
) -> CandidateEvaluationResult:
    payloads = _validated_primitive_payloads(
        batch,
        primitive,
        capability,
        validate_domain=True,
    )
    return _candidate_result(batch, capability, payloads)


def _validate_packed_primitive_words(payloads: bytes) -> None:
    if not payloads:
        return
    word_count = len(payloads) // _WORD_BYTES
    high_mask, delta_lanes, carry_mask = _packed_domain_masks(word_count)
    packed = int.from_bytes(payloads, _LITTLE_ENDIAN)
    # High bits first establish unsigned 16-bit lanes. Adding 0xffff-MAX_WORD
    # cannot cross a 32-bit lane; bit 16 is set exactly when that lane is
    # too large.
    if not packed & high_mask and not (packed + delta_lanes) & carry_mask:
        return
    maximum = max(_iter_u32le_words(payloads), default=0)
    message = f"primitive backend result outside classic domain: {maximum}"
    raise InvalidAcceleratorResultError(message)


@lru_cache(maxsize=4)
def _packed_domain_masks(word_count: int) -> tuple[int, int, int]:
    """Build repeated masks for exact independent 32-bit lane validation.

    Returns:
        High-bit, threshold-delta, and threshold-carry masks.

    """
    lane_repetition = ((1 << (_PACKED_LANE_BITS * word_count)) - 1) // (
        (1 << _PACKED_LANE_BITS) - 1
    )
    return (
        _PACKED_HIGH_MASK * lane_repetition,
        _PACKED_DOMAIN_DELTA * lane_repetition,
        _PACKED_CARRY_MASK * lane_repetition,
    )


def _iter_u32le_words(payloads: bytes) -> Iterator[int]:
    for offset in range(0, len(payloads), _WORD_BYTES):
        yield int.from_bytes(
            payloads[offset : offset + _WORD_BYTES],
            _LITTLE_ENDIAN,
        )


def _validate_primitive_values(values: tuple[int, ...]) -> None:
    if not values:
        return
    minimum = min(values)
    maximum = max(values)
    if minimum < 0:
        invalid = minimum
    elif maximum > MAX_WORD:
        invalid = maximum
    else:
        return
    message = f"primitive backend result outside classic domain: {invalid}"
    raise InvalidAcceleratorResultError(message)


def _pack_words(values: tuple[int, ...]) -> bytes:
    words = array("I", values)
    if words.itemsize != _WORD_BYTES:
        message = "native unsigned-int width cannot encode packed u32 evidence"
        raise InvalidAcceleratorResultError(message)
    if sys.byteorder != _LITTLE_ENDIAN:
        words.byteswap()
    return words.tobytes()


def _validate_evidence_word(value: int) -> None:
    if value > MAX_WORD:
        message = (
            f"primitive candidate evidence outside classic domain: {value}"
        )
        raise InvalidAcceleratorResultError(message)


def _encode_word(value: int) -> bytes:
    return value.to_bytes(_WORD_BYTES, "little")


def _evaluator_id(kind: PrimitiveKind) -> str:
    if kind is PrimitiveKind.CRAZY:
        return CRAZY_EVALUATOR_ID
    return ROTATE_EVALUATOR_ID


def _validate_word(value: int) -> None:
    if not 0 <= value <= MAX_WORD:
        message = f"primitive candidate word outside classic domain: {value}"
        raise InvalidAcceleratorWorkError(message)
