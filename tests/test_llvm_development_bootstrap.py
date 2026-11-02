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

import hashlib
import os
import shutil
import subprocess as sp
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, Self, cast, override

import pytest
from scripts.bootstrap import llvm_development_validation

from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

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


@pytest.mark.parametrize("name", [r"nested\clang-devel.rpm", r"nested\..\clang-devel.rpm"])
def test_development_rpm_filename_rejects_windows_path_components(
    tmp_path: Path,
    name: str,
) -> None:
    """Linux asset URLs still require one portable basename, not backslash paths."""
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="one RPM filename",
    ):
        _ = llvm_development_validation._asset_url(
            _identity(tmp_path), replace(_asset(), name=name)
        )


@pytest.mark.parametrize(
    "name",
    [
        "clang?mirror.rpm",
        "clang#fragment.rpm",
        "clang%2Fsegment.rpm",
        "clang;parameter.rpm",
        "clang whitespace.rpm",
        "clang\x00null.rpm",
        "clang\u200bhidden.rpm",
    ],
)
def test_development_rpm_filename_rejects_url_control_characters(
    tmp_path: Path,
    name: str,
) -> None:
    """Pinned asset names cannot change the HTTP URL beyond a path segment."""
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="one RPM filename",
    ):
        _ = llvm_development_validation._asset_url(
            _identity(tmp_path), replace(_asset(), name=name)
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


def _is_staged_file_open(
    candidate: object, target: Path, dir_fd: int | None
) -> bool:
    """Match direct and descriptor-relative writes to one staging leaf."""
    return candidate == target or (
        os.name == "posix" and candidate == target.name and dir_fd is not None
    )


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


def test_development_provision_rejects_unlisted_staged_symlink(
    tmp_path: Path,
) -> None:
    """An extra symlink cannot enter the committed development include tree."""
    identity = _identity(tmp_path)
    outside = tmp_path / "external-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)

    def linked_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        try:
            _ = (destination / "include/extra.h").symlink_to(outside)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"file aliases unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="symlink|physical member",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=linked_extractor,
        )
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


def test_development_provision_rejects_unlisted_staged_hardlink(
    tmp_path: Path,
) -> None:
    """An extra staged header may not share an external writable inode."""
    identity = _identity(tmp_path)
    outside = tmp_path / "outside-extra-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)

    def hardlinked_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        try:
            os.link(outside, destination / "include/extra.h")
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hardlinks unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="hardlink|physical member",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path, identity, downloader=_downloader([]), extractor=hardlinked_extractor
        )
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


def test_development_rejects_header_hardlinked_after_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late external header alias must not cross the publication boundary."""
    identity = _identity(tmp_path)
    outside = tmp_path / "external-staged-header.h"
    marker = llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    native_writer = llvm_development_validation._write_verified_staging_bytes
    linked = False

    def link_after_marker(path: Path, content: bytes) -> None:
        nonlocal linked
        native_writer(path, content)
        if path.name == marker:
            try:
                os.link(path.parent / "include/clang/AST/AST.h", outside)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"hardlinks unavailable: {error}")
            linked = True

    monkeypatch.setattr(
        llvm_development_validation, "_write_verified_staging_bytes", link_after_marker
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="hardlink",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path, identity, downloader=_downloader([]), extractor=_extract_headers
        )
    assert linked
    assert outside.read_bytes() == HEADER_BYTES
    assert not identity.development_root.exists()


def test_rpm_copy_rejects_header_swapped_to_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Copy-time link swaps must not import an untrusted external header."""
    identity = _identity(tmp_path)
    outside = tmp_path / "external-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    native_copytree = shutil.copytree
    swapped = False

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
    ) -> bytes:
        del stdin
        if arguments[0] == "cpio" and cwd is not None:
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
        return b""

    def swapped_copytree(
        src: Path | os.DirEntry[str],
        dst: Path | os.DirEntry[str],
        *args: object,
        **kwargs: object,
    ) -> Path:
        nonlocal swapped
        if not swapped and isinstance(src, Path) and src.name == "include":
            header = src / "clang/AST/AST.h"
            header.unlink()
            try:
                _ = header.symlink_to(outside)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"file aliases unavailable: {error}")
            swapped = True
        dynamic_copytree = cast("Callable[..., Path]", native_copytree)
        return dynamic_copytree(src, dst, *args, **kwargs)

    def synthetic_payload(_rpm: Path) -> bytes:
        return b"cpio"

    def synthetic_members(_data: bytes) -> tuple[str, ...]:
        return ("./usr/include/clang/AST/AST.h",)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", synthetic_payload
        )
        isolated.setattr(
            llvm_development_validation, "_cpio_members", synthetic_members
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        isolated.setattr(shutil, "copytree", swapped_copytree)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="missing|symlink|physical member",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert swapped
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


@pytest.mark.parametrize("via_provision", [False, True])
@pytest.mark.parametrize("swap_phase", ["after-copy", "tool-fault"])
def test_rpm_cleanup_preserves_swapped_foreign_package_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    via_provision: bool,
    swap_phase: str,
) -> None:
    """Direct and outer cleanup must preserve a substituted package directory."""
    if via_provision:
        staging = (
            tmp_path / ".temp/llvm-development-provision-linux-x86_64/packages"
        )
        destination = _identity(tmp_path).development_root
    else:
        staging = tmp_path / "packages"
        staging.mkdir()
        destination = tmp_path / "development"
        destination.mkdir()
    package_stage = staging / PACKAGE_NAME.removesuffix(".rpm")
    preserved = tmp_path / "preserved-package"
    sentinel = package_stage / "foreign-sentinel"
    native_copytree = shutil.copytree

    def swap_package() -> None:
        package_stage.rename(preserved)
        package_stage.mkdir()
        _ = sentinel.write_bytes(FOREIGN_CONTENT_BYTES)

    def synthetic_payload(_rpm: Path) -> bytes:
        if swap_phase == "tool-fault":
            swap_package()
            raise OSError("synthetic RPM tool fault after stage swap")
        return b"cpio"

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
    ) -> bytes:
        del stdin
        if arguments[0] == "cpio" and cwd is not None:
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
        return b""

    def swapped_copytree(
        src: Path | os.DirEntry[str],
        dst: Path | os.DirEntry[str],
        *args: object,
        **kwargs: object,
    ) -> Path:
        result = cast("Callable[..., Path]", native_copytree)(
            src, dst, *args, **kwargs
        )
        if (
            swap_phase == "after-copy"
            and isinstance(src, Path)
            and src.name == "include"
        ):
            swap_package()
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", synthetic_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _data: ("./usr/include/clang/AST/AST.h",),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        isolated.setattr(shutil, "copytree", swapped_copytree)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging child identity changed",
        ):
            if via_provision:
                _ = llvm_development_validation.provision_development_identity(
                    tmp_path, _identity(tmp_path), downloader=_downloader([])
                )
            else:
                llvm_development_validation._extract_rpm_headers(
                    PACKAGE_BYTES, _asset(), destination, staging=staging
                )
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert (preserved / PACKAGE_NAME).read_bytes() == PACKAGE_BYTES


