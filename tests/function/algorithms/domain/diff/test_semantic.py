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
#   - Synthetic tests for mapped semantic compatible placement.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for mapped semantic compatible placement."""

from __future__ import annotations

import builtins
import hashlib
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import semantic as semantic_module
from algorithms.diff.mapped import MappedUnit, MappedView
from algorithms.diff.semantic import (
    SemanticAuthoringPlan,
    SemanticEdit,
    SemanticLocator,
    SemanticPlacementError,
    apply_semantic_plan,
    build_semantic_plan,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sized

_TOKEN = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]")
_REPLACED = b"extra ; alpha   = new ; omega tail"
_INSERTED = b"alpha   added; omega"
_DELETED = b"alpha      ; omega"
_LARGE_REPLACEMENT = b"new"
_EXPECTED_DISTINCT_INSERTIONS = 2


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _map(raw: bytes) -> MappedView:
    units = tuple(
        MappedUnit(
            canonical=match.group(0),
            raw_start=match.start(),
            raw_end=match.end(),
        )
        for match in _TOKEN.finditer(raw)
    )
    return MappedView(raw=raw, units=units)


def test_replacement_preserves_candidate_formatting() -> None:
    """Patch one semantic unit without normalizing unrelated candidate bytes."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate_raw = b"extra ; alpha   = old ; omega tail"
    candidate = _map(candidate_raw)
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(
        output == _REPLACED,
        "semantic replacement discarded candidate presentation or additions",
    )


def test_format_only_target_change_authors_no_semantic_edits() -> None:
    """Preserve candidate bytes when source and target units agree."""
    source = _map(b"alpha=old;")
    target = _map(b"alpha = old ;")
    candidate = _map(b"alpha\t=\told ;  ")
    plan = build_semantic_plan(source, target)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(not plan.edits, "format-only target authored a semantic edit")
    _expect(output == candidate.raw, "format-only plan rewrote candidate bytes")


def test_semantic_insertion_uses_candidate_boundary_and_preserves_trivia() -> (
    None
):
    """Insert target units at a uniquely located canonical boundary."""
    source = _map(b"alpha ; omega")
    target = _map(b"alpha added ; omega")
    candidate = _map(b"alpha   ; omega")
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(output == _INSERTED, "semantic insertion moved trivia")


def test_distinct_semantic_insertions_remain_valid() -> None:
    """Independent insertion boundaries may coexist in one authoring plan."""
    source = _map(b"a ; b ; c")
    target = _map(b"a ; x ; b ; y ; c")
    plan = build_semantic_plan(source, target, context_units=2)
    _expect(
        len(plan.edits) == _EXPECTED_DISTINCT_INSERTIONS,
        "fixture must author two insertions",
    )
    observed = apply_semantic_plan(source, plan, _map)
    _expect(_map(observed).keys == target.keys, "two insertions changed target")


@pytest.mark.parametrize("distinct_locator", [False, True])
def test_duplicate_insertion_at_one_semantic_boundary_is_rejected(
    *,
    distinct_locator: bool,
) -> None:
    """Different hashed locators cannot reuse one zero-width coordinate."""
    source = _map(b"a ; b")
    target = _map(b"a ; x ; b")
    plan = build_semantic_plan(source, target, context_units=2)
    _expect(len(plan.edits) == 1, "fixture must author one insertion")
    original = plan.edits[0]
    _expect(
        not original.locator.source_digests,
        "fixture insertion must have zero source width",
    )
    _expect(
        _map(apply_semantic_plan(source, plan, _map)).keys == target.keys,
        "single insertion must remain valid",
    )
    second = original
    if distinct_locator:
        second = SemanticEdit(
            locator=SemanticLocator(
                source_digests=(),
                before_digests=original.locator.before_digests[-1:],
                after_digests=(),
            ),
            replacement=original.replacement,
            replacement_digests=original.replacement_digests,
        )
        _expect(second != original, "fixture locators must differ")
    duplicate = SemanticAuthoringPlan((original, second))
    with pytest.raises(SemanticPlacementError, match="overlap or reorder"):
        _ = apply_semantic_plan(source, duplicate, _map)


def test_semantic_deletion_keeps_surrounding_candidate_whitespace() -> None:
    """Delete only mapped source units and leave presentation gaps untouched."""
    source = _map(b"alpha obsolete ; omega")
    target = _map(b"alpha ; omega")
    candidate = _map(b"alpha   obsolete   ; omega")
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(output == _DELETED, "semantic deletion removed trivia")


def test_changed_or_ambiguous_source_region_fails_closed() -> None:
    """Reject unavailable or ambiguous semantic source evidence."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target, context_units=1)

    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(_map(b"alpha = upstream ; omega"), plan, _map)
    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(
            _map(b"alpha = old ; omega alpha = old ; omega"),
            plan,
            _map,
        )


