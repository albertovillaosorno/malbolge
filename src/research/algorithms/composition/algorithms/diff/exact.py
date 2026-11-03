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
#   - Exact deterministic tree planning and materialization for authoring.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Exact deterministic tree planning and materialization for authoring."""

from __future__ import annotations

import builtins
import io
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256 as _native_sha256
from pathlib import Path, PurePath
from stat import S_ISDIR, S_ISLNK, S_ISREG
from types import MemberDescriptorType
from typing import TYPE_CHECKING, cast

from algorithms.diff.model import (
    ExactAuthoringPlan,
    ExactInstruction,
    ExactInstructionKind,
    FileRecord,
    OracleLiteral,
    SourceSlice,
    TreeModelError,
    TreeSnapshot,
    _file_fields,  # pyright: ignore[reportPrivateUsage]
    _instruction_fields,  # pyright: ignore[reportPrivateUsage]
    _oracle_literal_data,  # pyright: ignore[reportPrivateUsage]
    _plan_fields,  # pyright: ignore[reportPrivateUsage]
    _snapshot_files,  # pyright: ignore[reportPrivateUsage]
    _source_slice_fields,  # pyright: ignore[reportPrivateUsage]
    reserved_windows_component,
)
from algorithms.diff.publication import publish_directory_no_replace

if TYPE_CHECKING:
    from collections.abc import Iterator

    from algorithms.diff.model import ExactSegment

_BACKSLASH = "\\"
_UNSAFE_PATH_PARTS = frozenset({"", ".", ".."})
_STAGING_SUFFIX = ".staging"
_MATCH_BLOCK_BYTES = 32
_FILE_READ_CHUNK_BYTES = 65_536
_FILE_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_BINARY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)
_ZERO = 0
# Keep path and passthrough admission independent of late host hooks.
_NATIVE_ANY = builtins.any
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_BYTEARRAY = builtins.bytearray
_NATIVE_MIN = builtins.min
_NATIVE_SET = builtins.set
_NATIVE_SORTED = builtins.sorted
_NATIVE_TYPE = builtins.type
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_BYTES = builtins.bytes
_NATIVE_BOOL = builtins.bool
_NATIVE_STR = builtins.str
_NATIVE_INT = builtins.int
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_RANGE = builtins.range
_NATIVE_OBJECT_NEW = object.__new__
_NUL = "\x00"
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_RELATIVE_TO = Path.relative_to
_NATIVE_PATH_RESOLVE = Path.resolve
_NATIVE_PATH_JOINPATH = Path.joinpath
_NATIVE_PATH_LSTAT = os.lstat
_NATIVE_PATH_WALK = Path.walk
_NATIVE_PATH_IS_JUNCTION = Path.is_junction
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_PARENT = cast("Callable[[Path], Path]", Path.parent.fget)
_NATIVE_PATH_NAME = cast("Callable[[Path], str]", Path.name.fget)
_NATIVE_IO_OPEN = io.open
_NATIVE_OS_MKDIR = os.mkdir
# Encode native Path strings without mutable late pathlib/os conversion hooks.
_FILESYSTEM_ENCODING = sys.getfilesystemencoding()
_FILESYSTEM_ERRORS = sys.getfilesystemencodeerrors()
# Owned staging deletion must ignore consumer changes to shutil hooks.
_NATIVE_RMTREE = shutil.rmtree
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
# Capturing Path.__str__ is insufficient: it reads a mutable cached slot,
# and original filesystem operations call late Path.__fspath__ dispatch.
_PATH_HOOK_NAMES = (
    "__getattribute__",
    "__getattr__",
    "__setattr__",
    "__str__",
    "__fspath__",
    "__truediv__",
    "as_posix",
    "_str",
    "_raw_paths",
    "_drv",
    "_root",
    "_tail_cached",
    "_raw_path",
    "_tail",
    "drive",
    "root",
    "_parse_path",
    "_format_parsed_parts",
    "parser",
)
_NATIVE_PATH_HOOKS = _NATIVE_TUPLE(
    (
        cls,
        _NATIVE_TUPLE((name, cls.__dict__.get(name)) for name in _PATH_HOOK_NAMES),
    )
    for cls in _NATIVE_PATH_TYPE.__mro__
    if issubclass(cls, PurePath)
)


def _require_native_path_hooks(*, direct_file_read: bool = False) -> None:
    """Guard path resolution; direct descriptor reads ignore late os.fspath."""
    if (
        (not direct_file_read and os.fspath is not _NATIVE_OS_FSPATH)
        or _NATIVE_ANY(
            cls.__dict__.get(name) is not original
            for cls, hooks in _NATIVE_PATH_HOOKS
            for name, original in hooks
            if not direct_file_read or name not in {"__truediv__", "as_posix"}
        )
    ):
        message = "exact filesystem path hooks changed"
        raise ExactTreeError(message)


class ExactTreeError(RuntimeError):
    """Raised when exact planning or materialization cannot proceed safely."""


# Snapshot receipts are created after filesystem reads and selection callbacks.
# Reuse the model validators without consulting mutable class allocation hooks.
_FILE_RECORD_INIT = cast(
    "Callable[[FileRecord, str, str, int], None]",
    FileRecord.__dict__["__init__"],
)
_TREE_SNAPSHOT_INIT = cast(
    "Callable[[TreeSnapshot, tuple[FileRecord, ...]], None]",
    TreeSnapshot.__dict__["__init__"],
)


def _new_file_record(path: str, sha256: str, size: int) -> FileRecord:
    record = _NATIVE_OBJECT_NEW(FileRecord)
    _FILE_RECORD_INIT(record, path, sha256, size)
    return record


def _new_tree_snapshot(files: tuple[FileRecord, ...]) -> TreeSnapshot:
    snapshot = _NATIVE_OBJECT_NEW(TreeSnapshot)
    _TREE_SNAPSHOT_INIT(snapshot, files)
    return snapshot


# Reconstruct the exact plan only with its original validating initializer.
# Class hooks remain mutable even on frozen slotted model records.
_EXACT_PLAN_VALIDATOR = cast(
    "Callable[[ExactAuthoringPlan], None]",
    ExactAuthoringPlan.__dict__["__post_init__"],
)
_EXACT_PLAN_INIT = cast(
    Callable[
        [
            ExactAuthoringPlan,
            TreeSnapshot,
            TreeSnapshot,
            tuple[ExactInstruction, ...],
            tuple[str, ...],
        ],
        None,
    ],
    ExactAuthoringPlan.__dict__["__init__"],
)


