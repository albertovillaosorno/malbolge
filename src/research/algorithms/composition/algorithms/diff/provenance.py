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
#   - Deterministic source-tree pins for exact revision provenance.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Deterministic source-tree pins for exact revision provenance."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
from typing import cast

from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import read_exact_regular_file

_ZERO = 0
_ONE = 1
_FRAME_BYTES = 8
_DOMAIN = b"malbolge-pinned-source-v1\0"
_PARENT = ".."
_DOT = "."
_BACKSLASH = "\\"
_NUL = "\x00"
_COMMIT_HEX_LENGTH = 40
_SHA256_HEX_LENGTH = 64
_LOWER_HEX = frozenset("0123456789abcdef")


class SourcePinError(RuntimeError):
    """Raised when a local source tree does not satisfy its pinned snapshot."""


@dataclass(frozen=True, slots=True)
class SourcePin:
    """Externally named revision plus locally verifiable snapshot identity."""

    repository: str
    commit: str
    roots: tuple[str, ...]
    file_count: int
    snapshot_sha256: str

    def __post_init__(self) -> None:
        """Reject malformed source-pin metadata."""
        _validate_repository(self.repository)
        _validate_commit(self.commit)
        _validate_file_count(self.file_count)
        _validate_snapshot_sha256(self.snapshot_sha256)
        _validate_roots(self.roots)


def _validate_repository(repository: object) -> None:
    if type(repository) is not str or not repository:
        message = "source pin repository must be a non-empty string"
        raise SourcePinError(message)
    if _NUL in repository:
        message = "source pin repository must not contain NUL"
        raise SourcePinError(message)
    try:
        _ = repository.encode("utf-8")
    except UnicodeError as error:
        message = "source pin repository must be UTF-8 encodable"
        raise SourcePinError(message) from error


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(char in _LOWER_HEX for char in value)


def _validate_commit(commit: object) -> None:
    if type(commit) is not str or not _is_lower_hex(commit, _COMMIT_HEX_LENGTH):
        message = (
            "source pin commit must be 40 lowercase hexadecimal characters"
        )
        raise SourcePinError(message)


def _validate_file_count(file_count: object) -> None:
    if type(file_count) is not int or file_count < _ONE:
        message = "source pin file_count must be a positive integer"
        raise SourcePinError(message)


def _validate_snapshot_sha256(snapshot_sha256: object) -> None:
    if type(snapshot_sha256) is not str or not _is_lower_hex(
        snapshot_sha256, _SHA256_HEX_LENGTH
    ):
        message = "source pin snapshot_sha256 must be lowercase SHA-256"
        raise SourcePinError(message)


def _validate_roots(roots: object) -> None:
    if type(roots) is not tuple:
        message = "source pin roots must use the exact immutable tuple type"
        raise SourcePinError(message)
    items = cast("tuple[object, ...]", roots)
    if any(type(root) is not str for root in items):
        message = "source pin roots must contain exact string paths"
        raise SourcePinError(message)
    string_roots = cast("tuple[str, ...]", roots)
    if not string_roots or string_roots != tuple(sorted(set(string_roots))):
        message = "source pin roots must be unique and sorted"
        raise SourcePinError(message)
    _require_disjoint_roots(string_roots)


def _require_disjoint_roots(roots: tuple[str, ...]) -> None:
    selected: set[str] = set()
    for root in roots:
        _ = _validate_relative_path(root)
        parents = PurePosixPath(root).parents
        if any(parent.as_posix() in selected for parent in parents):
            message = "source pin roots must not overlap"
            raise SourcePinError(message)
        selected.add(root)


@dataclass(frozen=True, slots=True)
class SourcePinEvidence:
    """Observed deterministic snapshot for one pinned local source tree."""

    file_count: int
    snapshot_sha256: str

    def __post_init__(self) -> None:
        """Reject malformed observed source-pin evidence."""
        _validate_file_count(self.file_count)
        _validate_snapshot_sha256(self.snapshot_sha256)


def _u64(value: int) -> bytes:
    return value.to_bytes(_FRAME_BYTES, byteorder="big", signed=False)


def _frame(value: bytes) -> bytes:
    return _u64(len(value)) + value


def _utf8_pinned_path(path: str) -> bytes:
    try:
        return path.encode("utf-8")
    except UnicodeError as error:
        message = "pinned source paths must be UTF-8 encodable"
        raise SourcePinError(message) from error


def _validate_relative_path(relative_path: object) -> str:
    if type(relative_path) is not str:
        message = "pinned source path must use the exact string type"
        raise SourcePinError(message)
    candidate = PurePosixPath(relative_path)
    unsafe = (
        not relative_path
        or _BACKSLASH in relative_path
        or _NUL in relative_path
        or relative_path == _DOT
        or candidate.is_absolute()
        or bool(PureWindowsPath(relative_path).drive)
        or _PARENT in candidate.parts
        or candidate.as_posix() != relative_path
    )
    if unsafe:
        message = f"unsafe pinned source path: {relative_path!r}"
        raise SourcePinError(message)
    _ = _utf8_pinned_path(relative_path)
    return relative_path


def _source_mode(path: Path, relative: str) -> int | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        message = f"pinned source status failed for {relative}: {error}"
        raise SourcePinError(message) from error
    if S_ISLNK(mode) or path.is_junction():
        message = f"symlink is not accepted in pinned source: {relative}"
        raise SourcePinError(message)
    return mode


