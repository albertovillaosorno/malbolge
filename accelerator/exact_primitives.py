# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Hardware-neutral exact discrete primitive batch contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

MAX_WORD = 59_048
ROTATE_HIGH_TRIT_WEIGHT = 19_683
TRIT_COUNT = 10


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
class PrimitiveResult:
    """Exact adapter result bound to one backend capability."""

    capability: AcceleratorCapability
    values: tuple[int, ...]


class ExactPrimitiveAdapter(Protocol):
    """Replaceable exact primitive evaluation port."""

    def capability(self) -> AcceleratorCapability:
        """Return stable backend/device identity.

        Returns:
            Capability identity for this adapter instance.

        """
        ...

    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        """Evaluate one validated batch without changing acceptance rules.

        Returns:
            Exact results in input order with backend identity.

        """
        ...
