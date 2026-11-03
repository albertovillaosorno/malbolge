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

import builtins
import hashlib
import io
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISLNK
from types import MemberDescriptorType
from typing import TYPE_CHECKING, cast

from algorithms.diff.exact import (
    ExactTreeError,
    read_exact_regular_file,
    snapshot_tree_excluding,
)
from algorithms.diff.model import (
    ExactAuthoringPlan,
    ExactInstruction,
    ExactInstructionKind,
    FileRecord,
    OracleLiteral,
    SourceSlice,
    TreeModelError,
    TreeSnapshot,
    reserved_windows_component,
)
from algorithms.diff.publication import publish_directory_no_replace

if TYPE_CHECKING:
    from algorithms.diff.model import ExactSegment

_ZERO = 0
_ONE = 1
_BOUNDARY_BYTES = 32
# A loaded domain must not redefine the relocation hash primitive.
_SHA256_FACTORY = hashlib.sha256
_SHA256_DIGEST_BYTES = _SHA256_FACTORY().digest_size
# Consumer modules cannot replace exact-record or byte-count admission.
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_BYTES = builtins.bytes
_NATIVE_STR = builtins.str
_NATIVE_LEN = builtins.len
_NATIVE_BOOL = builtins.bool
_NATIVE_TUPLE = builtins.tuple
# Keep output containment independent of post-load pathlib hook swaps.
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
_NATIVE_RESOLVE = _NATIVE_PATH_TYPE.resolve
_NATIVE_IS_RELATIVE_TO = _NATIVE_PATH_TYPE.is_relative_to
_NATIVE_RELATIVE_TO = _NATIVE_PATH_TYPE.relative_to
_NATIVE_IS_JUNCTION = _NATIVE_PATH_TYPE.is_junction
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_PARENT = cast("Callable[[Path], Path]", Path.parent.fget)
_NATIVE_PATH_NAME = cast("Callable[[Path], str]", Path.name.fget)
_NATIVE_PATH_WITH_NAME = Path.with_name
_NATIVE_IO_OPEN = io.open
_NATIVE_OS_MKDIR = os.mkdir
_NATIVE_FS_ENCODING = sys.getfilesystemencoding()
_NATIVE_FS_ERRORS = sys.getfilesystemencodeerrors()
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_IS_SYMLINK = S_ISLNK
# Owned staging deletion must ignore consumer changes to shutil hooks.
_NATIVE_RMTREE = shutil.rmtree
_NATIVE_ANY = builtins.any
_NATIVE_SET = builtins.set
_NATIVE_SUM = builtins.sum
_NATIVE_MIN = builtins.min
_NATIVE_RANGE = builtins.range
_NATIVE_OBJECT_NEW = object.__new__
_ORACLE_LITERAL_VALIDATOR = cast(
    "Callable[[OracleLiteral], None]", OracleLiteral.__dict__["__post_init__"]
)
# Exact-class plans may be allocated without the model constructor. Validate
# their original nested snapshots, instructions and target binding before I/O.
_EXACT_PLAN_VALIDATOR = cast(
    "Callable[[ExactAuthoringPlan], None]",
    ExactAuthoringPlan.__dict__["__post_init__"],
)


def _native_path_lstat(path: Path) -> os.stat_result:
    # Do not delegate to mutable pathlib or os status hooks after import.
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat
_STAGING_SUFFIX = ".relocatable-staging"
_NUL = "\x00"


class RelocationError(RuntimeError):
    """Raised when compatible source placement is unsafe or ambiguous."""


def _host_error_detail(error: BaseException) -> str:
    """Contain untrusted exception formatting within typed host failures."""
    if _NATIVE_TYPE(error) in (
        OSError,
        ValueError,
        RuntimeError,
        ExactTreeError,
        RelocationError,
    ):
        arguments = cast("tuple[object, ...]", error.args)
        if (
            _NATIVE_LEN(arguments) == 1
            and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR
        ):
            return arguments[0]
    return _NATIVE_TYPE(error).__name__


