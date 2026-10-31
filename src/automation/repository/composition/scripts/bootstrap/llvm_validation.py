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

from dataclasses import dataclass
import filecmp
import os
from pathlib import Path
import shutil
from stat import S_ISDIR
from stat import S_ISREG
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final
from typing import Never

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
    return any(LLVM_VERSION in line for line in version_text.splitlines())


def _unlinked_path(path: Path) -> bool:
    try:
        return not any(
            part.is_symlink() or part.is_junction()
            for part in (path, *path.parents)
        )
    except OSError, ValueError:
        return False


def _physical_file(path: Path) -> bool:
    try:
        return _unlinked_path(path) and S_ISREG(path.lstat().st_mode)
    except OSError, ValueError:
        return False


def _physical_directory(path: Path) -> bool:
    try:
        return _unlinked_path(path) and S_ISDIR(path.lstat().st_mode)
    except OSError, ValueError:
        return False


def _marker_bytes(platform_id: str) -> bytes:
    return f"llvm={LLVM_VERSION}\nplatform={platform_id}\n".encode()


def _marker_identity(status: os.stat_result) -> tuple[int, ...]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
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
    with os.fdopen(descriptor, "rb") as stream:
        before = _marker_identity(os.fstat(stream.fileno()))
        content = stream.read(len(expected) + 1)
        after = _marker_identity(os.fstat(stream.fileno()))
    return before == admitted and after == admitted and content == expected


def _valid_marker(root: Path, platform_id: str) -> bool:
    marker = root / LLVM_IMPORT_MARKER
    if not _physical_file(marker):
        return False
    expected = _marker_bytes(platform_id)
    try:
        initial = marker.lstat()
        admitted = _marker_identity(initial)
        return (
            initial.st_size == len(expected)
            and _stable_marker_descriptor(marker, admitted, expected)
            and _physical_file(marker)
            and _marker_identity(marker.lstat()) == admitted
        )
    except OSError, ValueError:
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
        platform_id != LINUX_PLATFORM
        or _physical_directory(root / "lib/clang/22")
    )


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        _ = shutil.copy2(source, destination)
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = _link_or_copy(str(source), str(destination))


def _require_physical_resources(root: Path) -> None:
    if not _physical_directory(root):
        _fail("host LLVM resource directory must not redirect")
    for member in root.rglob("*"):
        if member.is_symlink() or member.is_junction():
            _fail(f"host LLVM resource member must not redirect: {member}")


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
    return "\n".join((
        "#!/bin/sh",
        'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)',
        'export LD_LIBRARY_PATH="$ROOT/lib"',
        f'exec "$ROOT/bin/{tool}" "$@"',
        "",
    ))


def _write_linux_alias(path: Path, text: str) -> None:
    """Require the complete wrapper before admitting it as an executable."""
    written = path.write_text(text, encoding="utf-8", newline="\n")
    if type(written) is not int or written != len(text):
        _fail(f"LLVM wrapper write count mismatch: {path.name}")


def _write_import_marker(root: Path, platform_id: str) -> None:
    """Publish a complete marker or fail without retaining a partial one."""
    marker = root / LLVM_IMPORT_MARKER
    content = _marker_bytes(platform_id)
    written = marker.write_bytes(content)
    if type(written) is int and written == len(content):
        return
    try:
        marker.unlink(missing_ok=True)
    except (OSError, ValueError) as error:
        _fail(f"LLVM marker write count mismatch; cleanup failed: {error}")
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
            "".join((
                "host LLVM version mismatch: ",
                f"{observation.version} != {LLVM_VERSION}",
            ))
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


def import_linux_llvm(root: Path, observation: LlvmHostObservation) -> Path:
    """Import one exact Linux LLVM runtime into repository-local state.

    Returns:
        Repository-local LLVM root after atomic import or exact reuse.

    """
    _validate_observation(observation)
    destination = root / LLVM_ROOT
    if _runtime_ready(destination, LINUX_PLATFORM):
        return destination
    if (
        destination.exists()
        or destination.is_symlink()
        or destination.is_junction()
    ):
        _fail("repository-local LLVM exists without the exact import marker")
    staging = root / ".temp" / "llvm-import-linux-x86_64"
    if staging.exists():
        shutil.rmtree(staging)
    staged = staging / "llvm"
    try:
        _stage_linux_llvm(staged, observation)
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


def _admit_windows_alias(source: Path, alias: Path) -> None:
    if not _physical_file(source):
        _fail(f"Windows LLVM source tool must be physical: {source}")
    if alias.exists() or alias.is_symlink() or alias.is_junction():
        _require_matching_windows_alias(source, alias)


def _windows_alias_directory(root: Path) -> Path:
    """Verify Windows root and alias directory without following redirects.

    Returns:
        Physical or truly absent directory intended for neutral aliases.

    """
    if not _physical_directory(root):
        _fail("Windows LLVM bundle root must be physical")
    alias_root = root / "jig-bin"
    present = (
        alias_root.exists()
        or alias_root.is_symlink()
        or alias_root.is_junction()
    )
    if present and not _physical_directory(alias_root):
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
    # Check every member before creating an alias or publishing the marker.
    for source, alias in pairs:
        _admit_windows_alias(source, alias)
    alias_root.mkdir(parents=True, exist_ok=True)
    for source, alias in pairs:
        if not alias.exists():
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
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        arguments,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _observed_tool(name: str) -> Path | None:
    resolved = shutil.which(name)
    return None if resolved is None else Path(resolved).resolve()


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
        path = Path(path_text)
        return path.resolve() if path.is_file() else None
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
    resource_dir = Path(resource_text).resolve()
    if not resource_dir.is_dir():
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
