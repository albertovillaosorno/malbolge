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
import ntpath
import os
from typing import TYPE_CHECKING, cast

import pytest
from algorithms.diff import model as model_module
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

if TYPE_CHECKING:
    from collections.abc import Callable


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


@pytest.mark.parametrize(
    "unsafe",
    ["C:relative", "CON", "src/COM1", "src/stream:fork", "src/trailing."],
)
def test_model_rejects_late_ntpath_splitroot_spoof(
    monkeypatch: pytest.MonkeyPatch,
    unsafe: str,
) -> None:
    """Imported path helpers cannot trust mutable ntpath dependencies."""

    def hide_windows_path(value: object) -> tuple[str, str, str]:
        del value
        return "", "", "safe"

    with monkeypatch.context() as patch:
        patch.setattr(ntpath, "splitroot", hide_windows_path)
        with pytest.raises(TreeModelError, match="canonical relative path"):
            _ = FileRecord(unsafe, _HASH, 1)


@pytest.mark.parametrize("unsafe", ["D:relative", "NUL"])
def test_model_rejects_late_os_fspath_spoof(
    monkeypatch: pytest.MonkeyPatch,
    unsafe: str,
) -> None:
    """A post-import filesystem conversion hook cannot relabel paths."""

    def hide_windows_path(value: object) -> str:
        del value
        return "safe"

    with monkeypatch.context() as patch:
        patch.setattr(os, "fspath", hide_windows_path)
        with pytest.raises(TreeModelError, match="canonical relative path"):
            _ = FileRecord(unsafe, _HASH, 1)


def test_model_rejects_late_builtin_any_in_ntpath(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows device-name rejection cannot use mutable ntpath any()."""

    def omit_reserved_names(values: object) -> bool:
        del values
        return False

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "any", omit_reserved_names)
        with pytest.raises(TreeModelError, match="canonical relative path"):
            _ = FileRecord("CON", _HASH, 1)


@pytest.mark.parametrize(
    ("field", "stored", "forged", "message"),
    [
        ("path", "../unsafe", "safe.bin", "canonical relative path"),
        ("sha256", "not-a-hash", _HASH, "64 lowercase hex digits"),
        ("size", -1, 1, "non-negative integer"),
    ],
)
def test_model_file_record_constructor_ignores_late_field_getter(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    stored: object,
    forged: object,
    message: str,
) -> None:
    """Late class getters cannot misstate stored source snapshot evidence."""
    original_getattribute = FileRecord.__getattribute__
    calls = 0

    def forged_attribute(value: FileRecord, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original_getattribute(value, name))

    values: dict[str, object] = {"path": "safe.bin", "sha256": _HASH, "size": 1}
    values[field] = stored
    with monkeypatch.context() as patched:
        patched.setattr(FileRecord, "__getattribute__", forged_attribute)
        with pytest.raises(TreeModelError, match=message):
            constructor = cast("Callable[..., FileRecord]", FileRecord)
            _ = constructor(**values)
    assert calls == 0, "late file getter concealed invalid stored evidence"


def test_model_tree_snapshot_constructor_ignores_late_files_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable stored file list is never approved by a forged getter."""
    original_getattribute = TreeSnapshot.__getattribute__
    calls = 0

    def forged_files(value: TreeSnapshot, name: str) -> object:
        nonlocal calls
        if name == "files":
            calls += 1
            return ()
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(TreeSnapshot, "__getattribute__", forged_files)
        with pytest.raises(TreeModelError, match="exact immutable tuple"):
            _ = TreeSnapshot(cast("tuple[FileRecord, ...]", cast("object", [])))
    assert calls == 0, "late tree getter concealed mutable files"


def test_model_snapshot_path_order_ignores_late_file_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File path ordering checks must read admitted lexical file paths."""
    first = FileRecord("b.bin", _HASH, 1)
    second = FileRecord("a.bin", _HASH, 1)
    calls = 0

    def forged_path(value: FileRecord) -> str:
        nonlocal calls
        calls += 1
        return "a.bin" if value is first else "b.bin"

    with monkeypatch.context() as patched:
        patched.setattr(FileRecord, "path", property(forged_path))
        with pytest.raises(TreeModelError, match="unique and sorted"):
            _ = TreeSnapshot((first, second))
    assert calls == 0, "late file descriptor forged snapshot order"


@pytest.mark.parametrize(
    ("field", "invalid", "forged", "message"),
    [
        ("offset", -1, 0, "non-negative offset"),
        ("length", 0, 1, "positive length"),
    ],
)
def test_model_source_slice_constructor_ignores_late_field_getter(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: int,
    forged: int,
    message: str,
) -> None:
    """Late class getters cannot conceal invalid stored source offsets."""
    original_getattribute = SourceSlice.__getattribute__
    calls = 0

    def forged_attribute(value: SourceSlice, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original_getattribute(value, name))

    fields = {"offset": 0, "length": 1}
    fields[field] = invalid
    with monkeypatch.context() as patched:
        patched.setattr(SourceSlice, "__getattribute__", forged_attribute)
        with pytest.raises(TreeModelError, match=message):
            _ = SourceSlice(**fields)
    assert calls == 0, "late source-slice getter concealed bad coordinates"


def test_model_oracle_literal_constructor_ignores_late_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored mutable oracle material cannot pass by spoofing class getters."""
    original_getattribute = OracleLiteral.__getattribute__
    calls = 0

    def forged_data(value: OracleLiteral, name: str) -> object:
        nonlocal calls
        if name == "data":
            calls += 1
            return b"trusted"
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(OracleLiteral, "__getattribute__", forged_data)
        with pytest.raises(TreeModelError, match="exact bytes"):
            foreign = cast("bytes", cast("object", bytearray(b"unsafe")))
            _ = OracleLiteral(foreign)
    assert calls == 0, "late literal getter concealed mutable oracle bytes"


@pytest.mark.parametrize("segment_type", ["source", "literal"])
def test_model_exact_output_length_ignores_late_segment_getters(
    monkeypatch: pytest.MonkeyPatch, segment_type: str
) -> None:
    """An exact plan must count stored source and literal byte lengths."""
    if segment_type == "source":
        segment = SourceSlice(0, 2)
        original_getattribute = cast(
            "Callable[[object, str], object]", SourceSlice.__getattribute__
        )
        intercepted = "length"
        altered: object = 4
        record_type: type = SourceSlice
    else:
        segment = OracleLiteral(b"ab")
        original_getattribute = cast(
            "Callable[[object, str], object]", OracleLiteral.__getattribute__
        )
        intercepted = "data"
        altered = b"abcd"
        record_type = OracleLiteral
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == intercepted:
            calls += 1
            return altered
        return original_getattribute(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(record_type, "__getattribute__", forged_attribute)
        observed = model_module._exact_segment_length(segment)
    assert observed == 2, "late segment getter inflated planned output length"
    assert calls == 0, "late segment getter influenced output-size admission"