@pytest.mark.parametrize("location", ["staging", "package"])
def test_development_parent_descriptor_close_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
) -> None:
    """A close failure on owned staging parents retains its host cause."""
    if os.name != "posix":
        pytest.skip("POSIX descriptor closure boundary")
    identity = _identity(tmp_path)
    native_mkdir = os.mkdir
    native_close = os.close
    target_name = (
        f"llvm-development-provision-{LINUX_PLATFORM}"
        if location == "staging"
        else PACKAGE_NAME.removesuffix(".rpm")
    )
    parent_descriptors: set[int] = set()
    fault = OSError("synthetic directory descriptor close fault")

    def track_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if path == target_name and dir_fd is not None:
            parent_descriptors.add(dir_fd)
        native_mkdir(path, mode, dir_fd=dir_fd)

    def fail_parent_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in parent_descriptors:
            parent_descriptors.remove(descriptor)
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", track_mkdir)
        isolated.setattr(os, "close", fail_parent_close)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="close failed",
        ) as caught:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert caught.value.__cause__ is fault
    assert not parent_descriptors
    assert not identity.development_root.exists()


def test_rpm_package_stage_creation_cannot_follow_late_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Package extraction cannot create a workspace in a swapped parent."""
    if os.name != "posix":
        pytest.skip("POSIX directory extraction boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    stage_root = root / f".temp/llvm-development-provision-{LINUX_PLATFORM}"
    package_parent = stage_root / "packages"
    parked = root / "parked-package-stage"
    native_mkdir = os.mkdir
    native_rename = os.rename
    swapped = False

    def swap_at_packages_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if path == package_parent or (path == "packages" and dir_fd is not None):
            native_rename(stage_root, parked)
            _ = stage_root.symlink_to(external, target_is_directory=True)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_at_packages_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging|package",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([])
            )
    assert swapped
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


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


def test_development_stage_creation_does_not_follow_late_parent_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stage parent swapped during mkdir cannot redirect the new directory."""
    if os.name != "posix":
        pytest.skip("POSIX directory staging boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    stage_parent = root / ".temp"
    stage_parent.mkdir()
    parked = root / "parked-stage-parent"
    stage = stage_parent / f"llvm-development-provision-{LINUX_PLATFORM}"
    native_mkdir = os.mkdir
    native_rename = os.rename
    swapped = False

    def swap_at_stage_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if path == stage or (path == stage.name and dir_fd is not None):
            native_rename(stage_parent, parked)
            _ = stage_parent.symlink_to(external, target_is_directory=True)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_at_stage_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert swapped
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


def test_development_staging_parent_creation_stays_inside_pinned_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An absent .temp is created relative to the original physical root."""
    if os.name != "posix":
        pytest.skip("POSIX directory staging boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    external, sentinel = _external_sentinel(tmp_path)
    parked = tmp_path / "parked-repository"
    native_mkdir = os.mkdir
    native_rename = os.rename
    swapped = False

    def swap_during_temp_creation(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if path == ".temp" and dir_fd is not None:
            native_rename(root, parked)
            _ = root.symlink_to(external, target_is_directory=True)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_temp_creation)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert swapped
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert (parked / ".temp").is_dir()


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


def test_development_publication_rejects_late_destination_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The final move cannot publish into a redirected parent after preflight."""
    if os.name != "posix":
        pytest.skip("POSIX directory publication boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    outside, sentinel = _external_sentinel(tmp_path)
    destination_parent = identity.development_root.parent
    parked = destination_parent.with_name("parked-development-parent")
    native_validate = llvm_development_validation._reject_include_symlinks
    checks = 0

    def swap_after_final_check(
        include_root: Path, *, require_single_link: bool = False
    ) -> None:
        nonlocal checks
        native_validate(include_root, require_single_link=require_single_link)
        if require_single_link:
            checks += 1
        if checks == 2:
            destination_parent.rename(parked)
            try:
                _ = destination_parent.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"directory links unavailable: {error}")

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_reject_include_symlinks",
            swap_after_final_check,
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination|parent",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert checks == 2
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not (outside / identity.development_root.name).exists()


def test_development_publication_uses_pinned_parent_during_final_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late parent alias cannot redirect a descriptor-relative final move."""
    if os.name != "posix":
        pytest.skip("POSIX directory publication boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    outside, sentinel = _external_sentinel(tmp_path)
    destination_parent = identity.development_root.parent
    parked = destination_parent.with_name("parked-development-parent")
    native_rename = os.rename
    attacked = False

    def swap_at_rename(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal attacked
        if (
            source == "development"
            and target == identity.development_root.name
            and src_dir_fd is not None
            and dst_dir_fd is not None
        ):
            native_rename(destination_parent, parked)
            _ = destination_parent.symlink_to(outside, target_is_directory=True)
            attacked = True
        native_rename(
            source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "rename", swap_at_rename)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination|parent",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert attacked
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES
    assert (parked / identity.development_root.name).is_dir()


def test_development_publication_rejects_foreign_destination_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign fd cannot authorize publication even if it is a directory."""
    if os.name != "posix":
        pytest.skip("POSIX directory publication boundary")
    root = tmp_path / "repository"
    root.mkdir()
    identity = _identity(root)
    outside, sentinel = _external_sentinel(tmp_path)
    native_open = os.open
    wrong_fds: list[int] = []

    def substitute_parent_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if (
            path == identity.development_root.parent.name
            and dir_fd is not None
        ):
            descriptor = native_open(outside, flags)
            wrong_fds.append(descriptor)
            return descriptor
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", substitute_parent_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination parent descriptor does not match",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert len(wrong_fds) == 1
    with pytest.raises(OSError, match="Bad file descriptor"):
        _ = os.fstat(wrong_fds[0])
    assert list(outside.iterdir()) == [sentinel]
    assert not identity.development_root.exists()


def test_development_publication_types_unprintable_rename_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostile host rename failure cannot execute error formatting hooks."""
    if os.name != "posix":
        pytest.skip("POSIX directory publication boundary")
    identity = _identity(tmp_path)
    native_rename = os.rename

    class ForeignOSError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("host rename error must not be formatted")

    fault = ForeignOSError("synthetic publication failure")

    def broken_rename(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        if source == "development" and src_dir_fd is not None:
            raise fault
        native_rename(
            source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "rename", broken_rename)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination publication failed",
        ) as caught:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert caught.value.__cause__ is fault
    assert not identity.development_root.exists()


@pytest.mark.parametrize("parent", ["staging", "destination"])
def test_development_publication_parent_close_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    parent: str,
) -> None:
    """A postmove parent close failure retains its host cause and typed error."""
    if os.name != "posix":
        pytest.skip("POSIX publication descriptor closure")
    identity = _identity(tmp_path)
    native_rename = os.rename
    native_close = os.close
    closing: set[int] = set()
    fault = OSError("synthetic publication parent close fault")

    def capture_final_rename(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        if source == "development" and target == identity.development_root.name:
            selected = src_dir_fd if parent == "staging" else dst_dir_fd
            assert selected is not None
            closing.add(selected)
        native_rename(
            source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd
        )

    def fault_final_parent_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in closing:
            closing.remove(descriptor)
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "rename", capture_final_rename)
        isolated.setattr(os, "close", fault_final_parent_close)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="parent descriptor close failed",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert observed.value.__cause__ is fault
    assert not closing
    assert (identity.development_root / "include/clang/AST/AST.h").read_bytes() == HEADER_BYTES


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


@pytest.mark.parametrize("location", ["staging", "package", "destination"])
def test_development_host_directory_creation_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
) -> None:
    """Host mkdir failures preserve their cause and never publish a kit."""
    identity = _identity(tmp_path)
    stage = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    paths = {
        "staging": stage,
        "package": stage / "packages" / PACKAGE_NAME.removesuffix(".rpm"),
        "destination": identity.development_root.parent,
    }
    fault_path = paths[location]
    native_mkdir = Path.mkdir
    native_os_mkdir = os.mkdir
    fault = OSError(f"host refused {location} directory")

    def faulty_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == fault_path:
            raise fault
        native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def faulty_native_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if dir_fd is not None and (
            (location == "staging" and path == stage.name)
            or (location == "package" and path == PACKAGE_NAME.removesuffix(".rpm"))
        ):
            raise fault
        native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", faulty_mkdir)
        if os.name == "posix":
            isolated.setattr(os, "mkdir", faulty_native_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="creation failed",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers if location == "destination" else None,
            )
    assert observed.value.__cause__ is fault
    assert not stage.exists()
    assert not identity.development_root.exists()


def test_development_child_stage_creation_fault_cleans_owned_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed child mkdir leaves no owned stage or untyped host error."""
    identity = _identity(tmp_path)
    staging = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    child = staging / "development"
    native_mkdir = Path.mkdir
    fault = OSError("cannot create development child")

    def fault_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == child:
            raise fault
        return native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", fault_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="development stage creation failed",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert observed.value.__cause__ is fault
    assert not staging.exists()
    assert not identity.development_root.exists()


def test_development_rejects_swapped_physical_child_stage(
    tmp_path: Path,
) -> None:
    """A foreign physical child cannot receive the marker or be removed."""
    identity = _identity(tmp_path)
    stage = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    child = stage / "development"
    parked = stage / "development-owned"
    outside = tmp_path / "foreign-development"
    header = outside / identity.required_development_files[0]
    header.parent.mkdir(parents=True)
    _ = header.write_bytes(HEADER_BYTES)
    _ = (outside / "external-sentinel.txt").write_bytes(FOREIGN_CONTENT_BYTES)
    inserted = False

    def swapped_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        nonlocal inserted
        _extract_headers(data, asset, destination, staging=staging)
        _ = destination.rename(parked)
        _ = outside.rename(destination)
        inserted = True

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging.*identity changed",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=swapped_extractor,
        )
    assert inserted
    assert not identity.development_root.exists()
    assert (child / "external-sentinel.txt").read_bytes() == FOREIGN_CONTENT_BYTES
    assert parked.is_dir()
    assert not (child / llvm_development_validation.LLVM_DEVELOPMENT_MARKER).exists()