class _ForgedSemanticUnitDigest:
    """Stand-in hash object supplying one chosen SHA-256 digest."""

    def __init__(self, digest: bytes) -> None:
        self.digest_value: bytes = digest

    def digest(self) -> bytes:
        """Return the spoofed digest.

        Returns:
            A valid-size but substituted SHA-256 digest.

        """
        return self.digest_value


def test_semantic_locator_rejects_hostile_post_import_hash_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged digest cannot turn unrelated candidate tokens into source."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate = _map(b"alpha = upstream ; omega")
    plan = build_semantic_plan(source, target)
    genuine_constructor = hashlib.sha256
    original_unit = b"old"
    source_frame = (
        b"semantic-placement-unit-v1\0"
        + len(original_unit).to_bytes(8, "big")
        + original_unit
    )
    original_digest = genuine_constructor(source_frame).digest()

    def forged_constructor(data: bytes = b"") -> object:
        if data.endswith(b"upstream"):
            return _ForgedSemanticUnitDigest(original_digest)
        return genuine_constructor(data)

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", forged_constructor)
        with pytest.raises(
            SemanticPlacementError, match="missing or ambiguous"
        ):
            _ = apply_semantic_plan(candidate, plan, _map)


def test_semantic_authoring_ignores_hostile_hash_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing the ambient hash constructor cannot erase an authored edit."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")

    def forged_constructor(data: bytes = b"") -> _ForgedSemanticUnitDigest:
        del data
        return _ForgedSemanticUnitDigest(b"z" * 32)

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", forged_constructor)
        plan = build_semantic_plan(source, target)
        observed = apply_semantic_plan(source, plan, _map)

    _expect(
        bool(plan.edits), "hostile constructor suppressed the semantic edit"
    )
    _expect(
        observed == target.raw, "hostile constructor changed authored output"
    )


def test_retokenization_rejects_unsafe_insertion_seam() -> None:
    """Fail when raw insertion would merge semantic tokens."""
    source = _map(b"a;")
    target = _map(b"a b;")
    candidate = _map(b"a;")
    plan = build_semantic_plan(source, target, context_units=1)

    with pytest.raises(SemanticPlacementError, match="replacement seam"):
        _ = apply_semantic_plan(candidate, plan, _map)


def test_semantic_mapper_cannot_substitute_foreign_raw_source() -> None:
    """Post-edit digests must describe the actual output, not another file."""
    source = _map(b"a;")
    target = _map(b"a b;")
    candidate = _map(b"a;")
    plan = build_semantic_plan(source, target, context_units=1)
    expected_but_unpublished = _map(b"a b;")

    def foreign_raw_mapper(_: bytes) -> MappedView:
        return expected_but_unpublished

    with pytest.raises(SemanticPlacementError, match="actual output bytes"):
        _ = apply_semantic_plan(candidate, plan, foreign_raw_mapper)


def test_semantic_mapper_failure_is_contained() -> None:
    """Map failures after edits stay inside semantic placement diagnostics."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate = _map(b"alpha = old ; omega")
    plan = build_semantic_plan(source, target)

    def fail_mapper(_: bytes) -> MappedView:
        message = "consumer mapper boom"
        raise RuntimeError(message)

    with pytest.raises(SemanticPlacementError, match="mapper failed"):
        _ = apply_semantic_plan(candidate, plan, fail_mapper)


def test_semantic_mapper_does_not_format_foreign_exception() -> None:
    """A failed mapper cannot execute arbitrary exception string hooks."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target)

    class HostileError(RuntimeError):
        @override
        def __str__(self) -> str:
            message = "foreign mapper exception formatter executed"
            raise AssertionError(message)

    failure = HostileError("untrusted callback failure")

    def hostile_mapper(_: bytes) -> MappedView:
        raise failure

    with pytest.raises(
        SemanticPlacementError, match="semantic mapper failed"
    ) as caught:
        _ = apply_semantic_plan(source, plan, hostile_mapper)
    assert caught.value.__cause__ is failure


