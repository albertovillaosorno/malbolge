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
#   - Tests for tree-level structural and distributed-anchor admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for tree-level structural and distributed-anchor admission."""

import builtins
import hashlib
import math
import ntpath
import os
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import PurePosixPath
from types import MemberDescriptorType
from typing import cast

import pytest
from algorithms.diff.admission import (
    AdmissionError,
    AdmissionPolicy,
    AdmissionPolicyError,
    FileAdmissionEvidence,
    IdentityFile,
    IdentityTree,
    TreeAdmissionEvidence,
    evaluate_admission,
    identity_tree,
    require_admission,
)
from algorithms.diff.fingerprints import (
    AnchorCoverage,
    AnchorPolicy,
    StableAnchor,
)

_FILE_COUNT = 4
_BLOCKS_PER_FILE = 128
_INSERTION = b"compatible insertion"
_MINIMUM_ANCHOR_FILES = 3
_MINIMUM_ANCHORS_PER_FILE = 2
_DISTRIBUTION_REASON = "stable-anchor evidence is not sufficiently distributed"
_STRUCTURAL_REASON = "insufficient structural source similarity"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _content(label: str, file_index: int) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{file_index}:{block}".encode()).digest()
        for block in range(_BLOCKS_PER_FILE)
    )


def _reference_files() -> dict[str, bytes]:
    return {
        f"src/file-{index}.txt": _content("reference", index)
        for index in range(_FILE_COUNT)
    }


def _policy(
    *,
    source_similarity: float = 0.50,
    anchor_coverage: float = 0.66,
) -> AdmissionPolicy:
    return AdmissionPolicy(
        minimum_source_similarity=source_similarity,
        minimum_anchor_coverage=anchor_coverage,
        minimum_anchor_files=_MINIMUM_ANCHOR_FILES,
        minimum_anchors_per_file=_MINIMUM_ANCHORS_PER_FILE,
    )


def _candidate_with_first_insertion() -> tuple[IdentityTree, IdentityTree]:
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    first_path = min(candidate_files)
    content = candidate_files[first_path]
    midpoint = len(content) // 2
    candidate_files[first_path] = (
        content[:midpoint] + _INSERTION + content[midpoint:]
    )
    return identity_tree(reference_files), identity_tree(candidate_files)


def test_admission_rejects_post_import_math_fsum_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late global summation hook cannot forge source-lineage admission."""
    file = FileAdmissionEvidence("source.c", 0.0, 1.0, 1, 1)
    policy = AdmissionPolicy(
        minimum_source_similarity=0.75,
        minimum_anchor_coverage=0.5,
        minimum_anchor_files=1,
        minimum_anchors_per_file=1,
    )
    native_fsum = math.fsum
    calls = 0

    def forged_fsum(values: object) -> float:
        nonlocal calls
        values_tuple = tuple(cast("tuple[float, ...]", values))
        if values_tuple == (0.0,):
            calls += 1
            return 1.0
        return native_fsum(values_tuple)

    with monkeypatch.context() as patched:
        patched.setattr(math, "fsum", forged_fsum)
        with pytest.raises(
            AdmissionPolicyError, match="source similarity does not match"
        ):
            _ = TreeAdmissionEvidence(
                source_similarity=1.0,
                anchor_coverage=1.0,
                eligible_anchor_files=1,
                satisfied_anchor_files=1,
                files=(file,),
                reasons=(),
                policy=policy,
            )
    assert calls == 0


def test_admission_rejects_post_import_math_isfinite_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late finite-value hook cannot admit invalid lineage evidence."""
    calls = 0

    def forged_finite(value: float) -> bool:
        nonlocal calls
        del value
        calls += 1
        return True

    with monkeypatch.context() as patched:
        patched.setattr(math, "isfinite", forged_finite)
        with pytest.raises(AdmissionPolicyError, match="finite exact float"):
            _ = FileAdmissionEvidence("source.c", float("nan"), None, 0, 0)
    assert calls == 0


def test_admission_evidence_rejects_incoherent_direct_construction() -> None:
    """Per-file and aggregate evidence cannot contradict their local counts."""
    with pytest.raises(AdmissionPolicyError, match="cannot exceed reference"):
        _ = FileAdmissionEvidence("a.c", 1.0, 1.0, 1, 2)

    file = FileAdmissionEvidence("a.c", 1.0, 1.0, 1, 1)
    with pytest.raises(AdmissionPolicyError, match="source similarity"):
        _ = TreeAdmissionEvidence(0.5, 1.0, 1, 1, (file,), (), _policy())
    with pytest.raises(
        AdmissionPolicyError, match="eligible anchor file count"
    ):
        _ = TreeAdmissionEvidence(1.0, 1.0, 0, 0, (file,), (), _policy())

    unmatched = FileAdmissionEvidence("a.c", 1.0, 0.0, 1, 0)
    with pytest.raises(
        AdmissionPolicyError, match="satisfied anchor file count"
    ):
        _ = TreeAdmissionEvidence(1.0, 0.0, 1, 1, (unmatched,), (), _policy())


def test_direct_admission_evidence_cannot_erase_policy_failures() -> None:
    """Direct evidence must not turn a rejected source into an admitted one."""
    reference = identity_tree(_reference_files())
    rejected = evaluate_admission(reference, identity_tree({}), _policy())
    assert not rejected.admitted
    with pytest.raises(AdmissionPolicyError, match="reasons do not match"):
        _ = replace(rejected, reasons=())


