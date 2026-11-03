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
#   - Exact authoring data-model admission regressions.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Exact authoring data-model admission regressions."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import model as model_module
from algorithms.diff.model import ExactAuthoringPlan
from algorithms.diff.model import ExactInstruction
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import FileRecord
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.model import TreeModelError
from algorithms.diff.model import TreeSnapshot

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

_HASH = "0" * 64


def test_model_rejects_late_type_spoofed_oracle_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable literal must never become valid exact oracle evidence."""
    foreign = bytearray(b"oracle")
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = OracleLiteral(cast("bytes", cast("object", foreign)))
        except TreeModelError:
            rejected = True
    assert rejected, "late type hook admitted mutable oracle bytes"


def test_model_rejects_late_type_spoofed_source_coordinate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fractional byte offset cannot masquerade as native integer."""
    foreign = 1.5
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return int if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = SourceSlice(cast("int", cast("object", foreign)), 1)
        except TreeModelError:
            rejected = True
    assert rejected, "late type hook admitted fractional byte offset"


def test_model_rejects_late_type_spoofed_file_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshot file sizes must remain exact integers."""
    foreign = 1.5
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return int if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = FileRecord("file", _HASH, cast("int", cast("object", foreign)))
        except TreeModelError:
            rejected = True
    assert rejected, "late type hook admitted fractional file size"


def test_model_rejects_late_type_spoofed_foreign_file_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign snapshot records cannot slip through a forged type verdict."""

    class ForeignFile:
        path: str = "file"
        sha256: str = _HASH
        size: int = 1

    foreign = ForeignFile()
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return FileRecord if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = TreeSnapshot((cast("FileRecord", cast("object", foreign)),))
        except TreeModelError:
            rejected = True
    assert rejected, "late type hook admitted foreign snapshot record"


def test_model_rejects_late_type_spoofed_mutable_segments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable segment lists cannot masquerade as immutable authoring data."""
    foreign = [SourceSlice(0, 1)]
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return tuple if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = ExactInstruction(
                output_path="target",
                kind=ExactInstructionKind.PATCH_SOURCE,
                expected_sha256=_HASH,
                source_path="source",
                segments=cast(
                    "tuple[SourceSlice, ...]", cast("object", foreign)
                ),
            )
        except TreeModelError:
            rejected = True
    assert rejected, "late type hook admitted mutable instruction segments"


def test_model_rejects_late_len_spoofed_patch_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable output length hooks cannot approve an inconsistent patch."""
    source = TreeSnapshot(())
    target = TreeSnapshot((FileRecord("out", _HASH, 3),))
    literal = OracleLiteral(b"a")
    instruction = ExactInstruction(
        output_path="out",
        kind=ExactInstructionKind.PATCH_SOURCE,
        expected_sha256=_HASH,
        source_path="dynamic/input",
        segments=(literal,),
    )
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is literal.data:
            return 3
        return native_len(cast("tuple[object, ...]", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = ExactAuthoringPlan(
                source=source,
                target=target,
                instructions=(instruction,),
                passthrough_roots=("dynamic",),
            )
        except TreeModelError:
            rejected = True
    assert rejected, "late len hook admitted a short exact patch"


def test_model_rejects_late_range_spoofed_file_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty host range cannot erase ancestor/descendant collisions."""
    records = (
        FileRecord("file", _HASH, 1),
        FileRecord("file/nested", _HASH, 1),
    )
    rejected = False

    def forged_range(start: int, stop: int) -> tuple[()]:
        del start, stop
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "range", forged_range)
        try:
            _ = TreeSnapshot(records)
        except TreeModelError:
            rejected = True
    assert rejected, "late range hook erased a nested snapshot conflict"


def test_model_rejects_late_enumerate_spoofed_passthrough_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late position iterator cannot hide ancestor passthrough roots."""
    topology = cast(
        "Callable[[tuple[str, ...]], None]",
        vars(model_module)["_validate_passthrough_topology"],
    )

    def omit_all_roots(values: object) -> tuple[()]:
        del values
        return ()

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "enumerate", omit_all_roots)
        try:
            topology(("src", "src/deeper"))
        except TreeModelError:
            rejected = True
    assert rejected, (
        "late enumerate hook admitted overlapping passthrough roots"
    )


def test_model_native_passthrough_topology_survives_late_enumerate_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid and invalid native root topology is independent of aliases."""
    topology = cast(
        "Callable[[tuple[str, ...]], None]",
        vars(model_module)["_validate_passthrough_topology"],
    )

    def omit_all_roots(values: object) -> tuple[()]:
        del values
        return ()

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "enumerate", omit_all_roots)
        topology(("src", "tests"))
        try:
            topology(("src", "src/deeper"))
        except TreeModelError:
            rejected = True
    assert rejected, "overlapping native roots were accepted"
