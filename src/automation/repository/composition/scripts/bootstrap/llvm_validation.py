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
#   - Exact repository-local LLVM 22.1.8 validation-toolchain import.
# - Must-Not:
#   - Install system packages, download LLVM, or accept a version mismatch.
# - Allows:
#   - Inputs: exact host LLVM observation or an existing Windows LLVM bundle.
#   - Outputs: local LLVM runtime/resources and neutral validation aliases.
#   - Side effects: repository-local staging and hardlink/copy import only.
# - Split-When:
#   - LLVM downloading or additional platform packaging needs independent
#     policy.
# - Merge-When:
#   - Another bootstrap module owns the exact LLVM validation lifecycle.
# - Summary:
#   - Import exact host LLVM into one platform-neutral repository-local surface.
# - Description:
#   - Preserve Windows PE bytes and construct Linux wrappers around local ELF.
# - Usage:
#   - Called by project bootstrap before C/LLVM validation.
# - Defaults:
#   - Missing or wrong-version LLVM remains unavailable.
#

"""Import exact LLVM validation tooling into repository-local state."""

from __future__ import annotations

import ctypes
import errno
import os
import re
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from contextlib import suppress
from dataclasses import dataclass
from io import BufferedRandom, BufferedReader
from pathlib import Path
from stat import S_IMODE, S_ISDIR, S_ISLNK, S_ISREG
from typing import Final, Never, cast

LLVM_VERSION: Final = "22.1.8"
LLVM_ROOT: Final = Path(".dependencies/llvm") / LLVM_VERSION
LLVM_IMPORT_MARKER: Final = ".malbolge-llvm-import-v1"
LINUX_PLATFORM: Final = "linux-x86_64"
WINDOWS_PLATFORM: Final = "windows-x86_64"
_TOOL_NAMES: Final = ("clang", "clang-tidy", "clang-format")
_LLVM_LIBRARY_NAMES: Final = ("libLLVM.so.22.1", "libclang-cpp.so.22.1")
_HOST_CAPTURE_TIMEOUT_SECONDS: Final = 15
_HOST_MAX_CAPTURE_CHARS: Final = 16_384
_LINUX_RENAME_NOREPLACE: Final = 1
_MKDIR_SUPPORTS_DIR_FD: Final = os.mkdir in os.supports_dir_fd


class LlvmImportError(RuntimeError):
    """Exact host LLVM cannot be admitted into repository-local validation."""


@dataclass(frozen=True, slots=True)
class LlvmHostObservation:
    """Exact host LLVM binaries, runtime libraries, and resource directory."""

    clang: Path
    clang_format: Path
    clang_tidy: Path
    clang_cpp: Path
    llvm: Path
    resource_dir: Path
    version: str


@dataclass(frozen=True, slots=True)
class LlvmReadiness:
    """Repository-local LLVM readiness without project bootstrap coupling."""

    ready: bool
    path: Path
    detail: str


def _fail(message: str) -> Never:
    raise LlvmImportError(message)


def llvm_version_matches(version_text: str) -> bool:
    """Match a native Clang/LLVM tool banner against the pinned release.

    Returns:
        Whether the primary version banner identifies the pinned release.

    """
    if type(version_text) is not str:
        return False
    # Native banners use LF or CRLF line endings; arbitrary control/invisible
    # characters can otherwise hide content or masquerade as new banner lines.
    normalized = version_text.replace("\r\n", "\n")
    if any(not line.isprintable() for line in normalized.split("\n")):
        return False
    lines = normalized.splitlines()
    if not lines:
        return False
    # Clang and clang-format have a one-line release followed by optional
    # ordered target/runtime metadata. The version alone cannot authorize
    # unrecognized diagnostics appended to an otherwise valid first line.
    version = re.escape(LLVM_VERSION)
    release_banner = (
        r"(?:(?:Ubuntu|Debian|Apple) )?clang(?:-format)? version "
        + version
        + r"(?: \([^()\r\n]{1,256}\))?"
    )
    if re.fullmatch(release_banner, lines[0]) is not None:
        allowed = (
            ("Target: ", r"[A-Za-z0-9_.+-]{1,128}"),
            ("Thread model: ", r"[A-Za-z0-9_.+-]{1,64}"),
            ("InstalledDir: ", r"[^\x00-\x1f\x7f]{1,512}"),
        )
        last_index = -1
        for line in lines[1:]:
            index = next(
                (
                    i
                    for i, (prefix, expression) in enumerate(allowed)
                    if line.startswith(prefix)
                    and re.fullmatch(prefix + expression, line) is not None
                ),
                -1,
            )
            if index <= last_index:
                return False
            last_index = index
        return True
    # clang-tidy prints the LLVM banner and at most its native build mode.
    return (
        lines[0] == "LLVM (http://llvm.org/):"
        and len(lines) in (2, 3)
        and lines[1] == f"  LLVM version {LLVM_VERSION}"
        and (len(lines) == 2 or lines[2] in ("  Optimized build.", "  Debug build."))
    )


def _unlinked_path(path: Path) -> bool:
    try:
        for part in (path, *path.parents):
            linked = part.is_symlink()
            junction = part.is_junction()
            if type(linked) is not bool or type(junction) is not bool:
                return False
            status = part.lstat()
            if (
                type(cast("object", status)) is not os.stat_result
                or S_ISLNK(status.st_mode)
                or linked
                or junction
            ):
                return False
    except (OSError, ValueError, TypeError, RuntimeError):
        return False
    return True


def _physical_file(path: Path) -> bool:
    try:
        if not _unlinked_path(path):
            return False
        status = path.lstat()
        return type(cast("object", status)) is os.stat_result and S_ISREG(
            status.st_mode
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _physical_directory(path: Path) -> bool:
    try:
        if not _unlinked_path(path):
            return False
        status = path.lstat()
        return type(cast("object", status)) is os.stat_result and S_ISDIR(
            status.st_mode
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _marker_bytes(platform_id: str) -> bytes:
    return f"llvm={LLVM_VERSION}\nplatform={platform_id}\n".encode()


def _marker_identity(status: os.stat_result) -> tuple[int, ...]:
    if type(cast("object", status)) is not os.stat_result:
        raise TypeError("LLVM import marker requires native stat evidence")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_nlink,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _stable_marker_descriptor(
    path: Path,
    admitted: tuple[int, ...],
    expected: bytes,
) -> bool:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    if type(cast("object", descriptor)) is not int or descriptor < 0:
        return False
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError):
        # The raw fd remains owned by this caller if wrapper creation fails.
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError):
            pass
        raise
    if type(cast("object", stream)) is not BufferedReader:
        try:
            # Foreign stream wrappers may own the original descriptor.
            with stream:
                return False
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError):
            # A non-context object never acquired descriptor ownership.
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError, RuntimeError):
                pass
            return False
    with stream:
        stream_fd = stream.fileno()
        native_fd = type(cast("object", stream_fd)) is int
        if not native_fd or stream_fd != descriptor:
            # fdopen returned a different native stream: its context owns that
            # stream, but cannot release our original descriptor.
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError, RuntimeError):
                pass
            return False
        before = _marker_identity(os.fstat(stream_fd))
        content = stream.read(len(expected) + 1)
        after = _marker_identity(os.fstat(stream_fd))
    return (
        before == admitted
        and after == admitted
        and type(content) is bytes
        and content == expected
    )


