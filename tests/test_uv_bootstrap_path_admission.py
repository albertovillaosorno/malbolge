# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Regression tests for physical uv executable provisioning paths.
# - Must-Not:
#   - Download pinned tools or execute a real foreign binary.
# - Allows:
#   - Inputs: synthetic repository roots and fault-injected uv downloads.
#   - Outputs: deterministic fail-closed provisioning evidence.
#   - Side effects: only temporary pytest paths.
# - Split-When:
#   - A new provisioning responsibility requires its own test suite.
# - Merge-When:
#   - Another suite owns this exact physical uv path admission contract.
# - Summary:
#   - Reject redirected or multiply linked uv targets and staging paths.
#

"""Physical uv bootstrap path admission regressions."""

from __future__ import annotations

import http.client
import io
import json
import lzma
import os
import stat
import struct
import tarfile
import warnings
import zipfile
import zlib
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Self, cast

import pytest
from compression import zstd
from scripts.bootstrap import python_validation

if TYPE_CHECKING:
    from collections.abc import Callable

PLATFORM_ID = "linux-x86_64"
BINARY = b"synthetic-pinned-uv"
PRESERVED = b"preserve"
SYMBOLIC = "symbolic"
VERSION_FLAG = "--version"
ZIP_ARCHIVE_KIND = "zip"
FIRST_SELECTED = "first"
MINI_ARCHIVE_MEMBER_LIMIT = 4


def _mock_uv(monkeypatch: pytest.MonkeyPatch) -> python_validation.UvArtifact:
    artifact = python_validation.uv_artifact(PLATFORM_ID)

    def fake_download(selected: python_validation.UvArtifact) -> bytes:
        assert selected == artifact
        return BINARY

    def fake_member(
        data: bytes, selected: python_validation.UvArtifact
    ) -> bytes:
        assert data == BINARY
        assert selected == artifact
        return BINARY

    def fake_run(command: list[str]) -> str:
        assert command[-1] == VERSION_FLAG
        return f"uv {artifact.version}"

    monkeypatch.setattr(
        python_validation, "_download_uv_archive", fake_download
    )
    monkeypatch.setattr(python_validation, "_uv_member_bytes", fake_member)
    monkeypatch.setattr(python_validation, "_run", fake_run)
    return artifact


@pytest.mark.parametrize("reuse", [False, True])
def test_uv_relative_root_stays_pinned_when_callback_changes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, reuse: bool
) -> None:
    """A callback cannot redirect a relative checkout's uv target or receipt."""
    artifact = _mock_uv(monkeypatch)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    expected = python_validation.uv_executable(artifact, checkout)
    if reuse:
        expected.parent.mkdir(parents=True)
        _ = expected.write_bytes(BINARY)
        callback = python_validation._run

        def change_during_probe(command: list[str]) -> str:
            output = callback(command)
            monkeypatch.chdir(outside)
            return output

        monkeypatch.setattr(python_validation, "_run", change_during_probe)
    else:
        callback_download = python_validation._download_uv_archive

        def change_during_download(
            selected: python_validation.UvArtifact,
        ) -> bytes:
            content = callback_download(selected)
            monkeypatch.chdir(outside)
            return content

        monkeypatch.setattr(
            python_validation, "_download_uv_archive", change_during_download
        )
    monkeypatch.chdir(tmp_path)
    result = python_validation.ensure_uv(Path("checkout"), platform_id=PLATFORM_ID)
    assert result == expected
    assert expected.read_bytes() == BINARY
    assert not (outside / "checkout").exists()