def test_semantic_mapper_return_type_is_exact() -> None:
    """Reject foreign mapper output before digest inspection."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate = _map(b"alpha = old ; omega")
    plan = build_semantic_plan(source, target)

    def foreign_mapper(_: bytes) -> MappedView:
        return cast("MappedView", object())

    with pytest.raises(SemanticPlacementError, match="exact MappedView"):
        _ = apply_semantic_plan(candidate, plan, foreign_mapper)


def test_semantic_authoring_is_deterministic() -> None:
    """Produce stable hashed locators and target replacements across runs."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")

    first = build_semantic_plan(source, target)
    second = build_semantic_plan(source, target)

    _expect(first == second, "semantic authoring changed across runs")


def test_large_repetitive_sequence_authors_local_edit() -> None:
    """Keep a large repetitive fixture local instead of quadratic matching."""
    repeated = b"a " * 5_000
    source = _map(repeated + b"old " + repeated)
    target = _map(repeated + b"new " + repeated)

    plan = build_semantic_plan(source, target)

    _expect(len(plan.edits) == 1, "large local change fragmented unexpectedly")
    _expect(
        plan.edits[0].replacement == _LARGE_REPLACEMENT,
        "large local replacement changed",
    )


def test_semantic_metadata_requires_exact_digest_records() -> None:
    """Locators, edits, and plans reject mutable or malformed metadata."""
    digest = b"x" * 32
    with pytest.raises(SemanticPlacementError, match="immutable tuples"):
        _ = SemanticLocator(
            cast("tuple[bytes, ...]", cast("object", [digest])), (), ()
        )
    with pytest.raises(SemanticPlacementError, match="exact SHA-256 bytes"):
        _ = SemanticLocator((b"short",), (), ())
    locator = SemanticLocator((digest,), (), ())
    with pytest.raises(SemanticPlacementError, match="exact locator"):
        _ = SemanticEdit(cast("SemanticLocator", object()), b"x", (digest,))
    with pytest.raises(SemanticPlacementError, match="exact bytes"):
        _ = SemanticEdit(
            locator, cast("bytes", cast("object", bytearray(b"x"))), (digest,)
        )
    with pytest.raises(SemanticPlacementError, match="immutable tuple"):
        _ = SemanticEdit(
            locator,
            b"x",
            cast("tuple[bytes, ...]", cast("object", [digest])),
        )
    edit = SemanticEdit(locator, b"x", (digest,))
    with pytest.raises(SemanticPlacementError, match="immutable tuple"):
        _ = SemanticAuthoringPlan(
            cast("tuple[SemanticEdit, ...]", cast("object", [edit]))
        )
    with pytest.raises(SemanticPlacementError, match="foreign edit"):
        _ = SemanticAuthoringPlan((cast("SemanticEdit", object()),))