@dataclass(frozen=True, slots=True, init=False)
class RangeLocator:
    """Hash-only locator for one source range in a later candidate file."""

    source_length: int
    window_bytes: int
    start_digest: bytes
    end_digest: bytes | None = None

    def __init__(
        self,
        source_length: int,
        window_bytes: int,
        start_digest: bytes,
        end_digest: bytes | None = None,
    ) -> None:
        """Initialize slots and invoke the captured native validator."""
        _LOCATOR_LENGTH_SLOT.__set__(self, source_length)
        _LOCATOR_WIDTH_SLOT.__set__(self, window_bytes)
        _LOCATOR_START_SLOT.__set__(self, start_digest)
        _LOCATOR_END_SLOT.__set__(self, end_digest)
        _LOCATOR_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject malformed range locators.

        Raises:
            RelocationError: Locator widths or digests are invalid.

        """
        length, width, start_digest, end_digest = _locator_fields(self)
        if _NATIVE_TYPE(length) is not _NATIVE_INT or length <= _ZERO:
            message = "relocatable source length must be a positive integer"
            raise RelocationError(message)
        if (
            _NATIVE_TYPE(width) is not _NATIVE_INT
            or width <= _ZERO
            or width > length
        ):
            message = "relocatable boundary width must be a valid integer"
            raise RelocationError(message)
        if (
            _NATIVE_TYPE(start_digest) is not _NATIVE_BYTES
            or _NATIVE_LEN(start_digest) != _SHA256_DIGEST_BYTES
        ):
            message = "relocatable start digest must be exact SHA-256 bytes"
            raise RelocationError(message)
        if end_digest is not None and (
            _NATIVE_TYPE(end_digest) is not _NATIVE_BYTES
            or _NATIVE_LEN(end_digest) != _SHA256_DIGEST_BYTES
        ):
            message = "relocatable end digest must be exact SHA-256 bytes"
            raise RelocationError(message)
        _validate_range_end_shape(self)


# Generated dataclass initializers dispatch through a mutable class hook.
_LOCATOR_VALIDATOR = cast(
    "Callable[[RangeLocator], None]", RangeLocator.__dict__["__post_init__"]
)

# Frozen slots still allow later class getter replacement. Original descriptors
# are the authority for both direct validation and downstream placement.
_LOCATOR_LENGTH_SLOT = cast(
    "MemberDescriptorType", RangeLocator.__dict__["source_length"]
)
_LOCATOR_WIDTH_SLOT = cast(
    "MemberDescriptorType", RangeLocator.__dict__["window_bytes"]
)
_LOCATOR_START_SLOT = cast(
    "MemberDescriptorType", RangeLocator.__dict__["start_digest"]
)
_LOCATOR_END_SLOT = cast(
    "MemberDescriptorType", RangeLocator.__dict__["end_digest"]
)


def _locator_fields(
    locator: RangeLocator,
) -> tuple[int, int, bytes, bytes | None]:
    return (
        _LOCATOR_LENGTH_SLOT.__get__(locator, RangeLocator),
        _LOCATOR_WIDTH_SLOT.__get__(locator, RangeLocator),
        _LOCATOR_START_SLOT.__get__(locator, RangeLocator),
        _LOCATOR_END_SLOT.__get__(locator, RangeLocator),
    )


def _validate_range_end_shape(locator: RangeLocator) -> None:
    length, width, _, end_digest = _locator_fields(locator)
    if (end_digest is None) != (length == width):
        message = (
            "relocatable end boundary digest must exist exactly when "
            "the source range exceeds its boundary window"
        )
        raise RelocationError(message)


@dataclass(frozen=True, slots=True, init=False)
class RelocatableSourceRange:
    """Source-backed output segment located by content rather than offset."""

    locator: RangeLocator

    def __init__(self, locator: RangeLocator) -> None:
        """Initialize and validate stored source-range metadata."""
        _SOURCE_RANGE_LOCATOR_SLOT.__set__(self, locator)
        _SOURCE_RANGE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require one exact admitted range locator.

        Raises:
            RelocationError: Locator metadata is foreign.

        """
        locator = _range_locator_field(self)
        if _NATIVE_TYPE(locator) is not RangeLocator:
            message = "relocatable source range must use the exact locator type"
            raise RelocationError(message)
        try:
            _LOCATOR_VALIDATOR(locator)
        except AttributeError as error:
            message = "relocatable source range has incomplete locator metadata"
            raise RelocationError(message) from error


_SOURCE_RANGE_VALIDATOR = cast(
    "Callable[[RelocatableSourceRange], None]",
    RelocatableSourceRange.__dict__["__post_init__"],
)
_SOURCE_RANGE_LOCATOR_SLOT = cast(
    "MemberDescriptorType", RelocatableSourceRange.__dict__["locator"]
)


def _range_locator_field(source_range: RelocatableSourceRange) -> RangeLocator:
    return cast(
        "RangeLocator",
        _SOURCE_RANGE_LOCATOR_SLOT.__get__(
            source_range, RelocatableSourceRange
        ),
    )


RelocatableSegment = RelocatableSourceRange | OracleLiteral


def _validate_relocatable_paths(instruction: RelocatableInstruction) -> None:
    output_path, source_path, _, _, _ = _instruction_fields(instruction)
    _ = _validate_relative_path(output_path)
    if source_path is not None:
        _ = _validate_relative_path(source_path)


def _validate_relocatable_payload(instruction: RelocatableInstruction) -> None:
    _, _, copy_candidate_file, literal, segments = (
        _instruction_fields(instruction)
    )
    if _NATIVE_TYPE(copy_candidate_file) is not _NATIVE_BOOL:
        message = "relocatable copy flag must use the exact boolean type"
        raise RelocationError(message)
    if (
        literal is not None
        and _NATIVE_TYPE(literal) is not _NATIVE_BYTES
    ):
        message = "relocatable literal must use exact bytes or None"
        raise RelocationError(message)
    if _NATIVE_TYPE(segments) is not _NATIVE_TUPLE:
        message = "relocatable segments must use the immutable tuple type"
        raise RelocationError(message)
    if _NATIVE_ANY(
        _NATIVE_TYPE(segment) not in {RelocatableSourceRange, OracleLiteral}
        for segment in segments
    ):
        message = "relocatable instruction contains a foreign segment"
        raise RelocationError(message)
    _require_valid_segments(segments)