def _valid_marker(root: Path, platform_id: str) -> bool:
    marker = root / LLVM_IMPORT_MARKER
    if not _physical_file(marker):
        return False
    expected = _marker_bytes(platform_id)
    try:
        initial = marker.lstat()
        admitted = _marker_identity(initial)
        return (
            type(initial.st_nlink) is int
            and initial.st_nlink == 1
            and initial.st_size == len(expected)
            and _stable_marker_descriptor(marker, admitted, expected)
            and _physical_file(marker)
            and _marker_identity(marker.lstat()) == admitted
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _runtime_files(root: Path, platform_id: str) -> tuple[Path, ...]:
    if platform_id == LINUX_PLATFORM:
        binaries = tuple(root / "bin" / tool for tool in _TOOL_NAMES)
        libraries = tuple(root / "lib" / name for name in _LLVM_LIBRARY_NAMES)
        return (*binaries, *libraries)
    return tuple(root / "bin" / f"{tool}.exe" for tool in _TOOL_NAMES)


def _runtime_ready(root: Path, platform_id: str) -> bool:
    if platform_id not in {LINUX_PLATFORM, WINDOWS_PLATFORM}:
        return False
    if not _valid_marker(root, platform_id):
        return False
    if not all(_physical_file(path) for path in _runtime_files(root, platform_id)):
        return False
    if platform_id == LINUX_PLATFORM:
        # The marker alone cannot authorize symlinks, junctions or special
        # files inserted into the header tree after initial import.
        try:
            _require_physical_resources(root / "lib/clang/22")
        except LlvmImportError:
            return False
        return all(
            _valid_linux_wrapper(root / "jig-bin" / f"{tool}.bin", tool)
            for tool in _TOOL_NAMES
        )
    return all(
        _windows_alias_ready(
            root / "bin" / f"{tool}.exe", root / "jig-bin" / f"{tool}.bin"
        )
        for tool in _TOOL_NAMES
    )


def _matches_open_import_file(
    path: Path, descriptor: int, size: int, *, single_link: bool = False
) -> bool:
    """Attest a physical named file against an open descriptor and exact size."""
    try:
        opened = os.fstat(descriptor)
        named = path.lstat()
        return (
            _physical_file(path)
            and type(opened) is os.stat_result
            and type(named) is os.stat_result
            and S_ISREG(opened.st_mode)
            and opened.st_size == size
            and (not single_link or opened.st_nlink == 1)
            and _marker_identity(opened) == _marker_identity(named)
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _attest_import_hardlink(source: Path, destination: Path) -> None:
    """Admit a native hardlink only when both physical names share one inode."""
    try:
        source_status = source.lstat()
        destination_status = destination.lstat()
        if (
            not _physical_file(source)
            or not _physical_file(destination)
            or type(source_status) is not os.stat_result
            or type(destination_status) is not os.stat_result
            or not S_ISREG(source_status.st_mode)
            or not S_ISREG(destination_status.st_mode)
            or source_status.st_nlink < 2
            or _marker_identity(source_status) != _marker_identity(destination_status)
        ):
            _fail("LLVM import hardlink identity did not match the source")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import hardlink status failed: {type(error).__name__}"
        ) from error


def _exclusive_import_target(
    destination: Path, parent_descriptor: int | None
) -> BufferedRandom:
    """Open a new destination below a pinned parent without path redirection."""
    if parent_descriptor is None:
        return destination.open("x+b")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination.name, flags, 0o600, dir_fd=parent_descriptor)
    if type(cast("object", descriptor)) is not int or descriptor < 0:
        _fail("LLVM import fallback destination descriptor must be native")
    try:
        stream = os.fdopen(descriptor, "w+b")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        # A failing fdopen wrapper may have already released its raw fd.
        with suppress(OSError, ValueError, TypeError, RuntimeError):
            os.close(descriptor)
        error_type = type(error).__name__
        message = f"LLVM fallback destination stream wrap failed: {error_type}"
        raise LlvmImportError(message) from error
    try:
        if type(cast("object", stream)) is not BufferedRandom:
            _fail("LLVM import fallback destination stream must be native")
        stream_fd: object = stream.fileno()
        if type(stream_fd) is not int or stream_fd != descriptor:
            _fail("LLVM import fallback destination stream descriptor differs")
    except (
        LlvmImportError,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        AttributeError,
    ) as error:
        close_faults = (
            OSError,
            ValueError,
            TypeError,
            RuntimeError,
            AttributeError,
        )
        with suppress(*close_faults):
            stream.close()
        # A substituted wrapper may own a different fd or no fd at all.
        # Explicitly release the raw fd opened by this function as well.
        with suppress(OSError, ValueError, TypeError, RuntimeError):
            os.close(descriptor)
        if isinstance(error, LlvmImportError):
            raise
        error_type = type(error).__name__
        message = f"LLVM fallback destination stream failed: {error_type}"
        raise LlvmImportError(message) from error
    return stream


def _link_or_copy(
    source: str,
    destination: str,
    *,
    expected_parent_inode: tuple[int, int] | None = None,
) -> str:
    """Import a new file without overwriting a raced destination link."""
    source_path = Path(source)
    destination_path = Path(destination)
    if not _physical_directory(destination_path.parent):
        _fail("LLVM import destination parent must be physical")
    if (
        expected_parent_inode is not None
        and _native_directory_inode(destination_path.parent) != expected_parent_inode
    ):
        _fail("LLVM import destination parent changed before opening")
    parent_descriptor = (
        _open_physical_import_parent(destination_path.parent, "LLVM import destination")
        if os.name == "posix"
        else None
    )
    try:
        if expected_parent_inode is not None and parent_descriptor is not None:
            try:
                opened_parent = os.fstat(parent_descriptor)
                if (
                    type(opened_parent) is not os.stat_result
                    or (opened_parent.st_dev, opened_parent.st_ino)
                    != expected_parent_inode
                ):
                    _fail("LLVM import destination parent changed during opening")
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                error_type = type(error).__name__
                raise LlvmImportError(
                    f"LLVM import destination parent status failed: {error_type}"
                ) from error
        return _link_or_copy_in_parent(source_path, destination_path, parent_descriptor)
    finally:
        if parent_descriptor is not None:
            try:
                os.close(parent_descriptor)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                error_type = type(error).__name__
                raise LlvmImportError(
                    f"LLVM import destination parent close failed: {error_type}"
                ) from error


def _link_or_copy_in_parent(
    source_path: Path, destination_path: Path, parent_descriptor: int | None
) -> str:
    """Write under an admitted parent and recheck its physical identity."""
    source, destination = str(source_path), str(destination_path)
    try:
        linked = (
            os.link(source, destination_path.name, dst_dir_fd=parent_descriptor)
            if parent_descriptor is not None
            else os.link(source, destination)
        )
    except OSError:
        owned_inode: tuple[int, int] | None = None
        try:
            with _exclusive_import_target(
                destination_path, parent_descriptor
            ) as target:
                target_fd = target.fileno()
                if type(target_fd) is not int or not _owned_exclusive_descriptor(
                    destination_path, target_fd
                ):
                    _fail("LLVM import fallback copy destination is not owned")
                target_stat = os.fstat(target_fd)
                if type(target_stat) is not os.stat_result:
                    _fail("LLVM import fallback copy destination status is not native")
                owned_inode = (target_stat.st_dev, target_stat.st_ino)
                with source_path.open("rb") as original:
                    source_fd = original.fileno()
                    source_stat = os.fstat(source_fd)
                    if (
                        type(source_fd) is not int
                        or type(source_stat) is not os.stat_result
                        or not _matches_open_import_file(
                            source_path, source_fd, source_stat.st_size
                        )
                    ):
                        _fail("LLVM import fallback copy source is not physical")
                    admitted_source = _marker_identity(source_stat)
                    shutil.copyfileobj(original, target)
                    target.flush()
                    _ = original.seek(0)
                    _ = target.seek(0)
                    while True:
                        source_chunk = original.read(65536)
                        if type(source_chunk) is not bytes:
                            _fail(
                                "LLVM import fallback copy source bytes are not native"
                            )
                        if not source_chunk:
                            break
                        target_chunk = target.read(len(source_chunk))
                        if (
                            type(target_chunk) is not bytes
                            or target_chunk != source_chunk
                        ):
                            _fail("LLVM import fallback copy bytes differ from source")
                    if target.read(1) != b"":
                        _fail("LLVM import fallback copy has trailing bytes")
                    if (
                        _marker_identity(os.fstat(source_fd)) != admitted_source
                        or not _matches_open_import_file(
                            source_path, source_fd, source_stat.st_size
                        )
                        or not _matches_open_import_file(
                            destination_path,
                            target_fd,
                            source_stat.st_size,
                            single_link=True,
                        )
                    ):
                        _fail("LLVM import fallback copy identity changed")
                    # Never apply metadata through a replaceable destination path.
                    os.fchmod(target_fd, S_IMODE(source_stat.st_mode))
                    if not _matches_open_import_file(
                        destination_path,
                        target_fd,
                        source_stat.st_size,
                        single_link=True,
                    ):
                        _fail("LLVM import fallback copy identity changed after chmod")
        except (LlvmImportError, OSError, ValueError, TypeError, RuntimeError) as error:
            if owned_inode is not None:
                try:
                    _discard_owned_file(destination_path, owned_inode)
                except (OSError, ValueError, TypeError, RuntimeError):
                    pass
            raise LlvmImportError(
                f"LLVM import fallback copy failed: {type(error).__name__}"
            ) from error
    else:
        if linked is not None:
            _fail("LLVM import hardlink returned a nonnative completion receipt")
        _attest_import_hardlink(source_path, destination_path)
    if parent_descriptor is not None:
        try:
            opened_parent = os.fstat(parent_descriptor)
            if (
                type(opened_parent) is not os.stat_result
                or not S_ISDIR(opened_parent.st_mode)
                or _native_directory_inode(destination_path.parent)
                != (opened_parent.st_dev, opened_parent.st_ino)
            ):
                _fail("LLVM import destination parent identity changed")
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            error_type = type(error).__name__
            raise LlvmImportError(
                f"LLVM import destination parent status failed: {error_type}"
            ) from error
    return destination


