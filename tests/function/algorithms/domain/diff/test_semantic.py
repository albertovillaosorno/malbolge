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
