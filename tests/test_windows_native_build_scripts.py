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
#   - Windows native C frontend and clang-tidy build script admission tests.
# - Must-Not:
#   - Require Windows, build LLVM, or install native developer toolchains.
# - Allows:
#   - Inputs: pinned identities, temporary paths, and faulty file writers.
#   - Outputs: exact script-write rejection or complete script bytes.
#   - Side effects: temporary build scripts only.
# - Split-When:
#   - Another platform needs different executable build-script semantics.
# - Merge-When:
#   - The frontend or tidy build suites own identical script admission.
# - Summary:
#   - Fail closed on truncated Windows build scripts before command launch.
# - Description:
#   - Cross-platform tests for complete generated CMake/Ninja script writes.
# - Usage:
#   - Run with the repository Python validation suite.
# - Defaults:
#   - A malformed script write acknowledgement cannot be treated as success.
#

"""Regression tests for Windows native build-script publication."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from subprocess import CompletedProcess
from typing import cast

import pytest

from scripts.validate import c_frontend_build
from scripts.validate import tidy_build
from scripts.validate import tidy_toolchain

FRONTEND_KIND = "frontend"
TIDY_KIND = "tidy"
TRUNCATED_SCRIPT = "@"
NINJA_FLAG = "-G Ninja"
VCVARS_COMMAND = "vcvars64.bat"
CRLF = b"\r\n"
DOUBLE_CRLF = b"\r\r\n"
BARE_LF = b"\n"

type ScriptBuilder = Callable[
    [tidy_build.VisualStudioTools, tidy_toolchain.ToolchainIdentity], Path
]


def _windows_tools(tmp_path: Path) -> tidy_build.VisualStudioTools:
    """Provide named Windows build tools without executing any of them.

    Returns:
        Build tool paths suitable for deterministic script generation.

    """
    return tidy_build.VisualStudioTools(
        cmake=tmp_path / "cmake.exe",
        dia_guids=tmp_path / "diaguids.lib",
        installation=tmp_path / "vs",
        ninja=tmp_path / "ninja.exe",
        vcvars64=tmp_path / "vcvars64.bat",
    )


def _script_builder(
    kind: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[
    ScriptBuilder,
    type[Exception],
    Path,
]:
    """Select the guarded author and its dedicated exception type.

    Returns:
        Script creator, failure type, and generated script path.

    """
    module = c_frontend_build if kind == FRONTEND_KIND else tidy_build
    error_type = (
        c_frontend_build.FrontendBuildError
        if kind == FRONTEND_KIND
        else tidy_build.BuildError
    )
    directory = tmp_path / kind
    monkeypatch.setattr(module, "BUILD_ROOT", directory)
    builder = cast(
        "ScriptBuilder",
        vars(module)["_write_build_script"],
    )
    return builder, error_type, directory / "build.cmd"


@pytest.mark.parametrize("kind", [FRONTEND_KIND, TIDY_KIND])
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_windows_builder_rejects_incomplete_script_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    kind: str,
    bad_count: object,
) -> None:
    """Reject a script whose host writer did not acknowledge all characters."""
    builder, error_type, script = _script_builder(kind, monkeypatch, tmp_path)
    tools = _windows_tools(tmp_path)
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    original_write = Path.write_text

    def faulty_write(
        path: Path,
        text: str,
        encoding: str | None = None,
        *,
        newline: str | None = None,
    ) -> int:
        if path != script:
            return original_write(
                path, text, encoding=encoding, newline=newline
            )
        _ = original_write(path, text[:1], encoding=encoding, newline=newline)
        return cast("int", bad_count)

    monkeypatch.setattr(Path, "write_text", faulty_write)
    with pytest.raises(error_type, match="write count"):
        _ = builder(tools, identity)
    assert script.read_text(encoding="utf-8") == TRUNCATED_SCRIPT


@pytest.mark.parametrize("kind", [FRONTEND_KIND, TIDY_KIND])
def test_windows_builder_accepts_exact_complete_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    kind: str,
) -> None:
    """A complete native build script retains all expected batch commands."""
    builder, _, script = _script_builder(kind, monkeypatch, tmp_path)
    tools = _windows_tools(tmp_path)
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    assert builder(tools, identity) == script
    content = script.read_text(encoding="utf-8")
    assert content.startswith("@echo off\nsetlocal\n")
    assert NINJA_FLAG in content
    assert VCVARS_COMMAND in content
    assert content.endswith("exit /b %errorlevel%\n")
    raw = script.read_bytes()
    assert CRLF in raw
    assert DOUBLE_CRLF not in raw
    assert BARE_LF not in raw.replace(CRLF, b"")


@pytest.mark.parametrize(
    "path_kind",
    [
        "destination-root-symlink",
        "destination-parent-symlink",
        "destination-leaf-symlink",
        "destination-parent-file",
        "destination-leaf-file",
        "source-parent-symlink",
        "source-header-symlink",
    ],
)
def test_windows_tidy_resource_copy_rejects_untrusted_paths(
    tmp_path: Path,
    path_kind: str,
) -> None:
    """Never delete or copy through a redirected Clang resource directory."""
    repository = tmp_path / "repository"
    repository.mkdir()
    identity = tidy_toolchain.load_identity(
        root=repository, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    resource = identity.runtime_root / "lib/clang/22"
    target = identity.plugin_output_root / "lib/clang/22"
    external = tmp_path / "external"
    external.mkdir()
    marker = external / "foreign-marker.txt"
    _ = marker.write_bytes(b"foreign data")
    if path_kind == "source-parent-symlink":
        resource.parent.mkdir(parents=True)
        (external / "include").mkdir()
        _ = (external / "include/limits.h").write_bytes(b"foreign header")
        try:
            resource.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        (resource / "include").mkdir(parents=True)
        header = resource / "include/limits.h"
        if path_kind == "source-header-symlink":
            external_header = external / "limits.h"
            _ = external_header.write_bytes(b"foreign header")
            try:
                header.symlink_to(external_header)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"file links unavailable: {error}")
        else:
            _ = header.write_bytes(b"trusted header")
    if path_kind == "destination-root-symlink":
        identity.plugin_output_root.parent.mkdir(parents=True)
        selected = identity.plugin_output_root
    elif path_kind == "destination-parent-symlink":
        identity.plugin_output_root.mkdir(parents=True)
        selected = identity.plugin_output_root / "lib"
        (external / "clang/22").mkdir(parents=True)
        _ = (external / "clang/22/foreign-member.txt").write_bytes(b"preserve")
    elif path_kind == "destination-leaf-symlink":
        target.parent.mkdir(parents=True)
        selected = target
    elif path_kind == "destination-parent-file":
        identity.plugin_output_root.mkdir(parents=True)
        selected = identity.plugin_output_root / "lib"
        _ = selected.write_bytes(b"not a directory")
    elif path_kind == "destination-leaf-file":
        target.parent.mkdir(parents=True)
        selected = target
        _ = selected.write_bytes(b"not a directory")
    else:
        selected = None
    if selected is not None and path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    with pytest.raises(tidy_build.BuildError, match="Clang resource"):
        tidy_build.provision_clang_resources(identity)
    assert marker.read_bytes() == b"foreign data"
    if path_kind == "destination-parent-symlink":
        assert (external / "clang/22/foreign-member.txt").read_bytes() == b"preserve"
    if path_kind.startswith("source-"):
        assert not target.exists()


@pytest.mark.parametrize(
    "path_kind", ["parent-symlink", "leaf-symlink", "parent-file", "leaf-file"]
)
def test_windows_tidy_script_rejects_untrusted_build_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Build scripts cannot write through a redirected or invalid cache."""
    build_root = tmp_path / "cache" / "build"
    monkeypatch.setattr(tidy_build, "BUILD_ROOT", build_root)
    selected = build_root.parent if path_kind.startswith("parent") else build_root
    selected.parent.mkdir(parents=True, exist_ok=True)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    with pytest.raises(tidy_build.BuildError, match="build cache"):
        builder = cast("ScriptBuilder", vars(tidy_build)["_write_build_script"])
        _ = builder(_windows_tools(tmp_path), identity)
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("link_kind", ["symbolic", "hard"])
def test_windows_tidy_build_script_rejects_linked_existing_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """An existing build.cmd cannot overwrite another file through an alias."""
    build_root = tmp_path / "cache" / "build"
    build_root.mkdir(parents=True)
    monkeypatch.setattr(tidy_build, "BUILD_ROOT", build_root)
    outside = tmp_path / "foreign-script.cmd"
    _ = outside.write_bytes(b"do not overwrite")
    script = build_root / "build.cmd"
    try:
        if link_kind == "symbolic":
            script.symlink_to(outside)
        else:
            script.hardlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file links unavailable: {error}")
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    with pytest.raises(tidy_build.BuildError, match="build cache"):
        builder = cast("ScriptBuilder", vars(tidy_build)["_write_build_script"])
        _ = builder(_windows_tools(tmp_path), identity)
    assert outside.read_bytes() == b"do not overwrite"
    assert script.exists()


