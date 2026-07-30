# File:
#   - test_cuda_runtime_identity.py
# Path:
#   - tests/optimizer/test_cuda_runtime_identity.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - CUDA Driver API, NVRTC, and toolchain-manifest identity regressions.
# - Must-Not:
#   - Treat Driver API compatibility as display-driver build identity.
# - Allows:
#   - Inputs: fake version callbacks, temporary manifests, and scoped live CUDA.
# - Outputs: exact identity, failure classification, and live-version
#   assertions.
# - Side effects: temporary files and scoped optional CUDA execution only.
# - Split-When:
#   - Split when NVML display-driver identity gains an independent contract.
# - Merge-When:
#   - Merge when another suite owns this exact runtime identity boundary.
# - Summary:
#   - CUDA runtime/toolchain identity regressions.
# - Description:
#   - Proves measured compatibility and manifest digest are fail-closed.
# - Usage:
#   - Runs with optimizer tests; the live route skips without CUDA.
# - Defaults:
#   - Query or manifest failure classifies the optional backend unavailable.
#
# Related documents:
# - accelerator/cuda/runtime.py
# - accelerator/cuda/toolchain.json
#
# Large file:
#   - false
#

"""CUDA Driver API, NVRTC, and toolchain identity tests."""

from __future__ import annotations

import ctypes
from hashlib import sha256
from typing import TYPE_CHECKING

import pytest

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import cuda_runtime_identity_id
from accelerator.cuda import measure_cuda_runtime_identity
from accelerator.cuda.runtime import CUDA_TOOLCHAIN_MANIFEST
from accelerator.exact_primitives import AcceleratorUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

IDENTITY_ID = "cuda-runtime-toolchain-identity-v1"
DRIVER_API_VERSION = 13_030
NVRTC_MAJOR = 13
NVRTC_MINOR = 3
TOOLCHAIN_SHA256 = (
    "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
)
FAILURE_STATUS = 7


def _version_callback(
    value: int,
    *,
    status: int = 0,
) -> Callable[..., int]:
    def callback(pointer: ctypes.c_void_p) -> int:
        target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_int))
        target[0] = value
        return status

    return callback


def _nvrtc_callback(
    major: int,
    minor: int,
    *,
    status: int = 0,
) -> Callable[..., int]:
    def callback(
        major_pointer: ctypes.c_void_p,
        minor_pointer: ctypes.c_void_p,
    ) -> int:
        major_target = ctypes.cast(
            major_pointer,
            ctypes.POINTER(ctypes.c_int),
        )
        minor_target = ctypes.cast(
            minor_pointer,
            ctypes.POINTER(ctypes.c_int),
        )
        major_target[0] = major
        minor_target[0] = minor
        return status

    return callback


def test_cuda_runtime_identity_protocol_is_stable() -> None:
    """The measured runtime identity remains explicitly versioned."""
    assert cuda_runtime_identity_id() == IDENTITY_ID


def test_fake_runtime_identity_measures_versions_and_manifest(
    tmp_path: Path,
) -> None:
    """Callbacks and exact manifest bytes produce one immutable identity."""
    manifest = tmp_path / "toolchain.json"
    payload = b'{"schema_version":1}\n'
    _ = manifest.write_bytes(payload)
    identity = measure_cuda_runtime_identity(
        _version_callback(DRIVER_API_VERSION),
        _nvrtc_callback(NVRTC_MAJOR, NVRTC_MINOR),
        manifest,
    )
    assert identity.driver_api_version == DRIVER_API_VERSION
    assert identity.identity_id == IDENTITY_ID
    assert identity.nvrtc_major == NVRTC_MAJOR
    assert identity.nvrtc_minor == NVRTC_MINOR
    assert identity.toolchain_manifest_sha256 == sha256(payload).hexdigest()


def test_driver_version_query_failure_is_unavailable(tmp_path: Path) -> None:
    """A failed Driver API query prevents optional backend admission."""
    manifest = tmp_path / "toolchain.json"
    _ = manifest.write_text("{}\n", encoding="utf-8", newline="\n")
    with pytest.raises(AcceleratorUnavailableError, match="cuDriverGetVersion"):
        _ = measure_cuda_runtime_identity(
            _version_callback(DRIVER_API_VERSION, status=FAILURE_STATUS),
            _nvrtc_callback(NVRTC_MAJOR, NVRTC_MINOR),
            manifest,
        )


def test_nvrtc_version_query_failure_is_unavailable(tmp_path: Path) -> None:
    """A failed NVRTC query prevents evidence-bound profile use."""
    manifest = tmp_path / "toolchain.json"
    _ = manifest.write_text("{}\n", encoding="utf-8", newline="\n")
    with pytest.raises(AcceleratorUnavailableError, match="nvrtcVersion"):
        _ = measure_cuda_runtime_identity(
            _version_callback(DRIVER_API_VERSION),
            _nvrtc_callback(
                NVRTC_MAJOR,
                NVRTC_MINOR,
                status=FAILURE_STATUS,
            ),
            manifest,
        )


def test_missing_toolchain_manifest_is_unavailable(tmp_path: Path) -> None:
    """Runtime identity never continues without exact manifest bytes."""
    with pytest.raises(
        AcceleratorUnavailableError, match="manifest unavailable"
    ):
        _ = measure_cuda_runtime_identity(
            _version_callback(DRIVER_API_VERSION),
            _nvrtc_callback(NVRTC_MAJOR, NVRTC_MINOR),
            tmp_path / "missing.json",
        )


def test_live_cuda_runtime_identity_matches_current_compatibility() -> None:
    """Live CUDA reports retained API/NVRTC and tracked manifest identity."""
    try:
        adapter = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with adapter:
        identity = adapter.runtime_identity
    assert identity.driver_api_version >= DRIVER_API_VERSION
    assert (identity.nvrtc_major, identity.nvrtc_minor) == (
        NVRTC_MAJOR,
        NVRTC_MINOR,
    )
    assert identity.toolchain_manifest_sha256 == TOOLCHAIN_SHA256
    assert sha256(CUDA_TOOLCHAIN_MANIFEST.read_bytes()).hexdigest() == (
        TOOLCHAIN_SHA256
    )