def test_tree_evidence_rejects_late_reason_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class attribute hooks cannot authorize erased source policy failures."""
    reference = identity_tree(_reference_files())
    rejected = evaluate_admission(reference, identity_tree({}), _policy())
    original_reasons = rejected.reasons
    calls = 0

    def forged_attribute(value: object, name: str) -> object:
        nonlocal calls
        if name == "reasons":
            calls += 1
            return original_reasons
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(
            TreeAdmissionEvidence, "__getattribute__", forged_attribute
        )
        with pytest.raises(AdmissionPolicyError, match="reasons do not match"):
            _ = replace(rejected, reasons=())
    assert calls == 0, "late reason getter participated in admission"


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_tree_evidence_admitted_ignores_late_reason_hook(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A completed rejected source receipt cannot be promoted by a hook."""
    reference = identity_tree(_reference_files())
    rejected = evaluate_admission(reference, identity_tree({}), _policy())
    assert not rejected.admitted

    def forged_attribute(value: object, name: str) -> object:
        if name == "reasons":
            return ()
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(
                TreeAdmissionEvidence, "reasons", property(lambda _: ())
            )
        else:
            patched.setattr(
            TreeAdmissionEvidence, "__getattribute__", forged_attribute
        )
        assert not rejected.admitted


def test_direct_admission_evidence_cannot_forge_distribution_count() -> None:
    """The accepted anchor-file count must come from policy and file scores."""
    reference = identity_tree(_reference_files())
    admitted = evaluate_admission(reference, reference, _policy())
    assert admitted.satisfied_anchor_files == _FILE_COUNT
    with pytest.raises(
        AdmissionPolicyError, match="satisfied anchor file count"
    ):
        _ = replace(admitted, satisfied_anchor_files=_FILE_COUNT - 1)


def test_direct_admission_evidence_rejects_policy_swap() -> None:
    """Reported decisions cannot inherit a different threshold policy."""
    reference = identity_tree(_reference_files())
    rejected = evaluate_admission(reference, identity_tree({}), _policy())
    with pytest.raises(AdmissionPolicyError, match="reasons do not match"):
        _ = replace(rejected, policy=_policy(source_similarity=0.0))


def test_direct_admission_evidence_binds_anchor_eligibility() -> None:
    """Only files eligible under policy may report a coverage score."""
    reference = identity_tree(_reference_files())
    evidence = evaluate_admission(reference, reference, _policy())
    with pytest.raises(AdmissionPolicyError, match="eligibility"):
        _ = replace(
            evidence,
            policy=replace(evidence.policy, minimum_anchors_per_file=10**9),
        )


def test_direct_admission_evidence_requires_exact_policy() -> None:
    """Foreign policy objects cannot impersonate a source-lineage decision."""
    reference = identity_tree(_reference_files())
    evidence = evaluate_admission(reference, reference, _policy())
    with pytest.raises(AdmissionPolicyError, match="exact AdmissionPolicy"):
        _ = replace(evidence, policy=cast("AdmissionPolicy", object()))



@pytest.mark.parametrize("invalid_order", ["unsorted", "duplicate"])
def test_identity_tree_ignores_late_sort_and_set_hooks(
    monkeypatch: pytest.MonkeyPatch,
    invalid_order: str,
) -> None:
    """A late hook cannot admit unordered or duplicated source identities."""
    reference = identity_tree({"first.c": b"first", "second.c": b"second"})
    first, second = reference.files
    records = (
        (second, first) if invalid_order == "unsorted" else (first, first)
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", lambda values: list(values))
        patch.setattr(builtins, "set", lambda values: list(values))
        try:
            _ = IdentityTree(files=records)
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "late hooks admitted malformed source identity records"



@pytest.mark.parametrize(
    ("unsafe_path", "hook", "forged_verdict"),
    [
        ("src/\x00file.c", "any", False),
        ("src/../file.c", "all", True),
    ],
)
def test_identity_path_rejects_late_truth_hooks(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
    hook: str,
    forged_verdict: bool,
) -> None:
    """Replacing built-in predicates cannot admit unsafe source labels."""
    identity_rejected = False
    evidence_rejected = False
    def forged_predicate(values: object) -> bool:
        del values
        return forged_verdict

    with monkeypatch.context() as patched:
        patched.setattr(builtins, hook, forged_predicate)
        try:
            _ = IdentityFile(unsafe_path, b"source")
        except AdmissionPolicyError:
            identity_rejected = True
        try:
            _ = FileAdmissionEvidence(unsafe_path, 1.0, 1.0, 1, 1)
        except AdmissionPolicyError:
            evidence_rejected = True
    assert identity_rejected, "late predicate admitted unsafe identity path"
    assert evidence_rejected, "late predicate admitted unsafe evidence path"


def test_identity_file_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign mutable byte buffer cannot pass an exact bytes admission."""
    foreign = bytearray(b"source")
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = IdentityFile("source.c", cast("bytes", cast("object", foreign)))
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "late type hook admitted mutable source bytes"


def test_identity_tree_rejects_late_any_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign identity record cannot be smuggled through tree admission."""

    class ForeignRecord:
        path: str = "source.c"
        canonical: bytes = b"source"

    def forged_any(values: Iterable[object]) -> bool:
        del values
        return False

    foreign = cast("IdentityFile", cast("object", ForeignRecord()))
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", forged_any)
        try:
            _ = IdentityTree(files=(foreign,))
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "late any hook admitted a foreign identity record"


def test_tree_evidence_rejects_late_len_score_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing tuple lengths cannot inflate structural source evidence."""
    first = FileAdmissionEvidence("a.c", 0.0, 0.0, 1, 0)
    second = FileAdmissionEvidence("b.c", 1.0, 1.0, 1, 1)
    policy = AdmissionPolicy(0.75, 0.75, 1, 1)
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if isinstance(value, tuple) and value == (0.0, 1.0):
            return 1
        return native_len(cast("tuple[object, ...]", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = TreeAdmissionEvidence(
                1.0, 1.0, 1, 1, (first, second), (), policy
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "late len hook inflated lineage evidence"


def test_structural_similarity_ignores_late_frozenset_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source digests cannot be replaced by one invented shared digest."""
    reference = identity_tree({"source.c": b"A" * 512})
    candidate = identity_tree({"source.c": b"B" * 512})
    policy = AdmissionPolicy(0.9, 0.0, 1, 1)
    native_frozenset = frozenset

    def forged_frozenset(values: object) -> frozenset[bytes]:
        del values
        return native_frozenset({b"forged"})

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "frozenset", forged_frozenset)
        evidence = evaluate_admission(reference, candidate, policy)
    assert evidence.source_similarity == 0.0
    assert not evidence.admitted


