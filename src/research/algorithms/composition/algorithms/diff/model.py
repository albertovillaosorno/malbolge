# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
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
#   - Deterministic data model for authoring tree transformations.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Deterministic data model for authoring tree transformations."""

from __future__ import annotations

from builtins import any as _native_any
from builtins import bytes as _native_bytes
from builtins import enumerate as _native_enumerate
from builtins import int as _native_int
from builtins import isinstance as _native_isinstance
from builtins import len as _native_len
from builtins import object as _native_object
from builtins import range as _native_range
from builtins import set as _native_set
from builtins import sorted as _native_sorted
from builtins import str as _native_str
from builtins import sum as _native_sum
from builtins import tuple as _native_tuple
from builtins import type as _native_type
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256 as _native_sha256
from types import MemberDescriptorType
from typing import cast

_ZERO = 0
_NATIVE_OBJECT_SETATTR = _native_object.__setattr__
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")
_BACKSLASH = "\\"
_NUL = "\x00"
_UNSAFE_COMPONENTS = frozenset(("", ".", ".."))
# Freeze Windows path-policy literals instead of calling ntpath helpers that
# resolve late, mutable os.fspath, splitroot, and builtin hooks.
_WINDOWS_RESERVED_CHARACTERS = frozenset(
    '*?"<>/\\:|' + "".join(chr(code) for code in range(32))
)
_WINDOWS_DEVICE_NAMES = frozenset(
    (
        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
        "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
    )
    + tuple(
        f"{prefix}{index}"
        for prefix in ("COM", "LPT")
        for index in range(1, 10)
    )
)


class TreeModelError(ValueError):
    """Raised when a tree or transformation violates the model contract."""


def _validate_sha256_hex(value: object, context: str) -> None:
    if (
        _native_type(value) is not _native_str
        or _native_len(value) != _SHA256_HEX_LENGTH
    ):
        message = f"{context} must be 64 lowercase hex digits"
        raise TreeModelError(message)
    if _native_any(char not in _HEX_DIGITS for char in value):
        message = f"{context} must be 64 lowercase hex digits"
        raise TreeModelError(message)


def reserved_windows_component(component: str) -> bool:
    """Check one component against stable Windows name rules."""
    if component[-1:] in (".", " ") and component not in (".", ".."):
        return True
    if _native_any(char in _WINDOWS_RESERVED_CHARACTERS for char in component):
        return True
    stem = component.partition(".")[0].rstrip(" ").upper()
    return stem in _WINDOWS_DEVICE_NAMES


def _require_canonical_relative_path(value: object, context: str) -> None:
    if _native_type(value) is not _native_str or not value:
        message = f"{context} must be a canonical relative path"
        raise TreeModelError(message)
    # Security-critical path labels must not consult mutable pathlib methods.
    unsafe = (
        _BACKSLASH in value
        or _NUL in value
        or _native_any(
            reserved_windows_component(component)
            for component in value.split("/")
        )
        or _native_any(part in _UNSAFE_COMPONENTS for part in value.split("/"))
    )
    if unsafe:
        message = f"{context} must be a canonical relative path"
        raise TreeModelError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeError as error:
        message = f"{context} must be a canonical relative path"
        raise TreeModelError(message) from error


