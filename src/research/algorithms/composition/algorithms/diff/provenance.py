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

import builtins
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256 as _native_sha256
from pathlib import Path, PurePath
from stat import S_ISDIR, S_ISLNK, S_ISREG
from sys import getfilesystemencodeerrors as _get_filesystem_encode_errors
from sys import getfilesystemencoding as _get_filesystem_encoding
from types import MemberDescriptorType
from typing import Final, cast

from algorithms.diff.exact import ExactTreeError, read_exact_regular_file
from algorithms.diff.model import reserved_windows_component

_ZERO = 0
_ONE = 1
_FRAME_BYTES = 8
_DOMAIN = b"malbolge-pinned-source-v1\0"
_PARENT = ".."
_DOT = "."
_BACKSLASH = "\\"
_HOST_PATH_SEPARATOR: Final = os.sep
_NUL = "\x00"
_COMMIT_HEX_LENGTH = 40
_SHA256_HEX_LENGTH = 64
_LOWER_HEX = frozenset("0123456789abcdef")
# Snapshot acceptance must not depend on later consumer-global hooks.
_NATIVE_ALL = builtins.all
_NATIVE_ANY = builtins.any
_NATIVE_LEN = builtins.len
_NATIVE_SET = builtins.set
_NATIVE_SORTED = builtins.sorted
_NATIVE_TUPLE = builtins.tuple
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_STR = builtins.str
_NATIVE_ZIP = builtins.zip
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
_NATIVE_STAT_RESULT: Final = os.stat_result
_NATIVE_OBJECT_NEW: Final = object.__new__
_NATIVE_RELATIVE_TO = Path.relative_to
_NATIVE_PATH_RESOLVE = Path.resolve
_NATIVE_HOST_REALPATH = os.path.realpath
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_READLINK = os.readlink
_NATIVE_OS_GETCWD = os.getcwd
_NATIVE_STAT_ISLNK = stat.S_ISLNK
_NATIVE_STAT_ISDIR = stat.S_ISDIR
_NATIVE_OS_SCANDIR = os.scandir
_NATIVE_PATH_JOINPATH = Path.joinpath
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_IS_JUNCTION = Path.is_junction
# Path.__str__ reads a mutable cached slot and, on a fresh path, mutable
# pathlib parser descriptors. A late class-hook replacement must not redirect
# the filesystem tree selected by source-pin verification.
_PATH_STRING_DEPENDENCIES: Final = (
    "__getattribute__",
    "__str__",
    "__fspath__",
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
_NATIVE_PATH_STRING_HOOKS: Final = tuple(
    (
        cls,
        tuple((name, cls.__dict__.get(name)) for name in _PATH_STRING_DEPENDENCIES),
    )
    for cls in _NATIVE_PATH_TYPE.__mro__
    if issubclass(cls, PurePath)
)
# Path.resolve constructs its result through class-level factories. The
# original method still dispatches to these replaceable Python attributes.
_NATIVE_PATH_FACTORY_HOOKS: Final = tuple(
    (
        cls,
        tuple(
            (name, cls.__dict__.get(name))
            for name in ("with_segments", "__new__", "__init__")
        ),
    )
    for cls in _NATIVE_PATH_TYPE.__mro__
    if issubclass(cls, PurePath)
)
# Match os.fsencode's host codec without late os.fspath/fsencode lookups.
_FILESYSTEM_ENCODING = _get_filesystem_encoding()
_FILESYSTEM_ERRORS = _get_filesystem_encode_errors()


def _native_path_lstat(path: Path) -> os.stat_result:
    # Native input status cannot be redefined by subsequent domain callbacks.
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat


def _native_relative_label(path: Path, root: Path) -> str:
    """Bind discovered paths to unambiguous portable relative labels."""
    relative = _NATIVE_RELATIVE_TO(path, root)
    spelling = _NATIVE_PATH_STRING(relative)
    # On POSIX a backslash is a literal filename byte, not a separator.
    # Replacing it with '/' could make an unrelated file certify a pin for
    # a different directory tree when the alias's parent also exists.
    if _HOST_PATH_SEPARATOR == _BACKSLASH:
        spelling = spelling.replace(_BACKSLASH, "/")
    return _validate_relative_path(spelling)


class SourcePinError(RuntimeError):
    """Raised when a local source tree does not satisfy its pinned snapshot."""


@dataclass(frozen=True, slots=True, init=False)
class SourcePin:
    """Externally named revision plus locally verifiable snapshot identity."""

    repository: str
    commit: str
    roots: tuple[str, ...]
    file_count: int
    snapshot_sha256: str

    def __init__(
        self,
        repository: str,
        commit: str,
        roots: tuple[str, ...],
        file_count: int,
        snapshot_sha256: str,
    ) -> None:
        """Bind raw fields and execute the original metadata validator."""
        _PIN_REPOSITORY_SLOT.__set__(self, repository)
        _PIN_COMMIT_SLOT.__set__(self, commit)
        _PIN_ROOTS_SLOT.__set__(self, roots)
        _PIN_COUNT_SLOT.__set__(self, file_count)
        _PIN_DIGEST_SLOT.__set__(self, snapshot_sha256)
        _SOURCE_PIN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject malformed source-pin metadata."""
        repository, commit, roots, file_count, digest = _source_pin_fields(self)
        _validate_repository(repository)
        _validate_commit(commit)
        _validate_file_count(file_count)
        _validate_snapshot_sha256(digest)
        _validate_roots(roots)


# Record classes can acquire late class getters or validator replacements.
# Preserve their initial member storage readers and constructor guards.
_SOURCE_PIN_VALIDATOR: Final = SourcePin.__post_init__
_PIN_REPOSITORY_SLOT = cast(
    "MemberDescriptorType", SourcePin.__dict__["repository"]
)
_PIN_COMMIT_SLOT = cast("MemberDescriptorType", SourcePin.__dict__["commit"])
_PIN_ROOTS_SLOT = cast("MemberDescriptorType", SourcePin.__dict__["roots"])
_PIN_COUNT_SLOT = cast("MemberDescriptorType", SourcePin.__dict__["file_count"])
_PIN_DIGEST_SLOT = cast(
    "MemberDescriptorType", SourcePin.__dict__["snapshot_sha256"]
)


def _source_pin_fields(
    pin: SourcePin,
) -> tuple[str, str, tuple[str, ...], int, str]:
    return (
        cast("str", _PIN_REPOSITORY_SLOT.__get__(pin, SourcePin)),
        cast("str", _PIN_COMMIT_SLOT.__get__(pin, SourcePin)),
        cast("tuple[str, ...]", _PIN_ROOTS_SLOT.__get__(pin, SourcePin)),
        cast("int", _PIN_COUNT_SLOT.__get__(pin, SourcePin)),
        cast("str", _PIN_DIGEST_SLOT.__get__(pin, SourcePin)),
    )


def _validate_repository(repository: object) -> None:
    if _NATIVE_TYPE(repository) is not _NATIVE_STR or not repository:
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
    return _NATIVE_LEN(value) == length and _NATIVE_ALL(
        char in _LOWER_HEX for char in value
    )


def _validate_commit(commit: object) -> None:
    if _NATIVE_TYPE(commit) is not _NATIVE_STR or not _is_lower_hex(
        commit, _COMMIT_HEX_LENGTH
    ):
        message = "source pin commit must be 40 lowercase hexadecimal characters"
        raise SourcePinError(message)


def _validate_file_count(file_count: object) -> None:
    if _NATIVE_TYPE(file_count) is not _NATIVE_INT or file_count < _ONE:
        message = "source pin file_count must be a positive integer"
        raise SourcePinError(message)


def _validate_snapshot_sha256(snapshot_sha256: object) -> None:
    if _NATIVE_TYPE(snapshot_sha256) is not _NATIVE_STR or not _is_lower_hex(
        snapshot_sha256, _SHA256_HEX_LENGTH
    ):
        message = "source pin snapshot_sha256 must be lowercase SHA-256"
        raise SourcePinError(message)


def _validate_roots(roots: object) -> None:
    if _NATIVE_TYPE(roots) is not _NATIVE_TUPLE:
        message = "source pin roots must use the exact immutable tuple type"
        raise SourcePinError(message)
    items = cast("tuple[object, ...]", roots)
    if _NATIVE_ANY(_NATIVE_TYPE(root) is not _NATIVE_STR for root in items):
        message = "source pin roots must contain exact string paths"
        raise SourcePinError(message)
    string_roots = cast("tuple[str, ...]", roots)
    if not string_roots or string_roots != _NATIVE_TUPLE(
        _NATIVE_SORTED(_NATIVE_SET(string_roots))
    ):
        message = "source pin roots must be unique and sorted"
        raise SourcePinError(message)
    _require_disjoint_roots(string_roots)


def _require_disjoint_roots(roots: tuple[str, ...]) -> None:
    selected: set[str] = _NATIVE_SET()
    for root in roots:
        _ = _validate_relative_path(root)
        components = root.split("/")
        parent = components[0]
        for component in components[1:]:
            if parent in selected:
                message = "source pin roots must not overlap"
                raise SourcePinError(message)
            parent += "/" + component
        selected.add(root)


@dataclass(frozen=True, slots=True, init=False)
class SourcePinEvidence:
    """Observed deterministic snapshot for one pinned local source tree."""

    file_count: int
    snapshot_sha256: str

    def __init__(self, file_count: int, snapshot_sha256: str) -> None:
        """Bind observed fields and execute the original evidence validator."""
        _EVIDENCE_COUNT_SLOT.__set__(self, file_count)
        _EVIDENCE_DIGEST_SLOT.__set__(self, snapshot_sha256)
        _SOURCE_EVIDENCE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject malformed observed source-pin evidence."""
        count, digest = _source_evidence_fields(self)
        _validate_file_count(count)
        _validate_snapshot_sha256(digest)


_SOURCE_EVIDENCE_VALIDATOR: Final = SourcePinEvidence.__post_init__
_EVIDENCE_COUNT_SLOT = cast(
    "MemberDescriptorType", SourcePinEvidence.__dict__["file_count"]
)
_EVIDENCE_DIGEST_SLOT = cast(
    "MemberDescriptorType", SourcePinEvidence.__dict__["snapshot_sha256"]
)
_SOURCE_EVIDENCE_INIT = cast(
    "Callable[[SourcePinEvidence, int, str], None]",
    SourcePinEvidence.__dict__["__init__"],
)


def _new_source_evidence(count: int, digest: str) -> SourcePinEvidence:
    """Preserve observed source identity across late evidence class hooks."""
    observed = _NATIVE_OBJECT_NEW(SourcePinEvidence)
    _SOURCE_EVIDENCE_INIT(observed, count, digest)
    return observed


def _source_evidence_fields(evidence: SourcePinEvidence) -> tuple[int, str]:
    return (
        cast(
            "int", _EVIDENCE_COUNT_SLOT.__get__(evidence, SourcePinEvidence)
        ),
        cast(
            "str", _EVIDENCE_DIGEST_SLOT.__get__(evidence, SourcePinEvidence)
        ),
    )


def _u64(value: int) -> bytes:
    return value.to_bytes(_FRAME_BYTES, byteorder="big", signed=False)


def _frame(value: bytes) -> bytes:
    return _u64(_NATIVE_LEN(value)) + value


def _utf8_pinned_path(path: str) -> bytes:
    try:
        return path.encode("utf-8")
    except UnicodeError as error:
        message = "pinned source paths must be UTF-8 encodable"
        raise SourcePinError(message) from error


def _validate_relative_path(relative_path: object) -> str:
    if _NATIVE_TYPE(relative_path) is not _NATIVE_STR:
        message = "pinned source path must use the exact string type"
        raise SourcePinError(message)
    # Root labels are lexical evidence, not mutable pathlib method results.
    # Empty/dot/parent components also reject repeated or trailing slashes.
    unsafe = (
        not relative_path
        or _BACKSLASH in relative_path
        or _NUL in relative_path
        or relative_path.startswith("/")
        or _NATIVE_ANY(
            reserved_windows_component(component)
            for component in relative_path.split("/")
        )
        or _NATIVE_ANY(part in {"", _DOT, _PARENT} for part in relative_path.split("/"))
    )
    if unsafe:
        message = f"unsafe pinned source path: {relative_path!r}"
        raise SourcePinError(message)
    _ = _utf8_pinned_path(relative_path)
    return relative_path


def _host_error_detail(error: BaseException) -> str:
    """Keep foreign exception formatters outside provenance diagnostics."""
    if _NATIVE_TYPE(error) in (
        OSError, ValueError, RuntimeError, ExactTreeError
    ):
        arguments = cast("tuple[object, ...]", error.args)
        if (
            _NATIVE_LEN(arguments) == 1
            and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR
        ):
            return arguments[0]
    return _NATIVE_TYPE(error).__name__


def _source_mode(path: Path, relative: str) -> int | None:
    try:
        receipt = _NATIVE_PATH_LSTAT(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"pinned source status failed for {relative}: {detail}"
        raise SourcePinError(message) from error
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = f"pinned source status must be native for {relative}"
        raise SourcePinError(message)
    mode = receipt.st_mode
    try:
        is_link = S_ISLNK(mode) or _NATIVE_PATH_IS_JUNCTION(path)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"pinned source status failed for {relative}: {detail}"
        raise SourcePinError(message) from error
    if is_link:
        message = f"symlink is not accepted in pinned source: {relative}"
        raise SourcePinError(message)
    return mode


def _require_unlinked_parent_components(root: Path, relative: str) -> None:
    current = root
    for component in relative.split("/")[:-1]:
        current /= component
        label = _native_relative_label(current, root)
        mode = _source_mode(current, label)
        if mode is None or not S_ISDIR(mode):
            message = f"pinned source parent must be a directory: {label}"
            raise SourcePinError(message)


def _selected_root(root: Path, relative_root: str) -> tuple[Path, int]:
    _require_unlinked_parent_components(root, relative_root)
    selected = _NATIVE_PATH_JOINPATH(root, *relative_root.split("/"))
    mode = _source_mode(selected, relative_root)
    if mode is None:
        message = f"missing pinned source root: {relative_root}"
        raise SourcePinError(message)
    if S_ISREG(mode) or S_ISDIR(mode):
        return selected, mode
    message = f"special entry is not accepted in pinned source: {relative_root}"
    raise SourcePinError(message)


def _raise_source_walk_error(
    error: OSError | ValueError | RuntimeError,
) -> None:
    message = f"pinned source traversal failed: {_host_error_detail(error)}"
    raise SourcePinError(message) from error


def _directory_paths(selected: Path) -> tuple[Path, ...]:
    """Enumerate a source tree without late mutable pathlib/os walk hooks."""
    paths: list[Path] = []
    pending = [selected]
    while pending:
        directory = pending.pop()
        try:
            with _NATIVE_OS_SCANDIR(_NATIVE_PATH_STRING(directory)) as entries:
                for entry in entries:
                    child = _NATIVE_PATH_JOINPATH(directory, entry.name)
                    relative = _native_relative_label(child, selected)
                    mode = _source_mode(child, relative)
                    if mode is None:
                        message = f"pinned source entry disappeared: {relative}"
                        raise SourcePinError(message)
                    if not (S_ISDIR(mode) or S_ISREG(mode)):
                        message = (
                            "special entry is not accepted in pinned source: "
                            f"{relative}"
                        )
                        raise SourcePinError(message)
                    paths.append(child)
                    if S_ISDIR(mode):
                        pending.append(child)
        except SourcePinError:
            raise
        except (OSError, ValueError, RuntimeError) as error:
            _raise_source_walk_error(error)
    return _NATIVE_TUPLE(_NATIVE_SORTED(paths))


def _directory_files(root: Path, selected: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in _directory_paths(selected):
        relative = _native_relative_label(path, root)
        mode = _source_mode(path, relative)
        if mode is None:
            message = f"pinned source entry disappeared: {relative}"
            raise SourcePinError(message)
        if S_ISREG(mode):
            files.append(path)
            continue
        if not S_ISDIR(mode):
            message = f"special entry is not accepted in pinned source: {relative}"
            raise SourcePinError(message)
    return _NATIVE_TUPLE(files)


def _collect_root(root: Path, relative_root: str) -> tuple[Path, ...]:
    selected, mode = _selected_root(root, relative_root)
    if S_ISREG(mode):
        return (selected,)
    return _directory_files(root, selected)


def _pinned_files(root: Path, roots: tuple[str, ...]) -> tuple[Path, ...]:
    files = _NATIVE_TUPLE(
        path for relative in roots for path in _collect_root(root, relative)
    )
    unique = {_native_relative_label(path, root) for path in files}
    if _NATIVE_LEN(unique) != _NATIVE_LEN(files):
        message = "pinned source roots overlap"
        raise SourcePinError(message)
    return _NATIVE_TUPLE(
        _NATIVE_SORTED(files, key=lambda path: _native_relative_label(path, root))
    )


def _validate_root_path(root: object) -> None:
    # A foreign Path subclass can override source pin status and byte reads.
    if _NATIVE_TYPE(root) is not _NATIVE_PATH_TYPE:
        message = "pinned source root must use exact pathlib Path"
        raise SourcePinError(message)
    if _NATIVE_ANY(
        cls.__dict__.get(name) is not original
        for cls, hooks in _NATIVE_PATH_STRING_HOOKS
        for name, original in hooks
    ):
        message = "pinned source root path hooks changed"
        raise SourcePinError(message)
    raw = _NATIVE_PATH_STRING(root)
    if _NUL in raw:
        message = "pinned source root path must not contain NUL"
        raise SourcePinError(message)
    try:
        _ = raw.encode("utf-8")
        _ = raw.encode(_FILESYSTEM_ENCODING, _FILESYSTEM_ERRORS)
    except UnicodeError as error:
        message = "pinned source root path must be filesystem-encodable"
        raise SourcePinError(message) from error


def _require_native_root_resolver() -> None:
    """Reject late host hooks consulted by the original pathlib resolver."""
    if os.path.realpath is not _NATIVE_HOST_REALPATH:
        message = "pinned source root native host resolver changed"
        raise SourcePinError(message)
    # Original realpath still calls host functions by their mutable names.
    # Native lstat used for our status check does not protect its internals.
    if (
        os.fspath is not _NATIVE_OS_FSPATH
        or os.lstat is not _NATIVE_OS_LSTAT
        or os.readlink is not _NATIVE_OS_READLINK
        or os.getcwd is not _NATIVE_OS_GETCWD
        or stat.S_ISLNK is not _NATIVE_STAT_ISLNK
        or stat.S_ISDIR is not _NATIVE_STAT_ISDIR
    ):
        message = "pinned source root native host resolver dependencies changed"
        raise SourcePinError(message)
    if _NATIVE_ANY(
        cls.__dict__.get(name) is not original
        for cls, hooks in _NATIVE_PATH_FACTORY_HOOKS
        for name, original in hooks
    ):
        message = "pinned source root native path factory changed"
        raise SourcePinError(message)


def _resolved_source_root(root: Path) -> Path:
    # Pin the resolver's indirect dependencies before and after normalization.
    _require_native_root_resolver()
    mode = _source_mode(root, ".")
    if mode is None or not S_ISDIR(mode):
        message = f"pinned source root must be a directory: {root}"
        raise SourcePinError(message)
    _require_native_root_resolver()
    try:
        resolved = _NATIVE_PATH_RESOLVE(root, strict=True)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _host_error_detail(error)
        message = f"pinned source root resolution failed: {root}: {detail}"
        raise SourcePinError(message) from error
    _require_native_root_resolver()
    return resolved


def _read_pinned_source(root: Path, path: Path, relative: str) -> bytes:
    _require_unlinked_parent_components(root, relative)
    try:
        return read_exact_regular_file(path, "pinned source")
    except ExactTreeError as error:
        detail = _host_error_detail(error)
        message = f"pinned source read failed for {relative}: {detail}"
        failure = SourcePinError(message)
        if _NATIVE_TYPE(error) is ExactTreeError:
            for note in cast("list[str]", getattr(error, "__notes__", [])):
                failure.add_note(note)
        raise failure from error


def _pinned_file_receipt(path: Path, relative: str) -> tuple[int, ...]:
    """Capture a physical file identity that survives mtime restoration."""
    try:
        status = _NATIVE_PATH_LSTAT(path)
    except (OSError, ValueError, RuntimeError, TypeError) as error:
        message = f"pinned source file changed during snapshot: {relative}"
        raise SourcePinError(message) from error
    if _NATIVE_TYPE(status) is not _NATIVE_STAT_RESULT:
        message = f"pinned source status must be native for {relative}"
        raise SourcePinError(message)
    if not S_ISREG(status.st_mode):
        message = f"pinned source file changed during snapshot: {relative}"
        raise SourcePinError(message)
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def source_snapshot_evidence(root: Path, roots: tuple[str, ...]) -> SourcePinEvidence:
    """Hash selected source roots by normalized path and exact file bytes.

    Returns:
        Deterministic count and SHA-256 snapshot evidence.

    """
    _validate_root_path(root)
    _validate_roots(roots)
    digest = _native_sha256()
    digest.update(_DOMAIN)
    resolved_root = _resolved_source_root(root)
    files = _pinned_files(resolved_root, roots)
    digest.update(_u64(_NATIVE_LEN(files)))
    receipts: list[tuple[int, ...]] = []
    for path in files:
        relative_text = _native_relative_label(path, resolved_root)
        relative = _utf8_pinned_path(relative_text)
        receipts.append(_pinned_file_receipt(path, relative_text))
        data = _read_pinned_source(resolved_root, path, relative_text)
        digest.update(_frame(relative))
        digest.update(_frame(_native_sha256(data).digest()))
    # Entries added or removed after discovery must not be absent from the
    # returned pin just because all initially enumerated bytes were stable.
    if _pinned_files(resolved_root, roots) != files:
        message = "pinned source file set changed during snapshot"
        raise SourcePinError(message)
    for path, before in _NATIVE_ZIP(files, receipts, strict=True):
        relative_text = _native_relative_label(path, resolved_root)
        if _pinned_file_receipt(path, relative_text) != before:
            message = f"pinned source file changed during snapshot: {relative_text}"
            raise SourcePinError(message)
    return _new_source_evidence(
        count=_NATIVE_LEN(files),
        digest=digest.hexdigest(),
    )


def require_source_pin(root: Path, pin: SourcePin) -> SourcePinEvidence:
    """Require exact selected-tree identity for a named external revision.

    Returns:
        Matching local snapshot evidence.

    Raises:
        SourcePinError: File count or snapshot digest differs from the pin.

    """
    if _NATIVE_TYPE(pin) is not SourcePin:
        message = "source pin must use the exact SourcePin type"
        raise SourcePinError(message)
    # A caller can allocate this exact frozen class without its constructor.
    # Only the original validator can attest all stored revision metadata.
    try:
        _SOURCE_PIN_VALIDATOR(pin)
    except (AttributeError, TypeError) as error:
        message = "source pin has incomplete native metadata"
        raise SourcePinError(message) from error
    repository, commit, roots, expected_count, expected_digest = (
        _source_pin_fields(pin)
    )
    observed = source_snapshot_evidence(root, roots)
    if _NATIVE_TYPE(observed) is not SourcePinEvidence:
        message = "source pin evidence requires exact native receipt"
        raise SourcePinError(message)
    try:
        _SOURCE_EVIDENCE_VALIDATOR(observed)
    except (AttributeError, TypeError) as error:
        message = "source pin evidence has incomplete native metadata"
        raise SourcePinError(message) from error
    count, digest = _source_evidence_fields(observed)
    if count != expected_count:
        message = (
            "pinned source file count mismatch: "
            f"expected {expected_count}, found {count}"
        )
        raise SourcePinError(message)
    if digest != expected_digest:
        message = f"pinned source snapshot mismatch for {repository}@{commit}"
        raise SourcePinError(message)
    return observed