def test_identity_tree_builder_ignores_late_sort_and_set_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The identity-tree constructor preserves native path sorting."""
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", lambda values: list(values))
        patch.setattr(builtins, "set", lambda values: list(values))
        identity = identity_tree({"z.c": b"z", "a.c": b"a"})
    assert tuple(item.path for item in identity.files) == ("a.c", "z.c")


def test_tree_evidence_ignores_late_sort_and_set_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unordered evidence cannot pass under mutated process-wide hooks."""
    policy = AdmissionPolicy(
        minimum_source_similarity=0.0,
        minimum_anchor_coverage=0.5,
        minimum_anchor_files=1,
        minimum_anchors_per_file=1,
    )
    first = FileAdmissionEvidence("a.c", 1.0, 1.0, 1, 1)
    second = FileAdmissionEvidence("z.c", 1.0, 1.0, 1, 1)
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", lambda values: list(values))
        patch.setattr(builtins, "set", lambda values: list(values))
        try:
            _ = TreeAdmissionEvidence(
                source_similarity=1.0,
                anchor_coverage=1.0,
                eligible_anchor_files=2,
                satisfied_anchor_files=2,
                files=(second, first),
                reasons=(),
                policy=policy,
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "late hooks admitted unordered file evidence"


def test_identity_tree_rejects_file_ancestor_overlap() -> None:
    """File identities cannot also act as containing directories."""
    ancestor = IdentityFile(path="src/file", canonical=b"A")
    child = IdentityFile(path="src/file/child", canonical=b"B")
    with pytest.raises(AdmissionPolicyError, match="ancestor"):
        _ = IdentityTree(files=(ancestor, child))
    with pytest.raises(AdmissionPolicyError, match="ancestor"):
        _ = identity_tree({
            ancestor.path: ancestor.canonical,
            child.path: child.canonical,
        })

    ancestor_evidence = FileAdmissionEvidence(ancestor.path, 1.0, 1.0, 1, 1)
    child_evidence = FileAdmissionEvidence(child.path, 1.0, 1.0, 1, 1)
    with pytest.raises(AdmissionPolicyError, match="ancestor"):
        _ = TreeAdmissionEvidence(
            1.0, 1.0, 2, 2, (ancestor_evidence, child_evidence), (), _policy()
        )


def test_exact_identity_tree_is_admitted() -> None:
    """Exact source lineage satisfies both independent source metrics."""
    files = _reference_files()
    evidence = require_admission(
        identity_tree(files), identity_tree(files), _policy()
    )
    _expect(
        math.isclose(evidence.source_similarity, 1.0),
        "exact structural score changed",
    )
    _expect(
        math.isclose(evidence.anchor_coverage, 1.0),
        "exact anchor score changed",
    )
    _expect(
        evidence.satisfied_anchor_files == _FILE_COUNT,
        "files not distributed",
    )


def test_compatible_insertions_preserve_distributed_evidence() -> None:
    """Keep distributed evidence across offset-shifting insertions."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    for path, content in tuple(candidate_files.items()):
        midpoint = len(content) // 2
        candidate_files[path] = (
            content[:midpoint] + _INSERTION + content[midpoint:]
        )
    evidence = require_admission(
        identity_tree(reference_files),
        identity_tree(candidate_files),
        _policy(),
    )
    _expect(evidence.source_similarity < 1.0, "insertion looked byte-exact")
    _expect(evidence.anchor_coverage < 1.0, "insertion kept every anchor")
    _expect(evidence.admitted, "compatible insertion was rejected")


def test_missing_empty_identity_file_is_not_a_structural_match() -> None:
    """An absent selected path is not equivalent to a present empty file."""
    reference_files = {"empty.c": b"", "populated.c": _content("source", 0)}
    reference = identity_tree(reference_files)
    policy = AdmissionPolicy(
        minimum_source_similarity=0.75,
        minimum_anchor_coverage=0.0,
        minimum_anchor_files=1,
        minimum_anchors_per_file=1,
    )
    complete = evaluate_admission(reference, reference, policy)
    absent = evaluate_admission(
        reference,
        identity_tree({"populated.c": reference_files["populated.c"]}),
        policy,
    )
    assert complete.admitted
    _expect(math.isclose(complete.source_similarity, 1.0), "complete score")
    _expect(not absent.admitted, "missing path was accepted")
    _expect(math.isclose(absent.source_similarity, 0.5), "missing path score")
    _expect(absent.files[0].path == reference.files[0].path, "wrong path")
    _expect(
        math.isclose(absent.files[0].structural_similarity, 0.0),
        "missing path received structural credit",
    )
    _expect(_STRUCTURAL_REASON in absent.reasons, "missing rejection reason")


def test_unrelated_source_fails_closed() -> None:
    """Same paths and sizes cannot replace structural source lineage."""
    reference = identity_tree(_reference_files())
    unrelated = identity_tree({
        f"src/file-{index}.txt": _content("unrelated", index)
        for index in range(_FILE_COUNT)
    })
    with pytest.raises(AdmissionError, match="structural source similarity"):
        _ = require_admission(reference, unrelated, _policy())


def test_require_admission_ignores_late_admitted_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a public descriptor cannot approve rejected source lineage."""
    reference = identity_tree(_reference_files())
    unrelated = identity_tree({
        f"src/file-{index}.txt": _content("unrelated", index)
        for index in range(_FILE_COUNT)
    })
    with monkeypatch.context() as patch:
        patch.setattr(
            TreeAdmissionEvidence, "admitted", property(lambda evidence: True)
        )
        with pytest.raises(AdmissionError, match="structural source similarity"):
            _ = require_admission(reference, unrelated, _policy())


def test_admission_distribution_ignores_late_sum_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late sum override cannot forge enough satisfied source files."""
    files = _reference_files()
    candidate = dict(files)
    candidate["src/file-0.txt"] = _content("unrelated", 0)
    reference = identity_tree(files)
    changed = identity_tree(candidate)
    policy = AdmissionPolicy(
        minimum_source_similarity=0.0,
        minimum_anchor_coverage=0.50,
        minimum_anchor_files=_FILE_COUNT,
        minimum_anchors_per_file=1,
    )
    baseline = evaluate_admission(reference, changed, policy)
    assert baseline.eligible_anchor_files == _FILE_COUNT
    assert baseline.satisfied_anchor_files == _FILE_COUNT - 1
    assert _DISTRIBUTION_REASON in baseline.reasons

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sum", lambda values: _FILE_COUNT)
        with pytest.raises(AdmissionError, match="sufficiently distributed"):
            _ = require_admission(reference, changed, policy)


def test_structural_threshold_boundary_is_fail_closed() -> None:
    """Reject the next representable threshold above measured similarity."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    candidate_files[min(candidate_files)] = _content("different", 0)
    reference = identity_tree(reference_files)
    candidate = identity_tree(candidate_files)
    baseline = evaluate_admission(
        reference, candidate, _policy(source_similarity=0.0)
    )
    below = math.nextafter(baseline.source_similarity, 0.0)
    above = math.nextafter(baseline.source_similarity, 1.0)
    passing = evaluate_admission(
        reference, candidate, _policy(source_similarity=below)
    )
    failing = evaluate_admission(
        reference, candidate, _policy(source_similarity=above)
    )
    _expect(passing.admitted, "threshold immediately below score rejected")
    _expect(not failing.admitted, "threshold immediately above score admitted")


def test_anchor_threshold_boundary_is_fail_closed() -> None:
    """Change acceptance exactly across the measured anchor boundary."""
    reference, candidate = _candidate_with_first_insertion()
    baseline = evaluate_admission(
        reference,
        candidate,
        _policy(anchor_coverage=0.0),
    )
    below = math.nextafter(baseline.anchor_coverage, 0.0)
    above = math.nextafter(baseline.anchor_coverage, 1.0)
    passing = evaluate_admission(
        reference, candidate, _policy(anchor_coverage=below)
    )
    failing = evaluate_admission(
        reference, candidate, _policy(anchor_coverage=above)
    )
    _expect(passing.admitted, "threshold immediately below coverage rejected")
    _expect(
        not failing.admitted,
        "threshold immediately above coverage admitted",
    )


def test_anchor_distribution_rejects_single_file_concentration() -> None:
    """Reject one strong file as evidence for a multi-file identity."""
    reference_files = _reference_files()
    first_path = min(reference_files)
    candidate_files = {first_path: reference_files[first_path]}
    evidence = evaluate_admission(
        identity_tree(reference_files),
        identity_tree(candidate_files),
        _policy(source_similarity=0.0, anchor_coverage=0.0),
    )
    _expect(not evidence.admitted, "single-file evidence admitted whole tree")
    _expect(
        _DISTRIBUTION_REASON in evidence.reasons,
        "distribution rejection reason is missing",
    )


def test_opaque_asset_size_cannot_dominate_explicit_identity_view() -> None:
    """Ignore candidate-only opaque size in reference-driven aggregation."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    candidate_files[min(candidate_files)] = _content("different", 0)
    reference = identity_tree(reference_files)
    policy = _policy(source_similarity=0.0)
    baseline = evaluate_admission(
        reference,
        identity_tree(candidate_files),
        policy,
    )
    candidate_files["data/opaque.bin"] = b"opaque" * 1_000_000
    with_asset = evaluate_admission(
        reference,
        identity_tree(candidate_files),
        policy,
    )
    _expect(
        baseline == with_asset, "candidate-only asset changed source evidence"
    )
    _expect(len(with_asset.files) == _FILE_COUNT, "asset changed identity size")


def test_admission_policy_rejects_boolean_numeric_fields() -> None:
    """Boolean aliases cannot weaken lineage thresholds or evidence counts."""
    with pytest.raises(AdmissionPolicyError, match="finite numeric fraction"):
        _ = AdmissionPolicy(
            minimum_source_similarity=True,
            minimum_anchor_coverage=0.66,
            minimum_anchor_files=3,
            minimum_anchors_per_file=2,
        )
    with pytest.raises(AdmissionPolicyError, match="positive integer"):
        _ = AdmissionPolicy(
            minimum_source_similarity=0.50,
            minimum_anchor_coverage=0.66,
            minimum_anchor_files=True,
            minimum_anchors_per_file=2,
        )


def test_admission_policy_accepts_integral_unit_fractions() -> None:
    """Zero and one remain valid native-integer threshold endpoints."""
    for fraction in (0, 1):
        policy = _policy(
            source_similarity=fraction,
            anchor_coverage=fraction,
        )
        assert policy.minimum_source_similarity == fraction
        assert policy.minimum_anchor_coverage == fraction


def test_admission_policy_rejects_huge_integer_fractions() -> None:
    """Invalid large integers stay inside the typed fraction policy boundary."""
    magnitudes: tuple[int, int] = (10**400, 10**5000)
    for magnitude in magnitudes:
        for invalid in (magnitude, -magnitude):
            with pytest.raises(AdmissionPolicyError, match="finite fraction"):
                _ = _policy(source_similarity=invalid)
            with pytest.raises(AdmissionPolicyError, match="finite fraction"):
                _ = _policy(anchor_coverage=invalid)


def test_identity_records_reject_foreign_runtime_types() -> None:
    """Identity construction accepts canonical strings and bytes only."""
    with pytest.raises(AdmissionPolicyError, match="exact string"):
        _ = IdentityFile(path=cast("str", object()), canonical=b"source")
    with pytest.raises(AdmissionPolicyError, match="exact bytes"):
        _ = IdentityFile(
            path="source.c",
            canonical=cast("bytes", cast("object", bytearray(b"source"))),
        )
    with pytest.raises(AdmissionPolicyError, match="immutable tuple"):
        _ = IdentityTree(
            files=cast("tuple[IdentityFile, ...]", cast("object", []))
        )
    with pytest.raises(AdmissionPolicyError, match="foreign file"):
        _ = IdentityTree(files=(cast("IdentityFile", object()),))
    with pytest.raises(AdmissionPolicyError, match="exact dictionary"):
        _ = identity_tree(cast("dict[str, bytes]", object()))
    with pytest.raises(AdmissionPolicyError, match="exact bytes"):
        _ = identity_tree({
            "source.c": cast("bytes", cast("object", bytearray(b"source")))
        })


def _forged_path_is_absolute(path: PurePosixPath) -> bool:
    del path
    return False


def _forged_path_parts(path: PurePosixPath) -> tuple[str, ...]:
    del path
    return ("src", "safe.c")


def _forged_path_as_posix(path: PurePosixPath) -> str:
    del path
    return "src//unsafe.c"


def _forged_path_parents(path: PurePosixPath) -> tuple[PurePosixPath, ...]:
    del path
    return ()


@pytest.mark.parametrize(
    "case",
    [
        ("/absolute/source.c", "is_absolute", _forged_path_is_absolute),
        ("src/../unsafe.c", "parts", property(_forged_path_parts)),
        ("src//unsafe.c", "as_posix", _forged_path_as_posix),
    ],
)
def test_identity_rejects_post_import_path_method_spoof(
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str, object],
) -> None:
    """Late pathlib method swaps must not approve malformed source labels."""
    unsafe_path, method, replacement = case
    with monkeypatch.context() as patched:
        patched.setattr(PurePosixPath, method, replacement)
        with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
            _ = IdentityFile(path=unsafe_path, canonical=b"source")


def test_identity_rejects_post_import_parent_topology_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable pathlib.parents cannot admit a file as another file's root."""
    file = IdentityFile(path="src", canonical=b"file")
    child = IdentityFile(path="src/file.c", canonical=b"child")
    with monkeypatch.context() as patched:
        patched.setattr(
            PurePosixPath, "parents", property(_forged_path_parents)
        )
        with pytest.raises(AdmissionPolicyError, match="ancestor"):
            _ = IdentityTree(files=(file, child))


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "src/\x00.c",
        "src/\ud800.c",
        "C:/drive.c",
        "C:relative.c",
        "NUL",
        "safe/CON.txt",
        "safe/COM1",
        "safe/name:stream",
        "safe/trailing.",
        "safe/trailing ",
    ],
)
def test_identity_paths_reject_nonportable_names(unsafe_path: str) -> None:
    """Malformed path metadata must fail before source binding and encoding."""
    with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
        _ = IdentityFile(path=unsafe_path, canonical=b"source")
    with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
        _ = identity_tree({unsafe_path: b"source"})
    with pytest.raises(
        AdmissionPolicyError, match="invalid file admission path"
    ):
        _ = FileAdmissionEvidence(unsafe_path, 1.0, 1.0, 1, 1)


