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
#   - Atomic no-replace directory publication for source-bound transforms.
# - Must-Not:
#   - Overwrite a destination created by another writer.
#   - Silently downgrade unsupported host publication semantics.
# - Allows:
#   - Inputs: staging and destination pathlib paths owned by the caller.
#   - Outputs: one atomic directory rename when the destination is absent.
#   - Side effects: filesystem rename only.
# - Split-When:
#   - Split when another publication primitive gains an independent lifecycle.
# - Merge-When:
#   - Merge when another module owns the exact same no-replace directory ABI.
# - Summary:
#   - Portable atomic no-replace directory publication.
# - Description:
#   - Implements Windows rename and Linux renameat2 no-replace semantics.
# - Usage:
#   - Used by source-bound tree materializers at their final publication step.
# - Defaults:
#   - Unsupported hosts and publication collisions fail closed.
#

"""Portable atomic no-replace directory publication."""

from __future__ import annotations

import builtins
import ctypes
import errno
import os
import stat
import sys
from pathlib import Path
from typing import Final, Protocol, cast

_WINDOWS_OS_NAME: Final = "nt"
_LINUX_PLATFORM: Final = "linux"
_HOST_OS_NAME: Final = os.name
_HOST_PLATFORM: Final = sys.platform
_AT_FDCWD: Final = -100
_RENAME_NOREPLACE: Final = 1
_NUL: Final = "\x00"
# Admission must not trust process-global builtins replaced by consumers.
_NATIVE_TYPE: Final = builtins.type
_NATIVE_STR_TYPE: Final = builtins.str
_NATIVE_INT_TYPE: Final = builtins.int
_NATIVE_PATH_TYPE: Final = _NATIVE_TYPE(Path())
_NATIVE_STAT_RESULT: Final = os.stat_result
_NATIVE_IS_DIR: Final = stat.S_ISDIR
# Keep syscall path encoding outside mutable process-global os path hooks.
_NATIVE_PATH_STRING: Final = Path.__str__
_NATIVE_OS_LSTAT: Final = os.lstat
_NATIVE_OS_RENAME: Final = os.rename
_FILESYSTEM_ENCODING: Final = sys.getfilesystemencoding()
_FILESYSTEM_ERRORS: Final = sys.getfilesystemencodeerrors()
# Pin the Linux syscall ABI before a consumer can replace ctypes aliases.
_NATIVE_C_INT: Final = ctypes.c_int
_NATIVE_C_CHAR_P: Final = ctypes.c_char_p
_NATIVE_C_UINT: Final = ctypes.c_uint
_NATIVE_CDLL: Final = ctypes.CDLL
_NATIVE_GET_ERRNO: Final = ctypes.get_errno
_NATIVE_STRERROR: Final = os.strerror
_MAX_LINUX_ERRNO: Final = 4095


class _RenameAt2(Protocol):
    """Typed view of the Linux libc renameat2 entry point."""

    argtypes: tuple[object, ...]
    restype: object

    def __call__(self, *arguments: int | bytes) -> int:
        """Rename one path with the fixed Linux renameat2 ABI arguments."""
        ...


def _native_fsencode_path(path: Path) -> bytes:
    """Encode a native Path without delegating to mutable os path hooks.

    Returns:
        The host filesystem encoding of one exact pathlib Path.

    """
    return _NATIVE_PATH_STRING(path).encode(
        _FILESYSTEM_ENCODING, _FILESYSTEM_ERRORS
    )


def _native_path_lstat(path: Path) -> os.stat_result:
    """Inspect a native path without mutable pathlib or os dispatch hooks.

    Returns:
        The native host status record for the given path.

    """
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


def _native_path_rename(source: Path, destination: Path) -> None:
    """Rename using the host operation bound before domain code can run."""
    _NATIVE_OS_RENAME(
        _NATIVE_PATH_STRING(source), _NATIVE_PATH_STRING(destination)
    )


_NATIVE_PATH_LSTAT: Final = _native_path_lstat
_NATIVE_PATH_RENAME: Final = _native_path_rename


