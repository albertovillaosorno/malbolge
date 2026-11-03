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

import builtins
import hashlib
import ntpath
import os
import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - bounded no-shell FIFO regression.
import sys
import textwrap
from dataclasses import replace
from pathlib import Path, PurePosixPath
from types import MemberDescriptorType, SimpleNamespace
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

import pytest
from algorithms.diff import exact as exact_module
from algorithms.diff.exact import (
    ExactTreeError,
    build_exact_plan,
    materialize_exact_plan,
    snapshot_tree,
    snapshot_tree_excluding,
)
from algorithms.diff.model import (
    ExactAuthoringPlan,
    ExactInstruction,
    ExactInstructionKind,
    FileRecord,
    OracleLiteral,
    SourceSlice,
    TreeModelError,
    TreeSnapshot,
)

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
_COPY_SIZE_CASE = "copy-size"
_PATCH_RANGE_CASE = "patch-range"
_LITERAL_SIZE_CASE = "literal-size"
_LITERAL_DIGEST_CASE = "literal-digest"
_SHORT_WRITE = "short"
_EXACT_POSTCLOSE_READS = 3
_EXACT_NATIVE_CLOSE = "native"
_EXACT_NATIVE_CLOSE_DETAIL = "native close failure"
_EXACT_NOTES_ATTRIBUTE = "__notes__"
_EXACT_INPLACE_REWRITE = "inplace-rewrite"
_EXACT_TAMPERED = b"tampered"


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


class _ForeignExactRoot(type(Path())):
    """An overridden filesystem path cannot establish tree authority."""

    @override
    def __str__(self) -> str:
        message = "foreign exact root path conversion was evaluated"
        raise AssertionError(message)


@pytest.mark.parametrize("role", ["snapshot", "source", "oracle", "output"])
def test_exact_roots_reject_foreign_path_subclasses_before_methods(
    tmp_path: Path, role: str
) -> None:
    """Authoring and materialization reject root hooks before filesystem I/O."""
    source, oracle = _synthetic_pair(tmp_path)
    foreign = _ForeignExactRoot(tmp_path / "redirect")
    actions = {
        "snapshot": lambda: snapshot_tree(foreign),
        "source": lambda: build_exact_plan(foreign, oracle),
        "oracle": lambda: build_exact_plan(source, foreign),
        "output": lambda: materialize_exact_plan(
            source, build_exact_plan(source, oracle), foreign
        ),
    }
    with pytest.raises(ExactTreeError, match="must use an exact pathlib Path"):
        _ = actions[role]()
    assert not (tmp_path / "redirect").exists()