@pytest.mark.parametrize(
    "unsafe_path", ["CON", "safe/COM1/child.txt", "NUL/child.txt"]
)
def test_identity_reserved_paths_ignore_mutable_host_hook(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
) -> None:
    """Domain code cannot reclassify Windows device names as portable paths."""

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
        _ = IdentityFile(path=unsafe_path, canonical=b"source")
    with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
        _ = identity_tree({unsafe_path: b"source"})
    with pytest.raises(
        AdmissionPolicyError, match="invalid file admission path"
    ):
        _ = FileAdmissionEvidence(unsafe_path, 1.0, 1.0, 1, 1)


def _forge_admission_any(patched: pytest.MonkeyPatch, invalid: str) -> None:
    del invalid
    native_any = builtins.any

    def forged_any(values: Iterable[object]) -> bool:
        frame = getattr(values, "gi_frame", None)
        globals_map = getattr(frame, "f_globals", {})
        if globals_map is vars(ntpath):
            return False
        return native_any(values)

    patched.setattr(builtins, "any", forged_any)


def _forge_admission_reversed(
    patched: pytest.MonkeyPatch, invalid: str
) -> None:
    native_reversed = builtins.reversed

    def forged_reversed(values: list[str]) -> object:
        if values == [invalid]:
            return ()
        return native_reversed(values)

    patched.setattr(builtins, "reversed", forged_reversed)