def _require_valid_segments(segments: tuple[RelocatableSegment, ...]) -> None:
    """Check captured constructor guards on native nested segments.

    Raises:
        RelocationError: A segment is malformed or incomplete.

    """
    try:
        for segment in segments:
            if _NATIVE_TYPE(segment) is RelocatableSourceRange:
                _SOURCE_RANGE_VALIDATOR(segment)
            else:
                _ORACLE_LITERAL_VALIDATOR(cast("OracleLiteral", segment))
    except (AttributeError, RelocationError, TreeModelError) as error:
        message = "relocatable instruction contains invalid native segment"
        raise RelocationError(message) from error


def _validate_relocatable_shape(instruction: RelocatableInstruction) -> None:
    _validate_relocatable_paths(instruction)
    _validate_relocatable_payload(instruction)


def _validate_relocatable_form(instruction: RelocatableInstruction) -> None:
    _, source_path, copy_candidate_file, literal, segments = (
        _instruction_fields(instruction)
    )
    forms = _NATIVE_SUM((
        copy_candidate_file,
        literal is not None,
        _NATIVE_BOOL(segments),
    ))
    if forms != _ONE:
        message = "relocatable instruction requires exactly one payload form"
        raise RelocationError(message)
    if copy_candidate_file and source_path is None:
        message = "candidate-file copy requires a source path"
        raise RelocationError(message)
    if segments and source_path is None:
        message = "relocatable segments require a source path"
        raise RelocationError(message)
    if literal is not None and source_path is not None:
        message = "literal relocatable instruction cannot require source"
        raise RelocationError(message)


@dataclass(frozen=True, slots=True, init=False)
class RelocatableInstruction:
    """One compatible-placement output instruction."""

    output_path: str
    source_path: str | None
    copy_candidate_file: bool
    literal: bytes | None = None
    segments: tuple[RelocatableSegment, ...] = ()

    def __init__(
        self,
        output_path: str,
        source_path: str | None,
        copy_candidate_file: bool,
        literal: bytes | None = None,
        segments: tuple[RelocatableSegment, ...] = (),
    ) -> None:
        """Initialize stored output instruction and run pinned validation."""
        _INSTRUCTION_OUTPUT_SLOT.__set__(self, output_path)
        _INSTRUCTION_SOURCE_SLOT.__set__(self, source_path)
        _INSTRUCTION_COPY_SLOT.__set__(self, copy_candidate_file)
        _INSTRUCTION_LITERAL_SLOT.__set__(self, literal)
        _INSTRUCTION_SEGMENTS_SLOT.__set__(self, segments)
        _INSTRUCTION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject ambiguous instruction forms."""
        _validate_relocatable_shape(self)
        _validate_relocatable_form(self)


_INSTRUCTION_VALIDATOR = cast(
    "Callable[[RelocatableInstruction], None]",
    RelocatableInstruction.__dict__["__post_init__"],
)
_INSTRUCTION_OUTPUT_SLOT = cast(
    "MemberDescriptorType", RelocatableInstruction.__dict__["output_path"]
)
_INSTRUCTION_SOURCE_SLOT = cast(
    "MemberDescriptorType", RelocatableInstruction.__dict__["source_path"]
)
_INSTRUCTION_COPY_SLOT = cast(
    "MemberDescriptorType",
    RelocatableInstruction.__dict__["copy_candidate_file"],
)
_INSTRUCTION_LITERAL_SLOT = cast(
    "MemberDescriptorType", RelocatableInstruction.__dict__["literal"]
)
_INSTRUCTION_SEGMENTS_SLOT = cast(
    "MemberDescriptorType", RelocatableInstruction.__dict__["segments"]
)


def _instruction_fields(
    instruction: RelocatableInstruction,
) -> tuple[str, str | None, bool, bytes | None, tuple[RelocatableSegment, ...]]:
    return (
        _INSTRUCTION_OUTPUT_SLOT.__get__(instruction, RelocatableInstruction),
        _INSTRUCTION_SOURCE_SLOT.__get__(instruction, RelocatableInstruction),
        _INSTRUCTION_COPY_SLOT.__get__(instruction, RelocatableInstruction),
        _INSTRUCTION_LITERAL_SLOT.__get__(instruction, RelocatableInstruction),
        _INSTRUCTION_SEGMENTS_SLOT.__get__(instruction, RelocatableInstruction),
    )


@dataclass(frozen=True, slots=True, init=False)
class RelocatableAuthoringPlan:
    """Non-distributable placement plan derived from an exact baseline."""

    instructions: tuple[RelocatableInstruction, ...]

    def __init__(
        self, instructions: tuple[RelocatableInstruction, ...]
    ) -> None:
        """Preserve construction checks under late validator replacement."""
        _PLAN_INSTRUCTIONS_SLOT.__set__(self, instructions)
        _PLAN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require immutable exact relocation instructions.

        Raises:
            RelocationError: Plan records are mutable or foreign.

        """
        instructions = _plan_instructions(self)
        if _NATIVE_TYPE(instructions) is not _NATIVE_TUPLE:
            message = (
                "relocatable plan instructions must use an immutable tuple"
            )
            raise RelocationError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(instruction) is not RelocatableInstruction
            for instruction in instructions
        ):
            message = "relocatable plan contains a foreign instruction record"
            raise RelocationError(message)
        _require_valid_relocatable_instructions(instructions)
        paths = _NATIVE_TUPLE(
            _instruction_fields(item)[0] for item in instructions
        )
        if _NATIVE_LEN(paths) != _NATIVE_LEN(_NATIVE_SET(paths)):
            message = "relocatable plan requires unique output paths"
            raise RelocationError(message)
        known_paths = _NATIVE_SET(paths)
        if _NATIVE_ANY(
            ancestor in known_paths
            for path in paths
            for ancestor in _lexical_ancestors(path)
        ):
            message = "relocatable output files have ancestor path overlap"
            raise RelocationError(message)


