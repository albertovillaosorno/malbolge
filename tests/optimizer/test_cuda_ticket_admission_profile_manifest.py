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

"""CUDA ticket-admission profile generation and strict loading tests."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
from typing import cast

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
import pytest

from benchmarks.accelerator import (
    ticket_admission_profile_manifest as generator,
)

MANIFEST = (
    "src/optimization/accelerator/adapter-outbound/accelerator/cuda/"
    "ticket_admission_profiles.json"
)
PROFILE_ID = "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
SOURCE_COMMIT = "431f542ab6321eeb12b7bcb9195318f25cf376a5"
THROUGHPUT_SHA256 = (
    "edeed94f6ccca041d1db034ba7dfbc75c506e7c02069018c6f049d95e459916e"
)
RAW_SHA256 = "329716e4f429b7ab65096a61266af732b6630faf2bba2f66a643ea1b41d3214f"
ROUTE_COUNT = 7
FILE_REDIRECT = "file"
SOURCE_RECHECK = 2
TOOLCHAIN_JSON_NAME = "toolchain.json"
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


@pytest.mark.parametrize("redirect", ["file", "directory"])
def test_profile_loader_rejects_redirected_manifest(
    tmp_path: Path,
    redirect: str,
) -> None:
    """Matching retained profiles do not authorize filesystem aliases."""
    real = tmp_path / "real"
    real.mkdir()
    source = real / "profiles.json"
    _ = source.write_text(profile_manifest_text(), encoding="utf-8")
    if redirect == FILE_REDIRECT:
        alias = tmp_path / "alias.json"
    else:
        alias = tmp_path / "alias"
    try:
        if redirect == FILE_REDIRECT:
            _ = alias.symlink_to(source)
        else:
            _ = alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    path = alias if redirect == FILE_REDIRECT else alias / source.name
    with pytest.raises(TicketAdmissionError, match=r"regular|redirect"):
        _ = load_cuda_ticket_admission_profiles(path)


def test_profile_loader_rejects_oversized_json(tmp_path: Path) -> None:
    """Untrusted profile documents are bounded before JSON parsing."""
    manifest = tmp_path / "huge.json"
    with manifest.open("wb") as stream:
        _ = stream.truncate(1024 * 1024 + 1)
    with pytest.raises(TicketAdmissionError, match="byte limit"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_profile_loader_rejects_invalid_utf8_as_typed_error(
    tmp_path: Path,
) -> None:
    """Invalid input encodings never escape the declared error boundary."""
    manifest = tmp_path / "invalid.json"
    _ = manifest.write_bytes(b"\xff")
    with pytest.raises(TicketAdmissionError, match="cannot read"):
        _ = load_cuda_ticket_admission_profiles(manifest)


def test_profile_loader_rejects_directory_and_fifo_manifest(
    tmp_path: Path,
) -> None:
    """Nonregular sources cannot block the admission path or supply JSON."""
    source = tmp_path / "source.json"
    source.mkdir()
    with pytest.raises(TicketAdmissionError, match="regular"):
        _ = load_cuda_ticket_admission_profiles(source)
    source.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unavailable on host")
    mkfifo(source)
    with pytest.raises(TicketAdmissionError, match="regular"):
        _ = load_cuda_ticket_admission_profiles(source)


def test_profile_loader_rejects_inode_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An equal-byte file replacement must invalidate pre-open admission."""
    source = tmp_path / "source.json"
    _ = source.write_text(profile_manifest_text(), encoding="utf-8")
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    replaced = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal replaced
        if path == source:
            _ = replacement.replace(source)
            replaced = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(TicketAdmissionError, match="changed before read"):
        _ = load_cuda_ticket_admission_profiles(source)
    assert replaced


def test_profile_loader_rejects_inode_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inode replacement after reading bytes cannot authorize a profile."""
    source = tmp_path / "source.json"
    _ = source.write_text(profile_manifest_text(), encoding="utf-8")
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(source.read_bytes())
    real_lstat = Path.lstat
    observed = 0

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == source:
            observed += 1
            if observed == SOURCE_RECHECK:
                _ = replacement.replace(source)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(TicketAdmissionError, match="changed during read"):
        _ = load_cuda_ticket_admission_profiles(source)
    assert observed == SOURCE_RECHECK


def test_profile_loader_rejects_in_place_edit_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-inode, equal-size mutations cannot authorize retained routes."""
    source = tmp_path / "source.json"
    _ = source.write_text(profile_manifest_text(), encoding="utf-8")
    real_lstat = Path.lstat
    observed = 0

    def mutate_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == source:
            observed += 1
            if observed == SOURCE_RECHECK:
                with source.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", mutate_at_recheck)
    with pytest.raises(TicketAdmissionError, match="changed during read"):
        _ = load_cuda_ticket_admission_profiles(source)
    assert observed == SOURCE_RECHECK


def _retained_fixture(root: Path) -> Path:
    """Copy each tracked source of one exact CUDA retained evidence bundle.

    Returns:
        Independent complete repository-root fixture without source aliases.

    """
    tracked = (
        generator.EVIDENCE_RELATIVE / "experiment.toml",
        generator.EVIDENCE_RELATIVE / "raw.csv",
        generator.EVIDENCE_RELATIVE / "source-commit.txt",
        generator.EVIDENCE_RELATIVE / "throughput.json",
        generator.TOOLCHAIN_RELATIVE,
    )
    for relative in tracked:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copyfile(generator.ROOT / relative, target)
    return root


