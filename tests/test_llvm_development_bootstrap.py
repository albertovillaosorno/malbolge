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
import http.client
import io
import os
import shutil
import subprocess as sp
from contextlib import suppress
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, Self, cast, override

import pytest
from scripts.bootstrap import llvm_development_validation

from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
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
POSIX_OS_NAME = "posix"
RPM2CPIO_NAME = "rpm2cpio"
SYMLINK_SUBSTITUTION = "symlink"


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


@pytest.mark.parametrize(
    "member",
    [
        "usr/include/clang/AST/AST.h",
        "usr/include/llvm/IR/Module.h",
        "usr/include/llvm-c/Core.h",
    ],
)
def test_cpio_filter_matches_normalized_includes(member: str) -> None:
    """GNU CPIO lists newc member names without an initial dot segment."""
    assert fnmatchcase(
        member, llvm_development_validation.CPIO_INCLUDE_PATTERN
    )
    assert not fnmatchcase(
        "usr/lib/libLLVM.so", llvm_development_validation.CPIO_INCLUDE_PATTERN
    )


def test_rpm_member_validation_rejects_parent_and_absolute_paths() -> None:
    """CPIO member names cannot escape the package extraction directory."""
    for member in ("./usr/include/../../escape", "/usr/include/escape"):
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="escapes package root",
        ):
            llvm_development_validation.validate_rpm_members((member,))


@pytest.mark.parametrize(
    "members",
    [
        ("usr/include/AST.h", "usr/include/AST.h"),
        ("usr/include/AST.h", "./usr/include/AST.h"),
        ("usr/include/AST.h", "usr//include/AST.h"),
        ("usr/include/clang/", "usr/include/clang"),
    ],
)
def test_rpm_member_validation_rejects_normalized_duplicate_names(
    members: tuple[str, str],
) -> None:
    """One physical destination must not receive two RPM archive entries."""
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="duplicate",
    ):
        llvm_development_validation.validate_rpm_members(members)


def test_rpm_member_validation_accepts_distinct_cpio_names() -> None:
    """CPIO may contain separate directory and header entries."""
    llvm_development_validation.validate_rpm_members(
        ("./usr/include", "usr/include/clang/AST.h", "usr/include/llvm/Module.h")
    )


@pytest.mark.parametrize(
    "member",
    [
        "usr/include/name\t.h",
        "usr/include/name\x00.h",
        "usr/include/name\u202e.h",
        "usr/include/name\u2028.h",
    ],
)
def test_rpm_member_validation_rejects_hidden_path_characters(member: str) -> None:
    """An RPM CPIO name cannot hide controls or display-order overrides."""
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="non-printable",
    ):
        llvm_development_validation.validate_rpm_members((member,))


@pytest.mark.parametrize(
    "listing",
    [
        b"usr/include/AST.h\r\0",
        "usr/include/foo\u2028bar.h\0".encode(),
        b"usr/include/name\ncontinued.h\0",
    ],
)
def test_cpio_listing_rejects_hidden_member_separators(
    monkeypatch: pytest.MonkeyPatch,
    listing: bytes,
) -> None:
    """CPIO NUL delimiters preserve embedded newline and format controls."""

    def synthetic_list(_argv: list[str], **_kwargs: object) -> bytes:
        return listing

    monkeypatch.setattr(
        llvm_development_validation, "_command_bytes", synthetic_list
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="non-printable",
    ):
        _ = llvm_development_validation._cpio_members(b"synthetic CPIO")


@pytest.mark.parametrize(
    "listing, expected",
    [
        (
            b"usr/include/one.h\0usr/include/two.h\0",
            ("usr/include/one.h", "usr/include/two.h"),
        ),
        (b"./usr/include/single.h\0", ("./usr/include/single.h",)),
    ],
)
def test_cpio_listing_accepts_null_delimited_member_names(
    monkeypatch: pytest.MonkeyPatch,
    listing: bytes,
    expected: tuple[str, ...],
) -> None:
    """NUL-delimited CPIO listings retain exact printable path names."""

    def synthetic_list(argv: list[str], **_kwargs: object) -> bytes:
        assert argv == ["cpio", "-it", "--quiet", "--null"]
        return listing

    monkeypatch.setattr(
        llvm_development_validation, "_command_bytes", synthetic_list
    )
    assert llvm_development_validation._cpio_members(b"payload") == expected


@pytest.mark.parametrize(
    "listing",
    [b"usr/include/missing-nul.h", b"usr/include/one.h\0extra"],
)
def test_cpio_listing_requires_complete_null_termination(
    monkeypatch: pytest.MonkeyPatch,
    listing: bytes,
) -> None:
    """Truncated CPIO listing output cannot authorize an incomplete member."""

    def synthetic_list(argv: list[str], **_kwargs: object) -> bytes:
        assert argv == ["cpio", "-it", "--quiet", "--null"]
        return listing

    monkeypatch.setattr(
        llvm_development_validation, "_command_bytes", synthetic_list
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="terminator",
    ):
        _ = llvm_development_validation._cpio_members(b"payload")


def test_rpm_duplicate_member_listing_rejects_before_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ambiguous names cannot reach an extractor or published header tree."""
    identity = _identity(tmp_path)
    listing = (
        b"usr/include/clang/AST/AST.h\0"
        b"./usr/include/clang/AST/AST.h\0"
    )

    def synthetic_list(argv: list[str], **_kwargs: object) -> bytes:
        assert argv == ["cpio", "-it", "--quiet", "--null"]
        return listing

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation, "_command_bytes", synthetic_list
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="duplicate destination",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


def test_rpm_control_character_listing_rejects_before_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untrusted member control characters never reach the CPIO extractor."""
    identity = _identity(tmp_path)

    def synthetic_list(argv: list[str], **_kwargs: object) -> bytes:
        assert argv == ["cpio", "-it", "--quiet", "--null"]
        return b"usr/include/clang/AST/AST.h\r\0"

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation, "_command_bytes", synthetic_list
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="non-printable",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


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
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        del stdin, pass_fds
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

    def synthetic_payload(_rpm: Path, _expected: bytes) -> bytes:
        del _rpm, _expected
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


CPIO_EXECUTABLE = "cpio"
INCLUDE_DIRECTORY = "include"


def _link_external_header(outside: Path, header: Path) -> None:
    header.unlink(missing_ok=True)
    try:
        os.link(outside, header)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")