@pytest.mark.parametrize(
    "invalid_path",
    [
        "../escape",
        "/absolute",
        "src//file",
        "src\\file",
        "C:/unsafe",
        "C:relative",
        "NUL",
        "CON",
        "src/COM1/child.bin",
        "src/trailing.",
        "src/stream:fork",
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
    "invalid_path", ["CON", "src/COM1/child.bin", "src/trailing."]
)
def test_exact_model_paths_resist_mutable_reserved_name_policy(
    monkeypatch: pytest.MonkeyPatch, invalid_path: str
) -> None:
    """Domain hooks cannot authorize nonportable snapshot or output names."""

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = FileRecord(invalid_path, "0" * 64, 0)
    with pytest.raises(TreeModelError, match="canonical relative"):
        _ = ExactInstruction(
            output_path=invalid_path,
            kind=ExactInstructionKind.LITERAL_ORACLE,
            expected_sha256="0" * 64,
            literal=b"",
        )


def _forge_model_path_method(
    patched: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    def forged_parts(_path: PurePosixPath) -> tuple[str, ...]:
        del _path
        return ()

    def forged_as_posix(_path: PurePosixPath) -> str:
        del _path
        return invalid

    def forged_absolute(_path: PurePosixPath) -> bool:
        del _path
        return False

    hooks = {
        "parts": property(forged_parts),
        "as_posix": forged_as_posix,
        "is_absolute": forged_absolute,
    }
    patched.setattr(PurePosixPath, method, hooks[method])


@pytest.mark.parametrize(
    ("method", "invalid"),
    [
        ("is_absolute", "/escape.bin"),
        ("parts", "nested/../escape.bin"),
        ("as_posix", "nested//escape.bin"),
    ],
)
def test_exact_model_path_admission_resists_late_pathlib_spoof(
    monkeypatch: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    """A mutable pathlib class must not authorize noncanonical exact labels."""
    with monkeypatch.context() as patched:
        _forge_model_path_method(patched, method, invalid)
        with pytest.raises(TreeModelError, match="canonical relative"):
            _ = FileRecord(invalid, "0" * 64, 0)
        with pytest.raises(TreeModelError, match="canonical relative"):
            _ = ExactInstruction(
                output_path=invalid,
                kind=ExactInstructionKind.LITERAL_ORACLE,
                expected_sha256="0" * 64,
                literal=b"",
            )
        with pytest.raises(TreeModelError, match="canonical relative"):
            _ = ExactAuthoringPlan(
                source=TreeSnapshot(files=()),
                target=TreeSnapshot(files=()),
                instructions=(),
                passthrough_roots=(invalid,),
            )


def test_exact_snapshot_topology_resists_late_parent_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late parent enumeration hook cannot admit nested file records."""
    ancestor = FileRecord("src/module", "0" * 64, 0)
    descendant = FileRecord("src/module/child", "0" * 64, 0)

    def forged_parents(_path: PurePosixPath) -> tuple[()]:
        del _path
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(PurePosixPath, "parents", property(forged_parents))
        with pytest.raises(TreeModelError, match="ancestor"):
            _ = TreeSnapshot(files=(ancestor, descendant))


@pytest.mark.parametrize(
    "invalid_root",
    [
        "dynamic\x00tail",
        "dynamic\ud800tail",
        "C:/escape",
        "CON",
        "src/COM1/child.c",
        "src/trailing.",
        "src/stream:fork",
    ],
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


@pytest.mark.parametrize(
    "reserved_root", ["CON", "src/COM1/child.c", "src/trailing."]
)
def test_exact_passthrough_roots_ignore_host_reserved_policy_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reserved_root: str,
) -> None:
    """Mutable host hooks cannot authorize a nonportable dynamic root."""
    source, oracle = _synthetic_pair(tmp_path)

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(TreeModelError, match="relative path"):
        _ = snapshot_tree_excluding(source, (reserved_root,))
    with pytest.raises(TreeModelError, match="relative path"):
        _ = build_exact_plan(source, oracle, passthrough_roots=(reserved_root,))


def _forge_exact_ntpath_any(patched: pytest.MonkeyPatch, root: str) -> None:
    del root
    native_any = builtins.any

    def forged_any(values: Iterable[object]) -> bool:
        frame = getattr(values, "gi_frame", None)
        if getattr(frame, "f_globals", None) is vars(ntpath):
            return False
        return native_any(values)

    patched.setattr(builtins, "any", forged_any)


def _forge_exact_ntpath_reversed(
    patched: pytest.MonkeyPatch, root: str
) -> None:
    native_reversed = builtins.reversed

    def forged_reversed(values: list[str]) -> object:
        if values == [root]:
            return ()
        return native_reversed(values)

    patched.setattr(builtins, "reversed", forged_reversed)


def _forge_exact_ntpath_splitroot(
    patched: pytest.MonkeyPatch, root: str
) -> None:
    native_splitroot = ntpath.splitroot

    def forged_splitroot(path: str) -> tuple[str, str, str]:
        if path == root:
            return "", "", "safe.c"
        return native_splitroot(path)

    patched.setattr(ntpath, "splitroot", forged_splitroot)


@pytest.mark.parametrize(
    "forge",
    [
        _forge_exact_ntpath_any,
        _forge_exact_ntpath_reversed,
        _forge_exact_ntpath_splitroot,
    ],
)
def test_exact_passthrough_rejects_late_ntpath_dependency_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forge: Callable[[pytest.MonkeyPatch, str], None],
) -> None:
    """No host hook may turn a DOS-device passthrough into a valid root."""
    source, _ = _synthetic_pair(tmp_path)
    reserved_root = "NUL"
    rejected = False
    with monkeypatch.context() as patched:
        forge(patched, reserved_root)
        try:
            _ = snapshot_tree_excluding(source, (reserved_root,))
        except TreeModelError:
            rejected = True
    assert rejected, "mutable ntpath dependency admitted DOS-device root"


@pytest.mark.parametrize(
    "attack",
    [
        "sha256", "path", "foreign-record", "ancestor-overlap",
        "patch-overrun", "passthrough-overlap", "static-target",
    ],
)
def test_exact_model_rejects_late_any_metadata_bypass(
    monkeypatch: pytest.MonkeyPatch, attack: str
) -> None:
    """Late any overrides must not forge exact metadata trust boundaries."""
    record = FileRecord("src.bin", "a" * 64, 1)
    source = TreeSnapshot(files=(record,))
    target = TreeSnapshot(files=(FileRecord("out.bin", "b" * 64, 2),))
    unsafe_patch = ExactInstruction(
        output_path="out.bin",
        kind=ExactInstructionKind.PATCH_SOURCE,
        expected_sha256="b" * 64,
        source_path="src.bin",
        segments=(SourceSlice(offset=1, length=2),),
    )
    literal = b"target"
    literal_sha256 = hashlib.sha256(literal).hexdigest()
    literal_target = TreeSnapshot(
        files=(FileRecord("assets/output.bin", literal_sha256, len(literal)),)
    )
    literal_instruction = ExactInstruction(
        output_path="assets/output.bin",
        kind=ExactInstructionKind.LITERAL_ORACLE,
        expected_sha256=literal_sha256,
        literal=literal,
    )
    empty = TreeSnapshot(files=())
    actions: dict[str, Callable[[], object]] = {
        "sha256": lambda: FileRecord("file.bin", "g" * 64, 0),
        "path": lambda: FileRecord("src/../escape", "a" * 64, 0),
        "foreign-record": lambda: TreeSnapshot(
            files=(
                cast(
                    "FileRecord",
                    cast("object", SimpleNamespace(path="foreign.bin")),
                ),
            )
        ),
        "ancestor-overlap": lambda: TreeSnapshot(
            files=(
                FileRecord("parent", "a" * 64, 0),
                FileRecord("parent/child", "b" * 64, 0),
            )
        ),
        "patch-overrun": lambda: ExactAuthoringPlan(
            source=source, target=target, instructions=(unsafe_patch,)
        ),
        "passthrough-overlap": lambda: ExactAuthoringPlan(
            source=empty,
            target=empty,
            instructions=(),
            passthrough_roots=("assets", "assets/sub"),
        ),
        "static-target": lambda: ExactAuthoringPlan(
            source=empty,
            target=literal_target,
            instructions=(literal_instruction,),
            passthrough_roots=("assets",),
        ),
    }
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = actions[attack]()
        except TreeModelError:
            rejected = True
    assert rejected, f"late any hook admitted model {attack}"


def test_exact_model_rejects_late_set_duplicate_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced set cannot certify duplicate file identities."""
    record = FileRecord("file.bin", "a" * 64, 0)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "set", lambda values: list(values))
        try:
            _ = TreeSnapshot(files=(record, record))
        except TreeModelError:
            rejected = True
    assert rejected, "late set hook admitted duplicate snapshot file paths"



def test_exact_model_rejects_late_bool_drive_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late bool hook cannot authorize a Windows drive-relative label."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", lambda value: False)
        try:
            _ = FileRecord("C:escape", "a" * 64, 1)
        except TreeModelError:
            rejected = True
    assert rejected, "late bool hook admitted a Windows drive-relative path"


def test_exact_model_rejects_late_sum_patch_size_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged aggregator cannot certify false patch output lengths."""
    source = TreeSnapshot(files=(FileRecord("src.bin", "a" * 64, 3),))
    target = TreeSnapshot(files=(FileRecord("out.bin", "b" * 64, 10),))
    instruction = ExactInstruction(
        output_path="out.bin",
        kind=ExactInstructionKind.PATCH_SOURCE,
        expected_sha256="b" * 64,
        source_path="src.bin",
        segments=(SourceSlice(0, 2),),
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "sum", lambda values: 10)
        try:
            _ = ExactAuthoringPlan(
                source=source,
                target=target,
                instructions=(instruction,),
            )
        except TreeModelError:
            rejected = True
    assert rejected, "late sum hook certified false patch output length"


def test_exact_relative_path_rejects_late_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late builtins changes cannot authorize traversal-containing paths."""
    validate = cast(
        "Callable[[str], str]", vars(exact_module)["_validate_relative_path"]
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda items: False)
        try:
            _ = validate("src/../escape")
        except TreeModelError:
            rejected = True
    assert rejected, "late any hook admitted a parent traversal"


@pytest.mark.parametrize("path", ["C:escape", "C:/escape"])
def test_exact_relative_path_rejects_late_bool_drive_override(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """A late bool hook cannot suppress Windows drive-relative rejection."""
    validate = cast(
        "Callable[[str], str]", vars(exact_module)["_validate_relative_path"]
    )

    def always_false(_: object) -> bool:
        return False

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", always_false)
        try:
            _ = validate(path)
        except TreeModelError:
            rejected = True
    assert rejected, "late bool hook admitted a Windows drive path"


def test_exact_relative_path_accepts_native_label_after_late_bool_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid label must not consult a hostile late bool hook."""
    validate = cast(
        "Callable[[str], str]", vars(exact_module)["_validate_relative_path"]
    )

    def always_true(_: object) -> bool:
        return True

    admitted = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", always_true)
        try:
            admitted = validate("src/file.txt") == "src/file.txt"
        except TreeModelError:
            pass
    assert admitted, "late bool hook rejected a native valid path"


def test_exact_passthrough_roots_reject_late_builtin_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root uniqueness, order, and nonoverlap survive hostile builtins."""
    normalized_roots = cast(
        "Callable[[tuple[str, ...]], tuple[str, ...]]",
        vars(exact_module)["_normalized_roots"],
    )
    cases = (
        ("any", lambda values: False, ("root", "root/sub")),
        ("set", lambda values: list(values), ("root", "root")),
        ("sorted", lambda values: ("z", "a"), ("z", "a")),
    )
    rejected: list[bool] = []
    for name, forged, roots in cases:
        with monkeypatch.context() as patched:
            patched.setattr(builtins, name, forged)
            try:
                _ = normalized_roots(roots)
            except ExactTreeError:
                rejected.append(True)
            else:
                rejected.append(False)
    assert rejected == [True, True, True], "late hook admitted unsafe roots"


def test_exact_passthrough_snapshot_resists_late_any_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late any hook cannot smuggle dynamic files into static identity."""
    source, _ = _synthetic_pair(tmp_path)
    baseline = snapshot_tree_excluding(source, ("assets",))
    assert "assets/blob.bin" not in {file.path for file in baseline.files}
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda items: False)
        observed = snapshot_tree_excluding(source, ("assets",))
    assert observed == baseline, "late any hook changed static source identity"


def test_exact_file_reader_resists_late_bytearray_collector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged collector must not replace source bytes with equal-size data."""
    leaf = tmp_path / "source.bin"
    content = b"read-only-authentic-source-bytes"
    _ = leaf.write_bytes(content)
    native_bytearray = builtins.bytearray
    native_bytes = builtins.bytes

    class _SubstitutingCollector:
        def __init__(self) -> None:
            self.data = native_bytearray()

        def __len__(self) -> int:
            return len(self.data)

        def extend(self, chunk: bytes) -> None:
            self.data.extend(b"x" * len(chunk))

        def __bytes__(self) -> bytes:
            return native_bytes(self.data)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytearray", _SubstitutingCollector)
        observed = exact_module.read_exact_regular_file(leaf, "tree entry")
    assert observed == content, "late bytearray collector changed source bytes"


def test_exact_file_reader_resists_late_min_chunk_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced min must not increase the bounded per-read file quota."""
    leaf = tmp_path / "large.bin"
    _ = leaf.write_bytes(b"a" * 70_000)
    native_read = cast(
        "Callable[[int, int, str], bytes]",
        vars(exact_module)["_read_native_chunk"],
    )
    chunks: list[int] = []

    def measured_read(descriptor: int, count: int, context: str) -> bytes:
        chunks.append(count)
        return native_read(descriptor, count, context)

    with monkeypatch.context() as patched:
        patched.setattr(exact_module, "_read_native_chunk", measured_read)
        patched.setattr(builtins, "min", lambda left, right: right)
        observed = exact_module.read_exact_regular_file(leaf, "tree entry")
    assert len(observed) == 70_000
    assert max(chunks) <= 65_536, "late min hook increased native read quota"


def test_tree_snapshot_order_resists_late_sorted_hook_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable global sorter cannot certify out-of-order source records."""
    reversed_records = (
        FileRecord("z.bin", "0" * 64, 1),
        FileRecord("a.bin", "1" * 64, 1),
    )
    calls = 0

    def forged_sorted(values: object) -> list[str]:
        """Return the attacker-chosen reversed record order.

        Returns:
            An unsorted forged record list.

        """
        nonlocal calls
        del values
        calls += 1
        return ["z.bin", "a.bin"]

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", forged_sorted)
        try:
            _ = TreeSnapshot(files=reversed_records)
        except TreeModelError:
            rejected = True

    _expect(rejected, "forged sorted hook admitted an unsorted snapshot")
    _expect(calls == 0, "hostile sorting hook was consulted")


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
        instruction.output_path: instruction for instruction in plan.instructions
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

    monkeypatch.setattr(exact_module, "read_exact_regular_file", read_then_mutate)
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
    ("variant", "expected"),
    [
        ("missing-source", "source path is absent"),
        ("copy-digest", "copy-source digest"),
        ("copy-size", "copy-source size"),
        ("patch-range", "source slice exceeds"),
    ],
)
def test_direct_exact_plan_rejects_impossible_static_source_references(
    variant: str,
    expected: str,
) -> None:
    """Static snapshot evidence must bound all referenced source bytes."""
    source = TreeSnapshot(
        files=(
            FileRecord("src/a.bin", "a" * 64, 4),
            FileRecord("src/b.bin", "b" * 64, 2),
        )
    )
    target_size = {
        _COPY_SIZE_CASE: 5,
        _PATCH_RANGE_CASE: 2,
    }.get(variant, 4)
    target = TreeSnapshot(files=(FileRecord("out.bin", "a" * 64, target_size),))
    source_path = {
        "missing-source": "src/missing.bin",
        "copy-digest": "src/b.bin",
    }.get(variant, "src/a.bin")
    if variant == _PATCH_RANGE_CASE:
        instruction = ExactInstruction(
            output_path="out.bin",
            kind=ExactInstructionKind.PATCH_SOURCE,
            expected_sha256="a" * 64,
            source_path=source_path,
            segments=(SourceSlice(offset=3, length=2),),
        )
    else:
        instruction = ExactInstruction(
            output_path="out.bin",
            kind=ExactInstructionKind.COPY_SOURCE,
            expected_sha256="a" * 64,
            source_path=source_path,
        )
    with pytest.raises(TreeModelError, match=expected):
        _ = ExactAuthoringPlan(
            source=source,
            target=target,
            instructions=(instruction,),
        )


@pytest.mark.parametrize(
    ("invalid_case", "error_fragment"),
    [
        ("literal-size", "literal-oracle size"),
        ("literal-digest", "literal-oracle digest"),
        ("patch-size", "patch-source size"),
    ],
)
def test_direct_exact_plan_rejects_impossible_output_lengths_and_digest(
    invalid_case: str,
    error_fragment: str,
) -> None:
    """Fully known output bytes must agree with the static target snapshot."""
    raw_literal = b"literal"
    literal_sha256 = hashlib.sha256(raw_literal).hexdigest()
    source = TreeSnapshot(files=(FileRecord("src.bin", "a" * 64, 4),))
    if invalid_case in {_LITERAL_SIZE_CASE, _LITERAL_DIGEST_CASE}:
        target_size = len(raw_literal) + int(invalid_case == _LITERAL_SIZE_CASE)
        target_digest = (
            "b" * 64 if invalid_case == _LITERAL_DIGEST_CASE else literal_sha256
        )
        instruction = ExactInstruction(
            output_path="out.bin",
            kind=ExactInstructionKind.LITERAL_ORACLE,
            expected_sha256=target_digest,
            literal=raw_literal,
        )
    else:
        target_size = 8
        target_digest = "b" * 64
        instruction = ExactInstruction(
            output_path="out.bin",
            kind=ExactInstructionKind.PATCH_SOURCE,
            expected_sha256=target_digest,
            source_path="src.bin",
            segments=(SourceSlice(offset=0, length=4), OracleLiteral(b"more!")),
        )
    target = TreeSnapshot(files=(FileRecord("out.bin", target_digest, target_size),))
    with pytest.raises(TreeModelError, match=error_fragment):
        _ = ExactAuthoringPlan(
            source=source,
            target=target,
            instructions=(instruction,),
        )


def test_snapshot_digests_ignore_replaced_global_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced global hash cannot give different exact trees equal receipts."""
    original = tmp_path / "original"
    changed = tmp_path / "changed"
    _write(original, "src/file.bin", b"trusted")
    _write(changed, "src/file.bin", b"altered")
    calls = 0

    class _CollidingHash:
        def hexdigest(self) -> str:
            return "0" * 64

    def fake_sha256(_data: bytes) -> _CollidingHash:
        nonlocal calls
        calls += 1
        return _CollidingHash()

    monkeypatch.setattr(hashlib, "sha256", fake_sha256)
    first = snapshot_tree(original)
    second = snapshot_tree(changed)
    assert first.files[0].sha256 != second.files[0].sha256
    assert calls == 0


def test_exact_plan_literal_digest_ignores_replaced_global_sha256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An injected hash constructor must not admit a forged oracle literal."""
    expected = b"authentic"
    forged = b"forgeries"
    target_hash = hashlib.sha256(expected).hexdigest()
    target = TreeSnapshot(files=(FileRecord("out.bin", target_hash, len(expected)),))
    instruction = ExactInstruction(
        output_path="out.bin",
        kind=ExactInstructionKind.LITERAL_ORACLE,
        expected_sha256=target_hash,
        literal=forged,
    )
    calls = 0

    class _ForgedHash:
        def hexdigest(self) -> str:
            return target_hash

    def forged_sha256(_data: bytes) -> _ForgedHash:
        nonlocal calls
        calls += 1
        return _ForgedHash()

    monkeypatch.setattr(hashlib, "sha256", forged_sha256)
    with pytest.raises(TreeModelError, match="literal-oracle digest"):
        _ = ExactAuthoringPlan(
            source=TreeSnapshot(files=()),
            target=target,
            instructions=(instruction,),
        )
    assert calls == 0


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

    monkeypatch.setattr(exact_module, "snapshot_tree", snapshot_then_change_source)
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

    monkeypatch.setattr(exact_module, "snapshot_tree", snapshot_then_change_runtime)
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


def test_exact_snapshot_ignores_post_import_root_resolution_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host resolver swap cannot replace the admitted source byte identity."""
    source = tmp_path / "source"
    redirected = tmp_path / "redirected"
    _write(source, "payload", b"source")
    _write(redirected, "payload", b"foreign")
    baseline = snapshot_tree(source)
    native_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == source and strict:
            calls += 1
            return native_resolve(redirected, strict=True)
        return native_resolve(path, strict=strict)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "resolve", forged_resolve)
        observed = snapshot_tree(source)
    assert calls == 0
    assert observed == baseline


def test_exact_materialization_ignores_post_import_output_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host resolver swap cannot publish verified bytes to another root."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "intended-output"
    redirected = tmp_path / "redirected-output"
    native_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == output:
            calls += 1
            return native_resolve(redirected, strict=strict)
        return native_resolve(path, strict=strict)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "resolve", forged_resolve)
        materialize_exact_plan(source, plan, output)
    assert calls == 0
    assert not redirected.exists()
    assert snapshot_tree(output) == plan.target


def test_exact_output_containment_ignores_mutated_path_is_relative_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-load pathlib hooks cannot allow output staging inside source."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = source / "nested-output"
    native_check = Path.is_relative_to

    def forged_check(path: Path, other: Path) -> bool:
        if path == output and other == source:
            return False
        return native_check(path, other)

    def reject_verification(*_args: object) -> None:
        message = "unsafe output reached source verification"
        raise AssertionError(message)

    monkeypatch.setattr(Path, "is_relative_to", forged_check)
    monkeypatch.setattr(exact_module, "_verify_source", reject_verification)
    with pytest.raises(ExactTreeError, match="inside the source tree"):
        materialize_exact_plan(source, plan, output)
    assert not output.exists()


def test_exact_tree_containment_ignores_mutated_path_relative_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged relative_to verdict cannot make a symlinked path contained."""
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    _ = (outside / "secret.txt").write_bytes(b"external bytes")
    try:
        (root / "alias").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    native_relative = Path.relative_to

    def forged_relative(
        path: Path, other: Path, *, walk_up: bool = False
    ) -> Path:
        if path == outside / "secret.txt":
            return Path(".")
        return native_relative(path, other, walk_up=walk_up)

    monkeypatch.setattr(Path, "relative_to", forged_relative)
    safe_path = cast(
        "Callable[[Path, str], Path]",
        vars(exact_module)["_safe_tree_path"],
    )
    with pytest.raises(ExactTreeError, match="path escapes tree root"):
        _ = safe_path(root, "alias/secret.txt")


@pytest.mark.parametrize("operation", ["author-read", "materialize-path"])
def test_exact_accepted_paths_ignore_late_joinpath_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A valid label cannot be redirected by a consumer Path join hook."""
    nested = tmp_path / "nested"
    nested.mkdir()
    _ = (nested / "source.bin").write_bytes(b"admitted")
    decoy = tmp_path / "decoy.bin"
    _ = decoy.write_bytes(b"substituted")
    original_joinpath = Path.joinpath

    def forged_joinpath(path: Path, *other: str) -> Path:
        if path == tmp_path and other == ("nested", "source.bin"):
            return decoy
        return original_joinpath(path, *other)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "joinpath", forged_joinpath)
        if operation == "author-read":
            reader = cast(
                "Callable[[Path, str], bytes]",
                vars(exact_module)["_tree_bytes"],
            )
            assert reader(tmp_path, "nested/source.bin") == b"admitted"
        else:
            safe = cast(
                "Callable[[Path, str], Path]",
                vars(exact_module)["_safe_tree_path"],
            )
            assert safe(tmp_path, "nested/source.bin") == nested / "source.bin"


@pytest.mark.parametrize("operation", ["author-read", "materialize-path"])
def test_exact_accepted_paths_ignore_late_posix_parts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A valid source label must not resolve to a consumer-selected file."""
    nested = tmp_path / "nested"
    nested.mkdir()
    _ = (nested / "source.bin").write_bytes(b"admitted")
    _ = (tmp_path / "decoy.bin").write_bytes(b"substituted")
    native_parts = PurePosixPath.parts

    def forged_parts(value: PurePosixPath) -> tuple[str, ...]:
        if type(value) is PurePosixPath:
            return ("decoy.bin",)
        return cast("tuple[str, ...]", native_parts.__get__(value))

    with monkeypatch.context() as patch:
        patch.setattr(PurePosixPath, "parts", property(forged_parts))
        if operation == "author-read":
            read = cast(
                "Callable[[Path, str], bytes]",
                vars(exact_module)["_tree_bytes"],
            )
            assert read(tmp_path, "nested/source.bin") == b"admitted"
        else:
            safe = cast(
                "Callable[[Path, str], Path]",
                vars(exact_module)["_safe_tree_path"],
            )
            actual = safe(tmp_path, "nested/source.bin")
            assert actual == nested / "source.bin"


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


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(ExactTreeError, match="output root resolution failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "output resolution failure published output")


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
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


def test_exact_output_writer_ignores_late_path_write_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staging writes must not touch a foreign file through a class hook."""
    target = tmp_path / "stage" / "payload.bin"
    target.parent.mkdir()
    victim = tmp_path / "victim.bin"
    _ = victim.write_bytes(b"untouched")
    original_write = Path.write_bytes
    calls = 0

    def forged_write(path: Path, data: bytes) -> int:
        nonlocal calls
        if path == target:
            calls += 1
            return original_write(victim, data)
        return original_write(path, data)

    writer = cast(
        "Callable[[Path, bytes, str], None]", vars(exact_module)["_write_output_file"]
    )
    with monkeypatch.context() as patched:
        patched.setattr(Path, "write_bytes", forged_write)
        writer(target, b"trusted", "staging output")
    assert calls == 0, "late Path.write_bytes redirected a staged write"
    assert target.read_bytes() == b"trusted"
    assert victim.read_bytes() == b"untouched"


def test_exact_output_writer_ignores_late_parent_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staged parent creation must use the original path parent."""
    target = tmp_path / "stage" / "nested" / "payload.bin"
    victim = tmp_path / "foreign"
    original_parent = Path.parent
    calls = 0

    def forged_parent(path: Path) -> Path:
        nonlocal calls
        if path == target:
            calls += 1
            return victim
        return original_parent.__get__(path, type(path))

    writer = cast(
        "Callable[[Path, bytes, str], None]", vars(exact_module)["_write_output_file"]
    )
    with monkeypatch.context() as patched:
        patched.setattr(Path, "parent", property(forged_parent))
        writer(target, b"trusted", "staging output")
    assert calls == 0, "late parent hook redirected staging directory"
    assert target.read_bytes() == b"trusted"
    assert not victim.exists()


def test_exact_staging_ignores_late_path_with_name_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer must not redirect the temporary directory before checks."""
    output = tmp_path / "target"
    victim = tmp_path / "outside"
    original_with_name = Path.with_name
    calls = 0

    def forged_with_name(path: Path, name: str) -> Path:
        nonlocal calls
        if path == output:
            calls += 1
            return victim
        return original_with_name(path, name)

    prepare = cast("Callable[[Path], Path]", vars(exact_module)["_prepare_staging"])
    with monkeypatch.context() as patched:
        patched.setattr(Path, "with_name", forged_with_name)
        staging = prepare(output)
    assert calls == 0, "late with_name hook redirected staging root"
    assert staging == tmp_path / ".target.staging"
    assert staging.is_dir()
    assert not victim.exists()


@pytest.mark.parametrize("hook", ["path-mkdir", "os-mkdir"])
def test_exact_staging_ignores_late_directory_creation_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Hostile directory builders cannot redirect an owned staging root."""
    output = tmp_path / "nested" / "target"
    calls = 0

    def forged_path_mkdir(_path: Path, *_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late pathlib mkdir reached")

    def forged_os_mkdir(
        _path: str | bytes | os.PathLike[str], _mode: int = 0o777
    ) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late os.mkdir reached")

    prepare = cast("Callable[[Path], Path]", vars(exact_module)["_prepare_staging"])
    with monkeypatch.context() as patched:
        if hook == "path-mkdir":
            patched.setattr(Path, "mkdir", forged_path_mkdir)
        else:
            patched.setattr(os, "mkdir", forged_os_mkdir)
        staging = prepare(output)
    assert calls == 0, "late directory hook executed"
    assert staging == tmp_path / "nested" / ".target.staging"
    assert staging.is_dir()
    assert not output.exists()


def test_exact_writer_ignores_late_io_open_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staging bytes must not be routed through a replaced io.open alias."""
    import io

    stage = tmp_path / "stage"
    stage.mkdir()
    output = stage / "result"
    victim = tmp_path / "victim"
    _ = victim.write_bytes(b"untouched")
    calls = 0

    def forged_open(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late io.open reached")

    writer = cast(
        "Callable[[Path, bytes, str], None]", vars(exact_module)["_write_output_file"]
    )
    with monkeypatch.context() as patched:
        patched.setattr(io, "open", forged_open)
        writer(output, b"trusted", "staging output")
    assert calls == 0, "late io.open hook executed"
    assert output.read_bytes() == b"trusted"
    assert victim.read_bytes() == b"untouched"


def test_exact_staging_ignores_late_path_name_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staging uses the original basename, even after a class name hook."""
    output = tmp_path / "target"
    calls = 0
    original_name = Path.name

    def forged_name(path: Path) -> str:
        nonlocal calls
        if path == output:
            calls += 1
            return "foreign"
        return original_name.__get__(path, type(path))

    prepare = cast("Callable[[Path], Path]", vars(exact_module)["_prepare_staging"])
    with monkeypatch.context() as patched:
        patched.setattr(Path, "name", property(forged_name))
        staging = prepare(output)
    assert calls == 0, "late name hook chose staging root"
    assert staging == tmp_path / ".target.staging"
    assert staging.is_dir()
    assert not (tmp_path / ".foreign.staging").exists()


def test_exact_writer_never_replaces_existing_staged_file(tmp_path: Path) -> None:
    """One staged file should only be created once, without truncation."""
    target = tmp_path / "staging" / "existing"
    target.parent.mkdir()
    _ = target.write_bytes(b"existing")
    writer = cast(
        "Callable[[Path, bytes, str], None]", vars(exact_module)["_write_output_file"]
    )
    with pytest.raises(ExactTreeError, match="write failed"):
        writer(target, b"replacement", "staging output")
    assert target.read_bytes() == b"existing"


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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
    original_write = cast(
        "Callable[[Path, bytes], int]", vars(exact_module)["_NATIVE_WRITE_OUTPUT_BYTES"]
    )

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked staging write"
            raise failure_type(message)
        return original_write(path, data)

    monkeypatch.setattr(exact_module, "_NATIVE_WRITE_OUTPUT_BYTES", fail_write)
    with pytest.raises(ExactTreeError, match="instruction output write failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "write failure published output")
    _expect(not (tmp_path / ".result.staging").exists(), "staging survived")


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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
    original_mkdir = cast(
        "Callable[[str], None]", vars(exact_module)["_NATIVE_OS_MKDIR"]
    )

    def fail_mkdir(path: str) -> None:
        if Path(path) == staging:
            message = "blocked staging directory"
            raise failure_type(message)
        original_mkdir(path)

    monkeypatch.setattr(exact_module, "_NATIVE_OS_MKDIR", fail_mkdir)
    with pytest.raises(ExactTreeError, match="staging root creation failed"):
        materialize_exact_plan(source, plan, output)
    _expect(not output.exists(), "staging mkdir failure published output")
    _expect(not staging.exists(), "staging mkdir failure left staging")


def test_exact_cleanup_ignores_post_import_rmtree_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late shutil hook cannot suppress deletion of owned staging."""
    staging = tmp_path / "owned-staging"
    staging.mkdir()
    _ = (staging / "payload.bin").write_bytes(b"temporary")
    calls = 0

    def forged_rmtree(path: Path) -> None:
        nonlocal calls
        _ = path
        calls += 1

    cleanup = cast(
        "Callable[[Path], str | None]",
        vars(exact_module)["_cleanup_exact_staging"],
    )
    with monkeypatch.context() as patched:
        patched.setattr(shutil, "rmtree", forged_rmtree)
        detail = cleanup(staging)
    assert detail is None
    assert calls == 0, "late cleanup hook executed"
    assert not staging.exists(), "owned staging remained after cleanup"


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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
    original_write = cast(
        "Callable[[Path, bytes], int]", vars(exact_module)["_NATIVE_WRITE_OUTPUT_BYTES"]
    )

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked staging write"
            raise PermissionError(message)
        return original_write(path, data)

    def fail_cleanup(path: Path) -> None:
        _ = path
        message = "blocked staging cleanup"
        raise failure_type(message)

    monkeypatch.setattr(exact_module, "_NATIVE_WRITE_OUTPUT_BYTES", fail_write)
    monkeypatch.setattr(exact_module, "_NATIVE_RMTREE", fail_cleanup)
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", fail_lstat)
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


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", fail_status)
    with pytest.raises(ExactTreeError, match="tree root status failed"):
        _ = snapshot_tree(root)


@pytest.mark.parametrize("target_kind", ["root", "entry"])
def test_exact_snapshot_rejects_non_native_path_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """Foreign stat records must not certify root or discovered entry modes."""
    root = tmp_path / "tree"
    root.mkdir()
    leaf = root / "leaf"
    _ = leaf.write_bytes(b"trusted")
    target = {"root": root, "entry": leaf}[target_kind]
    original_lstat = Path.lstat
    forged = False

    def forge_status(path: Path) -> object:
        nonlocal forged
        if path == target:
            forged = True
            return SimpleNamespace(st_mode=original_lstat(path).st_mode)
        return original_lstat(path)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", forge_status)
    with pytest.raises(ExactTreeError, match="native filesystem status"):
        _ = snapshot_tree(root)
    _expect(forged, "the forged stat receipt was not consumed")


@pytest.mark.parametrize("target_kind", ["root", "entry"])
def test_exact_snapshot_rejects_foreign_junction_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """A false-like non-bool cannot certify that a path is not a junction."""
    root = tmp_path / "tree"
    root.mkdir()
    leaf = root / "leaf"
    _ = leaf.write_bytes(b"trusted")
    target = {"root": root, "entry": leaf}[target_kind]
    native_junction = Path.is_junction
    checked = False

    def forged_verdict(path: Path) -> object:
        nonlocal checked
        if path == target:
            checked = True
            return 0
        return native_junction(path)

    monkeypatch.setattr(
        exact_module, "_NATIVE_PATH_IS_JUNCTION", forged_verdict
    )
    with pytest.raises(ExactTreeError, match="native boolean"):
        _ = snapshot_tree(root)
    _expect(checked, "foreign junction verdict was not reached")


def test_exact_junction_rejects_foreign_verdict_under_late_bool_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late bool type alias cannot admit a foreign false-like verdict."""
    is_redirect = cast(
        "Callable[[Path, int], bool]", vars(exact_module)["_is_redirect"]
    )

    def foreign_junction(_: Path) -> int:
        return 0

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", int)
        patched.setattr(
            exact_module, "_NATIVE_PATH_IS_JUNCTION", foreign_junction
        )
        try:
            _ = is_redirect(tmp_path, tmp_path.stat().st_mode)
        except ExactTreeError:
            rejected = True
    assert rejected, "late bool alias admitted a nonnative junction verdict"


def test_exact_junction_accepts_native_verdict_under_late_bool_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native false junction verdict must survive a late bool alias."""
    is_redirect = cast(
        "Callable[[Path, int], bool]", vars(exact_module)["_is_redirect"]
    )
    observed: bool | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", int)
        try:
            observed = is_redirect(tmp_path, tmp_path.stat().st_mode)
        except ExactTreeError:
            pass
    assert observed is False, "late bool alias rejected a native junction"


@pytest.mark.parametrize("role", ["root", "output", "source-path"])
def test_exact_rejects_foreign_resolved_path_before_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    """Resolution must not inject a Path subclass into filesystem authority."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    selected = {
        "root": source,
        "output": output,
        "source-path": source / _MOVED_SOURCE,
    }[role]
    foreign = _ForeignExactRoot(selected)
    native_resolve = Path.resolve
    observed = False

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal observed
        if path == selected:
            observed = True
            return foreign
        return native_resolve(path, strict=strict)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_RESOLVE", forged_resolve)
    action = {
        "root": lambda: snapshot_tree(source),
        "output": lambda: materialize_exact_plan(source, plan, output),
        "source-path": lambda: materialize_exact_plan(source, plan, output),
    }[role]
    with pytest.raises(ExactTreeError, match="native Path"):
        _ = action()
    _expect(observed, "foreign resolved path was not consumed")
    _expect(not output.exists(), "foreign resolution published output")


class _HostileExactHostError(OSError):
    """External host callbacks must not control diagnostic formatting."""

    @override
    def __str__(self) -> str:
        message = "foreign exact-tree formatter executed"
        raise AssertionError(message)


@pytest.mark.parametrize("operation", ["status", "junction", "walk", "resolve"])
def test_exact_snapshot_rejects_hostile_host_errors_without_formatting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Keep failing filesystem callbacks inside the typed tree boundary."""
    root = tmp_path / "tree"
    root.mkdir()
    _ = (root / "leaf").write_bytes(b"trusted")
    fault = _HostileExactHostError("host refused")
    methods = {
        "status": (
            exact_module, "_NATIVE_PATH_LSTAT", "tree root status failed"
        ),
        "junction": (
            exact_module,
            "_NATIVE_PATH_IS_JUNCTION",
            "tree redirect status failed",
        ),
        "walk": (exact_module, "_NATIVE_PATH_WALK", "tree traversal failed"),
        "resolve": (
            exact_module, "_NATIVE_PATH_RESOLVE", "tree root resolution failed"
        ),
    }
    owner, method, expected = methods[operation]

    def fail_host(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(owner, method, fail_host)
    with pytest.raises(ExactTreeError, match=expected) as caught:
        _ = snapshot_tree(root)
    _expect(caught.value.__cause__ is fault, "foreign host cause was lost")


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


def test_exact_snapshot_rejects_linked_root_under_post_import_status_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged directory status cannot hide a linked source tree root."""
    real = tmp_path / "real"
    _write(real, "payload", b"oracle")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    native_lstat = Path.lstat
    real_status = real.stat()
    calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal calls
        if path == linked:
            calls += 1
            return real_status
        return native_lstat(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(
            ExactTreeError, match="tree root must not be linked"
        ):
            _ = snapshot_tree(linked)
    assert calls == 0


def test_exact_snapshot_rejects_linked_root_under_post_import_os_lstat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OS lstat replacement cannot turn a source-tree link into a directory."""
    real = tmp_path / "real"
    _write(real, "payload", b"oracle")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    native_lstat = os.lstat
    native_status = real.stat()
    calls = 0

    def forged_lstat(
        path: Path | str | bytes, *args: object, **kwargs: object
    ) -> os.stat_result:
        nonlocal calls
        if path == linked:
            calls += 1
            return native_status
        return native_lstat(path, *args, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", forged_lstat)
        with pytest.raises(
            ExactTreeError, match="tree root must not be linked"
        ):
            _ = snapshot_tree(linked)
    assert calls == 0


def test_exact_snapshot_ignores_post_import_tree_walk_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced walker cannot erase source files from the digest tree."""
    root = tmp_path / "source"
    _write(root, "source.txt", b"identity")
    baseline = snapshot_tree(root)
    calls = 0

    def forged_walk(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        del _args, _kwargs
        calls += 1
        return iter(())

    with monkeypatch.context() as patched:
        patched.setattr(Path, "walk", forged_walk)
        observed = snapshot_tree(root)
    assert calls == 0
    assert observed == baseline


def test_exact_snapshot_ignores_post_import_junction_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An injected junction verdict cannot reject an ordinary source tree."""
    root = tmp_path / "source"
    _write(root, "source.txt", b"identity")
    baseline = snapshot_tree(root)
    calls = 0

    def forged_junction(_path: Path) -> bool:
        nonlocal calls
        del _path
        calls += 1
        return True

    with monkeypatch.context() as patched:
        patched.setattr(Path, "is_junction", forged_junction)
        observed = snapshot_tree(root)
    assert calls == 0
    assert observed == baseline


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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_WALK", fail_walk)
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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", fail_status)
    with pytest.raises(ExactTreeError, match="tree entry status failed"):
        _ = snapshot_tree(root)


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
@pytest.mark.parametrize("is_root", [True, False])
def test_snapshot_host_status_exceptions_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
    *,
    is_root: bool,
) -> None:
    """Host status exceptions cannot bypass exact-tree admission errors."""
    root = tmp_path / "tree"
    root.mkdir()
    blocked = root if is_root else root / "payload.bin"
    if not is_root:
        _ = blocked.write_bytes(b"payload")
    original_lstat = Path.lstat

    def fail_status(path: Path) -> os.stat_result:
        if path == blocked:
            message = "host metadata status broke"
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", fail_status)
    context = "tree root" if is_root else "tree entry"
    with pytest.raises(ExactTreeError, match=f"{context} status failed"):
        _ = snapshot_tree(root)


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
@pytest.mark.parametrize("excluded", [False, True])
def test_snapshot_host_walk_exceptions_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
    *,
    excluded: bool,
) -> None:
    """A failed full or excluded recursive traversal rejects source identity."""
    root = tmp_path / "tree"
    root.mkdir()
    _ = (root / "payload.bin").write_bytes(b"payload")

    def fail_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = path, top_down, on_error, follow_symlinks
        message = "host tree walker broke"
        raise failure_type(message)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_WALK", fail_walk)

    def run_snapshot() -> TreeSnapshot:
        if excluded:
            return snapshot_tree_excluding(root, ("unused",))
        return snapshot_tree(root)

    with pytest.raises(ExactTreeError, match="tree traversal failed"):
        _ = run_snapshot()


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_snapshot_host_junction_exceptions_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Link-classification failures cannot authorize a supposed tree root."""
    root = tmp_path / "tree"
    root.mkdir()
    original_junction = Path.is_junction

    def fail_junction(path: Path) -> bool:
        if path == root:
            message = "host junction classification broke"
            raise failure_type(message)
        return original_junction(path)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_IS_JUNCTION", fail_junction)
    with pytest.raises(ExactTreeError, match="tree redirect status failed"):
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


class _ExactForeignPrimaryError(ExactTreeError):
    """A foreign primary exception must not control note propagation."""

    @override
    def add_note(self, note: str) -> None:
        del note
        message = "foreign primary note hook executed"
        raise AssertionError(message)


class _ExactHostileArgument:
    """No exception error-detail path may format arbitrary arguments."""

    @override
    def __str__(self) -> str:
        message = "foreign host argument formatter executed"
        raise AssertionError(message)


class _ExactHostileNoteError(OSError):
    """No exception error-detail path may dispatch foreign note accessors."""

    @override
    def __getattribute__(self, name: str) -> object:
        if name == _EXACT_NOTES_ATTRIBUTE:
            message = "foreign host note accessor executed"
            raise AssertionError(message)
        return cast("object", super().__getattribute__(name))


@pytest.mark.parametrize("secondary_kind", ["native", "foreign", "hostile-args"])
def test_exact_descriptor_close_cannot_override_original_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    secondary_kind: str,
) -> None:
    """Never format foreign cleanup faults or invoke primary note overrides."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"payload")

    primary = _ExactForeignPrimaryError("rejected original descriptor read")
    secondary = {
        "native": OSError(_EXACT_NATIVE_CLOSE_DETAIL),
        "foreign": _HostileExactHostError("foreign close failure"),
        "hostile-args": OSError(_ExactHostileArgument()),
    }[secondary_kind]
    original_close = os.close

    def fail_read(descriptor: int, count: int) -> bytes:
        del descriptor, count
        raise primary

    def fail_close(descriptor: int) -> None:
        original_close(descriptor)
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(os, "read", fail_read)
        patch.setattr(os, "close", fail_close)
        with pytest.raises(
            ExactTreeError, match="rejected original descriptor read"
        ) as caught:
            _ = exact_module.read_exact_regular_file(leaf, "tree entry")

    _expect(caught.value is primary, "cleanup replaced primary file error")
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    _expect(
        len(notes) == 1 and _CLOSE_FAILURE_NOTE in notes[0],
        "native cleanup note missing from original error",
    )
    if secondary_kind == _EXACT_NATIVE_CLOSE:
        _expect(
            _EXACT_NATIVE_CLOSE_DETAIL in notes[0],
            "trusted native close detail was lost",
        )


@pytest.mark.parametrize(
    "fault_kind", ["foreign-str", "native-hostile-arg", "foreign-notes"]
)
def test_exact_regular_reader_cannot_dispatch_foreign_host_error_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_kind: str,
) -> None:
    """Host read rejection stays typed without foreign text or notes access."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"payload")

    fault = {
        "foreign-str": _HostileExactHostError("host read failed"),
        "native-hostile-arg": OSError(_ExactHostileArgument()),
        "foreign-notes": _ExactHostileNoteError("host read failed"),
    }[fault_kind]

    def fail_read(descriptor: int, count: int) -> bytes:
        del descriptor, count
        raise fault

    with monkeypatch.context() as patch:
        patch.setattr(os, "read", fail_read)
        with pytest.raises(ExactTreeError, match="tree entry read failed") as caught:
            _ = exact_module.read_exact_regular_file(leaf, "tree entry")

    _expect(caught.value.__cause__ is fault, "foreign host read cause lost")
    _expect(
        type(caught.value) is ExactTreeError,
        "host read fault escaped exact tree admission boundary",
    )


def test_exact_regular_reader_preserves_native_host_error_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Safe native read diagnostics remain useful and causal."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"payload")
    primary = OSError("native read denied")

    def fail_read(descriptor: int, count: int) -> bytes:
        del descriptor, count
        raise primary

    monkeypatch.setattr(os, "read", fail_read)
    with pytest.raises(ExactTreeError, match="native read denied") as caught:
        _ = exact_module.read_exact_regular_file(leaf, "tree entry")
    _expect(caught.value.__cause__ is primary, "native read cause lost")


def test_exact_reader_rejects_foreign_junction_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fake false-like junction verdict cannot approve a direct file read."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"trusted")
    native_junction = Path.is_junction

    def foreign_verdict(path: Path) -> object:
        return 0 if path == leaf else native_junction(path)

    monkeypatch.setattr(
        exact_module, "_NATIVE_PATH_IS_JUNCTION", foreign_verdict
    )
    with pytest.raises(ExactTreeError, match="native boolean"):
        _ = exact_module.read_exact_regular_file(leaf, "tree entry")


@pytest.mark.parametrize("phase", ["body", "eof"])
def test_exact_reader_rejects_foreign_read_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Neither a foreign body nor EOF callback may authorize file evidence."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"trusted")
    native_read = os.read
    reads = 0

    def foreign_read(descriptor: int, count: int) -> bytes:
        nonlocal reads
        reads += 1
        observed = native_read(descriptor, count)
        if (phase, reads) in {("body", 1), ("eof", 2)}:
            return cast("bytes", cast("object", bytearray(observed)))
        return observed

    monkeypatch.setattr(os, "read", foreign_read)
    with pytest.raises(ExactTreeError, match="native read bytes"):
        _ = exact_module.read_exact_regular_file(leaf, "tree entry")


def test_exact_reader_rejects_forged_postclose_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A counterfeit final pathname receipt cannot release stale bytes."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"trusted")
    native_lstat = Path.lstat
    receipts: list[Path] = []

    def forged_final_status(path: Path) -> object:
        if path == leaf:
            receipts.append(path)
            if len(receipts) == _EXACT_POSTCLOSE_READS:
                return SimpleNamespace(st_mode=native_lstat(path).st_mode)
        return native_lstat(path)

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", forged_final_status)
    with pytest.raises(ExactTreeError, match="native filesystem status"):
        _ = exact_module.read_exact_regular_file(leaf, "tree entry")
    _expect(
        len(receipts) == _EXACT_POSTCLOSE_READS,
        "the final pathname receipt was not checked",
    )


def test_exact_reader_rejects_forged_descriptor_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fabricated fstat inode must not let redirected file bytes escape."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"trusted")
    foreign = tmp_path / "foreign"
    _ = foreign.write_bytes(b"hostile")
    trusted_status = leaf.lstat()
    original_open = os.open
    original_fstat = os.fstat
    redirected = False

    def redirect_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal redirected
        if os.fspath(path) == os.fspath(leaf):
            redirected = True
            return original_open(foreign, flags, mode, dir_fd=dir_fd)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def forge_fstat(descriptor: int) -> object:
        _ = original_fstat(descriptor)
        return SimpleNamespace(
            st_mode=trusted_status.st_mode,
            st_dev=trusted_status.st_dev,
            st_ino=trusted_status.st_ino,
            st_size=trusted_status.st_size,
            st_mtime_ns=trusted_status.st_mtime_ns,
            st_ctime_ns=trusted_status.st_ctime_ns,
        )

    monkeypatch.setattr(os, "open", redirect_open)
    monkeypatch.setattr(os, "fstat", forge_fstat)
    with pytest.raises(ExactTreeError, match="native filesystem status"):
        _ = exact_module.read_exact_regular_file(leaf, "tree entry")
    _expect(redirected, "redirected host descriptor was not opened")


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

    monkeypatch.setattr(exact_module, "_NATIVE_PATH_LSTAT", swap_after_status)
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
        from algorithms.diff import exact as exact_module
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

        exact_module._NATIVE_PATH_LSTAT = swap
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
    # jig-ignore-next-line: preserve the inline checked subprocess rule ID
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


@pytest.mark.parametrize("attack", ["inplace-rewrite", "inode-replacement"])
def test_exact_reader_rejects_postclose_source_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attack: str
) -> None:
    """Close callbacks cannot authorize stale file bytes with restored mtime."""
    leaf = tmp_path / "leaf"
    _ = leaf.write_bytes(b"accepted")
    before = leaf.stat()
    replacement = tmp_path / "replacement"
    _ = replacement.write_bytes(b"tampered")
    native_close = os.close
    changed = False

    def mutate_after_close(descriptor: int) -> None:
        nonlocal changed
        native_close(descriptor)
        if attack == _EXACT_INPLACE_REWRITE:
            _ = leaf.write_bytes(_EXACT_TAMPERED)
        else:
            _ = replacement.replace(leaf)
        os.utime(leaf, ns=(before.st_atime_ns, before.st_mtime_ns))
        changed = True

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", mutate_after_close)
        with pytest.raises(ExactTreeError, match="changed after descriptor close"):
            _ = exact_module.read_exact_regular_file(leaf, "tree entry")
    _expect(changed, "the descriptor close mutation did not execute")
    assert leaf.read_bytes() == _EXACT_TAMPERED


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
        all(not item.path.startswith("external/") for item in plan.source.files),
        "passthrough path leaked into static source snapshot",
    )


@pytest.mark.parametrize(
    "reported",
    [_SHORT_WRITE, None, True, -1, 10**9],
)
def test_passthrough_write_count_must_not_publish_incomplete_dynamic_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reported: object,
) -> None:
    """Dynamic passthrough bytes need complete writes, not a static digest."""
    source, oracle = _synthetic_pair(tmp_path)
    _write(source, "external/game.bin", b"authoring-data")
    _write(oracle, "external/game.bin", b"authoring-data")
    plan = build_exact_plan(source, oracle, passthrough_roots=("external",))
    _write(source, "external/game.bin", _RUNTIME_DATA)
    output = tmp_path / "passthrough-out"
    staging = tmp_path / ".passthrough-out.staging"
    blocked = staging / "external/game.bin"
    original_write = cast(
        "Callable[[Path, bytes], int]", vars(exact_module)["_NATIVE_WRITE_OUTPUT_BYTES"]
    )

    def misreported_write(path: Path, data: bytes) -> int:
        if path == blocked and reported == _SHORT_WRITE:
            return original_write(path, data[:1])
        written = original_write(path, data)
        if path == blocked:
            return cast("int", reported)
        return written

    monkeypatch.setattr(exact_module, "_NATIVE_WRITE_OUTPUT_BYTES", misreported_write)
    with pytest.raises(ExactTreeError, match="short or invalid byte count"):
        materialize_exact_plan(source, plan, output)
    assert not output.exists()
    assert not staging.exists()


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


def test_exact_snapshot_rejects_late_type_spoofed_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nonnative Path subclass cannot become a trusted source root."""
    native_path_type = type(Path())
    foreign_path_type = type("ForeignPath", (native_path_type,), {})
    root = tmp_path / "source"
    root.mkdir()
    foreign = cast("Path", foreign_path_type(root))
    native_type = type
    expected_context = "exact pathlib Path"
    rejected = False

    def forged_type(value: object) -> type:
        if native_type(value) is foreign_path_type:
            return native_path_type
        return native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = snapshot_tree(foreign)
        except ExactTreeError as error:
            rejected = expected_context in str(error)
    assert rejected, "late type hook admitted a foreign snapshot root"


def test_exact_read_rejects_late_type_spoofed_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable host read receipt must not become authoritative bytes."""
    read_chunk = cast(
        "Callable[[int, int, str], bytes]",
        vars(exact_module)["_read_native_chunk"],
    )
    foreign = bytearray(b"data")
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    def forged_read(descriptor: int, count: int) -> bytearray:
        del descriptor, count
        return foreign

    with monkeypatch.context() as patched:
        patched.setattr(os, "read", forged_read)
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = read_chunk(7, 4, "test receipt")
        except ExactTreeError:
            rejected = True
    assert rejected, "late type hook admitted a mutable read receipt"


def test_exact_snapshot_ignores_late_len_size_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late length hook cannot falsify a snapshot's file-size receipt."""
    root = tmp_path / "source"
    root.mkdir()
    source_bytes = b"abc"
    _write(root, "file", source_bytes)
    baseline = snapshot_tree(root)
    native_len = len

    def forged_len(value: object) -> int:
        if type(value) is bytes and value == source_bytes:
            return 100
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        observed = snapshot_tree(root)
    assert observed == baseline, "late len hook falsified snapshot file size"


def test_exact_roots_reject_late_enumerate_suppression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late enumerate override must not skip nested passthrough roots."""
    normalized_roots = cast(
        "Callable[[tuple[str, ...]], tuple[str, ...]]",
        vars(exact_module)["_normalized_roots"],
    )

    def omit_roots(values: object) -> tuple[()]:
        del values
        return ()

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "enumerate", omit_roots)
        try:
            _ = normalized_roots(("src", "src/nested"))
        except ExactTreeError:
            rejected = True
    assert rejected, "late enumerate admitted nested passthrough roots"


def test_exact_roots_accept_native_disjoint_after_late_enumerate_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid pair of native roots does not require the current builtin."""
    normalized_roots = cast(
        "Callable[[tuple[str, ...]], tuple[str, ...]]",
        vars(exact_module)["_normalized_roots"],
    )

    def omit_roots(values: object) -> tuple[()]:
        del values
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "enumerate", omit_roots)
        roots = normalized_roots(("src", "tests"))
    assert roots == ("src", "tests")