def test_semantic_digest_records_reject_late_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late any replacement cannot admit invalid digest sizes or edit types."""
    source_digest = b"a" * 32
    locator = SemanticLocator((source_digest,), (), ())
    attempts = (
        lambda: SemanticLocator((b"short",), (), ()),
        lambda: SemanticEdit(locator, b"new", (b"short",)),
        lambda: SemanticAuthoringPlan(
            (
                cast(
                    "SemanticEdit",
                    cast(
                        "object",
                        SimpleNamespace(locator=locator, replacement=b"new"),
                    ),
                ),
            )
        ),
    )
    rejected: list[bool] = []
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: type(values) is tuple)
        for attempt in attempts:
            try:
                _ = attempt()
            except SemanticPlacementError:
                rejected.append(True)
            else:
                rejected.append(False)
    assert rejected == [True, True, True], (
        "late any hook admitted foreign evidence"
    )


def test_semantic_locator_rejects_late_any_empty_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late any replacement cannot forge a nonempty locator."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: type(values) is tuple)
        try:
            _ = SemanticLocator((), (), ())
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late any hook admitted an empty source locator"


def test_semantic_placement_rejects_late_sorted_edit_drop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An untrusted sorter cannot omit duplicate edits before overlap checks."""
    source = _map(b"a ; b")
    target = _map(b"a ; x ; b")
    plan = build_semantic_plan(source, target, context_units=2)
    assert len(plan.edits) == 1
    duplicate = SemanticAuthoringPlan((plan.edits[0], plan.edits[0]))
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(
            builtins, "sorted", lambda values, *, key=None: list(values)[:1]
        )
        try:
            _ = apply_semantic_plan(source, duplicate, _map)
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late sorted hook discarded a duplicate edit"



@pytest.mark.parametrize(
    ("hook", "result", "candidate_raw"),
    [
        ("max", 9999, b"x ; old ; b"),
        ("min", 0, b"a ; old ; y"),
    ],
)
def test_semantic_locator_context_rejects_late_bounds_override(
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
    result: int,
    candidate_raw: bytes,
) -> None:
    """Late bound arithmetic cannot erase authoring-side source context."""
    source = _map(b"a ; old ; b")
    target = _map(b"a ; new ; b")
    candidate = _map(candidate_raw)
    baseline = build_semantic_plan(source, target, context_units=2)
    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(candidate, baseline, _map)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, hook, lambda left, right: result)
        altered = build_semantic_plan(source, target, context_units=2)

    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(candidate, altered, _map)


def test_semantic_public_boundaries_reject_boolean_and_foreign_inputs() -> None:
    """Build/apply validate views, context width, plan, and mapper first."""
    view = _map(b"alpha")
    with pytest.raises(SemanticPlacementError, match="exact MappedView"):
        _ = build_semantic_plan(cast("MappedView", object()), view)
    with pytest.raises(SemanticPlacementError, match="positive integer"):
        _ = build_semantic_plan(view, view, context_units=True)
    empty = SemanticAuthoringPlan(())
    with pytest.raises(SemanticPlacementError, match="exact MappedView"):
        _ = apply_semantic_plan(cast("MappedView", object()), empty, _map)
    with pytest.raises(SemanticPlacementError, match="exact authoring-plan"):
        _ = apply_semantic_plan(
            view, cast("SemanticAuthoringPlan", object()), _map
        )
    with pytest.raises(SemanticPlacementError, match="callable"):
        _ = apply_semantic_plan(
            view,
            empty,
            cast("Callable[[bytes], MappedView]", object()),
        )


@pytest.mark.parametrize("group", ["source", "before", "after"])
def test_semantic_rejects_late_tuple_alias_for_mutable_locator_groups(
    monkeypatch: pytest.MonkeyPatch, group: str
) -> None:
    """A late tuple alias cannot certify mutable source-lineage evidence."""
    digest = b"a" * 32
    mutable = cast("tuple[bytes, ...]", cast("object", [digest]))
    empty = cast("tuple[bytes, ...]", cast("object", []))
    source = mutable if group == "source" else empty
    before = mutable if group == "before" else empty
    after = mutable if group == "after" else empty
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        try:
            _ = SemanticLocator(source, before, after)
        except SemanticPlacementError:
            rejected = True
    assert rejected, f"late tuple alias admitted mutable {group} locator"


