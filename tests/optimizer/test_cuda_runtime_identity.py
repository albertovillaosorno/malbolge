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
#   - CUDA, NVML, host OS, Python, and toolchain identity regressions.
# - Must-Not:
#   - Make optional NVML a prerequisite for ordinary CUDA availability.
# - Allows:
#   - Inputs: fake FFI callbacks, temporary manifests, and scoped live CUDA.
# - Outputs: exact identity, failure classification, and live-version
#   assertions.
# - Side effects: temporary files and scoped optional CUDA execution only.
# - Split-When:
#   - Split when NVML gains device-management responsibilities.
# - Merge-When:
#   - Merge when another suite owns this exact runtime identity boundary.
# - Summary:
#   - CUDA runtime, display-driver, host, and toolchain regressions.
# - Description:
#   - Proves required compatibility and optional environment identity.
# - Usage:
#   - Runs with optimizer tests; the live route skips without CUDA.
# - Defaults:
#   - Optional identity failure leaves CUDA available but profiles unmatched.
#
# Related documents:
# - accelerator/cuda/runtime.py
# - accelerator/cuda/toolchain.json
#
# Large file:
#   - false
#

"""CUDA, NVML, host OS, Python, and toolchain identity tests."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

import pytest

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaHostRuntimeIdentity
from accelerator.cuda import CudaRuntimeEnvironment
from accelerator.cuda import cuda_host_runtime_identity_id
from accelerator.cuda import cuda_runtime_identity_id
from accelerator.cuda import measure_cuda_host_runtime_identity
from accelerator.cuda import measure_cuda_runtime_identity
from accelerator.cuda import measure_nvml_display_driver_version
from accelerator.cuda.runtime import CUDA_TOOLCHAIN_MANIFEST
from accelerator.exact_primitives import AcceleratorUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

IDENTITY_ID = "cuda-runtime-toolchain-identity-v1"
HOST_IDENTITY_ID = "cuda-host-runtime-identity-v1"
DRIVER_API_VERSION = 13_030
NVRTC_MAJOR = 13
NVRTC_MINOR = 3
TOOLCHAIN_SHA256 = (
    "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
)
FAILURE_STATUS = 7
DISPLAY_DRIVER_VERSION = "610.88"
HOST_RUNTIME_IDENTITY = CudaHostRuntimeIdentity(
    host_edition="Professional",
    host_machine="x86_64",
    host_release="11",
    host_system="Windows",
    host_version="10.0.26200",
    identity_id=HOST_IDENTITY_ID,
    python_implementation="CPython",
    python_version="3.14.6",
)
ENVIRONMENT = CudaRuntimeEnvironment(
    display_driver_version=DISPLAY_DRIVER_VERSION,
    host_runtime_identity=HOST_RUNTIME_IDENTITY,
)


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


@dataclass(slots=True)
class _FakeNvmlState:
    init_status: int = 0
    query_status: int = 0
    shutdown_calls: int = 0
    shutdown_status: int = 0

    def load(
        self,
        path: Path,
    ) -> tuple[Callable[..., int], Callable[..., int], Callable[..., int]]:
        del path
        return self.init, self.driver_version, self.shutdown

    def init(self) -> int:
        return self.init_status

    def driver_version(self, buffer: ctypes.c_void_p, size: int) -> int:
        del size
        payload = DISPLAY_DRIVER_VERSION.encode("ascii") + b"\0"
        _ = ctypes.memmove(buffer, payload, len(payload))
        return self.query_status

    def shutdown(self) -> int:
        self.shutdown_calls += 1
        return self.shutdown_status


def test_cuda_runtime_identity_protocol_is_stable() -> None:
    """Measured CUDA and host runtime identities remain versioned."""
    assert cuda_host_runtime_identity_id() == HOST_IDENTITY_ID
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
        environment=ENVIRONMENT,
    )
    assert identity.display_driver_version == DISPLAY_DRIVER_VERSION
    assert identity.driver_api_version == DRIVER_API_VERSION
    assert identity.host_runtime_identity == HOST_RUNTIME_IDENTITY
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


def test_runtime_identity_rejects_malformed_display_driver(
    tmp_path: Path,
) -> None:
    """Malformed display-driver text never enters a measured identity."""
    manifest = tmp_path / "toolchain.json"
    _ = manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(
        AcceleratorUnavailableError,
        match="display-driver version is invalid",
    ):
        _ = measure_cuda_runtime_identity(
            _version_callback(DRIVER_API_VERSION),
            _nvrtc_callback(NVRTC_MAJOR, NVRTC_MINOR),
            manifest,
            environment=CudaRuntimeEnvironment(display_driver_version="610"),
        )


def test_measured_host_runtime_matches_retained_environment() -> None:
    """Live host and Python identity match the retained evidence context."""
    assert measure_cuda_host_runtime_identity() == HOST_RUNTIME_IDENTITY


def test_host_runtime_identity_rejects_invalid_text() -> None:
    """Malformed host fields never enter a composed CUDA identity."""
    invalid = CudaHostRuntimeIdentity(
        host_edition="Professional",
        host_machine="",
        host_release="11",
        host_system="Windows",
        host_version="10.0.26200",
        identity_id=HOST_IDENTITY_ID,
        python_implementation="CPython",
        python_version="3.14.6",
    )
    with pytest.raises(
        AcceleratorUnavailableError,
        match="contains invalid text",
    ):
        _ = invalid.validated()


def test_missing_nvml_is_optional(tmp_path: Path) -> None:
    """Missing NVML leaves display build unknown without disabling CUDA."""
    assert measure_nvml_display_driver_version(tmp_path / "missing.dll") is None


def test_fake_nvml_init_failure_is_optional(tmp_path: Path) -> None:
    """Failed NVML initialization leaves the optional identity unknown."""
    state = _FakeNvmlState(init_status=FAILURE_STATUS)
    assert (
        measure_nvml_display_driver_version(
            tmp_path / "nvml.dll",
            loader=state.load,
        )
        is None
    )
    assert state.shutdown_calls == 0


def test_fake_nvml_returns_driver_build_and_shuts_down(
    tmp_path: Path,
) -> None:
    """A successful optional NVML lifetime publishes exact build text."""
    state = _FakeNvmlState()
    assert (
        measure_nvml_display_driver_version(
            tmp_path / "nvml.dll",
            loader=state.load,
        )
        == DISPLAY_DRIVER_VERSION
    )
    assert state.shutdown_calls == 1


def test_fake_nvml_query_failure_is_optional_and_shuts_down(
    tmp_path: Path,
) -> None:
    """A failed version query returns unknown after exact shutdown."""
    state = _FakeNvmlState(query_status=FAILURE_STATUS)
    assert (
        measure_nvml_display_driver_version(
            tmp_path / "nvml.dll",
            loader=state.load,
        )
        is None
    )
    assert state.shutdown_calls == 1


def test_fake_nvml_shutdown_failure_is_optional(
    tmp_path: Path,
) -> None:
    """Failed NVML shutdown prevents publishing the optional build identity."""
    state = _FakeNvmlState(shutdown_status=FAILURE_STATUS)
    assert (
        measure_nvml_display_driver_version(
            tmp_path / "nvml.dll",
            loader=state.load,
        )
        is None
    )
    assert state.shutdown_calls == 1


def test_live_cuda_runtime_identity_matches_current_compatibility() -> None:
    """Live CUDA reports retained API/NVRTC and tracked manifest identity."""
    try:
        adapter = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with adapter:
        identity = adapter.runtime_identity
    assert identity.display_driver_version == DISPLAY_DRIVER_VERSION
    assert identity.driver_api_version >= DRIVER_API_VERSION
    assert identity.host_runtime_identity == HOST_RUNTIME_IDENTITY
    assert (identity.nvrtc_major, identity.nvrtc_minor) == (
        NVRTC_MAJOR,
        NVRTC_MINOR,
    )
    assert identity.toolchain_manifest_sha256 == TOOLCHAIN_SHA256
    assert sha256(CUDA_TOOLCHAIN_MANIFEST.read_bytes()).hexdigest() == (
        TOOLCHAIN_SHA256
    )