@pytest.mark.parametrize("hide_exists", [False, True])
def test_development_rejects_late_occupied_final_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hide_exists: bool,
) -> None:
    """Publication must not replace an independently created empty directory."""
    identity = _identity(tmp_path)
    inserted = False

    def insert_destination(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        nonlocal inserted
        _extract_headers(data, asset, destination, staging=staging)
        identity.development_root.mkdir(parents=True)
        inserted = True

    native_exists = Path.exists

    def hidden_exists(path: Path) -> bool:
        return False if path == identity.development_root else native_exists(path)

    with monkeypatch.context() as isolated:
        if hide_exists:
            isolated.setattr(Path, "exists", hidden_exists)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination.*occupied",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=insert_destination,
            )
    assert inserted
    assert identity.development_root.is_dir()
    assert list(identity.development_root.iterdir()) == []
    assert not (
        tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    ).exists()


def test_development_cleanup_preserves_foreign_replacement_directory(
    tmp_path: Path,
) -> None:
    """Cleanup must not delete another directory swapped over its stage."""
    identity = _identity(tmp_path)
    staging = tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    parked = tmp_path / "parked-owned-stage"
    sentinel = staging / "foreign-sentinel.txt"
    content = b"protected foreign staging data"
    swapped = False

    def swapped_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        nonlocal swapped
        _extract_headers(data, asset, destination, staging=staging)
        _ = staging.parent.rename(parked)
        staging.parent.mkdir()
        _ = sentinel.write_bytes(content)
        swapped = True

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging ownership changed",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=swapped_extractor,
        )
    assert swapped
    assert sentinel.read_bytes() == content
    assert parked.is_dir()
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


