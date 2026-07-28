# File:
#   - exact_primitives.py
# Path:
#   - accelerator/exact_primitives.py
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
#   - Hardware-neutral exact discrete primitive batch contract.
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

"""Hardware-neutral exact discrete primitive batch contract."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from enum import StrEnum
import sys
from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

MAX_WORD = 59_048
ROTATE_HIGH_TRIT_WEIGHT = 19_683
TRIT_COUNT = 10
PREPARED_PRIMITIVE_STORAGE_ID = "proof-bound-u32le-primitive-input-v1"
_WORD_BYTES = 4
_LITTLE_ENDIAN = "little"
_PREPARED_PRIMITIVE_PROOF = object()


class AcceleratorError(RuntimeError):
    """Base failure for an optional accelerator adapter."""


class AcceleratorUnavailableError(AcceleratorError):
    """Requested accelerator runtime or hardware is unavailable."""


class AcceleratorExecutionError(AcceleratorError):
    """An available accelerator failed during compile or execution."""


class InvalidPrimitiveBatchError(AcceleratorError, ValueError):
    """A primitive batch violates the hardware-neutral exact contract."""


class PrimitiveKind(StrEnum):
    """Exact discrete operation implemented by replaceable adapters."""

    CRAZY = "crazy"
    ROTATE = "rotate"


@dataclass(frozen=True, slots=True)
class AcceleratorCapability:
    """Stable adapter identity and optional device metadata."""

    backend_id: str
    device_arch: str
    device_name: str


@dataclass(frozen=True, slots=True)
class PrimitiveBatch:
    """One homogeneous exact-operation batch."""

    accumulators: tuple[int, ...]
    data: tuple[int, ...]
    kind: PrimitiveKind

    def validated(self) -> PrimitiveBatch:
        """Validate exact classic-domain batch shape and values.

        Returns:
            The unchanged immutable batch after every invariant succeeds.

        Raises:
            InvalidPrimitiveBatchError: If shape or word domain is invalid.

        """
        if self.kind is PrimitiveKind.ROTATE and self.accumulators:
            message = "rotate batch must not carry accumulators"
            raise InvalidPrimitiveBatchError(message)
        if self.kind is PrimitiveKind.CRAZY and len(self.accumulators) != len(
            self.data
        ):
            message = "crazy batch arrays must have equal length"
            raise InvalidPrimitiveBatchError(message)
        for value in (*self.data, *self.accumulators):
            if not 0 <= value <= MAX_WORD:
                message = f"word outside classic domain: {value}"
                raise InvalidPrimitiveBatchError(message)
        return self


@dataclass(frozen=True, slots=True)
class PreparedPrimitiveBatch:
    """Proof-bound packed primitive input reusable across exact backends."""

    accumulators_u32le: bytes
    data_u32le: bytes
    kind: PrimitiveKind
    _proof: object

    def validated_storage(self) -> PreparedPrimitiveBatch:
        """Return packed state only for repository-created preparation.

        Returns:
            This immutable proof-bound packed primitive input.

        Raises:
            InvalidPrimitiveBatchError: If this state was forged.

        """
        if self._proof is not _PREPARED_PRIMITIVE_PROOF:
            message = "prepared primitive batch was not created by prepare"
            raise InvalidPrimitiveBatchError(message)
        return self

    def validated_batch(self) -> PrimitiveBatch:
        """Materialize the compatibility tuple batch on explicit request.

        Returns:
            Exact tuple-based primitive batch reconstructed from packed storage.

        """
        validated = self.validated_storage()
        return PrimitiveBatch(
            accumulators=_unpack_words(validated.accumulators_u32le),
            data=_unpack_words(validated.data_u32le),
            kind=validated.kind,
        )

    def count(self) -> int:
        """Return the exact prepared primitive cardinality.

        Returns:
            Number of packed data words.

        """
        _ = self.validated_storage()
        return len(self.data_u32le) // _WORD_BYTES


def prepared_primitive_storage_id() -> str:
    """Return the active proof-bound primitive input storage identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PREPARED_PRIMITIVE_STORAGE_ID