@dataclass(frozen=True, slots=True, order=True, init=False)
class FileRecord:
    """One regular file in a deterministic tree snapshot."""

    path: str
    sha256: str
    size: int

    def __init__(
        self,
        path: str,
        sha256: str,
        size: int,
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "path", path)
        _NATIVE_OBJECT_SETATTR(self, "sha256", sha256)
        _NATIVE_OBJECT_SETATTR(self, "size", size)
        _FILE_RECORD_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact immutable snapshot metadata types.

        Raises:
            TreeModelError: Snapshot metadata uses an invalid runtime value.

        """
        path, digest, size = _file_fields(self)
        _require_canonical_relative_path(path, "file record path")
        _validate_sha256_hex(digest, "file record sha256")
        if _native_type(size) is not _native_int or size < _ZERO:
            message = "file record size must be a non-negative integer"
            raise TreeModelError(message)


_FILE_RECORD_VALIDATOR = cast(
    "Callable[[FileRecord], None]", FileRecord.__dict__["__post_init__"]
)


# Exact file metadata must retain its original stored values after consumers
# replace class properties or __getattribute__ during source evaluation.
_FILE_PATH_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["path"])
_FILE_DIGEST_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["sha256"])
_FILE_SIZE_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["size"])


def _file_fields(record: FileRecord) -> tuple[str, str, int]:
    return (
        _FILE_PATH_SLOT.__get__(record, FileRecord),
        _FILE_DIGEST_SLOT.__get__(record, FileRecord),
        _FILE_SIZE_SLOT.__get__(record, FileRecord),
    )


def _has_file_ancestor(path: str, file_paths: set[str]) -> bool:
    components = path.split("/")
    return _native_any(
        "/".join(components[:index]) in file_paths
        for index in _native_range(1, _native_len(components))
    )


@dataclass(frozen=True, slots=True, init=False)
class TreeSnapshot:
    """Sorted regular-file snapshot used for deterministic verification."""

    files: tuple[FileRecord, ...]

    def __init__(
        self,
        files: tuple[FileRecord, ...],
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "files", files)
        _TREE_SNAPSHOT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require immutable exact records in deterministic path order.

        Raises:
            TreeModelError: File records are mutable, foreign, or unordered.

        """
        files = _snapshot_files(self)
        if _native_type(files) is not _native_tuple:
            message = (
                "tree snapshot files must use the exact immutable tuple type"
            )
            raise TreeModelError(message)
        if _native_any(
            _native_type(item) is not FileRecord for item in files
        ):
            message = "tree snapshot contains a foreign file record"
            raise TreeModelError(message)
        paths = _native_tuple(_file_fields(item)[0] for item in files)
        if paths != _native_tuple(_native_sorted(_native_set(paths))):
            message = "tree snapshot paths must be unique and sorted"
            raise TreeModelError(message)
        file_paths = _native_set(paths)
        if _native_any(_has_file_ancestor(path, file_paths) for path in paths):
            message = "tree snapshot has an ancestor/descendant file overlap"
            raise TreeModelError(message)


_TREE_SNAPSHOT_VALIDATOR = cast(
    "Callable[[TreeSnapshot], None]", TreeSnapshot.__dict__["__post_init__"]
)


_SNAPSHOT_FILES_SLOT = cast(
    "MemberDescriptorType", TreeSnapshot.__dict__["files"]
)


def _snapshot_files(snapshot: TreeSnapshot) -> tuple[FileRecord, ...]:
    return _SNAPSHOT_FILES_SLOT.__get__(snapshot, TreeSnapshot)


class ExactInstructionKind(StrEnum):
    """How one exact-baseline output file obtains its bytes."""

    COPY_SOURCE = "copy-source"
    PATCH_SOURCE = "patch-source"
    LITERAL_ORACLE = "literal-oracle"