def test_development_marker_rejects_hardlinked_leaf(tmp_path: Path) -> None:
    """An externally reachable marker inode cannot attest local ownership."""
    identity = _provisioned_identity(tmp_path)
    marker = identity.development_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    outside = tmp_path / "outside-marker"
    try:
        os.link(marker, outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)
    assert outside.read_bytes() == marker.read_bytes()


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


def test_development_readiness_rejects_hardlinked_required_header(
    tmp_path: Path,
) -> None:
    """Required headers must not remain writable through an outside path."""
    identity = _provisioned_identity(tmp_path)
    header = identity.development_root / "include/clang/AST/AST.h"
    outside = tmp_path / "outside-header.h"
    try:
        os.link(header, outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert not llvm_development_validation.development_root_matches(identity)
    assert outside.read_bytes() == HEADER_BYTES


def test_development_provision_rejects_hardlinked_staged_header(
    tmp_path: Path,
) -> None:
    """External aliases cannot be imported as verified staged headers."""
    identity = _identity(tmp_path)
    outside = tmp_path / "outside-header.h"

    def linked_extractor(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        try:
            os.link(destination / "include/clang/AST/AST.h", outside)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hardlinks unavailable: {error}")

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="missing|physical",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path, identity, downloader=_downloader([]), extractor=linked_extractor
        )
    assert outside.read_bytes() == HEADER_BYTES
    assert not identity.development_root.exists()


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


@pytest.mark.parametrize("alias_kind", ["root", "header_parent"])
def test_development_readiness_rejects_masked_linked_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_kind: str
) -> None:
    """False native link answers cannot hide an actual linked header ancestor."""
    identity = _provisioned_identity(tmp_path)
    alias = (
        identity.development_root
        if alias_kind == "root"
        else identity.development_root / "include/clang/AST"
    )
    relocated = alias.with_name(f"{alias.name}-physical")
    _ = alias.replace(relocated)
    try:
        _ = alias.symlink_to(relocated, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    native_is_symlink = Path.is_symlink

    def hidden_link(path: Path) -> bool:
        return False if path == alias else native_is_symlink(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", hidden_link)
        assert not llvm_development_validation.development_root_matches(identity)
    assert alias.is_symlink()


@pytest.mark.parametrize("ancestor_kind", ["root", "header_parent"])
def test_development_readiness_rejects_foreign_ancestor_lstat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ancestor_kind: str
) -> None:
    """A duck-typed ancestor directory status cannot certify local headers."""
    identity = _provisioned_identity(tmp_path)
    ancestor = (
        identity.development_root
        if ancestor_kind == "root"
        else identity.development_root / "include/clang/AST"
    )
    native_lstat = Path.lstat

    def foreign_lstat(path: Path) -> object:
        if path == ancestor:
            return SimpleNamespace(st_mode=0o40700, st_dev=1, st_ino=1)
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", foreign_lstat)
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


def test_development_marker_rejects_forged_native_bytes_from_foreign_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An injected stream must not forge readiness for altered disk bytes."""
    identity = _provisioned_identity(tmp_path)
    marker = identity.development_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    expected = marker.read_bytes()
    altered = bytes([expected[0] ^ 1]) + expected[1:]
    _ = marker.write_bytes(altered)
    assert not llvm_development_validation.development_root_matches(identity)
    native_fdopen = os.fdopen

    class ForgedRead:
        def __init__(self, native: object) -> None:
            self.native: BinaryIO = cast("BinaryIO", native)

        def __enter__(self) -> Self:
            _ = self.native.__enter__()
            return self

        def __exit__(
            self,
            kind: type[BaseException] | None,
            error: BaseException | None,
            trace: TracebackType | None,
        ) -> object:
            return self.native.__exit__(kind, error, trace)

        def fileno(self) -> int:
            return self.native.fileno()

        def read(self, amount: int) -> bytes:
            _ = self.native.read(amount)
            return expected

    def forged_fdopen(descriptor: int, mode: str) -> object:
        return ForgedRead(native_fdopen(descriptor, mode))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", forged_fdopen)
        assert not llvm_development_validation.development_root_matches(identity)
    assert marker.read_bytes() == altered


@pytest.mark.parametrize("foreign", ["bytearray", "view", "subclass"])
def test_development_marker_rejects_foreign_stream_read_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign: str
) -> None:
    """A mutable or subclass read cannot prove the pinned readiness marker."""
    identity = _provisioned_identity(tmp_path)
    native_fdopen = os.fdopen

    class ForeignBytes(bytes):
        pass

    class ModifiedRead:
        def __init__(self, native: object) -> None:
            self.native: BinaryIO = cast("BinaryIO", native)

        def __enter__(self) -> Self:
            _ = self.native.__enter__()
            return self

        def __exit__(
            self,
            kind: type[BaseException] | None,
            error: BaseException | None,
            trace: TracebackType | None,
        ) -> object:
            return self.native.__exit__(kind, error, trace)

        def fileno(self) -> int:
            return self.native.fileno()

        def read(self, amount: int) -> object:
            received = self.native.read(amount)
            return {
                "bytearray": lambda: bytearray(received),
                "view": lambda: memoryview(received),
                "subclass": lambda: ForeignBytes(received),
            }[foreign]()

    def foreign_fdopen(descriptor: int, mode: str) -> object:
        return ModifiedRead(native_fdopen(descriptor, mode))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", foreign_fdopen)
        assert not llvm_development_validation.development_root_matches(identity)


def test_development_marker_rejects_foreign_descriptor_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A duck-typed matching fstat cannot supply readiness evidence."""
    identity = _provisioned_identity(tmp_path)
    native_fstat = os.fstat
    marker = identity.development_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    admitted = marker.lstat()
    native_open = os.open
    opened: list[int] = []

    def capture_open(path: Path, flags: int) -> int:
        result = native_open(path, flags)
        if path == marker:
            opened.append(result)
        return result

    def foreign_fstat(descriptor: int) -> object:
        if descriptor in opened:
            return SimpleNamespace(
                st_dev=admitted.st_dev,
                st_ino=admitted.st_ino,
                st_size=admitted.st_size,
                st_mtime_ns=admitted.st_mtime_ns,
                st_ctime_ns=admitted.st_ctime_ns,
                st_mode=admitted.st_mode,
            )
        return native_fstat(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", capture_open)
        isolated.setattr(os, "fstat", foreign_fstat)
        assert not llvm_development_validation.development_root_matches(identity)


@pytest.mark.parametrize("invalid", [None, False, True, 1.5, -1])
def test_development_marker_rejects_non_native_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """A forged open receipt must not reach fdopen or close a borrowed fd."""
    identity = _provisioned_identity(tmp_path)
    marker = identity.development_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    native_open = os.open
    native_close = os.close
    fdopen_calls: list[int] = []

    def forged_open(path: Path, flags: int) -> int:
        if path == marker:
            return cast("int", invalid)
        return native_open(path, flags)

    def unexpected_fdopen(descriptor: int, _mode: str) -> object:
        fdopen_calls.append(descriptor)
        raise OSError("foreign descriptor must not be wrapped")

    def protected_close(descriptor: int) -> None:
        if descriptor is invalid:
            return
        native_close(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", forged_open)
        isolated.setattr(os, "fdopen", unexpected_fdopen)
        isolated.setattr(os, "close", protected_close)
        assert not llvm_development_validation.development_root_matches(identity)
    assert not fdopen_calls


def test_development_marker_rejects_foreign_stream_fileno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An integer subclass file number is not marker descriptor authority."""
    identity = _provisioned_identity(tmp_path)
    native_fdopen = os.fdopen

    class ForeignInteger(int):
        pass

    class ForeignFileno:
        def __init__(self, native: object) -> None:
            self.native: BinaryIO = cast("BinaryIO", native)

        def __enter__(self) -> Self:
            _ = self.native.__enter__()
            return self

        def __exit__(
            self,
            kind: type[BaseException] | None,
            error: BaseException | None,
            trace: TracebackType | None,
        ) -> object:
            return self.native.__exit__(kind, error, trace)

        def fileno(self) -> int:
            return ForeignInteger(self.native.fileno())

        def read(self, amount: int) -> bytes:
            return self.native.read(amount)

    def foreign_fdopen(descriptor: int, mode: str) -> object:
        return ForeignFileno(native_fdopen(descriptor, mode))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", foreign_fdopen)
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
    real_write = os.write

    def wrong_write(descriptor: int, data: bytes) -> int:
        _ = real_write(descriptor, data[:-1])
        return _bad_write_count(invalid_count, len(data))

    monkeypatch.setattr(os, "write", wrong_write)
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


@pytest.mark.parametrize("target", ["rpm", "marker"])
def test_development_staging_rejects_corrupted_complete_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    """A full write count cannot certify corrupted RPM or marker bytes."""
    identity = _identity(tmp_path)
    native_write = os.write
    corrupted = False

    def corrupted_write(descriptor: int, data: bytes) -> int:
        nonlocal corrupted
        is_rpm = data == PACKAGE_BYTES
        if (target == "rpm") == is_rpm and not corrupted:
            corrupted = True
            _ = native_write(descriptor, bytes([data[0] ^ 1]) + data[1:])
            return len(data)
        return native_write(descriptor, data)

    def unexpected_cpio(path: Path) -> bytes:
        pytest.fail(f"corrupted RPM reached CPIO: {path.name}")

    monkeypatch.setattr(os, "write", corrupted_write)
    if target == "rpm":
        monkeypatch.setattr(
            llvm_development_validation, "_cpio_payload", unexpected_cpio
        )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="staging content mismatch",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=_downloader([]),
            extractor=None if target == "rpm" else _extract_headers,
        )
    assert corrupted
    assert not identity.development_root.exists()
    assert not (
        tmp_path / ".temp/llvm-development-provision-linux-x86_64"
    ).exists()


@pytest.mark.parametrize("invalid_count", list(_BAD_WRITE_RESULTS))
def test_rpm_extraction_rejects_incomplete_staging_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """Never execute a staged RPM with an invalid host write count."""
    identity = _identity(tmp_path)
    real_write = os.write

    def wrong_write(descriptor: int, data: bytes) -> int:
        _ = real_write(descriptor, data[:-1])
        return _bad_write_count(invalid_count, len(data))

    def unexpected_cpio(path: Path) -> bytes:
        pytest.fail(f"unverified RPM reached CPIO: {path.name}")

    monkeypatch.setattr(os, "write", wrong_write)
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


def test_rpm_command_enforces_process_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stalled RPM decoder cannot hold provisioning indefinitely."""
    command = ["cpio", "-it", "--quiet"]
    fault = sp.TimeoutExpired(command, timeout=120)

    def stalled_run(
        argv: list[str], *, timeout: int, **_kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        assert argv == command
        assert timeout == 120
        raise fault

    monkeypatch.setattr(llvm_development_validation.sp, "run", stalled_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="TimeoutExpired",
    ) as observed:
        _ = llvm_development_validation._command_bytes(command)
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


@pytest.mark.parametrize("label", ["staging", "destination"])
def test_development_preflight_rejects_masked_linked_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str
) -> None:
    """False native link replies cannot certify a physically linked ancestor."""
    external = tmp_path / "outside"
    external.mkdir()
    linked = tmp_path / "linked"
    try:
        _ = linked.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    native_link = Path.is_symlink

    def masked_link(path: Path) -> bool:
        return False if path == linked else native_link(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", masked_link)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical directory",
        ):
            llvm_development_validation._require_physical_directories(
                linked, label
            )
    assert linked.is_symlink()


def test_development_preflight_rejects_foreign_directory_lstat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A duck-typed lstat cannot certify staging directory ownership."""
    target = tmp_path / "staging"
    target.mkdir()
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> object:
        if path == target:
            return SimpleNamespace(st_mode=0o40700, st_dev=1, st_ino=1)
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical directory",
        ):
            llvm_development_validation._require_physical_directories(
                target, "staging"
            )


def test_development_preflight_rejects_false_missing_real_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged nonexistent answer cannot bypass physical directory proof."""
    target = tmp_path / "staging"
    target.mkdir()
    native_exists = Path.exists

    def hidden_directory(path: Path) -> bool:
        return False if path == target else native_exists(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "exists", hidden_directory)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical directory",
        ):
            llvm_development_validation._require_physical_directories(
                target, "staging"
            )


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


@pytest.mark.parametrize("alias_kind", ["symlink", "hardlink"])
def test_development_staging_rejects_leaf_swap_after_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_kind: str
) -> None:
    """An existing target cannot replace an empty leaf just before create."""
    target = tmp_path / "stage.rpm"
    sentinel = tmp_path / "external.rpm"
    original = b"protected RPM outside staging"
    _ = sentinel.write_bytes(original)
    native_exists = Path.exists
    swapped = False

    def swap_during_exists(path: Path) -> bool:
        nonlocal swapped
        if path == target and not swapped:
            swapped = True
            try:
                if alias_kind == "symlink":
                    _ = path.symlink_to(sentinel)
                else:
                    os.link(sentinel, path)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"file aliases unavailable: {error}")
            return False
        return native_exists(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "exists", swap_during_exists)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                target, PACKAGE_BYTES
            )
    assert swapped
    assert sentinel.read_bytes() == original


