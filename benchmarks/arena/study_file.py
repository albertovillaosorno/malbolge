# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Bounded nonblocking ordinary-file admission for arena JSON input.
# - Must-Not:
#   - Authenticate producer provenance or claim atomic filesystem snapshots.
# - Allows:
#   - Inputs: an explicit local path and a positive byte-size budget.
#   - Outputs: exact file bytes if path and descriptor identity remain stable.
#   - Side effects: one read-only descriptor open and checked stream close.
# - Split-When:
#   - Cross-process atomic filesystem snapshots require a separate owner.
# - Merge-When:
#   - Evidence-file admission gains one shared platform-safe reader.
# - Summary:
#   - Closes a preflight-to-open FIFO/symlink substitution window.
# - Description:
#   - Checks regular descriptor identity, bounded reads and observed drift.
# - Usage:
#   - Called by both arena CLI routes before parsing untrusted JSON input.
# - Defaults:
#   - Drift, symlinks, devices, oversize, and short reads fail closed.
#

"""Safe bounded study-file read with explicit descriptor identity admission."""

from __future__ import annotations

import io
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Never

MAX_STUDY_BYTES = 16 * 1024 * 1024
# Public reporting aliases cannot widen the original source-file read cap.
_SOURCE_MAX_STUDY_BYTES = MAX_STUDY_BYTES
MAX_NATIVE_DESCRIPTOR = 2**31 - 1
_SOURCE_MAX_NATIVE_DESCRIPTOR = MAX_NATIVE_DESCRIPTOR
# Read directly from the original opened descriptor to cross-check any
# replaceable buffered-reader receipt against source bytes, not just metadata.
_SOURCE_GETATTR = getattr
_SOURCE_TYPE = type
_NATIVE_PREAD = _SOURCE_GETATTR(os, "pread", None)
_NATIVE_READ = os.read
_NATIVE_LSEEK = os.lseek
# A swapped module builtin cannot skip the source-byte reread, forge a read
# length, or replace the native buffer/byte representation after import.
_SOURCE_LEN = len
_SOURCE_MIN = min
_SOURCE_BYTES = bytes
_SOURCE_BYTEARRAY = bytearray

if TYPE_CHECKING:
    from typing import BinaryIO


class StudyFileError(ValueError):
    """An arena input file cannot be admitted as stable regular bytes."""


def _native_stat(info: os.stat_result) -> os.stat_result:
    # Filesystem calls normally return an exact native stat_result. Reject a
    # substituted dependency receipt before consulting attacker-owned fields.
    if _SOURCE_TYPE(info) is not os.stat_result:
        _fail("arena input returned invalid file metadata")
    return info


def _native_resolved_path(resolved: Path) -> Path:
    # Only the platform's native Path may supply an opened-file provenance
    # claim. Reject foreign resolve() results before fspath or comparison.
    if _SOURCE_TYPE(resolved) is not _SOURCE_TYPE(Path()):
        _fail("arena input returned invalid resolved path")
    return resolved


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    info = _native_stat(info)
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _fail(message: str) -> Never:
    raise StudyFileError(message)


def _admit_descriptor(receipt: object, *, source: str) -> int:
    # A forged os.open/fileno return must not become a procfs lookup, fstat,
    # fdopen, or os.close on an unrelated handle (notably bool 0/1).
    # OS file descriptors use native signed C ints on the supported hosts.
    if (
        _SOURCE_TYPE(receipt) is not int
        or not 0 <= receipt <= _SOURCE_MAX_NATIVE_DESCRIPTOR
    ):
        _fail(f"arena input {source} descriptor is not a native OS integer")
    return receipt


def _admit_limit(limit: int) -> None:
    if _SOURCE_TYPE(limit) is not int or not 0 < limit <= _SOURCE_MAX_STUDY_BYTES:
        _fail("arena study byte limit must be a positive integer up to 16 MiB")


def _parent_identity(path: Path) -> tuple[int, int]:
    try:
        parent = path.parent.stat()
    except Exception as error:
        message = "arena input parent directory changed"
        raise StudyFileError(message) from error
    parent = _native_stat(parent)
    if not stat.S_ISDIR(parent.st_mode):
        _fail("arena input parent directory changed")
    return parent.st_dev, parent.st_ino


def _admit_path(path: Path, limit: int) -> os.stat_result:
    original = _native_stat(path.lstat())
    if not stat.S_ISREG(original.st_mode):
        _fail("arena input must be a regular file, not a link or device")
    if original.st_size > limit:
        _fail("arena input exceeds 16 MiB limit")
    return original