def test_exact_root_admission_ignores_late_fsencode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-import filesystem hook cannot replace exact root preflight."""
    _write(tmp_path, "src/a.c", b"trusted source")
    baseline = snapshot_tree(tmp_path)
    calls = 0

    def forged_fsencode(value: object) -> bytes:
        nonlocal calls
        del value
        calls += 1
        raise AssertionError("consumer fsencode hook executed")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsencode", forged_fsencode)
        observed = snapshot_tree(tmp_path)
    assert observed == baseline
    assert calls == 0, "consumer filesystem codec hook was consulted"


@pytest.mark.parametrize("invalid", [False, True])
def test_exact_root_admission_ignores_late_path_string_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: bool,
) -> None:
    """A late Path formatter cannot authorize or deny a native root."""
    require_root = cast(
        "Callable[[object, str], None]",
        vars(exact_module)["_require_filesystem_root"],
    )
    source = tmp_path / ("nul\x00root" if invalid else "safe-root")

    def forged_path_string(path: Path) -> str:
        del path
        return "safe-root" if invalid else "nul\x00root"

    with monkeypatch.context() as patch:
        patch.setattr(Path, "__str__", forged_path_string)
        if invalid:
            with pytest.raises(ExactTreeError, match="representable"):
                require_root(source, "tree root")
        else:
            require_root(source, "tree root")


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("source", "observed-source"),
        ("target", TreeSnapshot(())),
        ("instructions", ()),
        ("passthrough_roots", ("forged",)),
    ],
)
def test_exact_materialization_ignores_late_plan_field_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    forged: object,
) -> None:
    """Validated plan storage cannot be replaced by consumer class accessors."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    if field == "source":
        _write(source, "keep.txt", b"changed after planning")
    replacement = snapshot_tree(source) if field == "source" else forged
    original = ExactAuthoringPlan.__getattribute__
    calls = 0

    def forged_getter(record: ExactAuthoringPlan, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return replacement
        return original(record, name)

    with monkeypatch.context() as patch:
        patch.setattr(ExactAuthoringPlan, "__getattribute__", forged_getter)
        if field == "source":
            with pytest.raises(ExactTreeError, match="source tree"):
                materialize_exact_plan(source, plan, output)
        else:
            materialize_exact_plan(source, plan, output)
    assert calls == 0, "late plan getter influenced exact admission"
    assert output.exists() is (field != "source")


def test_exact_materialization_rejects_late_snapshot_equality_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacing record equality must not forgive changed source evidence."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "unrelated.txt", b"source v1")
    _write(oracle, "target.txt", b"literal-only target")
    plan = build_exact_plan(source, oracle)
    _write(source, "unrelated.txt", b"source v2")
    output = tmp_path / "result"
    calls = 0

    def forged_eq(_left: TreeSnapshot, _right: object) -> bool:
        nonlocal calls
        calls += 1
        return True

    with monkeypatch.context() as patch:
        patch.setattr(TreeSnapshot, "__eq__", forged_eq)
        with pytest.raises(ExactTreeError, match="source tree"):
            materialize_exact_plan(source, plan, output)
    assert calls == 0, "late snapshot equality skipped source verification"
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("output_path", "forged.bin"),
        ("kind", ExactInstructionKind.LITERAL_ORACLE),
        ("expected_sha256", "f" * 64),
        ("source_path", "other.bin"),
    ],
)
def test_exact_materialization_ignores_late_instruction_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: object,
) -> None:
    """Replay reads admitted instruction fields, not substituted class hooks."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "safe.bin", b"verified source bytes")
    _write(source, "other.bin", b"wrong source bytes")
    _write(oracle, "target.bin", b"verified source bytes")
    plan = build_exact_plan(source, oracle)
    original = ExactInstruction.__getattribute__
    calls = 0

    def forged_getter(record: ExactInstruction, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return replacement
        return original(record, name)

    output = tmp_path / "result"
    with monkeypatch.context() as patch:
        patch.setattr(ExactInstruction, "__getattribute__", forged_getter)
        materialize_exact_plan(source, plan, output)
    assert calls == 0, "late instruction getter changed exact replay"
    assert (output / "target.bin").read_bytes() == b"verified source bytes"
    assert not (output / "forged.bin").exists()


@pytest.mark.parametrize("field", ["path", "sha256", "size"])
def test_exact_plan_ignores_late_file_record_getters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Planning uses admitted source/target record metadata, not hooks."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "same.bin", b"source bytes")
    _write(oracle, "same.bin", b"source bytes")
    replacements: dict[str, object] = {
        "path": "forged.bin",
        "sha256": "f" * 64,
        "size": 1_000_000,
    }
    replacement = replacements[field]
    original = FileRecord.__getattribute__
    calls = 0

    def forged_getter(record: FileRecord, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return replacement
        return original(record, name)

    with monkeypatch.context() as patch:
        patch.setattr(FileRecord, "__getattribute__", forged_getter)
        plan = build_exact_plan(source, oracle)
    assert calls == 0, "late file record getter influenced plan authoring"
    assert plan.target.files[0].path == "same.bin"
    assert plan.instructions[0].kind is ExactInstructionKind.COPY_SOURCE


@pytest.mark.parametrize("field", ["offset", "length"])
def test_exact_replay_ignores_late_slice_getters(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A patched class accessor cannot redirect admitted byte-range reuse."""
    segment = SourceSlice(1, 2)
    original = SourceSlice.__getattribute__
    calls = 0

    def forged_getter(record: SourceSlice, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return 100
        return original(record, name)

    with monkeypatch.context() as patch:
        patch.setattr(SourceSlice, "__getattribute__", forged_getter)
        result = exact_module._patch_bytes(b"abcd", (segment,))
    assert calls == 0, "late source slice getter modified exact byte ranges"
    assert result == b"bc"


def test_exact_replay_ignores_late_literal_data_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Literal patch bytes remain pinned to the admitted literal record."""
    segment = OracleLiteral(b"admitted")
    original = OracleLiteral.__getattribute__
    calls = 0

    def forged_getter(record: OracleLiteral, name: str) -> object:
        nonlocal calls
        if name == "data":
            calls += 1
            return b"forged"
        return original(record, name)

    with monkeypatch.context() as patch:
        patch.setattr(OracleLiteral, "__getattribute__", forged_getter)
        result = exact_module._patch_bytes(b"source", (segment,))
    assert calls == 0, "late literal data getter modified exact output bytes"
    assert result == b"admitted"


def test_exact_plan_ignores_late_snapshot_files_getter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A patched snapshot files getter must not erase authoring evidence."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "source.bin", b"admitted")
    _write(oracle, "target.bin", b"admitted")
    original = TreeSnapshot.__getattribute__
    calls = 0

    def forged_getter(record: TreeSnapshot, field: str) -> object:
        nonlocal calls
        if field == "files":
            calls += 1
            return ()
        return original(record, field)

    with monkeypatch.context() as patch:
        patch.setattr(TreeSnapshot, "__getattribute__", forged_getter)
        plan = build_exact_plan(source, oracle)
    assert calls == 0, "late snapshot getter erased planned output"
    assert len(plan.target.files) == 1
    assert len(plan.instructions) == 1


def test_exact_passthrough_equality_does_not_trust_late_record_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Different runtime roots are not equivalent under fake record equality."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "data/runtime.bin", b"runtime v1")
    _write(oracle, "data/runtime.bin", b"runtime v2")
    calls = 0

    def forged_eq(_left: TreeSnapshot, _right: object) -> bool:
        nonlocal calls
        calls += 1
        return True

    with monkeypatch.context() as patch:
        patch.setattr(TreeSnapshot, "__eq__", forged_eq)
        with pytest.raises(ExactTreeError, match="passthrough roots differ"):
            _ = build_exact_plan(source, oracle, passthrough_roots=("data",))
    assert calls == 0, "late snapshot equality skipped passthrough admission"


def test_exact_materialization_rejects_foreign_plan_before_tree_reads(
    tmp_path: Path,
) -> None:
    """An arbitrary object cannot impersonate admitted authoring evidence."""
    source = tmp_path / "missing-source"
    output = tmp_path / "output"
    with pytest.raises(ExactTreeError, match="exact authoring plan"):
        materialize_exact_plan(source, cast("ExactAuthoringPlan", object()), output)
    assert not output.exists()


@pytest.mark.parametrize(
    "case",
    [
        ("_MatchContext", "source"),
        ("_MatchContext", "target"),
        ("_MatchContext", "index"),
        ("_PlanningContext", "source_root"),
        ("_PlanningContext", "oracle_root"),
        ("_PlanningContext", "source_by_path"),
        ("_PlanningContext", "source_by_content"),
    ],
)
def test_exact_transient_contexts_preserve_fields_under_late_setters(
    monkeypatch: pytest.MonkeyPatch, case: tuple[str, str]
) -> None:
    """Class properties must not redirect exact patch or tree-planning data."""
    name, field = case
    values: dict[str, dict[str, object]] = {
        "_MatchContext": {
            "source": b"source evidence",
            "target": b"target evidence",
            "index": {b"source": 0},
        },
        "_PlanningContext": {
            "source_root": Path("source"),
            "oracle_root": Path("oracle"),
            "source_by_path": {},
            "source_by_content": {},
        },
    }
    owner = cast("type[object]", vars(exact_module)[name])
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    intercepted: list[object] = []
    forged = object()

    def forged_setter(value: object, supplied: object) -> None:
        intercepted.append(supplied)
        slot.__set__(value, forged)

    def read_original(value: object) -> object:
        return cast("object", slot.__get__(value, owner))

    with monkeypatch.context() as patched:
        patched.setattr(owner, field, property(read_original, forged_setter))
        created = cast("Callable[..., object]", owner)(**values[name])
    assert not intercepted, "late context field setter changed internal storage"
    assert slot.__get__(created, owner) is values[name][field]


@pytest.mark.parametrize("test_case", ["matching", "changed"])
def test_exact_plan_ignores_late_init_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, test_case: str
) -> None:
    """A late plan initializer cannot erase source-derived instructions."""
    source, oracle = _synthetic_pair(tmp_path)
    if test_case == "matching":
        _write(oracle, "modify.txt", b"old\n")
    expected = build_exact_plan(source, oracle)
    original_init = cast("Callable[..., None]", ExactAuthoringPlan.__dict__["__init__"])
    instruction_slot = cast(
        "MemberDescriptorType", ExactAuthoringPlan.__dict__["instructions"]
    )
    calls = 0

    def forged_init(self: ExactAuthoringPlan, *args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        original_init(self, *args, **kwargs)
        instruction_slot.__set__(self, ())

    with monkeypatch.context() as patched:
        patched.setattr(ExactAuthoringPlan, "__init__", forged_init)
        assert build_exact_plan(source, oracle) == expected
    assert calls == 0, "late plan initializer replaced computed instructions"


@pytest.mark.parametrize("test_case", ["matching", "changed"])
def test_exact_plan_ignores_late_new_hook(test_case: str) -> None:
    """Check unsafe post-import __new__ patch in an isolated interpreter."""
    script = f"""
from pathlib import Path
from tempfile import TemporaryDirectory
from test_exact import _synthetic_pair, _write
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.model import ExactAuthoringPlan
with TemporaryDirectory() as directory:
    source, oracle = _synthetic_pair(Path(directory))
    if {test_case!r} == "matching":
        _write(oracle, "modify.txt", b"old\\n")
    baseline = build_exact_plan(source, oracle)
    def forbidden_new(*args, **kwargs):
        raise AssertionError("late plan allocation was consulted")
    ExactAuthoringPlan.__new__ = staticmethod(forbidden_new)
    assert build_exact_plan(source, oracle) == baseline
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [*sys.path, "tests/function/algorithms/domain/diff"]
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("record", ["instruction", "literal", "slice"])
def test_exact_internal_records_ignore_late_init_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Plan creation cannot reenter a replaced instruction/segment initializer."""
    source, oracle = _synthetic_pair(tmp_path)
    expected = build_exact_plan(source, oracle)
    owner: type[object] = {
        "instruction": ExactInstruction,
        "literal": OracleLiteral,
        "slice": SourceSlice,
    }[record]
    calls = 0

    def forbidden_init(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late instruction/segment initializer was consulted")

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__init__", forbidden_init)
        assert build_exact_plan(source, oracle) == expected
    assert calls == 0, "late instruction/segment initializer was consulted"


@pytest.mark.parametrize("record", ["instruction", "literal", "slice"])
def test_exact_internal_records_ignore_late_new_hook(record: str) -> None:
    """Isolate unsafe allocation replacement from other exact plan tests."""
    script = f"""
from pathlib import Path
from tempfile import TemporaryDirectory
from test_exact import _synthetic_pair
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.model import ExactInstruction, OracleLiteral, SourceSlice
with TemporaryDirectory() as directory:
    source, oracle = _synthetic_pair(Path(directory))
    expected = build_exact_plan(source, oracle)
    owner = {{
        "instruction": ExactInstruction,
        "literal": OracleLiteral,
        "slice": SourceSlice,
    }}[{record!r}]
    def forbidden_new(*args, **kwargs):
        raise AssertionError("late instruction/segment allocation was consulted")
    owner.__new__ = staticmethod(forbidden_new)
    assert build_exact_plan(source, oracle) == expected
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [*sys.path, "tests/function/algorithms/domain/diff"]
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("context", ["_MatchContext", "_PlanningContext"])
def test_exact_internal_contexts_ignore_late_init_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str
) -> None:
    """Admitted tree roots and patch bytes survive late context hook changes."""
    source, oracle = _synthetic_pair(tmp_path)
    baseline = build_exact_plan(source, oracle)
    owner = cast("type[object]", vars(exact_module)[context])
    calls = 0

    def forged_init(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late matching/planning context initializer was called")

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__init__", forged_init)
        assert build_exact_plan(source, oracle) == baseline
    assert calls == 0, "late matching/planning initializer participated in plan"


@pytest.mark.parametrize("context", ["_MatchContext", "_PlanningContext"])
def test_exact_internal_contexts_ignore_late_new_hook(context: str) -> None:
    """Check context allocation hardening in an isolated interpreter."""
    script = f"""
from pathlib import Path
from tempfile import TemporaryDirectory
from test_exact import _synthetic_pair
from algorithms.diff.exact import build_exact_plan
from algorithms.diff import exact as exact_module
with TemporaryDirectory() as directory:
    source, oracle = _synthetic_pair(Path(directory))
    expected = build_exact_plan(source, oracle)
    owner = vars(exact_module)[{context!r}]
    def forbidden_new(*args, **kwargs):
        raise AssertionError("late matching/planning allocation was consulted")
    owner.__new__ = staticmethod(forbidden_new)
    assert build_exact_plan(source, oracle) == expected
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [*sys.path, "tests/function/algorithms/domain/diff"]
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


_SNAPSHOT_CONSTRUCTION_CASES = (
    ("file", "normal"),
    ("file", "excluded"),
    ("tree", "normal"),
    ("tree", "excluded"),
    ("tree", "filtered"),
)


@pytest.mark.parametrize(("record", "entrypoint"), _SNAPSHOT_CONSTRUCTION_CASES)
def test_exact_snapshot_ignores_late_record_init_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    entrypoint: str,
) -> None:
    """Tree scans and passthrough filtering cannot forge snapshot metadata."""
    source, _ = _synthetic_pair(tmp_path)
    baseline = snapshot_tree(source)

    def snapshot() -> TreeSnapshot:
        if entrypoint == "excluded":
            return snapshot_tree_excluding(source, ("assets",))
        if entrypoint == "filtered":
            return exact_module._filter_snapshot(baseline, ("assets",), inside=False)
        return snapshot_tree(source)

    expected = snapshot()
    owner = FileRecord if record == "file" else TreeSnapshot
    calls = 0

    def forbidden_init(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late snapshot initializer executed")

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__init__", forbidden_init)
        assert snapshot() == expected
    assert calls == 0


@pytest.mark.parametrize(("record", "entrypoint"), _SNAPSHOT_CONSTRUCTION_CASES)
def test_exact_snapshot_ignores_late_record_new_hook(
    record: str,
    entrypoint: str,
) -> None:
    """Test native snapshot allocation after class mutation in a child."""
    script = f'''
from pathlib import Path
from tempfile import TemporaryDirectory
from test_exact import _synthetic_pair
from algorithms.diff.exact import snapshot_tree, snapshot_tree_excluding, _filter_snapshot
from algorithms.diff.model import FileRecord, TreeSnapshot
with TemporaryDirectory() as directory:
    source, _ = _synthetic_pair(Path(directory))
    baseline = snapshot_tree(source)
    def snapshot():
        if {entrypoint!r} == "excluded":
            return snapshot_tree_excluding(source, ("assets",))
        if {entrypoint!r} == "filtered":
            return _filter_snapshot(baseline, ("assets",), inside=False)
        return snapshot_tree(source)
    expected = snapshot()
    owner = FileRecord if {record!r} == "file" else TreeSnapshot
    def forbidden_new(*args, **kwargs):
        raise AssertionError("late snapshot allocation executed")
    owner.__new__ = staticmethod(forbidden_new)
    assert snapshot() == expected
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [*sys.path, "tests/function/algorithms/domain/diff"]
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