def _new_exact_plan(
    source: TreeSnapshot,
    target: TreeSnapshot,
    instructions: tuple[ExactInstruction, ...],
    passthrough_roots: tuple[str, ...],
) -> ExactAuthoringPlan:
    """Construct an internally authored plan without late class hooks."""
    plan = _NATIVE_OBJECT_NEW(ExactAuthoringPlan)
    _EXACT_PLAN_INIT(plan, source, target, instructions, passthrough_roots)
    return plan


# Patch segments and instructions are computed after tree reads; internal
# creation must not reenter class hooks installed during consumer callbacks.
_SOURCE_SLICE_INIT = cast(
    "Callable[[SourceSlice, int, int], None]",
    SourceSlice.__dict__["__init__"],
)
_ORACLE_LITERAL_INIT = cast(
    "Callable[[OracleLiteral, bytes], None]",
    OracleLiteral.__dict__["__init__"],
)
_EXACT_INSTRUCTION_INIT = cast(
    Callable[
        [
            ExactInstruction,
            str,
            ExactInstructionKind,
            str,
            str | None,
            bytes | None,
            tuple[SourceSlice | OracleLiteral, ...],
        ],
        None,
    ],
    ExactInstruction.__dict__["__init__"],
)


def _new_source_slice(offset: int, length: int) -> SourceSlice:
    segment = _NATIVE_OBJECT_NEW(SourceSlice)
    _SOURCE_SLICE_INIT(segment, offset, length)
    return segment


def _new_oracle_literal(data: bytes) -> OracleLiteral:
    segment = _NATIVE_OBJECT_NEW(OracleLiteral)
    _ORACLE_LITERAL_INIT(segment, data)
    return segment


def _new_exact_instruction(
    output_path: str,
    kind: ExactInstructionKind,
    expected_sha256: str,
    source_path: str | None = None,
    literal: bytes | None = None,
    segments: tuple[ExactSegment, ...] = (),
) -> ExactInstruction:
    instruction = _NATIVE_OBJECT_NEW(ExactInstruction)
    _EXACT_INSTRUCTION_INIT(
        instruction,
        output_path,
        kind,
        expected_sha256,
        source_path,
        literal,
        segments,
    )
    return instruction


@dataclass(frozen=True, slots=True, init=False)
class _MatchContext:
    """Immutable byte-matching inputs shared across one file diff."""

    source: bytes
    target: bytes
    index: dict[bytes, int]

    def __init__(
        self, source: bytes, target: bytes, index: dict[bytes, int]
    ) -> None:
        """Preserve exact byte-matching data despite class setter changes."""
        _MATCH_SOURCE_SLOT.__set__(self, source)
        _MATCH_TARGET_SLOT.__set__(self, target)
        _MATCH_INDEX_SLOT.__set__(self, index)


@dataclass(frozen=True, slots=True, init=False)
class _PlanningContext:
    """Immutable tree indexes shared across target-file planning."""

    source_root: Path
    oracle_root: Path
    source_by_path: dict[str, FileRecord]
    source_by_content: dict[tuple[str, int], tuple[str, ...]]

    def __init__(
        self,
        source_root: Path,
        oracle_root: Path,
        source_by_path: dict[str, FileRecord],
        source_by_content: dict[tuple[str, int], tuple[str, ...]],
    ) -> None:
        """Preserve admitted roots and file indexes against class setters."""
        _PLANNING_SOURCE_ROOT_SLOT.__set__(self, source_root)
        _PLANNING_ORACLE_ROOT_SLOT.__set__(self, oracle_root)
        _PLANNING_BY_PATH_SLOT.__set__(self, source_by_path)
        _PLANNING_BY_CONTENT_SLOT.__set__(self, source_by_content)


# Keep matching and authoring indexes opaque to late class allocation hooks.
_MATCH_CONTEXT_INIT = cast(
    "Callable[[_MatchContext, bytes, bytes, dict[bytes, int]], None]",
    _MatchContext.__dict__["__init__"],
)
_PLANNING_CONTEXT_INIT = cast(
    Callable[
        [
            _PlanningContext,
            Path,
            Path,
            dict[str, FileRecord],
            dict[tuple[str, int], tuple[str, ...]],
        ],
        None,
    ],
    _PlanningContext.__dict__["__init__"],
)


def _new_match_context(
    source: bytes, target: bytes, index: dict[bytes, int]
) -> _MatchContext:
    context = _NATIVE_OBJECT_NEW(_MatchContext)
    _MATCH_CONTEXT_INIT(context, source, target, index)
    return context


def _new_planning_context(
    source_root: Path,
    oracle_root: Path,
    source_by_path: dict[str, FileRecord],
    source_by_content: dict[tuple[str, int], tuple[str, ...]],
) -> _PlanningContext:
    context = _NATIVE_OBJECT_NEW(_PlanningContext)
    _PLANNING_CONTEXT_INIT(
        context, source_root, oracle_root, source_by_path, source_by_content
    )
    return context


# Captured original descriptors prevent late getter or setter substitution.
_MATCH_SOURCE_SLOT = cast(
    "MemberDescriptorType", _MatchContext.__dict__["source"]
)
_MATCH_TARGET_SLOT = cast(
    "MemberDescriptorType", _MatchContext.__dict__["target"]
)
_MATCH_INDEX_SLOT = cast(
    "MemberDescriptorType", _MatchContext.__dict__["index"]
)
_PLANNING_SOURCE_ROOT_SLOT = cast(
    "MemberDescriptorType", _PlanningContext.__dict__["source_root"]
)
_PLANNING_ORACLE_ROOT_SLOT = cast(
    "MemberDescriptorType", _PlanningContext.__dict__["oracle_root"]
)
_PLANNING_BY_PATH_SLOT = cast(
    "MemberDescriptorType", _PlanningContext.__dict__["source_by_path"]
)
_PLANNING_BY_CONTENT_SLOT = cast(
    "MemberDescriptorType", _PlanningContext.__dict__["source_by_content"]
)


