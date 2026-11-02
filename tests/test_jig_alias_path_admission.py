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
#   - Regression tests for physical Jig alias source and parent admission.
# - Must-Not:
#   - Install or execute native validation tools.
# - Allows:
#   - Inputs: synthetic source files and host status fault injection.
#   - Outputs: fail-closed source admission evidence.
#   - Side effects: temporary pytest paths only.
# - Split-When:
#   - A distinct alias admission responsibility gains its own lifecycle.
# - Merge-When:
#   - Another test suite owns this exact Jig source status boundary.
# - Summary:
#   - Require physical host identity before accepting Jig tool source bytes.
#

"""Physical Jig source path admission regressions."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import cast

import pytest
from scripts.bootstrap import python_validation

BINARY = b"synthetic-native-jig-binary"


@pytest.mark.parametrize("masked", [False, 0])
def test_jig_source_rejects_masked_linked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    masked: object,
) -> None:
    """A linked source parent cannot be admitted through a false host predicate."""
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = (foreign / "tool.bin").write_bytes(BINARY)
    alias = tmp_path / "alias"
    try:
        _ = alias.symlink_to(foreign, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    native = Path.is_symlink

    def masked_symlink(path: Path) -> bool:
        if path == alias:
            return cast("bool", masked)
        return native(path)

    monkeypatch.setattr(Path, "is_symlink", masked_symlink)
    with pytest.raises(python_validation.ProvisionError, match="redirect|native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            alias / "tool.bin"
        )
    assert (foreign / "tool.bin").read_bytes() == BINARY


class ForeignStatus:
    """A foreign object can mimic a native filesystem stat receipt."""

    def __init__(self, observed: os.stat_result) -> None:
        self.st_mode: int = observed.st_mode
        self.st_nlink: int = observed.st_nlink
        self.st_dev: int = observed.st_dev
        self.st_ino: int = observed.st_ino
        self.st_size: int = observed.st_size
        self.st_mtime_ns: int = observed.st_mtime_ns
        self.st_ctime_ns: int = observed.st_ctime_ns


def test_jig_source_rejects_foreign_leaf_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged stat proxy cannot establish native Jig source identity."""
    source = tmp_path / "tool.bin"
    _ = source.write_bytes(BINARY)
    native = Path.lstat

    def forged_status(path: Path) -> os.stat_result:
        observed = native(path)
        if path == source:
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    monkeypatch.setattr(Path, "lstat", forged_status)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert source.read_bytes() == BINARY


@pytest.mark.parametrize("predicate", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("component", ["parent", "leaf"])
def test_jig_source_rejects_foreign_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    predicate: str,
    component: str,
) -> None:
    """A nonboolean link-status receipt cannot certify an alias source."""
    directory = tmp_path / "tools"
    directory.mkdir()
    source = directory / "tool.bin"
    _ = source.write_bytes(BINARY)
    affected = source if component == "leaf" else directory
    native = Path.is_symlink if predicate == "is_symlink" else Path.is_junction

    def forged_status(path: Path) -> bool:
        if path == affected:
            return cast("bool", cast("object", 0))
        return native(path)

    monkeypatch.setattr(Path, predicate, forged_status)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert source.read_bytes() == BINARY


def test_jig_source_types_host_lstat_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Physical source inspection faults remain typed and causal."""
    source = tmp_path / "tool.bin"
    _ = source.write_bytes(BINARY)
    native = Path.lstat
    fault = PermissionError("source lstat denied")

    def denied_status(path: Path) -> os.stat_result:
        if path == source:
            raise fault
        return native(path)

    monkeypatch.setattr(Path, "lstat", denied_status)
    with pytest.raises(python_validation.ProvisionError, match="inspect") as caught:
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert caught.value.__cause__ is fault


def test_jig_alias_stage_rejects_foreign_ownership_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged stage status cannot authorize a foreign leaf cleanup."""
    stage = tmp_path / "jig.tmp"
    _ = stage.write_bytes(BINARY)
    native = Path.lstat
    recorded = native(stage)

    def forged_status(path: Path) -> os.stat_result:
        if path == stage:
            return cast("os.stat_result", cast("object", ForeignStatus(recorded)))
        return native(path)

    monkeypatch.setattr(Path, "lstat", forged_status)
    assert not python_validation._jig_alias_stage_is_owned(  # pyright: ignore[reportPrivateUsage]
        stage,
        (recorded.st_dev, recorded.st_ino),
        expected_size=len(BINARY),
    )


def test_jig_alias_swap_with_forged_stage_status_preserves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged stage metadata must not publish a foreign replacement binary."""
    if not hasattr(os, "fchmod"):
        pytest.skip("descriptor chmod unsupported")
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    original = b"verified-jig-alias"
    _ = target.write_bytes(original)
    unrelated = tmp_path / "unrelated"
    sentinel = b"x" * len(BINARY)
    _ = unrelated.write_bytes(sentinel)
    retained = tmp_path / "retained-stage"
    native_mkstemp = tempfile.mkstemp
    native_lstat = Path.lstat
    native_fchmod = os.fchmod
    stages: list[Path] = []
    stage_statuses: list[os.stat_result] = []
    swapped = False

    def capture_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        descriptor, pathname = native_mkstemp(prefix=prefix, dir=dir)
        stages.append(Path(pathname))
        stage_statuses.append(native_lstat(stages[0]))
        return descriptor, pathname

    def swapping_chmod(descriptor: int, mode: int) -> None:
        nonlocal swapped
        native_fchmod(descriptor, mode)
        assert stages
        _ = stages[0].replace(retained)
        _ = unrelated.replace(stages[0])
        swapped = True

    def spoofing_lstat(path: Path) -> os.stat_result:
        if swapped and stages and path == stages[0]:
            forged = ForeignStatus(stage_statuses[0])
            forged.st_size = len(BINARY)
            return cast("os.stat_result", cast("object", forged))
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(tempfile, "mkstemp", capture_mkstemp)
        isolated.setattr(os, "fchmod", swapping_chmod)
        isolated.setattr(Path, "lstat", spoofing_lstat)
        with pytest.raises(python_validation.ProvisionError, match="temporary changed"):
            python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
                target, BINARY, windows=False
            )
    assert swapped
    assert len(stages) == 1
    assert stages[0].read_bytes() == sentinel
    assert retained.read_bytes() == BINARY
    assert target.read_bytes() == original


@pytest.mark.parametrize("receipt", ["descriptor", "path", "both"])
def test_jig_alias_temporary_rejects_foreign_status_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A forged stat proxy cannot bind one Jig temporary to its descriptor."""
    descriptor, name = tempfile.mkstemp(prefix=".ruff.", dir=tmp_path)
    temporary = Path(name)
    native_fstat = os.fstat
    native_lstat = Path.lstat

    def forged_fstat(fd: int) -> os.stat_result:
        observed = native_fstat(fd)
        if fd == descriptor and receipt in ("descriptor", "both"):
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    def forged_lstat(path: Path) -> os.stat_result:
        observed = native_lstat(path)
        if path == temporary and receipt in ("path", "both"):
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fstat", forged_fstat)
            isolated.setattr(Path, "lstat", forged_lstat)
            with pytest.raises(python_validation.ProvisionError, match="native"):
                _ = python_validation._admit_jig_alias_temporary(  # pyright: ignore[reportPrivateUsage]
                    descriptor, name, alias_root=tmp_path, prefix=".ruff."
                )
    finally:
        os.close(descriptor)
        temporary.unlink()
