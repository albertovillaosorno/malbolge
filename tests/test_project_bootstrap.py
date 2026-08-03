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
#   - Cross-platform checkout bootstrap regression evidence.
# - Must-Not:
#   - Download native toolchains or claim Linux CUDA runtime support.
# - Allows:
#   - Inputs: temporary roots, manifests, and explicit platform identities.
#   - Outputs: deterministic layouts, launchers, and component status.
#   - Side effects: temporary files and directories only.
# - Split-When:
#   - Split when native toolchain provisioning gains executable behavior.
# - Merge-When:
#   - Merge when another test owns this exact bootstrap contract.
# - Summary:
#   - Project bootstrap and platform-layout regressions.
# - Description:
#   - Verifies checkout initialization without requiring optional hardware.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Optional components report missing or unsupported instead of guessing.
#

"""Project bootstrap and platform-layout regressions."""

from __future__ import annotations

import json
import os
import stat
from typing import TYPE_CHECKING

import pytest
from scripts.bootstrap import project
from scripts.bootstrap import python_validation

if TYPE_CHECKING:
    from pathlib import Path

CUDA_VERSION_ROOT = ".dependencies/cuda/13.3.1/toolkit"
WINDOWS_PLATFORM = "windows-x86_64"
LINUX_PLATFORM = "linux-x86_64"
WINDOWS_CHANNEL = "stable-1.97.1-x86_64-pc-windows-gnu"
WINDOWS_PYTHON = "python.exe"
WINDOWS_PYTHON_LAUNCHER = "python-jig.cmd"
WINDOWS_PYTEST = "pytest.exe"
WINDOWS_PYTEST_LAUNCHER = "pytest-jig.cmd"
POSIX_PYTHON = "python"
POSIX_PYTHON_LAUNCHER = "python-jig"
POSIX_PYTEST = "pytest"
POSIX_PYTEST_LAUNCHER = "pytest-jig"
POSIX_HEADER = "#!/bin/sh\nset -eu\n"
CACHE_VARIABLE = "PYTHONPYCACHEPREFIX"
POSIX_PYTHON_EXEC = 'exec "$SCRIPT_DIR/python" "$@"'
POSIX_PYTEST_EXEC = 'exec "$SCRIPT_DIR/python" -m pytest "$@"'
LINUX_AARCH64 = "linux-aarch64"


