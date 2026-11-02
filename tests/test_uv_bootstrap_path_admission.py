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

import os
from pathlib import Path
from typing import cast

import pytest
from scripts.bootstrap import python_validation

PLATFORM_ID = "linux-x86_64"
BINARY = b"synthetic-pinned-uv"
PRESERVED = b"preserve"
SYMBOLIC = "symbolic"
VERSION_FLAG = "--version"


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
        path: str | os.PathLike[str], flags: int, mode: int = 0o777
    ) -> int:
        if os.fspath(path) == os.fspath(stage):
            descriptor = original_open(foreign, os.O_WRONLY)
            opened.append(descriptor)
            return descriptor
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
