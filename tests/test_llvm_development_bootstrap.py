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

from contextlib import suppress
from dataclasses import replace
import hashlib
import os
import shutil
from pathlib import Path
import subprocess as sp
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Self
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
FOREIGN_CONTENT_BYTES = b"foreign content"
STAGE_LINKED_PARENT = "linked-parent"
STAGE_LINKED_LEAF = "linked-stage"
STAGE_NONDIRECTORY_PARENT = "nondirectory-parent"
TARGET_DANGLING_LEAF = "dangling-leaf"
MARKER_BINARY_MODE = "rb"


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


def _external_sentinel(tmp_path: Path) -> tuple[Path, Path]:
    """Create a foreign directory with immutable reference content.

    Returns:
        The foreign directory and sentinel path.

    """
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(FOREIGN_CONTENT_BYTES)
    return external, sentinel


def _redirect_development_staging(
    root: Path, external: Path, stage_kind: str
) -> None:
    """Prepare one inadmissible staging directory or ancestor."""
    temp_root = root / ".temp"
    if stage_kind == STAGE_NONDIRECTORY_PARENT:
        _ = temp_root.write_bytes(b"not a directory")
        return
    if stage_kind == STAGE_LINKED_PARENT:
        alias = temp_root
    else:
        temp_root.mkdir()
        alias = temp_root / f"llvm-development-provision-{LINUX_PLATFORM}"
    try:
        _ = alias.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")


def _redirect_development_destination(
    root: Path,
    identity: tidy_toolchain.ToolchainIdentity,
    external: Path,
    *,
    target_kind: str,
) -> None:
    """Prepare an inadmissible toolkit destination or ancestor."""
    destination_parent = root / ".dependencies"
    if target_kind == STAGE_NONDIRECTORY_PARENT:
        _ = destination_parent.write_bytes(b"not a directory")
        return
    if target_kind == STAGE_LINKED_PARENT:
        alias = destination_parent
        target = external
    else:
        identity.development_root.parent.mkdir(parents=True)
        alias = identity.development_root
        target = external / "missing"
    try:
        _ = alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")


@pytest.mark.parametrize(
    "stage_kind",
    [STAGE_LINKED_PARENT, STAGE_LINKED_LEAF, STAGE_NONDIRECTORY_PARENT],
)
def test_development_provision_rejects_redirected_staging_before_download(
    tmp_path: Path, stage_kind: str
) -> None:
    """Staging must stay inside physical checkout directories."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    _redirect_development_staging(root, external, stage_kind)
    downloads: list[str] = []
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader(downloads),
            extractor=_extract_headers,
        )
    assert not downloads
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


@pytest.mark.parametrize(
    "target_kind",
    [STAGE_LINKED_PARENT, TARGET_DANGLING_LEAF, STAGE_NONDIRECTORY_PARENT],
)
def test_development_provision_rejects_redirected_destination_before_download(
    tmp_path: Path, target_kind: str
) -> None:
    """A foreign destination alias is not an admissible toolkit root."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    _redirect_development_destination(
        root, identity, external, target_kind=target_kind
    )
    downloads: list[str] = []
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="destination",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader(downloads),
            extractor=_extract_headers,
        )
    assert not downloads
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    if target_kind == TARGET_DANGLING_LEAF:
        assert identity.development_root.is_symlink()


def test_development_provision_rechecks_staging_after_download(
    tmp_path: Path,
) -> None:
    """A downloader must not redirect subsequent extraction or cleanup."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    stage_parent = root / ".temp"
    owned_parent = root / ".temp-owned"

    def swap_stage(url: str) -> bytes:
        del url
        _ = stage_parent.rename(owned_parent)
        try:
            _ = stage_parent.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
        return PACKAGE_BYTES

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=swap_stage,
            extractor=_extract_headers,
        )
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert owned_parent.is_dir()
    assert not identity.development_root.exists()


def test_development_provision_rechecks_destination_after_extraction(
    tmp_path: Path,
) -> None:
    """An extractor cannot redirect the final publication destination."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    destination_parent = root / ".dependencies"

    def swap_destination(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        try:
            _ = destination_parent.symlink_to(
                external, target_is_directory=True
            )
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="destination",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader([]),
            extractor=swap_destination,
        )
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert destination_parent.is_symlink()
    assert not identity.development_root.exists()


