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

"""Synthetic tests for exact external source revision pins."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.provenance import SourcePin
from algorithms.diff.provenance import SourcePinError
from algorithms.diff.provenance import require_source_pin
from algorithms.diff.provenance import source_snapshot_evidence
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

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


def test_pinned_source_root_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible pin root cannot be normalized into a weaker error."""
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == tmp_path:
            message = "blocked pin root"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_source_rejects_linked_root_when_supported(
    tmp_path: Path,
) -> None:
    """Do not resolve a linked pin root before applying provenance policy."""
    target = tmp_path / "target"
    _write(target, "README", b"release")
    _write(target, "src/a.c", b"int a;" + bytes((10,)))
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(SourcePinError, match="symlink is not accepted"):
        _ = source_snapshot_evidence(linked, ("README", "src"))


def test_pinned_snapshot_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recursive scan failure cannot disappear from a revision pin."""
    selected = tmp_path / "src"
    selected.mkdir()

    def fail_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = path, top_down, follow_symlinks
        assert on_error is not None
        _ = on_error(PermissionError("blocked pinned source"))
        return iter(())

    monkeypatch.setattr(Path, "walk", fail_walk)
    with pytest.raises(SourcePinError, match="pinned source traversal failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_entry_status_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible pinned entry cannot disappear from source evidence."""
    blocked = tmp_path / "src" / "blocked.c"
    _write(tmp_path, "src/blocked.c", b"int blocked;\n")
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == blocked:
            message = "blocked pinned entry"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_entry_read_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable admitted source file cannot leak a host exception."""
    blocked = tmp_path / "src" / "a.c"
    _write(tmp_path, "src/a.c", b"int a;")
    original_read = Path.read_bytes

    def fail_read(path: Path) -> bytes:
        if path == blocked:
            message = "blocked pinned source read"
            raise PermissionError(message)
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(SourcePinError, match="pinned source read failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


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


def test_source_pin_rejects_foreign_runtime_metadata() -> None:
    """Pins admit exact strings, immutable roots, and integer file counts."""
    with pytest.raises(SourcePinError, match="non-empty string"):
        _ = SourcePin(cast("str", object()), _COMMIT, ("src",), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="40 lowercase"):
        _ = SourcePin("repo", cast("str", object()), ("src",), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="positive integer"):
        _ = SourcePin(
            repository="repo",
            commit=_COMMIT,
            roots=("src",),
            file_count=True,
            snapshot_sha256="0" * 64,
        )
    with pytest.raises(SourcePinError, match="immutable tuple"):
        _ = SourcePin(
            "repo",
            _COMMIT,
            cast("tuple[str, ...]", cast("object", ["src"])),
            1,
            "0" * 64,
        )
    with pytest.raises(SourcePinError, match="lowercase SHA-256"):
        _ = SourcePin("repo", _COMMIT, ("src",), 1, cast("str", object()))


def test_snapshot_and_pin_public_inputs_fail_typed(tmp_path: Path) -> None:
    """Snapshot APIs validate roots and pins before filesystem dereference."""
    _write(tmp_path, "src/a.c", b"int a;" + bytes((10,)))
    with pytest.raises(SourcePinError, match="pathlib Path"):
        _ = source_snapshot_evidence(cast("Path", object()), ("src",))
    with pytest.raises(SourcePinError, match="immutable tuple"):
        _ = source_snapshot_evidence(
            tmp_path,
            cast("tuple[str, ...]", cast("object", ["src"])),
        )
    with pytest.raises(SourcePinError, match="unique and sorted"):
        _ = source_snapshot_evidence(tmp_path, ())
    with pytest.raises(SourcePinError, match="exact SourcePin"):
        _ = require_source_pin(tmp_path, cast("SourcePin", object()))