def _import_source_identity(path: Path) -> tuple[int, int, int, int]:
    """Pin source inode, size, and mtime across link or fallback copy.

    Returns:
        Native identity components unaffected by adding hardlinks.

    Raises:
        LlvmImportError: If the host source is not a physical regular file.

    """
    if not _physical_file(path):
        _fail("LLVM import source file must be physical")
    try:
        status = path.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = f"LLVM import source status failed: {type(error).__name__}"
        raise LlvmImportError(message) from error
    if type(status) is not os.stat_result or not S_ISREG(status.st_mode):
        _fail("LLVM import source status must be a native regular file")
    # Link creation changes st_nlink and ctime, not admitted file contents.
    return status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns


def _copy_file(
    source: Path,
    destination: Path,
    *,
    expected_parent_inode: tuple[int, int] | None = None,
) -> None:
    """Create one import file under the originally admitted physical parent."""
    source_identity = _import_source_identity(source)
    original_parent_inode = _native_directory_inode(destination.parent)
    if (
        expected_parent_inode is not None
        and original_parent_inode != expected_parent_inode
    ):
        _fail("LLVM import file parent changed before creation")
    ancestor_inode = _native_directory_inode(destination.parent.parent)
    if ancestor_inode is None:
        _fail("LLVM import file parent ancestor must be physical")
    _create_physical_import_directory(
        destination.parent,
        label="LLVM import file parent",
        expected_parent_inode=ancestor_inode,
        exist_ok=True,
    )
    parent_inode = _native_directory_inode(destination.parent)
    if parent_inode is None or (
        original_parent_inode is not None and parent_inode != original_parent_inode
    ):
        _fail("LLVM import destination parent changed during mkdir")
    _ = _link_or_copy(str(source), str(destination), expected_parent_inode=parent_inode)
    if _import_source_identity(source) != source_identity:
        _fail("LLVM import source file changed during copying")


def _require_physical_resources(root: Path) -> None:
    if not _physical_directory(root):
        _fail("host LLVM resource directory must not redirect")
    try:
        for member in root.rglob("*"):
            if (
                type(member) is not type(root)
                or member == root
                or not member.is_relative_to(root)
                or ".." in member.relative_to(root).parts
            ):
                _fail("host LLVM resource member must be inside its root")
            if not (_physical_file(member) or _physical_directory(member)):
                _fail(f"host LLVM resource member must be physical: {member}")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"host LLVM resource traversal failed: {type(error).__name__}"
        ) from error


def _copy_resource_tree(source: Path, destination: Path) -> None:
    """Copy LLVM resources without creating through replaceable parent names."""
    source_inode = _native_directory_inode(source)
    if source_inode is None:
        _fail("host LLVM resource root must be physical")
    _require_physical_resources(source)
    if _native_directory_inode(source) != source_inode:
        _fail("host LLVM resource root changed during preflight")
    ancestor_inode = _native_directory_inode(destination.parent.parent)
    if ancestor_inode is None:
        _fail("LLVM resource destination ancestor must be physical")
    _create_physical_import_directory(
        destination.parent,
        label="LLVM resource destination parent",
        expected_parent_inode=ancestor_inode,
        exist_ok=True,
    )
    parent_inode = _native_directory_inode(destination.parent)
    if parent_inode is None:
        _fail("LLVM resource destination parent must be physical")

    def copy_directory(
        source_directory: Path,
        destination_directory: Path,
        expected_source_inode: tuple[int, int],
        expected_parent_inode: tuple[int, int],
    ) -> None:
        if _native_directory_inode(source_directory) != expected_source_inode:
            _fail("host LLVM resource directory changed before copying")
        _create_physical_import_directory(
            destination_directory,
            label="LLVM resource member directory",
            expected_parent_inode=expected_parent_inode,
        )
        owned_inode = _native_directory_inode(destination_directory)
        if owned_inode is None:
            _fail("LLVM resource member directory must be physical")
        try:
            for member in source_directory.iterdir():
                if _native_directory_inode(source_directory) != expected_source_inode:
                    _fail("host LLVM resource directory changed during copying")
                if (
                    type(member) is not type(source_directory)
                    or member.parent != source_directory
                    or member.name in ("", ".", "..")
                    or "/" in member.name
                    or "\\" in member.name
                ):
                    _fail("host LLVM resource member must be a direct native child")
                target = destination_directory / member.name
                if _physical_directory(member):
                    child_inode = _native_directory_inode(member)
                    if child_inode is None:
                        _fail("host LLVM resource child directory must be physical")
                    copy_directory(member, target, child_inode, owned_inode)
                elif _physical_file(member):
                    identity = _import_source_identity(member)
                    _ = _link_or_copy(
                        str(member), str(target), expected_parent_inode=owned_inode
                    )
                    if _import_source_identity(member) != identity:
                        _fail("host LLVM resource file changed during copying")
                else:
                    _fail(f"host LLVM resource member must be physical: {member}")
        except LlvmImportError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"host LLVM resource traversal failed: {type(error).__name__}"
            ) from error
        if _native_directory_inode(source_directory) != expected_source_inode:
            _fail("host LLVM resource directory changed after copying")
        if _native_directory_inode(destination_directory) != owned_inode:
            _fail("LLVM resource destination directory changed during copy")

    copy_directory(source, destination, source_inode, parent_inode)
    _require_physical_resources(destination)


def _linux_wrapper(tool: str) -> str:
    return "\n".join(
        (
            "#!/bin/sh",
            'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)',
            'export LD_LIBRARY_PATH="$ROOT/lib"',
            f'exec "$ROOT/bin/{tool}" "$@"',
            "",
        )
    )