def test_development_provision_rejects_swapped_staged_root(
    tmp_path: Path,
) -> None:
    """Extractors cannot redirect the staged marker to a foreign directory."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    foreign_header = external / identity.required_development_files[0]
    foreign_header.parent.mkdir(parents=True)
    _ = foreign_header.write_bytes(HEADER_BYTES)

    def swap_staged_root(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        owned = destination.with_name("development-owned")
        _ = destination.rename(owned)
        try:
            _ = destination.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader([]),
            extractor=swap_staged_root,
        )
    assert set(external.rglob("*")) == {
        sentinel,
        external / "include",
        external / "include/clang",
        external / "include/clang/AST",
        foreign_header,
    }
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


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


def _inject_marker_stream_fault(
    monkeypatch: pytest.MonkeyPatch,
    marker: Path,
    fault_type: type[Exception],
) -> list[int]:
    """Inject a wrapper fault and record raw descriptors opened for the marker.

    Returns:
        Descriptors that readiness must close on rejection.

    """
    native_open = os.open
    native_fdopen = os.fdopen
    opened: list[int] = []
    fault = fault_type("injected LLVM development marker stream failure")

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == marker:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in opened and mode == MARKER_BINARY_MODE:
            raise fault
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    return opened


@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, TypeError, RuntimeError]
)
def test_development_marker_fdopen_fault_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A host stream-wrapper failure must not leak marker readiness or an fd."""
    identity = _provisioned_identity(tmp_path)
    marker = (
        identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    opened = _inject_marker_stream_fault(monkeypatch, marker, fault_type)
    try:
        assert not llvm_development_validation.development_root_matches(
            identity
        )
        assert len(opened) == 1
        with pytest.raises(
            OSError, match=r"Bad file descriptor|Invalid handle"
        ):
            _ = os.fstat(opened[0])
    finally:
        for descriptor in opened:
            with suppress(OSError):
                os.close(descriptor)


@pytest.mark.parametrize(
    "failure",
    [
        (operation, fault_type)
        for operation in ("is_symlink", "is_junction", "lstat")
        for fault_type in (TypeError, RuntimeError)
    ],
)
@pytest.mark.parametrize("target_kind", ["marker", "header"])
def test_development_readiness_rejects_host_status_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    failure: tuple[str, type[Exception]],
    target_kind: str,
) -> None:
    """Uncertain host status must not authorize LLVM development readiness."""
    identity = _provisioned_identity(tmp_path)
    operation, fault_type = failure
    target = {
        "marker": (
            identity.development_root
            / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
        ),
        "header": (
            identity.development_root / identity.required_development_files[0]
        ),
    }[target_kind]
    original = {
        "is_symlink": Path.is_symlink,
        "is_junction": Path.is_junction,
        "lstat": Path.lstat,
    }[operation]
    fault = fault_type("injected LLVM development status failure")

    def fail_status(path: Path) -> object:
        if path == target:
            raise fault
        return original(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, fail_status)
        assert not llvm_development_validation.development_root_matches(
            identity
        )


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