def _require_valid_relocatable_instructions(
    instructions: tuple[RelocatableInstruction, ...],
) -> None:
    """Revalidate nested instructions even after raw slot fabrication.

    Raises:
        RelocationError: An instruction is malformed or incomplete.

    """
    try:
        for instruction in instructions:
            _INSTRUCTION_VALIDATOR(instruction)
    except AttributeError as error:
        message = "relocatable plan has incomplete native instruction metadata"
        raise RelocationError(message) from error


_PLAN_VALIDATOR = cast(
    "Callable[[RelocatableAuthoringPlan], None]",
    RelocatableAuthoringPlan.__dict__["__post_init__"],
)
_PLAN_INSTRUCTIONS_SLOT = cast(
    "MemberDescriptorType", RelocatableAuthoringPlan.__dict__["instructions"]
)


def _plan_instructions(
    plan: RelocatableAuthoringPlan,
) -> tuple[RelocatableInstruction, ...]:
    return cast(
        "tuple[RelocatableInstruction, ...]",
        _PLAN_INSTRUCTIONS_SLOT.__get__(plan, RelocatableAuthoringPlan),
    )


# The placement writer builds internal records after source reads. Capture
# original constructors so later class substitutions cannot forge locators.
_RANGE_LOCATOR_INIT = cast(
    "Callable[[RangeLocator, int, int, bytes, bytes | None], None]",
    RangeLocator.__dict__["__init__"],
)
_SOURCE_RANGE_INIT = cast(
    "Callable[[RelocatableSourceRange, RangeLocator], None]",
    RelocatableSourceRange.__dict__["__init__"],
)
_RELOCATABLE_INSTRUCTION_INIT = cast(
    Callable[
        [
            RelocatableInstruction,
            str,
            str | None,
            bool,
            bytes | None,
            tuple[RelocatableSegment, ...],
        ],
        None,
    ],
    RelocatableInstruction.__dict__["__init__"],
)
_RELOCATABLE_PLAN_INIT = cast(
    "Callable[[RelocatableAuthoringPlan, tuple[RelocatableInstruction, ...]], None]",
    RelocatableAuthoringPlan.__dict__["__init__"],
)


def _new_range_locator(
    source_length: int,
    window_bytes: int,
    start_digest: bytes,
    end_digest: bytes | None,
) -> RangeLocator:
    locator = _NATIVE_OBJECT_NEW(RangeLocator)
    _RANGE_LOCATOR_INIT(
        locator, source_length, window_bytes, start_digest, end_digest
    )
    return locator


def _new_source_range(locator: RangeLocator) -> RelocatableSourceRange:
    segment = _NATIVE_OBJECT_NEW(RelocatableSourceRange)
    _SOURCE_RANGE_INIT(segment, locator)
    return segment


def _new_relocatable_instruction(
    output_path: str,
    source_path: str | None,
    copy_candidate_file: bool,
    literal: bytes | None = None,
    segments: tuple[RelocatableSegment, ...] = (),
) -> RelocatableInstruction:
    instruction = _NATIVE_OBJECT_NEW(RelocatableInstruction)
    _RELOCATABLE_INSTRUCTION_INIT(
        instruction, output_path, source_path, copy_candidate_file, literal, segments
    )
    return instruction


def _new_relocatable_plan(
    instructions: tuple[RelocatableInstruction, ...],
) -> RelocatableAuthoringPlan:
    plan = _NATIVE_OBJECT_NEW(RelocatableAuthoringPlan)
    _RELOCATABLE_PLAN_INIT(plan, instructions)
    return plan


