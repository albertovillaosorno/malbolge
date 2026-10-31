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

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import provenance as provenance_module
from algorithms.diff.provenance import SourcePin
from algorithms.diff.provenance import SourcePinError
from algorithms.diff.provenance import SourcePinEvidence
from algorithms.diff.provenance import require_source_pin
from algorithms.diff.provenance import source_snapshot_evidence
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

_COMMIT = "0123456789abcdef0123456789abcdef01234567"
_EXPECTED_FILE_COUNT = 3
_WINDOWS_OS_NAME = "nt"


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


def test_source_pin_rejects_non_utf8_root_metadata(tmp_path: Path) -> None:
    """Selected roots must be UTF-8 encodable before source inspection."""
    bad_root = "src\ud800"
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = SourcePin("repo", _COMMIT, (bad_root,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = source_snapshot_evidence(tmp_path, (bad_root,))


@pytest.mark.parametrize("invalid", ["nul\x00root", "unpaired\ud800root"])
def test_source_snapshot_rejects_nonportable_root_path(
    tmp_path: Path, invalid: str
) -> None:
    """Native filesystem path errors must remain source-pin failures."""
    with pytest.raises(SourcePinError, match="root path"):
        _ = source_snapshot_evidence(tmp_path / invalid, ("src",))


@pytest.mark.parametrize("path", ["C:/absolute.c", "D:relative.c"])
def test_source_pin_rejects_windows_drive_roots_before_traversal(
    tmp_path: Path,
    path: str,
) -> None:
    """Pinned root labels cannot change path authority across host OSes."""
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = SourcePin("repo", _COMMIT, (path,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = source_snapshot_evidence(tmp_path, (path,))


@pytest.mark.parametrize("invalid", ["nul\x00repo", "unpaired\ud800repo"])
def test_source_pin_rejects_nonportable_repository_label(
    invalid: str,
) -> None:
    """Distributable pin names must not carry unsafe string encodings."""
    with pytest.raises(SourcePinError, match="repository"):
        _ = SourcePin(invalid, _COMMIT, ("src",), 1, "0" * 64)


def test_source_snapshot_rejects_non_utf8_walk_filename(
    tmp_path: Path,
) -> None:
    """Non-UTF-8 filesystem entries cannot leak raw encoding exceptions."""
    if os.name == _WINDOWS_OS_NAME:
        pytest.skip("raw-byte filesystem names require POSIX")
    _write(tmp_path, "src/valid.c", b"valid source")
    filename = os.fsencode(tmp_path / "src") + b"/invalid-\xff.c"
    descriptor = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _ = os.write(descriptor, b"non-UTF8 path")
    finally:
        os.close(descriptor)
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_source_pin_rejects_linked_directory_after_enumeration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject aliases introduced between path discovery and file reads."""
    _write(tmp_path, "src/nested/source.c", b"source bytes")
    original_pinned_files = cast(
        "Callable[[Path, tuple[str, ...]], tuple[Path, ...]]",
        vars(provenance_module)["_pinned_files"],
    )
    changed = False

    def replace_after_discovery(
        root: Path, roots: tuple[str, ...]
    ) -> tuple[Path, ...]:
        nonlocal changed
        files = original_pinned_files(root, roots)
        _ = (root / "src/nested").rename(root / "src/actual")
        try:
            (root / "src/nested").symlink_to(
                root / "src/actual", target_is_directory=True
            )
        except OSError:
            pytest.skip("directory symlinks unavailable")
        changed = True
        return files

    monkeypatch.setattr(
        provenance_module, "_pinned_files", replace_after_discovery
    )
    with pytest.raises(SourcePinError, match="symlink"):
        _ = source_snapshot_evidence(tmp_path, ("src",))
    _expect(changed, "post-enumeration alias fixture was not installed")


def test_source_pin_evidence_rejects_malformed_direct_construction() -> None:
    """Observed pin evidence uses the same count and digest domain as pins."""
    with pytest.raises(SourcePinError, match="positive integer"):
        _ = SourcePinEvidence(file_count=True, snapshot_sha256="0" * 64)
    with pytest.raises(SourcePinError, match="lowercase SHA-256"):
        _ = SourcePinEvidence(file_count=1, snapshot_sha256="A" * 64)


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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_pinned_source_root_status_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An inaccessible pin root cannot be normalized into a weaker error."""
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == tmp_path:
            message = "blocked pin root"
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_pinned_source_root_resolution_errors_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Do not leak invalid or cyclic root normalization from source-pin APIs."""
    _write(tmp_path, "README", b"pinned")
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked pin root resolution"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(
        SourcePinError, match="pinned source root resolution failed"
    ):
        _ = source_snapshot_evidence(tmp_path, ("README",))


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


def test_pinned_source_accepts_regular_nested_root(tmp_path: Path) -> None:
    """A valid multi-component source root remains eligible for hashing."""
    _write(tmp_path, "src/nested/leaf.c", b"valid source")
    evidence = source_snapshot_evidence(tmp_path, ("src/nested",))
    _expect(evidence.file_count == 1, "nested pinned root lost its file")


@pytest.mark.parametrize("outside", [False, True])
def test_pinned_source_rejects_linked_intermediate_root_component(
    tmp_path: Path,
    *,
    outside: bool,
) -> None:
    """Selected subpaths cannot traverse symlink ancestors."""
    root = tmp_path / "source"
    root.mkdir()
    actual = tmp_path / "outside" if outside else root / "real"
    _write(actual, "nested/leaf.c", b"secret source")
    try:
        (root / "link").symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")

    with pytest.raises(SourcePinError, match="symlink is not accepted"):
        _ = source_snapshot_evidence(root, ("link/nested",))


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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_pinned_entry_status_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An inaccessible pinned entry cannot disappear from source evidence."""
    blocked = tmp_path / "src" / "blocked.c"
    _write(tmp_path, "src/blocked.c", b"int blocked;\n")
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == blocked:
            message = "blocked pinned entry"
            raise failure_type(message)
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
    original_open = os.open

    def fail_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(file) == os.fspath(blocked):
            message = "blocked pinned source read"
            raise PermissionError(message)
        return original_open(file, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(SourcePinError, match="pinned source read failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_source_rejects_symlink_swapped_after_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-read status cannot admit a later foreign leaf pathname."""
    root = tmp_path / "source"
    root.mkdir()
    leaf = root / "README"
    _ = leaf.write_bytes(b"same byte content")
    foreign = tmp_path / "foreign"
    _ = foreign.write_bytes(b"same byte content")
    original_status = Path.lstat
    swapped = False

    def swap_after_status(path: Path) -> object:
        nonlocal swapped
        status = original_status(path)
        if path == leaf and not swapped:
            leaf.unlink()
            try:
                leaf.symlink_to(foreign)
            except OSError:
                pytest.skip("filesystem symlinks unavailable")
            swapped = True
        return status

    monkeypatch.setattr(Path, "lstat", swap_after_status)
    with pytest.raises(SourcePinError, match="pinned source read failed"):
        _ = source_snapshot_evidence(root, ("README",))
    _expect(swapped, "source pin symlink substitution did not execute")


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


def test_source_pin_rejects_nul_root_before_filesystem_access(
    tmp_path: Path,
) -> None:
    """Path metadata cannot defer embedded NUL failure to host path APIs."""
    nul_root = "src\x00hidden"
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = SourcePin("repo", _COMMIT, (nul_root,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = source_snapshot_evidence(tmp_path, (nul_root,))


def test_source_pin_rejects_overlapping_roots_before_tree_walk(
    tmp_path: Path,
) -> None:
    """Disjoint pin roots must be admitted without traversing duplicates."""
    roots = ("src", "src/nested")
    with pytest.raises(SourcePinError, match="must not overlap"):
        _ = SourcePin("repo", _COMMIT, roots, 1, "0" * 64)
    with pytest.raises(SourcePinError, match="must not overlap"):
        _ = source_snapshot_evidence(tmp_path, roots)


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
