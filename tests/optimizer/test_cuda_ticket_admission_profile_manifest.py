# File:
#   - test_cuda_ticket_admission_profile_manifest.py
# Path:
#   - tests/optimizer/test_cuda_ticket_admission_profile_manifest.py
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
#   - Generated CUDA ticket-admission manifest and strict-loader regressions.
# - Must-Not:
#   - Execute benchmark work or rewrite the tracked product manifest.
# - Allows:
#   - Inputs: retained evidence, tracked JSON, and malformed temporary
#     documents.
#   - Outputs: byte-equality, provenance, schema, and rejection assertions.
#   - Side effects: temporary manifest files only.
# - Split-When:
#   - Split when another backend gains an independent admission profile schema.
# - Merge-When:
#   - Merge when another suite owns this exact generation/loading contract.
# - Summary:
#   - CUDA ticket-admission profile manifest regressions.
# - Description:
#   - Proves evidence derivation and fail-closed product loading remain aligned.
# - Usage:
#   - Runs with optimizer tests without requiring CUDA hardware.
# - Defaults:
#   - Any evidence or manifest drift fails the test suite.
#
# Related documents:
# - accelerator/cuda/ticket_admission_profile.py
# - benchmarks/accelerator/ticket_admission_profile_manifest.py
#
# Large file:
#   - false
#