def _linux_rename_noreplace(source: Path, destination: Path) -> None:
    try:
        library = _NATIVE_CDLL(None, use_errno=True)
        renameat2 = cast("_RenameAt2", cast("object", library.renameat2))
        renameat2.argtypes = (
            _NATIVE_C_INT,
            _NATIVE_C_CHAR_P,
            _NATIVE_C_INT,
            _NATIVE_C_CHAR_P,
            _NATIVE_C_UINT,
        )
        renameat2.restype = _NATIVE_C_INT
    except (
        AttributeError,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        raise OSError(
            errno.ENOTSUP,
            "Linux renameat2(RENAME_NOREPLACE) is unavailable",
            destination,
        ) from error
    try:
        result = renameat2(
            _AT_FDCWD,
            _native_fsencode_path(source),
            _AT_FDCWD,
            _native_fsencode_path(destination),
            _RENAME_NOREPLACE,
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise OSError(
            errno.EINVAL,
            "Linux renameat2 invocation failed",
            destination,
        ) from error
    if _NATIVE_TYPE(result) is not _NATIVE_INT_TYPE:
        raise OSError(
            errno.EINVAL,
            "Linux renameat2 returned an invalid status",
            destination,
        )
    if result != 0:
        error_number = _NATIVE_GET_ERRNO()
        if (
            _NATIVE_TYPE(error_number) is not _NATIVE_INT_TYPE
            or error_number < 1
            or error_number > _MAX_LINUX_ERRNO
        ):
            raise OSError(
                errno.EIO,
                "Linux renameat2 returned an invalid errno status",
                destination,
            )
        raise OSError(
            error_number,
            _NATIVE_STRERROR(error_number),
            destination,
        )


def _require_fs_encodable_path(path: Path) -> None:
    try:
        _ = _native_fsencode_path(path)
    except UnicodeError as error:
        raise OSError(
            errno.EINVAL,
            "directory publication paths must be filesystem-encodable",
            path,
        ) from error


def _require_staging_directory(staging: Path) -> tuple[int, int]:
    """Reject non-directory payloads before a no-replace filesystem rename.

    Raises:
        OSError: Staging is missing or not a real directory.

    """
    try:
        receipt = _NATIVE_PATH_LSTAT(staging)
    except (TypeError, ValueError, RuntimeError) as error:
        raise OSError(
            errno.EINVAL,
            "staging directory status failed",
            staging,
        ) from error
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        raise OSError(
            errno.EINVAL,
            "staging directory requires native filesystem status",
            staging,
        )
    if not _NATIVE_IS_DIR(receipt.st_mode):
        raise OSError(
            errno.ENOTDIR,
            "staging must be an existing directory, not a file or symlink",
            staging,
        )
    return receipt.st_dev, receipt.st_ino


def _require_host_match(os_name: str, platform: str, destination: Path) -> None:
    if os_name != _HOST_OS_NAME or platform != _HOST_PLATFORM:
        raise OSError(
            errno.EINVAL,
            "directory publication host selectors must match the running host",
            destination,
        )


def _validate_publication_inputs(
    staging: object,
    destination: object,
    *,
    os_name: object,
    platform: object,
) -> tuple[Path, Path, str, str, tuple[int, int]]:
    # A Path subclass can override __fspath__, lstat or rename and redirect
    # the publication operation. Admit only the host's exact native Path type
    # before calling any path or filesystem method.
    native_path_type = _NATIVE_PATH_TYPE
    if (
        _NATIVE_TYPE(staging) is not native_path_type
        or _NATIVE_TYPE(destination) is not native_path_type
    ):
        raise OSError(
            errno.EINVAL,
            "directory publication paths must use exact pathlib Path",
        )
    if (
        _NUL in _NATIVE_PATH_STRING(staging)
        or _NUL in _NATIVE_PATH_STRING(destination)
    ):
        raise OSError(
            errno.EINVAL,
            "directory publication paths must not contain NUL bytes",
            destination,
        )
    _require_fs_encodable_path(staging)
    _require_fs_encodable_path(destination)
    if (
        _NATIVE_TYPE(os_name) is not _NATIVE_STR_TYPE
        or _NATIVE_TYPE(platform) is not _NATIVE_STR_TYPE
    ):
        raise OSError(
            errno.EINVAL,
            "directory publication host selectors must use exact strings",
        )
    _require_host_match(os_name, platform, destination)
    if staging == destination:
        raise OSError(
            errno.EINVAL,
            "directory publication staging and destination must differ",
            destination,
        )
    identity = _require_staging_directory(staging)
    return staging, destination, os_name, platform, identity


def _require_completed_publication(
    staging: Path, destination: Path, identity: tuple[int, int]
) -> None:
    """Reject a success-looking rename without the original staged inode."""
    message = "directory publication was not completed with the staged directory"
    try:
        result = _NATIVE_PATH_LSTAT(destination)
    except (OSError, ValueError, RuntimeError, TypeError) as error:
        raise OSError(errno.EIO, message, destination) from error
    if (
        _NATIVE_TYPE(result) is not _NATIVE_STAT_RESULT
        or not _NATIVE_IS_DIR(result.st_mode)
        or (result.st_dev, result.st_ino) != identity
    ):
        raise OSError(errno.EIO, message, destination)
    try:
        _ = _NATIVE_PATH_LSTAT(staging)
    except FileNotFoundError:
        return
    except (OSError, ValueError, RuntimeError, TypeError) as error:
        raise OSError(errno.EIO, message, destination) from error
    raise OSError(errno.EIO, message, destination)


def publish_directory_no_replace(
    staging: Path,
    destination: Path,
    *,
    os_name: str = os.name,
    platform: str = sys.platform,
) -> None:
    """Atomically publish one directory without replacing an existing target.

    Raises:
        OSError: The target exists or atomic no-replace publication is
            unavailable.

    """
    staging, destination, os_name, platform, identity = _validate_publication_inputs(
        staging,
        destination,
        os_name=os_name,
        platform=platform,
    )
    if os_name == _WINDOWS_OS_NAME:
        try:
            _ = _NATIVE_PATH_RENAME(staging, destination)
        except (TypeError, ValueError, RuntimeError) as error:
            raise OSError(
                errno.EIO,
                "Windows directory rename failed",
                destination,
            ) from error
        _require_completed_publication(staging, destination, identity)
        return
    if platform == _LINUX_PLATFORM:
        _linux_rename_noreplace(staging, destination)
        _require_completed_publication(staging, destination, identity)
        return
    raise OSError(
        errno.ENOTSUP,
        "atomic no-replace directory publication is unsupported",
        destination,
    )