def _valid_linux_wrapper(path: Path, tool: str) -> bool:
    """Require the exact executable wrapper bytes on one stable local inode."""
    if not _physical_file(path):
        return False
    expected = _linux_wrapper(tool).encode("utf-8")
    try:
        admitted = path.lstat()
        identity = _marker_identity(admitted)
        if (
            type(admitted) is not os.stat_result
            or admitted.st_nlink != 1
            or S_IMODE(admitted.st_mode) != 0o755
            or admitted.st_size != len(expected)
            or not _stable_marker_descriptor(path, identity, expected)
            or not _physical_file(path)
        ):
            return False
        current = path.lstat()
        return (
            type(current) is os.stat_result
            and S_IMODE(current.st_mode) == 0o755
            and _marker_identity(current) == identity
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _owned_exclusive_descriptor(path: Path, descriptor: int) -> bool:
    """Attest a newly created empty regular inode at an exact leaf."""
    try:
        opened = os.fstat(descriptor)
        named = path.lstat()
        return (
            type(opened) is os.stat_result
            and type(named) is os.stat_result
            and S_ISREG(opened.st_mode)
            and S_ISREG(named.st_mode)
            and opened.st_dev == named.st_dev
            and opened.st_ino == named.st_ino
            and opened.st_nlink == named.st_nlink == 1
            and opened.st_size == named.st_size == 0
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _verify_linux_alias_bytes(path: Path, descriptor: int, content: bytes) -> None:
    """Recheck the owned wrapper inode and its exact on-disk bytes."""
    opened = os.fstat(descriptor)
    named = path.lstat()
    if (
        not _physical_file(path)
        or type(opened) is not os.stat_result
        or type(named) is not os.stat_result
        or not S_ISREG(opened.st_mode)
        or _marker_identity(opened) != _marker_identity(named)
        or opened.st_nlink != 1
    ):
        _fail("LLVM wrapper identity changed during publication")
    if opened.st_size != len(content):
        _fail("LLVM wrapper content length does not match the intended script")
    admitted = _marker_identity(opened)
    offset = os.lseek(descriptor, 0, os.SEEK_SET)
    if type(offset) is not int or offset != 0:
        _fail("LLVM wrapper content read offset is not native")
    observed = bytearray()
    while len(observed) <= len(content):
        chunk = os.read(descriptor, len(content) + 1 - len(observed))
        if type(chunk) is not bytes:
            _fail("LLVM wrapper content read receipt is not native")
        if not chunk:
            break
        observed.extend(chunk)
    if bytes(observed) != content:
        _fail("LLVM wrapper content does not match the intended script")
    if (
        not _physical_file(path)
        or _marker_identity(os.fstat(descriptor)) != admitted
        or _marker_identity(path.lstat()) != admitted
    ):
        _fail("LLVM wrapper identity changed during content verification")


def _write_linux_alias(
    path: Path, text: str, *, expected_parent_inode: tuple[int, int] | None = None
) -> None:
    """Publish an executable wrapper against its original physical parent."""
    if not _physical_directory(path.parent):
        _fail("LLVM wrapper parent must be a physical directory")
    try:
        initial_parent = path.parent.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM wrapper parent status failed: {type(error).__name__}"
        ) from error
    if type(initial_parent) is not os.stat_result or not S_ISDIR(
        initial_parent.st_mode
    ):
        _fail("LLVM wrapper parent status must be native")
    if (
        expected_parent_inode is not None
        and (initial_parent.st_dev, initial_parent.st_ino) != expected_parent_inode
    ):
        _fail("LLVM wrapper parent changed before publication")
    content = text.encode("utf-8")
    parent_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        parent_descriptor = os.open(path.parent, parent_flags)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM wrapper parent open failed: {type(error).__name__}"
        ) from error
    if type(cast("object", parent_descriptor)) is not int or parent_descriptor < 0:
        _fail("LLVM wrapper parent descriptor must be native")
    try:
        opened = os.fstat(parent_descriptor)
        named = path.parent.lstat()
        if (
            not _physical_directory(path.parent)
            or type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            or (opened.st_dev, opened.st_ino)
            != (initial_parent.st_dev, initial_parent.st_ino)
            or (
                expected_parent_inode is not None
                and (opened.st_dev, opened.st_ino) != expected_parent_inode
            )
        ):
            _fail("LLVM wrapper parent descriptor does not match the path")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path.name, flags, 0o600, dir_fd=parent_descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM wrapper exclusive creation failed: {type(error).__name__}"
            ) from error
        if type(cast("object", descriptor)) is not int or descriptor < 0:
            _fail("LLVM wrapper descriptor must be a native nonnegative integer")
        try:
            try:
                if not _owned_exclusive_descriptor(path, descriptor):
                    _fail("LLVM wrapper descriptor does not own the physical leaf")
                written = os.write(descriptor, content)
                if type(written) is not int or written != len(content):
                    _fail(f"LLVM wrapper write count mismatch: {path.name}")
                _verify_linux_alias_bytes(path, descriptor, content)
                # A path chmod would follow an alias swapped after publication.
                os.fchmod(descriptor, 0o755)
                _verify_linux_alias_bytes(path, descriptor, content)
            finally:
                os.close(descriptor)
        except LlvmImportError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM wrapper write failed: {type(error).__name__}"
            ) from error
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM wrapper parent status failed: {type(error).__name__}"
        ) from error
    finally:
        try:
            os.close(parent_descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM wrapper parent close failed: {type(error).__name__}"
            ) from error


def _existing_import_marker(root: Path, platform_id: str) -> bool:
    """Admit only an exact, singly linked marker or a truly absent leaf."""
    marker = root / LLVM_IMPORT_MARKER
    try:
        _ = marker.lstat()
    except FileNotFoundError:
        return False
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import marker status failed: {type(error).__name__}"
        ) from error
    if not _valid_marker(root, platform_id):
        _fail("LLVM import marker already exists without exact physical identity")
    return True


def _discard_owned_file(marker: Path, inode: tuple[int, int]) -> None:
    """Unlink only the same unique file inode opened by this writer."""
    try:
        current = marker.lstat()
    except FileNotFoundError:
        return
    if (
        type(cast("object", current)) is os.stat_result
        and S_ISREG(current.st_mode)
        and current.st_dev == inode[0]
        and current.st_ino == inode[1]
        and current.st_nlink == 1
    ):
        marker.unlink()


def _open_physical_import_parent(root: Path, label: str) -> int:
    """Pin a native physical parent before publishing an import file."""
    if not _physical_directory(root):
        _fail(f"{label} parent must be physical")
    try:
        initial = root.lstat()
        if type(initial) is not os.stat_result or not S_ISDIR(initial.st_mode):
            _fail(f"{label} parent status must be native")
        flags = (
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(root, flags)
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"{label} parent open failed: {type(error).__name__}"
        ) from error
    if type(cast("object", descriptor)) is not int or descriptor < 0:
        _fail(f"{label} parent descriptor must be native")
    try:
        opened = os.fstat(descriptor)
        named = root.lstat()
        if (
            not _physical_directory(root)
            or type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            or (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino)
        ):
            _fail(f"{label} parent descriptor does not match the path")
    except (LlvmImportError, OSError, ValueError, TypeError, RuntimeError) as error:
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError):
            pass
        if isinstance(error, LlvmImportError):
            raise
        raise LlvmImportError(
            f"{label} parent status failed: {type(error).__name__}"
        ) from error
    return descriptor


