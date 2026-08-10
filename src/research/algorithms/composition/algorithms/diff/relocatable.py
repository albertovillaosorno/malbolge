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
from pathlib import Path
from pathlib import PurePosixPath
import shutil
from typing import TYPE_CHECKING

from algorithms.diff.model import ExactAuthoringPlan
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral
from algorithms.diff.publication import publish_directory_no_replace

if TYPE_CHECKING:
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
        if type(self.source_length) is not int or self.source_length <= _ZERO:
            message = "relocatable source length must be a positive integer"
            raise RelocationError(message)
        if (
            type(self.window_bytes) is not int
            or self.window_bytes <= _ZERO
            or self.window_bytes > self.source_length
        ):
            message = "relocatable boundary width must be a valid integer"
            raise RelocationError(message)
        if (
            type(self.start_digest) is not bytes
            or len(self.start_digest) != hashlib.sha256().digest_size
        ):
            message = "relocatable start digest must be exact SHA-256 bytes"
            raise RelocationError(message)
        if self.end_digest is not None and (
            type(self.end_digest) is not bytes
            or len(self.end_digest) != hashlib.sha256().digest_size
        ):
            message = "relocatable end digest must be exact SHA-256 bytes"
            raise RelocationError(message)


@dataclass(frozen=True, slots=True)
class RelocatableSourceRange:
    """Source-backed output segment located by content rather than offset."""

    locator: RangeLocator

    def __post_init__(self) -> None:
        """Require one exact admitted range locator.

        Raises:
            RelocationError: Locator metadata is foreign.

        """
        if type(self.locator) is not RangeLocator:
            message = "relocatable source range must use the exact locator type"
            raise RelocationError(message)


RelocatableSegment = RelocatableSourceRange | OracleLiteral


def _validate_relocatable_paths(instruction: RelocatableInstruction) -> None:
    _ = _validate_relative_path(instruction.output_path)
    if instruction.source_path is not None:
        _ = _validate_relative_path(instruction.source_path)


def _validate_relocatable_payload(instruction: RelocatableInstruction) -> None:
    if type(instruction.copy_candidate_file) is not bool:
        message = "relocatable copy flag must use the exact boolean type"
        raise RelocationError(message)
    if (
        instruction.literal is not None
        and type(instruction.literal) is not bytes
    ):
        message = "relocatable literal must use exact bytes or None"
        raise RelocationError(message)
    if type(instruction.segments) is not tuple:
        message = "relocatable segments must use the immutable tuple type"
        raise RelocationError(message)
    if any(
        type(segment) not in {RelocatableSourceRange, OracleLiteral}
        for segment in instruction.segments
    ):
        message = "relocatable instruction contains a foreign segment"
        raise RelocationError(message)


def _validate_relocatable_shape(instruction: RelocatableInstruction) -> None:
    _validate_relocatable_paths(instruction)
    _validate_relocatable_payload(instruction)


def _validate_relocatable_form(instruction: RelocatableInstruction) -> None:
    forms = sum((
        instruction.copy_candidate_file,
        instruction.literal is not None,
        bool(instruction.segments),
    ))
    if forms != _ONE:
        message = "relocatable instruction requires exactly one payload form"
        raise RelocationError(message)
    if instruction.copy_candidate_file and instruction.source_path is None:
        message = "candidate-file copy requires a source path"
        raise RelocationError(message)
    if instruction.segments and instruction.source_path is None:
        message = "relocatable segments require a source path"
        raise RelocationError(message)
    if instruction.literal is not None and instruction.source_path is not None:
        message = "literal relocatable instruction cannot require source"
        raise RelocationError(message)


