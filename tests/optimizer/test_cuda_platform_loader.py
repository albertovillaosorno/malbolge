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
#   - CUDA Windows/Linux native-library loader selection evidence.
# - Must-Not:
#   - Execute CUDA symbols or require a physical GPU.
# - Allows:
#   - Inputs: immutable toolchain selections and injected native loaders.
#   - Outputs: exact loader names, search-directory lifetime, typed failures.
#   - Side effects: test-local toolkit fixtures only.
# - Split-When:
#   - Native loader policy gains another independently supported platform.
# - Merge-When:
#   - CUDA runtime identity tests own these exact loader contracts.
# - Summary:
#   - Proves Windows WinDLL and Linux CDLL selection without hardware.
# - Description:
#   - Exercises platform normalization and library-loading boundaries.
# - Usage:
#   - Collected with optimizer tests on every supported development host.
# - Defaults:
#   - Missing pinned NVRTC fails before any Driver API load.
#

"""CUDA Windows/Linux native-library loader selection evidence."""

from __future__ import annotations

# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false
import ctypes
from typing import TYPE_CHECKING

from accelerator.cuda import runtime
from accelerator.cuda.toolchain import CudaToolchainSelection
from accelerator.exact_primitives import AcceleratorUnavailableError
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

WINDOWS_PLATFORM = "windows-x86_64"
LINUX_PLATFORM = "linux-x86_64"
WINDOWS_DRIVER = "nvcuda.dll"
LINUX_DRIVER = "libcuda.so.1"
WINDOWS_NVRTC = "bin/x64/nvrtc64_130_0.dll"
LINUX_NVRTC = "lib64/libnvrtc.so.13"


def _selection(
    tmp_path: Path,
    platform_id: str,
) -> CudaToolchainSelection:
    toolkit = tmp_path / "toolkit"
    if platform_id == WINDOWS_PLATFORM:
        loader_kind = "windll"
        driver = WINDOWS_DRIVER
        nvrtc = WINDOWS_NVRTC
        manifest_name = "toolchain.json"
    else:
        loader_kind = "cdll"
        driver = LINUX_DRIVER
        nvrtc = LINUX_NVRTC
        manifest_name = "toolchain-linux-x86_64.json"
    nvrtc_path = toolkit / nvrtc
    nvrtc_path.parent.mkdir(parents=True)
    nvrtc_path.touch()
    return CudaToolchainSelection(
        platform_id=platform_id,
        manifest_path=tmp_path / manifest_name,
        toolkit_root=toolkit,
        loader_kind=loader_kind,
        driver_library=driver,
        nvrtc_library=nvrtc_path,
    )


def _loader(calls: list[str]) -> Callable[[str], ctypes.CDLL]:
    def load(name: str) -> ctypes.CDLL:
        calls.append(name)
        return ctypes.CDLL(None)

    return load


def _directory_opener(
    paths: list[Path],
    token: object,
) -> Callable[[Path], object]:
    def open_directory(path: Path) -> object:
        paths.append(path)
        return token

    return open_directory


def test_platform_id_normalizes_windows_and_linux() -> None:
    """Runtime host IDs match the tracked CUDA selector keys."""
    assert (
        runtime._cuda_platform_id(system="Windows", machine="AMD64")
        == WINDOWS_PLATFORM
    )
    assert (
        runtime._cuda_platform_id(system="Linux", machine="x86_64")
        == LINUX_PLATFORM
    )


def test_windows_uses_windll_names_and_search_directory(tmp_path: Path) -> None:
    """Windows loads nvcuda/NVRTC with one explicit DLL search lifetime."""
    selection = _selection(tmp_path, WINDOWS_PLATFORM)
    windows_calls: list[str] = []
    posix_calls: list[str] = []
    search_paths: list[Path] = []
    token = object()

    loaded = runtime._load_cuda_libraries(
        selection,
        windows_loader=_loader(windows_calls),
        posix_loader=_loader(posix_calls),
        dll_directory_opener=_directory_opener(search_paths, token),
    )

    assert windows_calls == [WINDOWS_DRIVER, str(selection.nvrtc_library)]
    assert posix_calls == []
    assert search_paths == [selection.nvrtc_library.parent]
    assert loaded.search_directory is token


def test_linux_uses_cdll_without_windows_search_directory(
    tmp_path: Path,
) -> None:
    """Linux loads libcuda/NVRTC directly and never opens a DLL directory."""
    selection = _selection(tmp_path, LINUX_PLATFORM)
    windows_calls: list[str] = []
    posix_calls: list[str] = []
    search_paths: list[Path] = []

    loaded = runtime._load_cuda_libraries(
        selection,
        windows_loader=_loader(windows_calls),
        posix_loader=_loader(posix_calls),
        dll_directory_opener=_directory_opener(search_paths, object()),
    )

    assert windows_calls == []
    assert posix_calls == [LINUX_DRIVER, str(selection.nvrtc_library)]
    assert search_paths == []
    assert loaded.search_directory is None


def test_missing_pinned_nvrtc_fails_before_driver_load(tmp_path: Path) -> None:
    """An incomplete toolkit never falls back to ambient NVRTC."""
    selection = _selection(tmp_path, LINUX_PLATFORM)
    selection.nvrtc_library.unlink()
    calls: list[str] = []

    with pytest.raises(
        AcceleratorUnavailableError,
        match="pinned CUDA NVRTC library missing",
    ):
        _ = runtime._load_cuda_libraries(
            selection,
            windows_loader=_loader(calls),
            posix_loader=_loader(calls),
            dll_directory_opener=_directory_opener([], object()),
        )

    assert calls == []
