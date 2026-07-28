# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Exact-baseline tests for the generic source-bound diff authoring model."""

from typing import TYPE_CHECKING

import pytest

from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import materialize_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice

if TYPE_CHECKING:
    from pathlib import Path

_MOVED_SOURCE = "rename-me.txt"
_PATCH_PATH = "patch.txt"
_PATCH_PREFIX = b"0123456789abcdef" * 8
_PATCH_INSERTION = b"<inserted-target-only>"
_PATCH_SUFFIX = b"fedcba9876543210" * 8
_RUNTIME_DATA = b"runtime-data"
_RUNTIME_EXTRA = b"runtime-extra"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, relative_path: str, data: bytes) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


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


def test_exact_materialization_rejects_existing_output(tmp_path: Path) -> None:
    """Never overwrite an existing output tree implicitly."""
    source, oracle = _synthetic_pair(tmp_path)
    plan = build_exact_plan(source, oracle)
    output = tmp_path / "result"
    output.mkdir()

    with pytest.raises(ExactTreeError, match="already exists"):
        materialize_exact_plan(source, plan, output)


def test_snapshot_rejects_symlink_when_supported(tmp_path: Path) -> None:
    """Do not silently dereference source-tree symlinks."""
    root = tmp_path / "tree"
    root.mkdir()
    target = root / "target.txt"
    target.write_bytes(b"target")
    link = root / "link.txt"
    try:
        link.symlink_to(target.name)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(ExactTreeError, match="symlinks"):
        snapshot_tree(root)


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
        build_exact_plan(
            source,
            oracle,
            passthrough_roots=("external",),
        )
