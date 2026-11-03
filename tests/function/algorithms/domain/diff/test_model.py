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
from dataclasses import replace
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

type ModelRecord = (
    FileRecord | TreeSnapshot | SourceSlice | OracleLiteral
    | ExactInstruction | ExactAuthoringPlan
)


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


_MODEL_VALID_RECORDS = (
    (FileRecord, lambda: FileRecord("ok.bin", _HASH, 1)),
    (TreeSnapshot, lambda: TreeSnapshot((FileRecord("ok.bin", _HASH, 1),))),
    (SourceSlice, lambda: SourceSlice(0, 1)),
    (OracleLiteral, lambda: OracleLiteral(b"ok")),
    (
        ExactInstruction,
        lambda: ExactInstruction(
            "ok.bin", ExactInstructionKind.COPY_SOURCE, _HASH,
            source_path="ok.bin",
        ),
    ),
    (
        ExactAuthoringPlan,
        lambda: ExactAuthoringPlan(TreeSnapshot(()), TreeSnapshot(()), ()),
    ),
)


@pytest.mark.parametrize(
    ("record_type", "factory", "invalid_field", "invalid_value"),
    [
        (FileRecord, _MODEL_VALID_RECORDS[0][1], "size", -1),
        (TreeSnapshot, _MODEL_VALID_RECORDS[1][1], "files", []),
        (SourceSlice, _MODEL_VALID_RECORDS[2][1], "length", 0),
        (OracleLiteral, _MODEL_VALID_RECORDS[3][1], "data", bytearray(b"bad")),
        (ExactInstruction, _MODEL_VALID_RECORDS[4][1], "source_path", None),
        (ExactAuthoringPlan, _MODEL_VALID_RECORDS[5][1], "source", object()),
    ],
)
def test_model_constructor_validator_cannot_be_replaced(
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[object],
    factory: Callable[[], object],
    invalid_field: str,
    invalid_value: object,
) -> None:
    """Frozen record constructors still validate under late post-init hooks."""
    valid = factory()
    calls = 0

    def skip_validator(_record: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patch:
        patch.setattr(record_type, "__post_init__", skip_validator)
        with pytest.raises(TreeModelError):
            _ = replace(
                cast("ModelRecord", valid), **{invalid_field: invalid_value}
            )
    assert calls == 0, "late class validator admitted invalid model evidence"


@pytest.mark.parametrize(("record_type", "factory"), _MODEL_VALID_RECORDS)
def test_model_constructor_preserves_valid_records_after_validator_swap(
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[object],
    factory: Callable[[], object],
) -> None:
    """A foreign late post-init cannot reject admitted model evidence."""
    valid = factory()
    calls = 0

    def reject_every_record(_record: object) -> None:
        nonlocal calls
        calls += 1
        raise TreeModelError("forged model validator rejection")

    with monkeypatch.context() as patch:
        patch.setattr(record_type, "__post_init__", reject_every_record)
        replaced = replace(cast("ModelRecord", valid))
    assert replaced == valid
    assert calls == 0, "late class validator rejected valid model evidence"


@pytest.mark.parametrize(
    ("field", "invalid", "forged"),
    [
        ("output_path", "../bad", "good.bin"),
        ("kind", "copy-source", ExactInstructionKind.COPY_SOURCE),
        ("expected_sha256", "invalid", _HASH),
        ("source_path", None, "source.bin"),
        ("literal", bytearray(b"bad"), None),
        ("segments", [], ()),
    ],
)
def test_model_exact_instruction_rejects_late_descriptor_spoof(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
    forged: object,
) -> None:
    """Constructors validate original slots, not class properties."""
    fields: dict[str, object] = {
        "output_path": "good.bin",
        "kind": ExactInstructionKind.COPY_SOURCE,
        "expected_sha256": _HASH,
        "source_path": "source.bin",
        "literal": None,
        "segments": (),
    }
    fields[field] = invalid
    calls = 0

    original = ExactInstruction.__getattribute__

    def spoof(record: ExactInstruction, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(record, name))

    with monkeypatch.context() as patch:
        patch.setattr(ExactInstruction, "__getattribute__", spoof)
        with pytest.raises(TreeModelError):
            constructor = cast(
                "Callable[..., ExactInstruction]", ExactInstruction
            )
            _ = constructor(**fields)
    assert calls == 0, "instruction validation consulted class getter"


def test_model_exact_instruction_rejects_late_method_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The original instruction-kind validation cannot be skipped."""
    calls = 0

    def skip(_record: ExactInstruction) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patch:
        patch.setattr(ExactInstruction, "_validate_copy", skip)
        with pytest.raises(TreeModelError, match="copy-source"):
            _ = ExactInstruction(
                "good.bin", ExactInstructionKind.COPY_SOURCE, _HASH
            )
    assert calls == 0, "late instruction validator replaced the original"


@pytest.mark.parametrize(
    ("field", "invalid", "forged"),
    [
        ("source", object(), TreeSnapshot(())),
        ("target", object(), TreeSnapshot(())),
        ("instructions", [], ()),
        ("passthrough_roots", [], ()),
    ],
)
def test_model_exact_plan_rejects_late_descriptor_spoof(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
    forged: object,
) -> None:
    """Plans never admit foreign record fields through patched getters."""
    fields: dict[str, object] = {
        "source": TreeSnapshot(()), "target": TreeSnapshot(()),
        "instructions": (), "passthrough_roots": (),
    }
    fields[field] = invalid
    calls = 0

    original = ExactAuthoringPlan.__getattribute__

    def spoof(record: ExactAuthoringPlan, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(record, name))

    with monkeypatch.context() as patch:
        patch.setattr(ExactAuthoringPlan, "__getattribute__", spoof)
        with pytest.raises(TreeModelError):
            constructor = cast(
                "Callable[..., ExactAuthoringPlan]", ExactAuthoringPlan
            )
            _ = constructor(**fields)
    assert calls == 0, "exact plan validation consulted class getter"


def test_model_plan_does_not_trust_late_source_digest_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mismatching copy digest cannot be forged to match a target."""
    source_file = FileRecord("source.bin", _HASH, 1)
    target_hash = "f" * 64
    target_file = FileRecord("output.bin", target_hash, 1)
    instruction = ExactInstruction(
        "output.bin", ExactInstructionKind.COPY_SOURCE, target_hash,
        source_path="source.bin",
    )
    original = FileRecord.__getattribute__
    calls = 0

    def spoof(record: FileRecord, field: str) -> object:
        nonlocal calls
        if field == "sha256" and record is source_file:
            calls += 1
            return target_hash
        return cast("object", original(record, field))

    with monkeypatch.context() as patch:
        patch.setattr(FileRecord, "__getattribute__", spoof)
        with pytest.raises(TreeModelError, match="copy-source digest"):
            _ = ExactAuthoringPlan(
                TreeSnapshot((source_file,)),
                TreeSnapshot((target_file,)), (instruction,),
            )
    assert calls == 0, "late source hash getter influenced plan admission"


def test_model_plan_does_not_trust_late_source_slice_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source byte slice outside the file remains invalid under late hooks."""
    source_file = FileRecord("source.bin", _HASH, 1)
    target_file = FileRecord("output.bin", _HASH, 1)
    segment = SourceSlice(50, 1)
    instruction = ExactInstruction(
        "output.bin", ExactInstructionKind.PATCH_SOURCE, _HASH,
        source_path="source.bin", segments=(segment,),
    )
    original = SourceSlice.__getattribute__
    calls = 0

    def spoof(record: SourceSlice, field: str) -> object:
        nonlocal calls
        if field == "offset":
            calls += 1
            return 0
        return cast("object", original(record, field))

    with monkeypatch.context() as patch:
        patch.setattr(SourceSlice, "__getattribute__", spoof)
        with pytest.raises(TreeModelError, match="slice exceeds"):
            _ = ExactAuthoringPlan(
                TreeSnapshot((source_file,)),
                TreeSnapshot((target_file,)), (instruction,),
            )
    assert calls == 0, "late slice offset getter influenced plan admission"


@pytest.mark.parametrize(
    ("record_type", "field"),
    [
        (FileRecord, "path"),
        (TreeSnapshot, "files"),
        (SourceSlice, "length"),
        (OracleLiteral, "data"),
        (ExactInstruction, "output_path"),
        (ExactAuthoringPlan, "passthrough_roots"),
    ],
)
def test_model_constructor_does_not_dispatch_forged_property_setter(
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[ModelRecord],
    field: str,
) -> None:
    """A swapped field setter cannot sanitize rejected constructor data."""
    slot = record_type.__dict__[field]
    calls = 0

    def forged_setter(self: ModelRecord, _value: object) -> None:
        nonlocal calls
        calls += 1
        repaired: object
        if field == "path":
            repaired = "safe"
        elif field == "files":
            repaired = ()
        elif field == "length":
            repaired = 1
        elif field == "data":
            repaired = b"safe"
        elif field == "output_path":
            repaired = "target"
        else:
            repaired = ()
        slot.__set__(self, repaired)

    with monkeypatch.context() as patch:
        patch.setattr(record_type, field, property(fset=forged_setter))
        with pytest.raises(TreeModelError):
            if record_type is FileRecord:
                _ = FileRecord("../unsafe", _HASH, 1)
            elif record_type is TreeSnapshot:
                _ = TreeSnapshot(
                    cast("tuple[FileRecord, ...]", cast("object", []))
                )
            elif record_type is SourceSlice:
                _ = SourceSlice(0, 0)
            elif record_type is OracleLiteral:
                _ = OracleLiteral(
                    cast("bytes", cast("object", bytearray(b"unsafe")))
                )
            elif record_type is ExactInstruction:
                _ = ExactInstruction(
                    output_path="../unsafe",
                    kind=ExactInstructionKind.COPY_SOURCE,
                    expected_sha256=_HASH,
                    source_path="source",
                )
            else:
                _ = ExactAuthoringPlan(
                    source=TreeSnapshot(()),
                    target=TreeSnapshot(()),
                    instructions=(),
                    passthrough_roots=cast(
                        "tuple[str, ...]", cast("object", ["unsafe"])
                    ),
                )
    assert calls == 0, f"constructor dispatched forged {field} setter"


@pytest.mark.parametrize(
    ("record_type", "field"),
    [
        (FileRecord, "path"),
        (FileRecord, "sha256"),
        (FileRecord, "size"),
        (TreeSnapshot, "files"),
        (SourceSlice, "offset"),
        (SourceSlice, "length"),
        (OracleLiteral, "data"),
        (ExactInstruction, "output_path"),
        (ExactInstruction, "kind"),
        (ExactInstruction, "expected_sha256"),
        (ExactInstruction, "source_path"),
        (ExactInstruction, "literal"),
        (ExactInstruction, "segments"),
        (ExactAuthoringPlan, "source"),
        (ExactAuthoringPlan, "target"),
        (ExactAuthoringPlan, "instructions"),
        (ExactAuthoringPlan, "passthrough_roots"),
    ],
)
def test_model_valid_constructor_writes_all_original_slots(
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[ModelRecord],
    field: str,
) -> None:
    """Valid model construction never invokes a substituted field setter."""
    calls = 0

    def forbidden_setter(_self: ModelRecord, _value: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("constructor dispatched a foreign field setter")

    with monkeypatch.context() as patch:
        patch.setattr(record_type, field, property(fset=forbidden_setter))
        if record_type is FileRecord:
            value = FileRecord("file", _HASH, 1)
        elif record_type is TreeSnapshot:
            value = TreeSnapshot(())
        elif record_type is SourceSlice:
            value = SourceSlice(0, 1)
        elif record_type is OracleLiteral:
            value = OracleLiteral(b"literal")
        elif record_type is ExactInstruction:
            value = ExactInstruction(
                output_path="output",
                kind=ExactInstructionKind.COPY_SOURCE,
                expected_sha256=_HASH,
                source_path="source",
            )
        else:
            value = ExactAuthoringPlan(
                source=TreeSnapshot(()),
                target=TreeSnapshot(()),
                instructions=(),
            )
    assert type(value) is record_type
    assert calls == 0, f"valid {record_type.__name__}.{field} used foreign setter"