def _synthetic_hardlinked_cpio(
    outside: Path, *, during_copy: bool
) -> Callable[..., bytes]:
    def run(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        del stdin, pass_fds
        if arguments[0] == CPIO_EXECUTABLE and cwd is not None:
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            if during_copy:
                _ = header.write_bytes(HEADER_BYTES)
            else:
                _link_external_header(outside, header)
        return b""

    return run


def _late_hardlinked_copytree(
    outside: Path, native_copytree: Callable[..., Path]
) -> Callable[..., Path]:
    def copy(
        src: Path | os.DirEntry[str],
        dst: Path | os.DirEntry[str],
        *args: object,
        **kwargs: object,
    ) -> Path:
        if isinstance(src, Path) and src.name == INCLUDE_DIRECTORY:
            _link_external_header(outside, src / "clang/AST/AST.h")
        return native_copytree(src, dst, *args, **kwargs)

    return copy


def _synthetic_hardlinked_payload(rpm: Path, expected: bytes) -> bytes:
    del rpm, expected
    return b"cpio"


def _synthetic_hardlinked_members(payload: bytes) -> tuple[str, ...]:
    del payload
    return ("usr/include/clang/AST/AST.h",)


@pytest.mark.skipif(
    os.name != POSIX_OS_NAME, reason="requires POSIX package extraction"
)
@pytest.mark.parametrize("during_copy", [False, True])
def test_rpm_copy_rejects_externally_hardlinked_source_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, during_copy: bool
) -> None:
    """External source hardlinks cannot enter the published development kit."""
    outside = tmp_path / "outside-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    identity = _identity(tmp_path)
    native_copytree = cast("Callable[..., Path]", shutil.copytree)
    with monkeypatch.context() as isolated:
        if during_copy:
            isolated.setattr(
                shutil,
                "copytree",
                _late_hardlinked_copytree(outside, native_copytree),
            )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            _synthetic_hardlinked_members,
        )
        isolated.setattr(
            llvm_development_validation,
            "_command_bytes",
            _synthetic_hardlinked_cpio(outside, during_copy=during_copy),
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="hardlink",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


@pytest.mark.skipif(
    os.name != POSIX_OS_NAME, reason="requires POSIX package extraction"
)
def test_rpm_overlay_does_not_overwrite_external_destination_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prior header alias cannot direct the next overlay write outside."""
    identity = _identity(tmp_path)
    outside = tmp_path / "outside-header.h"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    staged_header = (
        tmp_path
        / ".temp"
        / f"llvm-development-provision-{LINUX_PLATFORM}"
        / "development/include/clang/AST/AST.h"
    )

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        del stdin, pass_fds
        if arguments[0] == CPIO_EXECUTABLE and cwd is not None:
            source = cwd / "usr/include/clang/AST/AST.h"
            source.parent.mkdir(parents=True)
            _ = source.write_bytes(HEADER_BYTES)
            staged_header.parent.mkdir(parents=True)
            _link_external_header(outside, staged_header)
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            _synthetic_hardlinked_members,
        )
        isolated.setattr(
            llvm_development_validation, "_command_bytes", synthetic_cpio
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="hardlink",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES
    assert not identity.development_root.exists()


@pytest.mark.parametrize("stdout", [b"", b"unexpected extraction output"])
def test_rpm_extraction_requires_empty_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: bytes,
) -> None:
    """Quiet CPIO extraction must not report an unexpected stdout receipt."""
    staging = tmp_path / "package"
    staging.mkdir()

    def synthetic_command(
        argv: list[str], **_options: object
    ) -> bytes:
        assert argv[:2] == ["cpio", "-idm"]
        return stdout

    monkeypatch.setattr(
        llvm_development_validation, "_command_bytes", synthetic_command
    )
    if stdout:
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="unexpected stdout",
        ):
            llvm_development_validation._extract_cpio_headers(b"data", staging)
    else:
        llvm_development_validation._extract_cpio_headers(b"data", staging)


@pytest.mark.parametrize(
    "existing, incoming, accepted",
    [
        (b"first content", b"different bytes", False),
        (b"same header", b"same header", True),
    ],
)
def test_rpm_overlay_rejects_conflicting_header_bytes(
    tmp_path: Path,
    existing: bytes,
    incoming: bytes,
    *,
    accepted: bool,
) -> None:
    """Pinned packages cannot silently overwrite incompatible shared headers."""
    source = tmp_path / "package/usr/include/clang"
    source.mkdir(parents=True)
    _ = (source / "AST.h").write_bytes(incoming)
    destination = tmp_path / "development/include/clang"
    destination.mkdir(parents=True)
    previous = destination / "AST.h"
    _ = previous.write_bytes(existing)

    if accepted:
        llvm_development_validation._copy_rpm_include_tree(
            source.parent, destination.parent
        )
    else:
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="conflicting header",
        ):
            llvm_development_validation._copy_rpm_include_tree(
                source.parent, destination.parent
            )
    assert previous.read_bytes() == (incoming if accepted else existing)


@pytest.mark.parametrize("replacement", ["symlink", "hardlink"])
def test_rpm_overlay_preserves_late_foreign_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """A destination swapped after comparison must never receive copied bytes."""
    source = tmp_path / "package/usr/include/clang/AST.h"
    source.parent.mkdir(parents=True)
    _ = source.write_bytes(HEADER_BYTES)
    destination = tmp_path / "development/include/clang/AST.h"
    destination.parent.mkdir(parents=True)
    _ = destination.write_bytes(HEADER_BYTES)
    outside = tmp_path / "external-header"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    native_copytree = shutil.copytree

    def replace_during_copy(
        src: Path, dst: Path, *args: object, **kwargs: object
    ) -> Path:
        destination.unlink()
        try:
            if replacement == "symlink":
                _ = destination.symlink_to(outside)
            else:
                os.link(outside, destination)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"filesystem aliases unavailable: {error}")
        return cast("Callable[..., Path]", native_copytree)(
            src, dst, *args, **kwargs
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "copytree", replace_during_copy)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="conflicting header",
        ):
            llvm_development_validation._copy_rpm_include_tree(
                source.parent.parent, destination.parent.parent
            )
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES


@pytest.mark.parametrize("change", ["omit", "alter", "add", "replace-existing"])
def test_rpm_overlay_rejects_false_successful_copy_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    """A successful copytree return cannot certify unverified header output."""
    source = tmp_path / "package/usr/include/clang/AST.h"
    source.parent.mkdir(parents=True)
    _ = source.write_bytes(HEADER_BYTES)
    destination = tmp_path / "development/include/clang/AST.h"
    destination.parent.mkdir(parents=True)
    retained = destination.parent / "preexisting.h"
    _ = retained.write_bytes(FOREIGN_CONTENT_BYTES)
    native_copytree = shutil.copytree

    def false_success(src: Path, dst: Path, *args: object, **kwargs: object) -> Path:
        copied = cast("Callable[..., Path]", native_copytree)(src, dst, *args, **kwargs)
        if src != source.parent.parent:
            return copied
        if change == "omit":
            destination.unlink()
        elif change == "alter":
            _ = destination.write_bytes(FOREIGN_CONTENT_BYTES)
        elif change == "add":
            _ = (dst / "unlisted.h").write_bytes(FOREIGN_CONTENT_BYTES)
        else:
            _ = retained.write_bytes(b"replaced existing header")
        return copied

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "copytree", false_success)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="copy receipt",
        ):
            llvm_development_validation._copy_rpm_include_tree(
                source.parent.parent, destination.parent.parent
            )


@pytest.mark.parametrize("existing", [False, True])
def test_rpm_overlay_uses_pinned_native_header_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    """Late FIFO or symlink replacement cannot reach a blocking Path.open."""
    incoming = tmp_path / "incoming.h"
    _ = incoming.write_bytes(HEADER_BYTES)
    destination = tmp_path / "included.h"
    if existing:
        _ = destination.write_bytes(HEADER_BYTES)
    native_open = Path.open

    def forbid_pathname_read(
        path: Path, *args: object, **kwargs: object
    ) -> BinaryIO:
        if path in (incoming, destination):
            pytest.fail("header overlay used a replaceable pathname stream")
        return cast("Callable[..., BinaryIO]", native_open)(path, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "open", forbid_pathname_read)
        result = llvm_development_validation._copy_header_no_replace(
            str(incoming), str(destination)
        )
    assert result == str(destination)
    assert destination.read_bytes() == HEADER_BYTES


@pytest.mark.skipif(os.name != POSIX_OS_NAME, reason="requires native FIFO flags")
@pytest.mark.parametrize("existing", [False, True])
def test_rpm_overlay_rejects_late_fifo_before_native_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    """Path substitution after lstat never blocks or reads a pipe."""
    incoming = tmp_path / "incoming.h"
    _ = incoming.write_bytes(HEADER_BYTES)
    destination = tmp_path / "included.h"
    if existing:
        _ = destination.write_bytes(HEADER_BYTES)
    victim = destination if existing else incoming
    native_open = os.open
    opened: list[int] = []

    def swap_to_fifo(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
    ) -> int:
        if Path(path) == victim:
            if not opened:
                victim.unlink()
                os.mkfifo(victim)
            opened.append(flags)
        return native_open(path, flags)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", swap_to_fifo)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical header|descriptor identity",
        ):
            _ = llvm_development_validation._copy_header_no_replace(
                str(incoming), str(destination)
            )
    assert opened
    assert all(flag & os.O_NONBLOCK for flag in opened)
    assert all(flag & os.O_NOFOLLOW for flag in opened)
    assert victim.is_fifo()


def test_rpm_overlay_rejects_late_source_header_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Source bytes must remain stable across extraction into the overlay."""
    source = tmp_path / "package/usr/include/clang/AST.h"
    source.parent.mkdir(parents=True)
    _ = source.write_bytes(HEADER_BYTES)
    destination = tmp_path / "development/include"
    native_copytree = shutil.copytree

    def drift_source(src: Path, dst: Path, *args: object, **kwargs: object) -> Path:
        copied = cast("Callable[..., Path]", native_copytree)(src, dst, *args, **kwargs)
        if src == source.parent.parent:
            _ = source.write_bytes(FOREIGN_CONTENT_BYTES)
        return copied

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "copytree", drift_source)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="copy receipt",
        ):
            llvm_development_validation._copy_rpm_include_tree(
                source.parent.parent, destination
            )


