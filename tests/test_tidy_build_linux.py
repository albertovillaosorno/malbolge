# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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

import subprocess as sp
from typing import TYPE_CHECKING, cast

import pytest

from scripts.validate import tidy_build_linux, tidy_toolchain

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


@pytest.mark.parametrize(
    "receipt_args",
    [
        None,
        "cmake -S source",
        ("cmake", "--version"),
        ["another-cmake", "--version"],
        ["cmake", "--build"],
        ["cmake", True],
    ],
)
def test_linux_build_rejects_nonmatching_process_argv_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt_args: object,
) -> None:
    """Success receipts must be from the exact command that was launched."""
    command = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            args=cast("list[str]", receipt_args),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(sp, "run", fake_run)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="process receipt"):
        tidy_build_linux._checked_run(command, "CMake configure")


@pytest.mark.parametrize("method", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("bad_status", [None, 0, 1, [], "yes"])
def test_linux_build_rejects_foreign_directory_status_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    method: str,
    bad_status: object,
) -> None:
    """Only exact native booleans can admit an output directory."""
    target = tmp_path / "build"
    target.mkdir()
    original = getattr(type(target), method)

    def fake_status(self: Path) -> object:
        if self == target:
            return bad_status
        return original(self)

    monkeypatch.setattr(type(target), method, fake_status)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="status receipt"):
        tidy_build_linux._require_physical_build_directory(target, "build cache")


def test_linux_build_rejects_foreign_directory_lstat_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Forged stat objects must not prove a physical output directory."""
    target = tmp_path / "build"
    target.mkdir()
    original = type(target).lstat

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        if self == target:
            return object()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(target), "lstat", fake_lstat)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="stat receipt"):
        tidy_build_linux._require_physical_build_directory(target, "build cache")


def test_linux_build_rejects_non_directory_native_lstat_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Path predicates alone cannot override a native non-directory mode."""
    import os
    import stat

    target = tmp_path / "build"
    target.mkdir()
    original = type(target).lstat
    file_stat = os.stat_result((stat.S_IFREG | 0o644, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        if self == target:
            return file_stat
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(target), "lstat", fake_lstat)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="directory"):
        tidy_build_linux._require_physical_build_directory(target, "plugin output")


def test_linux_build_rejects_lying_link_predicates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Physical symlink mode wins over forged directory path predicates."""
    external = tmp_path / "external"
    external.mkdir()
    link = tmp_path / "build"
    try:
        link.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    monkeypatch.setattr(type(link), "is_symlink", lambda _self: False)
    monkeypatch.setattr(type(link), "is_junction", lambda _self: False)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="redirect"):
        tidy_build_linux._require_physical_build_directory(link, "build cache")


def test_linux_build_rejects_lying_missing_path_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Physically present directories cannot be hidden by forged exists()."""
    target = tmp_path / "build"
    target.mkdir()
    original = type(target).exists

    def fake_exists(self: Path) -> bool:
        return False if self == target else original(self)

    monkeypatch.setattr(type(target), "exists", fake_exists)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="directory"):
        tidy_build_linux._require_physical_build_directory(target, "build cache")


def test_linux_build_preserves_native_stat_error_cause_without_foreign_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A hostile OS error string formatter is never invoked during preflight."""

    class HostilePermissionError(PermissionError):
        def __str__(self) -> str:
            raise AssertionError("foreign host exception formatted")

    target = tmp_path / "build"
    target.mkdir()
    original = type(target).lstat
    hostile = HostilePermissionError("failed")

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        if self == target:
            raise hostile
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(target), "lstat", fake_lstat)
    with pytest.raises(
        tidy_build_linux.LinuxBuildError, match="HostilePermissionError"
    ) as failure:
        tidy_build_linux._require_physical_build_directory(target, "plugin output")
    assert failure.value.__cause__ is hostile


def test_linux_build_runs_only_pinned_output_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A successful build uses the configured cache and plugin output roots."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = tmp_path / "cache" / "build"
    monkeypatch.setattr(tidy_build_linux, "BUILD_ROOT", cache)
    tools = tidy_build_linux.LinuxBuildTools(
        cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
    )
    monkeypatch.setattr(tidy_toolchain, "validate_installation", lambda _: None)
    monkeypatch.setattr(tidy_build_linux, "linux_build_tools", lambda: tools)
    commands: list[tuple[list[str], str]] = []

    def record_command(command: list[str], label: str) -> None:
        assert cache.is_dir()
        assert identity.plugin_output_root.is_dir()
        commands.append((command, label))

    monkeypatch.setattr(tidy_build_linux, "_checked_run", record_command)
    tidy_build_linux.build(identity)
    assert commands == [
        (tidy_build_linux.configure_command(identity, tools), "CMake configure"),
        (
            [str(tools.cmake), "--build", str(cache), "--config", "Release"],
            "CMake build",
        ),
    ]


@pytest.mark.parametrize("mode", [None, True, 1.5, "directory", object()])
def test_linux_build_rejects_malformed_native_stat_modes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: object
) -> None:
    """Even native stat containers must carry a native integer file mode."""
    import os

    target = tmp_path / "build"
    target.mkdir()
    original = type(target).lstat
    forged = os.stat_result((cast("int", mode), 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        return forged if self == target else original(self, *args, **kwargs)

    monkeypatch.setattr(type(target), "lstat", fake_lstat)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="stat receipt"):
        tidy_build_linux._require_physical_build_directory(target, "build cache")


@pytest.mark.parametrize("mutation", ["executable", "argument", "append"])
def test_linux_build_rejects_mutated_launch_command(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """A subprocess hook cannot rewrite CMake expectations before receipt checks."""
    command = ["cmake", "--version"]

    def mutate_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "executable":
            args[0] = "/foreign/cmake"
        elif mutation == "argument":
            args[1] = "--build"
        else:
            args.append("--forged")
        return sp.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr(sp, "run", mutate_run)
    with pytest.raises(tidy_build_linux.LinuxBuildError, match="process receipt"):
        tidy_build_linux._checked_run(command, "CMake configure")
    assert command == ["cmake", "--version"]