def _write_cuda_manifest(root: Path, platform_id: str) -> Path:
    directory = root / "accelerator" / "cuda"
    directory.mkdir(parents=True)
    manifest = directory / "toolchain.json"
    _ = manifest.write_text(
        json.dumps({
            "platform": platform_id,
            "toolkit_root": CUDA_VERSION_ROOT,
        }),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _write_rust_manifest(root: Path, channel: str = WINDOWS_CHANNEL) -> Path:
    manifest = root / ".jig/version/rust-toolchain.toml"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(
        f'[toolchain]\nchannel = "{channel}"\n',
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def test_validation_layout_uses_windows_native_names(tmp_path: Path) -> None:
    """Windows validation paths retain Scripts, EXE, and CMD conventions."""
    layout = python_validation.validation_layout(tmp_path, windows=True)

    assert layout.scripts == layout.environment / "Scripts"
    assert layout.python.name == WINDOWS_PYTHON
    assert layout.python_launcher.name == WINDOWS_PYTHON_LAUNCHER
    assert layout.pytest.name == WINDOWS_PYTEST
    assert layout.pytest_launcher.name == WINDOWS_PYTEST_LAUNCHER
    assert layout.expected_tools == (
        ("basedpyright.exe", "basedpyright 1.39.9"),
        ("pytest.exe", "pytest 9.1.1"),
        ("python-jig.cmd", "Python 3.14.6"),
        ("ruff.exe", "ruff 0.16.0"),
    )


def test_validation_layout_uses_posix_native_names(tmp_path: Path) -> None:
    """POSIX validation paths use bin and extension-free launchers."""
    layout = python_validation.validation_layout(tmp_path, windows=False)

    assert layout.scripts == layout.environment / "bin"
    assert layout.python.name == POSIX_PYTHON
    assert layout.python_launcher.name == POSIX_PYTHON_LAUNCHER
    assert layout.pytest.name == POSIX_PYTEST
    assert layout.pytest_launcher.name == POSIX_PYTEST_LAUNCHER
    assert layout.expected_tools == (
        ("basedpyright", "basedpyright 1.39.9"),
        ("pytest", "pytest 9.1.1"),
        ("python-jig", "Python 3.14.6"),
        ("ruff", "ruff 0.16.0"),
    )


def test_posix_launchers_are_executable_and_cache_bound(tmp_path: Path) -> None:
    """POSIX launchers use the local interpreter and repository cache."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)

    python_validation.write_launchers(layout, windows=False)

    python_text = layout.python_launcher.read_text(encoding="ascii")
    pytest_text = layout.pytest_launcher.read_text(encoding="ascii")
    assert python_text.startswith(POSIX_HEADER)
    assert CACHE_VARIABLE in python_text
    assert POSIX_PYTHON_EXEC in python_text
    assert POSIX_PYTEST_EXEC in pytest_text
    if os.name != python_validation.WINDOWS_OS_NAME:
        assert layout.python_launcher.stat().st_mode & stat.S_IXUSR
        assert layout.pytest_launcher.stat().st_mode & stat.S_IXUSR


def test_platform_identity_normalizes_windows_and_linux() -> None:
    """Host names normalize to manifest-compatible OS/architecture IDs."""
    assert (
        project.host_platform_id(system="Windows", machine="AMD64")
        == WINDOWS_PLATFORM
    )
    assert (
        project.host_platform_id(system="Linux", machine="x86_64")
        == LINUX_PLATFORM
    )
    assert (
        project.host_platform_id(system="Linux", machine="arm64")
        == LINUX_AARCH64
    )


def test_cuda_inspection_requires_matching_platform_and_bundle(
    tmp_path: Path,
) -> None:
    """A matching manifest is ready only after its exact toolkit root exists."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    missing = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    toolkit.mkdir(parents=True)
    ready = project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    assert missing.state is project.ComponentState.MISSING
    assert missing.path == toolkit
    assert ready.state is project.ComponentState.READY
    assert ready.path == toolkit


def test_cuda_inspection_rejects_windows_manifest_on_linux(
    tmp_path: Path,
) -> None:
    """The current Windows bundle is explicitly unsupported on Linux."""
    _ = _write_cuda_manifest(tmp_path, WINDOWS_PLATFORM)

    status = project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    assert status.state is project.ComponentState.UNSUPPORTED
    assert WINDOWS_PLATFORM in status.detail
    assert LINUX_PLATFORM in status.detail


def test_rust_inspection_rejects_windows_channel_on_linux(
    tmp_path: Path,
) -> None:
    """A Windows GNU Rust channel never becomes Linux-ready by inference."""
    _ = _write_rust_manifest(tmp_path)

    status = project.inspect_rust(tmp_path, LINUX_PLATFORM)

    assert status.state is project.ComponentState.UNSUPPORTED
    assert WINDOWS_CHANNEL in status.detail


def test_local_directory_initialization_is_idempotent(tmp_path: Path) -> None:
    """Ignored checkout state directories can be initialized repeatedly."""
    first = project.initialize_local_directories(tmp_path)
    second = project.initialize_local_directories(tmp_path)

    assert first == second
    assert tuple(path.name for path in first) == project.LOCAL_DIRECTORIES
    assert all(path.is_dir() for path in first)


def test_repository_validation_fails_closed_for_wrong_root(
    tmp_path: Path,
) -> None:
    """Bootstrap refuses a directory without the repository authority files."""
    with pytest.raises(project.InitializationError, match="repository root"):
        project.validate_repository(tmp_path)
