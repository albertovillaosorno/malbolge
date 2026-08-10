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
#   - Exact-baseline tests for the generic source-bound diff authoring model.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Exact-baseline tests for the generic source-bound diff authoring model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from algorithms.diff import exact as exact_module
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import materialize_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
import pytest

_MOVED_SOURCE = "rename-me.txt"
_PATCH_PATH = "patch.txt"
_PATCH_PREFIX = b"0123456789abcdef" * 8
_PATCH_INSERTION = b"<inserted-target-only>"
_PATCH_SUFFIX = b"fedcba9876543210" * 8
_RUNTIME_DATA = b"runtime-data"
_RUNTIME_EXTRA = b"runtime-extra"
_FOREIGN_OUTPUT = b"foreign"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, relative_path: str, data: bytes) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _synthetic_pair(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    source.mkdir()
    oracle.mkdir()

    _write(source, "keep.txt", b"stable\n")
    _write(source, _MOVED_SOURCE, b"same bytes after move\n")
    _write(source, "modify.txt", b"old\n")
    _write(source, "delete.txt", b"gone\n")
    _write(source, "assets/blob.bin", bytes(range(32)))
    _write(source, _PATCH_PATH, _PATCH_PREFIX + _PATCH_SUFFIX)

    _write(oracle, "keep.txt", b"stable\n")
    _write(oracle, "moved.txt", b"same bytes after move\n")
    _write(oracle, "modify.txt", b"new\x00bytes\n")
    _write(oracle, "created.txt", b"created\n")
    _write(oracle, "assets/blob.bin", bytes(range(32)))
    _write(
        oracle,
        _PATCH_PATH,
        _PATCH_PREFIX + _PATCH_INSERTION + _PATCH_SUFFIX,
    )
    return source, oracle


def test_exact_plan_reconstructs_synthetic_tree_byte_for_byte(
    tmp_path: Path,
) -> None:
    """Cover unchanged, moved, patched, created, deleted, and binary files."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "out" / "result"

    materialize_exact_plan(source, plan, output)

    _expect(snapshot_tree(output) == snapshot_tree(oracle), "tree mismatch")
    _expect(not (output / "delete.txt").exists(), "deleted file survived")
    by_output = {
        instruction.output_path: instruction
        for instruction in plan.instructions
    }
    moved = by_output["moved.txt"]
    modified = by_output["modify.txt"]
    created = by_output["created.txt"]
    patched = by_output[_PATCH_PATH]
    _expect(moved.kind is ExactInstructionKind.COPY_SOURCE, "move not reused")
    _expect(moved.source_path == _MOVED_SOURCE, "wrong move source")
    _expect(
        modified.kind is ExactInstructionKind.LITERAL_ORACLE,
        "small modified file was not literal",
    )
    _expect(
        created.kind is ExactInstructionKind.LITERAL_ORACLE,
        "created file was not literal",
    )
    _expect(
        patched.kind is ExactInstructionKind.PATCH_SOURCE,
        "large modified file did not reuse source spans",
    )
    _expect(
        any(isinstance(segment, SourceSlice) for segment in patched.segments),
        "patch contains no source slices",
    )
    literal_bytes = sum(
        len(segment.data)
        for segment in patched.segments
        if isinstance(segment, OracleLiteral)
    )
    _expect(
        literal_bytes == len(_PATCH_INSERTION),
        "patch retained more literal bytes than the insertion",
    )


def test_exact_plan_is_deterministic(tmp_path: Path) -> None:
    """Produce the same immutable plan and instruction order repeatedly."""
    source, oracle = _synthetic_pair(tmp_path)

    first = build_exact_plan(source, oracle)
    second = build_exact_plan(source, oracle)
    observed_paths = tuple(item.output_path for item in first.instructions)
    expected_paths = tuple(sorted(observed_paths))

    _expect(first == second, "repeated plans differ")
    _expect(
        observed_paths == expected_paths,
        "instructions are not path sorted",
    )


def test_exact_materialization_rejects_changed_source_before_output(
    tmp_path: Path,
) -> None:
    """Reject a changed exact source before publishing a target tree."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    _write(source, "keep.txt", b"changed after generation\n")
    output = tmp_path / "result"

    with pytest.raises(ExactTreeError, match="source tree"):
        materialize_exact_plan(source, plan, output)

    _expect(not output.exists(), "rejected output was published")
    staging = tmp_path / ".result.staging"
    _expect(not staging.exists(), "rejected staging tree survived")


def test_exact_materialization_rejects_linked_source_root_when_supported(
    tmp_path: Path,
) -> None:
    """Materialization must not erase a source-root link before verification."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    linked = tmp_path / "linked-source"
    try:
        linked.symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")
    output = tmp_path / "result"

    with pytest.raises(ExactTreeError, match="tree root must not be linked"):
        materialize_exact_plan(linked, plan, output)
    _expect(not output.exists(), "linked-source rejection published output")


def test_exact_materialization_wraps_output_root_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep output-root resolution failures inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == output:
            message = "blocked exact output"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(ExactTreeError, match="output root resolution failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "output resolution failure published output")


def test_exact_materialization_wraps_tree_path_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep source-path resolution failures inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    blocked = source / _MOVED_SOURCE
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == blocked:
            message = "blocked source path"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    output = tmp_path / "result"
    with pytest.raises(ExactTreeError, match="tree path resolution failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "resolution failure published output")


def test_exact_publication_collision_preserves_foreign_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late destination race cannot be replaced by exact publication."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"

    def collide(staging: Path, destination: Path) -> None:
        _ = staging
        destination.mkdir()
        _ = (destination / "foreign.txt").write_bytes(_FOREIGN_OUTPUT)
        raise FileExistsError(destination)

    monkeypatch.setattr(exact_module, "publish_directory_no_replace", collide)
    with pytest.raises(ExactTreeError, match="output publication failed"):
        materialize_exact_plan(source, plan, output)

    assert (output / "foreign.txt").read_bytes() == _FOREIGN_OUTPUT
    assert not (tmp_path / ".result.staging").exists()


def test_exact_materialization_rejects_existing_output(tmp_path: Path) -> None:
    """Never overwrite an existing output tree implicitly."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    output.mkdir()

    with pytest.raises(ExactTreeError, match="already exists"):
        materialize_exact_plan(source, plan, output)


def test_snapshot_root_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible root cannot be reported as merely non-directory."""
    root = tmp_path / "tree"
    root.mkdir()
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == root:
            message = "blocked exact root"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(ExactTreeError, match="tree root status failed"):
        _ = snapshot_tree(root)


def test_snapshot_rejects_linked_root_when_supported(tmp_path: Path) -> None:
    """A linked root cannot erase the exact tree boundary during resolution."""
    target = tmp_path / "target"
    target.mkdir()
    _ = (target / "payload.txt").write_bytes(b"payload")
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(ExactTreeError, match="tree root must not be linked"):
        _ = snapshot_tree(linked)


def test_snapshot_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recursive scan failure cannot disappear from exact tree identity."""
    root = tmp_path / "tree"
    root.mkdir()

    def fail_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = path, top_down, follow_symlinks
        assert on_error is not None
        _ = on_error(PermissionError("blocked exact tree"))
        return iter(())

    monkeypatch.setattr(Path, "walk", fail_walk)
    with pytest.raises(ExactTreeError, match="tree traversal failed"):
        _ = snapshot_tree(root)


def test_snapshot_entry_status_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible discovered entry cannot vanish from exact identity."""
    root = tmp_path / "tree"
    root.mkdir()
    blocked = root / "blocked.txt"
    _ = blocked.write_text("evidence", encoding="utf-8")
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == blocked:
            message = "blocked exact entry"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(ExactTreeError, match="tree entry status failed"):
        _ = snapshot_tree(root)


def test_snapshot_entry_read_errors_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable regular file cannot leak a host filesystem exception."""
    root = tmp_path / "tree"
    root.mkdir()
    blocked = root / "blocked.txt"
    _ = blocked.write_bytes(b"evidence")
    original_read = Path.read_bytes

    def fail_read(path: Path) -> bytes:
        if path == blocked:
            message = "blocked exact read"
            raise PermissionError(message)
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(ExactTreeError, match="tree entry read failed"):
        _ = snapshot_tree(root)


def test_snapshot_rejects_symlink_when_supported(tmp_path: Path) -> None:
    """Do not silently dereference source-tree symlinks."""
    root = tmp_path / "tree"
    root.mkdir()
    target = root / "target.txt"
    _ = target.write_bytes(b"target")
    link = root / "link.txt"
    try:
        link.symlink_to(target.name)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(ExactTreeError, match="symlinks"):
        _ = snapshot_tree(root)


def test_passthrough_root_is_dynamic_after_exact_authoring(
    tmp_path: Path,
) -> None:
    """Preserve external input while exact-gating the transformed tree."""
    source, oracle = _synthetic_pair(tmp_path)
    _write(source, "external/game.bin", b"authoring-data")
    _write(oracle, "external/game.bin", b"authoring-data")
    plan = build_exact_plan(
        source,
        oracle,
        passthrough_roots=("external",),
    )
    _write(source, "external/game.bin", _RUNTIME_DATA)
    _write(source, "external/extra.bin", _RUNTIME_EXTRA)
    output = tmp_path / "passthrough-out"

    materialize_exact_plan(source, plan, output)

    _expect(
        (output / "external/game.bin").read_bytes() == _RUNTIME_DATA,
        "passthrough file was pinned to authoring bytes",
    )
    _expect(
        (output / "external/extra.bin").read_bytes() == _RUNTIME_EXTRA,
        "passthrough candidate-only file was lost",
    )
    _expect(
        all(
            not item.path.startswith("external/") for item in plan.source.files
        ),
        "passthrough path leaked into static source snapshot",
    )


def test_passthrough_authoring_requires_matching_source_and_oracle(
    tmp_path: Path,
) -> None:
    """Prove the dynamic policy reproduces the authoring baseline initially."""
    source, oracle = _synthetic_pair(tmp_path)
    _write(source, "external/game.bin", b"source-data")
    _write(oracle, "external/game.bin", b"different-oracle-data")

    with pytest.raises(ExactTreeError, match="passthrough roots differ"):
        _ = build_exact_plan(
            source,
            oracle,
            passthrough_roots=("external",),
        )
