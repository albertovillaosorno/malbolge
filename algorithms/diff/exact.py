# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Exact deterministic tree planning and materialization for authoring."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import shutil
from typing import TYPE_CHECKING

from algorithms.diff.model import ExactAuthoringPlan
from algorithms.diff.model import ExactInstruction
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import FileRecord
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.model import TreeModelError
from algorithms.diff.model import TreeSnapshot

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.model import ExactSegment

_BACKSLASH = "\\"
_UNSAFE_PATH_PARTS = frozenset({"", ".", ".."})
_STAGING_SUFFIX = ".staging"
_MATCH_BLOCK_BYTES = 32
_ZERO = 0


class ExactTreeError(RuntimeError):
    """Raised when exact planning or materialization cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class _MatchContext:
    """Immutable byte-matching inputs shared across one file diff."""

    source: bytes
    target: bytes
    index: dict[bytes, int]


@dataclass(frozen=True, slots=True)
class _PlanningContext:
    """Immutable tree indexes shared across target-file planning."""

    source_root: Path
    oracle_root: Path
    source_by_path: dict[str, FileRecord]
    source_by_content: dict[tuple[str, int], tuple[str, ...]]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_relative_path(relative_path: str) -> str:
    """Validate and normalize one portable relative file path.

    Returns:
        The unchanged canonical POSIX-style relative path.

    Raises:
        TreeModelError: The path is empty, unsafe, or non-canonical.

    """
    if not relative_path or _BACKSLASH in relative_path:
        message = f"invalid relative path: {relative_path!r}"
        raise TreeModelError(message)
    candidate = PurePosixPath(relative_path)
    unsafe_part = any(part in _UNSAFE_PATH_PARTS for part in candidate.parts)
    if candidate.is_absolute() or unsafe_part:
        message = f"unsafe relative path: {relative_path!r}"
        raise TreeModelError(message)
    normalized = candidate.as_posix()
    if normalized != relative_path:
        message = (
            f"relative path is not canonically normalized: {relative_path!r}"
        )
        raise TreeModelError(message)
    return normalized


def _record_file(root: Path, path: Path) -> FileRecord | None:
    if path.is_symlink():
        message = f"symlinks are not supported: {path}"
        raise ExactTreeError(message)
    if path.is_dir():
        return None
    if not path.is_file():
        message = f"special filesystem entry is not supported: {path}"
        raise ExactTreeError(message)
    relative = path.relative_to(root).as_posix()
    relative_path = _validate_relative_path(relative)
    data = path.read_bytes()
    return FileRecord(path=relative_path, sha256=_sha256(data), size=len(data))


def snapshot_tree(root: Path) -> TreeSnapshot:
    """Snapshot regular files under ``root`` in stable path order.

    Symlinks and special filesystem objects fail closed. Empty directories are
    outside the version-one model because they carry no byte content.

    Returns:
        A path-sorted regular-file snapshot.

    Raises:
        ExactTreeError: The root or one of its entries is unsupported.

    """
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        message = f"tree root is not a directory: {resolved_root}"
        raise ExactTreeError(message)
    records = (
        record
        for path in resolved_root.rglob("*")
        if (record := _record_file(resolved_root, path)) is not None
    )
    return TreeSnapshot(files=tuple(sorted(records)))


def _source_paths_by_content(
    source: TreeSnapshot,
) -> dict[tuple[str, int], tuple[str, ...]]:
    paths: dict[tuple[str, int], list[str]] = {}
    for record in source.files:
        key = (record.sha256, record.size)
        paths.setdefault(key, []).append(record.path)
    return {key: tuple(sorted(value)) for key, value in paths.items()}


def _tree_bytes(root: Path, relative_path: str) -> bytes:
    relative = PurePosixPath(relative_path)
    return root.joinpath(*relative.parts).read_bytes()


def _oracle_bytes(oracle_root: Path, target_record: FileRecord) -> bytes:
    literal = _tree_bytes(oracle_root, target_record.path)
    if _sha256(literal) != target_record.sha256:
        message = f"oracle file changed while planning: {target_record.path}"
        raise ExactTreeError(message)
    return literal


def _block_index(source: bytes) -> dict[bytes, int]:
    last_start = len(source) - _MATCH_BLOCK_BYTES
    if last_start < _ZERO:
        return {}
    offsets = range(_ZERO, last_start + 1, _MATCH_BLOCK_BYTES)
    index: dict[bytes, int] = {}
    for offset in offsets:
        block = source[offset : offset + _MATCH_BLOCK_BYTES]
        index.setdefault(block, offset)
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
        and context.source[source_offset - 1]
        == context.target[target_offset - 1]
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
        source_offset + length < len(context.source)
        and target_offset + length < len(context.target)
        and context.source[source_offset + length]
        == context.target[target_offset + length]
    ):
        length += 1
    return length


def _matching_slice(
    context: _MatchContext,
    target_offset: int,
    literal_start: int,
) -> tuple[int, int, int] | None:
    block_end = target_offset + _MATCH_BLOCK_BYTES
    if block_end > len(context.target):
        return None
    block = context.target[target_offset:block_end]
    source_offset = context.index.get(block)
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
        segments.append(OracleLiteral(target[start:end]))


def _build_patch_segments(
    source: bytes, target: bytes
) -> tuple[ExactSegment, ...]:
    context = _MatchContext(
        source=source,
        target=target,
        index=_block_index(source),
    )
    if not context.index:
        return (OracleLiteral(target),)
    segments: list[ExactSegment] = []
    literal_start = _ZERO
    cursor = _ZERO
    while cursor < len(target):
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
        segments.append(SourceSlice(offset=source_offset, length=length))
        cursor = target_offset + length
        literal_start = cursor
    _append_literal(
        segments,
        target,
        start=literal_start,
        end=len(target),
    )
    return tuple(segments)


def _contains_source_slice(segments: tuple[ExactSegment, ...]) -> bool:
    return any(isinstance(segment, SourceSlice) for segment in segments)


def _patch_instruction(
    source_root: Path,
    target_record: FileRecord,
    target_bytes: bytes,
) -> ExactInstruction:
    source_bytes = _tree_bytes(source_root, target_record.path)
    segments = _build_patch_segments(source_bytes, target_bytes)
    if _contains_source_slice(segments):
        return ExactInstruction(
            output_path=target_record.path,
            kind=ExactInstructionKind.PATCH_SOURCE,
            source_path=target_record.path,
            segments=segments,
            expected_sha256=target_record.sha256,
        )
    return ExactInstruction(
        output_path=target_record.path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        literal=target_bytes,
        expected_sha256=target_record.sha256,
    )


def _instruction_for_target(
    context: _PlanningContext,
    target_record: FileRecord,
) -> ExactInstruction:
    key = (target_record.sha256, target_record.size)
    candidates = context.source_by_content.get(key, ())
    if candidates:
        source_path = (
            target_record.path
            if target_record.path in candidates
            else candidates[0]
        )
        return ExactInstruction(
            output_path=target_record.path,
            kind=ExactInstructionKind.COPY_SOURCE,
            source_path=source_path,
            expected_sha256=target_record.sha256,
        )
    target_bytes = _oracle_bytes(context.oracle_root, target_record)
    if target_record.path in context.source_by_path:
        return _patch_instruction(
            context.source_root,
            target_record,
            target_bytes,
        )
    return ExactInstruction(
        output_path=target_record.path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        literal=target_bytes,
        expected_sha256=target_record.sha256,
    )


def build_exact_plan(
    source_root: Path,
    oracle_root: Path,
) -> ExactAuthoringPlan:
    """Build a deterministic exact-baseline plan from two local trees.

    Exact target bytes are represented by whole-file source copies, source
    slices plus local literals, or local literals when no source reuse exists.

    Returns:
        A deterministic, non-distributable authoring plan.

    """
    source = snapshot_tree(source_root)
    target = snapshot_tree(oracle_root)
    context = _PlanningContext(
        source_root=source_root,
        oracle_root=oracle_root,
        source_by_path={record.path: record for record in source.files},
        source_by_content=_source_paths_by_content(source),
    )
    instructions = tuple(
        _instruction_for_target(context, record) for record in target.files
    )
    return ExactAuthoringPlan(
        source=source,
        target=target,
        instructions=instructions,
    )


def _safe_tree_path(root: Path, relative_path: str) -> Path:
    normalized = _validate_relative_path(relative_path)
    path = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        message = f"path escapes tree root: {relative_path!r}"
        raise ExactTreeError(message) from exc
    return path


def _patch_bytes(source: bytes, segments: tuple[ExactSegment, ...]) -> bytes:
    parts: list[bytes] = []
    for segment in segments:
        if isinstance(segment, OracleLiteral):
            parts.append(segment.data)
            continue
        end = segment.offset + segment.length
        if end > len(source):
            message = "source slice exceeds source file"
            raise ExactTreeError(message)
        parts.append(source[segment.offset : end])
    return b"".join(parts)


def _instruction_bytes(
    source_root: Path,
    instruction: ExactInstruction,
) -> bytes:
    if instruction.kind is ExactInstructionKind.LITERAL_ORACLE:
        if instruction.literal is None:
            message = "literal-oracle instruction lost its literal bytes"
            raise ExactTreeError(message)
        return instruction.literal
    if instruction.source_path is None:
        message = "source-backed instruction lost its source path"
        raise ExactTreeError(message)
    source_path = _safe_tree_path(source_root, instruction.source_path)
    source = source_path.read_bytes()
    if instruction.kind is ExactInstructionKind.COPY_SOURCE:
        return source
    return _patch_bytes(source, instruction.segments)


def _write_instruction(
    source_root: Path,
    staging_root: Path,
    instruction: ExactInstruction,
) -> None:
    data = _instruction_bytes(source_root, instruction)
    if _sha256(data) != instruction.expected_sha256:
        message = (
            "instruction bytes do not match expected hash for "
            f"{instruction.output_path}"
        )
        raise ExactTreeError(message)
    output_path = _safe_tree_path(staging_root, instruction.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


def _verify_source(source_root: Path, plan: ExactAuthoringPlan) -> None:
    if snapshot_tree(source_root) != plan.source:
        message = "source tree does not match exact authoring snapshot"
        raise ExactTreeError(message)


def _prepare_staging(output_root: Path) -> Path:
    if output_root.exists():
        message = f"output root already exists: {output_root}"
        raise ExactTreeError(message)
    staging_name = f".{output_root.name}{_STAGING_SUFFIX}"
    staging_root = output_root.with_name(staging_name)
    if staging_root.exists():
        message = f"staging root already exists: {staging_root}"
        raise ExactTreeError(message)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir()
    return staging_root


def _populate_staging(
    source_root: Path,
    staging_root: Path,
    plan: ExactAuthoringPlan,
) -> None:
    for instruction in plan.instructions:
        _write_instruction(source_root, staging_root, instruction)
    if snapshot_tree(staging_root) != plan.target:
        message = "materialized tree does not match target snapshot"
        raise ExactTreeError(message)


def materialize_exact_plan(
    source_root: Path,
    plan: ExactAuthoringPlan,
    output_root: Path,
) -> None:
    """Verify an exact plan completely before publishing its output tree.

    The candidate source must match the authoring snapshot exactly. Fuzzy
    admission belongs to later layers.
    """
    resolved_source = source_root.resolve()
    resolved_output = output_root.resolve()
    _verify_source(resolved_source, plan)
    staging_root = _prepare_staging(resolved_output)
    try:
        _populate_staging(resolved_source, staging_root, plan)
        staging_root.replace(resolved_output)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