@dataclass(frozen=True, slots=True, init=False)
class SourceSlice:
    """A byte range reused from an admitted source file."""

    offset: int
    length: int

    def __init__(
        self,
        offset: int,
        length: int,
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "offset", offset)
        _NATIVE_OBJECT_SETATTR(self, "length", length)
        _SOURCE_SLICE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject nonsensical source ranges.

        Raises:
            TreeModelError: The range is negative or empty.

        """
        offset, length = _source_slice_fields(self)
        if (
            _native_type(offset) is not _native_int
            or _native_type(length) is not _native_int
        ):
            message = "source slice coordinates must use exact integers"
            raise TreeModelError(message)
        if offset < _ZERO or length <= _ZERO:
            message = "source slices require a non-negative offset and positive length"
            raise TreeModelError(message)


_SOURCE_SLICE_VALIDATOR = cast(
    "Callable[[SourceSlice], None]", SourceSlice.__dict__["__post_init__"]
)


_SOURCE_SLICE_OFFSET_SLOT = cast(
    "MemberDescriptorType", SourceSlice.__dict__["offset"]
)
_SOURCE_SLICE_LENGTH_SLOT = cast(
    "MemberDescriptorType", SourceSlice.__dict__["length"]
)


def _source_slice_fields(segment: SourceSlice) -> tuple[int, int]:
    return (
        _SOURCE_SLICE_OFFSET_SLOT.__get__(segment, SourceSlice),
        _SOURCE_SLICE_LENGTH_SLOT.__get__(segment, SourceSlice),
    )


@dataclass(frozen=True, slots=True, init=False)
class OracleLiteral:
    """Target-only bytes retained only inside the local authoring plan."""

    data: bytes

    def __init__(
        self,
        data: bytes,
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "data", data)
        _ORACLE_LITERAL_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact immutable target bytes.

        Raises:
            TreeModelError: Target literal is not exact bytes.

        """
        if _native_type(_oracle_literal_data(self)) is not _native_bytes:
            message = "oracle literal must use exact bytes"
            raise TreeModelError(message)


_ORACLE_LITERAL_VALIDATOR = cast(
    "Callable[[OracleLiteral], None]", OracleLiteral.__dict__["__post_init__"]
)


_ORACLE_LITERAL_DATA_SLOT = cast(
    "MemberDescriptorType", OracleLiteral.__dict__["data"]
)


def _oracle_literal_data(literal: OracleLiteral) -> bytes:
    return _ORACLE_LITERAL_DATA_SLOT.__get__(literal, OracleLiteral)


ExactSegment = SourceSlice | OracleLiteral


def _validate_exact_segments(value: object) -> None:
    if _native_type(value) is not _native_tuple:
        message = "exact instruction segments must use an immutable tuple"
        raise TreeModelError(message)
    segments = cast("tuple[object, ...]", value)
    allowed_types = {SourceSlice, OracleLiteral}
    foreign = (
        _native_type(segment) not in allowed_types for segment in segments
    )
    if _native_any(foreign):
        message = "exact instruction contains a foreign segment record"
        raise TreeModelError(message)


def _validate_exact_instruction_metadata(instruction: ExactInstruction) -> None:
    path, kind, digest, source, literal, segments = _instruction_fields(
        instruction
    )
    _require_canonical_relative_path(path, "exact instruction output path")
    if _native_type(kind) is not ExactInstructionKind:
        message = "exact instruction kind must use the exact enum type"
        raise TreeModelError(message)
    _validate_sha256_hex(digest, "exact instruction sha256")
    if source is not None:
        _require_canonical_relative_path(
            source, "exact instruction source path"
        )
    if literal is not None and _native_type(literal) is not _native_bytes:
        message = "exact instruction literal must use exact bytes or None"
        raise TreeModelError(message)
    _validate_exact_segments(segments)