@pytest.mark.parametrize("mutation", ["executable", "argument", "append"])
def test_rpm_command_rejects_mutated_subprocess_argv(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """A launcher cannot alter both the borrowed command and its own receipt."""
    expected = ["cpio", "-it", "--quiet"]

    def mutate_run(argv: list[str], **_kwargs: object) -> sp.CompletedProcess[bytes]:
        if mutation == "executable":
            argv[0] = "foreign-cpio"
        elif mutation == "argument":
            argv[1] = "-idm"
        else:
            argv.append("--forged")
        return sp.CompletedProcess(argv, 0, b"./usr/include/ok.h\n", b"")

    monkeypatch.setattr(llvm_development_validation.sp, "run", mutate_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="process receipt",
    ):
        llvm_development_validation._command_bytes(expected)
    assert expected == ["cpio", "-it", "--quiet"]


@pytest.mark.parametrize(
    "malformed",
    [
        "foreign",
        "bool_status",
        "float_status",
        "foreign_argv",
        "wrong_argv",
        "foreign_arg",
        "text_stdout",
        "text_stderr",
        "bytearray_stdout",
    ],
)
def test_rpm_command_rejects_non_native_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    malformed: str,
) -> None:
    """Only matching native binary CPIO tool receipts can prove a command."""
    expected = ["cpio", "-it", "--quiet"]

    def forged_run(argv: list[str], **_kwargs: object) -> object:
        if malformed == "foreign":
            return object()
        returned_argv: object = argv.copy()
        status: object = 0
        stdout: object = b"verified"
        stderr: object = b""
        if malformed == "bool_status":
            status = False
        elif malformed == "float_status":
            status = 0.0
        elif malformed == "foreign_argv":
            returned_argv = tuple(argv)
        elif malformed == "wrong_argv":
            returned_argv = ["cpio", "-idm", "--quiet"]
        elif malformed == "foreign_arg":

            class ForeignString(str):
                pass

            returned_argv = ["cpio", "-it", ForeignString("--quiet")]
        elif malformed == "text_stdout":
            stdout = "verified"
        elif malformed == "text_stderr":
            stderr = ""
        elif malformed == "bytearray_stdout":
            stdout = bytearray(b"verified")
        return sp.CompletedProcess(returned_argv, cast("int", status), stdout, stderr)

    monkeypatch.setattr(llvm_development_validation.sp, "run", forged_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="process receipt",
    ):
        llvm_development_validation._command_bytes(expected)


def test_rpm_command_accepts_native_binary_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An actual RPM2CPIO/CPIO invocation still returns its binary payload."""
    expected = ["cpio", "-it", "--quiet"]

    def native_run(argv: list[str], **_kwargs: object) -> sp.CompletedProcess[bytes]:
        return sp.CompletedProcess(argv, 0, b"verified", b"")

    monkeypatch.setattr(llvm_development_validation.sp, "run", native_run)
    assert llvm_development_validation._command_bytes(expected) == b"verified"


def test_rpm_command_rejects_native_tool_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real CPIO diagnostic remains available on nonzero process exit."""

    def failing_run(argv: list[str], **_kwargs: object) -> sp.CompletedProcess[bytes]:
        return sp.CompletedProcess(argv, 2, b"", b"corrupt archive\n")

    monkeypatch.setattr(llvm_development_validation.sp, "run", failing_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="LLVM RPM tool failed: cpio: corrupt archive",
    ):
        llvm_development_validation._command_bytes(["cpio", "-it"])


@pytest.mark.parametrize("failure", [OSError, ValueError, TypeError, RuntimeError])
def test_rpm_command_wraps_host_launch_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """Host subprocess launch failures stay within the typed provision boundary."""
    fault = failure("host refused launch")

    def failing_run(_argv: list[str], **_kwargs: object) -> object:
        raise fault

    monkeypatch.setattr(llvm_development_validation.sp, "run", failing_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="failed to execute LLVM RPM tool",
    ) as observed:
        llvm_development_validation._command_bytes(["rpm2cpio", "file.rpm"])
    assert observed.value.__cause__ is fault


@pytest.mark.parametrize("failure", ["timeout", "foreign_oserror"])
def test_rpm_command_does_not_format_foreign_host_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Do not execute custom exception __str__ while rejecting RPM tool faults."""

    class ForeignOSError(OSError):
        def __str__(self) -> str:
            raise AssertionError("untrusted RPM launch failure formatted")

    fault = (
        sp.TimeoutExpired(cmd=["rpm2cpio"], timeout=1)
        if failure == "timeout"
        else ForeignOSError("host refused launch")
    )

    def failing_run(_argv: list[str], **_kwargs: object) -> object:
        raise fault

    monkeypatch.setattr(llvm_development_validation.sp, "run", failing_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match=type(fault).__name__,
    ) as observed:
        llvm_development_validation._command_bytes(["rpm2cpio", "file.rpm"])
    assert observed.value.__cause__ is fault


def test_rpm_command_rejects_foreign_completed_process_subclass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An equality-compatible custom completion class is not native evidence."""

    class ForeignCompletion(sp.CompletedProcess[bytes]):
        pass

    def forged_run(argv: list[str], **_kwargs: object) -> object:
        return ForeignCompletion(argv, 0, b"verified", b"")

    monkeypatch.setattr(llvm_development_validation.sp, "run", forged_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="process receipt",
    ):
        llvm_development_validation._command_bytes(["cpio", "-it"])