def test_staging_writer_does_not_follow_late_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A parent redirected at open cannot receive the new RPM or marker."""
    if os.name != "posix":
        pytest.skip("POSIX directory writer boundary")
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    parked = tmp_path / "parked-stage"
    external, sentinel = _external_sentinel(tmp_path)
    target = parent / "stage.rpm"
    native_open = os.open
    native_rename = os.rename
    swapped = False

    def swap_at_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if path == target or (path == target.name and dir_fd is not None):
            native_rename(parent, parked)
            _ = parent.symlink_to(external, target_is_directory=True)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", swap_at_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                target, PACKAGE_BYTES
            )
    assert swapped
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == FOREIGN_CONTENT_BYTES


@pytest.mark.parametrize("invalid_descriptor", [None, False, 0.5, -1])
def test_staging_writer_rejects_non_native_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_descriptor: object,
) -> None:
    """A forged descriptor never supplies authority to overwrite a file."""
    path = tmp_path / "staged.rpm"
    native_open = os.open

    def false_open(
        candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if _is_staged_file_open(candidate, path, dir_fd):
            return cast("int", invalid_descriptor)
        return native_open(candidate, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", false_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="invalid descriptor",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                path, PACKAGE_BYTES
            )
    assert not path.exists()


def test_staging_writer_rejects_shared_inode_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An alias introduced at open cannot receive even rejected stage bytes."""
    target = tmp_path / "private.rpm"
    outside = tmp_path / "external.rpm"
    native_open = os.open
    linked = False

    def linked_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal linked
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if _is_staged_file_open(path, target, dir_fd):
            try:
                os.link(target, outside)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"hardlinks unavailable: {error}")
            linked = True
        return descriptor

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", linked_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="descriptor mismatch",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                target, PACKAGE_BYTES
            )
    assert linked
    assert outside.read_bytes() == b""


