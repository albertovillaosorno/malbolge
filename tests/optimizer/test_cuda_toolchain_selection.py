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
#   - Deterministic CUDA platform-toolchain selection evidence.
# - Must-Not:
#   - Load CUDA libraries, access devices, or accept ambient toolkit paths.
# - Allows:
#   - Inputs: tracked selector/manifest fixtures under test-local roots.
#   - Outputs: exact platform loader, library, and repository-local path checks.
#   - Side effects: test-local files only.
# - Split-When:
#   - Package download/extraction gains independent selection semantics.
# - Merge-When:
#   - Another suite owns the exact CUDA platform manifest boundary.
# - Summary:
#   - Proves CUDA platform manifests select exact Windows and Linux runtimes.
# - Description:
#   - Locks selector schema, platform agreement, and path containment.
# - Usage:
#   - Collected with optimizer tests without requiring CUDA hardware.
# - Defaults:
#   - Unknown, malformed, or escaping manifest selection fails closed.
#

"""Deterministic CUDA platform-toolchain selection evidence."""

from __future__ import annotations

import json
from pathlib import Path

from accelerator.cuda import toolchain
import pytest

WINDOWS_PLATFORM = "windows-x86_64"
LINUX_PLATFORM = "linux-x86_64"
TOOLKIT_ROOT = ".dependencies/cuda/13.3.1/toolkit"
WINDOWS_LOADER = "windll"
LINUX_LOADER = "cdll"
WINDOWS_DRIVER = "nvcuda.dll"
LINUX_DRIVER = "libcuda.so.1"
WINDOWS_MANIFEST = "toolchain.json"
LINUX_MANIFEST = "toolchain-linux-x86_64.json"
LINUX_BUILTINS = "lib/libnvrtc-builtins.so.13.3"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _manifest_root(root: Path) -> Path:
    value = root / toolchain.CUDA_TOOLCHAIN_INDEX
    value.parent.mkdir(parents=True, exist_ok=True)
    return value.parent


def _write_manifest(root: Path, platform_id: str, filename: str) -> Path:
    path = _manifest_root(root) / filename
    _ = path.write_text(
        json.dumps({
            "schema_version": 1,
            "cuda_release": "13.3 Update 1",
            "redistrib_manifest": "redistrib_13.3.1.json",
            "release_date": "2026-06-29",
            "platform": platform_id,
            "toolkit_root": TOOLKIT_ROOT,
            "packages": [],
            "redistrib_base_url": "https://example.invalid/cuda/",
        }),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_index(root: Path) -> Path:
    _ = _manifest_root(root)
    path = root / toolchain.CUDA_TOOLCHAIN_INDEX
    _ = path.write_text(
        json.dumps({
            "schema_version": 1,
            "platforms": {
                WINDOWS_PLATFORM: {
                    "manifest": "toolchain.json",
                    "loader": "windll",
                    "driver_library": "nvcuda.dll",
                    "nvrtc_library": "bin/x64/nvrtc64_130_0.dll",
                    "preload_libraries": [],
                },
                LINUX_PLATFORM: {
                    "manifest": "toolchain-linux-x86_64.json",
                    "loader": "cdll",
                    "driver_library": "libcuda.so.1",
                    "nvrtc_library": "lib/libnvrtc.so.13",
                    "preload_libraries": [LINUX_BUILTINS],
                },
            },
        }),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _write_complete_fixture(root: Path) -> None:
    _ = _write_manifest(root, WINDOWS_PLATFORM, "toolchain.json")
    _ = _write_manifest(
        root,
        LINUX_PLATFORM,
        "toolchain-linux-x86_64.json",
    )
    _ = _write_index(root)


def test_selects_windows_runtime_contract(tmp_path: Path) -> None:
    """Windows keeps WinDLL, retained manifest, and reviewed DLL names."""
    _write_complete_fixture(tmp_path)

    selected = toolchain.select_cuda_toolchain(tmp_path, WINDOWS_PLATFORM)

    assert selected.platform_id == WINDOWS_PLATFORM
    assert selected.loader_kind == WINDOWS_LOADER
    assert selected.driver_library == WINDOWS_DRIVER
    assert selected.manifest_path.name == WINDOWS_MANIFEST
    assert selected.toolkit_root == tmp_path / TOOLKIT_ROOT
    assert selected.nvrtc_library == (
        selected.toolkit_root / "bin/x64/nvrtc64_130_0.dll"
    )
    assert selected.preload_libraries == ()


def test_selects_linux_runtime_contract(tmp_path: Path) -> None:
    """Linux selects CDLL, libcuda soname, and repository-local NVRTC."""
    _write_complete_fixture(tmp_path)

    selected = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)

    assert selected.platform_id == LINUX_PLATFORM
    assert selected.loader_kind == LINUX_LOADER
    assert selected.driver_library == LINUX_DRIVER
    assert selected.manifest_path.name == LINUX_MANIFEST
    assert selected.nvrtc_library == (
        selected.toolkit_root / "lib/libnvrtc.so.13"
    )
    assert selected.preload_libraries == (
        selected.toolkit_root / LINUX_BUILTINS,
    )


def test_unknown_platform_is_rejected(tmp_path: Path) -> None:
    """A host absent from the selector never inherits another CUDA bundle."""
    _write_complete_fixture(tmp_path)

    with pytest.raises(
        toolchain.CudaToolchainSelectionError,
        match="unsupported CUDA platform: linux-riscv64",
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, "linux-riscv64")


def test_manifest_path_escape_is_rejected(tmp_path: Path) -> None:
    """Selector entries cannot redirect package authority outside their root."""
    index = _write_index(tmp_path)
    _ = index.write_text(
        json.dumps({
            "schema_version": 1,
            "platforms": {
                LINUX_PLATFORM: {
                    "manifest": "../escape.json",
                    "loader": "cdll",
                    "driver_library": "libcuda.so.1",
                    "nvrtc_library": "lib/libnvrtc.so.13",
                    "preload_libraries": [LINUX_BUILTINS],
                }
            },
        }),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(
        toolchain.CudaToolchainSelectionError,
        match="manifest must be one local filename",
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


def test_selected_manifest_must_match_platform(tmp_path: Path) -> None:
    """A Linux selector cannot relabel a Windows CUDA package manifest."""
    _ = _write_manifest(
        tmp_path,
        WINDOWS_PLATFORM,
        "toolchain-linux-x86_64.json",
    )
    _ = _write_index(tmp_path)

    with pytest.raises(
        toolchain.CudaToolchainSelectionError,
        match="selected manifest platform mismatch",
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


def test_repository_linux_selector_matches_published_nvrtc_layout() -> None:
    """Tracked Linux selection follows the extracted NVIDIA archive layout."""
    selected = toolchain.select_cuda_toolchain(REPOSITORY_ROOT, LINUX_PLATFORM)

    assert selected.nvrtc_library == (
        selected.toolkit_root / "lib/libnvrtc.so.13"
    )