def test_header_tree_receipt_rejects_foreign_descriptor_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign opened inode cannot certify the physically listed header."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    header = include_root / "header.h"
    _ = header.write_bytes(HEADER_BYTES)
    foreign = tmp_path / "foreign-header"
    _ = foreign.write_bytes(HEADER_BYTES)
    native_open = os.open
    swapped: list[bool] = []

    def redirected_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        if path == header:
            swapped.append(True)
            return native_open(foreign, flags)
        return native_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", redirected_open)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="descriptor identity",
        ):
            _ = llvm_development_validation._header_tree_receipt(include_root)
    assert swapped


def test_header_tree_receipt_uses_physical_descriptor_not_foreign_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted pathname stream cannot forge the header digest receipt."""
    include_root = tmp_path / "usr/include"
    include_root.mkdir(parents=True)
    header = include_root / "header.h"
    _ = header.write_bytes(HEADER_BYTES)
    native_open = Path.open

    def foreign_open(path: Path, *args: object, **kwargs: object):
        if path == header:
            return io.BytesIO(FOREIGN_CONTENT_BYTES)
        return native_open(path, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "open", foreign_open)
        receipt = llvm_development_validation._header_tree_receipt(include_root)
    assert receipt[Path("header.h")][1] == hashlib.sha256(HEADER_BYTES).digest()


@pytest.mark.parametrize("missing", ["optional-file", "listed-empty-dir"])
def test_rpm_extraction_rejects_missing_listed_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    """CPIO must extract every listed include member before publication."""
    identity = _identity(tmp_path)

    def synthetic_cpio(
        arguments: list[str], *, cwd: Path | None = None, **_kwargs: object
    ) -> bytes:
        if arguments[0] == "cpio" and cwd is not None:
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
        return b""

    additional = (
        "usr/include/clang/AST/Optional.h"
        if missing == "optional-file"
        else "usr/include/other-empty-dir/"
    )
    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", _synthetic_hardlinked_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _payload: ("usr/include/clang/AST/AST.h", additional),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="missing listed",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


def test_rpm_extraction_accepts_listed_optional_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Listed optional headers and empty directories remain valid package output."""
    identity = _identity(tmp_path)

    def synthetic_cpio(
        arguments: list[str], *, cwd: Path | None = None, **_kwargs: object
    ) -> bytes:
        if arguments[0] == "cpio" and cwd is not None:
            include = cwd / "usr/include"
            directory = include / "clang/AST"
            directory.mkdir(parents=True)
            _ = (directory / "AST.h").write_bytes(HEADER_BYTES)
            _ = (directory / "Optional.h").write_bytes(FOREIGN_CONTENT_BYTES)
            (include / "empty-dir").mkdir()
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", _synthetic_hardlinked_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _payload: (
                "./usr/include/clang/AST/AST.h",
                "usr/include/clang/AST/Optional.h",
                "usr/include/empty-dir/",
            ),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        published = llvm_development_validation.provision_development_identity(
            tmp_path, identity, downloader=_downloader([])
        )
    assert llvm_development_validation.development_root_matches(identity)
    assert (published / "include/clang/AST/Optional.h").read_bytes() == FOREIGN_CONTENT_BYTES
    assert (published / "include/empty-dir").is_dir()