def test_staging_writer_rejects_nonempty_new_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host-open mutation cannot supply a prefilled staging descriptor."""
    target = tmp_path / "private.rpm"
    native_open = os.open

    def prefilled_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if _is_staged_file_open(path, target, dir_fd):
            _ = os.write(descriptor, FOREIGN_CONTENT_BYTES)
            _ = os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", prefilled_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="descriptor mismatch",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                target, PACKAGE_BYTES
            )
    assert target.read_bytes() == FOREIGN_CONTENT_BYTES


def test_staging_writer_rejects_forged_regular_fd_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A duck-typed fstat cannot authorize a newly created RPM file."""
    path = tmp_path / "staged.rpm"
    opened: list[int] = []
    native_open = os.open
    native_fstat = os.fstat

    def capture_open(
        candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(candidate, flags, mode, dir_fd=dir_fd)
        if _is_staged_file_open(candidate, path, dir_fd):
            opened.append(descriptor)
        return descriptor

    def fake_fstat(descriptor: int) -> object:
        if descriptor in opened:
            return SimpleNamespace(st_mode=0o100600, st_dev=1, st_ino=1)
        return native_fstat(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", capture_open)
        isolated.setattr(os, "fstat", fake_fstat)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="descriptor mismatch",
        ):
            llvm_development_validation._write_verified_staging_bytes(
                path, PACKAGE_BYTES
            )
    assert opened
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])
    assert path.read_bytes() == b""