@dataclass(frozen=True, slots=True, init=False)
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

    def __init__(
        self,
        output_path: str,
        kind: ExactInstructionKind,
        expected_sha256: str,
        source_path: str | None = None,
        literal: bytes | None = None,
        segments: tuple[ExactSegment, ...] = (),
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "output_path", output_path)
        _NATIVE_OBJECT_SETATTR(self, "kind", kind)
        _NATIVE_OBJECT_SETATTR(self, "expected_sha256", expected_sha256)
        _NATIVE_OBJECT_SETATTR(self, "source_path", source_path)
        _NATIVE_OBJECT_SETATTR(self, "literal", literal)
        _NATIVE_OBJECT_SETATTR(self, "segments", segments)
        _EXACT_INSTRUCTION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject ambiguous or incomplete instruction payloads.

        Raises:
            TreeModelError: The instruction payload does not match its kind.

        """
        _validate_exact_instruction_metadata(self)
        kind = _instruction_fields(self)[1]
        if kind is ExactInstructionKind.COPY_SOURCE:
            _EXACT_COPY_VALIDATOR(self)
            return
        if kind is ExactInstructionKind.PATCH_SOURCE:
            _EXACT_PATCH_VALIDATOR(self)
            return
        if kind is ExactInstructionKind.LITERAL_ORACLE:
            _EXACT_LITERAL_VALIDATOR(self)
            return
        message = f"unsupported exact instruction kind: {kind!r}"
        raise TreeModelError(message)

    def _validate_copy(self) -> None:
        _, _, _, source, literal, segments = _instruction_fields(self)
        if source is None or literal is not None or segments:
            message = "copy-source requires only source_path"
            raise TreeModelError(message)

    def _validate_patch(self) -> None:
        _, _, _, source, literal, segments = _instruction_fields(self)
        if source is None or literal is not None or not segments:
            message = "patch-source requires source_path and segments"
            raise TreeModelError(message)

    def _validate_literal(self) -> None:
        _, _, _, source, literal, segments = _instruction_fields(self)
        if literal is None or source is not None or segments:
            message = "literal-oracle requires only literal bytes"
            raise TreeModelError(message)


_EXACT_INSTRUCTION_VALIDATOR = cast(
    "Callable[[ExactInstruction], None]",
    ExactInstruction.__dict__["__post_init__"],
)

_EXACT_COPY_VALIDATOR = cast(
    "Callable[[ExactInstruction], None]",
    ExactInstruction.__dict__["_validate_copy"],
)
_EXACT_PATCH_VALIDATOR = cast(
    "Callable[[ExactInstruction], None]",
    ExactInstruction.__dict__["_validate_patch"],
)
_EXACT_LITERAL_VALIDATOR = cast(
    "Callable[[ExactInstruction], None]",
    ExactInstruction.__dict__["_validate_literal"],
)
_INSTRUCTION_OUTPUT_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["output_path"]
)
_INSTRUCTION_KIND_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["kind"]
)
_INSTRUCTION_SHA256_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["expected_sha256"]
)
_INSTRUCTION_SOURCE_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["source_path"]
)
_INSTRUCTION_LITERAL_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["literal"]
)
_INSTRUCTION_SEGMENTS_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["segments"]
)


def _instruction_fields(instruction: ExactInstruction) -> tuple[
    str, ExactInstructionKind, str, str | None, bytes | None,
    tuple[ExactSegment, ...]
]:
    return (
        _INSTRUCTION_OUTPUT_SLOT.__get__(instruction, ExactInstruction),
        _INSTRUCTION_KIND_SLOT.__get__(instruction, ExactInstruction),
        _INSTRUCTION_SHA256_SLOT.__get__(instruction, ExactInstruction),
        _INSTRUCTION_SOURCE_SLOT.__get__(instruction, ExactInstruction),
        _INSTRUCTION_LITERAL_SLOT.__get__(instruction, ExactInstruction),
        _INSTRUCTION_SEGMENTS_SLOT.__get__(instruction, ExactInstruction),
    )


@dataclass(frozen=True, slots=True, init=False)
class ExactAuthoringPlan:
    """Local exact plan produced from a source tree and oracle tree."""

    source: TreeSnapshot
    target: TreeSnapshot
    instructions: tuple[ExactInstruction, ...]
    passthrough_roots: tuple[str, ...] = ()

    def __init__(
        self,
        source: TreeSnapshot,
        target: TreeSnapshot,
        instructions: tuple[ExactInstruction, ...],
        passthrough_roots: tuple[str, ...] = (),
    ) -> None:
        """Admit record fields through the captured original validator."""
        _NATIVE_OBJECT_SETATTR(self, "source", source)
        _NATIVE_OBJECT_SETATTR(self, "target", target)
        _NATIVE_OBJECT_SETATTR(self, "instructions", instructions)
        _NATIVE_OBJECT_SETATTR(self, "passthrough_roots", passthrough_roots)
        _EXACT_AUTHORING_PLAN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact snapshots and immutable plan metadata.

        Raises:
            TreeModelError: Plan metadata is mutable, foreign, or malformed.

        """
        source, target, instructions, roots = _plan_fields(self)
        if (
            _native_type(source) is not TreeSnapshot
            or _native_type(target) is not TreeSnapshot
        ):
            message = "exact plan snapshots must use exact TreeSnapshot records"
            raise TreeModelError(message)
        if _native_type(instructions) is not _native_tuple or _native_any(
            _native_type(item) is not ExactInstruction
            for item in instructions
        ):
            message = "exact plan instructions must be exact immutable records"
            raise TreeModelError(message)
        paths = _native_tuple(
            _instruction_fields(item)[0] for item in instructions
        )
        if _native_len(paths) != _native_len(_native_set(paths)):
            message = "exact plan requires unique output paths"
            raise TreeModelError(message)
        authored_outputs = _native_tuple(
            (_instruction_fields(item)[0], _instruction_fields(item)[2])
            for item in instructions
        )
        target_outputs = _native_tuple(
            (_file_fields(item)[0], _file_fields(item)[1])
            for item in _snapshot_files(target)
        )
        if authored_outputs != target_outputs:
            message = "exact plan instructions must match the target snapshot"
            raise TreeModelError(message)
        _require_passthrough_roots(roots)
        _require_static_target_outside_passthrough(target, roots)
        _require_static_source_references(self)