def test_rpm_extraction_rejects_unlisted_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An extraction may create implicit parents, not unlisted empty trees."""
    identity = _identity(tmp_path)

    def synthetic_cpio(
        arguments: list[str], *, cwd: Path | None = None, **_kwargs: object
    ) -> bytes:
        if arguments[0] == "cpio" and cwd is not None:
            include = cwd / "usr/include"
            header = include / "clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
            (include / "unlisted-empty").mkdir()
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", _synthetic_hardlinked_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _payload: ("usr/include/clang/AST/AST.h",),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="unlisted",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


@pytest.mark.parametrize(
    "unlisted",
    ["clang/AST/Surprise.h", "outside-list.h"],
)
def test_rpm_extraction_rejects_unlisted_header_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unlisted: str
) -> None:
    """A native CPIO listing must account for every extracted header file."""
    identity = _identity(tmp_path)

    def synthetic_cpio(
        arguments: list[str], *, cwd: Path | None = None, **_kwargs: object
    ) -> bytes:
        if arguments[0] == "cpio" and cwd is not None:
            include = cwd / "usr/include"
            included = include / "clang/AST/AST.h"
            included.parent.mkdir(parents=True)
            _ = included.write_bytes(HEADER_BYTES)
            unexpected = include / unlisted
            unexpected.parent.mkdir(parents=True, exist_ok=True)
            _ = unexpected.write_bytes(FOREIGN_CONTENT_BYTES)
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", _synthetic_hardlinked_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _payload: ("./usr/include/clang/AST/AST.h",),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="unlisted header",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


def test_development_provision_rejects_missing_optional_copied_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exact copied archive membership is mandatory beyond required headers."""
    identity = _identity(tmp_path)
    native_copytree = shutil.copytree

    def synthetic_cpio(
        arguments: list[str], *, cwd: Path | None = None, **_kwargs: object
    ) -> bytes:
        if arguments[0] == "cpio" and cwd is not None:
            include = cwd / "usr/include/clang/AST"
            include.mkdir(parents=True)
            _ = (include / "AST.h").write_bytes(HEADER_BYTES)
            _ = (include / "Optional.h").write_bytes(HEADER_BYTES)
        return b""

    def omit_optional(src: Path, dst: Path, *args: object, **kwargs: object) -> Path:
        copied = cast("Callable[..., Path]", native_copytree)(
            src, dst, *args, **kwargs
        )
        if isinstance(src, Path) and src.name == "include":
            (dst / "clang/AST/Optional.h").unlink()
        return copied

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation, "_cpio_payload", _synthetic_hardlinked_payload
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            lambda _payload: (
                "usr/include/clang/AST/AST.h",
                "usr/include/clang/AST/Optional.h",
            ),
        )
        isolated.setattr(llvm_development_validation, "_command_bytes", synthetic_cpio)
        isolated.setattr(shutil, "copytree", omit_optional)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="copy receipt",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert not identity.development_root.exists()


def test_rpm_overlay_identical_header_preserves_existing_metadata(
    tmp_path: Path,
) -> None:
    """An already equal header does not need an in-place overwrite."""
    source = tmp_path / "package/usr/include/clang/AST.h"
    source.parent.mkdir(parents=True)
    _ = source.write_bytes(HEADER_BYTES)
    destination = tmp_path / "development/include/clang/AST.h"
    destination.parent.mkdir(parents=True)
    _ = destination.write_bytes(HEADER_BYTES)
    initial_mtime = 1_000_000_000
    os.utime(destination, ns=(initial_mtime, initial_mtime))
    identity = destination.stat()

    llvm_development_validation._copy_rpm_include_tree(
        source.parent.parent, destination.parent.parent
    )
    after = destination.stat()
    assert (after.st_dev, after.st_ino) == (identity.st_dev, identity.st_ino)
    assert after.st_mtime_ns == initial_mtime
    assert destination.read_bytes() == HEADER_BYTES


def test_rpm_overlay_rechecks_bytes_after_same_mtime_source_mutation(
    tmp_path: Path,
) -> None:
    """An earlier identical overlay may not cache a later conflict as equal."""
    source = tmp_path / "package/usr/include/clang/AST.h"
    source.parent.mkdir(parents=True)
    _ = source.write_bytes(b"original-1")
    destination = tmp_path / "development/include/clang/AST.h"
    destination.parent.mkdir(parents=True)
    _ = destination.write_bytes(b"original-1")
    original = source.stat()
    os.utime(destination, ns=(original.st_atime_ns, original.st_mtime_ns))

    llvm_development_validation._copy_rpm_include_tree(
        source.parent.parent, destination.parent.parent
    )
    _ = source.write_bytes(b"modified-1")
    os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="conflicting header",
    ):
        llvm_development_validation._copy_rpm_include_tree(
            source.parent.parent, destination.parent.parent
        )
    assert destination.read_bytes() == b"original-1"


@pytest.mark.parametrize("conflicting", [False, True])
def test_two_rpm_header_overlays_preserve_shared_byte_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    conflicting: bool,
) -> None:
    """Two pinned RPMs may share exact headers, not silently replace them."""
    first_asset = _asset()
    second_asset = replace(first_asset, name="llvm-devel-22.1.8-4.fc44.x86_64.rpm")
    identity = replace(
        _identity(tmp_path), development_assets=(first_asset, second_asset)
    )
    extracts = 0

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        nonlocal extracts
        del stdin, pass_fds
        if arguments[0] == "cpio" and cwd is not None:
            extracts += 1
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            contents = (
                FOREIGN_CONTENT_BYTES
                if conflicting and extracts == 2
                else HEADER_BYTES
            )
            _ = header.write_bytes(contents)
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            _synthetic_hardlinked_members,
        )
        isolated.setattr(
            llvm_development_validation, "_command_bytes", synthetic_cpio
        )
        if conflicting:
            with pytest.raises(
                llvm_development_validation.LlvmDevelopmentProvisionError,
                match="conflicting header",
            ):
                _ = llvm_development_validation.provision_development_identity(
                    tmp_path, identity, downloader=_downloader([])
                )
        else:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert extracts == 2
    assert identity.development_root.exists() != conflicting
    if not conflicting:
        assert (
            identity.development_root / "include/clang/AST/AST.h"
        ).read_bytes() == HEADER_BYTES


@pytest.mark.parametrize("failure", [OSError, shutil.Error, RuntimeError])
def test_rpm_overlay_copy_host_fault_is_typed_and_not_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """A failed header overlay copy cannot leak a raw host exception."""
    identity = _identity(tmp_path)
    fault = failure("overlay copy failed")

    def failing_copytree(
        _source: Path, _destination: Path, **_kwargs: object
    ) -> None:
        raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_cpio_payload",
            _synthetic_hardlinked_payload,
        )
        isolated.setattr(
            llvm_development_validation,
            "_cpio_members",
            _synthetic_hardlinked_members,
        )
        isolated.setattr(
            llvm_development_validation,
            "_command_bytes",
            _synthetic_hardlinked_cpio(tmp_path / "unused", during_copy=True),
        )
        isolated.setattr(shutil, "copytree", failing_copytree)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="LLVM RPM header overlay copy failed",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([])
            )
    assert observed.value.__cause__ is fault
    assert not identity.development_root.exists()


