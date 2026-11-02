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

import os
import re
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from dataclasses import dataclass
from io import BufferedReader
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
    lines = version_text.splitlines()
    if not lines:
        return False
    # Clang/clang-format identify their own release on the first line.  A
    # diagnostic elsewhere in stdout cannot attest the installed executable.
    suffix = re.escape(LLVM_VERSION) + r"(?=$|[ \t(])"
    if re.match(
        r"^(?:(?:Ubuntu|Debian|Apple) )?clang(?:-format)? version " + suffix,
        lines[0],
    ):
        return True
    # clang-tidy uses LLVM's two-line banner rather than "clang-tidy version".
    return (
        lines[0] == "LLVM (http://llvm.org/):"
        and len(lines) > 1
        and re.match(r"^  LLVM version " + suffix, lines[1]) is not None
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
        if type(cast("object", stream_fd)) is not int or stream_fd != descriptor:
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
        return _physical_directory(root / "lib/clang/22") and all(
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


def _link_or_copy(source: str, destination: str) -> str:
    """Import a new file without overwriting a raced destination link."""
    source_path = Path(source)
    destination_path = Path(destination)
    if not _physical_directory(destination_path.parent):
        _fail("LLVM import destination parent must be physical")
    try:
        linked = os.link(source, destination)
    except OSError:
        owned_inode: tuple[int, int] | None = None
        try:
            with destination_path.open("x+b") as target:
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
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = _link_or_copy(str(source), str(destination))


def _require_physical_resources(root: Path) -> None:
    if not _physical_directory(root):
        _fail("host LLVM resource directory must not redirect")
    try:
        for member in root.rglob("*"):
            if not (_physical_file(member) or _physical_directory(member)):
                _fail(f"host LLVM resource member must be physical: {member}")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"host LLVM resource traversal failed: {type(error).__name__}"
        ) from error


def _copy_resource_tree(source: Path, destination: Path) -> None:
    _require_physical_resources(source)
    _ = shutil.copytree(
        source,
        destination,
        copy_function=_link_or_copy,
        symlinks=True,
    )
    # Reject links introduced while copytree was traversing the host source.
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
    if observed != content:
        _fail("LLVM wrapper content does not match the intended script")
    if (
        not _physical_file(path)
        or _marker_identity(os.fstat(descriptor)) != admitted
        or _marker_identity(path.lstat()) != admitted
    ):
        _fail("LLVM wrapper identity changed during content verification")


def _write_linux_alias(path: Path, text: str) -> None:
    """Publish a complete executable wrapper through an exclusive descriptor."""
    if not _physical_directory(path.parent):
        _fail("LLVM wrapper parent must be a physical directory")
    content = text.encode("utf-8")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
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
            # A path chmod would follow an alias swapped in after publication.
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


def _write_import_marker(root: Path, platform_id: str) -> None:
    """Publish an exclusive marker or reuse only exact physical evidence."""
    if _existing_import_marker(root, platform_id):
        return
    marker = root / LLVM_IMPORT_MARKER
    content = _marker_bytes(platform_id)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(marker, flags, 0o600)
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
                _fail("LLVM import marker descriptor does not own its physical leaf")
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
            raise LlvmImportError(
                f"LLVM marker write count mismatch; cleanup failed: {type(error).__name__}"
            ) from error
    _fail("LLVM marker write count or content verification mismatch")


def _write_linux_aliases(root: Path) -> tuple[Path, ...]:
    aliases: list[Path] = []
    alias_root = root / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    for tool in _TOOL_NAMES:
        alias = alias_root / f"{tool}.bin"
        _write_linux_alias(alias, _linux_wrapper(tool))
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
    _write_import_marker(staged, LINUX_PLATFORM)


def _admit_linux_import_staging(root: Path, staging: Path) -> None:
    """Fail closed before cleanup or writes through redirected staging paths."""
    if not _physical_directory(root):
        _fail("LLVM import staging repository root must be physical")
    temporary_root = root / ".temp"
    if temporary_root.is_symlink() or temporary_root.is_junction():
        _fail("LLVM import staging root must not redirect")
    if not temporary_root.exists():
        try:
            temporary_root.mkdir()
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
    if not _physical_directory(root):
        _fail("LLVM import destination repository root must be physical")
    parent = root
    for component in (".dependencies", "llvm"):
        parent = parent / component
        try:
            parent.mkdir()
        except FileExistsError:
            pass
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM import destination parent creation failed: {type(error).__name__}"
            ) from error
        if not _physical_directory(parent):
            _fail("LLVM import destination parent must be physical")
    return parent


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
        _ = os.replace(staged, destination.name, dst_dir_fd=descriptor)
        if not _physical_directory(parent):
            _fail("LLVM import destination parent changed during publication")
    except LlvmImportError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM import destination publication failed: {type(error).__name__}"
        ) from error
    finally:
        os.close(descriptor)


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
        try:
            staging.mkdir()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmImportError(
                f"LLVM import staging exclusive creation failed: {type(error).__name__}"
            ) from error
        owned_staging = _native_directory_inode(staging)
        if owned_staging is None:
            _fail("LLVM import staging directory must be physical")
        staged.mkdir()
        owned_child = _native_directory_inode(staged)
        if owned_child is None:
            _fail("LLVM import staging child must be physical")
        _stage_linux_llvm(staged, observation)
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
            shutil.rmtree(staging)
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
    alias_root.mkdir(parents=True, exist_ok=True)
    if not _physical_directory(alias_root):
        _fail("Windows LLVM alias directory must not redirect")
    for (source, alias), present in zip(pairs, existing, strict=True):
        if not present:
            _copy_file(source, alias)
    if not all(_windows_alias_ready(source, alias) for source, alias in pairs):
        _fail("Windows LLVM alias evidence changed before marker publication")
    _write_import_marker(root, WINDOWS_PLATFORM)
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
    ):
        return None
    if max(len(completed.stdout), len(completed.stderr)) > _HOST_MAX_CAPTURE_CHARS:
        return None
    output = completed.stdout.strip()
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
    prefix = f"{soname} => "
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        path_text = stripped.removeprefix(prefix).split(" (", 1)[0]
        try:
            path = Path(path_text)
            if not path.is_absolute():
                return None
            resolved = path.resolve(strict=True)
            return resolved if _physical_file(resolved) else None
        except (OSError, ValueError, TypeError, RuntimeError):
            return None
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
    try:
        resource_dir = Path(resource_text).resolve(strict=True)
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