def _open_study(path: Path) -> BinaryIO:
    flags = (
        os.O_RDONLY
        | _SOURCE_GETATTR(os, "O_BINARY", 0)
        | _SOURCE_GETATTR(os, "O_NONBLOCK", 0)
        | _SOURCE_GETATTR(os, "O_NOFOLLOW", 0)
    )
    # A leaf-only O_NOFOLLOW open cannot detect a transient symlinked
    # parent. Freeze the pre-open resolved target and compare it with the
    # real opened descriptor pathname before accepting any bytes. Stable
    # symlinked parents remain valid, but transient redirection rejects.
    expected_path = (
        os.fspath(_native_resolved_path(path.resolve(strict=True)))
        if sys.platform == "linux"
        else None
    )
    descriptor = _admit_descriptor(os.open(path, flags), source="raw")
    try:
        if expected_path is not None:
            opened_path = os.readlink(f"/proc/self/fd/{descriptor}")
            if _SOURCE_TYPE(opened_path) is not str:
                _fail("arena input returned invalid opened path")
            if opened_path != expected_path:
                _fail("arena input opened path changed")
        stream = os.fdopen(descriptor, "rb")
        # fdopen must transfer ownership of this exact raw descriptor to a
        # native buffered FileIO. A substituted stream can report the correct
        # fileno and inode while returning unrelated bytes from read().
        if (
            _SOURCE_TYPE(stream) is not io.BufferedReader
            or _SOURCE_TYPE(stream.raw) is not io.FileIO
        ):
            _fail("arena input stream is not a native buffered file")
        if _admit_descriptor(stream.fileno(), source="stream") != descriptor:
            _fail("arena input stream descriptor differs from opened descriptor")
        return stream
    except Exception as error:
        # fdopen has not taken ownership when path or stream admission fails.
        # Cleanup cannot replace the original reason for rejecting this file.
        try:
            os.close(descriptor)
        except Exception:
            # Preserve the primary admission failure without invoking a
            # foreign close exception's diagnostic formatter.
            BaseException.add_note(error, "arena input descriptor cleanup also failed")
        if isinstance(error, StudyFileError):
            raise error  # ruff: ignore[TRY201]
        raise StudyFileError("arena input stream construction failed") from error


def _read_complete(stream: BinaryIO, *, size: int) -> bytes:
    """Read the admitted file length across bounded, valid byte chunks.

    Returns:
        Exact bytes from the already-opened regular file.

    Raises:
        StudyFileError: A read fails or stops before the admitted file size.

    """
    data = _SOURCE_BYTEARRAY()
    while _SOURCE_LEN(data) < size:
        requested = _SOURCE_MIN(size - _SOURCE_LEN(data), 1024 * 1024)
        try:
            chunk = stream.read(requested)
        except Exception as error:
            message = "arena input stream read failed"
            raise StudyFileError(message) from error
        if _SOURCE_TYPE(chunk) is not _SOURCE_BYTES or _SOURCE_LEN(chunk) > requested:
            _fail("arena input stream read returned invalid bytes")
        if not chunk:
            _fail("arena input read ended before declared file size")
        data.extend(chunk)
    return _SOURCE_BYTES(data)


def _verify_descriptor_bytes(descriptor: int, data: bytes) -> None:
    """Require an independent native descriptor read to match admitted bytes.

    Raises:
        StudyFileError: The reader's bytes differ from the opened source.

    """
    if _SOURCE_TYPE(data) is not _SOURCE_BYTES:
        _fail("arena input source bytes differ from opened descriptor")
    try:
        if _NATIVE_PREAD is None:
            # Windows lacks pread; no further buffered reads occur after this.
            _NATIVE_LSEEK(descriptor, 0, os.SEEK_SET)
        offset = 0
        while offset < _SOURCE_LEN(data):
            requested = _SOURCE_MIN(_SOURCE_LEN(data) - offset, 1024 * 1024)
            if _NATIVE_PREAD is not None:
                observed = _NATIVE_PREAD(descriptor, requested, offset)
            else:
                observed = _NATIVE_READ(descriptor, requested)
            if (
                _SOURCE_TYPE(observed) is not _SOURCE_BYTES
                or not observed
                or observed != data[offset : offset + _SOURCE_LEN(observed)]
            ):
                _fail("arena input source bytes differ from opened descriptor")
            offset += _SOURCE_LEN(observed)
    except StudyFileError:
        raise
    except Exception as error:
        message = "arena input source descriptor reread failed"
        raise StudyFileError(message) from error