@pytest.mark.skipif(
    os.name != POSIX_OS_NAME, reason="requires POSIX RPM descriptor"
)
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_rpm_decoder_never_reads_replaced_package_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """A late RPM filename swap cannot substitute unverified input bytes."""
    package = tmp_path / PACKAGE_NAME
    _ = package.write_bytes(PACKAGE_BYTES)
    parked = tmp_path / "retained-rpm"
    foreign = tmp_path / "foreign-rpm"
    _ = foreign.write_bytes(FOREIGN_CONTENT_BYTES)
    seen: list[bytes] = []

    def swapped_decoder(
        arguments: list[str], **_options: object
    ) -> sp.CompletedProcess[bytes]:
        del _options
        _ = package.rename(parked)
        if substitution == SYMLINK_SUBSTITUTION:
            _ = package.symlink_to(foreign)
        else:
            _ = foreign.rename(package)
        seen.append(Path(arguments[1]).read_bytes())
        return sp.CompletedProcess(arguments, 0, b"mock CPIO", b"")

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_development_validation.sp, "run", swapped_decoder)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging content mismatch",
        ):
            _ = llvm_development_validation._cpio_payload(  # ruff: ignore[private-member-access]
                package, PACKAGE_BYTES
            )
    assert seen == [PACKAGE_BYTES]
    assert parked.read_bytes() == PACKAGE_BYTES
    remaining = foreign if substitution == SYMLINK_SUBSTITUTION else package
    assert remaining.read_bytes() == FOREIGN_CONTENT_BYTES


def _cpio_stage_swap_process(
    package: Path,
    *,
    foreign: Path,
    substitution: str,
    swaps: list[bool],
) -> Callable[..., sp.CompletedProcess[bytes]]:
    """Simulate tool startup after a late replacement of its cwd pathname.

    Returns:
        A process stub that resolves CPIO cwd after substituting the package.

    """

    def synthetic_process(
        arguments: list[str], **options: object
    ) -> sp.CompletedProcess[bytes]:
        if arguments[:2] == ["cpio", "-idm"]:
            parked = package.parent.parent / "parked-package"
            _ = package.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                _ = package.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(package)
            swaps.append(True)
            cwd = options["cwd"]
            assert isinstance(cwd, Path)
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
        stdout = {
            RPM2CPIO_NAME: b"mock CPIO payload",
            "cpio": b"./usr/include/clang/AST/AST.h\0",
        }.get(arguments[0], b"")
        return sp.CompletedProcess(arguments, 0, stdout, b"")

    return synthetic_process


@pytest.mark.skipif(
    os.name != POSIX_OS_NAME, reason="requires POSIX stage descriptor"
)
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_rpm_extraction_uses_owned_cwd_after_late_package_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """A late CPIO cwd swap must not extract into an unrelated directory."""
    staging = tmp_path / "packages"
    staging.mkdir()
    destination = tmp_path / "development"
    destination.mkdir()
    package = staging / PACKAGE_NAME.removesuffix(".rpm")
    parked = tmp_path / "parked-package"
    foreign = tmp_path / "foreign-package"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(FOREIGN_CONTENT_BYTES)
    swaps: list[bool] = []
    fake_process = _cpio_stage_swap_process(
        package, foreign=foreign, substitution=substitution, swaps=swaps
    )

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_development_validation.sp, "run", fake_process)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging child identity changed",
        ):
            llvm_development_validation._extract_rpm_headers(  # ruff: ignore[private-member-access]
                PACKAGE_BYTES, _asset(), destination, staging=staging
            )
    assert swaps == [True]
    foreign_root = foreign if substitution == SYMLINK_SUBSTITUTION else package
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_CONTENT_BYTES
    assert not (foreign_root / "usr/include").exists()
    assert (parked / "usr/include/clang/AST/AST.h").read_bytes() == HEADER_BYTES
    assert not (destination / "include").exists()


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

    def synthetic_payload(_rpm: Path, _expected: bytes) -> bytes:
        del _rpm, _expected
        if swap_phase == "tool-fault":
            swap_package()
            raise OSError("synthetic RPM tool fault after stage swap")
        return b"cpio"

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        del stdin, pass_fds
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


@pytest.mark.parametrize("cleanup", ["package", "staging"])
@pytest.mark.parametrize("failure_type", [OSError, shutil.Error, RuntimeError])
def test_llvm_development_cleanup_host_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup: str,
    failure_type: type[Exception],
) -> None:
    """Failed cleanup must retain host cause behind the provisioning boundary."""
    identity = _identity(tmp_path)
    fault = failure_type("synthetic development cleanup failure")
    native_rmtree = shutil.rmtree
    target = (
        PACKAGE_NAME.removesuffix(".rpm")
        if cleanup == "package"
        else f"llvm-development-provision-{LINUX_PLATFORM}"
    )

    def fail_cleanup(path: Path, *args: object, **kwargs: object) -> None:
        if path.name == target:
            raise fault
        _ = native_rmtree(path, *args, **kwargs)

    def synthetic_cpio(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        stdin: bytes | None = None,
        pass_fds: tuple[int, ...] = (),
    ) -> bytes:
        del stdin, pass_fds
        if arguments[0] == "cpio" and cwd is not None:
            header = cwd / "usr/include/clang/AST/AST.h"
            header.parent.mkdir(parents=True)
            _ = header.write_bytes(HEADER_BYTES)
        return b""

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "rmtree", fail_cleanup)
        if cleanup == "package":
            isolated.setattr(
                llvm_development_validation,
                "_cpio_payload",
                _synthetic_hardlinked_payload,
            )
            isolated.setattr(
                llvm_development_validation,
                "_cpio_members",
                _synthetic_hardlinked_members,
            )
            isolated.setattr(
                llvm_development_validation, "_command_bytes", synthetic_cpio
            )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="cleanup",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=(
                    None if cleanup == "package" else _extract_headers
                ),
            )
    assert observed.value.__cause__ is fault
    assert identity.development_root.exists() == (cleanup == "staging")
    if cleanup == "staging":
        assert llvm_development_validation.development_root_matches(identity)


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


