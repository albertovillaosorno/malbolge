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

from dataclasses import replace
import os
from pathlib import Path
import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - bounded no-shell FIFO regression.
import sys
import textwrap
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

from algorithms.diff import exact as exact_module
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import materialize_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.exact import snapshot_tree_excluding
from algorithms.diff.model import ExactAuthoringPlan
from algorithms.diff.model import ExactInstruction
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import FileRecord
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.model import TreeModelError
from algorithms.diff.model import TreeSnapshot
import pytest

_MOVED_SOURCE = "rename-me.txt"
_PATCH_PATH = "patch.txt"
_PATCH_PREFIX = b"0123456789abcdef" * 8
_PATCH_INSERTION = b"<inserted-target-only>"
_PATCH_SUFFIX = b"fedcba9876543210" * 8
_RUNTIME_DATA = b"runtime-data"
_RUNTIME_EXTRA = b"runtime-extra"
_FOREIGN_OUTPUT = b"foreign"
_POSIX_OS_NAME = "posix"
_MISSING_PLAN_TARGET = "missing"
_EXTRA_PLAN_TARGET = "extra"
_CLOSE_FAILURE_NOTE = "descriptor close also failed"
_TREE_FILE_CONTEXT = "tree file"


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


@pytest.mark.parametrize(
    "invalid_path",
    [
        "../escape",
        "/absolute",
        "src//file",
        "src\\file",
        "C:/unsafe",
        "C:relative",
        "src\x00file",
        "src\ud800file",
    ],
)
def test_exact_authoring_metadata_rejects_noncanonical_paths(
    invalid_path: str,
) -> None:
    """Direct model construction rejects invalid tree paths before any I/O."""
    expected_sha256 = "0" * 64
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = FileRecord(path=invalid_path, sha256=expected_sha256, size=0)
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = ExactInstruction(
            output_path=invalid_path,
            kind=ExactInstructionKind.LITERAL_ORACLE,
            expected_sha256=expected_sha256,
            literal=b"",
        )
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = ExactInstruction(
            output_path="output.bin",
            kind=ExactInstructionKind.COPY_SOURCE,
            expected_sha256=expected_sha256,
            source_path=invalid_path,
        )
    empty = TreeSnapshot(files=())
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = ExactAuthoringPlan(
            source=empty,
            target=empty,
            instructions=(),
            passthrough_roots=(invalid_path,),
        )


@pytest.mark.parametrize(
    "invalid_root", ["dynamic\x00tail", "dynamic\ud800tail", "C:/escape"]
)
def test_exact_passthrough_roots_fail_before_source_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_root: str,
) -> None:
    """Malformed paths cannot begin tree traversal before policy rejection."""
    source, oracle = _synthetic_pair(tmp_path)

    def deny_snapshot(root: Path) -> TreeSnapshot:
        message = f"source snapshot ran before root validation: {root}"
        raise AssertionError(message)

    with pytest.raises(TreeModelError, match="relative path"):
        _ = snapshot_tree_excluding(source, (invalid_root,))
    monkeypatch.setattr(exact_module, "snapshot_tree", deny_snapshot)
    with pytest.raises(TreeModelError, match="relative path"):
        _ = build_exact_plan(source, oracle, passthrough_roots=(invalid_root,))


def test_direct_tree_snapshot_rejects_file_ancestor_collisions() -> None:
    """Snapshot metadata cannot describe a file acting as a directory."""
    digest = "0" * 64
    ancestor = FileRecord("src/module", digest, 1)
    descendant = FileRecord("src/module/dependency", digest, 1)
    with pytest.raises(TreeModelError, match="ancestor"):
        _ = TreeSnapshot(files=(ancestor, descendant))


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