def _lexical_ancestors(path: str) -> tuple[str, ...]:
    """Find canonical file ancestors without mutable pathlib class hooks."""
    parts = path.split("/")
    return _NATIVE_TUPLE(
        "/".join(parts[:end])
        for end in _NATIVE_RANGE(_ONE, _NATIVE_LEN(parts))
    )


def _sha256(data: bytes) -> bytes:
    return _SHA256_FACTORY(data).digest()


# Relocation consumes exact authoring evidence after domain callbacks may have
# replaced model class readers. Keep the original model storage descriptors.
_SLICE_OFFSET_SLOT = cast(
    "MemberDescriptorType", SourceSlice.__dict__["offset"]
)
_SLICE_LENGTH_SLOT = cast(
    "MemberDescriptorType", SourceSlice.__dict__["length"]
)
_LITERAL_DATA_SLOT = cast(
    "MemberDescriptorType", OracleLiteral.__dict__["data"]
)
_EXACT_KIND_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["kind"]
)
_EXACT_OUTPUT_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["output_path"]
)
_EXACT_SOURCE_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["source_path"]
)
_EXACT_LITERAL_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["literal"]
)
_EXACT_SEGMENTS_SLOT = cast(
    "MemberDescriptorType", ExactInstruction.__dict__["segments"]
)
_EXACT_PLAN_SOURCE_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["source"]
)
_EXACT_PLAN_INSTRUCTIONS_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["instructions"]
)
_EXACT_PLAN_PASSTHROUGH_SLOT = cast(
    "MemberDescriptorType", ExactAuthoringPlan.__dict__["passthrough_roots"]
)

# Tree/file dataclass comparisons and getters remain replaceable after import.
_SNAPSHOT_FILES_SLOT = cast(
    "MemberDescriptorType", TreeSnapshot.__dict__["files"]
)
_FILE_PATH_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["path"])
_FILE_DIGEST_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["sha256"])
_FILE_SIZE_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["size"])


def _snapshot_evidence(
    snapshot: TreeSnapshot,
) -> tuple[tuple[str, str, int], ...]:
    """Compare stored path, digest and size without late record hooks."""
    if _NATIVE_TYPE(snapshot) is not TreeSnapshot:
        message = "relocatable snapshot must use exact tree evidence"
        raise RelocationError(message)
    files = cast(
        "tuple[FileRecord, ...]",
        _SNAPSHOT_FILES_SLOT.__get__(snapshot, TreeSnapshot),
    )
    if _NATIVE_TYPE(files) is not _NATIVE_TUPLE or _NATIVE_ANY(
        _NATIVE_TYPE(item) is not FileRecord for item in files
    ):
        message = "relocatable snapshot contains foreign file evidence"
        raise RelocationError(message)
    return _NATIVE_TUPLE(
        (
            _FILE_PATH_SLOT.__get__(item, FileRecord),
            _FILE_DIGEST_SLOT.__get__(item, FileRecord),
            _FILE_SIZE_SLOT.__get__(item, FileRecord),
        )
        for item in files
    )


def _source_slice_fields(segment: SourceSlice) -> tuple[int, int]:
    return (
        _SLICE_OFFSET_SLOT.__get__(segment, SourceSlice),
        _SLICE_LENGTH_SLOT.__get__(segment, SourceSlice),
    )


def _oracle_literal_bytes(literal: OracleLiteral) -> bytes:
    return cast("bytes", _LITERAL_DATA_SLOT.__get__(literal, OracleLiteral))


def _exact_instruction_fields(
    instruction: ExactInstruction,
) -> tuple[
    ExactInstructionKind,
    str,
    str | None,
    bytes | None,
    tuple[ExactSegment, ...],
]:
    return (
        _EXACT_KIND_SLOT.__get__(instruction, ExactInstruction),
        _EXACT_OUTPUT_SLOT.__get__(instruction, ExactInstruction),
        _EXACT_SOURCE_SLOT.__get__(instruction, ExactInstruction),
        _EXACT_LITERAL_SLOT.__get__(instruction, ExactInstruction),
        _EXACT_SEGMENTS_SLOT.__get__(instruction, ExactInstruction),
    )


def _exact_plan_fields(
    plan: ExactAuthoringPlan,
) -> tuple[TreeSnapshot, tuple[ExactInstruction, ...], tuple[str, ...]]:
    return (
        _EXACT_PLAN_SOURCE_SLOT.__get__(plan, ExactAuthoringPlan),
        _EXACT_PLAN_INSTRUCTIONS_SLOT.__get__(plan, ExactAuthoringPlan),
        _EXACT_PLAN_PASSTHROUGH_SLOT.__get__(plan, ExactAuthoringPlan),
    )