@pytest.mark.parametrize("change_phase", ["download", "extract"])
@pytest.mark.parametrize("relative_identity", [False, True])
def test_development_provision_relative_root_survives_cwd_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change_phase: str,
    relative_identity: bool,
) -> None:
    """A callback cannot redirect repository staging by changing host cwd."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(tmp_path)
    identity = _identity(Path("checkout") if relative_identity else checkout)
    expected = (
        checkout / identity.development_root.relative_to(Path("checkout"))
        if relative_identity
        else identity.development_root
    )

    def download(_url: str) -> bytes:
        if change_phase == "download":
            monkeypatch.chdir(elsewhere)
        return PACKAGE_BYTES

    def extract(
        data: bytes,
        asset: tidy_toolchain.DevelopmentAsset,
        destination: Path,
        *,
        staging: Path,
    ) -> None:
        _extract_headers(data, asset, destination, staging=staging)
        if change_phase == "extract":
            monkeypatch.chdir(elsewhere)

    result = llvm_development_validation.provision_development_identity(
        Path("checkout"), identity, downloader=download, extractor=extract
    )
    assert result == expected
    assert (result / "include/clang/AST/AST.h").read_bytes() == HEADER_BYTES
    assert not (elsewhere / "checkout").exists()
    assert not (checkout / ".temp/llvm-development-provision-linux-x86_64").exists()


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


@pytest.mark.parametrize("phase", ["destination_setup", "final_publish"])
@pytest.mark.parametrize("mutation", ["overwrite", "remove", "add", "marker"])
def test_development_publication_rejects_late_staged_header_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    phase: str,
) -> None:
    """Neither destination setup nor final rename may publish changed bytes."""
    identity = _identity(tmp_path)
    staged_root = (
        tmp_path / f".temp/llvm-development-provision-{LINUX_PLATFORM}/development"
    )
    marker = staged_root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    header = staged_root / "include/clang/AST/AST.h"
    native_check = llvm_development_validation._require_development_destination
    changed = False
    marker_checks = 0

    def mutate_after_marker(path: Path) -> None:
        nonlocal changed, marker_checks
        native_check(path)
        if marker.is_file():
            marker_checks += 1
        trigger = 1 if phase == "destination_setup" else 3
        if marker_checks == trigger and not changed:
            if mutation == "overwrite":
                _ = header.write_bytes(FOREIGN_CONTENT_BYTES)
            elif mutation == "remove":
                header.unlink()
            elif mutation == "add":
                _ = (header.parent / "Unexpected.h").write_bytes(FOREIGN_CONTENT_BYTES)
            else:
                _ = marker.write_bytes(marker.read_bytes()[:-1] + b"!")
            changed = True

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_require_development_destination",
            mutate_after_marker,
        )
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staged headers changed|staged marker changed",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert changed
    assert not identity.development_root.exists()


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
    marker = (
        root / f".temp/llvm-development-provision-{LINUX_PLATFORM}/development"
        / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
    )
    native_validate = llvm_development_validation._reject_include_symlinks
    swapped = False

    def swap_after_final_check(
        include_root: Path, *, require_single_link: bool = False
    ) -> None:
        nonlocal swapped
        native_validate(include_root, require_single_link=require_single_link)
        if require_single_link and marker.is_file() and not swapped:
            swapped = True
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
    assert swapped
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
    native_publish = llvm_development_validation._rename_linux_development_no_replace
    attacked = False

    def swap_at_rename(
        source: str,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        nonlocal attacked
        if source == "development" and target == identity.development_root.name:
            native_rename(destination_parent, parked)
            _ = destination_parent.symlink_to(outside, target_is_directory=True)
            attacked = True
        native_publish(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_rename_linux_development_no_replace",
            swap_at_rename,
        )
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
            match=(
                "destination (parent descriptor does not match"
                "|physical parent descriptor failed)"
            ),
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

    class ForeignOSError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("host rename error must not be formatted")

    fault = ForeignOSError("synthetic publication failure")

    def broken_rename(
        source: str,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        del source, target, src_dir_fd, dst_dir_fd
        raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_rename_linux_development_no_replace",
            broken_rename,
        )
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
    native_publish = llvm_development_validation._rename_linux_development_no_replace
    native_close = os.close
    closing: set[int] = set()
    fault = OSError("synthetic publication parent close fault")

    def capture_final_rename(
        source: str,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        if source == "development" and target == identity.development_root.name:
            selected = src_dir_fd if parent == "staging" else dst_dir_fd
            closing.add(selected)
        native_publish(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def fault_final_parent_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in closing:
            closing.remove(descriptor)
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_rename_linux_development_no_replace",
            capture_final_rename,
        )
        isolated.setattr(os, "close", fault_final_parent_close)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="parent descriptor close failed",
        ) as observed:
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert observed.value.__cause__ is fault
    assert not closing
    assert (identity.development_root / "include/clang/AST/AST.h").read_bytes() == HEADER_BYTES


@pytest.mark.parametrize("phase", ["after-rename", "after-cleanup"])
@pytest.mark.parametrize(
    "mutation", ["overwrite-header", "remove-header", "insert-header", "rewrite-marker"]
)
def test_development_publication_rejects_late_published_content_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    mutation: str,
) -> None:
    """A late write cannot turn a changed published kit into a success receipt."""
    if phase == "after-rename" and os.name != "posix":
        pytest.skip("Linux descriptor-relative publication boundary")
    identity = _identity(tmp_path)
    native_publish = llvm_development_validation._rename_linux_development_no_replace
    native_rmtree = shutil.rmtree
    stage_name = f"llvm-development-provision-{LINUX_PLATFORM}"
    changed = False

    def mutate_published_root() -> None:
        nonlocal changed
        assert not changed
        root = identity.development_root
        header = root / "include/clang/AST/AST.h"
        marker = root / llvm_development_validation.LLVM_DEVELOPMENT_MARKER
        if mutation == "overwrite-header":
            _ = header.write_bytes(b"x" * len(HEADER_BYTES))
        elif mutation == "remove-header":
            header.unlink()
        elif mutation == "insert-header":
            _ = (root / "include/foreign.h").write_bytes(FOREIGN_CONTENT_BYTES)
        else:
            _ = marker.write_bytes(b"x" * marker.stat().st_size)
        changed = True

    def mutate_after_rename(
        source: str,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        native_publish(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
        if phase == "after-rename":
            mutate_published_root()

    def mutate_after_cleanup(path: Path, *args: object, **kwargs: object) -> None:
        _ = native_rmtree(path, *args, **kwargs)
        if phase == "after-cleanup" and path.name == stage_name:
            mutate_published_root()

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_development_validation,
            "_rename_linux_development_no_replace",
            mutate_after_rename,
        )
        isolated.setattr(shutil, "rmtree", mutate_after_cleanup)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="published|marker|headers|publication",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert changed


def test_development_publication_rejects_late_same_byte_root_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new inode with identical contents cannot inherit a publication receipt."""
    identity = _identity(tmp_path)
    native_rmtree = shutil.rmtree
    parked = tmp_path / "parked-published-development"
    replaced = False

    def substitute_root_during_cleanup(
        path: Path, *args: object, **kwargs: object
    ) -> None:
        nonlocal replaced
        _ = native_rmtree(path, *args, **kwargs)
        if path.name == f"llvm-development-provision-{LINUX_PLATFORM}":
            original = identity.development_root
            original.rename(parked)
            _ = shutil.copytree(parked, original)
            replaced = True

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "rmtree", substitute_root_during_cleanup)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="staging child identity changed",
        ):
            _ = llvm_development_validation.provision_development_identity(
                tmp_path,
                identity,
                downloader=_downloader([]),
                extractor=_extract_headers,
            )
    assert replaced
    assert (parked / "include/clang/AST/AST.h").read_bytes() == HEADER_BYTES
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
            or (location == "destination" and path == fault_path.name)
        ):
            raise fault
        native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", faulty_mkdir)
        if os.name == "posix":
            isolated.setattr(os, "mkdir", faulty_native_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="creation failed|physical parent descriptor failed",
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
    native_os_mkdir = os.mkdir
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

    def fault_native_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if path == child.name and dir_fd is not None:
            raise fault
        native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        if os.name == "posix":
            isolated.setattr(os, "mkdir", fault_native_mkdir)  # pyright: ignore[reportUnreachable]
        else:
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


@pytest.mark.parametrize("omission", ["child", "visit"])
def test_rpm_header_receipt_rejects_incomplete_native_walk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omission: str,
) -> None:
    """Physical RPM headers cannot disappear from the walk used for admission."""
    include = tmp_path / "include"
    directory = include / "clang/AST"
    directory.mkdir(parents=True)
    _ = (directory / "AST.h").write_bytes(HEADER_BYTES)
    _ = (include / "surprise.h").write_bytes(FOREIGN_CONTENT_BYTES)
    native_walk = Path.walk

    def omit_member(
        self: Path, *, on_error: Callable[[OSError], object] | None = None
    ) -> Iterator[tuple[Path, list[str], list[str]]]:
        for walked, folders, files in native_walk(self, on_error=on_error):
            if omission == "child" and walked == include:
                files.remove("surprise.h")
            if omission == "visit" and walked != include:
                continue
            yield walked, folders, files

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "walk", omit_member)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="walk|scan|inventory|missing",
        ):
            _ = llvm_development_validation._header_tree_receipt(include)


