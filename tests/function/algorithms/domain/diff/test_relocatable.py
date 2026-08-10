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
#   - Synthetic tests for content-relocatable compatible placement.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for content-relocatable compatible placement."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.exact import build_exact_plan
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.model import TreeModelError
from algorithms.diff.relocatable import RangeLocator
from algorithms.diff.relocatable import RelocatableInstruction
from algorithms.diff.relocatable import RelocatableSourceRange
from algorithms.diff.relocatable import RelocationError
from algorithms.diff.relocatable import build_relocatable_plan
from algorithms.diff.relocatable import materialize_relocatable_plan
import pytest

if TYPE_CHECKING:
    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.relocatable import RelocatableAuthoringPlan

_BLOCKS = 64
_INSERTION = b"candidate-insertion-preserved"
_TARGET = b"TARGET-ONLY-CORRECTION"
_CREATED = b"created-target"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _blocks(label: str) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCKS)
    )


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _fixture(tmp_path: Path) -> tuple[Path, Path, bytes]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    base = _blocks("base")
    _write(source, "code.bin", base)
    _write(source, "copy.bin", _blocks("copy"))
    _write(oracle, "code.bin", base[:900] + _TARGET + base[900:])
    _write(oracle, "copy.bin", _blocks("copy"))
    _write(oracle, "created.bin", _CREATED)
    return source, oracle, base


def test_candidate_insertion_inside_source_range_is_preserved(
    tmp_path: Path,
) -> None:
    """Relocate source spans around an insertion without absolute offsets."""
    source, oracle, base = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    plan = build_relocatable_plan(source, exact)
    candidate = tmp_path / "candidate"
    insertion_offset = 1400
    _write(
        candidate,
        "code.bin",
        base[:insertion_offset] + _INSERTION + base[insertion_offset:],
    )
    _write(candidate, "copy.bin", _blocks("copy") + b"candidate-tail")
    output = tmp_path / "out"

    materialize_relocatable_plan(candidate, plan, output)

    expected_code = (
        base[:900]
        + _TARGET
        + base[900:insertion_offset]
        + _INSERTION
        + base[insertion_offset:]
    )
    _expect(
        (output / "code.bin").read_bytes() == expected_code, "insertion lost"
    )
    _expect(
        (output / "copy.bin").read_bytes()
        == _blocks("copy") + b"candidate-tail",
        "whole-file candidate difference was not preserved",
    )
    _expect(
        (output / "created.bin").read_bytes() == _CREATED,
        "created target file changed",
    )


def test_relocatable_materialization_wraps_path_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep candidate resolution failures inside relocatable placement."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    blocked = candidate / "code.bin"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == blocked:
            message = "blocked relocatable path"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    output = tmp_path / "out"
    with pytest.raises(RelocationError, match="path resolution failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "resolution failure published output")


def test_byte_boundary_change_remains_fail_closed(tmp_path: Path) -> None:
    """Document why semantic token placement is the next compatibility layer."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", b"X" + base[1:])
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="boundary"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "byte-changed boundary published output")


def test_missing_boundary_fails_before_publishing_output(
    tmp_path: Path,
) -> None:
    """Reject a candidate that destroys required source placement evidence."""
    source, oracle, _ = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", _blocks("unrelated"))
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="boundary"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "rejected relocatable output was published")


def test_ambiguous_boundary_fails_closed(tmp_path: Path) -> None:
    """Reject duplicate boundary windows instead of guessing a placement."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    duplicated = base + base
    _write(candidate, "code.bin", duplicated)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="ambiguous"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "ambiguous relocatable output was published")


def test_relocatable_plan_is_deterministic(tmp_path: Path) -> None:
    """Author the same hash-only placement metadata repeatedly."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)

    first = build_relocatable_plan(source, exact)
    second = build_relocatable_plan(source, exact)

    _expect(first == second, "relocatable authoring changed across runs")


def test_exact_model_rejects_boolean_and_foreign_segment_metadata() -> None:
    """Exact source ranges and literals require exact immutable value types."""
    with pytest.raises(TreeModelError, match="exact integers"):
        _ = SourceSlice(offset=True, length=1)
    with pytest.raises(TreeModelError, match="exact integers"):
        _ = SourceSlice(offset=0, length=True)
    with pytest.raises(TreeModelError, match="exact bytes"):
        _ = OracleLiteral(cast("bytes", cast("object", bytearray(b"x"))))


def test_relocatable_metadata_rejects_boolean_and_foreign_records() -> None:
    """Range locators and instructions cannot rely on Python coercions."""
    digest = b"x" * 32
    with pytest.raises(RelocationError, match="positive integer"):
        _ = RangeLocator(
            source_length=True, window_bytes=1, start_digest=digest
        )
    with pytest.raises(RelocationError, match="valid integer"):
        _ = RangeLocator(
            source_length=1, window_bytes=True, start_digest=digest
        )
    with pytest.raises(RelocationError, match="exact SHA-256 bytes"):
        _ = RangeLocator(1, 1, cast("bytes", object()))
    locator = RangeLocator(1, 1, digest)
    with pytest.raises(RelocationError, match="exact locator"):
        _ = RelocatableSourceRange(cast("RangeLocator", object()))
    with pytest.raises(RelocationError, match="exact boolean"):
        _ = RelocatableInstruction(
            "out", "src", cast("bool", cast("object", 1))
        )
    with pytest.raises(RelocationError, match="immutable tuple"):
        _ = RelocatableInstruction(
            "out",
            "src",
            copy_candidate_file=False,
            segments=cast(
                "tuple[RelocatableSourceRange | OracleLiteral, ...]",
                cast("object", [RelocatableSourceRange(locator)]),
            ),
        )
    with pytest.raises(RelocationError, match="foreign segment"):
        _ = RelocatableInstruction(
            "out",
            "src",
            copy_candidate_file=False,
            segments=(cast("RelocatableSourceRange", object()),),
        )


def test_relocatable_public_boundaries_reject_foreign_inputs(
    tmp_path: Path,
) -> None:
    """Build/materialize validate roots and plans before filesystem work."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    with pytest.raises(RelocationError, match="pathlib Path"):
        _ = build_relocatable_plan(cast("Path", object()), exact)
    with pytest.raises(RelocationError, match="exact authoring-plan"):
        _ = build_relocatable_plan(source, cast("ExactAuthoringPlan", object()))
    plan = build_relocatable_plan(source, exact)
    output = tmp_path / "invalid-out"
    with pytest.raises(RelocationError, match="pathlib Path"):
        materialize_relocatable_plan(cast("Path", object()), plan, output)
    with pytest.raises(RelocationError, match="exact plan type"):
        materialize_relocatable_plan(
            source, cast("RelocatableAuthoringPlan", object()), output
        )
    _expect(not output.exists(), "invalid public input published output")
