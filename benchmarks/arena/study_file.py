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
#   - Bounded nonblocking ordinary-file admission for arena JSON input.
# - Must-Not:
#   - Authenticate producer provenance or claim atomic filesystem snapshots.
# - Allows:
#   - Inputs: an explicit local path and a positive byte-size budget.
#   - Outputs: exact file bytes if path and descriptor identity remain stable.
#   - Side effects: one read-only descriptor open and close.
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

import os
import stat
import sys
from typing import TYPE_CHECKING, Never

MAX_STUDY_BYTES = 16 * 1024 * 1024

if TYPE_CHECKING:
    from pathlib import Path
    from typing import BinaryIO


class StudyFileError(ValueError):
    """An arena input file cannot be admitted as stable regular bytes."""


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _fail(message: str) -> Never:
    raise StudyFileError(message)


def _admit_limit(limit: int) -> None:
    if type(limit) is not int or not 0 < limit <= MAX_STUDY_BYTES:
        _fail("arena study byte limit must be a positive integer up to 16 MiB")


def _parent_identity(path: Path) -> tuple[int, int]:
    try:
        parent = path.parent.stat()
    except (OSError, RuntimeError) as error:
        message = "arena input parent directory changed"
        raise StudyFileError(message) from error
    if not stat.S_ISDIR(parent.st_mode):
        _fail("arena input parent directory changed")
    return parent.st_dev, parent.st_ino


def _admit_path(path: Path, limit: int) -> os.stat_result:
    original = path.lstat()
    if not stat.S_ISREG(original.st_mode):
        _fail("arena input must be a regular file, not a link or device")
    if original.st_size > limit:
        _fail("arena input exceeds 16 MiB limit")
    return original


def _open_study(path: Path) -> BinaryIO:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    # A leaf-only O_NOFOLLOW open cannot detect a transient symlinked
    # parent. Freeze the pre-open resolved target and compare it with the
    # real opened descriptor pathname before accepting any bytes. Stable
    # symlinked parents remain valid, but transient redirection rejects.
    expected_path = (
        os.fspath(path.resolve(strict=True)) if sys.platform == "linux" else None
    )
    descriptor = os.open(path, flags)
    try:
        if expected_path is not None:
            opened_path = os.readlink(f"/proc/self/fd/{descriptor}")
            if opened_path != expected_path:
                _fail("arena input opened path changed")
        return os.fdopen(descriptor, "rb")
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        # fdopen has not taken ownership when path or stream admission fails.
        # Cleanup cannot replace the original reason for rejecting this file.
        try:
            os.close(descriptor)
        except (
            OSError,
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
        ) as close_error:
            error.add_note(f"arena input descriptor cleanup also failed: {close_error}")
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
    data = bytearray()
    while len(data) < size:
        requested = min(size - len(data), 1024 * 1024)
        try:
            chunk = stream.read(requested)
        except (
            OSError,
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
        ) as error:
            message = "arena input stream read failed"
            raise StudyFileError(message) from error
        if type(chunk) is not bytes or len(chunk) > requested:
            _fail("arena input stream read returned invalid bytes")
        if not chunk:
            _fail("arena input read ended before declared file size")
        data.extend(chunk)
    return bytes(data)


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
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or (
                    _identity(opened) != _identity(before)
                ):
                    _fail("arena input changed between path and open")
                if opened.st_size > limit:
                    _fail("arena input exceeds 16 MiB limit")
                data = _read_complete(stream, size=opened.st_size)
                completed = os.fstat(stream.fileno())
                if _identity(completed) != _identity(opened):
                    _fail("arena input changed during read")
            except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
                primary = error
                raise
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        if primary is not None and error is not primary:
            primary.add_note(f"arena input stream cleanup also failed: {error}")
            error = primary
        if isinstance(error, StudyFileError):
            # It can be the rejected read, not the active close error.
            raise error  # ruff: ignore[TRY201]
        message = "arena input stream access failed"
        raise StudyFileError(message) from error
    return data, opened


def _admit_completion(
    path: Path,
    opened: os.stat_result,
    data: bytes,
    *,
    limit: int,
) -> None:
    after = path.lstat()
    if not stat.S_ISREG(after.st_mode) or _identity(after) != _identity(opened):
        _fail("arena input path changed during read")
    if len(data) > limit:
        _fail("arena input exceeds 16 MiB limit")
    if len(data) != opened.st_size:
        _fail("arena input read ended before declared file size")


def read_study_bytes(path: Path, *, limit: int) -> bytes:
    """Read one file without trusting mutable pathname evidence.

    Returns:
        Exact bytes from a regular descriptor that remained path-bound.

    """
    _admit_limit(limit)
    before = _admit_path(path, limit)
    original_parent = _parent_identity(path)
    # Even if a different parent resolves to a hard link of the same inode,
    # the source's canonical location must remain the originally admitted one.
    # The descriptor check in _open_study independently binds the open itself.
    original_target = path.resolve(strict=True) if sys.platform == "linux" else None
    data, opened = _read_descriptor(path, before, limit=limit)
    _admit_completion(path, opened, data, limit=limit)
    if original_target is not None:
        try:
            current_target = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            message = "arena input parent path changed during read"
            raise StudyFileError(message) from error
        if current_target != original_target:
            _fail("arena input parent path changed during read")
    if _parent_identity(path) != original_parent:
        _fail("arena input parent directory changed")
    return data