def _forge_admission_splitroot(
    patched: pytest.MonkeyPatch, invalid: str
) -> None:
    native_splitroot = ntpath.splitroot

    def forged_splitroot(path: str) -> tuple[str, str, str]:
        if path == invalid:
            return "", "", "safe.c"
        return native_splitroot(path)

    patched.setattr(ntpath, "splitroot", forged_splitroot)


def _forge_admission_fspath(patched: pytest.MonkeyPatch, invalid: str) -> None:
    native_fspath = os.fspath

    def forged_fspath(path: os.PathLike[str] | str) -> str:
        if path == invalid:
            return "safe.c"
        return native_fspath(path)

    patched.setattr(os, "fspath", forged_fspath)


@pytest.mark.parametrize(
    ("forge", "unsafe_path"),
    [
        (_forge_admission_any, "NUL"),
        (_forge_admission_reversed, "NUL"),
        (_forge_admission_splitroot, "src/COM1/child.txt"),
        (_forge_admission_fspath, "C:/escape.c"),
    ],
)
def test_identity_admission_ignores_late_ntpath_dependency_hooks(
    monkeypatch: pytest.MonkeyPatch,
    forge: Callable[[pytest.MonkeyPatch, str], None],
    unsafe_path: str,
) -> None:
    """Mutating ntpath helper internals cannot admit foreign source evidence."""
    constructors = (
        lambda: IdentityFile(path=unsafe_path, canonical=b"source"),
        lambda: identity_tree({unsafe_path: b"source"}),
        lambda: FileAdmissionEvidence(unsafe_path, 1.0, 1.0, 1, 1),
    )
    rejected = []
    with monkeypatch.context() as patched:
        forge(patched, unsafe_path)
        for constructor in constructors:
            try:
                _ = constructor()
            except AdmissionPolicyError:
                rejected.append(True)
    assert len(rejected) == len(constructors), (
        f"mutable host admitted unsafe identity {unsafe_path!r}"
    )