def _write_import_marker(
    root: Path,
    platform_id: str,
    *,
    expected_parent_inode: tuple[int, int] | None = None,
) -> None:
    """Publish an exclusive marker inside the original physical stage."""
    if (
        expected_parent_inode is not None
        and _native_directory_inode(root) != expected_parent_inode
    ):
        _fail("LLVM import marker parent changed before publication")
    if _existing_import_marker(root, platform_id):
        if (
            expected_parent_inode is not None
            and _native_directory_inode(root) != expected_parent_inode
        ):
            _fail("LLVM import marker parent changed during reuse")
        return
    marker = root / LLVM_IMPORT_MARKER
    content = _marker_bytes(platform_id)
    parent_descriptor = (
        _open_physical_import_parent(root, "LLVM import marker")
        if os.name == "posix"
        else None
    )
    try:
        if expected_parent_inode is not None:
            if parent_descriptor is None:
                # Non-POSIX hosts cannot pin the directory by fd, but must
                # still reject a changed parent before pathname publication.
                if _native_directory_inode(root) != expected_parent_inode:
                    _fail("LLVM import marker parent changed before creation")
            else:
                try:
                    parent_status = os.fstat(parent_descriptor)
                    if (
                        type(parent_status) is not os.stat_result
                        or (parent_status.st_dev, parent_status.st_ino)
                        != expected_parent_inode
                        or _native_directory_inode(root) != expected_parent_inode
                    ):
                        _fail(
                            "LLVM import marker parent changed before exclusive creation"
                        )
                except LlvmImportError:
                    raise
                except (OSError, ValueError, TypeError, RuntimeError) as error:
                    raise LlvmImportError(
                        f"LLVM import marker parent status failed: {type(error).__name__}"
                    ) from error
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        try:
            descriptor = (
                os.open(marker.name, flags, 0o600, dir_fd=parent_descriptor)
                if parent_descriptor is not None
                else os.open(marker, flags, 0o600)
            )
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM import marker exclusive creation failed: {type(error).__name__}"
            ) from error
        if type(cast("object", descriptor)) is not int or descriptor < 0:
            _fail("LLVM import marker descriptor must be a native integer")
        owned_inode: tuple[int, int] | None = None
        try:
            try:
                if not _owned_exclusive_descriptor(marker, descriptor):
                    _fail(
                        "LLVM import marker descriptor does not own its physical leaf"
                    )
                opened = os.fstat(descriptor)
                if type(cast("object", opened)) is not os.stat_result:
                    _fail("LLVM import marker descriptor status must be native")
                owned_inode = (opened.st_dev, opened.st_ino)
                written = os.write(descriptor, content)
            finally:
                os.close(descriptor)
        except LlvmImportError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            if owned_inode is not None:
                try:
                    _discard_owned_file(marker, owned_inode)
                except (OSError, ValueError, TypeError, RuntimeError):
                    pass
            raise LlvmImportError(
                f"LLVM import marker write failed: {type(error).__name__}"
            ) from error
        if (
            type(written) is int
            and written == len(content)
            and _valid_marker(root, platform_id)
        ):
            return
        if owned_inode is not None:
            try:
                _discard_owned_file(marker, owned_inode)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                error_type = type(error).__name__
                raise LlvmImportError(
                    f"LLVM marker write count mismatch; cleanup failed: {error_type}"
                ) from error
        _fail("LLVM marker write count or content verification mismatch")

    finally:
        if parent_descriptor is not None:
            try:
                os.close(parent_descriptor)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise LlvmImportError(
                    f"LLVM import marker parent close failed: {type(error).__name__}"
                ) from error


def _write_linux_aliases(root: Path) -> tuple[Path, ...]:
    aliases: list[Path] = []
    alias_root = root / "jig-bin"
    _create_physical_import_directory(alias_root, label="LLVM import staging aliases")
    alias_inode = _native_directory_inode(alias_root)
    if alias_inode is None:
        _fail("LLVM wrapper alias parent must be physical")
    for tool in _TOOL_NAMES:
        alias = alias_root / f"{tool}.bin"
        _write_linux_alias(
            alias, _linux_wrapper(tool), expected_parent_inode=alias_inode
        )
        aliases.append(alias)
    return tuple(aliases)


def _validate_observation(observation: LlvmHostObservation) -> None:
    if observation.version != LLVM_VERSION:
        _fail(
            "".join(
                (
                    "host LLVM version mismatch: ",
                    f"{observation.version} != {LLVM_VERSION}",
                )
            )
        )
    files = (
        observation.clang,
        observation.clang_tidy,
        observation.clang_format,
        observation.clang_cpp,
        observation.llvm,
    )
    if not all(_physical_file(path) for path in files):
        _fail("host LLVM observation has a missing or redirected tool")
    _require_physical_resources(observation.resource_dir)


def _stage_linux_llvm(
    staged: Path,
    observation: LlvmHostObservation,
    *,
    expected_staged_inode: tuple[int, int] | None = None,
) -> None:
    for tool, source in (
        ("clang", observation.clang),
        ("clang-tidy", observation.clang_tidy),
        ("clang-format", observation.clang_format),
    ):
        _copy_file(source, staged / "bin" / tool)
    for soname, source in zip(
        _LLVM_LIBRARY_NAMES, (observation.llvm, observation.clang_cpp), strict=True
    ):
        _copy_file(source, staged / "lib" / soname)
    _copy_resource_tree(
        observation.resource_dir,
        staged / "lib" / "clang" / "22",
    )
    _ = _write_linux_aliases(staged)
    _write_import_marker(
        staged, LINUX_PLATFORM, expected_parent_inode=expected_staged_inode
    )


def _admit_linux_import_staging(root: Path, staging: Path) -> None:
    """Fail closed before cleanup or writes through redirected staging paths."""
    root_inode = _native_directory_inode(root)
    if root_inode is None:
        _fail("LLVM import staging repository root must be physical")
    temporary_root = root / ".temp"
    if temporary_root.is_symlink() or temporary_root.is_junction():
        _fail("LLVM import staging root must not redirect")
    if not temporary_root.exists():
        try:
            _create_physical_import_directory(
                temporary_root,
                label="LLVM import staging root",
                expected_parent_inode=root_inode,
            )
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM import staging root creation failed: {type(error).__name__}"
            ) from error
    if not _physical_directory(temporary_root):
        _fail("LLVM import staging root must be a physical directory")
    if staging.is_symlink() or staging.is_junction():
        _fail("LLVM import staging directory must not redirect")
    if staging.exists() and not _physical_directory(staging):
        _fail("LLVM import staging directory must be physical")


def _create_physical_import_directory(
    path: Path,
    *,
    label: str,
    expected_parent_inode: tuple[int, int] | None = None,
    exist_ok: bool = False,
) -> None:
    """Create or admit a directory under its original pinned physical parent."""
    if not _MKDIR_SUPPORTS_DIR_FD:
        if os.supports_dir_fd:
            _fail(f"{label} requires native directory-descriptor mkdir support")
        # Windows has no dir_fd support; Linux stages require pinned parents.
        try:
            path.mkdir(exist_ok=exist_ok)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"{label} directory creation failed: {type(error).__name__}"
            ) from error
        if expected_parent_inode is not None and (
            _native_directory_inode(path.parent) != expected_parent_inode
        ):
            _fail(f"{label} parent changed during directory creation")
        if _native_directory_inode(path) is None:
            _fail(f"{label} created directory must be physical")
        return
    parent_descriptor = _open_physical_import_parent(path.parent, label)
    try:
        opened = os.fstat(parent_descriptor)
        if type(opened) is not os.stat_result or not S_ISDIR(opened.st_mode):
            _fail(f"{label} parent descriptor status must be native")
        opened_inode = (opened.st_dev, opened.st_ino)
        if expected_parent_inode is not None and opened_inode != expected_parent_inode:
            _fail(f"{label} parent changed before directory creation")
        try:
            os.mkdir(path.name, dir_fd=parent_descriptor)
        except FileExistsError:
            if not exist_ok:
                raise
        if _native_directory_inode(path.parent) != opened_inode:
            _fail(f"{label} parent changed during directory creation")
        if _native_directory_inode(path) is None:
            _fail(f"{label} created directory must be physical")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"{label} directory creation failed: {type(error).__name__}"
        ) from error
    finally:
        try:
            os.close(parent_descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"{label} parent close failed: {type(error).__name__}"
            ) from error


def _native_directory_inode(path: Path) -> tuple[int, int] | None:
    """Observe a real physical directory, or refuse an untrusted path."""
    try:
        if not _physical_directory(path):
            return None
        status = path.lstat()
        if type(status) is not os.stat_result or not S_ISDIR(status.st_mode):
            return None
        return status.st_dev, status.st_ino
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _owned_staging_safe_to_clean(
    staging: Path,
    staged: Path,
    owned_staging: tuple[int, int],
    owned_child: tuple[int, int] | None,
) -> bool:
    """Avoid recursively deleting an unowned substitute in the stage tree."""
    if _native_directory_inode(staging) != owned_staging:
        return False
    try:
        _ = staged.lstat()
    except FileNotFoundError:
        return True
    except (OSError, ValueError, TypeError, RuntimeError):
        return False
    return owned_child is not None and _native_directory_inode(staged) == owned_child