@pytest.mark.parametrize("field", ["replacement", "digests", "plan"])
def test_semantic_rejects_late_native_alias_for_mutable_edits(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Late bytes/tuple aliases cannot admit mutable edit or plan payloads."""
    digest = b"a" * 32
    locator = SemanticLocator((digest,), (), ())
    edit = SemanticEdit(locator, b"new", (digest,))
    rejected = False
    with monkeypatch.context() as patch:
        if field == "replacement":
            patch.setattr(builtins, "bytes", bytearray)
        else:
            patch.setattr(builtins, "tuple", list)
        try:
            if field == "replacement":
                _ = SemanticEdit(
                    locator,
                    cast("bytes", cast("object", bytearray(b"new"))),
                    (),
                )
            elif field == "digests":
                _ = SemanticEdit(
                    locator,
                    b"new",
                    cast("tuple[bytes, ...]", cast("object", [digest])),
                )
            else:
                _ = SemanticAuthoringPlan(
                    cast("tuple[SemanticEdit, ...]", cast("object", [edit]))
                )
        except SemanticPlacementError:
            rejected = True
    assert rejected, f"late native alias admitted mutable {field}"


def test_semantic_context_rejects_late_int_alias_for_boolean_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Boolean context width is never admitted as native integer metadata."""
    view = _map(b"alpha old beta")
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = build_semantic_plan(view, view, context_units=True)
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late int alias admitted Boolean context width"


def test_semantic_valid_records_resist_late_type_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real immutable evidence remains valid under late consumer aliases."""
    digest = b"a" * 32
    locator = SemanticLocator((digest,), (), ())
    view = _map(b"alpha")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        patch.setattr(builtins, "bytes", bytearray)
        patch.setattr(builtins, "int", bool)
        assert SemanticLocator((digest,), (), ()) == locator
        edit = SemanticEdit(locator, b"new", (digest,))
        assert SemanticAuthoringPlan((edit,)).edits == (edit,)
        assert build_semantic_plan(view, view).edits == ()


def test_semantic_position_seeds_ignore_late_enumerate_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host iterator hooks cannot erase a duplicated candidate position."""
    digest = b"a" * 32
    candidate = (digest, digest)
    locator = SemanticLocator((digest,), (), ())
    position_seeds = cast(
        "Callable[[tuple[bytes, ...], SemanticLocator], tuple[int, ...]]",
        cast("object", semantic_module.__dict__["_position_seeds"]),
    )
    expected = position_seeds(candidate, locator)
    assert expected == (0, 1)
    calls = 0
    native_enumerate = builtins.enumerate

    def hide_duplicate(values: tuple[bytes, ...]) -> enumerate[bytes]:
        nonlocal calls
        if values is candidate:
            calls += 1
            return native_enumerate(candidate[:1])
        return native_enumerate(values)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "enumerate", hide_duplicate)
        observed = position_seeds(candidate, locator)
    assert observed == expected, (
        "late enumerate removed ambiguous source positions"
    )
    assert calls == 0, "host enumerate hook controlled source-position evidence"


def test_semantic_unique_windows_ignore_late_range_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host range hooks cannot remove canonical anchor windows."""
    data = (b"a", b"b", b"c")
    unique_windows = cast(
        "Callable[..., dict[tuple[bytes, ...], int]]",
        cast("object", semantic_module.__dict__["_unique_windows"]),
    )
    expected = unique_windows(data, 0, 3, width=2)
    assert len(expected) == 2
    calls = 0
    native_range = builtins.range

    def erase_windows(*_args: int) -> range:
        nonlocal calls
        calls += 1
        return native_range(0)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "range", erase_windows)
        observed = unique_windows(data, 0, 3, width=2)
    assert observed == expected, "late range erased canonical matching windows"
    assert calls == 0, "host range hook controlled anchor-window evidence"


def test_semantic_context_rejects_late_bool_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A swapped Boolean constructor cannot forge missing context evidence."""
    source = _map(b"a ; old ; b")
    target = _map(b"a ; new ; b")
    candidate = _map(b"x ; old ; y")
    plan = build_semantic_plan(source, target, context_units=2)
    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(candidate, plan, _map)
    rejected = False

    def always_true(_value: object) -> bool:
        return True

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bool", always_true)
        try:
            _ = apply_semantic_plan(candidate, plan, _map)
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late bool override forged source-context compatibility"


class _ForeignInsertionSet:
    """Hostile set that never retains seen insertion boundaries."""

    def __contains__(self, _value: object) -> bool:
        return False

    def add(self, _value: int) -> None:
        return


