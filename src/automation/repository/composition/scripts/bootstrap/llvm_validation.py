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

import filecmp
import os
import re
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISREG
from typing import Final, Never, cast

LLVM_VERSION: Final = "22.1.8"
LLVM_ROOT: Final = Path(".dependencies/llvm") / LLVM_VERSION
LLVM_IMPORT_MARKER: Final = ".malbolge-llvm-import-v1"
LINUX_PLATFORM: Final = "linux-x86_64"
WINDOWS_PLATFORM: Final = "windows-x86_64"
_TOOL_NAMES: Final = ("clang", "clang-tidy", "clang-format")
_LLVM_LIBRARY_NAMES: Final = ("libLLVM.so.22.1", "libclang-cpp.so.22.1")


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
    """Match one tool banner against the exact pinned LLVM version.

    Returns:
        Whether the banner contains the exact pinned release identity.

    """
    exact = re.compile(r"(?<![\w.+-])" + re.escape(LLVM_VERSION) + r"(?![\w.+-])")
    return any(exact.search(line) is not None for line in version_text.splitlines())


def _unlinked_path(path: Path) -> bool:
    try:
        for part in (path, *path.parents):
            linked = part.is_symlink()
            junction = part.is_junction()
            if type(linked) is not bool or type(junction) is not bool:
                return False
            if linked or junction:
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
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError):
        # The raw fd remains owned by this caller if wrapper creation fails.
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError):
            pass
        raise
    with stream:
        before = _marker_identity(os.fstat(stream.fileno()))
        content = stream.read(len(expected) + 1)
        after = _marker_identity(os.fstat(stream.fileno()))
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
    aliases = tuple(root / "jig-bin" / f"{tool}.bin" for tool in _TOOL_NAMES)
    physical_files = (*aliases, *_runtime_files(root, platform_id))
    return all(_physical_file(path) for path in physical_files) and (
        platform_id != LINUX_PLATFORM or _physical_directory(root / "lib/clang/22")
    )


def _link_or_copy(source: str, destination: str) -> str:
    """Import a new file without overwriting a raced destination link."""
    if not _physical_directory(Path(destination).parent):
        _fail("LLVM import destination parent must be physical")
    try:
        os.link(source, destination)
    except OSError:
        created = False
        try:
            with Path(destination).open("xb") as target:
                created = True
                with Path(source).open("rb") as original:
                    shutil.copyfileobj(original, target)
            shutil.copystat(source, destination)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            if created:
                try:
                    Path(destination).unlink(missing_ok=True)
                except (OSError, ValueError, TypeError, RuntimeError):
                    pass
            raise LlvmImportError(
                f"LLVM import fallback copy failed: {type(error).__name__}"
            ) from error
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


def _write_linux_alias(path: Path, text: str) -> None:
    """Require the complete wrapper before admitting it as an executable."""
    written = path.write_text(text, encoding="utf-8", newline="\n")
    if type(written) is not int or written != len(text):
        _fail(f"LLVM wrapper write count mismatch: {path.name}")


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
    try:
        try:
            written = os.write(descriptor, content)
        finally:
            os.close(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        try:
            marker.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, RuntimeError):
            pass
        raise LlvmImportError(
            f"LLVM import marker write failed: {type(error).__name__}"
        ) from error
    if type(written) is int and written == len(content):
        return
    try:
        marker.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmImportError(
            f"LLVM marker write count mismatch; cleanup failed: {type(error).__name__}"
        ) from error
    _fail("LLVM marker write count mismatch")


def _write_linux_aliases(root: Path) -> tuple[Path, ...]:
    aliases: list[Path] = []
    alias_root = root / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    for tool in _TOOL_NAMES:
        alias = alias_root / f"{tool}.bin"
        _write_linux_alias(alias, _linux_wrapper(tool))
        alias.chmod(0o755)
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
    _copy_file(observation.llvm, staged / "lib" / observation.llvm.name)
    _copy_file(
        observation.clang_cpp,
        staged / "lib" / observation.clang_cpp.name,
    )
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
    if staging.exists():
        shutil.rmtree(staging)
    _admit_linux_import_staging(root, staging)
    staged = staging / "llvm"
    try:
        _stage_linux_llvm(staged, observation)
        _admit_linux_import_staging(root, staging)
        if not _physical_directory(staged):
            _fail("LLVM import staging source must be a physical directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = staged.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def _require_matching_windows_alias(source: Path, alias: Path) -> None:
    if not _physical_file(alias):
        _fail(f"Windows LLVM alias must not redirect: {alias}")
    try:
        matching = filecmp.cmp(source, alias, shallow=False)
    except OSError as error:
        _fail(f"Windows LLVM alias cannot be read: {error}")
    if not matching:
        _fail(f"Windows LLVM alias mismatch: {alias}")


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
        )
    except (OSError, ValueError, TypeError, RuntimeError):
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