def _remove_pinned_import_contents(parent_fd: int) -> None:
    """Delete staged members only under physically pinned directory handles."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.scandir(parent_fd) as members:
        for member in members:
            if type(member) is not os.DirEntry:
                _fail("LLVM staging cleanup member receipt must be native")
            name = member.name
            if (
                type(name) is not str
                or name in ("", ".", "..")
                or os.path.basename(name) != name
                or "/" in name
                or "\\" in name
            ):
                _fail("LLVM staging cleanup member name must be a single leaf")
            admitted = member.stat(follow_symlinks=False)
            if type(admitted) is not os.stat_result:
                _fail("LLVM staging cleanup member status must be native")
            expected_inode = admitted.st_dev, admitted.st_ino
            if S_ISDIR(admitted.st_mode):
                child_fd: int | None = None
                try:
                    child_fd = os.open(member.name, flags, dir_fd=parent_fd)
                    if type(cast("object", child_fd)) is not int or child_fd < 0:
                        _fail("LLVM staging cleanup member descriptor must be native")
                    opened = os.fstat(child_fd)
                    if (
                        type(opened) is not os.stat_result
                        or not S_ISDIR(opened.st_mode)
                        or (opened.st_dev, opened.st_ino) != expected_inode
                    ):
                        _fail("LLVM staging cleanup member changed before recursion")
                    _remove_pinned_import_contents(child_fd)
                    named = os.stat(
                        member.name, dir_fd=parent_fd, follow_symlinks=False
                    )
                    if (
                        type(named) is not os.stat_result
                        or not S_ISDIR(named.st_mode)
                        or (named.st_dev, named.st_ino) != expected_inode
                    ):
                        _fail("LLVM staging cleanup member changed before removal")
                    receipt = os.rmdir(member.name, dir_fd=parent_fd)
                    if receipt is not None:
                        _fail(
                            "LLVM staging cleanup member removal receipt must be native"
                        )
                finally:
                    if type(child_fd) is int and child_fd >= 0:
                        os.close(child_fd)
            elif S_ISREG(admitted.st_mode):
                named = os.stat(member.name, dir_fd=parent_fd, follow_symlinks=False)
                if (
                    type(named) is not os.stat_result
                    or not S_ISREG(named.st_mode)
                    or (named.st_dev, named.st_ino) != expected_inode
                ):
                    _fail("LLVM staging cleanup file changed before unlink")
                receipt = os.unlink(member.name, dir_fd=parent_fd)
                if receipt is not None:
                    _fail("LLVM staging cleanup unlink receipt must be native")
            else:
                _fail(
                    "LLVM staging cleanup member must be a physical file or directory"
                )


def _cleanup_owned_linux_staging(
    staging: Path,
    staged: Path,
    owned_staging: tuple[int, int],
    owned_child: tuple[int, int] | None,
) -> None:
    """Remove only the owned staging tree through pinned directory handles."""
    if os.name != "posix":
        # Linux import is used on Linux; keep legacy simulation support on
        # hosts without descriptor-relative directory operations.
        shutil.rmtree(staging)
        return
    parent_fd: int | None = None
    staging_fd: int | None = None
    child_fd: int | None = None
    try:
        parent_fd = _open_physical_import_parent(staging.parent, "LLVM staging cleanup")
        flags = (
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        )
        staging_fd = os.open(staging.name, flags, dir_fd=parent_fd)
        if type(cast("object", staging_fd)) is not int or staging_fd < 0:
            _fail("LLVM staging cleanup directory descriptor must be native")
        opened = os.fstat(staging_fd)
        if (
            type(opened) is not os.stat_result
            or not S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != owned_staging
            or _native_directory_inode(staging) != owned_staging
        ):
            _fail("LLVM staging cleanup directory identity changed")
        try:
            child = os.stat(staged.name, dir_fd=staging_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if (
                type(child) is not os.stat_result
                or not S_ISDIR(child.st_mode)
                or (child.st_dev, child.st_ino) != owned_child
            ):
                _fail("LLVM staging cleanup child identity changed")
            child_fd = os.open(staged.name, flags, dir_fd=staging_fd)
            if type(cast("object", child_fd)) is not int or child_fd < 0:
                _fail("LLVM staging cleanup child descriptor must be native")
            opened_child = os.fstat(child_fd)
            if (
                type(opened_child) is not os.stat_result
                or not S_ISDIR(opened_child.st_mode)
                or (opened_child.st_dev, opened_child.st_ino) != owned_child
            ):
                _fail("LLVM staging cleanup child descriptor identity changed")
            _remove_pinned_import_contents(child_fd)
            named_child = os.stat(staged.name, dir_fd=staging_fd, follow_symlinks=False)
            if (
                type(named_child) is not os.stat_result
                or (named_child.st_dev, named_child.st_ino) != owned_child
            ):
                _fail("LLVM staging cleanup child changed during removal")
            child_receipt = os.rmdir(staged.name, dir_fd=staging_fd)
            if child_receipt is not None:
                _fail("LLVM staging cleanup child removal receipt must be native")
        if _native_directory_inode(staging) != owned_staging:
            _fail("LLVM staging cleanup directory changed before removal")
        final_status = os.stat(staging.name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            type(final_status) is not os.stat_result
            or (final_status.st_dev, final_status.st_ino) != owned_staging
        ):
            _fail("LLVM staging cleanup original directory was replaced")
        receipt = os.rmdir(staging.name, dir_fd=parent_fd)
        if receipt is not None:
            _fail("LLVM staging cleanup removal receipt must be native")
        try:
            _ = os.stat(staging.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _fail("LLVM staging cleanup did not remove the owned directory")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM staging cleanup failed: {type(error).__name__}"
        ) from error
    finally:
        for descriptor in (child_fd, staging_fd, parent_fd):
            if type(descriptor) is int and descriptor >= 0:
                try:
                    os.close(descriptor)
                except (OSError, ValueError, TypeError, RuntimeError) as error:
                    raise LlvmImportError(
                        f"LLVM staging cleanup close failed: {type(error).__name__}"
                    ) from error


def _require_absent_import_destination(destination: Path) -> None:
    """Reject late occupancy using native leaf status before publication."""
    try:
        _ = destination.lstat()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import destination status failed: {type(error).__name__}"
        ) from error
    _fail("LLVM import destination became occupied before publication")


def _ensure_physical_import_parent(root: Path) -> Path:
    """Create and admit the final destination without following parent aliases."""
    parent_inode = _native_directory_inode(root)
    if parent_inode is None:
        _fail("LLVM import destination repository root must be physical")
    parent = root
    for component in (".dependencies", "llvm"):
        child = parent / component
        _create_physical_import_directory(
            child,
            label="LLVM import destination parent",
            expected_parent_inode=parent_inode,
            exist_ok=True,
        )
        child_inode = _native_directory_inode(child)
        if child_inode is None:
            _fail("LLVM import destination parent must be physical")
        parent, parent_inode = child, child_inode
    return parent


def _rename_linux_import_no_replace(
    source: Path, destination: str, *, src_dir_fd: int, dst_dir_fd: int
) -> None:
    """Atomically move a Linux import without replacing an occupied leaf.

    Linux renameat2 with RENAME_NOREPLACE is required: os.replace can erase a
    concurrently inserted empty directory after our last absence check.
    """
    opened_source_parent = os.fstat(src_dir_fd)
    if type(opened_source_parent) is not os.stat_result or _native_directory_inode(
        source.parent
    ) != (opened_source_parent.st_dev, opened_source_parent.st_ino):
        _fail("LLVM import staging source parent changed before rename")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError) as error:
        raise LlvmImportError(
            "LLVM import requires native Linux no-replace directory rename"
        ) from error
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = cast(
        "object",
        renameat2(
            src_dir_fd,
            os.fsencode(source.name),
            dst_dir_fd,
            os.fsencode(destination),
            _LINUX_RENAME_NOREPLACE,
        ),
    )
    if type(result) is not int:
        _fail("LLVM import rename receipt must be a native integer")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number == errno.EEXIST:
            _fail("LLVM import destination became occupied during publication")
        raise OSError(error_number, "LLVM import no-replace directory rename failed")


def _publish_linux_import(root: Path, staged: Path, destination: Path) -> None:
    """Pin the physical destination directory across the final rename."""
    parent = _ensure_physical_import_parent(root)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(parent, flags)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import destination parent open failed: {type(error).__name__}"
        ) from error
    if type(cast("object", descriptor)) is not int or descriptor < 0:
        _fail("LLVM import destination parent descriptor must be native")
    try:
        opened = os.fstat(descriptor)
        named = parent.lstat()
        if (
            not _physical_directory(parent)
            or type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("LLVM import destination parent descriptor mismatch")
        _require_absent_import_destination(destination)
        try:
            _ = os.stat(destination.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM import destination status failed: {type(error).__name__}"
            ) from error
        else:
            _fail("LLVM import destination became occupied before publication")
        staged_inode = _native_directory_inode(staged)
        if staged_inode is None:
            _fail("LLVM import staging source must be physical")
        source_parent_fd = _open_physical_import_parent(
            staged.parent, "LLVM import staging source"
        )
        try:
            source_status = os.stat(
                staged.name, dir_fd=source_parent_fd, follow_symlinks=False
            )
            if (
                type(source_status) is not os.stat_result
                or not S_ISDIR(source_status.st_mode)
                or (source_status.st_dev, source_status.st_ino) != staged_inode
            ):
                _fail("LLVM import staging source changed before rename")
            published = _rename_linux_import_no_replace(
                staged,
                destination.name,
                src_dir_fd=source_parent_fd,
                dst_dir_fd=descriptor,
            )
        finally:
            try:
                os.close(source_parent_fd)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                error_type = type(error).__name__
                raise LlvmImportError(
                    f"LLVM import staging source parent close failed: {error_type}"
                ) from error
        if _native_directory_inode(parent) != (opened.st_dev, opened.st_ino):
            _fail("LLVM import destination parent changed during publication")
        if (
            published is not None
            or _native_directory_inode(destination) != staged_inode
            or _native_directory_inode(staged) is not None
        ):
            _fail("LLVM import destination publication did not move staged inode")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import destination publication failed: {type(error).__name__}"
        ) from error
    finally:
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            error_type = type(error).__name__
            raise LlvmImportError(
                f"LLVM import destination parent close failed: {error_type}"
            ) from error


def import_linux_llvm(root: Path, observation: LlvmHostObservation) -> Path:
    """Import one exact Linux LLVM runtime into repository-local state.

    Returns:
        Repository-local LLVM root after atomic import or exact reuse.

    """
    _validate_observation(observation)
    destination = root / LLVM_ROOT
    if _runtime_ready(destination, LINUX_PLATFORM):
        return destination
    if destination.exists() or destination.is_symlink() or destination.is_junction():
        _fail("repository-local LLVM exists without the exact import marker")
    staging = root / ".temp" / "llvm-import-linux-x86_64"
    _admit_linux_import_staging(root, staging)
    try:
        _ = staging.lstat()
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import staging occupancy status failed: {type(error).__name__}"
        ) from error
    else:
        _fail("LLVM import staging is occupied without an ownership receipt")
    _admit_linux_import_staging(root, staging)
    staged = staging / "llvm"
    owned_staging: tuple[int, int] | None = None
    owned_child: tuple[int, int] | None = None
    try:
        _create_physical_import_directory(
            staging, label="LLVM import staging exclusive creation"
        )
        owned_staging = _native_directory_inode(staging)
        if owned_staging is None:
            _fail("LLVM import staging directory must be physical")
        _create_physical_import_directory(staged, label="LLVM import staging child")
        owned_child = _native_directory_inode(staged)
        if owned_child is None:
            _fail("LLVM import staging child must be physical")
        _stage_linux_llvm(staged, observation, expected_staged_inode=owned_child)
        _admit_linux_import_staging(root, staging)
        if (
            _native_directory_inode(staging) != owned_staging
            or _native_directory_inode(staged) != owned_child
        ):
            _fail("LLVM import staging identity changed before publication")
        _publish_linux_import(root, staged, destination)
    finally:
        if owned_staging is not None and _owned_staging_safe_to_clean(
            staging, staged, owned_staging, owned_child
        ):
            _cleanup_owned_linux_staging(staging, staged, owned_staging, owned_child)
    return destination


def _windows_alias_ready(source: Path, alias: Path) -> bool:
    """Reject a copied PE alias that no longer matches its physical source."""
    if not _physical_file(source) or not _physical_file(alias):
        return False
    try:
        source_stat = source.lstat()
        alias_stat = alias.lstat()
        source_id = _marker_identity(source_stat)
        alias_id = _marker_identity(alias_stat)
        same_inode = (source_stat.st_dev, source_stat.st_ino) == (
            alias_stat.st_dev,
            alias_stat.st_ino,
        )
        expected_links = 2 if same_inode else 1
        if (
            source_stat.st_size != alias_stat.st_size
            or source_stat.st_nlink != expected_links
            or alias_stat.st_nlink != expected_links
        ):
            return False
        if not same_inode:
            with source.open("rb") as original, alias.open("rb") as copied:
                if (
                    _marker_identity(os.fstat(original.fileno())) != source_id
                    or _marker_identity(os.fstat(copied.fileno())) != alias_id
                ):
                    return False
                while True:
                    original_chunk = original.read(65536)
                    copied_chunk = copied.read(65536)
                    if (
                        type(original_chunk) is not bytes
                        or type(copied_chunk) is not bytes
                        or original_chunk != copied_chunk
                    ):
                        return False
                    if not original_chunk:
                        break
                if (
                    _marker_identity(os.fstat(original.fileno())) != source_id
                    or _marker_identity(os.fstat(copied.fileno())) != alias_id
                ):
                    return False
        return (
            _physical_file(source)
            and _physical_file(alias)
            and _marker_identity(source.lstat()) == source_id
            and _marker_identity(alias.lstat()) == alias_id
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _require_matching_windows_alias(source: Path, alias: Path) -> None:
    if not _windows_alias_ready(source, alias):
        _fail(f"Windows LLVM alias mismatch or borrowed physical identity: {alias}")


def _admit_windows_alias(source: Path, alias: Path) -> bool:
    """Require a physical matching alias, or prove its leaf truly absent."""
    if not _physical_file(source):
        _fail(f"Windows LLVM source tool must be physical: {source}")
    try:
        status = alias.lstat()
    except FileNotFoundError:
        return False
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"Windows LLVM alias status failed: {type(error).__name__}"
        ) from error
    if type(status) is not os.stat_result:
        _fail("Windows LLVM alias status must be native")
    _require_matching_windows_alias(source, alias)
    return True


def _windows_alias_directory(root: Path) -> Path:
    """Verify Windows root and alias directory without following redirects.

    Returns:
        Physical or truly absent directory intended for neutral aliases.

    """
    if not _physical_directory(root):
        _fail("Windows LLVM bundle root must be physical")
    alias_root = root / "jig-bin"
    try:
        status = alias_root.lstat()
    except FileNotFoundError:
        return alias_root
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"Windows LLVM alias directory status failed: {type(error).__name__}"
        ) from error
    if type(status) is not os.stat_result or not _physical_directory(alias_root):
        _fail("Windows LLVM alias directory must not redirect")
    return alias_root


def write_windows_llvm_aliases(root: Path) -> tuple[Path, ...]:
    """Create neutral aliases from an existing exact Windows LLVM bundle.

    Returns:
        Neutral aliases containing the exact existing Windows PE bytes.

    """
    alias_root = _windows_alias_directory(root)
    root_inode = _native_directory_inode(root)
    if root_inode is None:
        _fail("Windows LLVM bundle root must be physical")
    existing_alias_inode = _native_directory_inode(alias_root)
    pairs = tuple(
        (
            root / "bin" / f"{tool}.exe",
            alias_root / f"{tool}.bin",
        )
        for tool in _TOOL_NAMES
    )
    # Check existing markers and aliases before publishing any new aliases.
    _ = _existing_import_marker(root, WINDOWS_PLATFORM)
    existing = tuple(_admit_windows_alias(source, alias) for source, alias in pairs)
    _create_physical_import_directory(
        alias_root,
        label="Windows LLVM alias directory",
        expected_parent_inode=root_inode,
        exist_ok=existing_alias_inode is not None,
    )
    alias_inode = _native_directory_inode(alias_root)
    if alias_inode is None or (
        existing_alias_inode is not None and alias_inode != existing_alias_inode
    ):
        _fail("Windows LLVM alias directory changed during creation")
    for (source, alias), present in zip(pairs, existing, strict=True):
        if _native_directory_inode(root) != root_inode:
            _fail("Windows LLVM bundle root changed during alias publication")
        if not present:
            _copy_file(source, alias, expected_parent_inode=alias_inode)
    if not all(_windows_alias_ready(source, alias) for source, alias in pairs):
        _fail("Windows LLVM alias evidence changed before marker publication")
    if _native_directory_inode(root) != root_inode:
        _fail("Windows LLVM bundle root changed before marker publication")
    _write_import_marker(root, WINDOWS_PLATFORM, expected_parent_inode=root_inode)
    return tuple(alias for _, alias in pairs)


def inspect_llvm(root: Path, platform_id: str) -> LlvmReadiness:
    """Inspect neutral LLVM validation aliases for one supported host.

    Returns:
        Readiness plus the canonical neutral Clang alias path.

    """
    llvm_root = root / LLVM_ROOT
    alias_root = llvm_root / "jig-bin"
    clang = alias_root / "clang.bin"
    ready = _runtime_ready(llvm_root, platform_id)
    detail = (
        "exact neutral LLVM 22.1.8 aliases are present"
        if ready
        else "exact neutral LLVM 22.1.8 aliases are absent"
    )
    return LlvmReadiness(ready=ready, path=clang, detail=detail)


def _capture(arguments: list[str]) -> str | None:
    """Observe a native host tool only through its exact process receipt."""
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            arguments.copy(),
            check=False,
            capture_output=True,
            shell=False,
            text=True,
            timeout=_HOST_CAPTURE_TIMEOUT_SECONDS,
        )
    except (OSError, ValueError, TypeError, RuntimeError, sp.TimeoutExpired):
        return None
    if type(completed) is not sp.CompletedProcess:
        return None
    receipt_args = cast("object", completed.args)
    if type(receipt_args) is not list:
        return None
    argv = cast("list[object]", receipt_args)
    if (
        len(argv) != len(arguments)
        or any(type(argument) is not str for argument in argv)
        or argv != arguments
        or type(completed.returncode) is not int
        or type(completed.stdout) is not str
        or type(completed.stderr) is not str
        or completed.returncode != 0
        or completed.stderr
    ):
        return None
    if max(len(completed.stdout), len(completed.stderr)) > _HOST_MAX_CAPTURE_CHARS:
        return None
    # Host version, resource-root, and loader receipts are authority evidence;
    # trimming could silently erase malformed padding or control separators.
    exact_receipt = len(arguments) == 2 and (
        arguments[1] in ("--version", "-print-resource-dir") or arguments[0] == "ldd"
    )
    output = completed.stdout if exact_receipt else completed.stdout.strip()
    return output or None


def _observed_tool(name: str) -> Path | None:
    """Return a native physical host tool or mark optional discovery absent."""
    try:
        resolved = shutil.which(name)
        if type(resolved) is not str or not resolved:
            return None
        path = Path(resolved).resolve(strict=True)
        return path if _physical_file(path) else None
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _ldd_library(executable: Path, soname: str) -> Path | None:
    output = _capture(["ldd", str(executable)])
    if output is None:
        return None
    # GNU ldd emits printable text, indentation tabs, and line feeds. Reject
    # other separators rather than letting splitlines hide a forged record.
    output = output.replace("\r\n", "\n")
    if any(
        not character.isprintable() and character not in "\n\t" for character in output
    ):
        return None
    prefix = f"{soname} => "
    stripped_lines = (line.strip() for line in output.splitlines())
    matches = [line for line in stripped_lines if line.startswith(prefix)]
    # Multiple records for a single soname are ambiguous, even if the first
    # receipt resolves to a physical library.
    if len(matches) != 1:
        return None
    mapping = matches[0].removeprefix(prefix)
    # The address trailer is required; do not admit a truncated or diagnostic
    # line. A greedy pathname keeps legitimate parenthesized directories.
    parsed = re.fullmatch(r"(/.+) \(0x[0-9a-fA-F]+\)", mapping)
    if parsed is None:
        return None
    try:
        path = Path(parsed.group(1))
        if not path.is_absolute():
            return None
        resolved = path.resolve(strict=True)
        return resolved if _physical_file(resolved) else None
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _linux_tool_paths() -> tuple[Path, Path, Path] | None:
    clang = _observed_tool("clang")
    clang_tidy = _observed_tool("clang-tidy")
    clang_format = _observed_tool("clang-format")
    if clang is None or clang_tidy is None or clang_format is None:
        return None
    return clang, clang_tidy, clang_format


def _linux_tool_versions_match(tools: tuple[Path, Path, Path]) -> bool:
    return all(
        (version := _capture([str(tool), "--version"])) is not None
        and llvm_version_matches(version)
        for tool in tools
    )


def _linux_runtime_paths(clang: Path) -> tuple[Path, Path, Path] | None:
    resource_text = _capture([str(clang), "-print-resource-dir"])
    clang_cpp = _ldd_library(clang, _LLVM_LIBRARY_NAMES[1])
    llvm = _ldd_library(clang, _LLVM_LIBRARY_NAMES[0])
    if resource_text is None or clang_cpp is None or llvm is None:
        return None
    # Clang normally emits one absolute directory path with an optional final
    # native line ending. Do not silently admit extra lines or padding.
    if resource_text.endswith("\r\n"):
        resource_text = resource_text[:-2]
    elif resource_text.endswith("\n"):
        resource_text = resource_text[:-1]
    if (
        not resource_text
        or resource_text != resource_text.strip()
        or not resource_text.isprintable()
    ):
        return None
    try:
        reported = Path(resource_text)
        if not reported.is_absolute():
            return None
        resource_dir = reported.resolve(strict=True)
    except (OSError, ValueError, TypeError, RuntimeError):
        return None
    if not _physical_directory(resource_dir):
        return None
    return resource_dir, clang_cpp, llvm


def observe_linux_llvm_host() -> LlvmHostObservation | None:
    """Observe an already-installed exact Linux LLVM without installing it.

    Returns:
        Exact host observation, or ``None`` when any pinned input is absent.

    """
    tools = _linux_tool_paths()
    if tools is None or not _linux_tool_versions_match(tools):
        return None
    clang, clang_tidy, clang_format = tools
    runtime = _linux_runtime_paths(clang)
    if runtime is None:
        return None
    resource_dir, clang_cpp, llvm = runtime
    return LlvmHostObservation(
        clang=clang,
        clang_format=clang_format,
        clang_tidy=clang_tidy,
        clang_cpp=clang_cpp,
        llvm=llvm,
        resource_dir=resource_dir,
        version=LLVM_VERSION,
    )
