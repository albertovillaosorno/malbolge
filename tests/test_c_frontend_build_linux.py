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
#   - Linux normalized C frontend build orchestration regressions.
# - Must-Not:
#   - Use Windows tools, ambient LLVM development paths, or network access.
# - Allows:
#   - Inputs: exact repository-local LLVM runtime/development identity.
#   - Outputs: deterministic Linux CMake/Ninja argv and output path assertions.
#   - Side effects: test-local paths only.
# - Split-When:
#   - Another POSIX frontend host gains an independent native build ABI.
# - Merge-When:
#   - Frontend build protocols become identical across supported platforms.
# - Summary:
#   - Lock the Linux normalized C frontend build boundary.
# - Description:
#   - Proves exact local LLVM roots and neutral compiler/output selection.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Unsupported platform or missing exact inputs fails closed.
#

"""Linux normalized C frontend build orchestration regressions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.validate import c_frontend_build_linux
from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from pathlib import Path

LINUX_PLATFORM = "linux-x86_64"
CXX_DRIVER_MODE = "--driver-mode=g++"
WINDOWS_EXECUTABLE_SUFFIX = ".exe"


def test_linux_frontend_configure_uses_exact_local_llvm_roots(
    tmp_path: Path,
) -> None:
    """Linux configure uses neutral Clang and exact local LLVM inputs."""
    identity = tidy_toolchain.load_identity(
        root=tmp_path,
        platform_id=LINUX_PLATFORM,
    )
    tools = c_frontend_build_linux.LinuxFrontendBuildTools(
        cmake=tmp_path / "cmake",
        ninja=tmp_path / "ninja",
    )
    output_root = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"

    command = c_frontend_build_linux.configure_command(
        identity,
        tools,
        output_root=output_root,
    )
    rendered = " ".join(command)

    assert command[0] == str(tools.cmake)
    assert CXX_DRIVER_MODE in rendered
    assert str(identity.clang) in rendered
    assert str(identity.development_root) in rendered
    assert str(identity.runtime_root) in rendered
    assert str(output_root) in rendered
    assert WINDOWS_EXECUTABLE_SUFFIX not in rendered