def test_windows_tidy_resource_copy_replaces_physical_previous_version(
    tmp_path: Path,
) -> None:
    """An admitted resource directory still supports repeatable replacement."""
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    source = identity.runtime_root / "lib/clang/22"
    source_include = source / "include"
    source_include.mkdir(parents=True)
    _ = (source_include / "limits.h").write_bytes(b"canonical limits")
    destination = identity.plugin_output_root / "lib/clang/22"
    destination.mkdir(parents=True)
    old_file = destination / "stale-file.txt"
    _ = old_file.write_bytes(b"stale")
    tidy_build.provision_clang_resources(identity)
    assert (destination / "include/limits.h").read_bytes() == b"canonical limits"
    assert not old_file.exists()
    tidy_build.provision_clang_resources(identity)
    assert (destination / "include/limits.h").read_bytes() == b"canonical limits"


@pytest.mark.parametrize(
    "path_kind", ["parent-symlink", "leaf-symlink", "parent-file", "leaf-file"]
)
def test_windows_tidy_build_rejects_redirected_plugin_output_before_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """CMake cannot receive a redirected plugin output directory."""
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    output = identity.plugin_output_root
    selected = output.parent if path_kind.startswith("parent") else output
    selected.parent.mkdir(parents=True, exist_ok=True)
    external = tmp_path / "foreign"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    monkeypatch.setattr(tidy_build, "BUILD_ROOT", tmp_path / "cache")

    def skip_installation(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    monkeypatch.setattr(tidy_toolchain, "validate_installation", skip_installation)
    monkeypatch.setattr(
        tidy_build,
        "visual_studio_tools",
        lambda: _windows_tools(tmp_path),
    )
    calls: list[list[str]] = []

    def capture_command(command: list[str], *, capture: bool = False) -> None:
        _ = capture
        calls.append(command)

    monkeypatch.setattr(tidy_build, "_run", capture_command)
    with pytest.raises(tidy_build.BuildError, match="plugin output"):
        tidy_build.build(identity)
    assert not calls
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize(
    "path_kind", ["parent-symlink", "leaf-symlink", "parent-file", "leaf-file"]
)
def test_windows_frontend_script_rejects_unphysical_build_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Frontend scripts cannot write through redirected or invalid cache roots."""
    build_root = tmp_path / "cache/build"
    monkeypatch.setattr(c_frontend_build, "BUILD_ROOT", build_root)
    selected = build_root.parent if path_kind.startswith("parent") else build_root
    selected.parent.mkdir(parents=True, exist_ok=True)
    external = tmp_path / "foreign"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    builder = cast("ScriptBuilder", vars(c_frontend_build)["_write_build_script"])
    with pytest.raises(c_frontend_build.FrontendBuildError, match="build cache"):
        _ = builder(_windows_tools(tmp_path), identity)
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("link_kind", ["symbolic", "hard"])
def test_windows_frontend_script_rejects_linked_existing_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """An existing build.cmd cannot overwrite foreign scripts through aliases."""
    build_root = tmp_path / "cache/build"
    build_root.mkdir(parents=True)
    monkeypatch.setattr(c_frontend_build, "BUILD_ROOT", build_root)
    outside = tmp_path / "outside.cmd"
    _ = outside.write_bytes(b"foreign data")
    script = build_root / "build.cmd"
    try:
        if link_kind == "symbolic":
            script.symlink_to(outside)
        else:
            script.hardlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file links unavailable: {error}")
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    builder = cast("ScriptBuilder", vars(c_frontend_build)["_write_build_script"])
    with pytest.raises(c_frontend_build.FrontendBuildError, match="build cache"):
        _ = builder(_windows_tools(tmp_path), identity)
    assert outside.read_bytes() == b"foreign data"
    assert script.exists()


@pytest.mark.parametrize(
    "path_kind", ["parent-symlink", "leaf-symlink", "parent-file", "leaf-file"]
)
def test_windows_frontend_rejects_unphysical_output_before_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Never launch CMake with a redirected frontend output root."""
    output = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"
    selected = output.parent if path_kind.startswith("parent") else output
    selected.parent.mkdir(parents=True, exist_ok=True)
    external = tmp_path / "foreign"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    monkeypatch.setattr(c_frontend_build, "OUTPUT_ROOT", output)
    monkeypatch.setattr(c_frontend_build, "BUILD_ROOT", tmp_path / "cache")
    monkeypatch.setattr(
        tidy_build, "visual_studio_tools", lambda: _windows_tools(tmp_path)
    )
    calls: list[list[str]] = []

    def capture_run(
        command: list[str], *, capture: bool = False
    ) -> CompletedProcess[str]:
        _ = capture
        calls.append(command)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(c_frontend_build, "_run", capture_run)
    identity = tidy_toolchain.load_identity(
        root=tmp_path, platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    windows_builder = cast(
        "Callable[[tidy_toolchain.ToolchainIdentity], None]",
        vars(c_frontend_build)["_build_windows"],
    )
    with pytest.raises(c_frontend_build.FrontendBuildError, match="frontend output"):
        windows_builder(identity)
    assert not calls
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("link_kind", ["symbolic", "hard"])
def test_frontend_build_rejects_linked_native_executable_before_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """A forged linked frontend cannot supply the expected version response."""
    executable = tmp_path / "frontend.exe"
    external = tmp_path / "foreign.exe"
    _ = external.write_bytes(b"foreign executable")
    try:
        if link_kind == "symbolic":
            executable.symlink_to(external)
        else:
            executable.hardlink_to(external)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file links unavailable: {error}")
    monkeypatch.setattr(
        c_frontend_build, "HOST_PLATFORM_ID", tidy_toolchain.WINDOWS_PLATFORM
    )
    monkeypatch.setattr(c_frontend_build, "EXECUTABLE", executable)

    def skip_validation(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    monkeypatch.setattr(tidy_toolchain, "validate_installation", skip_validation)
    monkeypatch.setattr(c_frontend_build, "_build_windows", skip_validation)
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, capture: bool = False) -> CompletedProcess[str]:
        _ = capture
        calls.append(command)
        return CompletedProcess(command, 0, "malbolge-c-frontend 1 LLVM 22.1.8", "")

    monkeypatch.setattr(c_frontend_build, "_run", fake_run)
    with pytest.raises(
        c_frontend_build.FrontendBuildError, match="frontend executable"
    ):
        c_frontend_build.build()
    assert not calls
    assert external.read_bytes() == b"foreign executable"


def test_frontend_build_accepts_unlinked_native_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admitted physical executable can prove the required native version."""
    executable = tmp_path / "frontend.exe"
    _ = executable.write_bytes(b"local executable")
    monkeypatch.setattr(
        c_frontend_build, "HOST_PLATFORM_ID", tidy_toolchain.WINDOWS_PLATFORM
    )
    monkeypatch.setattr(c_frontend_build, "EXECUTABLE", executable)

    def skip_validation(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    monkeypatch.setattr(tidy_toolchain, "validate_installation", skip_validation)
    monkeypatch.setattr(c_frontend_build, "_build_windows", skip_validation)
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, capture: bool = False) -> CompletedProcess[str]:
        _ = capture
        calls.append(command)
        return CompletedProcess(command, 0, "malbolge-c-frontend 1 LLVM 22.1.8", "")

    monkeypatch.setattr(c_frontend_build, "_run", fake_run)
    c_frontend_build.build()
    assert calls == [[str(executable), "--version"]]


def test_frontend_build_rejects_redirected_executable_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A physical-looking leaf cannot execute through a linked parent."""
    external = tmp_path / "foreign"
    external.mkdir()
    external_executable = external / "frontend.exe"
    _ = external_executable.write_bytes(b"foreign executable")
    linked_parent = tmp_path / "output"
    try:
        linked_parent.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    executable = linked_parent / "frontend.exe"
    monkeypatch.setattr(
        c_frontend_build, "HOST_PLATFORM_ID", tidy_toolchain.WINDOWS_PLATFORM
    )
    monkeypatch.setattr(c_frontend_build, "EXECUTABLE", executable)

    def skip_validation(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    monkeypatch.setattr(tidy_toolchain, "validate_installation", skip_validation)
    monkeypatch.setattr(c_frontend_build, "_build_windows", skip_validation)
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, capture: bool = False) -> CompletedProcess[str]:
        _ = capture
        calls.append(command)
        return CompletedProcess(command, 0, "malbolge-c-frontend 1 LLVM 22.1.8", "")

    monkeypatch.setattr(c_frontend_build, "_run", fake_run)
    with pytest.raises(c_frontend_build.FrontendBuildError, match="frontend output"):
        c_frontend_build.build()
    assert not calls
    assert external_executable.read_bytes() == b"foreign executable"
