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
#   - Linux CMake/Ninja construction of the pinned Malbolge clang-tidy module.
# - Must-Not:
#   - Use Visual Studio, DIA, ambient LLVM headers, or download dependencies.
# - Allows:
#   - Inputs: reviewed repository-local LLVM runtime/development roots.
#   - Outputs: canonical ignored ELF clang-tidy plugin output.
#   - Side effects: CMake/Ninja compilation under repository-owned cache roots.
# - Split-When:
#   - Another POSIX host needs an independently versioned native build protocol.
# - Merge-When:
#   - The Windows and Linux native build protocols become identical.
# - Summary:
#   - Build the pinned Linux clang-tidy plugin from exact local LLVM inputs.
# - Description:
#   - Uses neutral Clang 22.1.8 plus exact local headers and shared libraries.
# - Usage:
#   - Dispatched by `scripts.validate.tidy_build` on Linux x86-64.
# - Defaults:
#   - Missing tools, platform drift, or failed native commands fail closed.
#

"""Build the Linux Malbolge clang-tidy module from exact local LLVM inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final
from typing import Never

from scripts.repository_root import repository_root
from scripts.validate import tidy_toolchain

ROOT: Final = repository_root(Path(__file__))
SOURCE_ROOT: Final = ROOT / "tools" / "tidy" / "composition"
BUILD_ROOT: Final = (
    ROOT
    / ".cache"
    / "tools-tidy"
    / tidy_toolchain.LLVM_VERSION
    / tidy_toolchain.LINUX_PLATFORM
    / "build"
)
CMAKE_NAME: Final = "cmake"
NINJA_NAME: Final = "ninja"


class LinuxBuildError(RuntimeError):
    """Linux native-analysis build prerequisites or commands are invalid."""


@dataclass(frozen=True, slots=True)
class LinuxBuildTools:
    """Resolved CMake and Ninja executables for the Linux build protocol."""

    cmake: Path
    ninja: Path


def _fail(message: str) -> Never:
    raise LinuxBuildError(message)


def _tool(name: str) -> Path:
    resolved = shutil.which(name)
    if resolved is None:
        _fail(f"Linux clang-tidy build tool is unavailable: {name}")
    path = Path(resolved)
    if not path.is_file():
        _fail(f"Linux clang-tidy build tool is not a file: {path}")
    return path


def linux_build_tools() -> LinuxBuildTools:
    """Resolve required platform build tools from the configured host PATH.

    Returns:
        CMake and Ninja executable paths for this Linux host.

    """
    return LinuxBuildTools(cmake=_tool(CMAKE_NAME), ninja=_tool(NINJA_NAME))


def configure_command(
    identity: tidy_toolchain.ToolchainIdentity,
    tools: LinuxBuildTools,
) -> list[str]:
    """Construct the deterministic Linux CMake configure argv.

    Returns:
        Explicit shell-free configure arguments using repository-local LLVM.

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
        f"-DMALBOLGE_OUTPUT_DIR={identity.plugin_output_root}",
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
        _fail(f"failed to execute Linux {label}: {error}")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        _fail(
            f"Linux {label} failed with status {completed.returncode}: {detail}"
        )


def build(identity: tidy_toolchain.ToolchainIdentity) -> None:
    """Build the Linux plugin from exact local native-analysis inputs."""
    if identity.platform_id != tidy_toolchain.LINUX_PLATFORM:
        message = (
            "Linux build received unsupported platform: "
            f"{identity.platform_id}"
        )
        _fail(message)
    tidy_toolchain.validate_installation(identity)
    tools = linux_build_tools()
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    identity.plugin_output_root.mkdir(parents=True, exist_ok=True)
    _checked_run(configure_command(identity, tools), "CMake configure")
    _checked_run(
        [str(tools.cmake), "--build", str(BUILD_ROOT), "--config", "Release"],
        "CMake build",
    )