def test_development_readiness_rejects_suppressed_directory_scan_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable header subtree cannot silently disappear from reuse checks."""
    identity = _provisioned_identity(tmp_path)
    inaccessible = identity.development_root / "include/clang"
    native_scandir = os.scandir
    fault = PermissionError("synthetic unreadable LLVM header directory")

    def fail_scandir(path: object) -> object:
        if isinstance(path, (str, bytes, os.PathLike)) and Path(path) == inaccessible:
            raise fault
        return native_scandir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "scandir", fail_scandir)
        assert not llvm_development_validation.development_root_matches(identity)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="scan",
        ) as observed:
            llvm_development_validation._reject_include_symlinks(
                identity.development_root, require_single_link=True
            )
    assert observed.value.__cause__ is fault


@pytest.mark.parametrize("location", ["include", "root"])
@pytest.mark.parametrize("member_kind", ["symlink", "hardlink", "fifo"])
def test_development_readiness_rejects_unlisted_nonphysical_members(
    tmp_path: Path,
    member_kind: str,
    location: str,
) -> None:
    """A trusted marker cannot hide new linked or special package members."""
    identity = _provisioned_identity(tmp_path)
    outside = tmp_path / "external-header"
    _ = outside.write_bytes(FOREIGN_CONTENT_BYTES)
    parent = (
        identity.development_root / "include"
        if location == "include"
        else identity.development_root
    )
    member = parent / "unexpected-header.h"
    try:
        if member_kind == "symlink":
            _ = member.symlink_to(outside)
        elif member_kind == "hardlink":
            os.link(outside, member)
        else:
            if not hasattr(os, "mkfifo"):
                pytest.skip("FIFO creation unavailable")
            os.mkfifo(member)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"filesystem member unavailable: {error}")

    assert not llvm_development_validation.development_root_matches(identity)
    assert outside.read_bytes() == FOREIGN_CONTENT_BYTES


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

    def unexpected_cpio(path: Path, _expected: bytes) -> bytes:
        del _expected
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

    def unexpected_cpio(path: Path, _expected: bytes) -> bytes:
        del _expected
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
        "argv_list_subclass",
        "status_subclass",
        "bytes_stdout_subclass",
        "bytes_stderr_subclass",
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
        elif malformed == "argv_list_subclass":

            class ForeignList(list[str]):
                pass

            returned_argv = ForeignList(argv)
        elif malformed == "status_subclass":

            class ForeignInt(int):
                pass

            status = ForeignInt(0)
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
        elif malformed == "bytes_stdout_subclass":

            class ForeignBytes(bytes):
                pass

            stdout = ForeignBytes(b"verified")
        elif malformed == "bytes_stderr_subclass":

            class ForeignBytes(bytes):
                pass

            stderr = ForeignBytes(b"")
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


@pytest.mark.parametrize(
    "command",
    [
        ["rpm2cpio", "/proc/self/fd/11"],
        ["cpio", "-it", "--quiet"],
        ["cpio", "-idm", "--quiet", "--no-absolute-filenames", "usr/include/*"],
    ],
)
def test_rpm_command_rejects_success_with_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    """Zero-exit CPIO/RPM warnings cannot certify successful extraction."""

    def diagnostic_run(
        argv: list[str], **_kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        assert argv == command
        return sp.CompletedProcess(argv, 0, b"reviewed", b"archive warning\n")

    monkeypatch.setattr(llvm_development_validation.sp, "run", diagnostic_run)
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="diagnostics",
    ):
        _ = llvm_development_validation._command_bytes(command)


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


@pytest.mark.parametrize("boundary", ["tool", "path", "download"])
def test_llvm_development_host_failure_does_not_read_foreign_class_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    """Untrusted host exception metaclasses cannot hijack error reporting."""

    class HostileMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name == "__name__":
                raise AssertionError("foreign exception metadata was evaluated")
            return super().__getattribute__(name)

    class ForeignHostError(OSError, metaclass=HostileMeta):
        def __str__(self) -> str:
            raise AssertionError("foreign exception text was formatted")

    fault = ForeignHostError("foreign host failure")

    def fail(*_args: object, **_kwargs: object) -> bool:
        raise fault

    if boundary == "tool":
        monkeypatch.setattr(llvm_development_validation.sp, "run", fail)
    elif boundary == "download":
        monkeypatch.setattr(
            llvm_development_validation.urllib.request, "urlopen", fail
        )

    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="ForeignHostError",
    ) as observed:
        if boundary == "tool":
            _ = llvm_development_validation._command_bytes(["cpio", "-it"])
        elif boundary == "path":
            _ = llvm_development_validation._preflight_path_status(
                tmp_path, fail, "staging"
            )
        else:
            _ = llvm_development_validation._download_asset(
                "https://example.invalid/reviewed.rpm",
                expected_size_bytes=len(PACKAGE_BYTES),
            )
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


@pytest.mark.parametrize("phase", ["open", "read"])
def test_llvm_development_download_normalizes_truncated_http_response(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """HTTP framing failures retain their cause inside the typed RPM boundary."""
    fault = http.client.IncompleteRead(b"partial", len(PACKAGE_BYTES))

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, _kind: object, _error: object, _trace: object) -> bool:
            return False

        def read(self, _limit: int) -> bytes:
            raise fault

    def open_response(*_args: object, **_kwargs: object) -> Response:
        if phase == "open":
            raise fault
        return Response()

    monkeypatch.setattr(
        llvm_development_validation.urllib.request, "urlopen", open_response
    )
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="IncompleteRead",
    ) as observed:
        _ = llvm_development_validation._download_asset(
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


@pytest.mark.skipif(os.name != "posix", reason="requires Linux directory descriptors")
def test_development_final_rename_preserves_late_empty_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty foreign directory inserted after the absence check survives."""
    staged = tmp_path / "staging" / "development"
    staged.mkdir(parents=True)
    destination = tmp_path / "installed" / "development"
    destination.parent.mkdir()
    original = staged.stat()
    destination_parent = destination.parent.stat()
    native_stat = os.stat
    inserted: tuple[int, int] | None = None

    def insert_after_check(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes] | int,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal inserted
        try:
            return native_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        except FileNotFoundError:
            if (
                path == destination.name
                and dir_fd is not None
                and (os.fstat(dir_fd).st_dev, os.fstat(dir_fd).st_ino)
                == (destination_parent.st_dev, destination_parent.st_ino)
                and inserted is None
            ):
                destination.mkdir()
                status = destination.lstat()
                inserted = (status.st_dev, status.st_ino)
            raise

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "stat", insert_after_check)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination.*occupied",
        ):
            llvm_development_validation._publish_development_root(  # pyright: ignore[reportPrivateUsage]
                staged, destination, (original.st_dev, original.st_ino),
                attest=lambda: None,
            )
    assert inserted is not None
    current = destination.lstat()
    assert (current.st_dev, current.st_ino) == inserted
    assert staged.is_dir()


