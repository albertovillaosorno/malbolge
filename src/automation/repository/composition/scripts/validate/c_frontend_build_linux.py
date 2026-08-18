# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Linux CMake/Ninja construction of the normalized C frontend executable.
# - Must-Not:
#   - Use Windows tools, ambient LLVM development paths, or download packages.
# - Allows:
#   - Inputs: exact repository-local LLVM runtime/development roots.
#   - Outputs: canonical ignored Linux normalized-frontend executable.
#   - Side effects: CMake/Ninja compilation under repository-owned cache roots.
# - Split-When:
#   - Another POSIX frontend host requires an independent native build protocol.
# - Merge-When:
#   - Frontend build protocols become identical across supported platforms.
# - Summary:
#   - Build the Linux normalized C frontend from exact local LLVM inputs.
# - Description:
#   - Uses neutral Clang plus exact local headers and shared LLVM libraries.
# - Usage:
#   - Dispatched by `scripts.validate.c_frontend_build` on Linux x86-64.
# - Defaults:
#   - Missing tools, platform drift, or failed native commands fail closed.
#

"""Build the Linux normalized C frontend from exact local LLVM inputs."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final
from typing import Never

from scripts.repository_root import repository_root
from scripts.validate import tidy_build_linux
from scripts.validate import tidy_toolchain

ROOT: Final = repository_root(Path(__file__))
SOURCE_ROOT: Final = ROOT / "src" / "compiler" / "c-frontend" / "composition"
BUILD_ROOT: Final = (
    ROOT
    / ".cache"
    / "compiler-c-frontend"
    / tidy_toolchain.LLVM_VERSION
    / tidy_toolchain.LINUX_PLATFORM
    / "build"
)
LinuxFrontendBuildTools = tidy_build_linux.LinuxBuildTools


class LinuxFrontendBuildError(RuntimeError):
    """Linux normalized-frontend build prerequisites or commands are invalid."""


def _fail(message: str) -> Never:
    raise LinuxFrontendBuildError(message)


def linux_build_tools() -> LinuxFrontendBuildTools:
    """Resolve CMake/Ninja through the reviewed Linux native build boundary.

    Returns:
        CMake and Ninja executable paths visible to the development shell.

    """
    try:
        return tidy_build_linux.linux_build_tools()
    except tidy_build_linux.LinuxBuildError as error:
        _fail(str(error))


def configure_command(
    identity: tidy_toolchain.ToolchainIdentity,
    tools: LinuxFrontendBuildTools,
    *,
    output_root: Path,
) -> list[str]:
    """Construct deterministic Linux frontend CMake configure arguments.

    Returns:
        Shell-free configure argv using exact repository-local LLVM inputs.

    """
    return [
        str(tools.cmake),
        "-S",
        str(SOURCE_ROOT),
        "-B",
        str(BUILD_ROOT),
        "-G",
        "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={tools.ninja}",
        f"-DCMAKE_CXX_COMPILER={identity.clang}",
        "-DCMAKE_CXX_COMPILER_ARG1=--driver-mode=g++",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DMALBOLGE_LLVM_DEVELOPMENT_ROOT={identity.development_root}",
        f"-DMALBOLGE_LLVM_RUNTIME_ROOT={identity.runtime_root}",
        f"-DMALBOLGE_OUTPUT_DIR={output_root}",
    ]


def _checked_run(command: list[str], label: str) -> None:
    try:
        # jig-ignore-next-line: Ruff suppression name is indivisible.
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute Linux frontend {label}: {error}")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        _fail(
            "".join((
                f"Linux frontend {label} failed with status ",
                f"{completed.returncode}: {detail}",
            ))
        )


def build(
    identity: tidy_toolchain.ToolchainIdentity,
    *,
    output_root: Path,
) -> None:
    """Build the Linux frontend from exact local native-analysis inputs."""
    if identity.platform_id != tidy_toolchain.LINUX_PLATFORM:
        message = f"unsupported Linux frontend platform: {identity.platform_id}"
        _fail(message)
    tidy_toolchain.validate_installation(identity)
    tools = linux_build_tools()
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    _checked_run(
        configure_command(identity, tools, output_root=output_root),
        "CMake configure",
    )
    _checked_run(
        [str(tools.cmake), "--build", str(BUILD_ROOT), "--config", "Release"],
        "CMake build",
    )