def test_semantic_duplicate_insertion_rejects_late_set_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate zero-width edits stay invalid under a changed set factory."""
    source = _map(b"a ; b")
    target = _map(b"a ; x ; b")
    plan = build_semantic_plan(source, target, context_units=2)
    assert len(plan.edits) == 1
    duplicate = SemanticAuthoringPlan((plan.edits[0], plan.edits[0]))
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "set", _ForeignInsertionSet)
        try:
            _ = apply_semantic_plan(source, duplicate, _map)
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late set override admitted duplicate insertion"


def test_semantic_output_rejects_late_reversed_edit_erasure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host reversed cannot silently remove edits from output verification."""
    source = _map(b"a ; old ; b")
    target = _map(b"a ; new ; b")
    plan = build_semantic_plan(source, target)
    expected = apply_semantic_plan(source, plan, _map)
    assert expected == target.raw

    def erase_edits(_value: object) -> tuple[()]:
        return ()

    native_reversed = builtins.reversed
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "reversed", erase_edits)
        try:
            observed = apply_semantic_plan(source, plan, _map)
        finally:
            # MonkeyPatch.undo itself uses reversed; restore before its teardown.
            patch.setattr(builtins, "reversed", native_reversed)
    assert observed == expected, "late reversed skipped authenticated edits"