def _require_unlinked_parent_components(root: Path, relative: str) -> None:
    current = root
    for component in PurePosixPath(relative).parts[:-1]:
        current /= component
        label = current.relative_to(root).as_posix()
        mode = _source_mode(current, label)
        if mode is None or not S_ISDIR(mode):
            message = f"pinned source parent must be a directory: {label}"
            raise SourcePinError(message)


def _selected_root(root: Path, relative_root: str) -> tuple[Path, int]:
    _require_unlinked_parent_components(root, relative_root)
    selected = root.joinpath(*PurePosixPath(relative_root).parts)
    mode = _source_mode(selected, relative_root)
    if mode is None:
        message = f"missing pinned source root: {relative_root}"
        raise SourcePinError(message)
    if S_ISREG(mode) or S_ISDIR(mode):
        return selected, mode
    message = f"special entry is not accepted in pinned source: {relative_root}"
    raise SourcePinError(message)


def _raise_source_walk_error(error: OSError) -> None:
    message = f"pinned source traversal failed: {error}"
    raise SourcePinError(message) from error


def _directory_paths(selected: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in selected.walk(
        on_error=_raise_source_walk_error
    ):
        paths.extend(directory / name for name in directories)
        paths.extend(directory / name for name in filenames)
    return tuple(sorted(paths))


def _directory_files(root: Path, selected: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in _directory_paths(selected):
        relative = path.relative_to(root).as_posix()
        mode = _source_mode(path, relative)
        if mode is None:
            message = f"pinned source entry disappeared: {relative}"
            raise SourcePinError(message)
        if S_ISREG(mode):
            files.append(path)
            continue
        if not S_ISDIR(mode):
            message = (
                f"special entry is not accepted in pinned source: {relative}"
            )
            raise SourcePinError(message)
    return tuple(files)


def _collect_root(root: Path, relative_root: str) -> tuple[Path, ...]:
    selected, mode = _selected_root(root, relative_root)
    if S_ISREG(mode):
        return (selected,)
    return _directory_files(root, selected)


def _pinned_files(root: Path, roots: tuple[str, ...]) -> tuple[Path, ...]:
    files = tuple(
        path for relative in roots for path in _collect_root(root, relative)
    )
    unique = {path.relative_to(root).as_posix() for path in files}
    if len(unique) != len(files):
        message = "pinned source roots overlap"
        raise SourcePinError(message)
    return tuple(
        sorted(files, key=lambda path: path.relative_to(root).as_posix())
    )


def _validate_root_path(root: object) -> None:
    if not isinstance(root, Path):
        message = "pinned source root must use a pathlib Path value"
        raise SourcePinError(message)
    raw = str(root)
    if _NUL in raw:
        message = "pinned source root path must not contain NUL"
        raise SourcePinError(message)
    try:
        _ = raw.encode("utf-8")
        _ = os.fsencode(root)
    except UnicodeError as error:
        message = "pinned source root path must be filesystem-encodable"
        raise SourcePinError(message) from error


def _resolved_source_root(root: Path) -> Path:
    mode = _source_mode(root, ".")
    if mode is None or not S_ISDIR(mode):
        message = f"pinned source root must be a directory: {root}"
        raise SourcePinError(message)
    try:
        return root.resolve(strict=True)
    except (OSError, ValueError, RuntimeError) as error:
        message = f"pinned source root resolution failed: {root}: {error}"
        raise SourcePinError(message) from error


def _read_pinned_source(root: Path, path: Path, relative: str) -> bytes:
    _require_unlinked_parent_components(root, relative)
    try:
        return read_exact_regular_file(path, "pinned source")
    except ExactTreeError as error:
        message = f"pinned source read failed for {relative}: {error}"
        failure = SourcePinError(message)
        for note in cast("list[str]", getattr(error, "__notes__", [])):
            failure.add_note(note)
        raise failure from error


def source_snapshot_evidence(
    root: Path, roots: tuple[str, ...]
) -> SourcePinEvidence:
    """Hash selected source roots by normalized path and exact file bytes.

    Returns:
        Deterministic count and SHA-256 snapshot evidence.

    """
    _validate_root_path(root)
    _validate_roots(roots)
    digest = hashlib.sha256()
    digest.update(_DOMAIN)
    resolved_root = _resolved_source_root(root)
    files = _pinned_files(resolved_root, roots)
    digest.update(_u64(len(files)))
    for path in files:
        relative_text = path.relative_to(resolved_root).as_posix()
        relative = _utf8_pinned_path(relative_text)
        data = _read_pinned_source(resolved_root, path, relative_text)
        digest.update(_frame(relative))
        digest.update(_frame(hashlib.sha256(data).digest()))
    return SourcePinEvidence(
        file_count=len(files),
        snapshot_sha256=digest.hexdigest(),
    )


def require_source_pin(root: Path, pin: SourcePin) -> SourcePinEvidence:
    """Require exact selected-tree identity for a named external revision.

    Returns:
        Matching local snapshot evidence.

    Raises:
        SourcePinError: File count or snapshot digest differs from the pin.

    """
    if type(pin) is not SourcePin:
        message = "source pin must use the exact SourcePin type"
        raise SourcePinError(message)
    observed = source_snapshot_evidence(root, pin.roots)
    if observed.file_count != pin.file_count:
        message = (
            "pinned source file count mismatch: "
            f"expected {pin.file_count}, found {observed.file_count}"
        )
        raise SourcePinError(message)
    if observed.snapshot_sha256 != pin.snapshot_sha256:
        message = (
            f"pinned source snapshot mismatch for {pin.repository}@{pin.commit}"
        )
        raise SourcePinError(message)
    return observed