def test_staging_writer_retains_host_open_fault_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OS open failure is a typed provision error with the same cause."""
    path = tmp_path / "staged.rpm"
    fault = OSError("cannot create local RPM")

    native_open = os.open

    def fault_open(
        candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if _is_staged_file_open(candidate, path, dir_fd):
            raise fault
        return native_open(candidate, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", fault_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="creation failed",
        ) as observed:
            llvm_development_validation._write_verified_staging_bytes(
                path, PACKAGE_BYTES
            )
    assert observed.value.__cause__ is fault
    assert not path.exists()


def test_staging_writer_retains_host_close_fault_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A descriptor close failure cannot report successful publication."""
    path = tmp_path / "staged.rpm"
    native_close = os.close
    native_open = os.open
    fault = OSError("cannot close local RPM")
    stage_descriptors: set[int] = set()

    def track_open(
        candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(candidate, flags, mode, dir_fd=dir_fd)
        if _is_staged_file_open(candidate, path, dir_fd):
            stage_descriptors.add(descriptor)
        return descriptor

    def fault_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in stage_descriptors:
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", fault_close)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="close failed",
        ) as observed:
            llvm_development_validation._write_verified_staging_bytes(
                path, PACKAGE_BYTES
            )
    assert observed.value.__cause__ is fault
    assert path.read_bytes() == PACKAGE_BYTES


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


def test_rpm_include_tree_rejects_masked_symlink_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A false link predicate cannot admit physically redirected CPIO content."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    outside = tmp_path / "external-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    member = include_root / "header.h"
    try:
        _ = member.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file aliases unavailable: {error}")
    native_is_symlink = Path.is_symlink

    def hidden_link(path: Path) -> bool:
        return False if path == member else native_is_symlink(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", hidden_link)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical member",
        ):
            llvm_development_validation._reject_include_symlinks(include_root)
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES


