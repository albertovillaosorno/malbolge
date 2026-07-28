# File:
#   - test_provenance.py
# Path:
#   - algorithms/diff/tests/test_provenance.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic tests for exact external source revision pins.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Synthetic tests for exact external source revision pins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from algorithms.diff.provenance import SourcePin
from algorithms.diff.provenance import SourcePinError
from algorithms.diff.provenance import require_source_pin
from algorithms.diff.provenance import source_snapshot_evidence

if TYPE_CHECKING:
    from pathlib import Path

_COMMIT = "0123456789abcdef0123456789abcdef01234567"
_EXPECTED_FILE_COUNT = 3


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _pin(root: Path) -> SourcePin:
    evidence = source_snapshot_evidence(root, ("README", "src"))
    return SourcePin(
        repository="https://example.invalid/source.git",
        commit=_COMMIT,
        roots=("README", "src"),
        file_count=evidence.file_count,
        snapshot_sha256=evidence.snapshot_sha256,
    )


def test_pinned_snapshot_accepts_exact_selected_tree(tmp_path: Path) -> None:
    """Bind path set and bytes while ignoring unrelated external assets."""
    _write(tmp_path, "README", b"release")
    _write(tmp_path, "src/a.c", b"int a;\n")
    _write(tmp_path, "src/b.h", b"#define B 1\n")
    _write(tmp_path, "data/external.bin", b"not part of source pin")
    pin = _pin(tmp_path)

    observed = require_source_pin(tmp_path, pin)

    _expect(
        observed.file_count == _EXPECTED_FILE_COUNT,
        "pinned source count changed",
    )


def test_pinned_snapshot_rejects_byte_or_path_change(tmp_path: Path) -> None:
    """Reject local mutation even when the named commit stays unchanged."""
    _write(tmp_path, "README", b"release")
    _write(tmp_path, "src/a.c", b"int a;\n")
    pin = _pin(tmp_path)
    _write(tmp_path, "src/a.c", b"int changed;\n")

    with pytest.raises(SourcePinError, match="snapshot mismatch"):
        _ = require_source_pin(tmp_path, pin)

    _write(tmp_path, "src/a.c", b"int a;\n")
    _write(tmp_path, "src/new.c", b"int new_file;\n")
    with pytest.raises(SourcePinError, match="file count mismatch"):
        _ = require_source_pin(tmp_path, pin)


def test_missing_or_symlinked_selected_root_fails_closed(
    tmp_path: Path,
) -> None:
    """Require concrete selected roots before computing source identity."""
    _write(tmp_path, "README", b"release")
    pin = SourcePin(
        repository="https://example.invalid/source.git",
        commit=_COMMIT,
        roots=("README", "src"),
        file_count=2,
        snapshot_sha256="0" * 64,
    )

    with pytest.raises(SourcePinError, match="missing pinned source root"):
        _ = require_source_pin(tmp_path, pin)
