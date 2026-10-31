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
#   - Linux LLVM development package provisioning regression evidence.
# - Must-Not:
#   - Contact Fedora or invoke host RPM tools during unit tests.
# - Allows:
#   - Inputs: synthetic package bytes and tracked Linux toolchain identity.
#   - Outputs: exact verification, containment, marker, and reuse assertions.
#   - Side effects: test-local files only.
# - Split-When:
#   - Another native development provider gains independent lifecycle policy.
# - Merge-When:
#   - Project bootstrap tests own this exact LLVM development lifecycle.
# - Summary:
#   - Prove exact, contained Linux LLVM development materialization.
# - Description:
#   - Exercises byte admission and atomic publication without network access.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Unverified or escaping RPM content fails before publication.
#

"""Linux LLVM development provisioning regression evidence."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts.bootstrap import llvm_development_validation

from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from collections.abc import Callable

LINUX_PLATFORM = "linux-x86_64"
PACKAGE_NAME = "clang-devel-22.1.8-4.fc44.x86_64.rpm"
HEADER_BYTES = b"reviewed-header"
PACKAGE_BYTES = b"synthetic exact rpm bytes"


def _asset() -> tidy_toolchain.DevelopmentAsset:
    return tidy_toolchain.DevelopmentAsset(
        name=PACKAGE_NAME,
        sha256=hashlib.sha256(PACKAGE_BYTES).hexdigest(),
        size_bytes=len(PACKAGE_BYTES),
    )


def _identity(tmp_path: Path) -> tidy_toolchain.ToolchainIdentity:
    ordinary = tidy_toolchain.load_identity(
        root=tmp_path,
        platform_id=LINUX_PLATFORM,
    )
    asset = _asset()
    return replace(
        ordinary,
        asset_name=asset.name,
        asset_sha256=asset.sha256,
        asset_size_bytes=asset.size_bytes,
        development_assets=(asset,),
        required_development_files=(Path("include/clang/AST/AST.h"),),
    )


def test_package_verification_rejects_size_and_sha_drift() -> None:
    """RPM bytes must satisfy both exact tracked size and SHA-256 identity."""
    asset = _asset()
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="size mismatch",
    ):
        llvm_development_validation.verify_development_asset(
            PACKAGE_BYTES + b"x",
            asset,
        )
    forged = replace(asset, sha256="0" * 64)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="SHA-256 mismatch",
    ):
        llvm_development_validation.verify_development_asset(
            PACKAGE_BYTES,
            forged,
        )


def test_rpm_member_validation_rejects_parent_and_absolute_paths() -> None:
    """CPIO member names cannot escape the package extraction directory."""
    for member in ("./usr/include/../../escape", "/usr/include/escape"):
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="escapes package root",
        ):
            llvm_development_validation.validate_rpm_members((member,))


def _extract_headers(
    data: bytes,
    asset: tidy_toolchain.DevelopmentAsset,
    destination: Path,
    *,
    staging: Path,
) -> None:
    del staging
    llvm_development_validation.verify_development_asset(data, asset)
    header = destination / "include/clang/AST/AST.h"
    header.parent.mkdir(parents=True, exist_ok=True)
    _ = header.write_bytes(HEADER_BYTES)


def _downloader(calls: list[str]) -> Callable[[str], bytes]:
    def download(url: str) -> bytes:
        calls.append(url)
        return PACKAGE_BYTES

    return download


def test_provision_is_marker_bound_and_idempotent(tmp_path: Path) -> None:
    """An exact completed development root never redownloads package bytes."""
    identity = _identity(tmp_path)
    calls: list[str] = []

    first = llvm_development_validation.provision_development_identity(
        tmp_path,
        identity,
        downloader=_downloader(calls),
        extractor=_extract_headers,
    )
    second = llvm_development_validation.provision_development_identity(
        tmp_path,
        identity,
        downloader=_downloader(calls),
        extractor=_extract_headers,
    )

    assert first == second == identity.development_root
    assert (first / "include/clang/AST/AST.h").read_bytes() == HEADER_BYTES
    assert len(calls) == 1
    assert calls[0].endswith(f"/c/{PACKAGE_NAME}")
    marker = first / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    assert marker.is_file()
    staging = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    assert not staging.exists()


def _provisioned_identity(tmp_path: Path) -> tidy_toolchain.ToolchainIdentity:
    identity = _identity(tmp_path)
    _ = llvm_development_validation.provision_development_identity(
        tmp_path,
        identity,
        downloader=_downloader([]),
        extractor=_extract_headers,
    )
    return identity


def test_development_marker_rejects_linked_leaf(tmp_path: Path) -> None:
    """An exact marker reached via symlink cannot authorize a package root."""
    identity = _provisioned_identity(tmp_path)
    marker = (
        identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    relocated = marker.with_name("real-marker.json")
    _ = marker.replace(relocated)
    try:
        _ = marker.symlink_to(relocated)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="without the exact provision marker",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=_extract_headers,
        )


def test_development_marker_rejects_development_root_alias(
    tmp_path: Path,
) -> None:
    """A linked development root cannot replace published physical state."""
    identity = _provisioned_identity(tmp_path)
    original = identity.development_root
    relocated = original.with_name("relocated-development")
    _ = original.replace(relocated)
    try:
        _ = original.symlink_to(relocated, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_required_header_symlink(
    tmp_path: Path,
) -> None:
    """Ready evidence requires real extracted headers, not aliases."""
    identity = _provisioned_identity(tmp_path)
    header = identity.development_root / "include/clang/AST/AST.h"
    relocated = header.with_suffix(".physical")
    _ = header.replace(relocated)
    try:
        _ = header.symlink_to(relocated)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_required_header_parent_alias(
    tmp_path: Path,
) -> None:
    """An alias in required include ancestry cannot satisfy readiness."""
    identity = _provisioned_identity(tmp_path)
    directory = identity.development_root / "include/clang/AST"
    relocated = directory.with_name("AST-physical")
    _ = directory.replace(relocated)
    try:
        _ = directory.symlink_to(relocated, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_same_byte_inode_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing an admitted marker before open invalidates readiness."""
    identity = _provisioned_identity(tmp_path)
    marker = (
        identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    replacement = marker.with_name("replacement-marker.json")
    _ = replacement.write_bytes(marker.read_bytes())
    real_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == marker:
            _ = replacement.replace(marker)
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_oversized_marker(tmp_path: Path) -> None:
    """Unbounded local marker content must not be read into memory."""
    identity = _provisioned_identity(tmp_path)
    marker = (
        identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    with marker.open("wb") as stream:
        _ = stream.truncate(2_000_000)
    assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_fifo_without_blocking(
    tmp_path: Path,
) -> None:
    """A pipe substituted for the marker never waits for an external writer."""
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    identity = _provisioned_identity(tmp_path)
    marker = (
        identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    marker.unlink()
    mkfifo(marker)
    assert not llvm_development_validation.development_root_matches(identity)


_BAD_WRITE_RESULTS = ("short", "overlong", "boolean", "missing")


def _bad_write_count(kind: str, expected: int) -> int:
    """Simulate a host reporting an invalid byte count.

    Returns:
        A short, overlong, boolean, or missing write acknowledgement.

    """
    results: dict[str, object] = {
        "short": expected - 1,
        "overlong": expected + 1,
        "boolean": True,
        "missing": None,
    }
    return cast("int", results[kind])


@pytest.mark.parametrize("invalid_count", list(_BAD_WRITE_RESULTS))
def test_provision_rejects_incomplete_marker_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """No development tree publishes when marker write reports bad count."""
    identity = _identity(tmp_path)
    real_write = Path.write_bytes

    def wrong_write(path: Path, data: bytes) -> int:
        if path.name == llvm_development_validation.LLVM_DEVELOPMENT_MARKER:
            _ = real_write(path, data[:-1])
            return _bad_write_count(invalid_count, len(data))
        return real_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", wrong_write)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="write count",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=_extract_headers,
        )
    assert not identity.development_root.exists()
    staging = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    assert not staging.exists()


@pytest.mark.parametrize("invalid_count", list(_BAD_WRITE_RESULTS))
def test_rpm_extraction_rejects_incomplete_staging_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """Never execute a staged RPM with an invalid host write count."""
    identity = _identity(tmp_path)
    real_write = Path.write_bytes

    def wrong_write(path: Path, data: bytes) -> int:
        if path.name == PACKAGE_NAME:
            _ = real_write(path, data[:-1])
            return _bad_write_count(invalid_count, len(data))
        return real_write(path, data)

    def unexpected_cpio(path: Path) -> bytes:
        pytest.fail(f"unverified RPM reached CPIO: {path.name}")

    monkeypatch.setattr(Path, "write_bytes", wrong_write)
    monkeypatch.setattr(
        llvm_development_validation, "_cpio_payload", unexpected_cpio
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="write count",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path, identity, downloader=_downloader([])
        )
    assert not identity.development_root.exists()