def prepare_primitive_batch(batch: PrimitiveBatch) -> PreparedPrimitiveBatch:
    """Validate one tuple batch and retain packed reusable proof.

    Returns:
        Hardware-neutral packed prepared primitive input.

    """
    validated = batch.validated()
    return prepare_packed_primitive_batch(
        accumulators_u32le=_pack_words(validated.accumulators),
        data_u32le=_pack_words(validated.data),
        kind=validated.kind,
    )


def prepare_packed_primitive_batch(
    *,
    accumulators_u32le: bytes,
    data_u32le: bytes,
    kind: PrimitiveKind,
) -> PreparedPrimitiveBatch:
    """Validate canonical packed words and retain reusable proof.

    Returns:
        Hardware-neutral packed prepared primitive input.

    """
    _validate_packed_prepared_shape(accumulators_u32le, data_u32le, kind)
    _validate_packed_words(data_u32le)
    _validate_packed_words(accumulators_u32le)
    return PreparedPrimitiveBatch(
        accumulators_u32le=accumulators_u32le,
        data_u32le=data_u32le,
        kind=kind,
        _proof=_PREPARED_PRIMITIVE_PROOF,
    )


def _validate_packed_prepared_shape(
    accumulators_u32le: bytes,
    data_u32le: bytes,
    kind: PrimitiveKind,
) -> None:
    if type(data_u32le) is not bytes or type(accumulators_u32le) is not bytes:
        message = "prepared primitive words must use immutable bytes"
        raise InvalidPrimitiveBatchError(message)
    if len(data_u32le) % _WORD_BYTES or len(accumulators_u32le) % _WORD_BYTES:
        message = "prepared primitive words must contain complete u32 values"
        raise InvalidPrimitiveBatchError(message)
    if kind is PrimitiveKind.ROTATE and accumulators_u32le:
        message = "rotate batch must not carry accumulators"
        raise InvalidPrimitiveBatchError(message)
    if kind is PrimitiveKind.CRAZY and len(accumulators_u32le) != len(
        data_u32le
    ):
        message = "crazy batch arrays must have equal length"
        raise InvalidPrimitiveBatchError(message)


def _validate_packed_words(words_u32le: bytes) -> None:
    for value in _iter_words(words_u32le):
        if value > MAX_WORD:
            message = f"word outside classic domain: {value}"
            raise InvalidPrimitiveBatchError(message)


def _pack_words(values: tuple[int, ...]) -> bytes:
    words = array("I", values)
    if words.itemsize != _WORD_BYTES:
        return b"".join(
            value.to_bytes(_WORD_BYTES, _LITTLE_ENDIAN) for value in values
        )
    if sys.byteorder != _LITTLE_ENDIAN:
        words.byteswap()
    return words.tobytes()


def _unpack_words(words_u32le: bytes) -> tuple[int, ...]:
    return tuple(_iter_words(words_u32le))


def _iter_words(words_u32le: bytes) -> Iterator[int]:
    if sys.byteorder == _LITTLE_ENDIAN:
        yield from memoryview(words_u32le).cast("I")
        return
    for offset in range(0, len(words_u32le), _WORD_BYTES):
        yield int.from_bytes(
            words_u32le[offset : offset + _WORD_BYTES],
            _LITTLE_ENDIAN,
        )


@dataclass(frozen=True, slots=True)
class PrimitiveResult:
    """Exact adapter result bound to one backend capability."""

    capability: AcceleratorCapability
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PackedPrimitiveResult:
    """Canonical little-endian u32 primitive words from one backend."""

    capability: AcceleratorCapability
    words_u32le: bytes


type PrimitiveExecutionResult = PrimitiveResult | PackedPrimitiveResult


class ExactPrimitiveAdapter(Protocol):
    """Replaceable exact primitive evaluation port."""

    def capability(self) -> AcceleratorCapability:
        """Return stable backend/device identity.

        Returns:
            Capability identity for this adapter instance.

        """
        ...

    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveExecutionResult:
        """Evaluate one batch with one-shot validation and execution.

        Returns:
            Exact results in input order with backend identity.

        """
        ...

    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveExecutionResult:
        """Evaluate repository-prepared immutable input.

        Returns:
            Exact results in input order with backend identity.

        """
        ...