_EXACT_AUTHORING_PLAN_VALIDATOR = cast(
    "Callable[[ExactAuthoringPlan], None]",
    ExactAuthoringPlan.__dict__["__post_init__"],
)

_PLAN_SOURCE_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["source"]
)
_PLAN_TARGET_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["target"]
)
_PLAN_INSTRUCTIONS_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["instructions"]
)
_PLAN_ROOTS_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["passthrough_roots"]
)


def _plan_fields(plan: ExactAuthoringPlan) -> tuple[
    TreeSnapshot, TreeSnapshot, tuple[ExactInstruction, ...], tuple[str, ...]
]:
    return (
        _PLAN_SOURCE_SLOT.__get__(plan, ExactAuthoringPlan),
        _PLAN_TARGET_SLOT.__get__(plan, ExactAuthoringPlan),
        _PLAN_INSTRUCTIONS_SLOT.__get__(plan, ExactAuthoringPlan),
        _PLAN_ROOTS_SLOT.__get__(plan, ExactAuthoringPlan),
    )


def _require_static_source_entry(
    path: str,
    source_by_path: dict[str, FileRecord],
    passthrough_roots: tuple[str, ...],
) -> FileRecord | None:
    """Find a static source file, or permit an explicit dynamic path.

    Returns:
        The admitted source record, or None for dynamic passthrough.

    Raises:
        TreeModelError: The static reference is absent from the snapshot.

    """
    source = source_by_path.get(path)
    if source is not None:
        return source
    dynamic = (path == r or path.startswith(r + "/") for r in passthrough_roots)
    if _native_any(dynamic):
        return None
    message = f"exact plan source path is absent from snapshot: {path}"
    raise TreeModelError(message)


def _require_static_instruction_consistency(
    instruction: ExactInstruction,
    source: FileRecord,
    target: FileRecord,
) -> None:
    """Require copy and patch references to fit their static snapshots.

    Raises:
        TreeModelError: A copy disagrees or a patch exceeds source size.

    """
    _, kind, digest, _, _, segments = _instruction_fields(instruction)
    source_path, source_digest, source_size = _file_fields(source)
    _, _, target_size = _file_fields(target)
    if kind is ExactInstructionKind.COPY_SOURCE:
        if digest != source_digest:
            message = f"exact plan copy-source digest differs: {source_path}"
            raise TreeModelError(message)
        if target_size != source_size:
            message = f"exact plan copy-source size differs: {source_path}"
            raise TreeModelError(message)
    if kind is ExactInstructionKind.PATCH_SOURCE and _native_any(
        _source_slice_fields(segment)[0] + _source_slice_fields(segment)[1]
        > source_size
        for segment in segments
        if _native_type(segment) is SourceSlice
    ):
        message = (
            f"exact plan source slice exceeds snapshot size: {source_path}"
        )
        raise TreeModelError(message)