@pytest.mark.parametrize("target_kind", ["marker", "header", "parent"])
@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("foreign_result", [None, 0, "", 0.0])
def test_development_readiness_rejects_foreign_path_decisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
    operation: str,
    foreign_result: object,
) -> None:
    """Nonboolean path-status hooks cannot authorize a reusable dev root."""
    identity = _provisioned_identity(tmp_path)
    header = identity.development_root / identity.required_development_files[0]
    target = {
        "marker": identity.development_root
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER,
        "header": header,
        "parent": header.parent,
    }[target_kind]
    original = getattr(Path, operation)

    def foreign_decision(path: Path) -> object:
        return foreign_result if path == target else original(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, foreign_decision)
        assert not llvm_development_validation.development_root_matches(identity)


@pytest.mark.parametrize("target_kind", ["marker", "header"])
def test_development_readiness_rejects_foreign_lstat_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """A duck-typed stat result cannot certify a marker or required header."""
    identity = _provisioned_identity(tmp_path)
    target = (
        identity.development_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
        if target_kind == "marker"
        else identity.development_root / identity.required_development_files[0]
    )
    native_lstat = Path.lstat

    def foreign_lstat(path: Path) -> object:
        stat = native_lstat(path)
        if path != target:
            return stat
        return SimpleNamespace(
            st_mode=stat.st_mode,
            st_dev=stat.st_dev,
            st_ino=stat.st_ino,
            st_size=stat.st_size,
            st_mtime_ns=stat.st_mtime_ns,
            st_ctime_ns=stat.st_ctime_ns,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", foreign_lstat)
        assert not llvm_development_validation.development_root_matches(identity)


@pytest.mark.parametrize("extra_mode_bits", [1 << 32, 1 << 40])
def test_development_readiness_rejects_out_of_range_native_stat_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_mode_bits: int,
) -> None:
    """A native stat object with a forged nonportable mode is not evidence."""
    identity = _provisioned_identity(tmp_path)
    header = identity.development_root / identity.required_development_files[0]
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> os.stat_result:
        observed = native_lstat(path)
        if path != header:
            return observed
        raw = list(observed)
        raw[0] = observed.st_mode | extra_mode_bits
        return os.stat_result(raw)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        assert not llvm_development_validation.development_root_matches(identity)


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_development_staging_rejects_foreign_path_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
) -> None:
    """No foreign false-like host result can certify a physical directory."""
    native = getattr(Path, operation)

    def foreign_status(path: Path) -> object:
        return foreign if path == tmp_path else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ):
            llvm_development_validation._require_physical_directories(
                tmp_path, "staging"
            )


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_development_destination_rejects_foreign_leaf_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
) -> None:
    """An absent target needs native no-redirect evidence at its leaf."""
    target = tmp_path / "unpublished"
    native = getattr(Path, operation)

    def foreign_status(path: Path) -> object:
        return foreign if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ):
            llvm_development_validation._require_development_destination(target)


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("failure", [OSError, ValueError, TypeError, RuntimeError])
def test_development_preflight_wraps_native_host_status_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    failure: type[Exception],
) -> None:
    """A failed host path probe cannot escape the typed provision boundary."""
    fault = failure("host status unavailable")
    native = getattr(Path, operation)

    def failed_status(path: Path) -> bool:
        if path == tmp_path:
            raise fault
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, failed_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ) as observed:
            llvm_development_validation._require_physical_directories(
                tmp_path, "staging"
            )
    assert observed.value.__cause__ is fault