def _match_source(context: _MatchContext) -> bytes:
    return cast("bytes", _MATCH_SOURCE_SLOT.__get__(context, _MatchContext))


def _match_target(context: _MatchContext) -> bytes:
    return cast("bytes", _MATCH_TARGET_SLOT.__get__(context, _MatchContext))


def _match_index(context: _MatchContext) -> dict[bytes, int]:
    return cast(
        "dict[bytes, int]", _MATCH_INDEX_SLOT.__get__(context, _MatchContext)
    )


def _planning_source_root(context: _PlanningContext) -> Path:
    return cast(
        "Path", _PLANNING_SOURCE_ROOT_SLOT.__get__(context, _PlanningContext)
    )


def _planning_oracle_root(context: _PlanningContext) -> Path:
    return cast(
        "Path", _PLANNING_ORACLE_ROOT_SLOT.__get__(context, _PlanningContext)
    )


def _planning_by_path(
    context: _PlanningContext,
) -> dict[str, FileRecord]:
    return cast(
        "dict[str, FileRecord]",
        _PLANNING_BY_PATH_SLOT.__get__(context, _PlanningContext),
    )


def _planning_by_content(
    context: _PlanningContext,
) -> dict[tuple[str, int], tuple[str, ...]]:
    return cast(
        "dict[tuple[str, int], tuple[str, ...]]",
        _PLANNING_BY_CONTENT_SLOT.__get__(context, _PlanningContext),
    )


def _native_path_inside(path: Path, root: Path) -> bool:
    """Check containment with the import-native pathlib method."""
    try:
        _ = _NATIVE_RELATIVE_TO(path, root)
    except ValueError:
        return False
    return True


def _sha256(data: bytes) -> str:
    return _native_sha256(data).hexdigest()


def _require_portable_path_label(value: object) -> str:
    """Admit one UTF-8 relative-path label before filesystem use.

    Returns:
        The unchanged path label.

    Raises:
        TreeModelError: The label is malformed or cannot encode as UTF-8.

    """
    if _NATIVE_TYPE(value) is not _NATIVE_STR or not value:
        message = f"invalid relative path: {value!r}"
        raise TreeModelError(message)
    if _BACKSLASH in value or _NUL in value:
        message = f"invalid relative path: {value!r}"
        raise TreeModelError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeEncodeError as error:
        message = f"invalid relative path: {value!r}"
        raise TreeModelError(message) from error
    return value


def _validate_relative_path(relative_path: str) -> str:
    """Validate and normalize one portable relative file path.

    Returns:
        The unchanged canonical POSIX-style relative path.

    Raises:
        TreeModelError: The path is empty, unsafe, or non-canonical.

    """
    admitted = _require_portable_path_label(relative_path)
    # Path metadata must not consult mutable ntpath or pathlib helpers.
    parts = admitted.split("/")
    if _NATIVE_ANY(part in _UNSAFE_PATH_PARTS for part in parts):
        message = f"relative path is not canonically normalized: {admitted!r}"
        raise TreeModelError(message)
    if _NATIVE_ANY(reserved_windows_component(part) for part in parts):
        message = f"unsafe relative path: {admitted!r}"
        raise TreeModelError(message)
    return admitted


def _normalized_roots(roots: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _NATIVE_TUPLE(_validate_relative_path(root) for root in roots)
    if normalized != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(normalized))):
        message = "passthrough roots must be unique and sorted"
        raise ExactTreeError(message)
    for index, root in _NATIVE_ENUMERATE(normalized):
        prefix = root + "/"
        if _NATIVE_ANY(
            other.startswith(prefix) for other in normalized[index + 1 :]
        ):
            message = "passthrough roots must not overlap"
            raise ExactTreeError(message)
    return normalized


def _path_in_roots(path: str, roots: tuple[str, ...]) -> bool:
    return _NATIVE_ANY(
        path == root or path.startswith(root + "/") for root in roots
    )


def _filter_snapshot(
    snapshot: TreeSnapshot,
    roots: tuple[str, ...],
    *,
    inside: bool,
) -> TreeSnapshot:
    return _new_tree_snapshot(
        files=_NATIVE_TUPLE(
            record
            for record in _snapshot_files(snapshot)
            if _path_in_roots(_file_fields(record)[0], roots) is inside
        )
    )


def _snapshots_match(left: TreeSnapshot, right: TreeSnapshot) -> bool:
    """Compare admitted file values, not replaceable record equality."""
    left_files = _NATIVE_TUPLE(
        _file_fields(record) for record in _snapshot_files(left)
    )
    right_files = _NATIVE_TUPLE(
        _file_fields(record) for record in _snapshot_files(right)
    )
    return left_files == right_files


def _raise_tree_walk_error(error: OSError | ValueError | RuntimeError) -> None:
    message = f"tree traversal failed: {_safe_host_error_detail(error)}"
    raise ExactTreeError(message) from error


def _walk_tree(
    root: Path,
) -> Iterator[tuple[Path, list[str], list[str]]]:
    _require_native_path_hooks()
    try:
        yield from _NATIVE_PATH_WALK(root, on_error=_raise_tree_walk_error)
    except ExactTreeError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        _raise_tree_walk_error(error)


