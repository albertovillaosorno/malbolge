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
import os
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
INDEX_AUTHORITY = "index"
SOURCE_RECHECK = 2


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


@pytest.mark.parametrize("authority", ["index", "manifest"])
def test_toolchain_rejects_linked_json_authority(
    tmp_path: Path,
    authority: str,
) -> None:
    """Tracked manifest bytes must come from the named physical source file."""
    _write_complete_fixture(tmp_path)
    selected = (
        tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX
        if authority == INDEX_AUTHORITY
        else _manifest_root(tmp_path) / LINUX_MANIFEST
    )
    actual = selected.with_name("actual.json")
    _ = actual.write_bytes(selected.read_bytes())
    selected.unlink()
    try:
        _ = selected.symlink_to(actual)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match=r"redirect|regular"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


def test_toolchain_rejects_linked_manifest_parent(tmp_path: Path) -> None:
    """A symlinked directory must not introduce external platform metadata."""
    real_root = tmp_path / "real"
    _write_complete_fixture(real_root)
    alias_root = tmp_path / "alias"
    try:
        _ = alias_root.symlink_to(real_root, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(toolchain.CudaToolchainSelectionError, match="redirect"):
        _ = toolchain.select_cuda_toolchain(alias_root, LINUX_PLATFORM)


@pytest.mark.parametrize("authority", ["index", "manifest"])
def test_toolchain_rejects_oversized_json(
    tmp_path: Path,
    authority: str,
) -> None:
    """Malformed tracked documents are bounded before JSON materialization."""
    _write_complete_fixture(tmp_path)
    selected = (
        tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX
        if authority == INDEX_AUTHORITY
        else _manifest_root(tmp_path) / LINUX_MANIFEST
    )
    with selected.open("wb") as stream:
        _ = stream.truncate(1024 * 1024 + 1)
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match="byte limit"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


def test_toolchain_invalid_utf8_is_typed_error(tmp_path: Path) -> None:
    """Corrupt encoded metadata fails closed through the public error type."""
    _write_complete_fixture(tmp_path)
    _ = (tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX).write_bytes(b"\xff")
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match="cannot read"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("authority", ["index", "manifest"])
def test_toolchain_rejects_directory_and_fifo_source(
    tmp_path: Path,
    authority: str,
) -> None:
    """Neither directory nor writerless pipe may stand in for source JSON."""
    _write_complete_fixture(tmp_path)
    selected = (
        tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX
        if authority == INDEX_AUTHORITY
        else _manifest_root(tmp_path) / LINUX_MANIFEST
    )
    selected.unlink()
    selected.mkdir()
    with pytest.raises(toolchain.CudaToolchainSelectionError, match="regular"):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)
    selected.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO creation unsupported on host")
    mkfifo(selected)
    with pytest.raises(toolchain.CudaToolchainSelectionError, match="regular"):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("authority", ["index", "manifest"])
def test_toolchain_rejects_inode_swap_between_stat_and_open(
    tmp_path: Path,
    authority: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even same-byte replacements cannot change admitted source identity."""
    _write_complete_fixture(tmp_path)
    selected = (
        tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX
        if authority == INDEX_AUTHORITY
        else _manifest_root(tmp_path) / LINUX_MANIFEST
    )
    replacement = selected.with_name("replacement.json")
    _ = replacement.write_bytes(selected.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == selected:
            _ = replacement.replace(selected)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match="changed before read"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)
    assert swapped


@pytest.mark.parametrize("authority", ["index", "manifest"])
def test_toolchain_rejects_same_byte_inode_swap_after_read(
    tmp_path: Path,
    authority: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The named manifest must still match its descriptor after reading."""
    _write_complete_fixture(tmp_path)
    selected = (
        tmp_path / toolchain.CUDA_TOOLCHAIN_INDEX
        if authority == INDEX_AUTHORITY
        else _manifest_root(tmp_path) / LINUX_MANIFEST
    )
    replacement = selected.with_name("replacement.json")
    _ = replacement.write_bytes(selected.read_bytes())
    real_lstat = Path.lstat
    observed = 0

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == selected:
            observed += 1
            if observed == SOURCE_RECHECK:
                _ = replacement.replace(selected)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match="changed during read"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)
    assert observed == SOURCE_RECHECK


def test_toolchain_rejects_manifest_in_place_mutation_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unchanged inode and size do not conceal modified manifest content."""
    _write_complete_fixture(tmp_path)
    selected = _manifest_root(tmp_path) / LINUX_MANIFEST
    real_lstat = Path.lstat
    observed = 0

    def mutate_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == selected:
            observed += 1
            if observed == SOURCE_RECHECK:
                with selected.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", mutate_at_recheck)
    with pytest.raises(
        toolchain.CudaToolchainSelectionError, match="changed during read"
    ):
        _ = toolchain.select_cuda_toolchain(tmp_path, LINUX_PLATFORM)
    assert observed == SOURCE_RECHECK
