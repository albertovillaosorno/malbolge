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
#   - Deterministic Linux clang-tidy plugin build orchestration regressions.
# - Must-Not:
#   - Require Visual Studio, DIA, or contact package repositories.
# - Allows:
#   - Inputs: synthetic exact tool paths and Linux native-analysis identity.
#   - Outputs: exact CMake/Ninja argv and platform-bound build assertions.
#   - Side effects: test-local paths only.
# - Split-When:
#   - Another POSIX platform gains an independent native-analysis build ABI.
# - Merge-When:
#   - Native-analysis toolchain tests own this exact Linux build protocol.
# - Summary:
#   - Lock the Linux native-analysis CMake/Ninja build boundary.
# - Description:
#   - Proves Linux uses neutral LLVM roots without Windows build dependencies.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Platform or toolchain disagreement fails before native compilation.
#

"""Linux native-analysis plugin build orchestration regressions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.validate import tidy_build_linux
from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from pathlib import Path

LINUX_PLATFORM = "linux-x86_64"
CMAKE_GENERATOR_FLAG = "-G"
NINJA_GENERATOR = "Ninja"
WINDOWS_DIA_MARKER = "DIA"
WINDOWS_EXECUTABLE_SUFFIX = ".exe"
CXX_DRIVER_MODE = "--driver-mode=g++"


def test_linux_configure_command_uses_only_neutral_local_llvm_roots(
    tmp_path: Path,
) -> None:
    """Linux CMake argv contains no Visual Studio or Windows executable."""
    identity = tidy_toolchain.load_identity(
        root=tmp_path,
        platform_id=LINUX_PLATFORM,
    )
    tools = tidy_build_linux.LinuxBuildTools(
        cmake=tmp_path / "bin/cmake",
        ninja=tmp_path / "bin/ninja",
    )

    command = tidy_build_linux.configure_command(identity, tools)
    rendered = " ".join(command)

    assert command[0] == str(tools.cmake)
    generator_index = command.index(CMAKE_GENERATOR_FLAG)
    assert command[generator_index + 1] == NINJA_GENERATOR
    assert str(identity.clang) in rendered
    assert CXX_DRIVER_MODE in rendered
    assert str(identity.development_root) in rendered
    assert str(identity.runtime_root) in rendered
    assert str(identity.plugin_output_root) in rendered
    assert WINDOWS_DIA_MARKER not in rendered
    assert WINDOWS_EXECUTABLE_SUFFIX not in rendered