@dataclass(frozen=True, slots=True)
class RelocatableInstruction:
    """One compatible-placement output instruction."""

    output_path: str
    source_path: str | None
    copy_candidate_file: bool
    literal: bytes | None = None
    segments: tuple[RelocatableSegment, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous instruction forms."""
        _validate_relocatable_shape(self)
        _validate_relocatable_form(self)


@dataclass(frozen=True, slots=True)
class RelocatableAuthoringPlan:
    """Non-distributable placement plan derived from an exact baseline."""

    instructions: tuple[RelocatableInstruction, ...]

    def __post_init__(self) -> None:
        """Require immutable exact relocation instructions.

        Raises:
            RelocationError: Plan records are mutable or foreign.

        """
        if type(self.instructions) is not tuple:
            message = (
                "relocatable plan instructions must use an immutable tuple"
            )
            raise RelocationError(message)
        if any(
            type(instruction) is not RelocatableInstruction
            for instruction in self.instructions
        ):
            message = "relocatable plan contains a foreign instruction record"
            raise RelocationError(message)


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
    source = _read_relocatable_bytes(source_path, "relocatable source")
    return RelocatableInstruction(
        output_path=exact_instruction.output_path,
        source_path=exact_instruction.source_path,
        copy_candidate_file=False,
        segments=tuple(
            _relocatable_segment(source, segment)
            for segment in exact_instruction.segments
        ),
    )


def _path_present(path: Path, context: str) -> bool:
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        message = f"{context} status failed: {path}: {error}"
        raise RelocationError(message) from error
    return True


def _read_relocatable_bytes(path: Path, context: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        message = f"{context} read failed: {path}: {error}"
        raise RelocationError(message) from error


def _write_relocatable_bytes(path: Path, data: bytes, context: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(data)
    except OSError as error:
        message = f"{context} write failed: {path}: {error}"
        raise RelocationError(message) from error


def _make_relocatable_directory(
    path: Path,
    context: str,
    *,
    parents: bool,
    exist_ok: bool,
) -> None:
    try:
        path.mkdir(parents=parents, exist_ok=exist_ok)
    except OSError as error:
        message = f"{context} creation failed: {path}: {error}"
        raise RelocationError(message) from error


def _validate_path(value: object, context: str) -> None:
    if not isinstance(value, Path):
        message = f"{context} must use a pathlib Path value"
        raise RelocationError(message)


def build_relocatable_plan(
    source_root: Path,
    exact_plan: ExactAuthoringPlan,
) -> RelocatableAuthoringPlan:
    """Replace exact source offsets with deterministic hash-only range locators.

    Returns:
        Non-distributable compatible-placement authoring plan.

    Raises:
        RelocationError: Source root or exact plan metadata is invalid.

    """
    _validate_path(source_root, "relocatable source root")
    if type(exact_plan) is not ExactAuthoringPlan:
        message = (
            "relocatable source plan must use the exact authoring-plan type"
        )
        raise RelocationError(message)
    return RelocatableAuthoringPlan(
        instructions=tuple(
            _instruction(source_root, instruction)
            for instruction in exact_plan.instructions
        )
    )


def _validate_relative_path(relative_path: object) -> str:
    if type(relative_path) is not str:
        message = "relocatable path must use the exact string type"
        raise RelocationError(message)
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
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except OSError as error:
        message = (
            f"relocatable path resolution failed: {relative_path!r}: {error}"
        )
        raise RelocationError(message) from error
    try:
        _ = resolved_path.relative_to(resolved_root)
    except ValueError as error:
        message = f"relocatable path escapes tree root: {relative_path!r}"
        raise RelocationError(message) from error
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
    candidate_path = _safe_path(candidate_root, instruction.source_path)
    candidate = _read_relocatable_bytes(candidate_path, "relocatable candidate")
    if instruction.copy_candidate_file:
        return candidate
    return _patch_bytes(candidate, instruction.segments)


def _prepare_staging(output_root: Path) -> Path:
    if _path_present(output_root, "relocatable output root"):
        message = f"output root already exists: {output_root}"
        raise RelocationError(message)
    staging = output_root.with_name(f".{output_root.name}{_STAGING_SUFFIX}")
    if _path_present(staging, "relocatable staging root"):
        message = f"relocatable staging root already exists: {staging}"
        raise RelocationError(message)
    _make_relocatable_directory(
        staging,
        "relocatable staging root",
        parents=True,
        exist_ok=False,
    )
    return staging


def _cleanup_relocatable_staging(path: Path) -> str | None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        return str(error)
    return None


def _raise_relocatable_cleanup_failure(
    error: Exception, cleanup_error: str
) -> None:
    message = f"{error}; relocatable staging cleanup failed: {cleanup_error}"
    raise RelocationError(message) from error


def _publish_relocatable_output(staging: Path, destination: Path) -> None:
    try:
        publish_directory_no_replace(staging, destination)
    except OSError as error:
        message = f"relocatable output publication failed: {error}"
        raise RelocationError(message) from error


def materialize_relocatable_plan(
    candidate_root: Path,
    plan: RelocatableAuthoringPlan,
    output_root: Path,
) -> None:
    """Materialize a relocatable authoring plan transactionally.

    This function intentionally performs placement only. Admission, protected
    literals, behavior routing, and output postconditions must wrap it before it
    can become a public compatible transform.

    Raises:
        RelocationError: Roots, plan metadata, or placement is invalid.

    """
    _validate_path(candidate_root, "relocatable candidate root")
    _validate_path(output_root, "relocatable output root")
    if type(plan) is not RelocatableAuthoringPlan:
        message = "relocatable materialization requires the exact plan type"
        raise RelocationError(message)
    staging = _prepare_staging(output_root)
    try:
        for instruction in plan.instructions:
            data = _instruction_bytes(candidate_root, instruction)
            output = _safe_path(staging, instruction.output_path)
            _write_relocatable_bytes(output, data, "relocatable output")
        _publish_relocatable_output(staging, output_root)
    except Exception as error:
        cleanup_error = _cleanup_relocatable_staging(staging)
        if cleanup_error is not None:
            _raise_relocatable_cleanup_failure(error, cleanup_error)
        raise
