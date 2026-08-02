# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
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
#   - Relocatable compatible-placement authoring over exact source ranges.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""
Relocatable compatible-placement authoring over exact source ranges.

This layer is intentionally non-distributable. It proves that exact authoring
source spans can be relocated in a later candidate without relying on absolute
offsets. Target-only literals remain local authoring bytes until the protected
compatible-plan layer is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import shutil
from typing import TYPE_CHECKING

from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.model import ExactInstruction
    from algorithms.diff.model import ExactSegment
    from algorithms.diff.model import SourceSlice

_ZERO = 0
_ONE = 1
_BOUNDARY_BYTES = 32
_STAGING_SUFFIX = ".relocatable-staging"
_BACKSLASH = "\\"
_DOT = "."
_PARENT = ".."


class RelocationError(RuntimeError):
    """Raised when compatible source placement is unsafe or ambiguous."""


@dataclass(frozen=True, slots=True)
class RangeLocator:
    """Hash-only locator for one source range in a later candidate file."""

    source_length: int
    window_bytes: int
    start_digest: bytes
    end_digest: bytes | None = None

    def __post_init__(self) -> None:
        """Reject malformed range locators.

        Raises:
            RelocationError: Locator widths or digests are invalid.

        """
        if self.source_length <= _ZERO:
            message = "relocatable source ranges must be non-empty"
            raise RelocationError(message)
        if self.window_bytes <= _ZERO or self.window_bytes > self.source_length:
            message = "relocatable boundary width exceeds source range"
            raise RelocationError(message)
        if len(self.start_digest) != hashlib.sha256().digest_size:
            message = "relocatable start digest must be SHA-256"
            raise RelocationError(message)
        if (
            self.end_digest is not None
            and len(self.end_digest) != hashlib.sha256().digest_size
        ):
            message = "relocatable end digest must be SHA-256"
            raise RelocationError(message)


@dataclass(frozen=True, slots=True)
class RelocatableSourceRange:
    """Source-backed output segment located by content rather than offset."""

    locator: RangeLocator


RelocatableSegment = RelocatableSourceRange | OracleLiteral