def test_development_staging_rejects_foreign_existence_before_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign false-like staging status cannot authorize mkdir."""
    target = tmp_path / "staging"
    native = Path.exists

    def foreign_exists(path: Path) -> object:
        return None if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "exists", foreign_exists)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ):
            llvm_development_validation._prepare_staging(target)
    assert not target.exists()


@pytest.mark.parametrize("target_kind", ["destination", "staging"])
def test_development_provision_rejects_foreign_existence_before_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """A false-like host existence receipt cannot authorize publication."""
    identity = _identity(tmp_path)
    target = (
        identity.development_root
        if target_kind == "destination"
        else tmp_path / ".temp" / f"llvm-development-provision-{LINUX_PLATFORM}"
    )
    original = Path.exists

    def foreign_exists(path: Path) -> object:
        return None if path == target else original(path)

    calls: list[str] = []
    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "exists", foreign_exists)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="invalid status",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader(calls),
                extractor=_extract_headers,
            )
    assert not calls
    assert not identity.development_root.exists()


def test_development_preflight_does_not_format_foreign_host_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path-status host errors preserve cause without formatting subclasses."""

    class ForeignHostError(OSError):
        def __str__(self) -> str:
            raise AssertionError("foreign path status exception was formatted")

    fault = ForeignHostError("foreign status")
    native = Path.is_junction

    def foreign_status(path: Path) -> bool:
        if path == tmp_path:
            raise fault
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_junction", foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="ForeignHostError",
        ) as observed:
            llvm_development_validation._require_physical_directories(
                tmp_path, "staging"
            )
    assert observed.value.__cause__ is fault


@pytest.mark.parametrize("alias_kind", ["symlink", "hardlink"])
def test_development_marker_staging_rejects_foreign_file_alias(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """An extractor must not redirect the verified marker write outside staging."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    original = sentinel.read_bytes()

    def alias_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        marker = destination / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
        try:
            if alias_kind == "symlink":
                _ = marker.symlink_to(sentinel)
            else:
                os.link(sentinel, marker)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"file aliases unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader([]),
            extractor=alias_extractor,
        )
    assert sentinel.read_bytes() == original
    assert list(external.iterdir()) == [sentinel]
    assert not identity.development_root.exists()


def test_development_staging_write_requires_unused_leaf(tmp_path: Path) -> None:
    """An existing ordinary staging leaf is not safe to overwrite."""
    target = tmp_path / "previous-marker.json"
    original = b"keep old staging bytes"
    _ = target.write_bytes(original)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        llvm_development_validation._write_verified_staging_bytes(target, b"new")
    assert target.read_bytes() == original


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction", "exists"])
@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_development_staging_file_rejects_non_native_leaf_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
) -> None:
    """A foreign false-like leaf decision never permits a staging write."""
    target = tmp_path / "payload.rpm"
    native = getattr(Path, operation)

    def foreign_status(path: Path) -> object:
        return foreign if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="invalid status",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                target, PACKAGE_BYTES
            )
    assert not target.exists()


@pytest.mark.parametrize("alias_kind", ["leaf", "parent"])
def test_development_provision_rejects_linked_required_header(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """A linked extracted header cannot become a published development kit."""
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    foreign_header = external / "AST.h"
    _ = foreign_header.write_bytes(HEADER_BYTES)

    def linked_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        header = destination / identity.required_development_files[0]
        if alias_kind == "leaf":
            header.unlink()
            alias = header
            target = foreign_header
        else:
            parent = header.parent
            shutil.rmtree(parent)
            alias = parent
            target = external
        try:
            _ = alias.symlink_to(target, target_is_directory=(alias_kind == "parent"))
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"file aliases unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="missing",
    ):
        _ = llvm_development_validation.provision_development_identity(
            root,
            identity,
            downloader=_downloader([]),
            extractor=linked_extractor,
        )
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert foreign_header.read_bytes() == HEADER_BYTES
    assert not identity.development_root.exists()


def test_development_provision_rejects_forged_missing_header_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A false file-existence witness must not complete a headerless kit."""
    identity = _identity(tmp_path)
    staged_header = (
        tmp_path
        / ".temp"
        / f"llvm-development-provision-{LINUX_PLATFORM}"
        / "development"
        / identity.required_development_files[0]
    )
    native = Path.is_file

    def forged_file_status(path: Path) -> object:
        return True if path == staged_header else native(path)

    def missing_header_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        del destination, staging
        llvm_development_validation.verify_development_asset(data, asset)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_file", forged_file_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="missing",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=missing_header_extractor,
            )
    assert not identity.development_root.exists()


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_rpm_include_tree_rejects_foreign_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
) -> None:
    """CPIO include members require native link-status evidence."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    header = include_root / "header.h"
    _ = header.write_bytes(HEADER_BYTES)
    native = getattr(Path, operation)

    def foreign_status(path: Path) -> object:
        return foreign if path == header else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ):
            llvm_development_validation._reject_include_symlinks(include_root)


def test_rpm_include_tree_rejects_linked_root(tmp_path: Path) -> None:
    """CPIO cannot redirect its /usr/include root to a foreign tree."""
    external = tmp_path / "outside"
    external.mkdir()
    _ = (external / "header.h").write_bytes(HEADER_BYTES)
    include_parent = tmp_path / "package/usr"
    include_parent.mkdir(parents=True)
    linked_root = include_parent / "include"
    try:
        _ = linked_root.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory aliases unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging",
    ):
        llvm_development_validation._reject_include_symlinks(linked_root)
    assert (external / "header.h").read_bytes() == HEADER_BYTES


def test_rpm_include_tree_rejects_junction_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A junction report is as disqualifying as a symlink report."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    header = include_root / "header.h"
    _ = header.write_bytes(HEADER_BYTES)
    native = Path.is_junction

    def forged_junction(path: Path) -> bool:
        return True if path == header else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_junction", forged_junction)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="symlink|redirect",
        ):
            llvm_development_validation._reject_include_symlinks(include_root)


@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_rpm_include_tree_rejects_foreign_root_directory_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """A foreign false-like directory witness is not CPIO root evidence."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    native = Path.is_dir

    def foreign_status(path: Path) -> object:
        return foreign if path == include_root else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_dir", foreign_status)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="status",
        ):
            llvm_development_validation._reject_include_symlinks(include_root)