def _range_locator(source: bytes, segment: SourceSlice) -> RangeLocator:
    offset, length = _source_slice_fields(segment)
    end = offset + length
    if end > _NATIVE_LEN(source):
        message = "exact source slice exceeds authoring source file"
        raise RelocationError(message)
    data = source[offset:end]
    window_bytes = _NATIVE_MIN(_BOUNDARY_BYTES, _NATIVE_LEN(data))
    start_digest = _sha256(data[:window_bytes])
    end_digest = None
    if _NATIVE_LEN(data) > window_bytes:
        end_digest = _sha256(data[-window_bytes:])
    return _new_range_locator(
        source_length=_NATIVE_LEN(data),
        window_bytes=window_bytes,
        start_digest=start_digest,
        end_digest=end_digest,
    )


def _relocatable_segment(
    source: bytes, segment: ExactSegment
) -> RelocatableSegment:
    if _NATIVE_TYPE(segment) is OracleLiteral:
        return segment
    source_slice = cast("SourceSlice", segment)
    return _new_source_range(_range_locator(source, source_slice))


def _instruction(
    source_root: Path,
    exact_instruction: ExactInstruction,
) -> RelocatableInstruction:
    kind, output_path, source_path, literal, segments = (
        _exact_instruction_fields(exact_instruction)
    )
    if kind is ExactInstructionKind.COPY_SOURCE:
        return _new_relocatable_instruction(
            output_path=output_path,
            source_path=source_path,
            copy_candidate_file=True,
        )
    if kind is ExactInstructionKind.LITERAL_ORACLE:
        if literal is None:
            message = "exact literal instruction lost authoring bytes"
            raise RelocationError(message)
        return _new_relocatable_instruction(
            output_path=output_path,
            source_path=None,
            copy_candidate_file=False,
            literal=literal,
        )
    if source_path is None:
        message = "exact patch instruction lost source path"
        raise RelocationError(message)
    source = _read_relocatable_bytes(
        _safe_path(source_root, source_path), "relocatable source"
    )
    return _new_relocatable_instruction(
        output_path=output_path,
        source_path=source_path,
        copy_candidate_file=False,
        segments=_NATIVE_TUPLE(
            _relocatable_segment(source, segment) for segment in segments
        ),
    )