@pytest.mark.parametrize("previously_provisioned", [False, True])
@pytest.mark.parametrize("via_parent_traversal", [False, True])
def test_development_provision_rejects_identity_from_other_checkout(
    tmp_path: Path, previously_provisioned: bool, via_parent_traversal: bool
) -> None:
    """The requested checkout cannot provision or reuse another root's kit."""
    checkout = tmp_path / "selected-checkout"
    foreign = tmp_path / "foreign-checkout"
    checkout.mkdir()
    foreign.mkdir()
    identity = _identity(foreign)
    if previously_provisioned:
        _ = llvm_development_validation.provision_development_identity(
            foreign, identity, downloader=_downloader([]), extractor=_extract_headers
        )
    if via_parent_traversal:
        identity = replace(
            identity,
            development_root=(
                checkout / ".." / foreign.name
                / identity.development_root.relative_to(foreign)
            ),
        )
    downloads: list[str] = []
    with pytest.raises(
        llvm_development_validation.LlvmDevelopmentProvisionError,
        match="checkout|root|destination",
    ):
        _ = llvm_development_validation.provision_development_identity(
            checkout,
            identity,
            downloader=_downloader(downloads),
            extractor=_extract_headers,
        )
    assert not downloads
    assert not (checkout / ".temp").exists()
    if not previously_provisioned:
        assert not identity.development_root.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("close_before_fault", [False, True])
def test_development_parent_walk_close_fault_closes_new_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, close_before_fault: bool
) -> None:
    """A parent close fault cannot leak the newly opened next directory."""
    target = tmp_path / "nested" / "kit"
    target.parent.mkdir()
    native_open = os.open
    native_close = os.close
    new_children: list[int] = []
    old_parents: set[int] = set()
    fault = OSError("synthetic parent-walk close failure")

    def track_child_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        child = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == "nested" and dir_fd is not None:
            new_children.append(child)
            old_parents.add(dir_fd)
        return child

    def fail_old_parent_close(descriptor: int) -> None:
        if descriptor in old_parents:
            old_parents.remove(descriptor)
            if close_before_fault:
                native_close(descriptor)
            raise fault
        native_close(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_child_open)
        isolated.setattr(os, "close", fail_old_parent_close)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="physical parent descriptor failed",
        ) as observed:
            _ = llvm_development_validation._open_physical_publication_parent(  # pyright: ignore[reportPrivateUsage]
                target, "staging"
            )
    assert observed.value.__cause__ is fault
    assert len(new_children) == 1
    assert not old_parents
    try:
        with pytest.raises(OSError):
            _ = os.fstat(new_children[0])
    finally:
        with suppress(OSError):
            native_close(new_children[0])


@pytest.mark.skipif(os.name != "posix", reason="requires pinned POSIX mkdir")
@pytest.mark.parametrize("replacement", ["symlink", "physical"])
def test_development_child_stage_mkdir_stays_on_owned_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A late staging swap must not create the child in a foreign parent."""
    root = tmp_path / "checkout"
    root.mkdir()
    identity = _identity(root)
    foreign, sentinel = _external_sentinel(tmp_path)
    staging = root / f".temp/llvm-development-provision-{LINUX_PLATFORM}"
    owned = tmp_path / "parked-original-staging"
    native_mkdir = os.mkdir
    swapped = False
    downloads: list[str] = []

    def swap_before_child_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (
            path == staging / "development"
            or (path == "development" and dir_fd is not None)
        ):
            _ = staging.rename(owned)
            if replacement == "symlink":
                _ = staging.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staging)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_before_child_mkdir)
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
    assert swapped
    foreign_root = foreign if replacement == "symlink" else staging
    assert set(foreign_root.iterdir()) == {
        sentinel if replacement == "symlink" else staging / sentinel.name
    }
    assert not downloads
    assert (owned / "development").is_dir()
    assert not identity.development_root.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires pinned POSIX mkdir")
@pytest.mark.parametrize("replacement", ["symlink", "physical"])
def test_development_destination_parent_mkdir_stays_on_owned_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A raced ancestor cannot receive a new development destination parent."""
    root = tmp_path / "checkout"
    root.mkdir()
    dependencies = root / ".dependencies"
    dependencies.mkdir()
    identity = _identity(root)
    foreign, sentinel = _external_sentinel(tmp_path)
    owned = tmp_path / "parked-dependencies"
    native_mkdir = os.mkdir
    swapped = False

    def swap_before_parent_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (
            path == identity.development_root.parent
            or (path == "llvm-dev" and dir_fd is not None)
        ):
            _ = dependencies.rename(owned)
            if replacement == "symlink":
                _ = dependencies.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(dependencies)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_before_parent_mkdir)
        with pytest.raises(
            llvm_development_validation.LlvmDevelopmentProvisionError,
            match="destination",
        ):
            _ = llvm_development_validation.provision_development_identity(
                root, identity, downloader=_downloader([]), extractor=_extract_headers
            )
    assert swapped
    foreign_root = foreign if replacement == "symlink" else dependencies
    assert set(foreign_root.iterdir()) == {
        sentinel if replacement == "symlink" else dependencies / sentinel.name
    }
    assert (owned / "llvm-dev").is_dir()
    assert not identity.development_root.exists()