def test_rpm_include_tree_accepts_physical_regular_members(tmp_path: Path) -> None:
    """Native CPIO include roots and regular members still pass inspection."""
    include_root = tmp_path / "usr/include"
    header = include_root / "clang/AST/AST.h"
    header.parent.mkdir(parents=True)
    _ = header.write_bytes(HEADER_BYTES)
    llvm_development_validation._reject_include_symlinks(include_root)


@pytest.mark.parametrize("receipt", [None, "rpm", bytearray(PACKAGE_BYTES)])
def test_llvm_development_download_rejects_foreign_binary_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only exact native bytes can become an LLVM RPM package candidate."""

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, _kind: object, _error: object, _trace: object) -> bool:
            return False

        def read(self) -> object:
            return receipt

    monkeypatch.setattr(
        llvm_development_validation.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="download receipt",
    ):
        llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm"
        )


@pytest.mark.parametrize("failure", [OSError, ValueError, TypeError, RuntimeError])
def test_llvm_development_download_preserves_native_host_error(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """Network and stream failures do not escape the typed provision boundary."""
    fault = failure("injected URL host fault")

    def fail_download(*_args: object, **_kwargs: object) -> object:
        raise fault

    monkeypatch.setattr(
        llvm_development_validation.urllib.request, "urlopen", fail_download
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="cannot download pinned LLVM development package",
    ) as observed:
        llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm"
        )
    assert observed.value.__cause__ is fault


def test_llvm_development_download_does_not_format_foreign_host_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign urllib exception text must not execute arbitrary formatters."""

    class ForeignHostError(OSError):
        def __str__(self) -> str:
            raise AssertionError("untrusted download exception was formatted")

    fault = ForeignHostError("untrusted")

    def fail_download(*_args: object, **_kwargs: object) -> object:
        raise fault

    monkeypatch.setattr(
        llvm_development_validation.urllib.request, "urlopen", fail_download
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="ForeignHostError",
    ) as observed:
        llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm"
        )
    assert observed.value.__cause__ is fault


def test_llvm_development_download_accepts_native_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary byte response preserves its exact payload for SHA admission."""

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, _kind: object, _error: object, _trace: object) -> bool:
            return False

        def read(self) -> bytes:
            return PACKAGE_BYTES

    monkeypatch.setattr(
        llvm_development_validation.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    assert (
        llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm"
        )
        == PACKAGE_BYTES
    )