def test_rpm_include_tree_rejects_foreign_member_lstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duck-typed stat metadata cannot certify a CPIO extracted header."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    member = include_root / "header.h"
    _ = member.write_bytes(HEADER_BYTES)
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> object:
        if path == member:
            return SimpleNamespace(st_mode=0o100600, st_dev=1, st_ino=1)
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical member",
        ):
            llvm_development_validation._reject_include_symlinks(include_root)


def test_rpm_include_tree_rejects_fifo_member(tmp_path: Path) -> None:
    """An extracted FIFO cannot satisfy a physical header member witness."""
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    mkfifo(include_root / "header.h")
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="physical member",
    ):
        llvm_development_validation._reject_include_symlinks(include_root)


def test_rpm_include_tree_accepts_physical_regular_members(tmp_path: Path) -> None:
    """Native CPIO include roots and regular members still pass inspection."""
    include_root = tmp_path / "usr/include"
    header = include_root / "clang/AST/AST.h"
    header.parent.mkdir(parents=True)
    _ = header.write_bytes(HEADER_BYTES)
    llvm_development_validation._reject_include_symlinks(include_root)


@pytest.mark.parametrize("invalid_size", [None, False, 0, -1, 134217729])
def test_default_development_download_rejects_unbounded_size(
    monkeypatch: pytest.MonkeyPatch, invalid_size: object
) -> None:
    """A malformed pin cannot authorize unbounded network memory."""

    def unexpected_urlopen(*_args: object, **_kwargs: object) -> object:
        pytest.fail("unbounded RPM size reached network access")

    monkeypatch.setattr(
        llvm_development_validation.urllib.request, "urlopen", unexpected_urlopen
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="download size",
    ):
        _ = llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm",
            expected_size_bytes=cast("int", invalid_size),
        )


def test_default_development_download_bounds_read_to_pinned_asset_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default RPM HTTP reader must never make an unbounded read."""
    identity = _identity(tmp_path)
    requested: list[int] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, _kind: object, _error: object, _trace: object) -> bool:
            return False

        def read(self, limit: int = -1) -> bytes:
            requested.append(limit)
            return PACKAGE_BYTES + b"x"

    monkeypatch.setattr(
        llvm_development_validation.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="exceeds pinned size",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path, identity, extractor=_extract_headers
        )
    assert requested == [len(PACKAGE_BYTES) + 1]
    assert not identity.development_root.exists()


def test_default_development_download_admits_exact_pinned_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid RPM response remains provisionable with bounded reads."""
    identity = _identity(tmp_path)
    requested: list[int] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, _kind: object, _error: object, _trace: object) -> bool:
            return False

        def read(self, limit: int = -1) -> bytes:
            requested.append(limit)
            return PACKAGE_BYTES

    monkeypatch.setattr(
        llvm_development_validation.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    result = llvm_development_validation.provision_development_identity(
        tmp_path, identity, extractor=_extract_headers
    )
    assert result == identity.development_root
    assert requested == [len(PACKAGE_BYTES) + 1]
    assert llvm_development_validation.development_root_matches(identity)


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

        def read(self, _limit: int) -> object:
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
            "https://example.invalid/pinned.rpm",
            expected_size_bytes=len(PACKAGE_BYTES),
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
            "https://example.invalid/pinned.rpm",
            expected_size_bytes=len(PACKAGE_BYTES),
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
            "https://example.invalid/pinned.rpm",
            expected_size_bytes=len(PACKAGE_BYTES),
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

        def read(self, _limit: int) -> bytes:
            return PACKAGE_BYTES

    monkeypatch.setattr(
        llvm_development_validation.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    assert (
        llvm_development_validation._download_asset(
            "https://example.invalid/pinned.rpm",
            expected_size_bytes=len(PACKAGE_BYTES),
        )
        == PACKAGE_BYTES
    )


@pytest.mark.parametrize("foreign", [None, "rpm", bytearray(PACKAGE_BYTES)])
def test_development_package_verification_rejects_foreign_byte_object(
    foreign: object,
) -> None:
    """Exact size and digest never admit an untrusted nonbyte RPM object."""
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="native bytes",
    ):
        llvm_development_validation.verify_development_asset(
            cast("bytes", foreign), _asset()
        )


def test_development_package_verification_rejects_bytes_subclass() -> None:
    """An input subclass cannot forge byte length while retaining a digest."""

    class ForeignBytes(bytes):
        pass

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="native bytes",
    ):
        llvm_development_validation.verify_development_asset(
            ForeignBytes(PACKAGE_BYTES), _asset()
        )


def test_development_provision_rejects_foreign_downloader_payload(
    tmp_path: Path,
) -> None:
    """A custom downloader returning bytearray cannot authorize publishing."""
    identity = _identity(tmp_path)
    extracted: list[str] = []

    def nonnative_download(_url: str) -> bytes:
        return cast("bytes", cast("object", bytearray(PACKAGE_BYTES)))

    def record_extraction(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        extracted.append(asset.name)
        _extract_headers(data, asset, destination, staging=staging)

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="native bytes",
    ):
        _ = llvm_development_validation.provision_development_identity(
            tmp_path,
            identity,
            downloader=nonnative_download,
            extractor=record_extraction,
        )
    assert not extracted
    assert not identity.development_root.exists()