def test_retained_generator_rejects_forged_parse_with_authentic_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Route payload and claimed SHA cannot come from distinct file reads."""
    root = _retained_fixture(tmp_path)
    throughput = root / generator.EVIDENCE_RELATIVE / "throughput.json"
    forged = cast(
        "dict[str, object]",
        json.loads(throughput.read_text(encoding="utf-8")),
    )
    routes = cast("dict[str, object]", forged["routes"])
    baseline = cast("dict[str, object]", routes["synchronous-sequential-1"])
    median = baseline["median_ns"]
    assert type(median) is int
    baseline["median_ns"] = median + 1
    untrusted = json.dumps(forged)
    real_read_text = Path.read_text

    def substitute_parse_source(
        path: Path,
        *,
        encoding: str | None = None,
    ) -> str:
        if path == throughput:
            return untrusted
        return real_read_text(path, encoding=encoding)

    monkeypatch.setattr(Path, "read_text", substitute_parse_source)
    assert profile_manifest_text(root) == profile_manifest_text(generator.ROOT)


@pytest.mark.parametrize(
    "source",
    [
        "throughput.json",
        "experiment.toml",
        "raw.csv",
        "source-commit.txt",
        "toolchain.json",
    ],
)
def test_retained_generator_rejects_linked_source(
    tmp_path: Path,
    source: str,
) -> None:
    """Matching evidence bytes do not grant authority to a linked source."""
    root = _retained_fixture(tmp_path)
    relative = (
        generator.TOOLCHAIN_RELATIVE
        if source == TOOLCHAIN_JSON_NAME
        else generator.EVIDENCE_RELATIVE / source
    )
    path = root / relative
    actual = path.with_name("physical-source")
    _ = actual.write_bytes(path.read_bytes())
    path.unlink()
    try:
        _ = path.symlink_to(actual)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(
        generator.ProfileManifestError, match=r"regular|redirect"
    ):
        _ = profile_manifest(root)


def test_retained_generator_rejects_redirected_evidence_directory(
    tmp_path: Path,
) -> None:
    """No retained evidence may be read through a linked parent folder."""
    real_root = _retained_fixture(tmp_path / "real")
    alias = tmp_path / "alias"
    try:
        _ = alias.symlink_to(real_root, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(generator.ProfileManifestError, match="redirect"):
        _ = profile_manifest(alias)


def test_retained_generator_rejects_oversized_raw_csv(tmp_path: Path) -> None:
    """Pinned raw sample input must be bounded before hashing."""
    root = _retained_fixture(tmp_path)
    raw = root / generator.EVIDENCE_RELATIVE / "raw.csv"
    with raw.open("wb") as stream:
        _ = stream.truncate(1024 * 1024 + 1)
    with pytest.raises(generator.ProfileManifestError, match="byte limit"):
        _ = profile_manifest(root)


def test_retained_generator_invalid_utf8_is_typed_error(tmp_path: Path) -> None:
    """Invalid source encoding uses the declared provenance error boundary."""
    root = _retained_fixture(tmp_path)
    evidence = root / generator.EVIDENCE_RELATIVE / "experiment.toml"
    _ = evidence.write_bytes(b"\xff")
    with pytest.raises(generator.ProfileManifestError, match="cannot read"):
        _ = profile_manifest(root)


def test_retained_generator_rejects_special_source_files(
    tmp_path: Path,
) -> None:
    """Retained evidence cannot be sourced from a directory or FIFO."""
    root = _retained_fixture(tmp_path)
    source = root / generator.EVIDENCE_RELATIVE / "experiment.toml"
    source.unlink()
    source.mkdir()
    with pytest.raises(generator.ProfileManifestError, match="regular"):
        _ = profile_manifest(root)
    source.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO creation unavailable")
    mkfifo(source)
    with pytest.raises(generator.ProfileManifestError, match="regular"):
        _ = profile_manifest(root)


def test_retained_generator_rejects_source_inode_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-byte inode swaps cannot alter the admitted source descriptor."""
    root = _retained_fixture(tmp_path)
    throughput = root / generator.EVIDENCE_RELATIVE / "throughput.json"
    replacement = throughput.with_name("replacement.json")
    _ = replacement.write_bytes(throughput.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == throughput:
            _ = replacement.replace(throughput)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(
        generator.ProfileManifestError, match="changed before read"
    ):
        _ = profile_manifest(root)
    assert swapped


def test_retained_generator_rejects_source_inode_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The named source must still match its descriptor after reading."""
    root = _retained_fixture(tmp_path)
    throughput = root / generator.EVIDENCE_RELATIVE / "throughput.json"
    replacement = throughput.with_name("replacement.json")
    _ = replacement.write_bytes(throughput.read_bytes())
    real_lstat = Path.lstat
    observed = 0

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == throughput:
            observed += 1
            if observed == SOURCE_RECHECK:
                _ = replacement.replace(throughput)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(
        generator.ProfileManifestError, match="changed during read"
    ):
        _ = profile_manifest(root)
    assert observed == SOURCE_RECHECK


def test_retained_generator_rejects_in_place_source_edit_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even same-size, same-inode mutation invalidates retained evidence."""
    root = _retained_fixture(tmp_path)
    throughput = root / generator.EVIDENCE_RELATIVE / "throughput.json"
    real_lstat = Path.lstat
    observed = 0

    def edit_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == throughput:
            observed += 1
            if observed == SOURCE_RECHECK:
                with throughput.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", edit_at_recheck)
    with pytest.raises(
        generator.ProfileManifestError, match="changed during read"
    ):
        _ = profile_manifest(root)
    assert observed == SOURCE_RECHECK