def _deny_file_open(
    monkeypatch: pytest.MonkeyPatch,
    blocked: Path,
    *,
    fail_on: int,
    label: str,
) -> None:
    """Fail one exact file-open after the chosen read admission count."""
    original_open = os.open
    attempts = 0

    def deny_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal attempts
        if os.fspath(file) == os.fspath(blocked):
            attempts += 1
            if attempts >= fail_on:
                message = f"blocked {label} read"
                raise PermissionError(message)
        return original_open(file, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", deny_open)


def test_exact_planning_wraps_oracle_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later oracle read failure stays inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    blocked = oracle / "created.txt"
    _deny_file_open(monkeypatch, blocked, fail_on=2, label="oracle replay")
    with pytest.raises(ExactTreeError, match="tree file read failed"):
        _ = build_exact_plan(source, oracle)


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


@pytest.mark.parametrize("change_source", [True, False])
def test_exact_authoring_rejects_tree_drift_during_instruction_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    change_source: bool,
) -> None:
    """A plan cannot bind stale source or oracle snapshots after replay."""
    source, oracle = _synthetic_pair(tmp_path)
    original_read = exact_module.read_exact_regular_file
    changed = False

    def read_then_mutate(path: Path, context: str) -> bytes:
        nonlocal changed
        data = original_read(path, context)
        if (
            not changed
            and path == oracle / "modify.txt"
            and context == _TREE_FILE_CONTEXT
        ):
            changed = True
            if change_source:
                _write(source, "keep.txt", b"changed while authoring\n")
            else:
                _write(oracle, "new-target-after-snapshot.txt", b"new oracle\n")
        return data

    monkeypatch.setattr(
        exact_module, "read_exact_regular_file", read_then_mutate
    )
    expected = "source tree" if change_source else "oracle tree"
    with pytest.raises(ExactTreeError, match=expected):
        _ = build_exact_plan(source, oracle)
    _expect(changed, "authoring test did not reach its replay trigger")


def test_exact_plan_rejects_static_target_inside_passthrough_root(
    tmp_path: Path,
) -> None:
    """Static instructions cannot compete with dynamic passthrough copies."""
    source, oracle = _synthetic_pair(tmp_path)
    valid = build_exact_plan(source, oracle)
    with pytest.raises(TreeModelError, match=r"static target.*passthrough"):
        _ = replace(valid, passthrough_roots=("assets",))


def test_exact_authoring_plan_rejects_duplicate_output_instructions(
    tmp_path: Path,
) -> None:
    """No output can be assigned two potentially conflicting instructions."""
    source, oracle = _synthetic_pair(tmp_path)
    valid = build_exact_plan(source, oracle)
    duplicate = valid.instructions[0]

    with pytest.raises(TreeModelError, match="unique output paths"):
        _ = ExactAuthoringPlan(
            source=valid.source,
            target=valid.target,
            instructions=(*valid.instructions, duplicate),
            passthrough_roots=valid.passthrough_roots,
        )


@pytest.mark.parametrize("variant", ["missing", "extra", "digest"])
def test_exact_plan_requires_exact_target_instruction_mapping(
    tmp_path: Path,
    variant: str,
) -> None:
    """Direct plans cannot defer target/instruction mismatch until staging."""
    source, oracle = _synthetic_pair(tmp_path)
    valid = build_exact_plan(source, oracle)
    if variant == _MISSING_PLAN_TARGET:
        instructions = valid.instructions[:-1]
    elif variant == _EXTRA_PLAN_TARGET:
        additional = replace(valid.instructions[0], output_path="unlisted.bin")
        instructions = (*valid.instructions, additional)
    else:
        wrong = replace(valid.instructions[0], expected_sha256="0" * 64)
        instructions = (wrong, *valid.instructions[1:])

    with pytest.raises(TreeModelError, match="target snapshot"):
        _ = ExactAuthoringPlan(
            source=valid.source,
            target=valid.target,
            instructions=instructions,
            passthrough_roots=valid.passthrough_roots,
        )


@pytest.mark.parametrize(
    "invalid_roots",
    [
        ("dynamic", "dynamic"),
        ("z-activity", "a-activity"),
        ("dynamic", "dynamic/nested"),
    ],
)
def test_exact_plan_rejects_ambiguous_passthrough_root_topology(
    tmp_path: Path,
    invalid_roots: tuple[str, ...],
) -> None:
    """Direct exact plans cannot bypass the builder's dynamic-root policy."""
    source, oracle = _synthetic_pair(tmp_path)
    valid = build_exact_plan(source, oracle)
    with pytest.raises(TreeModelError, match="passthrough roots"):
        _ = ExactAuthoringPlan(
            source=valid.source,
            target=valid.target,
            instructions=valid.instructions,
            passthrough_roots=invalid_roots,
        )