@dataclass(frozen=True, slots=True)
class RelocatableInstruction:
    """One compatible-placement output instruction."""

    output_path: str
    source_path: str | None
    copy_candidate_file: bool
    literal: bytes | None = None
    segments: tuple[RelocatableSegment, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous instruction forms.

        Raises:
            RelocationError: More than one payload form is configured.

        """
        forms = sum((
            self.copy_candidate_file,
            self.literal is not None,
            bool(self.segments),
        ))
        if forms != _ONE:
            message = (
                "relocatable instruction requires exactly one payload form"
            )
            raise RelocationError(message)
        if self.copy_candidate_file and self.source_path is None:
            message = "candidate-file copy requires a source path"
            raise RelocationError(message)
        if self.segments and self.source_path is None:
            message = "relocatable segments require a source path"
            raise RelocationError(message)
        if self.literal is not None and self.source_path is not None:
            message = "literal relocatable instruction cannot require source"
            raise RelocationError(message)


@dataclass(frozen=True, slots=True)
class RelocatableAuthoringPlan:
    """Non-distributable placement plan derived from an exact baseline."""

    instructions: tuple[RelocatableInstruction, ...]


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _range_locator(source: bytes, segment: SourceSlice) -> RangeLocator:
    end = segment.offset + segment.length
    if end > len(source):
        message = "exact source slice exceeds authoring source file"
        raise RelocationError(message)
    data = source[segment.offset : end]
    window_bytes = min(_BOUNDARY_BYTES, len(data))
    start_digest = _sha256(data[:window_bytes])
    end_digest = None
    if len(data) > window_bytes:
        end_digest = _sha256(data[-window_bytes:])
    return RangeLocator(
        source_length=len(data),
        window_bytes=window_bytes,
        start_digest=start_digest,
        end_digest=end_digest,
    )


def _relocatable_segment(
    source: bytes, segment: ExactSegment
) -> RelocatableSegment:
    if isinstance(segment, OracleLiteral):
        return segment
    return RelocatableSourceRange(_range_locator(source, segment))


def _instruction(
    source_root: Path,
    exact_instruction: ExactInstruction,
) -> RelocatableInstruction:
    if exact_instruction.kind is ExactInstructionKind.COPY_SOURCE:
        return RelocatableInstruction(
            output_path=exact_instruction.output_path,
            source_path=exact_instruction.source_path,
            copy_candidate_file=True,
        )
    if exact_instruction.kind is ExactInstructionKind.LITERAL_ORACLE:
        if exact_instruction.literal is None:
            message = "exact literal instruction lost authoring bytes"
            raise RelocationError(message)
        return RelocatableInstruction(
            output_path=exact_instruction.output_path,
            source_path=None,
            copy_candidate_file=False,
            literal=exact_instruction.literal,
        )
    if exact_instruction.source_path is None:
        message = "exact patch instruction lost source path"
        raise RelocationError(message)
    source_path = _safe_path(source_root, exact_instruction.source_path)
    source = source_path.read_bytes()
    return RelocatableInstruction(
        output_path=exact_instruction.output_path,
        source_path=exact_instruction.source_path,
        copy_candidate_file=False,
        segments=tuple(
            _relocatable_segment(source, segment)
            for segment in exact_instruction.segments
        ),
    )


def build_relocatable_plan(
    source_root: Path,
    exact_plan: ExactAuthoringPlan,
) -> RelocatableAuthoringPlan:
    """Replace exact source offsets with deterministic hash-only range locators.

    Returns:
        Non-distributable compatible-placement authoring plan.

    """
    return RelocatableAuthoringPlan(
        instructions=tuple(
            _instruction(source_root, instruction)
            for instruction in exact_plan.instructions
        )
    )


def _validate_relative_path(relative_path: str) -> str:
    candidate = PurePosixPath(relative_path)
    unsafe = (
        not relative_path
        or _BACKSLASH in relative_path
        or relative_path == _DOT
        or candidate.is_absolute()
        or _PARENT in candidate.parts
        or candidate.as_posix() != relative_path
    )
    if unsafe:
        message = f"unsafe relocatable tree path: {relative_path!r}"
        raise RelocationError(message)
    return relative_path


def _safe_path(root: Path, relative_path: str) -> Path:
    normalized = _validate_relative_path(relative_path)
    path = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        _ = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        message = f"relocatable path escapes tree root: {relative_path!r}"
        raise RelocationError(message) from exc
    return path


def _window_index(
    data: bytes, window_bytes: int
) -> dict[bytes, tuple[int, ...]]:
    if len(data) < window_bytes:
        return {}
    mutable: dict[bytes, list[int]] = {}
    last = len(data) - window_bytes
    for offset in range(last + _ONE):
        digest = _sha256(data[offset : offset + window_bytes])
        mutable.setdefault(digest, []).append(offset)
    return {digest: tuple(offsets) for digest, offsets in mutable.items()}


def _unique_offset(
    index: dict[bytes, tuple[int, ...]],
    digest: bytes,
    label: str,
) -> int:
    offsets = index.get(digest, ())
    if len(offsets) != _ONE:
        message = f"relocatable {label} boundary is missing or ambiguous"
        raise RelocationError(message)
    return offsets[0]


def _locate_range(candidate: bytes, locator: RangeLocator) -> tuple[int, int]:
    index = _window_index(candidate, locator.window_bytes)
    start = _unique_offset(index, locator.start_digest, "start")
    if locator.end_digest is None:
        return start, start + locator.source_length
    end_start = _unique_offset(index, locator.end_digest, "end")
    end = end_start + locator.window_bytes
    if end <= start or end - start < locator.source_length:
        message = "relocatable source boundaries are reversed or contracted"
        raise RelocationError(message)
    return start, end


def _patch_bytes(
    candidate: bytes,
    segments: tuple[RelocatableSegment, ...],
) -> bytes:
    parts: list[bytes] = []
    previous_end = _ZERO
    for segment in segments:
        if isinstance(segment, OracleLiteral):
            parts.append(segment.data)
            continue
        start, end = _locate_range(candidate, segment.locator)
        if start < previous_end:
            message = "relocatable source ranges overlap or reorder"
            raise RelocationError(message)
        parts.append(candidate[start:end])
        previous_end = end
    return b"".join(parts)


def _instruction_bytes(
    candidate_root: Path,
    instruction: RelocatableInstruction,
) -> bytes:
    if instruction.literal is not None:
        return instruction.literal
    if instruction.source_path is None:
        message = "relocatable instruction lost source path"
        raise RelocationError(message)
    candidate = _safe_path(candidate_root, instruction.source_path).read_bytes()
    if instruction.copy_candidate_file:
        return candidate
    return _patch_bytes(candidate, instruction.segments)


def _prepare_staging(output_root: Path) -> Path:
    if output_root.exists():
        message = f"output root already exists: {output_root}"
        raise RelocationError(message)
    staging = output_root.with_name(f".{output_root.name}{_STAGING_SUFFIX}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    return staging


def materialize_relocatable_plan(
    candidate_root: Path,
    plan: RelocatableAuthoringPlan,
    output_root: Path,
) -> None:
    """Materialize a relocatable authoring plan transactionally.

    This function intentionally performs placement only. Admission, protected
    literals, behavior routing, and output postconditions must wrap it before it
    can become a public compatible transform.
    """
    staging = _prepare_staging(output_root)
    try:
        for instruction in plan.instructions:
            data = _instruction_bytes(candidate_root, instruction)
            output = _safe_path(staging, instruction.output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            _ = output.write_bytes(data)
        _ = staging.replace(output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
