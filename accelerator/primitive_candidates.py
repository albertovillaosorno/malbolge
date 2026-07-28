# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Candidate-evaluation bridge for exact classic ternary primitives."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from functools import lru_cache
import sys
from typing import TYPE_CHECKING
from typing import final
from typing import override

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
class _DecodedBatch:
    accumulators: tuple[int, ...]
    data: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PreparedPrimitiveCandidateEvaluation:
    """Decoded primitive input reusable by matching exact backends."""

    batch: CandidateEvaluationBatch
    primitive: PreparedPrimitiveBatch
    evaluator_id: str
    kind: PrimitiveKind
    _proof: object

    def for_adapter(
        self,
        evaluator_id: str,
        kind: PrimitiveKind,
    ) -> tuple[CandidateEvaluationBatch, PreparedPrimitiveBatch]:
        """Return decoded state only to a matching primitive strategy.

        Returns:
            Original candidate batch and validated primitive batch.

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
        return (self.batch, self.primitive)


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
        prepared = _prepare_primitive_candidate_batch(batch, self._kind)
        candidate_batch, primitive_batch = prepared.for_adapter(
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
        batch, primitive_batch = state.for_adapter(
            self._evaluator_id,
            self._kind,
        )
        primitive = self._adapter.evaluate_prepared(primitive_batch)
        return _encode_result(batch, primitive, self.capability())


def prepare_crazy_candidate_batch(
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare decoded crazy inputs for matching CPU/CUDA execution.

    Returns:
        Hardware-neutral immutable primitive candidate state.

    """
    return _prepare_primitive_candidate_batch(batch, PrimitiveKind.CRAZY)


def packed_primitive_validation_id() -> str:
    """Return the active packed primitive validation identity.

    Returns:
        Stable validation algorithm identifier for benchmark provenance.

    """
    return PACKED_PRIMITIVE_VALIDATION_ID


def prepare_rotate_candidate_batch(
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare decoded rotate inputs for matching CPU/CUDA execution.

    Returns:
        Hardware-neutral immutable primitive candidate state.

    """
    return _prepare_primitive_candidate_batch(batch, PrimitiveKind.ROTATE)


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
    return PreparedPrimitiveCandidateEvaluation(
        batch=validated,
        primitive=primitive,
        evaluator_id=evaluator_id,
        kind=kind,
        _proof=_PREPARED_PRIMITIVE_PROOF,
    )


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


def _encode_result(
    batch: CandidateEvaluationBatch,
    primitive: PrimitiveExecutionResult,
    capability: AcceleratorCapability,
) -> CandidateEvaluationResult:
    if primitive.capability != capability:
        message = "primitive backend changed capability identity"
        raise InvalidAcceleratorResultError(message)
    if isinstance(primitive, PackedPrimitiveResult):
        return _encode_packed_result(batch, primitive, capability)
    if len(primitive.values) != len(batch.items):
        message = (
            "primitive backend result count does not match candidate batch"
        )
        raise InvalidAcceleratorResultError(message)
    _validate_primitive_values(primitive.values)
    return CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=_WORD_BYTES,
            payloads=_pack_words(primitive.values),
        ),
    )


def _encode_packed_result(
    batch: CandidateEvaluationBatch,
    primitive: PackedPrimitiveResult,
    capability: AcceleratorCapability,
) -> CandidateEvaluationResult:
    if type(primitive.words_u32le) is not bytes:
        message = "packed primitive result must use immutable bytes"
        raise InvalidAcceleratorResultError(message)
    expected_bytes = len(batch.items) * _WORD_BYTES
    if len(primitive.words_u32le) != expected_bytes:
        message = "packed primitive result count does not match candidate batch"
        raise InvalidAcceleratorResultError(message)
    _validate_packed_primitive_words(primitive.words_u32le)
    return CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=_WORD_BYTES,
            payloads=primitive.words_u32le,
        ),
    )


def _validate_packed_primitive_words(payloads: bytes) -> None:
    if not payloads:
        return
    word_count = len(payloads) // _WORD_BYTES
    high_mask, delta_lanes, carry_mask = _packed_domain_masks(word_count)
    packed = int.from_bytes(payloads, _LITTLE_ENDIAN)
    # High bits first establish unsigned 16-bit lanes. Adding 0xffff-MAX_WORD
    # cannot cross a 32-bit lane; bit 16 is set exactly when that lane is too large.
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