def test_exact_materialization_wraps_instruction_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replay source read failure cannot leak a host filesystem exception."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    blocked = source / _MOVED_SOURCE
    _deny_file_open(monkeypatch, blocked, fail_on=2, label="instruction")
    output = tmp_path / "result"
    with pytest.raises(ExactTreeError, match="instruction source read failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "instruction read failure published output")


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


@pytest.mark.parametrize("rewrite_existing", [True, False])
def test_exact_rejects_static_source_drift_after_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    rewrite_existing: bool,
) -> None:
    """Do not publish if source files change while output is being staged."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    staging = tmp_path / ".result.staging"

    def snapshot_then_change_source(root: Path) -> TreeSnapshot:
        measured = snapshot_tree(root)
        if root == staging:
            if rewrite_existing:
                _write(source, "keep.txt", b"changed after staging\n")
            else:
                _write(source, "new-after-staging.txt", b"new static file\n")
        return measured

    monkeypatch.setattr(
        exact_module, "snapshot_tree", snapshot_then_change_source
    )
    with pytest.raises(ExactTreeError, match="source tree"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "source drift published the exact target")
    _expect(not staging.exists(), "source drift left the exact staging tree")


def test_exact_allows_dynamic_source_changes_after_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A runtime passthrough change does not change exact static admission."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle, passthrough_roots=("assets",))
    old_data = (source / "assets/blob.bin").read_bytes()
    staging = tmp_path / ".result.staging"

    def snapshot_then_change_runtime(root: Path) -> TreeSnapshot:
        measured = snapshot_tree(root)
        if root == staging:
            _write(source, "assets/blob.bin", b"new runtime payload")
        return measured

    monkeypatch.setattr(
        exact_module, "snapshot_tree", snapshot_then_change_runtime
    )
    output = tmp_path / "result"
    materialize_exact_plan(source, plan, output)
    _expect(
        (output / "assets/blob.bin").read_bytes() == old_data,
        "output did not preserve the staged runtime payload",
    )
    _expect(
        snapshot_tree_excluding(output, ("assets",)) == plan.target,
        "runtime edit altered exact static target",
    )


def test_exact_rejects_linked_source_path_ancestor_before_read(
    tmp_path: Path,
) -> None:
    """An excluded dynamic alias cannot authorize an exact source read."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "real/file.bin", b"source")
    _write(source, "dynamic/keep.bin", b"unverified")
    _write(oracle, "output.bin", b"source")
    alias = source / "dynamic" / "alias"
    try:
        alias.symlink_to(source / "real", target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    target = snapshot_tree(oracle)
    source_snapshot = snapshot_tree_excluding(source, ("dynamic",))
    instruction = ExactInstruction(
        output_path="output.bin",
        kind=ExactInstructionKind.COPY_SOURCE,
        expected_sha256=target.files[0].sha256,
        source_path="dynamic/alias/file.bin",
    )
    plan = ExactAuthoringPlan(
        source=source_snapshot,
        target=target,
        instructions=(instruction,),
        passthrough_roots=("dynamic",),
    )
    output = tmp_path / "out"

    with pytest.raises(ExactTreeError, match="linked tree path component"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "linked source ancestor published output")


@pytest.mark.parametrize("unsafe_suffix", ["\x00", "\ud800"])
def test_exact_rejects_nonfilesystem_root_metadata(
    tmp_path: Path,
    unsafe_suffix: str,
) -> None:
    """Exact entrypoints cannot leak host path exceptions before staging."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    invalid = tmp_path / f"broken{unsafe_suffix}"

    with pytest.raises(ExactTreeError, match="filesystem path"):
        _ = snapshot_tree(invalid)
    with pytest.raises(ExactTreeError, match="filesystem path"):
        _ = build_exact_plan(invalid, oracle)
    with pytest.raises(ExactTreeError, match="filesystem path"):
        materialize_exact_plan(source, plan, invalid)
    _expect(not invalid.exists(), "malformed root published output")


@pytest.mark.skipif(os.name != _POSIX_OS_NAME, reason="POSIX raw path bytes")
def test_exact_roots_preserve_surrogateescaped_host_names(
    tmp_path: Path,
) -> None:
    """Real non-UTF-8 host filenames remain valid filesystem roots."""
    source = tmp_path / os.fsdecode(b"source-\xff")
    oracle = tmp_path / "oracle"
    output = tmp_path / os.fsdecode(b"output-\xff")
    _write(source, "file.bin", b"source")
    _write(oracle, "file.bin", b"target")

    plan = build_exact_plan(source, oracle)
    materialize_exact_plan(source, plan, output)

    _expect(snapshot_tree(output) == snapshot_tree(oracle), "raw root mismatch")


@pytest.mark.parametrize("linked_parent", [False, True])
def test_exact_materialization_rejects_output_inside_source_tree(
    tmp_path: Path,
    *,
    linked_parent: bool,
) -> None:
    """Staging and publication may never mutate the candidate source tree."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output_parent = source
    if linked_parent:
        output_parent = tmp_path / "source-alias"
        try:
            output_parent.symlink_to(source, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
    output = output_parent / "published"
    baseline = snapshot_tree(source)

    with pytest.raises(ExactTreeError, match=r"output root.*source tree"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "nested output was published")
    _expect(snapshot_tree(source) == baseline, "nested output mutated source")
    _expect(
        not (source / ".published.exact-staging").exists(),
        "nested output left staging inside source",
    )


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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_materialization_wraps_output_root_resolution_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Keep output-root resolution failures inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == output:
            message = "blocked exact output"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(ExactTreeError, match="output root resolution failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "output resolution failure published output")


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_materialization_wraps_tree_path_resolution_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Keep source-path resolution failures inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    blocked = source / _MOVED_SOURCE
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == blocked:
            message = "blocked source path"
            raise failure_type(message)
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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_materialization_wraps_output_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A staging write failure stays inside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    blocked = tmp_path / ".result.staging" / "created.txt"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked staging write"
            raise failure_type(message)
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with pytest.raises(ExactTreeError, match="instruction output write failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "write failure published output")
    _expect(not (tmp_path / ".result.staging").exists(), "staging survived")


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_materialization_wraps_staging_directory_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Staging mkdir failures cannot leak outside the exact-tree boundary."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    staging = tmp_path / ".result.staging"
    original_mkdir = Path.mkdir

    def fail_mkdir(
        path: Path,
        mode: int = 0o777,
        *,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == staging:
            message = "blocked staging directory"
            raise failure_type(message)
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    with pytest.raises(ExactTreeError, match="staging root creation failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "staging mkdir failure published output")
    _expect(not staging.exists(), "staging mkdir failure left staging")


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_cleanup_failure_is_reported_with_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A failed staging cleanup cannot hide or replace the primary failure."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    blocked = tmp_path / ".result.staging" / "created.txt"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked staging write"
            raise PermissionError(message)
        return original_write(path, data)

    def fail_cleanup(path: Path) -> None:
        _ = path
        message = "blocked staging cleanup"
        raise failure_type(message)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        ExactTreeError,
        match=r"instruction output write failed.*staging cleanup failed",
    ):
        materialize_exact_plan(source, plan, output)


def test_exact_staging_status_failure_is_not_reported_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible staging path cannot be mistaken for an absent path."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    staging = tmp_path / ".result.staging"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == staging:
            message = "blocked staging status"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(ExactTreeError, match="staging root status failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "status failure published output")


def test_exact_materialization_rejects_existing_output(tmp_path: Path) -> None:
    """Never overwrite an existing output tree implicitly."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    output.mkdir()

    with pytest.raises(ExactTreeError, match="already exists"):
        materialize_exact_plan(source, plan, output)


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_exact_tree_root_resolution_failure_stays_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Invalid host root resolution never escapes the exact-tree boundary."""
    root = tmp_path / "tree"
    root.mkdir()
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == root:
            message = "blocked exact root resolution"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(ExactTreeError, match="tree root resolution failed"):
        _ = snapshot_tree(root)


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
    _deny_file_open(monkeypatch, blocked, fail_on=1, label="exact")
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


def test_snapshot_read_error_remains_primary_after_close_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A secondary close failure must not hide the original read failure."""
    root = tmp_path / "tree"
    root.mkdir()
    _ = (root / "leaf").write_bytes(b"normal")
    original_close = os.close

    def fail_read(descriptor: int, count: int) -> bytes:
        _ = descriptor, count
        message = "injected read denial"
        raise PermissionError(message)

    def fail_close(descriptor: int) -> None:
        original_close(descriptor)
        message = "injected close denial"
        raise OSError(message)

    monkeypatch.setattr(os, "read", fail_read)
    monkeypatch.setattr(os, "close", fail_close)
    with pytest.raises(ExactTreeError, match="tree entry read failed") as error:
        _ = snapshot_tree(root)
    _expect(
        isinstance(error.value.__cause__, PermissionError),
        "file close error replaced the primary read error",
    )
    notes = cast("list[str]", getattr(error.value, "__notes__", []))
    _expect(
        any(_CLOSE_FAILURE_NOTE in note for note in notes),
        "close failure was not attached to the typed primary error",
    )


def test_snapshot_rejects_file_swapped_to_symlink_after_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A regular-file status cannot authorize a later linked file read."""
    root = tmp_path / "tree"
    root.mkdir()
    leaf = root / "data.bin"
    _ = leaf.write_bytes(b"original")
    foreign = tmp_path / "foreign.bin"
    _ = foreign.write_bytes(b"foreign!")
    original_status = Path.lstat
    swapped = False

    def swap_after_status(path: Path) -> os.stat_result:
        nonlocal swapped
        observed = original_status(path)
        if path == leaf and not swapped:
            leaf.unlink()
            try:
                leaf.symlink_to(foreign)
            except OSError:
                pytest.skip("filesystem leaf symlinks are unavailable")
            swapped = True
        return observed

    monkeypatch.setattr(Path, "lstat", swap_after_status)
    with pytest.raises(ExactTreeError, match="tree entry"):
        _ = snapshot_tree(root)
    _expect(swapped, "regular-file admission race did not execute")


def test_snapshot_rejects_writerless_fifo_swap_without_blocking(
    tmp_path: Path,
) -> None:
    """A FIFO substituted after lstat must not block an untrusted read."""
    if os.name != _POSIX_OS_NAME or not hasattr(os, "mkfifo"):
        pytest.skip("nonblocking FIFO admission requires POSIX")
    root = tmp_path / "tree"
    root.mkdir()
    _ = (root / "leaf").write_bytes(b"normal")
    script = textwrap.dedent(
        """\
        import os
        import sys
        from pathlib import Path
        from algorithms.diff.exact import ExactTreeError, snapshot_tree

        root = Path(sys.argv[1])
        leaf = root / "leaf"
        lstat = Path.lstat
        changed = [False]

        def swap(path):
            status = lstat(path)
            if path == leaf and not changed[0]:
                changed[0] = True
                leaf.unlink()
                os.mkfifo(leaf)
            return status

        Path.lstat = swap
        try:
            snapshot_tree(root)
        except ExactTreeError:
            sys.exit(0)
        sys.exit(2)
        """
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(sys.path)
    # A previous path-based read blocked forever here with no FIFO writer.
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - explicit argv and shell=False.
        [sys.executable, "-c", script, str(root)],
        shell=False,
        check=False,
        capture_output=True,
        timeout=2.0,
        env=environment,
    )
    _expect(
        completed.returncode == 0,
        f"FIFO read admission did not reject: {completed.stderr!r}",
    )


def test_snapshot_rejects_leaf_replacement_during_descriptor_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid opened inode cannot authorize a replaced pathname afterward."""
    root = tmp_path / "tree"
    root.mkdir()
    leaf = root / "leaf"
    _ = leaf.write_bytes(b"old bytes")
    foreign = tmp_path / "foreign"
    _ = foreign.write_bytes(b"foreign!!")
    original_read = os.read
    changed = False

    def replace_after_open(descriptor: int, count: int) -> bytes:
        nonlocal changed
        fragment = original_read(descriptor, count)
        if not changed:
            leaf.unlink()
            leaf.symlink_to(foreign)
            changed = True
        return fragment

    monkeypatch.setattr(os, "read", replace_after_open)
    with pytest.raises(ExactTreeError, match="regular file identity"):
        _ = snapshot_tree(root)
    _expect(changed, "post-open pathname replacement did not execute")


def test_snapshot_rejects_same_inode_rewrite_during_descriptor_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changed contents must reject even if the inode and size are stable."""
    root = tmp_path / "tree"
    root.mkdir()
    leaf = root / "leaf"
    _ = leaf.write_bytes(b"old bytes")
    original_read = os.read
    changed = False

    def rewrite_after_open(descriptor: int, count: int) -> bytes:
        nonlocal changed
        fragment = original_read(descriptor, count)
        if not changed:
            _ = leaf.write_bytes(b"new bytes")
            changed = True
        return fragment

    monkeypatch.setattr(os, "read", rewrite_after_open)
    with pytest.raises(ExactTreeError, match="inode changed"):
        _ = snapshot_tree(root)
    _expect(changed, "in-place rewrite did not execute")


def test_snapshot_excluding_does_not_read_passthrough_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Static verification must not read a fully excluded dynamic subtree."""
    root = tmp_path / "tree"
    _write(root, "static.bin", b"static")
    dynamic = root / "external" / "game.bin"
    _write(root, "external/game.bin", b"dynamic")
    _deny_file_open(monkeypatch, dynamic, fail_on=1, label="passthrough")
    snapshot = snapshot_tree_excluding(root, ("external",))
    _expect(
        tuple(record.path for record in snapshot.files) == ("static.bin",),
        "excluded passthrough leaked into static snapshot",
    )


def test_snapshot_excluding_nested_root_preserves_static_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prune only the configured nested root, not its static parent siblings."""
    root = tmp_path / "tree"
    _write(root, "external/keep.bin", b"keep")
    dynamic = root / "external" / "data" / "game.bin"
    _write(root, "external/data/game.bin", b"dynamic")
    _deny_file_open(monkeypatch, dynamic, fail_on=1, label="nested passthrough")
    snapshot = snapshot_tree_excluding(root, ("external/data",))
    paths = tuple(record.path for record in snapshot.files)
    _expect(
        paths == ("external/keep.bin",),
        "nested passthrough pruning removed a static sibling",
    )


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