def _path_status(path: Path, context: str) -> os.stat_result | None:
    try:
        status = _NATIVE_PATH_LSTAT(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"{context} status failed: {path}: {detail}"
        raise RelocationError(message) from error
    if _NATIVE_TYPE(status) is not _NATIVE_STAT_RESULT:
        message = f"{context} requires native filesystem status: {path}"
        raise RelocationError(message)
    return status


def _path_present(path: Path, context: str) -> bool:
    return _path_status(path, context) is not None


def _read_relocatable_bytes(path: Path, context: str) -> bytes:
    try:
        return read_exact_regular_file(path, context)
    except ExactTreeError as error:
        detail = _host_error_detail(error)
        message = f"{context} read failed: {path}: {detail}"
        failure = RelocationError(message)
        if _NATIVE_TYPE(error) is ExactTreeError:
            for note in cast("list[str]", getattr(error, "__notes__", [])):
                failure.add_note(note)
        raise failure from error


def _native_write_relocatable_bytes(path: Path, data: bytes) -> int:
    """Create a fresh staged file without post-import Path write hooks."""
    with _NATIVE_IO_OPEN(_NATIVE_PATH_STRING(path), "xb") as stream:
        return stream.write(data)


_NATIVE_WRITE_RELOCATABLE_BYTES = _native_write_relocatable_bytes


def _native_make_relocatable_directory(
    path: Path, *, parents: bool, exist_ok: bool
) -> None:
    """Create directories through captured native OS and path operations."""
    try:
        _NATIVE_OS_MKDIR(_NATIVE_PATH_STRING(path))
    except FileNotFoundError:
        parent = _NATIVE_PATH_PARENT(path)
        if not parents or _NATIVE_PATH_STRING(parent) == _NATIVE_PATH_STRING(path):
            raise
        _native_make_relocatable_directory(parent, parents=True, exist_ok=True)
        _native_make_relocatable_directory(path, parents=False, exist_ok=exist_ok)
    except FileExistsError:
        if not exist_ok:
            raise
        status = _path_status(path, "relocatable output directory")
        if status is None or not S_ISDIR(status.st_mode):
            raise


def _write_relocatable_bytes(path: Path, data: bytes, context: str) -> None:
    try:
        _native_make_relocatable_directory(
            _NATIVE_PATH_PARENT(path), parents=True, exist_ok=True
        )
        written = _NATIVE_WRITE_RELOCATABLE_BYTES(path, data)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"{context} write failed: {path}: {detail}"
        raise RelocationError(message) from error
    if _NATIVE_TYPE(written) is not _NATIVE_INT or written != _NATIVE_LEN(data):
        message = f"{context} short or invalid byte count: {path}"
        raise RelocationError(message)


def _make_relocatable_directory(
    path: Path,
    context: str,
    *,
    parents: bool,
    exist_ok: bool,
) -> None:
    try:
        _native_make_relocatable_directory(
            path, parents=parents, exist_ok=exist_ok
        )
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"{context} creation failed: {path}: {detail}"
        raise RelocationError(message) from error


def _validate_path(value: object, context: str) -> None:
    # A foreign Path subclass can redirect byte reads or output staging.
    if _NATIVE_TYPE(value) is not _NATIVE_PATH_TYPE:
        message = f"{context} must use exact pathlib Path"
        raise RelocationError(message)
    text = _NATIVE_PATH_STRING(value)
    if _NUL in text:
        message = f"{context} is not a representable filesystem path"
        raise RelocationError(message)
    try:
        _ = text.encode(_NATIVE_FS_ENCODING, _NATIVE_FS_ERRORS)
    except UnicodeError as error:
        message = f"{context} is not a representable filesystem path"
        raise RelocationError(message) from error


def _require_exact_source_snapshot(
    source_root: Path, exact_plan: ExactAuthoringPlan
) -> None:
    """Require the authoring tree to match the bound exact source evidence.

    Raises:
        RelocationError: The source snapshot is invalid or has changed.

    """
    try:
        source, _, passthrough = _exact_plan_fields(exact_plan)
        current = snapshot_tree_excluding(source_root, passthrough)
    except ExactTreeError as error:
        detail = _host_error_detail(error)
        message = f"relocatable source snapshot failed: {detail}"
        raise RelocationError(message) from error
    if _snapshot_evidence(current) != _snapshot_evidence(source):
        message = "relocatable source snapshot differs from exact plan"
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
    if _NATIVE_TYPE(exact_plan) is not ExactAuthoringPlan:
        message = (
            "relocatable source plan must use the exact authoring-plan type"
        )
        raise RelocationError(message)
    try:
        _EXACT_PLAN_VALIDATOR(exact_plan)
    except (AttributeError, TreeModelError, TypeError) as error:
        message = "relocatable exact plan has invalid native metadata"
        raise RelocationError(message) from error
    _require_exact_source_snapshot(source_root, exact_plan)
    instructions = _NATIVE_TUPLE(
        _instruction(source_root, instruction)
        for instruction in _exact_plan_fields(exact_plan)[1]
    )
    _require_exact_source_snapshot(source_root, exact_plan)
    return _new_relocatable_plan(instructions=instructions)


def _validate_relative_path(relative_path: object) -> str:
    if _NATIVE_TYPE(relative_path) is not _NATIVE_STR:
        message = "relocatable path must use the exact string type"
        raise RelocationError(message)
    try:
        _ = relative_path.encode("utf-8")
    except UnicodeEncodeError as error:
        message = f"unsafe relocatable tree path: {relative_path!r}"
        raise RelocationError(message) from error
    # Pathlib class methods and parsers remain mutable after import. Keep
    # canonical relative-path admission independent of consumer callbacks.
    unsafe = (
        not relative_path
        or _NUL in relative_path
        or _NATIVE_ANY(
            component in ("", ".", "..")
            or reserved_windows_component(component)
            for component in relative_path.split("/")
        )
    )
    if unsafe:
        message = f"unsafe relocatable tree path: {relative_path!r}"
        raise RelocationError(message)
    return relative_path


def _is_linked_ancestor(path: Path, status: os.stat_result) -> bool:
    try:
        symlink = _NATIVE_IS_SYMLINK(status.st_mode)
        junction = _NATIVE_IS_JUNCTION(path) if not symlink else False
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"ancestor inspection failed: {path}: {detail}"
        raise RelocationError(message) from error
    if (
        _NATIVE_TYPE(symlink) is not _NATIVE_BOOL
        or _NATIVE_TYPE(junction) is not _NATIVE_BOOL
    ):
        message = f"ancestor inspection failed: {path}: non-native verdict"
        raise RelocationError(message)
    return symlink or junction


def _reject_linked_ancestors(root: Path, relative_path: str) -> None:
    current = root
    for component in relative_path.split("/")[:-1]:
        current /= component
        status = _path_status(current, "relocatable path ancestor")
        if status is not None and _is_linked_ancestor(current, status):
            message = (
                f"relocatable linked path component is not supported: {current}"
            )
            raise RelocationError(message)


def _safe_path(root: Path, relative_path: str) -> Path:
    normalized = _validate_relative_path(relative_path)
    path = root.joinpath(*normalized.split("/"))
    try:
        resolved_path = _NATIVE_RESOLVE(path)
        resolved_root = _NATIVE_RESOLVE(root)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = (
            f"relocatable path resolution failed: {relative_path!r}: {detail}"
        )
        raise RelocationError(message) from error
    if (
        _NATIVE_TYPE(resolved_path) is not _NATIVE_PATH_TYPE
        or _NATIVE_TYPE(resolved_root) is not _NATIVE_PATH_TYPE
    ):
        message = "relocatable path resolution requires native resolved Path"
        raise RelocationError(message)
    try:
        _ = _NATIVE_RELATIVE_TO(resolved_path, resolved_root)
    except ValueError as error:
        message = f"relocatable path escapes tree root: {relative_path!r}"
        raise RelocationError(message) from error
    _reject_linked_ancestors(root, normalized)
    return path


def _window_index(
    data: bytes, window_bytes: int
) -> dict[bytes, tuple[int, ...]]:
    if _NATIVE_LEN(data) < window_bytes:
        return {}
    mutable: dict[bytes, list[int]] = {}
    last = _NATIVE_LEN(data) - window_bytes
    for offset in _NATIVE_RANGE(last + _ONE):
        digest = _sha256(data[offset : offset + window_bytes])
        mutable.setdefault(digest, []).append(offset)
    return {
        digest: _NATIVE_TUPLE(offsets)
        for digest, offsets in mutable.items()
    }


def _unique_offset(
    index: dict[bytes, tuple[int, ...]],
    digest: bytes,
    label: str,
) -> int:
    offsets = index.get(digest, ())
    if _NATIVE_LEN(offsets) != _ONE:
        message = f"relocatable {label} boundary is missing or ambiguous"
        raise RelocationError(message)
    return offsets[0]


def _locate_range(candidate: bytes, locator: RangeLocator) -> tuple[int, int]:
    length, width, start_digest, end_digest = _locator_fields(locator)
    index = _window_index(candidate, width)
    start = _unique_offset(index, start_digest, "start")
    if end_digest is None:
        return start, start + length
    end_start = _unique_offset(index, end_digest, "end")
    end = end_start + width
    if end <= start or end - start < length:
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
        if _NATIVE_TYPE(segment) is OracleLiteral:
            parts.append(_oracle_literal_bytes(segment))
            continue
        relocated = cast("RelocatableSourceRange", segment)
        start, end = _locate_range(candidate, _range_locator_field(relocated))
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
    _, source_path, copy_candidate_file, literal, segments = (
        _instruction_fields(instruction)
    )
    if literal is not None:
        return literal
    if source_path is None:
        message = "relocatable instruction lost source path"
        raise RelocationError(message)
    candidate_path = _safe_path(candidate_root, source_path)
    candidate = _read_relocatable_bytes(candidate_path, "relocatable candidate")
    if copy_candidate_file:
        return candidate
    return _patch_bytes(candidate, segments)


def _prepare_staging(output_root: Path) -> Path:
    if _path_present(output_root, "relocatable output root"):
        message = f"output root already exists: {output_root}"
        raise RelocationError(message)
    staging = _NATIVE_PATH_WITH_NAME(
        output_root, f".{_NATIVE_PATH_NAME(output_root)}{_STAGING_SUFFIX}"
    )
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
        _NATIVE_RMTREE(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        return _host_error_detail(error)
    return None


def _raise_relocatable_cleanup_failure(
    error: Exception, cleanup_error: str
) -> None:
    detail = _host_error_detail(error)
    message = f"{detail}; relocatable staging cleanup failed: {cleanup_error}"
    raise RelocationError(message) from error


def _publish_relocatable_output(staging: Path, destination: Path) -> None:
    try:
        publish_directory_no_replace(staging, destination)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"relocatable output publication failed: {detail}"
        raise RelocationError(message) from error


def _require_external_output_root(
    candidate_root: Path, output_root: Path
) -> None:
    """Reject a destination inside the candidate before staging writes.

    Raises:
        RelocationError: Root resolution fails or output is source-contained.

    """
    try:
        candidate = _NATIVE_RESOLVE(candidate_root)
        output = _NATIVE_RESOLVE(output_root)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"relocatable root resolution failed: {detail}"
        raise RelocationError(message) from error
    if (
        _NATIVE_TYPE(candidate) is not _NATIVE_PATH_TYPE
        or _NATIVE_TYPE(output) is not _NATIVE_PATH_TYPE
    ):
        message = "relocatable root resolution requires native resolved Path"
        raise RelocationError(message)
    if _NATIVE_IS_RELATIVE_TO(output, candidate):
        message = "relocatable output must not be inside the candidate source"
        raise RelocationError(message)


def _require_valid_native_relocatable_plan(
    plan: RelocatableAuthoringPlan,
) -> None:
    """Require exact native plan storage before materialization starts.

    Raises:
        RelocationError: The native plan has foreign or incomplete metadata.

    """
    try:
        _PLAN_VALIDATOR(plan)
    except AttributeError as error:
        message = "relocatable plan has incomplete native metadata"
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
    if _NATIVE_TYPE(plan) is not RelocatableAuthoringPlan:
        message = "relocatable materialization requires the exact plan type"
        raise RelocationError(message)
    _require_valid_native_relocatable_plan(plan)
    _require_external_output_root(candidate_root, output_root)
    staging = _prepare_staging(output_root)
    try:
        for instruction in _plan_instructions(plan):
            data = _instruction_bytes(candidate_root, instruction)
            output = _safe_path(staging, _instruction_fields(instruction)[0])
            _write_relocatable_bytes(output, data, "relocatable output")
        _publish_relocatable_output(staging, output_root)
    except Exception as error:
        cleanup_error = _cleanup_relocatable_staging(staging)
        if cleanup_error is not None:
            _raise_relocatable_cleanup_failure(error, cleanup_error)
        raise
