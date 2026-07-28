# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Candidate-evaluation bridge for exact classic ternary primitives."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import sys
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.work_ports import CandidateEvaluationAdapter
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import PackedCandidateEvidence

if TYPE_CHECKING:
    from collections.abc import Iterator

    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.exact_primitives import ExactPrimitiveAdapter
    from accelerator.exact_primitives import PrimitiveResult
    from accelerator.work_ports import CandidateEvaluationBatch

CRAZY_EVALUATOR_ID = "classic-crazy-u32le-v1"
ROTATE_EVALUATOR_ID = "classic-rotate-u32le-v1"
_WORD_BYTES = 4
_CRAZY_PAYLOAD_BYTES = 8
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"


@dataclass(frozen=True, slots=True)
class _DecodedBatch:
    accumulators: tuple[int, ...]
    data: tuple[int, ...]


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

        Raises:
            InvalidAcceleratorWorkError: If evaluator identity is malformed.

        """
        validated = batch.validated()
        if validated.evaluator_id != self._evaluator_id:
            message = "candidate batch selects a different primitive evaluator"
            raise InvalidAcceleratorWorkError(message)
        decoded = _decode_batch(validated, self._kind)
        primitive = self._adapter.evaluate(
            PrimitiveBatch(
                accumulators=decoded.accumulators,
                data=decoded.data,
                kind=self._kind,
            )
        )
        return _encode_result(validated, primitive, self.capability())


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
    primitive: PrimitiveResult,
    capability: AcceleratorCapability,
) -> CandidateEvaluationResult:
    if primitive.capability != capability:
        message = "primitive backend changed capability identity"
        raise InvalidAcceleratorResultError(message)
    if len(primitive.values) != len(batch.items):
        message = (
            "primitive backend result count does not match candidate batch"
        )
        raise InvalidAcceleratorResultError(message)
    for value in primitive.values:
        if not 0 <= value <= MAX_WORD:
            message = (
                f"primitive backend result outside classic domain: {value}"
            )
            raise InvalidAcceleratorResultError(message)
    return CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        packed=PackedCandidateEvidence(
            payload_width=_WORD_BYTES,
            payloads=_pack_words(primitive.values),
        ),
    )


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
