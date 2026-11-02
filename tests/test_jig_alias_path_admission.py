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