def _read_descriptor(
    path: Path,
    before: os.stat_result,
    *,
    limit: int,
) -> tuple[bytes, os.stat_result]:
    primary: Exception | None = None
    try:
        with _open_study(path) as stream:
            try:
                opened_fd = _admit_descriptor(stream.fileno(), source="stream")
                opened = _native_stat(os.fstat(opened_fd))
                if not stat.S_ISREG(opened.st_mode) or (
                    _identity(opened) != _identity(before)
                ):
                    _fail("arena input changed between path and open")
                if opened.st_size > limit:
                    _fail("arena input exceeds 16 MiB limit")
                data = _read_complete(stream, size=opened.st_size)
                completed_fd = _admit_descriptor(stream.fileno(), source="stream")
                if completed_fd != opened_fd:
                    _fail("arena input stream descriptor changed during read")
                completed = _native_stat(os.fstat(completed_fd))
                if _identity(completed) != _identity(opened):
                    _fail("arena input changed during read")
                _verify_descriptor_bytes(completed_fd, data)
                # The context manager can raise on close, but cannot expose a
                # forged non-None close receipt. Close explicitly after the
                # final descriptor check, while retaining its cleanup path.
                try:
                    close_receipt: object = stream.close()
                except Exception as error:
                    message = "arena input stream close failed"
                    raise StudyFileError(message) from error
                if close_receipt is not None:
                    _fail("arena input stream close completion was not native None")
            except Exception as error:
                primary = error
                raise
    except Exception as error:
        if primary is not None and error is not primary:
            BaseException.add_note(primary, "arena input stream cleanup also failed")
            error = primary
        if isinstance(error, StudyFileError):
            # It can be the rejected read, not the active close error.
            raise error  # ruff: ignore[TRY201]
        message = "arena input stream access failed"
        raise StudyFileError(message) from error
    # A substituted context manager may return a truthy __exit__ receipt and
    # swallow the rejection raised by the admitted read or final close. The
    # inner catch retains that original failure even when the with block exits
    # without propagating it, so such a stream cannot certify source bytes.
    if primary is not None:
        if isinstance(primary, StudyFileError):
            raise primary
        message = "arena input stream access failed"
        raise StudyFileError(message) from primary
    return data, opened


def _admit_completion(
    path: Path,
    opened: os.stat_result,
    data: bytes,
    *,
    limit: int,
) -> None:
    after = _native_stat(path.lstat())
    if not stat.S_ISREG(after.st_mode) or _identity(after) != _identity(opened):
        _fail("arena input path changed during read")
    if _SOURCE_LEN(data) > limit:
        _fail("arena input exceeds 16 MiB limit")
    if _SOURCE_LEN(data) != opened.st_size:
        _fail("arena input read ended before declared file size")


def _read_admitted_study(path: Path, *, limit: int) -> bytes:
    before = _admit_path(path, limit)
    original_parent = _parent_identity(path)
    # Even if a different parent resolves to a hard link of the same inode,
    # the source's canonical location must remain the originally admitted one.
    # The descriptor check in _open_study independently binds the open itself.
    original_target = (
        _native_resolved_path(path.resolve(strict=True))
        if sys.platform == "linux"
        else None
    )
    data, opened = _read_descriptor(path, before, limit=limit)
    _admit_completion(path, opened, data, limit=limit)
    if original_target is not None:
        try:
            current_target = _native_resolved_path(path.resolve(strict=True))
        except StudyFileError:
            raise
        except Exception as error:
            message = "arena input parent path changed during read"
            raise StudyFileError(message) from error
        if current_target != original_target:
            _fail("arena input parent path changed during read")
    if _parent_identity(path) != original_parent:
        _fail("arena input parent directory changed")
    return data


def read_study_bytes(path: Path, *, limit: int) -> bytes:
    """Read a bounded ordinary file under one typed admission boundary.

    Returns:
        Exact bytes from a regular descriptor that remained path-bound.

    Raises:
        StudyFileError: Invalid limit, path, stream, or observed drift.

    """
    _admit_limit(limit)
    # A Path subclass can override __fspath__ to name a different file than
    # its displayed path. Never perform stat/open/resolve on foreign methods.
    if _SOURCE_TYPE(path) is not _SOURCE_TYPE(Path()):
        _fail("arena input path requires an exact native Path")
    try:
        return _read_admitted_study(path, limit=limit)
    except StudyFileError:
        raise
    except Exception as error:
        message = "arena input path access failed"
        raise StudyFileError(message) from error