def _tree_paths(root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in _walk_tree(root):
        paths.extend(directory / name for name in directories)
        paths.extend(directory / name for name in filenames)
    return _NATIVE_TUPLE(_NATIVE_SORTED(paths))


def _walk_relative_path(root: Path, path: Path) -> str:
    return _NATIVE_RELATIVE_TO(path, root).as_posix()


def _prune_excluded_directories(
    root: Path,
    directory: Path,
    directories: list[str],
    *,
    roots: tuple[str, ...],
) -> tuple[Path, ...]:
    admitted: list[Path] = []
    kept: list[str] = []
    for name in directories:
        path = directory / name
        if _path_in_roots(_walk_relative_path(root, path), roots):
            continue
        admitted.append(path)
        kept.append(name)
    directories[:] = kept
    return _NATIVE_TUPLE(admitted)


def _admitted_files(
    root: Path,
    directory: Path,
    filenames: list[str],
    *,
    roots: tuple[str, ...],
) -> tuple[Path, ...]:
    paths = (directory / name for name in filenames)
    return _NATIVE_TUPLE(
        path
        for path in paths
        if not _path_in_roots(_walk_relative_path(root, path), roots)
    )


def _tree_paths_excluding(
    root: Path, roots: tuple[str, ...]
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in _walk_tree(root):
        paths.extend(
            _prune_excluded_directories(
                root, directory, directories, roots=roots
            )
        )
        paths.extend(_admitted_files(root, directory, filenames, roots=roots))
    return _NATIVE_TUPLE(_NATIVE_SORTED(paths))


def _entry_mode(path: Path, context: str) -> int | None:
    _require_native_path_hooks()
    try:
        receipt = _NATIVE_PATH_LSTAT(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        message = f"{context} status failed: {_safe_host_error_detail(error)}"
        raise ExactTreeError(message) from error
    _ = _require_native_status(receipt, context)
    return receipt.st_mode


def _is_redirect(path: Path, mode: int) -> bool:
    try:
        if S_ISLNK(mode):
            return True
        is_junction = _NATIVE_PATH_IS_JUNCTION(path)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_host_error_detail(error)
        message = f"tree redirect status failed: {path}: {detail}"
        raise ExactTreeError(message) from error
    if _NATIVE_TYPE(is_junction) is not _NATIVE_BOOL:
        message = "tree redirect status requires native boolean"
        raise ExactTreeError(message)
    return is_junction


def _require_native_status(receipt: object, context: str) -> os.stat_result:
    """Require exact native file-status metadata at trust boundaries.

    Returns:
        The native host filesystem status receipt.

    Raises:
        ExactTreeError: The status is a fabricated or foreign record.

    """
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = f"{context} requires native filesystem status"
        raise ExactTreeError(message)
    return receipt


def _file_identity(status: os.stat_result) -> tuple[int, ...]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _admit_opened_file(
    descriptor: int, path: Path, context: str
) -> os.stat_result:
    opened = _require_native_status(os.fstat(descriptor), context)
    named = _require_native_status(_NATIVE_PATH_LSTAT(path), context)
    regular_identity = (
        S_ISREG(opened.st_mode)
        and S_ISREG(named.st_mode)
        and (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)
    )
    if not regular_identity or _is_redirect(path, named.st_mode):
        message = f"{context} read lost regular file identity: {path}"
        raise ExactTreeError(message)
    return opened


def _read_native_chunk(descriptor: int, count: int, context: str) -> bytes:
    """Require exact host byte receipts, including the EOF observation.

    Returns:
        A native byte string returned by the descriptor reader.

    Raises:
        ExactTreeError: The reader provided a foreign result.

    """
    chunk = os.read(descriptor, count)
    if _NATIVE_TYPE(chunk) is not _NATIVE_BYTES:
        message = f"{context} requires native read bytes"
        raise ExactTreeError(message)
    return chunk


def _read_admitted_descriptor(
    descriptor: int, length: int, context: str
) -> bytes:
    payload = _NATIVE_BYTEARRAY()
    while _NATIVE_LEN(payload) < length:
        requested = _NATIVE_MIN(
            _FILE_READ_CHUNK_BYTES, length - _NATIVE_LEN(payload)
        )
        chunk = _read_native_chunk(descriptor, requested, context)
        if not chunk or _NATIVE_LEN(chunk) > requested:
            message = f"{context} read did not match admitted byte length"
            raise ExactTreeError(message)
        payload.extend(chunk)
    if _read_native_chunk(descriptor, 1, context):
        message = f"{context} read exceeded admitted byte length"
        raise ExactTreeError(message)
    return _NATIVE_BYTES(payload)


def _safe_host_error_detail(error: BaseException) -> str:
    """Describe only exact native exception arguments without calling hooks.

    Returns:
        The native single-string reason or the exception's class name.

    """
    if _NATIVE_TYPE(error) in {
        ExactTreeError,
        OSError,
        ValueError,
        RuntimeError,
    }:
        arguments = cast("tuple[object, ...]", error.args)
        if (
            _NATIVE_LEN(arguments) == 1
            and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR
        ):
            return arguments[0]
        if _NATIVE_TYPE(error) is OSError and _NATIVE_LEN(arguments) > 1:
            reason = arguments[1]
            if _NATIVE_TYPE(reason) is _NATIVE_STR:
                return reason
    return _NATIVE_TYPE(error).__name__


def _verify_closed_source(
    path: Path, context: str, before_close: os.stat_result
) -> None:
    """Reject pathname replacement or metadata mutation after descriptor close.

    Raises:
        ExactTreeError: The closed source no longer matches its admitted inode.

    """
    # Finalizers may change or replace the named file after the last fstat.
    try:
        final = _NATIVE_PATH_LSTAT(path)
    except (OSError, ValueError, RuntimeError) as error:
        message = f"{context} status failed after descriptor close: {path}"
        raise ExactTreeError(message) from error
    final = _require_native_status(final, context)
    if (
        not S_ISREG(final.st_mode)
        or _is_redirect(path, final.st_mode)
        or _file_identity(before_close) != _file_identity(final)
    ):
        message = f"{context} source changed after descriptor close: {path}"
        raise ExactTreeError(message)


def _read_bound_file(path: Path, context: str) -> bytes:
    # Opening a directly supplied regular file via the native descriptor API
    # does not resolve a directory or path segment with os.fspath. Preserve
    # generator source replays when a domain replaces only that global hook.
    _require_native_path_hooks(direct_file_read=True)
    descriptor = os.open(path, _FILE_READ_FLAGS)
    try:
        before = _admit_opened_file(descriptor, path, context)
        payload = _read_admitted_descriptor(descriptor, before.st_size, context)
        after = _admit_opened_file(descriptor, path, context)
        if _file_identity(before) != _file_identity(after):
            message = f"{context} read inode changed during acquisition"
            raise ExactTreeError(message)
    finally:
        primary = sys.exception()
        try:
            os.close(descriptor)
        except BaseException as error:
            if primary is None:
                raise
            # Cleanup is secondary: never call foreign exception formatters or
            # an overridden primary.add_note hook while reporting the failure.
            BaseException.add_note(
                primary,
                "file descriptor close also failed: "
                + _safe_host_error_detail(error),
            )
    _verify_closed_source(path, context, after)
    return payload


def _copy_native_failure_notes(
    error: BaseException, failure: ExactTreeError
) -> None:
    """Copy trusted notes without invoking foreign exception accessors."""
    try:
        notes = cast(
            "object",
            # Direct native dispatch bypasses an overridden foreign accessor.
            BaseException.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
                error, "__notes__"
            ),
        )
    except AttributeError:
        return
    if _NATIVE_TYPE(notes) is list:
        for note in cast("list[object]", notes):
            if _NATIVE_TYPE(note) is _NATIVE_STR:
                BaseException.add_note(failure, note)


def read_exact_regular_file(path: Path, context: str) -> bytes:
    """Read from an admitted regular inode, never an opened FIFO or link.

    Returns:
        Exact file bytes from a path still bound to the opened inode.

    Raises:
        ExactTreeError: File identity, length, or content acquisition failed.

    """
    try:
        return _read_bound_file(path, context)
    except ExactTreeError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_host_error_detail(error)
        message = f"{context} read failed: {path}: {detail}"
        failure = ExactTreeError(message)
        _copy_native_failure_notes(error, failure)
        raise failure from error


def _record_file(root: Path, path: Path) -> FileRecord | None:
    mode = _entry_mode(path, "tree entry")
    if mode is None:
        message = f"tree entry disappeared during traversal: {path}"
        raise ExactTreeError(message)
    if _is_redirect(path, mode):
        message = f"symlinks are not supported: {path}"
        raise ExactTreeError(message)
    if S_ISDIR(mode):
        return None
    if not S_ISREG(mode):
        message = f"special filesystem entry is not supported: {path}"
        raise ExactTreeError(message)
    relative = _NATIVE_RELATIVE_TO(path, root).as_posix()
    relative_path = _validate_relative_path(relative)
    data = read_exact_regular_file(path, "tree entry")
    return _new_file_record(
        path=relative_path, sha256=_sha256(data), size=_NATIVE_LEN(data)
    )


def _require_filesystem_root(value: object, context: str) -> None:
    # Subclasses may override conversion, status or resolution to redirect I/O.
    # Admit only the native host path before calling any such method.
    if _NATIVE_TYPE(value) is not _NATIVE_PATH_TYPE:
        message = f"{context} must use an exact pathlib Path filesystem path"
        raise ExactTreeError(message)
    _require_native_path_hooks()
    raw = _NATIVE_PATH_STRING(value)
    if _NUL in raw:
        message = f"{context} must use a representable filesystem path"
        raise ExactTreeError(message)
    try:
        _ = raw.encode(_FILESYSTEM_ENCODING, _FILESYSTEM_ERRORS)
    except UnicodeError as error:
        message = f"{context} must use a representable filesystem path"
        raise ExactTreeError(message) from error


def _require_native_resolved_path(value: object, context: str) -> Path:
    """Reject a foreign path returned by a host resolution callback.

    Returns:
        The host-native resolved path.

    Raises:
        ExactTreeError: The resolution callback returned a foreign path.

    """
    if _NATIVE_TYPE(value) is not _NATIVE_TYPE(Path()):
        message = f"{context} resolution must return native Path"
        raise ExactTreeError(message)
    return value


def _resolved_tree_root(root: Path) -> Path:
    _require_filesystem_root(root, "tree root")
    mode = _entry_mode(root, "tree root")
    if mode is None:
        message = f"tree root is not a directory: {root}"
        raise ExactTreeError(message)
    if _is_redirect(root, mode):
        message = f"tree root must not be linked: {root}"
        raise ExactTreeError(message)
    if not S_ISDIR(mode):
        message = f"tree root is not a directory: {root}"
        raise ExactTreeError(message)
    try:
        resolved = _NATIVE_PATH_RESOLVE(root, strict=True)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_host_error_detail(error)
        message = f"tree root resolution failed: {root}: {detail}"
        raise ExactTreeError(message) from error
    return _require_native_resolved_path(resolved, "tree root")


def snapshot_tree(root: Path) -> TreeSnapshot:
    """Snapshot regular files under ``root`` in stable path order.

    Symlinks and special filesystem objects fail closed. Empty directories are
    outside the version-one model because they carry no byte content.

    Returns:
        A path-sorted regular-file snapshot.

    """
    resolved_root = _resolved_tree_root(root)
    records = (
        record
        for path in _tree_paths(resolved_root)
        if (record := _record_file(resolved_root, path)) is not None
    )
    return _new_tree_snapshot(files=_NATIVE_TUPLE(_NATIVE_SORTED(records)))


def snapshot_tree_excluding(
    root: Path,
    excluded_roots: tuple[str, ...],
) -> TreeSnapshot:
    """Snapshot one tree while excluding explicit root subtrees.

    Returns:
        Static snapshot containing no files under the excluded roots.

    """
    roots = _normalized_roots(excluded_roots)
    resolved_root = _resolved_tree_root(root)
    records = (
        record
        for path in _tree_paths_excluding(resolved_root, roots)
        if (record := _record_file(resolved_root, path)) is not None
    )
    return _new_tree_snapshot(files=_NATIVE_TUPLE(_NATIVE_SORTED(records)))


def _source_paths_by_content(
    source: TreeSnapshot,
) -> dict[tuple[str, int], tuple[str, ...]]:
    paths: dict[tuple[str, int], list[str]] = {}
    for record in _snapshot_files(source):
        path, digest, size = _file_fields(record)
        key = (digest, size)
        paths.setdefault(key, []).append(path)
    return {
        key: _NATIVE_TUPLE(_NATIVE_SORTED(value))
        for key, value in paths.items()
    }


def _tree_bytes(root: Path, relative_path: str) -> bytes:
    path = _NATIVE_PATH_JOINPATH(root, *relative_path.split("/"))
    return read_exact_regular_file(path, "tree file")


def _oracle_bytes(oracle_root: Path, target_record: FileRecord) -> bytes:
    path, digest, _ = _file_fields(target_record)
    literal = _tree_bytes(oracle_root, path)
    if _sha256(literal) != digest:
        message = f"oracle file changed while planning: {path}"
        raise ExactTreeError(message)
    return literal


def _block_index(source: bytes) -> dict[bytes, int]:
    last_start = _NATIVE_LEN(source) - _MATCH_BLOCK_BYTES
    if last_start < _ZERO:
        return {}
    offsets = _NATIVE_RANGE(_ZERO, last_start + 1, _MATCH_BLOCK_BYTES)
    index: dict[bytes, int] = {}
    for offset in offsets:
        block = source[offset : offset + _MATCH_BLOCK_BYTES]
        _ = index.setdefault(block, offset)
    return index


def _extend_match_backward(
    context: _MatchContext,
    source_offset: int,
    target_offset: int,
    *,
    literal_start: int,
) -> tuple[int, int]:
    while (
        source_offset > _ZERO
        and target_offset > literal_start
        and _match_source(context)[source_offset - 1]
        == _match_target(context)[target_offset - 1]
    ):
        source_offset -= 1
        target_offset -= 1
    return source_offset, target_offset


def _extend_match_forward(
    context: _MatchContext,
    source_offset: int,
    target_offset: int,
) -> int:
    length = _MATCH_BLOCK_BYTES
    while (
        source_offset + length < _NATIVE_LEN(_match_source(context))
        and target_offset + length < _NATIVE_LEN(_match_target(context))
        and _match_source(context)[source_offset + length]
        == _match_target(context)[target_offset + length]
    ):
        length += 1
    return length


def _matching_slice(
    context: _MatchContext,
    target_offset: int,
    literal_start: int,
) -> tuple[int, int, int] | None:
    block_end = target_offset + _MATCH_BLOCK_BYTES
    if block_end > _NATIVE_LEN(_match_target(context)):
        return None
    block = _match_target(context)[target_offset:block_end]
    source_offset = _match_index(context).get(block)
    if source_offset is None:
        return None
    source_offset, target_offset = _extend_match_backward(
        context,
        source_offset,
        target_offset,
        literal_start=literal_start,
    )
    length = _extend_match_forward(context, source_offset, target_offset)
    return source_offset, target_offset, length


def _append_literal(
    segments: list[ExactSegment],
    target: bytes,
    *,
    start: int,
    end: int,
) -> None:
    if end > start:
        segments.append(_new_oracle_literal(target[start:end]))


def _build_patch_segments(
    source: bytes, target: bytes
) -> tuple[ExactSegment, ...]:
    context = _new_match_context(
        source=source,
        target=target,
        index=_block_index(source),
    )
    if not _match_index(context):
        return (_new_oracle_literal(target),)
    segments: list[ExactSegment] = []
    literal_start = _ZERO
    cursor = _ZERO
    while cursor < _NATIVE_LEN(target):
        match = _matching_slice(context, cursor, literal_start)
        if match is None:
            cursor += 1
            continue
        source_offset, target_offset, length = match
        _append_literal(
            segments,
            target,
            start=literal_start,
            end=target_offset,
        )
        segments.append(_new_source_slice(offset=source_offset, length=length))
        cursor = target_offset + length
        literal_start = cursor
    _append_literal(
        segments,
        target,
        start=literal_start,
        end=_NATIVE_LEN(target),
    )
    return _NATIVE_TUPLE(segments)


def _contains_source_slice(segments: tuple[ExactSegment, ...]) -> bool:
    return _NATIVE_ANY(
        _NATIVE_ISINSTANCE(segment, SourceSlice) for segment in segments
    )


def _patch_instruction(
    source_root: Path,
    target_record: FileRecord,
    target_bytes: bytes,
) -> ExactInstruction:
    path, digest, _ = _file_fields(target_record)
    source_bytes = _tree_bytes(source_root, path)
    segments = _build_patch_segments(source_bytes, target_bytes)
    if _contains_source_slice(segments):
        return _new_exact_instruction(
            output_path=path,
            kind=ExactInstructionKind.PATCH_SOURCE,
            source_path=path,
            segments=segments,
            expected_sha256=digest,
        )
    return _new_exact_instruction(
        output_path=path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        literal=target_bytes,
        expected_sha256=digest,
    )


def _instruction_for_target(
    context: _PlanningContext,
    target_record: FileRecord,
) -> ExactInstruction:
    path, digest, size = _file_fields(target_record)
    key = (digest, size)
    candidates = _planning_by_content(context).get(key, ())
    if candidates:
        source_path = path if path in candidates else candidates[0]
        return _new_exact_instruction(
            output_path=path,
            kind=ExactInstructionKind.COPY_SOURCE,
            source_path=source_path,
            expected_sha256=digest,
        )
    target_bytes = _oracle_bytes(_planning_oracle_root(context), target_record)
    if path in _planning_by_path(context):
        return _patch_instruction(
            _planning_source_root(context),
            target_record,
            target_bytes,
        )
    return _new_exact_instruction(
        output_path=path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        literal=target_bytes,
        expected_sha256=digest,
    )


def build_exact_plan(
    source_root: Path,
    oracle_root: Path,
    *,
    passthrough_roots: tuple[str, ...] = (),
) -> ExactAuthoringPlan:
    """Build a deterministic exact-baseline plan from two local trees.

    Exact target bytes are represented by whole-file source copies, source
    slices plus local literals, or local literals when no source reuse exists.

    Returns:
        A deterministic, non-distributable authoring plan.

    Raises:
        ExactTreeError: Passthrough policy is invalid or differs at authoring.

    """
    roots = _normalized_roots(passthrough_roots)
    source_full = snapshot_tree(source_root)
    target_full = snapshot_tree(oracle_root)
    source_passthrough = _filter_snapshot(source_full, roots, inside=True)
    target_passthrough = _filter_snapshot(target_full, roots, inside=True)
    if not _snapshots_match(source_passthrough, target_passthrough):
        message = "passthrough roots differ between source and authoring oracle"
        raise ExactTreeError(message)
    source = _filter_snapshot(source_full, roots, inside=False)
    target = _filter_snapshot(target_full, roots, inside=False)
    context = _new_planning_context(
        source_root=source_root,
        oracle_root=oracle_root,
        source_by_path={
            _file_fields(record)[0]: record for record in _snapshot_files(source)
        },
        source_by_content=_source_paths_by_content(source),
    )
    instructions = _NATIVE_TUPLE(
        _instruction_for_target(context, record)
        for record in _snapshot_files(target)
    )
    if not _snapshots_match(snapshot_tree(source_root), source_full):
        message = "source tree changed while exact planning"
        raise ExactTreeError(message)
    if not _snapshots_match(snapshot_tree(oracle_root), target_full):
        message = "oracle tree changed while exact planning"
        raise ExactTreeError(message)
    return _new_exact_plan(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=roots,
    )


def _reject_linked_tree_ancestors(root: Path, relative_path: str) -> None:
    current = root
    for component in relative_path.split("/")[:-1]:
        current = _NATIVE_PATH_JOINPATH(current, component)
        mode = _entry_mode(current, "tree path component")
        if mode is not None and _is_redirect(current, mode):
            message = f"linked tree path component is not supported: {current}"
            raise ExactTreeError(message)


def _safe_tree_path(root: Path, relative_path: str) -> Path:
    _require_native_path_hooks()
    normalized = _validate_relative_path(relative_path)
    path = _NATIVE_PATH_JOINPATH(root, *normalized.split("/"))
    try:
        resolved_path = _require_native_resolved_path(
            _NATIVE_PATH_RESOLVE(path), "tree path"
        )
        resolved_root = _require_native_resolved_path(
            _NATIVE_PATH_RESOLVE(root), "tree root"
        )
    except (OSError, ValueError, RuntimeError) as error:
        message = (
            "tree path resolution failed: "
            f"{relative_path!r}: {_safe_host_error_detail(error)}"
        )
        raise ExactTreeError(message) from error
    try:
        _ = _NATIVE_RELATIVE_TO(resolved_path, resolved_root)
    except ValueError as error:
        message = f"path escapes tree root: {relative_path!r}"
        raise ExactTreeError(message) from error
    _reject_linked_tree_ancestors(root, normalized)
    return path


def _patch_bytes(source: bytes, segments: tuple[ExactSegment, ...]) -> bytes:
    parts: list[bytes] = []
    for segment in segments:
        if _NATIVE_TYPE(segment) is OracleLiteral:
            parts.append(_oracle_literal_data(segment))
            continue
        offset, length = _source_slice_fields(cast("SourceSlice", segment))
        end = offset + length
        if end > _NATIVE_LEN(source):
            message = "source slice exceeds source file"
            raise ExactTreeError(message)
        parts.append(source[offset:end])
    return b"".join(parts)


def _instruction_bytes(
    source_root: Path,
    instruction: ExactInstruction,
) -> bytes:
    _, kind, _, source_path, literal, segments = _instruction_fields(instruction)
    if kind is ExactInstructionKind.LITERAL_ORACLE:
        if literal is None:
            message = "literal-oracle instruction lost its literal bytes"
            raise ExactTreeError(message)
        return literal
    if source_path is None:
        message = "source-backed instruction lost its source path"
        raise ExactTreeError(message)
    source = read_exact_regular_file(
        _safe_tree_path(source_root, source_path), "instruction source"
    )
    if kind is ExactInstructionKind.COPY_SOURCE:
        return source
    return _patch_bytes(source, segments)


def _native_write_output_bytes(path: Path, data: bytes) -> int:
    """Create one staged file through the import-pinned native file writer."""
    _require_native_path_hooks()
    with _NATIVE_IO_OPEN(_NATIVE_PATH_STRING(path), "xb") as stream:
        return stream.write(data)


_NATIVE_WRITE_OUTPUT_BYTES = _native_write_output_bytes


def _native_make_output_directory(path: Path, *, parents: bool, exist_ok: bool) -> None:
    """Create output directories without later class or os.mkdir hooks."""
    _require_native_path_hooks()
    try:
        _NATIVE_OS_MKDIR(_NATIVE_PATH_STRING(path))
    except FileNotFoundError:
        parent = _NATIVE_PATH_PARENT(path)
        if not parents or _NATIVE_PATH_STRING(parent) == _NATIVE_PATH_STRING(path):
            raise
        _native_make_output_directory(parent, parents=True, exist_ok=True)
        _native_make_output_directory(path, parents=False, exist_ok=exist_ok)
    except OSError:
        if not exist_ok:
            raise
        mode = _entry_mode(path, "output directory")
        if mode is None or not S_ISDIR(mode) or _is_redirect(path, mode):
            raise


def _write_output_file(path: Path, data: bytes, context: str) -> None:
    try:
        _native_make_output_directory(
            _NATIVE_PATH_PARENT(path), parents=True, exist_ok=True
        )
        written = _NATIVE_WRITE_OUTPUT_BYTES(path, data)
    except (OSError, ValueError, RuntimeError) as error:
        message = f"{context} write failed: {path}: " + _safe_host_error_detail(
            error
        )
        raise ExactTreeError(message) from error
    if _NATIVE_TYPE(written) is not _NATIVE_INT or written != _NATIVE_LEN(data):
        message = f"{context} short or invalid byte count: {path}"
        raise ExactTreeError(message)


def _make_output_directory(
    path: Path,
    context: str,
    *,
    parents: bool,
    exist_ok: bool,
) -> None:
    try:
        _native_make_output_directory(path, parents=parents, exist_ok=exist_ok)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_host_error_detail(error)
        message = f"{context} creation failed: {path}: {detail}"
        raise ExactTreeError(message) from error


def _write_instruction(
    source_root: Path,
    staging_root: Path,
    instruction: ExactInstruction,
) -> None:
    data = _instruction_bytes(source_root, instruction)
    output_label, _, digest, _, _, _ = _instruction_fields(instruction)
    if _sha256(data) != digest:
        message = (
            "instruction bytes do not match expected hash for "
            f"{output_label}"
        )
        raise ExactTreeError(message)
    output_path = _safe_tree_path(staging_root, output_label)
    _write_output_file(output_path, data, "instruction output")


def _verify_source(source_root: Path, plan: ExactAuthoringPlan) -> None:
    source, _, _, roots = _plan_fields(plan)
    current = snapshot_tree_excluding(source_root, roots)
    if not _snapshots_match(current, source):
        message = "source tree does not match exact authoring snapshot"
        raise ExactTreeError(message)


def _prepare_staging(output_root: Path) -> Path:
    if _entry_mode(output_root, "output root") is not None:
        message = f"output root already exists: {output_root}"
        raise ExactTreeError(message)
    staging_name = f".{_NATIVE_PATH_NAME(output_root)}{_STAGING_SUFFIX}"
    staging_root = _NATIVE_PATH_JOINPATH(_NATIVE_PATH_PARENT(output_root), staging_name)
    if _entry_mode(staging_root, "staging root") is not None:
        message = f"staging root already exists: {staging_root}"
        raise ExactTreeError(message)
    _make_output_directory(
        _NATIVE_PATH_PARENT(output_root),
        "output parent",
        parents=True,
        exist_ok=True,
    )
    _make_output_directory(
        staging_root,
        "staging root",
        parents=False,
        exist_ok=False,
    )
    return staging_root


def _copy_passthrough_file(source: Path, target: Path) -> None:
    data = read_exact_regular_file(source, "passthrough file")
    _write_output_file(target, data, "passthrough output")


def _copy_passthrough_entry(
    staging_root: Path, path: Path, relative: str
) -> None:
    mode = _entry_mode(path, "passthrough entry")
    if mode is None:
        message = f"passthrough entry disappeared: {relative}"
        raise ExactTreeError(message)
    if _is_redirect(path, mode):
        message = f"symlink is not supported in passthrough root: {relative}"
        raise ExactTreeError(message)
    output = _safe_tree_path(staging_root, relative)
    if S_ISDIR(mode):
        _make_output_directory(
            output,
            "passthrough directory",
            parents=True,
            exist_ok=True,
        )
    elif S_ISREG(mode):
        _copy_passthrough_file(path, output)
    else:
        message = f"special passthrough entry is not supported: {relative}"
        raise ExactTreeError(message)


def _copy_passthrough_directory(
    source_root: Path,
    staging_root: Path,
    source: Path,
) -> None:
    for path in _tree_paths(source):
        relative = _NATIVE_RELATIVE_TO(path, source_root).as_posix()
        _copy_passthrough_entry(staging_root, path, relative)


def _copy_passthrough_root(
    source_root: Path,
    staging_root: Path,
    relative_root: str,
) -> None:
    source = _safe_tree_path(source_root, relative_root)
    target = _safe_tree_path(staging_root, relative_root)
    mode = _entry_mode(source, "passthrough root")
    if mode is None:
        message = f"missing passthrough root: {relative_root}"
        raise ExactTreeError(message)
    if _is_redirect(source, mode):
        message = (
            f"symlink is not supported in passthrough root: {relative_root}"
        )
        raise ExactTreeError(message)
    if S_ISREG(mode):
        _copy_passthrough_file(source, target)
        return
    if S_ISDIR(mode):
        _make_output_directory(
            target,
            "passthrough root directory",
            parents=True,
            exist_ok=True,
        )
        _copy_passthrough_directory(source_root, staging_root, source)
        return
    message = f"special passthrough entry is not supported: {relative_root}"
    raise ExactTreeError(message)


def _copy_passthrough_roots(
    source_root: Path,
    staging_root: Path,
    roots: tuple[str, ...],
) -> None:
    for root in roots:
        _copy_passthrough_root(source_root, staging_root, root)


def _populate_staging(
    source_root: Path,
    staging_root: Path,
    plan: ExactAuthoringPlan,
) -> None:
    _, target, instructions, roots = _plan_fields(plan)
    for instruction in instructions:
        _write_instruction(source_root, staging_root, instruction)
    _copy_passthrough_roots(source_root, staging_root, roots)
    static_output = _filter_snapshot(
        snapshot_tree(staging_root), roots, inside=False
    )
    if not _snapshots_match(static_output, target):
        message = "materialized tree does not match target snapshot"
        raise ExactTreeError(message)


def _resolved_output_root(output_root: Path) -> Path:
    _require_filesystem_root(output_root, "output root")
    mode = _entry_mode(output_root, "output root")
    if mode is not None and _is_redirect(output_root, mode):
        message = f"output root must not be linked: {output_root}"
        raise ExactTreeError(message)
    try:
        resolved = _NATIVE_PATH_RESOLVE(output_root)
    except (OSError, ValueError, RuntimeError) as error:
        message = (
            "output root resolution failed: "
            f"{output_root}: {_safe_host_error_detail(error)}"
        )
        raise ExactTreeError(message) from error
    return _require_native_resolved_path(resolved, "output root")


def _cleanup_exact_staging(path: Path) -> str | None:
    try:
        _NATIVE_RMTREE(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        return _safe_host_error_detail(error)
    return None


def _raise_exact_cleanup_failure(error: Exception, cleanup_error: str) -> None:
    message = (
        _safe_host_error_detail(error)
        + f"; staging cleanup failed: {cleanup_error}"
    )
    raise ExactTreeError(message) from error


def _publish_exact_output(staging: Path, destination: Path) -> None:
    try:
        publish_directory_no_replace(staging, destination)
    except OSError as error:
        message = "exact output publication failed: " + _safe_host_error_detail(
            error
        )
        raise ExactTreeError(message) from error


def materialize_exact_plan(
    source_root: Path,
    plan: ExactAuthoringPlan,
    output_root: Path,
) -> None:
    """Verify an exact plan completely before publishing its output tree.

    The candidate source must match the authoring snapshot exactly. Fuzzy
    admission belongs to later layers.

    Raises:
        ExactTreeError: The source is invalid or the output is not separate.

    """
    if _NATIVE_TYPE(plan) is not ExactAuthoringPlan:
        message = "exact materialization requires an exact authoring plan"
        raise ExactTreeError(message)
    # Native slotted plans can be allocated without construction. Revalidate
    # their nested immutable evidence before any filesystem or staging access.
    try:
        _EXACT_PLAN_VALIDATOR(plan)
    except AttributeError as error:
        message = "exact materialization received an incomplete native authoring plan"
        raise TreeModelError(message) from error
    resolved_source = _resolved_tree_root(source_root)
    resolved_output = _resolved_output_root(output_root)
    if _native_path_inside(resolved_output, resolved_source):
        message = "exact output root must not be inside the source tree"
        raise ExactTreeError(message)
    _verify_source(resolved_source, plan)
    staging_root = _prepare_staging(resolved_output)
    try:
        _populate_staging(resolved_source, staging_root, plan)
        _verify_source(resolved_source, plan)
        _publish_exact_output(staging_root, resolved_output)
    except Exception as error:
        cleanup_error = _cleanup_exact_staging(staging_root)
        if cleanup_error is not None:
            _raise_exact_cleanup_failure(error, cleanup_error)
        raise
