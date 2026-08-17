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
from pathlib import Path
from typing import TYPE_CHECKING

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
        required_development_files=(
            Path("include/clang/AST/AST.h"),
        ),
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