@pytest.mark.parametrize("foreign", [bytearray(b"replacement"), b"short"])
def test_semantic_late_type_or_len_rejects_foreign_digest_or_bytes(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """Late mutable builtins cannot admit foreign replacement evidence."""
    digest = b"x" * 32
    locator = SemanticLocator((digest,), (), ())
    native_type = type
    native_len = len
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    def forged_len(value: object) -> int:
        return 32 if value is foreign else native_len(cast("Sized", value))

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", forged_len)
        patch.setattr(builtins, "type", forged_type)
        try:
            if isinstance(foreign, bytearray):
                _ = SemanticEdit(
                    locator, cast("bytes", cast("object", foreign)), (digest,)
                )
            else:
                _ = SemanticLocator((cast("bytes", foreign),), (), ())
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late builtin hook admitted foreign semantic data"


def test_semantic_late_type_rejects_foreign_edit_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plan admission must retain exact immutable edit records."""
    foreign = SimpleNamespace(
        locator=None, replacement=b"no", replacement_digests=()
    )
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return SemanticEdit if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            _ = SemanticAuthoringPlan(
                (cast("SemanticEdit", cast("object", foreign)),)
            )
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late type hook admitted foreign semantic edit"


def test_semantic_late_tuple_does_not_erase_mapped_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hostile tuple hooks cannot erase canonical source digest evidence."""
    view = _map(b"alpha")
    observed = None
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", lambda _: ())
        observed = semantic_module._view_digests(view)
    assert len(observed) == len(view.units)


def test_semantic_late_callable_rejects_nonmapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A false callable hook cannot authorize non-functions as mappers."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "callable", lambda _: True)
        try:
            semantic_module._validate_mapper(object())
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late callable hook admitted a foreign mapper"


def test_semantic_late_type_rejects_forged_mapper_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign mapped output cannot masquerade as an admitted view."""
    raw = b"output"
    foreign = SimpleNamespace(raw=raw, units=())
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return MappedView if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            semantic_module._map_semantic_output(
                cast(
                    "Callable[[bytes], MappedView]",
                    cast("object", lambda _: foreign),
                ),
                raw,
            )
        except SemanticPlacementError:
            rejected = True
    assert rejected, "late type hook admitted foreign mapped evidence"


@pytest.mark.parametrize("hook", ["unit", "view"])
def test_semantic_candidate_locator_ignores_late_record_getter(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A forged canonical mapping cannot turn unrelated source into a match."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate = _map(b"alpha = bad ; omega")
    plan = build_semantic_plan(source, target)
    target_unit = candidate.units[2]
    original_unit = MappedUnit.__getattribute__
    original_view = MappedView.__getattribute__
    calls = 0

    def unit_getter(value: MappedUnit, name: str) -> object:
        nonlocal calls
        if value is target_unit and name == "canonical":
            calls += 1
            return b"old"
        return cast("object", original_unit(value, name))

    def view_getter(value: MappedView, name: str) -> object:
        nonlocal calls
        if value is candidate and name == "units":
            calls += 1
            return source.units
        return cast("object", original_view(value, name))

    with monkeypatch.context() as patched:
        if hook == "unit":
            patched.setattr(MappedUnit, "__getattribute__", unit_getter)
        else:
            patched.setattr(MappedView, "__getattribute__", view_getter)
        with pytest.raises(
            SemanticPlacementError, match="missing or ambiguous"
        ):
            _ = apply_semantic_plan(candidate, plan, _map)
    assert calls == 0, "late class getter forged a matching source locator"


@pytest.mark.parametrize("field", ["raw_start", "raw_end"])
def test_semantic_placement_ignores_late_unit_span_getter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Canonical matches must be replaced at their original raw positions."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target)
    candidate = _map(b"alpha = old ; omega")
    edited_unit = candidate.units[2]
    original = MappedUnit.__getattribute__
    calls = 0

    def getter(value: MappedUnit, name: str) -> object:
        nonlocal calls
        if value is edited_unit and name == field:
            calls += 1
            return 0 if field == "raw_start" else len(candidate.raw)
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(MappedUnit, "__getattribute__", getter)
        result = apply_semantic_plan(candidate, plan, _map)
    assert result == b"alpha = new ; omega"
    assert calls == 0, "late span hook redirected semantic replacement"


def test_semantic_mapper_output_comparison_ignores_late_raw_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mapper cannot certify the wrong output bytes with a class getter."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target)
    forged = MappedView(raw=b"alpha = bad ; omega", units=target.units)
    original = MappedView.__getattribute__
    calls = 0

    def getter(value: MappedView, name: str) -> object:
        nonlocal calls
        if value is forged and name == "raw":
            calls += 1
            return b"alpha = new ; omega"
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(MappedView, "__getattribute__", getter)
        with pytest.raises(SemanticPlacementError, match="actual output bytes"):
            _ = apply_semantic_plan(source, plan, lambda _: forged)
    assert calls == 0, "late raw getter certified a foreign mapper response"


@pytest.mark.parametrize(
    "field", ["source_digests", "before_digests", "after_digests"]
)
def test_semantic_locator_constructor_ignores_late_getter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A class hook cannot hide mutable digest evidence at admission."""
    valid = (b"a" * 32,)
    values: dict[str, object] = {
        "source_digests": valid,
        "before_digests": (),
        "after_digests": (),
    }
    values[field] = [b"a" * 32]
    original = SemanticLocator.__getattribute__
    calls = 0

    def getter(value: SemanticLocator, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return valid
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(SemanticLocator, "__getattribute__", getter)
        constructor = cast("Callable[..., SemanticLocator]", SemanticLocator)
        with pytest.raises(SemanticPlacementError, match="immutable tuples"):
            _ = constructor(**values)
    assert calls == 0, "mutable locator metadata was concealed by a getter"


@pytest.mark.parametrize(
    "field", ["locator", "replacement", "replacement_digests"]
)
def test_semantic_edit_constructor_ignores_late_getter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A class hook cannot hide mutable replacement evidence."""
    locator = SemanticLocator((b"a" * 32,), (), ())
    valid: dict[str, object] = {
        "locator": locator,
        "replacement": b"new",
        "replacement_digests": (b"b" * 32,),
    }
    invalid: dict[str, object] = {
        "locator": object(),
        "replacement": bytearray(b"new"),
        "replacement_digests": [b"b" * 32],
    }
    values = valid | {field: invalid[field]}
    original = SemanticEdit.__getattribute__
    calls = 0

    def getter(value: SemanticEdit, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return valid[field]
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(SemanticEdit, "__getattribute__", getter)
        constructor = cast("Callable[..., SemanticEdit]", SemanticEdit)
        with pytest.raises(SemanticPlacementError):
            _ = constructor(**values)
    assert calls == 0, "mutable edit metadata was concealed by a getter"


def test_semantic_plan_constructor_ignores_late_edits_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late getters cannot turn a mutable edit list into a sealed plan."""
    original = SemanticAuthoringPlan.__getattribute__
    calls = 0

    def getter(value: SemanticAuthoringPlan, name: str) -> object:
        nonlocal calls
        if name == "edits":
            calls += 1
            return ()
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(SemanticAuthoringPlan, "__getattribute__", getter)
        constructor = cast(
            "Callable[..., SemanticAuthoringPlan]", SemanticAuthoringPlan
        )
        with pytest.raises(SemanticPlacementError, match="immutable tuple"):
            _ = constructor(edits=[])
    assert calls == 0, "mutable plan metadata was concealed by a getter"


@pytest.mark.parametrize("field", ["locator", "source_digests"])
def test_semantic_locator_rejects_late_source_evidence_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Class hooks must not authenticate a candidate with different units."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate = _map(b"alpha = bad ; omega")
    plan = build_semantic_plan(source, target)
    false_plan = build_semantic_plan(candidate, target)
    asserted = plan.edits[0]
    original_edit = SemanticEdit.__getattribute__
    original_locator = SemanticLocator.__getattribute__
    calls = 0

    def edit_getter(value: SemanticEdit, name: str) -> object:
        nonlocal calls
        if value is asserted and name == "locator":
            calls += 1
            return false_plan.edits[0].locator
        return cast("object", original_edit(value, name))

    def locator_getter(value: SemanticLocator, name: str) -> object:
        nonlocal calls
        if value is asserted.locator and name == "source_digests":
            calls += 1
            return false_plan.edits[0].locator.source_digests
        return cast("object", original_locator(value, name))

    with monkeypatch.context() as patched:
        if field == "locator":
            patched.setattr(SemanticEdit, "__getattribute__", edit_getter)
        else:
            patched.setattr(SemanticLocator, "__getattribute__", locator_getter)
        with pytest.raises(
            SemanticPlacementError, match="missing or ambiguous"
        ):
            _ = apply_semantic_plan(candidate, plan, _map)
    assert calls == 0, "late locator getter forged source authorization"


@pytest.mark.parametrize("field", ["replacement", "replacement_digests"])
def test_semantic_edit_ignores_late_payload_getter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Accepted semantic output follows the sealed edit's original payload."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target)
    original = SemanticEdit.__getattribute__
    calls = 0

    def getter(value: SemanticEdit, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return b"bad" if field == "replacement" else (b"0" * 32,)
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(SemanticEdit, "__getattribute__", getter)
        output = apply_semantic_plan(source, plan, _map)
    assert output == target.raw
    assert calls == 0, "late edit getter changed canonical replacement evidence"


def test_semantic_plan_ignores_late_empty_edits_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late class getter cannot silently skip an authenticated edit plan."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target)
    assert plan.edits
    original = SemanticAuthoringPlan.__getattribute__
    calls = 0

    def getter(value: SemanticAuthoringPlan, name: str) -> object:
        nonlocal calls
        if name == "edits":
            calls += 1
            return ()
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(SemanticAuthoringPlan, "__getattribute__", getter)
        output = apply_semantic_plan(source, plan, _map)
    assert output == target.raw
    assert calls == 0, "late plan getter dropped accepted semantic edits"


@pytest.mark.parametrize("kind", ["locator", "edit", "plan"])
def test_semantic_constructors_ignore_late_postinit_override(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A late validation-method override cannot admit malformed plans."""
    locator = SemanticLocator((b"a" * 32,), (), ())
    edit = SemanticEdit(locator, b"new", (b"b" * 32,))
    calls = 0

    if kind == "locator":
        record_type = SemanticLocator
        invalid: dict[str, object] = {
            "source_digests": [b"a" * 32],
            "before_digests": (),
            "after_digests": (),
        }
    elif kind == "edit":
        record_type = SemanticEdit
        invalid = {
            "locator": locator,
            "replacement": bytearray(b"new"),
            "replacement_digests": (b"b" * 32,),
        }
    else:
        record_type = SemanticAuthoringPlan
        invalid = {"edits": [edit]}

    def skip_validation(_value: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(record_type, "__post_init__", skip_validation)
        constructor = cast("Callable[..., object]", record_type)
        with pytest.raises(SemanticPlacementError):
            _ = constructor(**invalid)
    assert calls == 0, "late semantic validator admitted invalid evidence"