def test_admission_rejects_foreign_tree_and_policy_objects() -> None:
    """Lineage evaluation fails typed before dereferencing foreign objects."""
    reference = identity_tree(_reference_files())
    policy = _policy()
    with pytest.raises(AdmissionPolicyError, match="exact IdentityTree"):
        _ = evaluate_admission(
            cast("IdentityTree", object()),
            reference,
            policy,
        )
    with pytest.raises(AdmissionPolicyError, match="exact IdentityTree"):
        _ = evaluate_admission(
            reference,
            cast("IdentityTree", object()),
            policy,
        )
    with pytest.raises(AdmissionPolicyError, match="exact AdmissionPolicy"):
        _ = evaluate_admission(
            reference,
            reference,
            cast("AdmissionPolicy", object()),
        )


def test_identity_file_rejects_post_import_bytes_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late bytes aliases cannot certify mutable canonical source content."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", bytearray)
        try:
            _ = IdentityFile(
                "file.c",
                cast("bytes", cast("object", bytearray(b"source"))),
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "mutable source content passed a late bytes alias"


def test_identity_file_rejects_post_import_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late string aliases cannot dereference forged non-string paths."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", bytes)
        try:
            _ = IdentityFile(cast("str", cast("object", b"file.c")), b"source")
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "non-string path bypassed the exact string guard"


def test_identity_tree_rejects_post_import_tuple_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late tuple aliases cannot certify mutable identity collections."""
    entries = [IdentityFile("file.c", b"source")]
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", list)
        try:
            _ = IdentityTree(
                cast("tuple[IdentityFile, ...]", cast("object", entries))
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "mutable identity collection passed a late tuple alias"


def test_admission_policy_rejects_post_import_integer_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late int aliases cannot certify Boolean counts or thresholds."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        try:
            _ = AdmissionPolicy(
                minimum_source_similarity=0.5,
                minimum_anchor_coverage=0.6,
                minimum_anchor_files=True,
                minimum_anchors_per_file=True,
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "Boolean minimum file count bypassed native int check"

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        try:
            _ = AdmissionPolicy(
                minimum_source_similarity=True,
                minimum_anchor_coverage=0.6,
                minimum_anchor_files=True,
                minimum_anchors_per_file=True,
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "Boolean source threshold bypassed native fraction check"


def test_admission_evidence_rejects_post_import_float_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late float aliases cannot certify Boolean similarity scores."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "float", bool)
        try:
            _ = FileAdmissionEvidence(
                path="file.c",
                structural_similarity=True,
                anchor_coverage=None,
                reference_anchor_count=0,
                matched_anchor_count=0,
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "Boolean source score passed late float alias"


def test_admission_evidence_rejects_post_import_integer_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late int aliases cannot certify Boolean reference anchor counts."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        try:
            _ = FileAdmissionEvidence(
                path="file.c",
                structural_similarity=1.0,
                anchor_coverage=1.0,
                reference_anchor_count=True,
                matched_anchor_count=True,
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "Boolean anchor counts passed late int alias"


def test_identity_factory_rejects_post_import_dictionary_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late dict aliases cannot certify mutable non-mapping inputs."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "dict", list)
        try:
            _ = identity_tree(cast("dict[str, bytes]", cast("object", [])))
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "foreign mapping passed late dict alias"


def test_valid_admission_records_resist_late_builtin_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual native evidence survives aliases of public builtin names."""
    file = IdentityFile("file.c", b"source")
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", list)
        result = identity_tree({"file.c": b"source"})
        actual = IdentityTree((file,))
    assert type(result.files) is tuple
    assert result == actual

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "dict", list)
        result = identity_tree({"file.c": b"source"})
    assert result == IdentityTree((file,))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        policy = AdmissionPolicy(0, 1, 1, 1)
        score = FileAdmissionEvidence("file.c", 1.0, None, 0, 0)
    assert policy.minimum_source_similarity == 0
    assert score.reference_anchor_count == 0

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "float", bool)
        score = FileAdmissionEvidence("file.c", 1.0, None, 0, 0)
    assert math.isclose(score.structural_similarity, 1.0)


def test_tree_evidence_rejects_post_import_mutable_collections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late tuple aliases cannot replace immutable admission evidence lists."""
    reference = identity_tree({"file.c": b"source"})
    evidence = evaluate_admission(
        reference,
        reference,
        AdmissionPolicy(0, 0, 1, 1),
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", list)
        try:
            _ = replace(
                evidence,
                files=cast(
                    "tuple[FileAdmissionEvidence, ...]",
                    cast("object", list(evidence.files)),
                ),
                reasons=cast(
                    "tuple[str, ...]", cast("object", list(evidence.reasons))
                ),
            )
        except AdmissionPolicyError:
            rejected = True
    assert rejected, "mutable file and rejection evidence passed a late alias"


def test_structural_admission_ignores_late_anchor_digest_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late anchor getters cannot forge structural similarity of sources."""
    reference = identity_tree({"main.c": _content("reference", 0)})
    candidate = identity_tree({"main.c": _content("unrelated", 0)})
    policy = _policy(source_similarity=0.8)
    expected = evaluate_admission(reference, candidate, policy)
    assert expected.source_similarity < 0.8
    original = StableAnchor.__getattribute__
    calls = 0

    def forged_attribute(value: StableAnchor, name: str) -> object:
        nonlocal calls
        if name == "digest":
            calls += 1
            return b"z" * 32
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(StableAnchor, "__getattribute__", forged_attribute)
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "mutable digest reader forged structural evidence"