def _exact_segment_length(segment: ExactSegment) -> int:
    """Count bytes contributed by a source slice or oracle literal.

    Returns:
        Number of output bytes from this exact segment.

    """
    if _native_isinstance(segment, SourceSlice):
        return _source_slice_fields(segment)[1]
    return _native_len(_oracle_literal_data(segment))


def _require_literal_output_consistency(
    literal: bytes | None, target: FileRecord
) -> None:
    """Validate complete oracle literals against static output metadata.

    Raises:
        TreeModelError: Literal length or SHA-256 contradicts its target.

    """
    if literal is None:
        return
    path, digest, size = _file_fields(target)
    if _native_len(literal) != size:
        message = f"exact plan literal-oracle size differs: {path}"
        raise TreeModelError(message)
    if _native_sha256(literal).hexdigest() != digest:
        message = f"exact plan literal-oracle digest differs: {path}"
        raise TreeModelError(message)


def _require_exact_output_consistency(
    instruction: ExactInstruction,
    target: FileRecord,
) -> None:
    """Validate target sizes and hashes that need no source bytes.

    Raises:
        TreeModelError: Exact output metadata contradicts literal content.

    """
    _, kind, _, _, literal, segments = _instruction_fields(instruction)
    target_path, _, target_size = _file_fields(target)
    if kind is ExactInstructionKind.PATCH_SOURCE:
        reconstructed_size = _native_sum(
            _exact_segment_length(segment) for segment in segments
        )
        if reconstructed_size != target_size:
            message = f"exact plan patch-source size differs: {target_path}"
            raise TreeModelError(message)
    _require_literal_output_consistency(literal, target)


def _require_static_source_references(plan: ExactAuthoringPlan) -> None:
    """Reject impossible static copy and byte-slice instructions."""
    source, target_tree, instructions, roots = _plan_fields(plan)
    source_by_path = {
        _file_fields(record)[0]: record for record in _snapshot_files(source)
    }
    target_by_path = {
        _file_fields(record)[0]: record
        for record in _snapshot_files(target_tree)
    }
    for instruction in instructions:
        target = target_by_path[_instruction_fields(instruction)[0]]
        _require_exact_output_consistency(instruction, target)
        path = _instruction_fields(instruction)[3]
        if path is None:
            continue
        source = _require_static_source_entry(
            path, source_by_path, roots
        )
        if source is not None:
            _require_static_instruction_consistency(instruction, source, target)


def _require_static_target_outside_passthrough(
    target: TreeSnapshot, roots: tuple[str, ...]
) -> None:
    if _native_any(
        _file_fields(record)[0] == root
        or _file_fields(record)[0].startswith(root + "/")
        for record in _snapshot_files(target)
        for root in roots
    ):
        message = "exact plan static target conflicts with passthrough roots"
        raise TreeModelError(message)


def _require_passthrough_roots(roots: object) -> None:
    if _native_type(roots) is not _native_tuple:
        message = "exact plan passthrough roots must use an immutable tuple"
        raise TreeModelError(message)
    for root in cast("tuple[object, ...]", roots):
        _require_canonical_relative_path(root, "exact plan passthrough root")
    _validate_passthrough_topology(cast("tuple[str, ...]", roots))


def _validate_passthrough_topology(ordered: tuple[str, ...]) -> None:
    if ordered != _native_tuple(_native_sorted(_native_set(ordered))):
        message = "exact plan passthrough roots must be unique and sorted"
        raise TreeModelError(message)
    for index, root in _native_enumerate(ordered):
        prefix = root + "/"
        successors = ordered[index + 1 :]
        if _native_any(other.startswith(prefix) for other in successors):
            message = "exact plan passthrough roots must not overlap"
            raise TreeModelError(message)
