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

import pytest

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
def test_linux_frontend_build_rejects_unphysical_output_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Never invoke CMake through redirected cache or output ancestors."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = tmp_path / ".cache/compiler-c-frontend/22.1.8/linux-x86_64/build"
    output = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"
    monkeypatch.setattr(c_frontend_build_linux, "BUILD_ROOT", cache)
    selected = cache if path_kind.startswith("cache-") else output
    if "parent" in path_kind:
        selected = tmp_path / (
            ".cache" if path_kind.startswith("cache-") else ".dependencies"
        )
    external = tmp_path / "foreign"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    selected.parent.mkdir(parents=True, exist_ok=True)
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    commands: list[str] = []

    def validate_stub(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    def run_stub(_command: list[str], label: str) -> None:
        commands.append(label)

    monkeypatch.setattr(tidy_toolchain, "validate_installation", validate_stub)
    monkeypatch.setattr(
        c_frontend_build_linux,
        "linux_build_tools",
        lambda: c_frontend_build_linux.LinuxFrontendBuildTools(
            cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
        ),
    )
    monkeypatch.setattr(c_frontend_build_linux, "_checked_run", run_stub)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="build|output"
    ):
        c_frontend_build_linux.build(identity, output_root=output)
    assert not commands
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("target_kind", ["cache", "output"])
def test_linux_frontend_rejects_path_swap_after_configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """Native build must not run after configure redirects the build sink."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = tmp_path / ".cache/compiler-c-frontend/22.1.8/linux-x86_64/build"
    output = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"
    monkeypatch.setattr(c_frontend_build_linux, "BUILD_ROOT", cache)
    external = tmp_path / "foreign"
    external.mkdir()
    probe = tmp_path / "link-capability-probe"
    try:
        probe.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    probe.unlink()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    calls: list[str] = []

    def validate_stub(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    def run_stub(_command: list[str], label: str) -> None:
        calls.append(label)
        if label == "CMake configure":
            target = cache if target_kind == "cache" else output
            target.rmdir()
            target.symlink_to(external, target_is_directory=True)

    monkeypatch.setattr(tidy_toolchain, "validate_installation", validate_stub)
    monkeypatch.setattr(
        c_frontend_build_linux,
        "linux_build_tools",
        lambda: c_frontend_build_linux.LinuxFrontendBuildTools(
            cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
        ),
    )
    monkeypatch.setattr(c_frontend_build_linux, "_checked_run", run_stub)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="redirect"
    ):
        c_frontend_build_linux.build(identity, output_root=output)
    assert calls == ["CMake configure"]
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]