def test_file_admission_ignores_late_coverage_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File lineage counts must use raw cryptographic overlap metadata."""
    reference = identity_tree({"main.c": _content("reference", 0)})
    candidate = identity_tree({"main.c": _content("unrelated", 0)})
    policy = _policy(source_similarity=0.0)
    expected = evaluate_admission(reference, candidate, policy)
    assert expected.files[0].matched_anchor_count == 0
    original = AnchorCoverage.__getattribute__
    calls = 0
    forged = {"total": 1, "matched": 1, "ratio": 1.0}

    def forged_attribute(value: AnchorCoverage, name: str) -> object:
        nonlocal calls
        if name in forged:
            calls += 1
            return forged[name]
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(AnchorCoverage, "__getattribute__", forged_attribute)
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "mutable coverage reader forged file lineage"


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("minimum_source_similarity", 0.99),
        ("minimum_anchor_coverage", 0.99),
        ("minimum_anchor_files", 4),
        ("minimum_anchors_per_file", 40),
        (
            "structural_policy",
            AnchorPolicy(window_bytes=4, selection_modulus=1),
        ),
        ("anchor_policy", AnchorPolicy(window_bytes=4, selection_modulus=1)),
    ],
)
def test_admission_ignores_late_policy_getter_forgery(
    monkeypatch: pytest.MonkeyPatch, hook: str, field: str, forged: object
) -> None:
    """Class-level hooks cannot revise the source-admission policy in place."""
    reference, candidate = _candidate_with_first_insertion()
    policy = _policy()
    expected = evaluate_admission(reference, candidate, policy)
    original = AdmissionPolicy.__getattribute__
    calls = 0

    def forged_attribute(value: AdmissionPolicy, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(value, name))

    def forged_property(_value: AdmissionPolicy) -> object:
        nonlocal calls
        calls += 1
        return forged

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(AdmissionPolicy, field, property(forged_property))
        else:
            patch.setattr(AdmissionPolicy, "__getattribute__", forged_attribute)
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "mutable policy getter influenced admission"


@pytest.mark.parametrize(
    "field", ["minimum_anchor_files", "minimum_anchors_per_file"]
)
def test_admission_policy_constructor_rejects_late_getter_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Direct policy construction checks the stored counts, not class hooks."""
    original = AdmissionPolicy.__getattribute__

    def forged_attribute(value: AdmissionPolicy, name: str) -> object:
        if name == field:
            return 1
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(AdmissionPolicy, "__getattribute__", forged_attribute)
        with pytest.raises(AdmissionPolicyError, match="positive integer"):
            _ = AdmissionPolicy(
                minimum_source_similarity=0.5,
                minimum_anchor_coverage=0.5,
                minimum_anchor_files=(
                    True if field == "minimum_anchor_files" else 1
                ),
                minimum_anchors_per_file=(
                    True if field == "minimum_anchors_per_file" else 1
                ),
            )


@pytest.mark.parametrize(
    ("field", "forged", "expected"),
    [
        ("path", "source.c", "invalid identity path"),
        ("canonical", b"contents", "exact bytes"),
    ],
)
def test_identity_file_constructor_rejects_late_getter_forgery(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    forged: object,
    expected: str,
) -> None:
    """Identity metadata construction must inspect stored path and bytes."""
    original = IdentityFile.__getattribute__

    def forged_attribute(value: IdentityFile, name: str) -> object:
        if name == field:
            return forged
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(IdentityFile, "__getattribute__", forged_attribute)
        with pytest.raises(AdmissionPolicyError, match=expected):
            _ = IdentityFile(
                path="../escape.c" if field == "path" else "source.c",
                canonical=(
                    b"contents"
                    if field == "path"
                    else cast("bytes", cast("object", bytearray()))
                ),
            )


def test_identity_tree_constructor_rejects_late_files_getter_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late getter cannot hide reversed source path order at construction."""
    sorted_files = (
        IdentityFile("a.c", b"a"),
        IdentityFile("b.c", b"b"),
    )
    original = IdentityTree.__getattribute__

    def forged_attribute(value: IdentityTree, name: str) -> object:
        if name == "files":
            return sorted_files
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(IdentityTree, "__getattribute__", forged_attribute)
        with pytest.raises(AdmissionPolicyError, match="unique and sorted"):
            _ = IdentityTree(files=tuple(reversed(sorted_files)))


@pytest.mark.parametrize("field", ["path", "canonical"])
@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_admission_identity_file_reads_ignore_late_getters(
    monkeypatch: pytest.MonkeyPatch, field: str, hook: str
) -> None:
    """Source path matching and content comparison require stored identity."""
    reference = identity_tree({"source.c": b"reproducible source bytes"})
    candidate = identity_tree(
        {"other.c" if field == "path" else "source.c": b"unrelated bytes"}
    )
    policy = _policy(source_similarity=0.8)
    expected = evaluate_admission(reference, candidate, policy)
    assert not expected.admitted
    original = IdentityFile.__getattribute__
    calls = 0

    def forged_attribute(value: IdentityFile, name: str) -> object:
        nonlocal calls
        if name == field and value is candidate.files[0]:
            calls += 1
            return (
                b"reproducible source bytes"
                if field == "canonical"
                else "source.c"
            )
        return cast("object", original(value, name))

    def forged_property(value: IdentityFile) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(IdentityFile, field, property(forged_property))
        else:
            patch.setattr(IdentityFile, "__getattribute__", forged_attribute)
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "late identity file getter influenced lineage"


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_admission_identity_tree_reads_ignore_late_files_getter(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A replaced files getter cannot substitute reference records as source."""
    reference = identity_tree({"source.c": b"reproducible source bytes"})
    candidate = identity_tree({"other.c": b"unrelated bytes"})
    policy = _policy(source_similarity=0.8)
    expected = evaluate_admission(reference, candidate, policy)
    assert not expected.admitted
    original = IdentityTree.__getattribute__
    source_files = reference.files
    calls = 0

    def forged_attribute(value: IdentityTree, name: str) -> object:
        nonlocal calls
        if name == "files" and value is candidate:
            calls += 1
            return source_files
        return cast("object", original(value, name))

    def forged_property(value: IdentityTree) -> object:
        return forged_attribute(value, "files")

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(IdentityTree, "files", property(forged_property))
        else:
            patch.setattr(IdentityTree, "__getattribute__", forged_attribute)
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "late identity tree getter rewrote source lineage"