"""CUDA ticket-admission profile generation and strict loading tests."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import cast

import pytest

from accelerator.cuda import CudaHostRuntimeIdentity
from accelerator.cuda import CudaRuntimeIdentity
from accelerator.cuda import CudaTicketAdmissionHostRuntime
from accelerator.cuda import load_cuda_ticket_admission_profiles
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.ticket_admission import TicketAdmissionError
from benchmarks.accelerator.ticket_admission_profile_manifest import (
    profile_manifest,
)
from benchmarks.accelerator.ticket_admission_profile_manifest import (
    profile_manifest_text,
)

MANIFEST = "accelerator/cuda/ticket_admission_profiles.json"
PROFILE_ID = "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
SOURCE_COMMIT = "431f542ab6321eeb12b7bcb9195318f25cf376a5"
THROUGHPUT_SHA256 = (
    "edeed94f6ccca041d1db034ba7dfbc75c506e7c02069018c6f049d95e459916e"
)
RAW_SHA256 = "329716e4f429b7ab65096a61266af732b6630faf2bba2f66a643ea1b41d3214f"
ROUTE_COUNT = 7
PROFILE_VARIANT_COUNT = 2
DISPLAY_DRIVER_VERSION = "610.88"
DRIVER_API_VERSION = 13_030
NVRTC_MAJOR = 13
NVRTC_MINOR = 3
TOOLCHAIN_SHA256 = (
    "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
)
HOST_RUNTIME_IDENTITY = CudaHostRuntimeIdentity(
    host_edition="Professional",
    host_machine="x86_64",
    host_release="11",
    host_system="Windows",
    host_version="10.0.26200",
    identity_id="cuda-host-runtime-identity-v1",
    python_implementation="CPython",
    python_version="3.14.6",
)
PROFILE_HOST_RUNTIME = CudaTicketAdmissionHostRuntime(
    host_edition="Professional",
    host_machine="x86_64",
    host_release="11",
    host_system="Windows",
    host_version="10.0.26200",
    identity_id="cuda-host-runtime-identity-v1",
    python_implementation="CPython",
    python_version="3.14.6",
)
RUNTIME_IDENTITY = CudaRuntimeIdentity(
    display_driver_version=DISPLAY_DRIVER_VERSION,
    driver_api_version=DRIVER_API_VERSION,
    host_runtime_identity=HOST_RUNTIME_IDENTITY,
    identity_id="cuda-runtime-toolchain-identity-v1",
    nvrtc_major=NVRTC_MAJOR,
    nvrtc_minor=NVRTC_MINOR,
    toolchain_manifest_sha256=TOOLCHAIN_SHA256,
)


def test_generated_manifest_matches_tracked_product_bytes() -> None:
    """Retained evidence reproduces the tracked runtime manifest exactly."""
    tracked = Path(MANIFEST).read_text(encoding="utf-8")
    assert profile_manifest_text() == tracked


def test_loaded_profile_preserves_exact_provenance_and_routes() -> None:
    """The strict loader retains hashes, commit, and seven route records."""
    profiles = load_cuda_ticket_admission_profiles()
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.profile_id == PROFILE_ID
    assert profile.evidence.source_commit == SOURCE_COMMIT
    assert profile.evidence.throughput_sha256 == THROUGHPUT_SHA256
    assert profile.evidence.raw_sha256 == RAW_SHA256
    assert profile.runtime.display_driver_version == DISPLAY_DRIVER_VERSION
    assert profile.runtime.host_runtime == PROFILE_HOST_RUNTIME
    assert profile.runtime.minimum_driver_api_version == DRIVER_API_VERSION
    assert profile.runtime.nvrtc_major == NVRTC_MAJOR
    assert profile.runtime.nvrtc_minor == NVRTC_MINOR
    assert profile.runtime.toolchain_manifest_sha256 == TOOLCHAIN_SHA256
    assert len(profile.candidates) == ROUTE_COUNT
    assert [candidate.admitted for candidate in profile.candidates] == [
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]


def test_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """Duplicate object keys never acquire last-value-wins semantics."""
    manifest = tmp_path / "duplicate.json"
    _ = manifest.write_text(
        '{"schema_version":4,"schema_version":4,"profiles":[]}',
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(
        TicketAdmissionError,
        match=r"duplicate.*schema_version",
    ):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_rejects_unknown_root_keys(tmp_path: Path) -> None:
    """A future or misspelled root key requires a schema migration."""
    document = profile_manifest()
    document["unexpected"] = True
    manifest = _write_manifest(tmp_path, document, "unknown.json")
    with pytest.raises(TicketAdmissionError, match="unknown unexpected"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_rejects_unsupported_schema(tmp_path: Path) -> None:
    """Runtime loading never guesses a newer admission schema."""
    document = profile_manifest()
    document["schema_version"] = 5
    manifest = _write_manifest(tmp_path, document, "schema.json")
    with pytest.raises(TicketAdmissionError, match=r"unsupported.*schema"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_rejects_duplicate_route_identity(tmp_path: Path) -> None:
    """Two records for one mode/group cannot be cherry-picked."""
    document = profile_manifest()
    profile = _first_profile(document)
    routes = cast("list[object]", profile["routes"])
    first = cast("dict[str, object]", routes[0])
    routes.append(dict(first))
    manifest = _write_manifest(tmp_path, document, "routes.json")
    with pytest.raises(TicketAdmissionError, match="routes duplicates"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_rejects_invalid_display_driver_version(
    tmp_path: Path,
) -> None:
    """Malformed display-driver text cannot enter a runtime profile."""
    document = profile_manifest()
    profile = _first_profile(document)
    runtime = cast("dict[str, object]", profile["runtime"])
    runtime["display_driver_version"] = "610"
    manifest = _write_manifest(tmp_path, document, "driver.json")
    with pytest.raises(TicketAdmissionError, match="dotted numeric version"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_rejects_invalid_host_runtime(
    tmp_path: Path,
) -> None:
    """Empty host/Python identity fields cannot enter a runtime profile."""
    document = profile_manifest()
    profile = _first_profile(document)
    runtime = cast("dict[str, object]", profile["runtime"])
    host = cast("dict[str, object]", runtime["host_runtime"])
    host["python_version"] = ""
    manifest = _write_manifest(tmp_path, document, "host.json")
    with pytest.raises(TicketAdmissionError, match="trimmed non-empty string"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_loader_accepts_distinct_runtime_profiles(tmp_path: Path) -> None:
    """One workload/device may retain independent exact runtime variants."""
    document = profile_manifest()
    _append_profile_variant(
        document,
        profile_id="rtx4060-alternate-driver-v1",
        display_driver_version="611.00",
    )
    manifest = _write_manifest(tmp_path, document, "variants.json")
    profiles = load_cuda_ticket_admission_profiles(manifest)
    assert len(profiles) == PROFILE_VARIANT_COUNT
    assert [profile.runtime.display_driver_version for profile in profiles] == [
        DISPLAY_DRIVER_VERSION,
        "611.00",
    ]


def test_loader_rejects_duplicate_runtime_context(tmp_path: Path) -> None:
    """A second ID cannot duplicate one exact runtime/workload context."""
    document = profile_manifest()
    _append_profile_variant(
        document,
        profile_id="rtx4060-duplicate-context-v1",
        display_driver_version=DISPLAY_DRIVER_VERSION,
    )
    manifest = _write_manifest(tmp_path, document, "duplicate-context.json")
    with pytest.raises(
        TicketAdmissionError,
        match="capability/workload/runtime context",
    ):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_profile_plan_rejects_mismatched_capability() -> None:
    """Direct profile use cannot bypass exact device matching."""
    profile = load_cuda_ticket_admission_profiles()[0]
    mismatch = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="another sm_89 device",
    )
    with pytest.raises(
        TicketAdmissionError,
        match="capability/runtime mismatched",
    ):
        _ = profile.plan(mismatch, RUNTIME_IDENTITY, 1)


def test_profile_plan_rejects_mismatched_runtime() -> None:
    """Direct profile use cannot bypass runtime compatibility checks."""
    profile = load_cuda_ticket_admission_profiles()[0]
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    mismatch = CudaRuntimeIdentity(
        display_driver_version="611.00",
        driver_api_version=DRIVER_API_VERSION,
        host_runtime_identity=HOST_RUNTIME_IDENTITY,
        identity_id=RUNTIME_IDENTITY.identity_id,
        nvrtc_major=NVRTC_MAJOR,
        nvrtc_minor=NVRTC_MINOR,
        toolchain_manifest_sha256=TOOLCHAIN_SHA256,
    )
    with pytest.raises(
        TicketAdmissionError,
        match="capability/runtime mismatched",
    ):
        _ = profile.plan(capability, mismatch, 1)


def _append_profile_variant(
    document: dict[str, object],
    *,
    profile_id: str,
    display_driver_version: str,
) -> None:
    profiles = cast("list[object]", document["profiles"])
    variant = deepcopy(_first_profile(document))
    variant["profile_id"] = profile_id
    runtime = cast("dict[str, object]", variant["runtime"])
    runtime["display_driver_version"] = display_driver_version
    profiles.append(variant)


def _first_profile(document: dict[str, object]) -> dict[str, object]:
    profiles = cast("list[object]", document["profiles"])
    return cast("dict[str, object]", profiles[0])


def _write_manifest(
    directory: Path,
    document: dict[str, object],
    name: str,
) -> Path:
    path = directory / name
    _ = path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
