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

import pytest

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


@pytest.mark.parametrize(
    "path_kind",
    [
        "cache-parent-symlink",
        "cache-leaf-symlink",
        "cache-parent-file",
        "cache-leaf-file",
        "output-parent-symlink",
        "output-leaf-symlink",
        "output-parent-file",
        "output-leaf-file",
    ],
)
def test_linux_build_rejects_redirected_or_nonphysical_output_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Malformed build roots cannot select a foreign CMake or output sink."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = (
        tmp_path
        / ".cache/tools-tidy"
        / tidy_toolchain.LLVM_VERSION
        / LINUX_PLATFORM
        / "build"
    )
    monkeypatch.setattr(tidy_build_linux, "BUILD_ROOT", cache)
    output = identity.plugin_output_root
    selected = cache if path_kind.startswith("cache-") else output
    if "parent" in path_kind:
        selected = tmp_path / (
            ".cache" if path_kind.startswith("cache-") else ".dependencies"
        )
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"external unchanged")
    if path_kind.endswith("symlink"):
        selected.parent.mkdir(parents=True, exist_ok=True)
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        _ = selected.write_bytes(b"not a directory")
    called: list[str] = []

    def prohibit_command(_command: list[str], label: str) -> None:
        called.append(label)

    def skip_toolchain_validation(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    monkeypatch.setattr(
        tidy_toolchain, "validate_installation", skip_toolchain_validation
    )
    monkeypatch.setattr(
        tidy_build_linux,
        "linux_build_tools",
        lambda: tidy_build_linux.LinuxBuildTools(
            cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
        ),
    )
    monkeypatch.setattr(tidy_build_linux, "_checked_run", prohibit_command)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="build|output"):
        tidy_build_linux.build(identity)
    assert not called
    assert sentinel.read_bytes() == b"external unchanged"
    assert list(external.iterdir()) == [sentinel]