@pytest.mark.parametrize(
    ("field", "forged", "actual"),
    [
        ("matched_anchor_count", 1, ("source.c", 1.0, 1.0, 1, 2)),
        ("structural_similarity", 1.0, ("source.c", True, 1.0, 1, 1)),
    ],
)
def test_file_evidence_constructor_ignores_late_getter_forgery(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    forged: object,
    actual: tuple[object, ...],
) -> None:
    """A file receipt cannot validate fraudulent metadata via a late hook."""
    original = FileAdmissionEvidence.__getattribute__

    def forged_attribute(value: FileAdmissionEvidence, name: str) -> object:
        if name == field:
            return forged
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(
            FileAdmissionEvidence, "__getattribute__", forged_attribute
        )
        with pytest.raises(AdmissionPolicyError):
            _ = FileAdmissionEvidence(
                cast("str", actual[0]),
                cast("float", actual[1]),
                cast("float", actual[2]),
                cast("int", actual[3]),
                cast("int", actual[4]),
            )


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
def test_admission_ignores_late_file_score_forgery(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A completed source score cannot be promoted using a record class hook."""
    reference = identity_tree({"main.c": _content("reference", 0)})
    candidate = identity_tree({"main.c": _content("unrelated", 0)})
    policy = _policy(source_similarity=0.8)
    expected = evaluate_admission(reference, candidate, policy)
    assert not expected.admitted
    original = FileAdmissionEvidence.__getattribute__
    calls = 0

    def forged_attribute(value: FileAdmissionEvidence, name: str) -> object:
        nonlocal calls
        if name == "structural_similarity":
            calls += 1
            return 1.0
        return cast("object", original(value, name))

    def forged_property(value: FileAdmissionEvidence) -> object:
        return forged_attribute(value, "structural_similarity")

    original_slot = cast(
        "MemberDescriptorType",
        FileAdmissionEvidence.__dict__["structural_similarity"],
    )

    def store_score(value: FileAdmissionEvidence, score: float) -> None:
        original_slot.__set__(value, score)

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(
                FileAdmissionEvidence,
                "structural_similarity",
                property(forged_property, store_score),
            )
        else:
            patch.setattr(
                FileAdmissionEvidence,
                "__getattribute__",
                forged_attribute,
            )
        observed = evaluate_admission(reference, candidate, policy)
    assert observed == expected
    assert calls == 0, "mutable file score hook influenced source admission"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
@pytest.mark.parametrize(
    "field",
    [
        "source_similarity",
        "anchor_coverage",
        "eligible_anchor_files",
        "satisfied_anchor_files",
        "files",
        "policy",
    ],
)
def test_tree_evidence_constructor_rejects_late_field_forgery(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    hook: str,
) -> None:
    """A source receipt must validate stored scores and policy, not getters."""
    file = FileAdmissionEvidence("source.c", 1.0, 1.0, 1, 1)
    valid: dict[str, object] = {
        "source_similarity": 1.0,
        "anchor_coverage": 1.0,
        "eligible_anchor_files": 1,
        "satisfied_anchor_files": 1,
        "files": (file,),
        "policy": AdmissionPolicy(0.5, 0.5, 1, 1),
    }
    invalid: dict[str, object] = {
        "source_similarity": 0.0,
        "anchor_coverage": 0.0,
        "eligible_anchor_files": 0,
        "satisfied_anchor_files": 0,
        "files": (),
        "policy": object(),
    }
    values = valid | {field: invalid[field]}
    calls = 0

    def forged_attribute(value: TreeAdmissionEvidence, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return valid[field]
        return cast("object", object.__getattribute__(value, name))

    def forged_property(value: TreeAdmissionEvidence) -> object:
        return forged_attribute(value, field)

    with monkeypatch.context() as patch:
        if hook == "slot":
            original_slot = cast(
                "MemberDescriptorType", TreeAdmissionEvidence.__dict__[field]
            )

            def store(value: TreeAdmissionEvidence, stored: object) -> None:
                original_slot.__set__(value, stored)

            patch.setattr(
                TreeAdmissionEvidence,
                field,
                property(forged_property, store),
            )
        else:
            patch.setattr(
                TreeAdmissionEvidence, "__getattribute__", forged_attribute
            )
        with pytest.raises(AdmissionPolicyError):
            _ = TreeAdmissionEvidence(
                source_similarity=cast("float", values["source_similarity"]),
                anchor_coverage=cast("float", values["anchor_coverage"]),
                eligible_anchor_files=cast(
                    "int", values["eligible_anchor_files"]
                ),
                satisfied_anchor_files=cast(
                    "int", values["satisfied_anchor_files"]
                ),
                files=cast(
                    "tuple[FileAdmissionEvidence, ...]", values["files"]
                ),
                reasons=(),
                policy=cast("AdmissionPolicy", values["policy"]),
            )
    assert calls == 0, "late tree getter participated in source admission"