def _symlink(link: Path, destination: Path, *, directory: bool) -> None:
    try:
        _ = link.symlink_to(destination, target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symbolic links unsupported: {error}")


@pytest.mark.parametrize("component", ["dependencies", "uv", "version", "bin"])
def test_uv_rejects_linked_provision_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
) -> None:
    """An alias in the destination ancestry cannot receive uv bytes."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    paths = {
        "dependencies": root / ".dependencies",
        "uv": root / ".dependencies" / "uv",
        "version": root / ".dependencies" / "uv" / artifact.version,
        "bin": executable.parent,
    }
    link = paths[component]
    link.parent.mkdir(parents=True, exist_ok=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _symlink(link, foreign, directory=True)

    with pytest.raises(python_validation.ProvisionError, match=r"uv.*redirect"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert list(foreign.iterdir()) == []


def test_uv_does_not_create_directories_through_late_parent_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late symlink must not receive newly created provisioning directories."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    admitted = python_validation._admit_uv_provision_path
    swapped = False

    def redirect_after_first_check(
        path: Path, *, directory: bool = False, required: bool = False
    ) -> os.stat_result | None:
        nonlocal swapped
        result = admitted(path, directory=directory, required=required)
        if path == executable.parent and directory and not swapped:
            swapped = True
            _symlink(root / ".dependencies", foreign, directory=True)
        return result

    monkeypatch.setattr(
        python_validation, "_admit_uv_provision_path", redirect_after_first_check
    )
    with pytest.raises(python_validation.ProvisionError):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert swapped
    assert list(foreign.iterdir()) == []


def test_uv_does_not_write_through_swapped_stage_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A parent replaced after path admission must not receive staged bytes."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    retained = tmp_path / "retained-bin"
    admitted = python_validation._admit_uv_provision_path
    native_write = os.write
    swapped = False
    wrote_foreign = False

    def swap_after_admission(
        path: Path, *, directory: bool = False, required: bool = False
    ) -> os.stat_result | None:
        nonlocal swapped
        result = admitted(path, directory=directory, required=required)
        if path == stage and not swapped:
            swapped = True
            _ = executable.parent.rename(retained)
            _symlink(executable.parent, foreign, directory=True)
        return result

    def watch_write(descriptor: int, payload: bytes) -> int:
        nonlocal wrote_foreign
        if (foreign / stage.name).exists():
            wrote_foreign = True
        return native_write(descriptor, payload)

    monkeypatch.setattr(
        python_validation, "_admit_uv_provision_path", swap_after_admission
    )
    monkeypatch.setattr(os, "write", watch_write)
    with pytest.raises(python_validation.ProvisionError):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert swapped
    assert not wrote_foreign
    assert list(foreign.iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_parent_swap_after_descriptor_pin_does_not_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late parent swap after pinning cannot redirect the staging open."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    retained = tmp_path / "retained-bin"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    native_open = os.open
    swapped = False

    def swap_before_stage_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if os.fspath(path) == stage.name and dir_fd is not None:
            swapped = True
            _ = executable.parent.rename(retained)
            _symlink(executable.parent, foreign, directory=True)
        if dir_fd is not None:
            return native_open(path, flags, mode, dir_fd=dir_fd)
        return native_open(path, flags, mode)

    monkeypatch.setattr(os, "open", swap_before_stage_open)
    with pytest.raises(python_validation.ProvisionError, match="uv staging"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert swapped
    assert list(foreign.iterdir()) == []
    assert (retained / stage.name).read_bytes() == b""


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_rejects_forged_physical_parent_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An opened foreign directory cannot impersonate the selected UV bin."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    python_validation.uv_executable(artifact, root).parent.mkdir(parents=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    native_open = os.open
    injected: list[int] = []

    def forged_parent_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(path) == "bin" and dir_fd is not None:
            descriptor = native_open(foreign, os.O_RDONLY | os.O_DIRECTORY)
            injected.append(descriptor)
            return descriptor
        if dir_fd is not None:
            return native_open(path, flags, mode, dir_fd=dir_fd)
        return native_open(path, flags, mode)

    monkeypatch.setattr(os, "open", forged_parent_open)
    with pytest.raises(
        python_validation.ProvisionError, match="parent descriptor does not match"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert len(injected) == 1
    assert list(foreign.iterdir()) == []
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = os.fstat(injected[0])


def test_uv_rejects_non_directory_provision_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-directory bootstrap parent gets a typed error before writing."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    _ = (root / ".dependencies").write_bytes(PRESERVED)

    with pytest.raises(
        python_validation.ProvisionError, match=r"uv.*directory"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert (root / ".dependencies").read_bytes() == PRESERVED


@pytest.mark.parametrize("link_kind", [SYMBOLIC, "hard"])
def test_uv_rejects_linked_installed_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """A foreign executable with matching --version is not an admitted tool."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    foreign = tmp_path / "foreign-uv"
    _ = foreign.write_bytes(PRESERVED)
    if link_kind == SYMBOLIC:
        _symlink(executable, foreign, directory=False)
    else:
        try:
            os.link(foreign, executable)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hard links unsupported: {error}")

    with pytest.raises(
        python_validation.ProvisionError, match=r"uv.*(?:redirect|link)"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert foreign.read_bytes() == PRESERVED


@pytest.mark.parametrize("link_kind", [SYMBOLIC, "hard"])
def test_uv_rejects_linked_temporary_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """Preexisting uv.tmp links never overwrite their foreign targets."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    stage = executable.with_name(f"{executable.name}.tmp")
    foreign = tmp_path / "foreign-uv-stage"
    _ = foreign.write_bytes(PRESERVED)
    if link_kind == SYMBOLIC:
        _symlink(stage, foreign, directory=False)
    else:
        try:
            os.link(foreign, stage)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hard links unsupported: {error}")

    with pytest.raises(
        python_validation.ProvisionError,
        match=r"uv.*(?:staging|link|redirect)",
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert foreign.read_bytes() == PRESERVED
    assert not executable.exists()


def test_uv_rejects_preexisting_regular_temporary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale uv.tmp is never truncated or silently claimed as private."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    stage = executable.with_name(f"{executable.name}.tmp")
    _ = stage.write_bytes(PRESERVED)

    with pytest.raises(python_validation.ProvisionError, match="staging path"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert stage.read_bytes() == PRESERVED
    assert not executable.exists()


def test_uv_rejects_forged_staging_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign os.open descriptor cannot receive a pinned uv payload."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    stage = executable.with_name(f"{executable.name}.tmp")
    foreign = tmp_path / "foreign-uv"
    _ = foreign.write_bytes(PRESERVED)
    opened: list[int] = []
    original_open = os.open

    def forged_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(path) in (os.fspath(stage), stage.name):
            descriptor = original_open(foreign, os.O_WRONLY)
            opened.append(descriptor)
            return descriptor
        if dir_fd is not None:
            return original_open(path, flags, mode, dir_fd=dir_fd)
        return original_open(path, flags, mode)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(
        python_validation.ProvisionError, match="uv staging descriptor"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert foreign.read_bytes() == PRESERVED
    assert not stage.exists()
    assert not executable.exists()
    assert len(opened) == 1
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = os.fstat(opened[0])


def test_uv_rejects_staging_name_swapped_during_chmod(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An attacker cannot promote a replacement name after descriptor write."""
    if not hasattr(os, "fchmod"):
        pytest.skip("fchmod unavailable on this platform")
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    stage = executable.with_name(f"{executable.name}.tmp")
    retained = tmp_path / "original-stage"
    foreign = tmp_path / "foreign-uv"
    _ = foreign.write_bytes(PRESERVED)
    original_fchmod = os.fchmod

    def swap_stage(descriptor: int, mode: int) -> None:
        original_fchmod(descriptor, mode)
        _ = stage.replace(retained)
        _symlink(stage, foreign, directory=False)

    monkeypatch.setattr(os, "fchmod", swap_stage)
    with pytest.raises(
        python_validation.ProvisionError, match="uv staging changed"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert foreign.read_bytes() == PRESERVED
    assert retained.read_bytes() == BINARY
    assert stage.is_symlink()
    assert not executable.exists()


@pytest.mark.parametrize("predicate", ["is_symlink", "is_junction"])
def test_uv_rejects_nonnative_provision_directory_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    predicate: str,
) -> None:
    """A nonboolean parent link status must stop before a download or write."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    original = getattr(Path, predicate)

    def forged(path: Path) -> bool:
        if path == root:
            return cast("bool", cast("object", 0))
        return cast("bool", original(path))

    monkeypatch.setattr(Path, predicate, forged)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert not (root / ".dependencies").exists()


@pytest.mark.parametrize("predicate", ["is_symlink", "is_junction"])
def test_uv_rejects_nonnative_installed_leaf_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    predicate: str,
) -> None:
    """An existing executable cannot be trusted on a false-like host status."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    _ = executable.write_bytes(BINARY)
    original = getattr(Path, predicate)

    def forged(path: Path) -> bool:
        if path == executable:
            return cast("bool", cast("object", 0))
        return cast("bool", original(path))

    monkeypatch.setattr(Path, predicate, forged)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert executable.read_bytes() == BINARY


class _ForeignUvStatus:
    """Foreign status with accurate-looking native metadata values."""

    def __init__(self, observed: os.stat_result) -> None:
        self.st_mode: int = observed.st_mode
        self.st_nlink: int = observed.st_nlink
        self.st_dev: int = observed.st_dev
        self.st_ino: int = observed.st_ino
        self.st_size: int = observed.st_size


def test_uv_rejects_foreign_installed_file_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged leaf lstat values must not authorize execution of installed uv."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    _ = executable.write_bytes(BINARY)
    original = Path.lstat

    def forged(path: Path) -> os.stat_result:
        observed = original(path)
        if path == executable:
            return cast("os.stat_result", cast("object", _ForeignUvStatus(observed)))
        return observed

    monkeypatch.setattr(Path, "lstat", forged)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert executable.read_bytes() == BINARY


def test_uv_rejects_forged_staging_file_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign stat proxy cannot prove staged-executable inode ownership."""
    stage = tmp_path / "uv.tmp"
    _ = stage.write_bytes(BINARY)
    original = Path.lstat
    status = original(stage)

    def forged(path: Path) -> os.stat_result:
        observed = original(path)
        if path == stage:
            return cast("os.stat_result", cast("object", _ForeignUvStatus(observed)))
        return observed

    monkeypatch.setattr(Path, "lstat", forged)
    assert not python_validation._uv_stage_is_owned(
        stage, (status.st_dev, status.st_ino), expected_size=len(BINARY)
    )


def test_uv_types_provision_directory_status_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host filesystem faults cannot escape the typed uv provision boundary."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    original = Path.lstat
    failure = PermissionError("directory status denied")

    def fault(path: Path) -> os.stat_result:
        if path == root:
            raise failure
        return original(path)

    monkeypatch.setattr(Path, "lstat", fault)
    with pytest.raises(python_validation.ProvisionError, match="inspect") as raised:
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert raised.value.__cause__ is failure


@pytest.mark.parametrize("status_kind", ["proxy", "foreign-device", "foreign-mode"])
def test_uv_rejects_nonphysical_new_stage_descriptor_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_kind: str,
) -> None:
    """Forged fstat evidence cannot admit a newly opened uv stage."""
    stage = tmp_path / "uv.tmp"
    original = os.fstat
    observed_fds: list[int] = []

    def forged_status(descriptor: int) -> os.stat_result:
        observed = original(descriptor)
        if stat.S_ISDIR(observed.st_mode):
            return observed
        observed_fds.append(descriptor)
        if status_kind == "proxy":
            return cast("os.stat_result", cast("object", _ForeignUvStatus(observed)))
        if status_kind == "foreign-device":
            proxy = _ForeignUvStatus(observed)
            proxy.st_dev = cast("int", cast("object", False))
            return cast("os.stat_result", cast("object", proxy))
        native_fields = list(observed)
        native_fields[0] = 0o020000  # Character device, not a regular file.
        return os.stat_result(native_fields)

    monkeypatch.setattr(os, "fstat", forged_status)
    with pytest.raises(
        python_validation.ProvisionError,
        match="staging descriptor",
    ):
        _ = python_validation._write_verified_uv_binary(
            stage, BINARY, windows=True
        )
    assert observed_fds
    assert stage.read_bytes() == b""
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = original(observed_fds[-1])


class _UvExecutableBytesSubclass(bytes):
    """A byte-compatible object does not constitute native executable data."""


@pytest.mark.parametrize(
    "payload",
    [bytearray(BINARY), memoryview(BINARY), _UvExecutableBytesSubclass(BINARY)],
)
def test_uv_staging_rejects_foreign_executable_bytes_before_file_creation(
    tmp_path: Path,
    payload: object,
) -> None:
    """A fake extractor cannot write a nonnative executable payload."""
    stage = tmp_path / "uv.tmp"
    with pytest.raises(python_validation.ProvisionError, match="native bytes"):
        _ = python_validation._write_verified_uv_binary(
            stage, cast("bytes", payload), windows=True
        )
    assert not stage.exists()

def test_uv_rejects_forged_complete_stage_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reported full write cannot publish different executable bytes."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    stage = executable.with_name(f"{executable.name}.tmp")
    native_write = os.write

    def forged_write(descriptor: int, payload: bytes) -> int:
        corrupted = b"!" + payload[1:]
        assert native_write(descriptor, corrupted) == len(corrupted)
        return len(payload)

    monkeypatch.setattr(os, "write", forged_write)
    with pytest.raises(
        python_validation.ProvisionError, match=r"uv staging.*bytes"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert not executable.exists()
    assert not stage.exists()


def test_uv_rejects_stage_mutation_during_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-size mutation during fchmod cannot reach the published tool."""
    if not hasattr(os, "fchmod") or not hasattr(os, "pwrite"):
        pytest.skip("POSIX descriptor mutation unavailable")
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    stage = executable.with_name(f"{executable.name}.tmp")
    native_fchmod = os.fchmod
    native_pwrite = os.pwrite

    def mutate_stage(descriptor: int, mode: int) -> None:
        native_fchmod(descriptor, mode)
        assert native_pwrite(descriptor, b"!", 0) == 1

    monkeypatch.setattr(os, "fchmod", mutate_stage)
    with pytest.raises(
        python_validation.ProvisionError, match=r"uv staging.*bytes"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert not executable.exists()
    assert not stage.exists()


def test_uv_rejects_mutation_after_stage_descriptor_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A private stage changed before promotion is not the pinned executable."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    original_admit = python_validation._require_uv_destination_absent

    def mutate_after_write(target: Path) -> None:
        original_admit(target)
        if stage.is_file():
            with stage.open("r+b") as stream:
                assert stream.write(b"!") == 1

    monkeypatch.setattr(
        python_validation, "_require_uv_destination_absent", mutate_after_write
    )
    with pytest.raises(
        python_validation.ProvisionError, match=r"uv staging.*bytes"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert not executable.exists()
    assert not stage.exists()


@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("mutation", ["inode-swap", "in-place"])
def test_uv_rejects_executable_change_during_version_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    installed: bool,
    mutation: str,
) -> None:
    """Version output cannot endorse a different executable after the probe."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    preserved = tmp_path / "original-uv"
    if installed:
        executable.parent.mkdir(parents=True)
        _ = executable.write_bytes(BINARY)

    def mutate_during_probe(command: list[str]) -> str:
        assert command == [str(executable), VERSION_FLAG]
        if mutation == "inode-swap":
            _ = executable.replace(preserved)
            _ = executable.write_bytes(BINARY)
        else:
            previous = executable.stat()
            with executable.open("r+b") as stream:
                assert stream.write(b"!") == 1
            os.utime(executable, ns=(
                previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000
            ))
        return f"uv {artifact.version}"

    monkeypatch.setattr(python_validation, "_run", mutate_during_probe)
    with pytest.raises(
        python_validation.ProvisionError, match="uv executable changed"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    if mutation == "inode-swap":
        assert preserved.read_bytes() == BINARY
        assert executable.read_bytes() == BINARY
    else:
        assert executable.read_bytes() != BINARY


@pytest.mark.parametrize("member_type", [stat.S_IFLNK, stat.S_IFDIR, stat.S_IFIFO])
def test_uv_zip_rejects_nonregular_member_with_file_name(
    member_type: int,
) -> None:
    """ZIP members named like executables still need regular file metadata."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        member = zipfile.ZipInfo("uv.exe")
        member.create_system = 3
        member.external_attr = (member_type | 0o755) << 16
        archive.writestr(member, BINARY)
    with pytest.raises(
        python_validation.ProvisionError, match="uv zip member must be a regular file"
    ):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


def test_uv_zip_rejects_dos_directory_attribute_without_trailing_slash() -> None:
    """A DOS ZIP directory is not regular merely because its name is a file."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        member = zipfile.ZipInfo("uv.exe")
        member.create_system = 0
        member.external_attr = 0x10
        archive.writestr(member, BINARY)
    with pytest.raises(
        python_validation.ProvisionError, match="uv zip member must be a regular file"
    ):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


def test_uv_zip_rejects_dos_volume_label_with_executable_name() -> None:
    """A DOS volume label is not an ordinary executable archive file."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        member = zipfile.ZipInfo("uv.exe")
        member.create_system = 0
        member.external_attr = 0x08
        archive.writestr(member, BINARY)
    extract = cast(
        "Callable[[bytes, str], bytes]",
        vars(python_validation)["_zip_member_bytes"],
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="uv zip member must be a regular file",
    ):
        _ = extract(output.getvalue(), "uv.exe")


def test_uv_download_normalizes_incomplete_http_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken HTTP body cannot escape the typed downloader boundary."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    failure = http.client.IncompleteRead(b"partial", 12)

    class IncompleteResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            raise failure

    def incomplete_urlopen(*_args: object, **_kwargs: object) -> IncompleteResponse:
        return IncompleteResponse()

    monkeypatch.setattr(python_validation.urllib.request, "urlopen", incomplete_urlopen)
    with pytest.raises(
        python_validation.ProvisionError,
        match="cannot download pinned uv artifact: IncompleteRead",
    ) as raised:
        _ = python_validation._download_uv_archive(artifact)
    assert raised.value.__cause__ is failure


def test_uv_download_does_not_accept_suppressed_response_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A response context cannot erase a failed bounded download read."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    failure = OSError("broken response")

    class SuppressingResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> bool:
            return True

        def read(self, _limit: int) -> bytes:
            raise failure

    def fake_urlopen(*_args: object, **_kwargs: object) -> SuppressingResponse:
        return SuppressingResponse()

    monkeypatch.setattr(python_validation.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(
        python_validation.ProvisionError, match="cannot download pinned uv artifact"
    ) as rejected:
        _ = python_validation._download_uv_archive(artifact)
    assert rejected.value.__cause__ is failure


def test_uv_zip_does_not_accept_suppressed_archive_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ZIP archive context cannot suppress rejected executable metadata."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        info = zipfile.ZipInfo("uv.exe")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o755) << 16
        archive.writestr(info, BINARY)

    monkeypatch.setattr(zipfile.ZipFile, "__exit__", lambda *_args: True)
    with pytest.raises(python_validation.ProvisionError, match="suppressed"):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


def test_uv_tar_does_not_accept_suppressed_missing_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A TAR archive context cannot suppress missing pinned executable data."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo("unrelated")
        info.size = len(BINARY)
        archive.addfile(info, io.BytesIO(BINARY))

    monkeypatch.setattr(tarfile.TarFile, "__exit__", lambda *_args: True)
    with pytest.raises(python_validation.ProvisionError, match="suppressed"):
        _ = python_validation._uv_member_bytes(
            output.getvalue(), python_validation.uv_artifact(PLATFORM_ID)
        )


@pytest.mark.parametrize("archive_kind", ["zip", "tar"])
def test_uv_member_does_not_accept_suppressed_read_failure(
    monkeypatch: pytest.MonkeyPatch,
    archive_kind: str,
) -> None:
    """A forged member context cannot erase a failed bounded content read."""
    failure = OSError("cannot read compressed member")

    class SuppressingMember:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> bool:
            return True

        def read(self, _limit: int) -> bytes:
            raise failure

    output = io.BytesIO()
    if archive_kind == "zip":
        name = "uv.exe"
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(name, BINARY)
        monkeypatch.setattr(
            zipfile.ZipFile, "open", lambda *_args: SuppressingMember()
        )
        extract = python_validation._zip_member_bytes
    else:
        name = "uv-release/uv"
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(BINARY)
            archive.addfile(info, io.BytesIO(BINARY))
        monkeypatch.setattr(
            tarfile.TarFile, "extractfile", lambda *_args: SuppressingMember()
        )
        extract = python_validation._tar_member_bytes

    with pytest.raises(python_validation.ProvisionError, match="suppressed"):
        _ = extract(output.getvalue(), name)


@pytest.mark.parametrize("archive_kind", ["zip", "tar"])
def test_uv_archive_uses_constructed_archive_not_substituted_enter(
    monkeypatch: pytest.MonkeyPatch,
    archive_kind: str,
) -> None:
    """A substituted context entry cannot swap verified archive contents."""
    name = "uv.exe" if archive_kind == "zip" else "uv-release/uv"

    def encode(payload: bytes) -> bytes:
        result = io.BytesIO()
        if archive_kind == "zip":
            with zipfile.ZipFile(result, "w") as archive:
                archive.writestr(name, payload)
        else:
            with tarfile.open(fileobj=result, mode="w:gz") as archive:
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        return result.getvalue()

    checked = encode(BINARY)
    substituted = encode(b"foreign-unverified")
    if archive_kind == "zip":
        foreign_archive = zipfile.ZipFile(io.BytesIO(substituted))
        monkeypatch.setattr(
            zipfile.ZipFile, "__enter__", lambda *_args: foreign_archive
        )
        extract = python_validation._zip_member_bytes
    else:
        foreign_archive = tarfile.open(  # noqa: SIM115 - closed in finally.
            fileobj=io.BytesIO(substituted), mode="r:gz"
        )
        monkeypatch.setattr(
            tarfile.TarFile, "__enter__", lambda *_args: foreign_archive
        )
        extract = python_validation._tar_member_bytes
    try:
        assert extract(checked, name) == BINARY
    finally:
        foreign_archive.close()


def test_uv_zip_member_uses_opened_stream_not_substituted_enter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged ZIP member context cannot replace the selected executable."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("uv.exe", BINARY)
    foreign = b"foreign" + b"!" * (len(BINARY) - len(b"foreign"))
    monkeypatch.setattr(
        zipfile.ZipExtFile, "__enter__", lambda *_args: io.BytesIO(foreign)
    )
    assert python_validation._zip_member_bytes(output.getvalue(), "uv.exe") == BINARY


def test_uv_zip_rejects_hidden_duplicate_in_substituted_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The opened archive inventory cannot hide an ambiguous executable."""
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("uv.exe", b"first-uv")
            archive.writestr("uv.exe", b"second-uv")

    def concealed_inventory(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        return archive.filelist[:1]

    monkeypatch.setattr(zipfile.ZipFile, "infolist", concealed_inventory)
    with pytest.raises(python_validation.ProvisionError, match="duplicate uv zip"):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


def test_uv_zip_ignores_substituted_getinfo_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A redirecting lookup cannot replace the selected executable bytes."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("uv.exe", BINARY)
        archive.writestr("other.txt", b"foreign-bytes")

    def substituted_info(archive: zipfile.ZipFile, _name: str) -> zipfile.ZipInfo:
        return archive.filelist[1]

    monkeypatch.setattr(zipfile.ZipFile, "getinfo", substituted_info)
    assert python_validation._zip_member_bytes(output.getvalue(), "uv.exe") == BINARY


@pytest.mark.parametrize("forgery", ["object", "subclass"])
def test_uv_zip_rejects_foreign_inventory_entry_before_name_access(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """ZIP scanning cannot evaluate foreign entry names before admission."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("uv.exe", BINARY)

    class Trap:
        @property
        def filename(self) -> str:
            raise AssertionError("foreign ZIP entry name evaluated")

    class ZipInfoTrap(zipfile.ZipInfo):
        def __getattribute__(self, name: str) -> object:
            if name == "filename":
                raise AssertionError("foreign ZIP entry name evaluated")
            return super().__getattribute__(name)

    replacement = Trap() if forgery == "object" else ZipInfoTrap("unused")

    def injected_enter(archive: zipfile.ZipFile) -> zipfile.ZipFile:
        archive.filelist.append(cast("zipfile.ZipInfo", cast("object", replacement)))
        return archive

    monkeypatch.setattr(zipfile.ZipFile, "__enter__", injected_enter)
    with pytest.raises(python_validation.ProvisionError, match="native.*metadata"):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


def test_uv_zip_rejects_duplicate_selected_executable() -> None:
    """Ambiguous duplicate ZIP names cannot select executable contents."""
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("uv.exe", b"first-uv")
            archive.writestr("uv.exe", b"second-uv")
    with pytest.raises(
        python_validation.ProvisionError, match="duplicate uv zip member"
    ):
        _ = python_validation._zip_member_bytes(output.getvalue(), "uv.exe")


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_uv_zip_rejects_short_member_with_forged_declared_length(
    compression: int,
) -> None:
    """A valid CRC is insufficient when ZIP size metadata overstates bytes."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.writestr("uv.exe", BINARY)
    encoded = bytearray(output.getvalue())
    central_directory = encoded.index(b"PK\x01\x02")
    struct.pack_into("<I", encoded, central_directory + 24, len(BINARY) + 7)

    with pytest.raises(python_validation.ProvisionError, match="size|length"):
        _ = python_validation._zip_member_bytes(bytes(encoded), "uv.exe")



@pytest.mark.parametrize("forgery", ["object", "subclass"])
def test_uv_tar_rejects_foreign_candidate_before_name_access(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """TAR scanning cannot invoke foreign member-name hooks before admission."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo("uv-release/uv")
        info.size = len(BINARY)
        archive.addfile(info, io.BytesIO(BINARY))

    class Trap:
        @property
        def name(self) -> str:
            raise AssertionError("foreign TAR member name evaluated")

    class TarInfoTrap(tarfile.TarInfo):
        def __getattribute__(self, name: str) -> object:
            if name == "name":
                raise AssertionError("foreign TAR member name evaluated")
            return super().__getattribute__(name)

    replacement = Trap() if forgery == "object" else TarInfoTrap("unused")
    original_next = tarfile.TarFile.next
    called = 0

    def injected_next(archive: tarfile.TarFile) -> object:
        nonlocal called
        called += 1
        if called == 1:
            return original_next(archive)
        return replacement

    monkeypatch.setattr(tarfile.TarFile, "next", injected_next)
    with pytest.raises(python_validation.ProvisionError, match="native size metadata"):
        _ = python_validation._tar_member_bytes(output.getvalue(), "uv-release/uv")
    assert called > 1


def test_uv_tar_rejects_duplicate_selected_executable() -> None:
    """A tar archive with conflicting selected names is not unambiguous."""
    member_name = "uv-release/uv"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for payload in (b"first-uv", b"second-uv"):
            member = tarfile.TarInfo(member_name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    with pytest.raises(
        python_validation.ProvisionError, match="duplicate uv tar member"
    ):
        _ = python_validation._tar_member_bytes(output.getvalue(), member_name)


def test_uv_tar_rejects_selected_member_short_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a bounded short TAR read cannot become a complete uv executable."""
    member_name = "uv-release/uv"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo(member_name)
        info.size = len(BINARY)
        archive.addfile(info, io.BytesIO(BINARY))

    def incomplete_member(
        _archive: tarfile.TarFile, _member: tarfile.TarInfo | str
    ) -> io.BytesIO:
        return io.BytesIO(BINARY[:-1])

    monkeypatch.setattr(tarfile.TarFile, "extractfile", incomplete_member)
    with pytest.raises(python_validation.ProvisionError, match="length"):
        _ = python_validation._tar_member_bytes(output.getvalue(), member_name)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("selected_position", [FIRST_SELECTED, "last"])
def test_uv_tar_rejects_oversized_nonselected_member(
    monkeypatch: pytest.MonkeyPatch,
    selected_position: str,
) -> None:
    """Scanning beyond the selected uv must bound ignored TAR entries."""
    monkeypatch.setattr(python_validation, "MAX_UV_BINARY_BYTES", 4)
    members = [("padding", b"large"), ("uv-release/uv", b"u")]
    if selected_position == FIRST_SELECTED:
        members.reverse()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    extract = cast(
        "Callable[[bytes, str], bytes]",
        vars(python_validation)["_tar_member_bytes"],
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="archive member exceeds byte limit",
    ):
        _ = extract(output.getvalue(), "uv-release/uv")


@pytest.mark.parametrize("archive_kind", ["zip", "tar"])
@pytest.mark.parametrize("entry_count", [MINI_ARCHIVE_MEMBER_LIMIT, 5])
@pytest.mark.parametrize("selected_position", [FIRST_SELECTED, "last"])
def test_uv_archive_rejects_excessive_member_inventory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    archive_kind: str,
    entry_count: int,
    selected_position: str,
) -> None:
    """UV archive scanning must bound entries even after the executable."""
    monkeypatch.setattr(
        python_validation, "MAX_UV_ARCHIVE_MEMBERS", MINI_ARCHIVE_MEMBER_LIMIT
    )
    member_name = (
        "uv.exe" if archive_kind == ZIP_ARCHIVE_KIND else "uv-release/uv"
    )
    padding = [f"padding-{index}" for index in range(entry_count - 1)]
    names = (
        [member_name, *padding]
        if selected_position == FIRST_SELECTED
        else [*padding, member_name]
    )
    output = io.BytesIO()
    if archive_kind == ZIP_ARCHIVE_KIND:
        with zipfile.ZipFile(output, "w") as archive:
            for name in names:
                archive.writestr(name, BINARY if name == member_name else b"x")
        extract = cast(
            "Callable[[bytes, str], bytes]",
            vars(python_validation)["_zip_member_bytes"],
        )
    else:
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for name in names:
                payload = BINARY if name == member_name else b"x"
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        extract = cast(
            "Callable[[bytes, str], bytes]",
            vars(python_validation)["_tar_member_bytes"],
        )
    if entry_count > MINI_ARCHIVE_MEMBER_LIMIT:
        with pytest.raises(
            python_validation.ProvisionError, match="member limit"
        ):
            _ = extract(output.getvalue(), member_name)
    else:
        assert extract(output.getvalue(), member_name) == BINARY


def _damaged_uv_zip(method: int, damaged_byte: int) -> bytes:
    """Build a native ZIP with one intentionally damaged compressed member.

    Returns:
        Native ZIP bytes with a malformed selected member.

    """
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=method) as archive:
        archive.writestr("uv.exe", BINARY * 500)
    encoded = bytearray(output.getvalue())
    name_length, extra_length = struct.unpack_from("<HH", encoded, 26)
    payload_offset = 30 + name_length + extra_length
    encoded[payload_offset + damaged_byte] = 0xFF
    return bytes(encoded)


@pytest.mark.parametrize(
    "case",
    [
        (zipfile.ZIP_DEFLATED, 0, zlib.error),
        (zipfile.ZIP_LZMA, 9, lzma.LZMAError),
        (zipfile.ZIP_ZSTANDARD, 0, zstd.ZstdError),
    ],
)
def test_uv_zip_decoder_failure_is_typed(
    case: tuple[int, int, type[Exception]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed compressed uv members cannot publish executable bytes."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    encoded = _damaged_uv_zip(case[0], case[1])
    selected = replace(artifact, asset="uv-test.zip", member="uv.exe")
    extract = cast(
        "Callable[[bytes, python_validation.UvArtifact], bytes]",
        vars(python_validation)["_uv_member_bytes"],
    )
    with pytest.raises(
        python_validation.ProvisionError, match=case[2].__name__
    ) as failure:
        _ = extract(encoded, selected)
    assert type(failure.value.__cause__) is case[2]

    def fake_artifact(platform_id: str) -> python_validation.UvArtifact:
        assert platform_id == PLATFORM_ID
        return selected

    def fake_download(chosen: python_validation.UvArtifact) -> bytes:
        assert chosen == selected
        return encoded

    monkeypatch.setattr(python_validation, "uv_artifact", fake_artifact)
    monkeypatch.setattr(
        python_validation, "_download_uv_archive", fake_download
    )
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    with pytest.raises(
        python_validation.ProvisionError, match=case[2].__name__
    ):
        _ = python_validation.ensure_uv(checkout, platform_id=PLATFORM_ID)
    executable = python_validation.uv_executable(selected, checkout)
    assert not executable.exists()
    assert not executable.with_name(f"{executable.name}.tmp").exists()


def test_uv_truncated_gzip_archive_reports_typed_error() -> None:
    """A truncated compressed TAR must not leak an unhandled EOFError."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name in ("padding-a", "padding-b", artifact.member):
            payload = b"member" * 500
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    extract = cast(
        "Callable[[bytes, python_validation.UvArtifact], bytes]",
        vars(python_validation)["_uv_member_bytes"],
    )
    with pytest.raises(
        python_validation.ProvisionError, match="EOFError"
    ) as error:
        _ = extract(output.getvalue()[:-100], artifact)
    assert type(error.value.__cause__) is EOFError


def test_uv_does_not_replace_competing_destination_during_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late competing executable must retain its bytes, never be overwritten."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    stage = executable.with_name(f"{executable.name}.tmp")
    original_verify = python_validation._verify_uv_stage_descriptor_bytes
    calls = 0

    def occupy_during_publish(
        temporary: Path,
        descriptor: int,
        identity: tuple[int, int],
        binary: bytes,
    ) -> None:
        nonlocal calls
        original_verify(temporary, descriptor, identity, binary)
        calls += 1
        if calls == 2:
            assert not executable.exists()
            _ = executable.write_bytes(PRESERVED)

    monkeypatch.setattr(
        python_validation,
        "_verify_uv_stage_descriptor_bytes",
        occupy_during_publish,
    )
    with pytest.raises(
        python_validation.ProvisionError, match="uv executable appeared"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert calls == 2
    assert executable.read_bytes() == PRESERVED
    assert not stage.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_parent_swap_during_link_cannot_publish_outside_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped publication parent cannot receive the staged executable."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    retained = tmp_path / "retained-bin"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    native_link = os.link
    swapped = False

    def swap_parent_at_link(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        follow_symlinks: bool = True,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        assert not swapped
        swapped = True
        _ = executable.parent.rename(retained)
        _symlink(executable.parent, foreign, directory=True)
        _ = (foreign / "uv.tmp").write_bytes(PRESERVED)
        if src_dir_fd is not None and dst_dir_fd is not None:
            native_link(
                source, destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
                follow_symlinks=follow_symlinks,
            )
        else:
            native_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "link", swap_parent_at_link)
    with pytest.raises(python_validation.ProvisionError):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert swapped
    assert not (foreign / executable.name).exists()
    assert (foreign / "uv.tmp").read_bytes() == PRESERVED


def test_uv_rejects_staging_swap_during_atomic_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late substituted staging link cannot become the verified executable."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    retained = tmp_path / "retained-uv-stage"
    foreign = tmp_path / "foreign-uv"
    _ = foreign.write_bytes(PRESERVED)
    native_link = os.link

    def swap_source_before_link(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        follow_symlinks: bool = True,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert os.fspath(source) in (os.fspath(stage), stage.name)
        assert os.fspath(destination) in (os.fspath(executable), executable.name)
        _ = stage.replace(retained)
        _symlink(stage, foreign, directory=False)
        if src_dir_fd is not None and dst_dir_fd is not None:
            native_link(
                source, destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
                follow_symlinks=follow_symlinks,
            )
        else:
            native_link(source, destination, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "link", swap_source_before_link)
    with pytest.raises(
        python_validation.ProvisionError, match="uv linked stage changed"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert retained.read_bytes() == BINARY
    assert foreign.read_bytes() == PRESERVED
    assert stage.is_symlink()
    assert executable.is_symlink()


def test_uv_rejects_mutation_after_atomic_publication_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final executable is checked after its atomic no-replace link."""
    if not hasattr(os, "pwrite"):
        pytest.skip("descriptor positional writes unavailable")
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    native_link = os.link

    def mutate_after_link(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        follow_symlinks: bool = True,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        if src_dir_fd is not None and dst_dir_fd is not None:
            native_link(
                source, destination,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
                follow_symlinks=follow_symlinks,
            )
        else:
            native_link(source, destination, follow_symlinks=follow_symlinks)
        with executable.open("r+b") as stream:
            assert stream.write(b"!") == 1

    monkeypatch.setattr(os, "link", mutate_after_link)
    with pytest.raises(
        python_validation.ProvisionError, match="uv staging.*bytes"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert executable.read_bytes() != BINARY


def test_uv_successful_atomic_publication_is_single_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed UV install leaves no temporary hardlink behind."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    assert python_validation.ensure_uv(root, platform_id=PLATFORM_ID) == executable
    assert executable.read_bytes() == BINARY
    assert executable.lstat().st_nlink == 1
    assert not executable.with_name(f"{executable.name}.tmp").exists()


@pytest.mark.parametrize("entrypoint", ["document", "artifact"])
def test_uv_manifest_json_provider_cannot_substitute_pinned_release(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    """A forged decoder cannot replace uv version and download URL authority."""
    source = python_validation.UV_MANIFEST.read_text(encoding="utf-8")
    document = cast("dict[str, object]", json.loads(source))
    assert document["version"] == "0.12.20"
    document["version"] = "0.99.99"
    document["base_url"] = (
        "https://github.com/astral-sh/uv/releases/download/0.99.99/"
    )

    def substituted(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return document

    monkeypatch.setattr(json, "loads", substituted)
    with pytest.raises(
        python_validation.ProvisionError,
        match="uv JSON decoder provider differs from source",
    ):
        if entrypoint == "document":
            _ = python_validation._uv_manifest_document(python_validation.UV_MANIFEST)
        else:
            _ = python_validation.uv_artifact(PLATFORM_ID)


@pytest.mark.parametrize("entrypoint", ("document", "artifact"))
@pytest.mark.parametrize("providers", ("decoder-only", "joint", "self-restoring"))
def test_uv_manifest_public_decoder_cannot_forge_release(
    monkeypatch: pytest.MonkeyPatch, entrypoint: str, providers: str
) -> None:
    """Only the pinned file bytes may supply a uv release and artifact identity."""
    source = python_validation.UV_MANIFEST.read_text(encoding="utf-8")
    native_decoder = json.JSONDecoder
    forged = cast("dict[str, object]", native_decoder().decode(source))
    forged["version"] = "0.99.99"
    forged["base_url"] = (
        "https://github.com/astral-sh/uv/releases/download/0.99.99/"
    )

    class ForgedDecoder:
        def __init__(self, **_kwargs: object) -> None:
            if providers == "self-restoring":
                patch.setattr(json, "JSONDecoder", native_decoder)

        def decode(self, _source: str) -> object:
            return forged

    def forged_loads(_source: str, **_kwargs: object) -> object:
        return forged

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONDecoder", ForgedDecoder)
        if providers == "joint":
            patch.setattr(json, "loads", forged_loads)
        with pytest.raises(
            python_validation.ProvisionError,
            match="uv JSON decoder provider differs from source",
        ):
            if entrypoint == "document":
                _ = python_validation._uv_manifest_document(  # pyright: ignore[reportPrivateUsage]
                    python_validation.UV_MANIFEST
                )
            else:
                _ = python_validation.uv_artifact(PLATFORM_ID)


def test_uv_manifest_public_decoder_cannot_mask_invalid_syntax(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A fabricated public document cannot override malformed stored JSON."""
    invalid = tmp_path / "malformed-uv.json"
    _ = invalid.write_text('{"schema_version":1,,}', encoding="utf-8")
    original = json.loads(python_validation.UV_MANIFEST.read_text())

    class ForgedDecoder:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def decode(self, _source: str) -> object:
            return original

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONDecoder", ForgedDecoder)
        with pytest.raises(python_validation.ProvisionError, match="cannot read") as caught:
            _ = python_validation.uv_artifact(PLATFORM_ID, invalid)
    assert type(caught.value.__cause__) is json.JSONDecodeError


def test_uv_manifest_source_equivalent_public_decoder_is_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An honest public JSONDecoder delegate is compatible with pinned bytes."""
    native_decoder = json.JSONDecoder

    class DelegatingDecoder:
        def __init__(self, *, object_pairs_hook: object) -> None:
            self.decoder = native_decoder(
                object_pairs_hook=cast(
                    "Callable[[list[tuple[str, object]]], object]",
                    object_pairs_hook,
                )
            )

        def decode(self, source: str) -> object:
            return self.decoder.decode(source)

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONDecoder", DelegatingDecoder)
        assert python_validation.uv_artifact(PLATFORM_ID).version == "0.12.20"


def test_uv_manifest_json_provider_accepts_equivalent_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source-preserving JSON adapters retain pinned release behavior."""
    native = json.loads

    def delegated(text: str, *, object_pairs_hook: object) -> object:
        return native(
            text,
            object_pairs_hook=cast(
                "Callable[[list[tuple[str, object]]], object]", object_pairs_hook
            ),
        )

    monkeypatch.setattr(json, "loads", delegated)
    assert python_validation.uv_artifact(PLATFORM_ID).version == "0.12.20"


@pytest.mark.parametrize("entrypoint", ["document", "artifact"])
def test_uv_manifest_decoder_rejects_self_restoring_forgery(
    monkeypatch: pytest.MonkeyPatch, entrypoint: str
) -> None:
    """An injected decoder cannot restore itself mid-call to hide forged data."""
    original_loads = json.loads
    forged = cast(
        "dict[str, object]",
        original_loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    forged["version"] = "0.99.99"
    with monkeypatch.context() as context:

        def restore_and_forge(_text: str, *, object_pairs_hook: object) -> object:
            del object_pairs_hook
            context.setattr(json, "loads", original_loads)
            return forged

        context.setattr(json, "loads", restore_and_forge)
        with pytest.raises(
            python_validation.ProvisionError,
            match="uv JSON decoder provider differs from source",
        ):
            if entrypoint == "document":
                _ = python_validation._uv_manifest_document(python_validation.UV_MANIFEST)
            else:
                _ = python_validation.uv_artifact(PLATFORM_ID)


def test_uv_manifest_equivalent_adapter_cannot_mutate_source_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adapter-owned aliases cannot rewrite admitted nested manifest fields."""
    original_loads = json.loads
    returned: list[object] = []

    def equivalent(text: str, *, object_pairs_hook: object) -> object:
        parsed = cast(
            "object",
            original_loads(
                text,
                object_pairs_hook=cast(
                    "Callable[[list[tuple[str, object]]], object]",
                    object_pairs_hook,
                ),
            ),
        )
        returned.append(parsed)
        return parsed

    monkeypatch.setattr(json, "loads", equivalent)
    admitted = python_validation._uv_manifest_document(python_validation.UV_MANIFEST)
    assert admitted == returned[0]
    assert admitted is not returned[0]
    external = cast("dict[str, object]", returned[0])
    external_artifacts = cast("dict[str, object]", external["artifacts"])
    external_target = cast("dict[str, object]", external_artifacts[PLATFORM_ID])
    external_target["asset"] = "foreign-uv.zip"
    admitted_artifacts = cast("dict[str, object]", admitted["artifacts"])
    admitted_target = cast("dict[str, object]", admitted_artifacts[PLATFORM_ID])
    assert admitted_target["asset"] != "foreign-uv.zip"


def test_uv_manifest_json_provider_cannot_hide_invalid_syntax(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The trusted parser must read original malformed manifest syntax."""
    path = tmp_path / "invalid.json"
    _ = path.write_text('{"schema_version":1,,}', encoding="utf-8")
    forged = cast("dict[str, object]", json.loads(python_validation.UV_MANIFEST.read_text()))

    def substituted(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", substituted)
    with pytest.raises(python_validation.ProvisionError, match="cannot read") as caught:
        _ = python_validation.uv_artifact(PLATFORM_ID, path)
    assert type(caught.value.__cause__) is json.JSONDecodeError


def test_uv_manifest_json_provider_rejects_foreign_nested_key_before_equality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign colliding key cannot run equality during corroboration."""

    class ForeignKey(str):
        def __hash__(self) -> int:
            return str.__hash__(self)

        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign uv manifest equality executed")

    forged = cast("dict[str, object]", json.loads(python_validation.UV_MANIFEST.read_text()))
    artifacts = cast("dict[str, object]", forged["artifacts"])
    target = cast("dict[str, object]", artifacts[PLATFORM_ID])
    sha = target.pop("sha256")
    target[ForeignKey("sha256")] = sha

    def substituted(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", substituted)
    with pytest.raises(
        python_validation.ProvisionError,
        match="uv JSON decoder provider differs from source",
    ):
        _ = python_validation.uv_artifact(PLATFORM_ID)


def test_uv_manifest_rejects_hardlinked_external_authority(
    tmp_path: Path,
) -> None:
    """A multiply linked manifest cannot inherit authority from an outside path."""
    external = tmp_path / "outside-manifest.json"
    _ = external.write_bytes(python_validation.UV_MANIFEST.read_bytes())
    linked = tmp_path / "pinned-manifest.json"
    try:
        os.link(external, linked)
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    with pytest.raises(
        python_validation.ProvisionError, match="uv toolchain manifest.*single-link"
    ):
        _ = python_validation.uv_artifact(PLATFORM_ID, linked)
    assert external.read_bytes() == python_validation.UV_MANIFEST.read_bytes()


@pytest.mark.parametrize("failure", ["read", "post-read-identity"])
def test_uv_manifest_rejects_suppressed_authority_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A manifest context cannot erase a fault during physical evidence read."""
    manifest = tmp_path / "uv.json"
    _ = manifest.write_bytes(BINARY)
    native_open = python_validation._open_owned_binary_stream

    class SuppressingStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> bool:
            self.stream.close()
            return True

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            if failure == "read":
                raise OSError("cannot read manifest")
            content = self.stream.read(size)
            _ = manifest.write_bytes(b"X" * len(content))
            return content

    def injected_stream(descriptor: int) -> BinaryIO:
        return cast(
            "BinaryIO", cast("object", SuppressingStream(native_open(descriptor)))
        )

    monkeypatch.setattr(
        python_validation, "_open_owned_binary_stream", injected_stream
    )
    with pytest.raises(python_validation.ProvisionError):
        _ = python_validation._read_uv_manifest_bytes(manifest)


def test_uv_manifest_uses_owned_stream_not_substituted_enter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Context entry cannot redirect manifest reads to unrelated bytes."""
    manifest = tmp_path / "uv.json"
    _ = manifest.write_bytes(BINARY)
    native_open = python_validation._open_owned_binary_stream

    class ForeignStream:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor

        def fileno(self) -> int:
            return self.descriptor

        def read(self, _size: int) -> bytes:
            return b"X" * len(BINARY)

    class RedirectingStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> ForeignStream:
            return ForeignStream(self.stream.fileno())

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            return self.stream.read(size)

    def injected_stream(descriptor: int) -> BinaryIO:
        return cast(
            "BinaryIO", cast("object", RedirectingStream(native_open(descriptor)))
        )

    monkeypatch.setattr(
        python_validation, "_open_owned_binary_stream", injected_stream
    )
    assert python_validation._read_uv_manifest_bytes(manifest) == BINARY


@pytest.mark.parametrize("failure", ["read", "post-read-identity"])
def test_jig_source_rejects_suppressed_authority_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Jig must not accept partial or stale source bytes after a hidden fault."""
    source = tmp_path / "ruff"
    _ = source.write_bytes(BINARY)
    native_open = python_validation._open_owned_binary_stream

    class SuppressingStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> bool:
            self.stream.close()
            return True

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            if failure == "read":
                raise OSError("cannot read jig source")
            content = self.stream.read(size)
            _ = source.write_bytes(b"X" * len(content))
            return content

    def injected_stream(descriptor: int) -> BinaryIO:
        return cast(
            "BinaryIO", cast("object", SuppressingStream(native_open(descriptor)))
        )

    monkeypatch.setattr(
        python_validation, "_open_owned_binary_stream", injected_stream
    )
    with pytest.raises(python_validation.ProvisionError):
        _ = python_validation._read_jig_binary_source(source)


def test_jig_source_uses_owned_stream_not_substituted_enter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign stream returned at entry cannot substitute tool bytes."""
    source = tmp_path / "ruff"
    _ = source.write_bytes(BINARY)
    native_open = python_validation._open_owned_binary_stream

    class ForeignStream:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor

        def fileno(self) -> int:
            return self.descriptor

        def read(self, _size: int) -> bytes:
            return b"X" * len(BINARY)

    class RedirectingStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> ForeignStream:
            return ForeignStream(self.stream.fileno())

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            return self.stream.read(size)

    def injected_stream(descriptor: int) -> BinaryIO:
        return cast(
            "BinaryIO", cast("object", RedirectingStream(native_open(descriptor)))
        )

    monkeypatch.setattr(
        python_validation, "_open_owned_binary_stream", injected_stream
    )
    assert python_validation._read_jig_binary_source(source) == BINARY


def test_jig_alias_writer_uses_owned_stream_not_substituted_enter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stage write cannot be redirected to a foreign context-entry stream."""
    target = tmp_path / "jig-alias.bin"
    foreign_path = tmp_path / "protected-external.bin"
    preserved = b"protected-foreign-binary-unchanged"
    _ = foreign_path.write_bytes(preserved)
    native_open = python_validation._open_jig_alias_write_stream

    class RedirectingWriter:
        def __init__(self, stream: BinaryIO, foreign: BinaryIO) -> None:
            self.stream = stream
            self.foreign = foreign

        def __enter__(self) -> BinaryIO:
            return self.foreign

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def write(self, payload: bytes) -> int:
            return self.stream.write(payload)

        def fileno(self) -> int:
            return self.stream.fileno()

    with foreign_path.open("r+b") as foreign:
        def injected_writer(descriptor: int) -> BinaryIO:
            return cast(
                "BinaryIO",
                cast("object", RedirectingWriter(native_open(descriptor), foreign)),
            )

        monkeypatch.setattr(
            python_validation, "_open_jig_alias_write_stream", injected_writer
        )
        python_validation._publish_jig_tool_alias(target, BINARY, windows=False)
    assert target.read_bytes() == BINARY
    assert foreign_path.read_bytes() == preserved


def test_jig_alias_writer_rejects_suppressed_chmod_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A write-context exit cannot erase a failed executable-mode update."""
    target = tmp_path / "jig-alias.bin"
    native_open = python_validation._open_jig_alias_write_stream
    native_fchmod = os.fchmod
    watched: set[int] = set()

    class SuppressingWriter:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> bool:
            self.stream.close()
            return True

        def write(self, payload: bytes) -> int:
            return self.stream.write(payload)

        def fileno(self) -> int:
            return self.stream.fileno()

    def injected_writer(descriptor: int) -> BinaryIO:
        watched.add(descriptor)
        return cast("BinaryIO", cast("object", SuppressingWriter(native_open(descriptor))))

    def deny_chmod(descriptor: int, mode: int) -> None:
        if descriptor in watched:
            raise OSError("cannot mark Jig alias executable")
        native_fchmod(descriptor, mode)

    monkeypatch.setattr(
        python_validation, "_open_jig_alias_write_stream", injected_writer
    )
    monkeypatch.setattr(os, "fchmod", deny_chmod)
    with pytest.raises(python_validation.ProvisionError, match="suppressed"):
        python_validation._publish_jig_tool_alias(target, BINARY, windows=False)
    assert not target.exists()


@pytest.mark.parametrize("authority", ["uv-manifest", "jig-binary"])
def test_binary_authority_rejects_forged_fdopen_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority: str,
) -> None:
    """An injected stream cannot substitute valid-looking native file bytes."""
    if authority == "uv-manifest":
        path = tmp_path / "uv.json"
        genuine = python_validation.UV_MANIFEST.read_bytes()
        _ = path.write_bytes(b"!" + genuine[1:])
    else:
        path = tmp_path / "ruff"
        genuine = b"genuine-jig-tool"
        _ = path.write_bytes(b"foreign-jig-tool")
    real_fdopen = os.fdopen
    opened_streams: list[ForgedStream] = []

    class ForgedStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream: BinaryIO = stream

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, _size: int) -> bytes:
            return genuine

    def forged_fdopen(descriptor: int, mode: str) -> object:
        forged = ForgedStream(cast("BinaryIO", real_fdopen(os.dup(descriptor), mode)))
        opened_streams.append(forged)
        return forged

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", forged_fdopen)
            with pytest.raises(
                python_validation.ProvisionError, match="native.*stream"
            ):
                if authority == "uv-manifest":
                    _ = python_validation.uv_artifact("linux-x86_64", path)
                else:
                    _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
                        path
                    )
    finally:
        for forged in opened_streams:
            forged.stream.close()
    assert path.read_bytes() != genuine


@pytest.mark.parametrize("authority", ["uv-manifest", "jig-binary"])
def test_binary_authority_rejects_native_stream_on_duplicated_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority: str,
) -> None:
    """A native reader on a different FD must not impersonate the opened FD."""
    path = tmp_path / "authority"
    payload = (
        python_validation.UV_MANIFEST.read_bytes()
        if authority == "uv-manifest"
        else BINARY
    )
    _ = path.write_bytes(payload)
    native_fdopen = os.fdopen
    original_descriptors: list[int] = []
    duplicate_streams: list[BinaryIO] = []

    def rewrapped_fdopen(descriptor: int, mode: str) -> BinaryIO:
        original_descriptors.append(descriptor)
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        duplicate_streams.append(stream)
        return stream

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", rewrapped_fdopen)
            with pytest.raises(
                python_validation.ProvisionError, match="native.*descriptor"
            ):
                if authority == "uv-manifest":
                    _ = python_validation.uv_artifact(PLATFORM_ID, path)
                else:
                    _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
                        path
                    )
        assert len(original_descriptors) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(original_descriptors[0])
    finally:
        for descriptor in original_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for stream in duplicate_streams:
            stream.close()
    assert path.read_bytes() == payload


@pytest.mark.parametrize("field", ["version", "asset"])
@pytest.mark.parametrize(
    "unsafe_segment",
    [
        "NUL", "COM1.exe", "release.", "release ",
        "uv|foreign", "uv:stream", ".. ",
        "uv%2Fother", "uv%5cother", "uv%2e%2e", "uv%252fother",
        "uv#fragment", "uv;params", "uv@host", "uv\u202eother",
    ],
)
def test_uv_manifest_rejects_nonportable_path_segments(
    tmp_path: Path, field: str, unsafe_segment: str
) -> None:
    """Release identities must be literal portable URL and physical segments."""
    parsed = cast(
        "object", json.loads(python_validation.UV_MANIFEST.read_text())
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    if field == "version":
        document["version"] = unsafe_segment
        document["base_url"] = (
            f"{python_validation.UV_RELEASE_BASE}{unsafe_segment}/"
        )
    else:
        artifacts_value = document["artifacts"]
        assert isinstance(artifacts_value, dict)
        artifacts = cast("dict[str, object]", artifacts_value)
        selected = artifacts[PLATFORM_ID]
        assert isinstance(selected, dict)
        cast("dict[str, object]", selected)["asset"] = unsafe_segment
    manifest = tmp_path / "uv.json"
    _ = manifest.write_text(json.dumps(document))
    with pytest.raises(python_validation.ProvisionError, match="path segment"):
        _ = python_validation.uv_artifact(PLATFORM_ID, manifest)


class _UnprintableUvCloseError(OSError):
    """A host failure whose human-readable representation must not be read."""

    def __str__(self) -> str:
        raise AssertionError("untrusted close failure was formatted")


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX stage descriptors")
def test_uv_rejects_writable_stage_close_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed stage descriptor close must not publish trusted uv bytes."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    native_close = os.close
    original_write = python_validation._write_uv_stage_descriptor
    fault = _UnprintableUvCloseError("unprintable stage descriptor close")
    written_descriptor: int | None = None
    triggered = False

    def track_write(
        temporary: Path,
        receipt: tuple[int, tuple[int, int]],
        payload: bytes,
        *,
        windows: bool,
    ) -> None:
        nonlocal written_descriptor
        written_descriptor = receipt[0]
        original_write(temporary, receipt, payload, windows=windows)

    def fail_written_close(descriptor: int) -> None:
        nonlocal triggered
        if descriptor == written_descriptor and not triggered:
            triggered = True
            native_close(descriptor)
            raise fault
        native_close(descriptor)

    monkeypatch.setattr(python_validation, "_write_uv_stage_descriptor", track_write)
    monkeypatch.setattr(os, "close", fail_written_close)
    with pytest.raises(
        python_validation.ProvisionError, match="uv staging descriptor close"
    ) as raised:
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert raised.value.__cause__ is fault
    assert triggered and written_descriptor is not None
    with pytest.raises(OSError):
        _ = os.fstat(written_descriptor)
    assert not stage.exists()
    assert not executable.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_types_provision_parent_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed parent close before staging must remain a typed host fault."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    native_close = os.close
    fault = _UnprintableUvCloseError("unprintable parent close")
    triggered = False

    def fail_parent_close(descriptor: int) -> None:
        nonlocal triggered
        status = os.fstat(descriptor)
        if (
            not triggered
            and executable.parent.exists()
            and not stage.exists()
            and (status.st_dev, status.st_ino)
            == (executable.parent.stat().st_dev, executable.parent.stat().st_ino)
        ):
            triggered = True
            native_close(descriptor)
            raise fault
        native_close(descriptor)

    monkeypatch.setattr(os, "close", fail_parent_close)
    with pytest.raises(
        python_validation.ProvisionError, match="uv provisioning parent.*close"
    ) as captured:
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert captured.value.__cause__ is fault
    assert triggered
    assert not stage.exists()
    assert not executable.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_types_staging_parent_close_fault_without_leaking_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure after exclusive stage creation must close and discard that stage."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    native_close = os.close
    native_open = os.open
    opened: list[int] = []
    fault = _UnprintableUvCloseError("unprintable staging close")
    triggered = False

    def track_stage(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if dir_fd is not None:
            descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        else:
            descriptor = native_open(path, flags, mode)
        if os.fspath(path) in (stage.name, os.fspath(stage)) and flags & os.O_EXCL:
            opened.append(descriptor)
        return descriptor

    def fail_parent_close(descriptor: int) -> None:
        nonlocal triggered
        status = os.fstat(descriptor)
        if (
            not triggered
            and stage.exists()
            and (status.st_dev, status.st_ino)
            == (stage.parent.stat().st_dev, stage.parent.stat().st_ino)
        ):
            triggered = True
            native_close(descriptor)
            raise fault
        native_close(descriptor)

    monkeypatch.setattr(os, "open", track_stage)
    monkeypatch.setattr(os, "close", fail_parent_close)
    with pytest.raises(
        python_validation.ProvisionError, match="uv staging parent.*close"
    ) as captured:
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert captured.value.__cause__ is fault
    assert triggered
    assert len(opened) == 1
    for descriptor in opened:
        with pytest.raises(OSError):
            _ = os.fstat(descriptor)
    assert not stage.exists()
    assert not executable.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_types_publication_parent_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final parent close cannot turn publication into an untyped crash."""
    _ = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(
        python_validation.uv_artifact(PLATFORM_ID), root
    )
    stage = executable.with_name(f"{executable.name}.tmp")
    native_close = os.close
    fault = _UnprintableUvCloseError("unprintable publication close")
    triggered = False

    def fail_parent_close(descriptor: int) -> None:
        nonlocal triggered
        status = os.fstat(descriptor)
        if (
            not triggered
            and executable.exists()
            and not stage.exists()
            and (status.st_dev, status.st_ino)
            == (executable.parent.stat().st_dev, executable.parent.stat().st_ino)
        ):
            triggered = True
            native_close(descriptor)
            raise fault
        native_close(descriptor)

    monkeypatch.setattr(os, "close", fail_parent_close)
    with pytest.raises(
        python_validation.ProvisionError, match="uv publication parent.*close"
    ) as captured:
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert captured.value.__cause__ is fault
    assert triggered
    assert executable.read_bytes() == BINARY
    assert not stage.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
@pytest.mark.parametrize("mutation", ["name-swap", "rewrite"])
def test_uv_rejects_final_executable_mutation_during_publication_parent_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A post-verification close callback cannot approve a different uv binary."""
    artifact = _mock_uv(monkeypatch)
    root = tmp_path / "checkout"
    root.mkdir()
    executable = python_validation.uv_executable(artifact, root)
    parked = tmp_path / "original-published-uv"
    native_close = python_validation._close_uv_parent_descriptor  # pyright: ignore[reportPrivateUsage]
    mutated = False

    def mutate_on_close(descriptor: int, *, context: str) -> None:
        nonlocal mutated
        native_close(descriptor, context=context)
        if context != "publication":
            return
        mutated = True
        if mutation == "name-swap":
            _ = executable.rename(parked)
            _ = executable.write_bytes(PRESERVED)
        else:
            before = executable.stat()
            _ = executable.write_bytes(b"!" + BINARY[1:])
            os.utime(executable, ns=(before.st_atime_ns, before.st_mtime_ns))

    def do_not_execute_unattested_binary(_command: list[str]) -> str:
        raise AssertionError("version probe reached an unattested executable")

    monkeypatch.setattr(
        python_validation, "_close_uv_parent_descriptor", mutate_on_close
    )
    monkeypatch.setattr(python_validation, "_run", do_not_execute_unattested_binary)
    with pytest.raises(
        python_validation.ProvisionError, match="published executable changed"
    ):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert mutated
    assert executable.read_bytes() != BINARY
    if mutation == "name-swap":
        assert parked.read_bytes() == BINARY


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX dirfd support")
def test_uv_parent_walk_close_failure_does_not_leak_new_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ancestor close fault must not leak the next opened directory."""
    parent = tmp_path / "checkout" / ".dependencies" / "uv" / "0.12.20" / "bin"
    parent.mkdir(parents=True)
    native_open = os.open
    native_close = os.close
    fault = _UnprintableUvCloseError("unprintable ancestor close")
    opened_children: list[int] = []
    failed = False
    previous = parent.parent.stat()

    def track_parent_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if dir_fd is not None:
            descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        else:
            descriptor = native_open(path, flags, mode)
        if dir_fd is not None and os.fspath(path) == parent.name:
            opened_children.append(descriptor)
        return descriptor

    def fail_previous_close(descriptor: int) -> None:
        nonlocal failed
        status = os.fstat(descriptor)
        if (
            opened_children
            and not failed
            and (status.st_dev, status.st_ino) == (previous.st_dev, previous.st_ino)
        ):
            failed = True
            native_close(descriptor)
            raise fault
        native_close(descriptor)

    monkeypatch.setattr(os, "open", track_parent_open)
    monkeypatch.setattr(os, "close", fail_previous_close)
    with pytest.raises(
        python_validation.ProvisionError, match="uv parent physical descriptor"
    ) as captured:
        _ = python_validation._open_uv_physical_parent(parent / "uv")
    assert captured.value.__cause__ is fault
    assert failed
    assert len(opened_children) == 1
    try:
        with pytest.raises(OSError):
            _ = os.fstat(opened_children[0])
    finally:
        try:
            native_close(opened_children[0])
        except OSError:
            pass


@pytest.mark.parametrize(
    "output",
    [
        "uv 0.12.20 arbitrary",
        "uv 0.12.20 (wrong-target)",
        "uv 0.12.20 (x86_64-unknown-linux-gnu) trailing",
        "uv 0.12.20 (x86_64-unknown-linux-gnu)\nother output",
        "uv 0.12.20 \nother output",
        "uv 0.12.20\t(x86_64-unknown-linux-gnu)",
        "uv 0.12.20 (x86_64-unknown-linux-gnu);command",
    ],
)
def test_uv_rejects_noncanonical_version_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    """An installed uv cannot assert pin identity with arbitrary suffix text."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    root = tmp_path / "checkout"
    executable = python_validation.uv_executable(artifact, root)
    executable.parent.mkdir(parents=True)
    _ = executable.write_bytes(BINARY)
    monkeypatch.setattr(python_validation, "_run", lambda _command: output)
    with pytest.raises(python_validation.ProvisionError, match="unexpected uv version"):
        _ = python_validation.ensure_uv(root, platform_id=PLATFORM_ID)
    assert executable.read_bytes() == BINARY


@pytest.mark.parametrize(
    "platform_id, banner",
    [
        ("linux-x86_64", "uv 0.12.20 (x86_64-unknown-linux-gnu)"),
        ("linux-aarch64", "uv 0.12.20 (aarch64-unknown-linux-gnu)"),
        ("macos-x86_64", "uv 0.12.20 (x86_64-apple-darwin)"),
        ("macos-aarch64", "uv 0.12.20 (aarch64-apple-darwin)"),
        ("windows-x86_64", "uv 0.12.20 (x86_64-pc-windows-msvc)"),
    ],
)
def test_uv_accepts_canonical_target_triple_banner(
    platform_id: str, banner: str
) -> None:
    """The selected native artifact's real release format remains admitted."""
    artifact = python_validation.uv_artifact(platform_id)
    assert python_validation._uv_version_matches(banner, artifact)
    assert python_validation._uv_version_matches(f"uv {artifact.version}", artifact)


class _ForeignUvVersionOutput(str):
    """Untrusted process output must not provide foreign comparison behavior."""

    def __eq__(self, _other: object) -> bool:
        raise AssertionError("foreign version comparison executed")


def test_uv_version_rejects_nonnative_output_without_hooks() -> None:
    """Only an exact native version-output string may certify pinned uv."""
    artifact = python_validation.uv_artifact(PLATFORM_ID)
    output = _ForeignUvVersionOutput(f"uv {artifact.version}")
    assert not python_validation._uv_version_matches(output, artifact)
