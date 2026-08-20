# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
import os
from pathlib import Path
import shutil
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


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        _ = shutil.copy2(source, destination)
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ = _link_or_copy(str(source), str(destination))


def _copy_resource_tree(source: Path, destination: Path) -> None:
    _ = shutil.copytree(
        source,
        destination,
        copy_function=_link_or_copy,
        symlinks=True,
    )


def _linux_wrapper(tool: str) -> str:
    return "\n".join((
        "#!/bin/sh",
        'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)',
        'export LD_LIBRARY_PATH="$ROOT/lib"',
        f'exec "$ROOT/bin/{tool}" "$@"',
        "",
    ))


def _write_linux_aliases(root: Path) -> tuple[Path, ...]:
    aliases: list[Path] = []
    alias_root = root / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    for tool in _TOOL_NAMES:
        alias = alias_root / f"{tool}.bin"
        _ = alias.write_text(
            _linux_wrapper(tool),
            encoding="utf-8",
            newline="\n",
        )
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
    if not all(path.is_file() for path in files):
        _fail("host LLVM observation contains a missing required file")
    if not observation.resource_dir.is_dir():
        _fail("host LLVM resource directory is unavailable")


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
    _ = (staged / LLVM_IMPORT_MARKER).write_text(
        f"llvm={LLVM_VERSION}\nplatform={LINUX_PLATFORM}\n",
        encoding="utf-8",
        newline="\n",
    )


def import_linux_llvm(root: Path, observation: LlvmHostObservation) -> Path:
    """Import one exact Linux LLVM runtime into repository-local state.

    Returns:
        Repository-local LLVM root after atomic import or exact reuse.

    """
    _validate_observation(observation)
    destination = root / LLVM_ROOT
    if (destination / LLVM_IMPORT_MARKER).is_file():
        return destination
    if destination.exists():
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


def write_windows_llvm_aliases(root: Path) -> tuple[Path, ...]:
    """Create neutral aliases from an existing exact Windows LLVM bundle.

    Returns:
        Neutral aliases containing the exact existing Windows PE bytes.

    """
    aliases: list[Path] = []
    alias_root = root / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    for tool in _TOOL_NAMES:
        source = root / "bin" / f"{tool}.exe"
        if not source.is_file():
            _fail(f"Windows LLVM tool is absent: {source}")
        alias = alias_root / f"{tool}.bin"
        if not alias.exists():
            _copy_file(source, alias)
        aliases.append(alias)
    _ = (root / LLVM_IMPORT_MARKER).write_text(
        f"llvm={LLVM_VERSION}\nplatform={WINDOWS_PLATFORM}\n",
        encoding="utf-8",
        newline="\n",
    )
    return tuple(aliases)


def inspect_llvm(root: Path, platform_id: str) -> LlvmReadiness:
    """Inspect neutral LLVM validation aliases for one supported host.

    Returns:
        Readiness plus the canonical neutral Clang alias path.

    """
    llvm_root = root / LLVM_ROOT
    alias_root = llvm_root / "jig-bin"
    clang = alias_root / "clang.bin"
    aliases = tuple(alias_root / f"{tool}.bin" for tool in _TOOL_NAMES)
    marker = llvm_root / LLVM_IMPORT_MARKER
    supported = platform_id in {LINUX_PLATFORM, WINDOWS_PLATFORM}
    complete = marker.is_file() and all(path.is_file() for path in aliases)
    ready = supported and complete
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
