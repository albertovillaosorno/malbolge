# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Deterministic data model for authoring tree transformations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_ZERO = 0


class TreeModelError(ValueError):
    """Raised when a tree or transformation violates the model contract."""


@dataclass(frozen=True, slots=True, order=True)
class FileRecord:
    """One regular file in a deterministic tree snapshot."""

    path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class TreeSnapshot:
    """Sorted regular-file snapshot used for deterministic verification."""

    files: tuple[FileRecord, ...]


class ExactInstructionKind(StrEnum):
    """How one exact-baseline output file obtains its bytes."""

    COPY_SOURCE = "copy-source"
    PATCH_SOURCE = "patch-source"
    LITERAL_ORACLE = "literal-oracle"


@dataclass(frozen=True, slots=True)
class SourceSlice:
    """A byte range reused from an admitted source file."""

    offset: int
    length: int

    def __post_init__(self) -> None:
        """Reject nonsensical source ranges.

        Raises:
            TreeModelError: The range is negative or empty.

        """
        if self.offset < _ZERO or self.length <= _ZERO:
            message = (
                "source slices require a non-negative offset and positive "
                "length"
            )
            raise TreeModelError(message)


@dataclass(frozen=True, slots=True)
class OracleLiteral:
    """Target-only bytes retained only inside the local authoring plan."""

    data: bytes


ExactSegment = SourceSlice | OracleLiteral


@dataclass(frozen=True, slots=True)
class ExactInstruction:
    """One output-file instruction in a local authoring plan.

    Literal oracle bytes are intentionally allowed here because this model is
    local authoring evidence, not a distributable transform. Public emission
    must source-bind such material before serialization.
    """

    output_path: str
    kind: ExactInstructionKind
    expected_sha256: str
    source_path: str | None = None
    literal: bytes | None = None
    segments: tuple[ExactSegment, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous or incomplete instruction payloads.

        Raises:
            TreeModelError: The instruction payload does not match its kind.

        """
        if self.kind is ExactInstructionKind.COPY_SOURCE:
            self._validate_copy()
            return
        if self.kind is ExactInstructionKind.PATCH_SOURCE:
            self._validate_patch()
            return
        if self.kind is ExactInstructionKind.LITERAL_ORACLE:
            self._validate_literal()
            return
        message = f"unsupported exact instruction kind: {self.kind!r}"
        raise TreeModelError(message)

    def _validate_copy(self) -> None:
        if (
            self.source_path is None
            or self.literal is not None
            or self.segments
        ):
            message = "copy-source requires only source_path"
            raise TreeModelError(message)

    def _validate_patch(self) -> None:
        if (
            self.source_path is None
            or self.literal is not None
            or not self.segments
        ):
            message = "patch-source requires source_path and segments"
            raise TreeModelError(message)

    def _validate_literal(self) -> None:
        if (
            self.literal is None
            or self.source_path is not None
            or self.segments
        ):
            message = "literal-oracle requires only literal bytes"
            raise TreeModelError(message)


@dataclass(frozen=True, slots=True)
class ExactAuthoringPlan:
    """Local exact plan produced from a source tree and oracle tree."""

    source: TreeSnapshot
    target: TreeSnapshot
    instructions: tuple[ExactInstruction, ...]
