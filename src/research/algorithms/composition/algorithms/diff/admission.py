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
#   - Tree-level structural and stable-anchor source admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tree-level structural and stable-anchor source admission."""

from __future__ import annotations

import builtins
import math
from collections.abc import Callable
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import cast

from algorithms.diff.fingerprints import (
    AnchorCoverage,
    AnchorPolicy,
    StableAnchor,
    anchor_coverage,
    stable_anchors,
)

_BACKSLASH = "\\"
_NUL = "\x00"
_DOT = "."
_PARENT = ".."
_ZERO = 0
_ONE = 1
_STRUCTURAL_POLICY = AnchorPolicy(window_bytes=16, selection_modulus=8)
_ANCHOR_POLICY = AnchorPolicy(window_bytes=32, selection_modulus=64)
# Avoid mutable helper dependencies within ntpath.isreserved/splitdrive.
_WINDOWS_DRIVE_SEPARATOR = ":"
_WINDOWS_RESERVED_CHARACTERS = frozenset(
    chr(value) for value in range(32)
) | frozenset("*?<>/\\:|") | frozenset((chr(34),))
_WINDOWS_RESERVED_DEVICES = frozenset(
    ("CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$")
) | frozenset(
    f"{prefix}{digit}" for prefix in ("COM", "LPT")
    for digit in "123456789¹²³"
)
_NATIVE_FSUM = math.fsum
_NATIVE_ISFINITE = math.isfinite
# Source-lineage verdicts cannot trust post-import mutable sum hooks.
_NATIVE_SUM = builtins.sum
_NATIVE_SORTED = builtins.sorted
_NATIVE_SET = builtins.set
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_FLOAT = builtins.float
_NATIVE_STR = builtins.str
_NATIVE_BYTES = builtins.bytes
_NATIVE_TUPLE = builtins.tuple
_NATIVE_DICT = builtins.dict
_NATIVE_ANY = builtins.any
_NATIVE_ALL = builtins.all
_NATIVE_LEN = builtins.len
_NATIVE_FROZENSET = builtins.frozenset
# Fingerprint receipt classes retain mutable class-level attribute hooks.
_ANCHOR_DIGEST_SLOT = cast(
    "MemberDescriptorType", StableAnchor.__dict__["digest"]
)
_COVERAGE_TOTAL_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["total"]
)
_COVERAGE_MATCHED_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["matched"]
)
_COVERAGE_RATIO_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["ratio"]
)


class AdmissionPolicyError(ValueError):
    """Raised when tree admission policy is internally invalid."""


class AdmissionError(RuntimeError):
    """Raised when candidate source evidence does not satisfy admission."""


def _has_windows_drive(value: str) -> bool:
    return (
        value[1:2] == _WINDOWS_DRIVE_SEPARATOR
        or value.startswith(("//", "\\\\"))
    )


def _is_windows_reserved_component(component: str) -> bool:
    device = component.partition(".")[0].rstrip(" ").upper()
    return (
        (component[-1:] in {".", " "} and component not in {".", ".."})
        or bool(_WINDOWS_RESERVED_CHARACTERS.intersection(component))
        or device in _WINDOWS_RESERVED_DEVICES
    )


def _is_windows_reserved(value: str) -> bool:
    return _NATIVE_ANY(
        _is_windows_reserved_component(component)
        for component in value.split("/")
    )


def _is_portable_relative_path(path: str) -> bool:
    if (
        not path
        or path == _DOT
        or _NATIVE_ANY(char in path for char in (_NUL, _BACKSLASH))
    ):
        return False
    try:
        _ = path.encode("utf-8")
    except UnicodeEncodeError:
        return False
    # Identity labels are lexical authority, not mutable pathlib methods.
    # Empty/dot/parent components also cover absolute and noncanonical paths.
    return (
        not _has_windows_drive(path)
        and not _is_windows_reserved(path)
        and _NATIVE_ALL(
            part not in {"", _DOT, _PARENT} for part in path.split("/")
        )
    )


def _require_file_path_topology(paths: tuple[str, ...]) -> None:
    """Reject file labels that also name another file's ancestor directory.

    Raises:
        AdmissionPolicyError: A file path is the ancestor of another file.

    """
    file_paths = _NATIVE_SET(paths)
    for path in paths:
        components = path.split("/")
        ancestor = components[0]
        for component in components[1:]:
            if ancestor in file_paths:
                message = (
                    "identity file paths contain an ancestor/descendant overlap"
                )
                raise AdmissionPolicyError(message)
            ancestor += "/" + component


@dataclass(frozen=True, slots=True, order=True, init=False)
class IdentityFile:
    """One consumer-canonicalized file admitted to source identity."""

    path: str
    canonical: bytes

    def __init__(self, path: str, canonical: bytes) -> None:
        """Seal portable identity with the original validator."""
        _IDENTITY_PATH_SLOT.__set__(self, path)
        _IDENTITY_CANONICAL_SLOT.__set__(self, canonical)
        _IDENTITY_FILE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require one normalized portable relative file path.

        Raises:
            AdmissionPolicyError: The identity path is unsafe or non-canonical.

        """
        path, canonical = _identity_fields(self)
        if _NATIVE_TYPE(path) is not _NATIVE_STR:
            message = "identity path must use the exact string type"
            raise AdmissionPolicyError(message)
        if _NATIVE_TYPE(canonical) is not _NATIVE_BYTES:
            message = "identity canonical content must use exact bytes"
            raise AdmissionPolicyError(message)
        if not _is_portable_relative_path(path):
            message = f"invalid identity path: {path!r}"
            raise AdmissionPolicyError(message)


# Dataclass construction must not dispatch through a late class hook.
_IDENTITY_FILE_VALIDATOR = cast(
    "Callable[[IdentityFile], None]", IdentityFile.__dict__["__post_init__"]
)


# Do not let late class-level readers override canonical source identity.
_IDENTITY_PATH_SLOT = cast(
    "MemberDescriptorType", IdentityFile.__dict__["path"]
)
_IDENTITY_CANONICAL_SLOT = cast(
    "MemberDescriptorType", IdentityFile.__dict__["canonical"]
)


def _identity_fields(file: IdentityFile) -> tuple[str, bytes]:
    return (
        cast("str", _IDENTITY_PATH_SLOT.__get__(file, IdentityFile)),
        cast("bytes", _IDENTITY_CANONICAL_SLOT.__get__(file, IdentityFile)),
    )


@dataclass(frozen=True, slots=True, init=False)
class IdentityTree:
    """Explicit set of consumer-selected files participating in identity."""

    files: tuple[IdentityFile, ...]

    def __init__(self, files: tuple[IdentityFile, ...]) -> None:
        """Seal sorted source identity with the original validator."""
        _IDENTITY_FILES_SLOT.__set__(self, files)
        _IDENTITY_TREE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require sorted unique paths for deterministic evidence.

        Raises:
            AdmissionPolicyError: Files are duplicated or out of order.

        """
        files = _tree_files(self)
        if _NATIVE_TYPE(files) is not _NATIVE_TUPLE:
            message = "identity tree files must use the exact immutable tuple"
            raise AdmissionPolicyError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(item) is not IdentityFile for item in files
        ):
            message = "identity tree contains a foreign file record"
            raise AdmissionPolicyError(message)
        paths = _NATIVE_TUPLE(_identity_fields(item)[0] for item in files)
        if paths != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(paths))):
            message = "identity tree paths must be unique and sorted"
            raise AdmissionPolicyError(message)
        _require_file_path_topology(paths)


# Dataclass construction must not dispatch through a late class hook.
_IDENTITY_TREE_VALIDATOR = cast(
    "Callable[[IdentityTree], None]", IdentityTree.__dict__["__post_init__"]
)


_IDENTITY_FILES_SLOT = cast(
    "MemberDescriptorType", IdentityTree.__dict__["files"]
)


def _tree_files(tree: IdentityTree) -> tuple[IdentityFile, ...]:
    return cast(
        "tuple[IdentityFile, ...]",
        _IDENTITY_FILES_SLOT.__get__(tree, IdentityTree),
    )


@dataclass(frozen=True, slots=True, init=False)
class AdmissionPolicy:
    """Thresholds and distribution requirements for source admission."""

    minimum_source_similarity: float
    minimum_anchor_coverage: float
    minimum_anchor_files: int
    minimum_anchors_per_file: int
    structural_policy: AnchorPolicy = _STRUCTURAL_POLICY
    anchor_policy: AnchorPolicy = _ANCHOR_POLICY

    def __init__(
        self,
        minimum_source_similarity: float,
        minimum_anchor_coverage: float,
        minimum_anchor_files: int,
        minimum_anchors_per_file: int,
        structural_policy: AnchorPolicy = _STRUCTURAL_POLICY,
        anchor_policy: AnchorPolicy = _ANCHOR_POLICY,
    ) -> None:
        """Seal source admission thresholds with the original validator."""
        _POLICY_SOURCE_SLOT.__set__(self, minimum_source_similarity)
        _POLICY_COVERAGE_SLOT.__set__(self, minimum_anchor_coverage)
        _POLICY_FILES_SLOT.__set__(self, minimum_anchor_files)
        _POLICY_PER_FILE_SLOT.__set__(self, minimum_anchors_per_file)
        _POLICY_STRUCTURAL_SLOT.__set__(self, structural_policy)
        _POLICY_ANCHORS_SLOT.__set__(self, anchor_policy)
        _ADMISSION_POLICY_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Validate threshold and positive-count requirements.

        Raises:
            AdmissionPolicyError: A threshold or evidence count is invalid.

        """
        source, coverage, files, per_file, structural, anchors = (
            _policy_fields(self)
        )
        _validate_fraction("minimum_source_similarity", source)
        _validate_fraction("minimum_anchor_coverage", coverage)
        if _NATIVE_TYPE(files) is not _NATIVE_INT or files < _ONE:
            message = "minimum_anchor_files must be a positive integer"
            raise AdmissionPolicyError(message)
        if _NATIVE_TYPE(per_file) is not _NATIVE_INT or per_file < _ONE:
            message = "minimum_anchors_per_file must be a positive integer"
            raise AdmissionPolicyError(message)
        if _NATIVE_TYPE(structural) is not AnchorPolicy:
            message = "structural_policy must use the exact AnchorPolicy type"
            raise AdmissionPolicyError(message)
        if _NATIVE_TYPE(anchors) is not AnchorPolicy:
            message = "anchor_policy must use the exact AnchorPolicy type"
            raise AdmissionPolicyError(message)


# Dataclass construction must not dispatch through a late class hook.
_ADMISSION_POLICY_VALIDATOR = cast(
    "Callable[[AdmissionPolicy], None]",
    AdmissionPolicy.__dict__["__post_init__"],
)


# A frozen policy's class descriptors can still be replaced by consumers.
_POLICY_SOURCE_SLOT = cast(
    "MemberDescriptorType",
    AdmissionPolicy.__dict__["minimum_source_similarity"],
)
_POLICY_COVERAGE_SLOT = cast(
    "MemberDescriptorType", AdmissionPolicy.__dict__["minimum_anchor_coverage"]
)
_POLICY_FILES_SLOT = cast(
    "MemberDescriptorType", AdmissionPolicy.__dict__["minimum_anchor_files"]
)
_POLICY_PER_FILE_SLOT = cast(
    "MemberDescriptorType", AdmissionPolicy.__dict__["minimum_anchors_per_file"]
)
_POLICY_STRUCTURAL_SLOT = cast(
    "MemberDescriptorType", AdmissionPolicy.__dict__["structural_policy"]
)
_POLICY_ANCHORS_SLOT = cast(
    "MemberDescriptorType", AdmissionPolicy.__dict__["anchor_policy"]
)


def _policy_fields(
    policy: AdmissionPolicy,
) -> tuple[float, float, int, int, AnchorPolicy, AnchorPolicy]:
    return (
        cast("float", _POLICY_SOURCE_SLOT.__get__(policy, AdmissionPolicy)),
        cast("float", _POLICY_COVERAGE_SLOT.__get__(policy, AdmissionPolicy)),
        cast("int", _POLICY_FILES_SLOT.__get__(policy, AdmissionPolicy)),
        cast("int", _POLICY_PER_FILE_SLOT.__get__(policy, AdmissionPolicy)),
        cast(
            "AnchorPolicy",
            _POLICY_STRUCTURAL_SLOT.__get__(policy, AdmissionPolicy),
        ),
        cast(
            "AnchorPolicy",
            _POLICY_ANCHORS_SLOT.__get__(policy, AdmissionPolicy),
        ),
    )


def _require_evidence_fraction(value: object, context: str) -> float:
    if _NATIVE_TYPE(value) is not _NATIVE_FLOAT or not _NATIVE_ISFINITE(value):
        message = f"{context} must use a finite exact float"
        raise AdmissionPolicyError(message)
    if value < _ZERO or value > _ONE:
        message = f"{context} must be in [0, 1]"
        raise AdmissionPolicyError(message)
    return value


def _require_evidence_count(value: object, context: str) -> int:
    if _NATIVE_TYPE(value) is not _NATIVE_INT or value < _ZERO:
        message = f"{context} must use a non-negative exact integer"
        raise AdmissionPolicyError(message)
    return value


def _require_evidence_path(value: object) -> str:
    if _NATIVE_TYPE(value) is not _NATIVE_STR:
        message = "file admission path must use the exact string type"
        raise AdmissionPolicyError(message)
    if not _is_portable_relative_path(value):
        message = f"invalid file admission path: {value!r}"
        raise AdmissionPolicyError(message)
    return value


def _require_reason_tuple(value: object) -> tuple[str, ...]:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "tree admission reasons must use the exact immutable tuple"
        raise AdmissionPolicyError(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not _NATIVE_STR or not item for item in items
    ):
        message = "tree admission reasons must contain non-empty exact strings"
        raise AdmissionPolicyError(message)
    return cast("tuple[str, ...]", value)


def _require_file_anchor_relation(
    coverage: float | None,
    reference: int,
    matched: int,
) -> None:
    if matched > reference:
        message = "matched anchor count cannot exceed reference anchors"
        raise AdmissionPolicyError(message)
    if coverage is not None and (
        reference == _ZERO or coverage != matched / reference
    ):
        message = "file anchor coverage does not match anchor counts"
        raise AdmissionPolicyError(message)


def _validate_file_admission_evidence(evidence: FileAdmissionEvidence) -> None:
    path, similarity, fraction, count, matched_count = _file_evidence_fields(
        evidence
    )
    _ = _require_evidence_path(path)
    _ = _require_evidence_fraction(similarity, "file structural similarity")
    coverage = (
        _require_evidence_fraction(fraction, "file anchor coverage")
        if fraction is not None
        else None
    )
    reference = _require_evidence_count(count, "reference anchor count")
    matched = _require_evidence_count(matched_count, "matched anchor count")
    _require_file_anchor_relation(coverage, reference, matched)


def _require_file_evidence_tuple(
    value: object,
) -> tuple[FileAdmissionEvidence, ...]:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "tree admission files must use the exact immutable tuple"
        raise AdmissionPolicyError(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not FileAdmissionEvidence for item in items
    ):
        message = "tree admission files must use exact immutable records"
        raise AdmissionPolicyError(message)
    files = cast("tuple[FileAdmissionEvidence, ...]", value)
    if not files:
        message = "tree admission evidence requires at least one file"
        raise AdmissionPolicyError(message)
    paths = _NATIVE_TUPLE(_file_evidence_fields(item)[0] for item in files)
    if paths != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(paths))):
        message = "tree admission file paths must be unique and sorted"
        raise AdmissionPolicyError(message)
    _require_file_path_topology(paths)
    return files


def _tree_file_aggregates(
    files: tuple[FileAdmissionEvidence, ...],
) -> tuple[float, float, int]:
    source_values = _NATIVE_TUPLE(
        _file_evidence_fields(item)[1] for item in files
    )
    source = _NATIVE_FSUM(source_values) / _NATIVE_LEN(source_values)
    covered = _NATIVE_TUPLE(
        cast("float", _file_evidence_fields(item)[2])
        for item in files
        if _file_evidence_fields(item)[2] is not None
    )
    anchor = _NATIVE_FSUM(covered) / _NATIVE_LEN(covered) if covered else 0.0
    return source, anchor, _NATIVE_LEN(covered)


def _require_equal_evidence_value(
    actual: float,
    expected: float,
    message: str,
) -> None:
    if actual != expected:
        raise AdmissionPolicyError(message)


def _validate_tree_admission_evidence(evidence: TreeAdmissionEvidence) -> None:
    source, coverage, eligible_count, satisfied_count, records, policy = (
        _tree_evidence_fields(evidence)
    )
    files = _require_file_evidence_tuple(records)
    aggregates = _tree_file_aggregates(files)
    _require_equal_evidence_value(
        _require_evidence_fraction(source, "tree source similarity"),
        aggregates[0],
        "tree source similarity does not match file evidence",
    )
    _require_equal_evidence_value(
        _require_evidence_fraction(coverage, "tree anchor coverage"),
        aggregates[1],
        "tree anchor coverage does not match file evidence",
    )
    eligible = _require_evidence_count(
        eligible_count,
        "eligible anchor file count",
    )
    _require_equal_evidence_value(
        eligible,
        aggregates[2],
        "eligible anchor file count does not match file evidence",
    )
    satisfied = _require_evidence_count(
        satisfied_count,
        "satisfied anchor file count",
    )
    if satisfied > eligible:
        message = "satisfied anchor file count cannot exceed eligible files"
        raise AdmissionPolicyError(message)
    matched_eligible = _NATIVE_SUM(
        _file_evidence_fields(item)[2] is not None
        and _file_evidence_fields(item)[4] > _ZERO
        for item in files
    )
    if satisfied > matched_eligible:
        message = "satisfied anchor file count exceeds matched eligible files"
        raise AdmissionPolicyError(message)
    _validate_policy_bound_evidence(
        evidence, files, aggregates, satisfied, policy
    )


def _validate_policy_bound_evidence(
    evidence: TreeAdmissionEvidence,
    files: tuple[FileAdmissionEvidence, ...],
    aggregates: tuple[float, float, int],
    satisfied: int,
    policy: AdmissionPolicy,
) -> None:
    reasons = _require_reason_tuple(
        _TREE_REASONS_SLOT.__get__(evidence, TreeAdmissionEvidence)
    )
    if _NATIVE_TYPE(policy) is not AdmissionPolicy:
        message = "tree admission evidence requires exact AdmissionPolicy"
        raise AdmissionPolicyError(message)
    _, minimum_coverage, _, minimum_per_file, _, _ = _policy_fields(policy)
    if _NATIVE_ANY(
        (_file_evidence_fields(item)[2] is not None)
        != (_file_evidence_fields(item)[3] >= minimum_per_file)
        for item in files
    ):
        message = "file anchor eligibility does not match admission policy"
        raise AdmissionPolicyError(message)
    expected_satisfied = _NATIVE_SUM(
        _file_evidence_fields(item)[4] > _ZERO
        and _file_evidence_fields(item)[2] is not None
        and cast("float", _file_evidence_fields(item)[2]) >= minimum_coverage
        for item in files
    )
    if satisfied != expected_satisfied:
        message = "satisfied anchor file count does not match admission policy"
        raise AdmissionPolicyError(message)
    aggregate = _AggregateEvidence(
        source_similarity=aggregates[0],
        anchor_average=aggregates[1],
        eligible_files=aggregates[2],
        satisfied_files=expected_satisfied,
    )
    if reasons != _reason_tuple(aggregate, policy):
        message = "tree admission reasons do not match admission policy"
        raise AdmissionPolicyError(message)


@dataclass(frozen=True, slots=True, init=False)
class FileAdmissionEvidence:
    """Structural and anchor evidence for one reference identity file."""

    path: str
    structural_similarity: float
    anchor_coverage: float | None
    reference_anchor_count: int
    matched_anchor_count: int

    def __init__(
        self,
        path: str,
        structural_similarity: float,
        anchor_coverage: float | None,
        reference_anchor_count: int,
        matched_anchor_count: int,
    ) -> None:
        """Seal per-file source evidence with the original validator."""
        _FILE_EVIDENCE_PATH_SLOT.__set__(self, path)
        _FILE_EVIDENCE_SIMILARITY_SLOT.__set__(self, structural_similarity)
        _FILE_EVIDENCE_COVERAGE_SLOT.__set__(self, anchor_coverage)
        _FILE_EVIDENCE_REFERENCE_SLOT.__set__(self, reference_anchor_count)
        _FILE_EVIDENCE_MATCHED_SLOT.__set__(self, matched_anchor_count)
        _FILE_ADMISSION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require internally coherent per-file source evidence."""
        _validate_file_admission_evidence(self)


# Dataclass construction must not dispatch through a late class hook.
_FILE_ADMISSION_VALIDATOR = cast(
    "Callable[[FileAdmissionEvidence], None]",
    FileAdmissionEvidence.__dict__["__post_init__"],
)


# Per-file admission is also a class-mutable frozen record. Read raw slots.
_FILE_EVIDENCE_PATH_SLOT = cast(
    "MemberDescriptorType", FileAdmissionEvidence.__dict__["path"]
)
_FILE_EVIDENCE_SIMILARITY_SLOT = cast(
    "MemberDescriptorType",
    FileAdmissionEvidence.__dict__["structural_similarity"],
)
_FILE_EVIDENCE_COVERAGE_SLOT = cast(
    "MemberDescriptorType", FileAdmissionEvidence.__dict__["anchor_coverage"]
)
_FILE_EVIDENCE_REFERENCE_SLOT = cast(
    "MemberDescriptorType",
    FileAdmissionEvidence.__dict__["reference_anchor_count"],
)
_FILE_EVIDENCE_MATCHED_SLOT = cast(
    "MemberDescriptorType",
    FileAdmissionEvidence.__dict__["matched_anchor_count"],
)


def _file_evidence_fields(
    receipt: FileAdmissionEvidence,
) -> tuple[str, float, float | None, int, int]:
    return (
        cast(
            "str",
            _FILE_EVIDENCE_PATH_SLOT.__get__(receipt, FileAdmissionEvidence),
        ),
        cast(
            "float",
            _FILE_EVIDENCE_SIMILARITY_SLOT.__get__(
                receipt, FileAdmissionEvidence
            ),
        ),
        cast(
            "float | None",
            _FILE_EVIDENCE_COVERAGE_SLOT.__get__(
                receipt, FileAdmissionEvidence
            ),
        ),
        cast(
            "int",
            _FILE_EVIDENCE_REFERENCE_SLOT.__get__(
                receipt, FileAdmissionEvidence
            ),
        ),
        cast(
            "int",
            _FILE_EVIDENCE_MATCHED_SLOT.__get__(receipt, FileAdmissionEvidence),
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class TreeAdmissionEvidence:
    """Aggregated source-lineage evidence with deterministic failure reasons."""

    source_similarity: float
    anchor_coverage: float
    eligible_anchor_files: int
    satisfied_anchor_files: int
    files: tuple[FileAdmissionEvidence, ...]
    reasons: tuple[str, ...]
    policy: AdmissionPolicy

    def __init__(
        self,
        source_similarity: float,
        anchor_coverage: float,
        eligible_anchor_files: int,
        satisfied_anchor_files: int,
        files: tuple[FileAdmissionEvidence, ...],
        reasons: tuple[str, ...],
        policy: AdmissionPolicy,
    ) -> None:
        """Seal aggregate source evidence with the original validator."""
        _TREE_SOURCE_SLOT.__set__(self, source_similarity)
        _TREE_ANCHOR_SLOT.__set__(self, anchor_coverage)
        _TREE_ELIGIBLE_SLOT.__set__(self, eligible_anchor_files)
        _TREE_SATISFIED_SLOT.__set__(self, satisfied_anchor_files)
        _TREE_FILES_SLOT.__set__(self, files)
        _TREE_REASONS_SLOT.__set__(self, reasons)
        _TREE_POLICY_SLOT.__set__(self, policy)
        _TREE_ADMISSION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require aggregate evidence and a policy-consistent decision."""
        _validate_tree_admission_evidence(self)

    @property
    def admitted(self) -> bool:
        """Whether every source-lineage requirement passed.

        Returns:
            True exactly when no deterministic rejection reason exists.

        """
        return not _TREE_REASONS_SLOT.__get__(self, TreeAdmissionEvidence)


# Dataclass construction must not dispatch through a late class hook.
_TREE_ADMISSION_VALIDATOR = cast(
    "Callable[[TreeAdmissionEvidence], None]",
    TreeAdmissionEvidence.__dict__["__post_init__"],
)


# Class-level slot descriptors are mutable after consumer module imports.
# Evidence policy decisions must observe the value stored at construction.
_TREE_REASONS_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["reasons"]
)
_TREE_SOURCE_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["source_similarity"]
)
_TREE_ANCHOR_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["anchor_coverage"]
)
_TREE_ELIGIBLE_SLOT = cast(
    "MemberDescriptorType",
    TreeAdmissionEvidence.__dict__["eligible_anchor_files"],
)
_TREE_SATISFIED_SLOT = cast(
    "MemberDescriptorType",
    TreeAdmissionEvidence.__dict__["satisfied_anchor_files"],
)
_TREE_FILES_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["files"]
)
_TREE_POLICY_SLOT = cast(
    "MemberDescriptorType", TreeAdmissionEvidence.__dict__["policy"]
)


def _tree_evidence_fields(
    evidence: TreeAdmissionEvidence,
) -> tuple[
    float, float, int, int, tuple[FileAdmissionEvidence, ...], AdmissionPolicy
]:
    owner = TreeAdmissionEvidence
    return (
        cast("float", _TREE_SOURCE_SLOT.__get__(evidence, owner)),
        cast("float", _TREE_ANCHOR_SLOT.__get__(evidence, owner)),
        cast("int", _TREE_ELIGIBLE_SLOT.__get__(evidence, owner)),
        cast("int", _TREE_SATISFIED_SLOT.__get__(evidence, owner)),
        cast(
            "tuple[FileAdmissionEvidence, ...]",
            _TREE_FILES_SLOT.__get__(evidence, owner),
        ),
        cast("AdmissionPolicy", _TREE_POLICY_SLOT.__get__(evidence, owner)),
    )


def identity_tree(files: dict[str, bytes]) -> IdentityTree:
    """Build a sorted explicit identity tree from consumer-canonicalized bytes.

    Returns:
        A deterministic identity tree.

    Raises:
        AdmissionPolicyError: The mapping or any path/content value is invalid.

    """
    if _NATIVE_TYPE(files) is not _NATIVE_DICT:
        message = "identity source files must use the exact dictionary type"
        raise AdmissionPolicyError(message)
    for path, canonical in files.items():
        if _NATIVE_TYPE(path) is not _NATIVE_STR:
            message = "identity source path must use the exact string type"
            raise AdmissionPolicyError(message)
        if _NATIVE_TYPE(canonical) is not _NATIVE_BYTES:
            message = "identity source content must use exact bytes"
            raise AdmissionPolicyError(message)
    records = _NATIVE_TUPLE(
        IdentityFile(path=path, canonical=canonical)
        for path, canonical in _NATIVE_SORTED(files.items())
    )
    return IdentityTree(files=records)


def _validate_fraction(name: str, value: object) -> None:
    if _NATIVE_TYPE(value) is _NATIVE_INT:
        # Only zero and one can be integer fractions in the admitted range.
        # Never coerce arbitrary-sized integers to float or diagnostic text.
        if _ZERO <= value <= _ONE:
            return
    elif _NATIVE_TYPE(value) is _NATIVE_FLOAT:
        if _NATIVE_ISFINITE(value) and _ZERO <= value <= _ONE:
            return
    else:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise AdmissionPolicyError(message)
    message = f"{name} must be a finite fraction in [0, 1]"
    raise AdmissionPolicyError(message)


def _digest_set(anchors: tuple[StableAnchor, ...]) -> frozenset[bytes]:
    return _NATIVE_FROZENSET(
        cast("bytes", _ANCHOR_DIGEST_SLOT.__get__(anchor, StableAnchor))
        for anchor in anchors
    )


def _structural_similarity(
    reference: bytes,
    candidate: bytes,
    policy: AnchorPolicy,
) -> float:
    if reference == candidate:
        return 1.0
    reference_digests = _digest_set(stable_anchors(reference, policy))
    candidate_digests = _digest_set(stable_anchors(candidate, policy))
    if not reference_digests or not candidate_digests:
        return 0.0
    intersection = _NATIVE_LEN(reference_digests & candidate_digests)
    total = _NATIVE_LEN(reference_digests) + _NATIVE_LEN(candidate_digests)
    return 2.0 * intersection / total


def _file_evidence(
    reference: IdentityFile,
    candidate: IdentityFile | None,
    policy: AdmissionPolicy,
) -> FileAdmissionEvidence:
    reference_path, reference_bytes = _identity_fields(reference)
    candidate_bytes = (
        b"" if candidate is None else _identity_fields(candidate)[1]
    )
    _, _, _, minimum_per_file, structural_policy, anchor_policy = (
        _policy_fields(policy)
    )
    structural = (
        _structural_similarity(
            reference_bytes,
            candidate_bytes,
            structural_policy,
        )
        if candidate is not None
        else 0.0
    )
    reference_anchors = stable_anchors(reference_bytes, anchor_policy)
    candidate_anchors = stable_anchors(candidate_bytes, anchor_policy)
    coverage = anchor_coverage(reference_anchors, candidate_anchors)
    total = cast(
        "int", _COVERAGE_TOTAL_SLOT.__get__(coverage, AnchorCoverage)
    )
    matched = cast(
        "int", _COVERAGE_MATCHED_SLOT.__get__(coverage, AnchorCoverage)
    )
    ratio = cast(
        "float", _COVERAGE_RATIO_SLOT.__get__(coverage, AnchorCoverage)
    )
    eligible = total >= minimum_per_file
    return FileAdmissionEvidence(
        path=reference_path,
        structural_similarity=structural,
        anchor_coverage=ratio if eligible else None,
        reference_anchor_count=total,
        matched_anchor_count=matched,
    )


def _mean(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return _NATIVE_FSUM(values) / _NATIVE_LEN(values)


@dataclass(frozen=True, slots=True, init=False)
class _AggregateEvidence:
    source_similarity: float
    anchor_average: float
    eligible_files: int
    satisfied_files: int

    def __init__(
        self,
        source_similarity: float,
        anchor_average: float,
        eligible_files: int,
        satisfied_files: int,
    ) -> None:
        """Capture aggregate values without mutable class property setters."""
        _AGGREGATE_SOURCE_SLOT.__set__(self, source_similarity)
        _AGGREGATE_ANCHOR_SLOT.__set__(self, anchor_average)
        _AGGREGATE_ELIGIBLE_SLOT.__set__(self, eligible_files)
        _AGGREGATE_SATISFIED_SLOT.__set__(self, satisfied_files)


_AGGREGATE_SOURCE_SLOT = cast(
    "MemberDescriptorType", _AggregateEvidence.__dict__["source_similarity"]
)
_AGGREGATE_ANCHOR_SLOT = cast(
    "MemberDescriptorType", _AggregateEvidence.__dict__["anchor_average"]
)
_AGGREGATE_ELIGIBLE_SLOT = cast(
    "MemberDescriptorType", _AggregateEvidence.__dict__["eligible_files"]
)
_AGGREGATE_SATISFIED_SLOT = cast(
    "MemberDescriptorType", _AggregateEvidence.__dict__["satisfied_files"]
)


def _aggregate_fields(aggregate: _AggregateEvidence) -> tuple[float, float, int, int]:
    """Read original score storage without replaceable class getters."""
    return (
        cast("float", _AGGREGATE_SOURCE_SLOT.__get__(aggregate, _AggregateEvidence)),
        cast("float", _AGGREGATE_ANCHOR_SLOT.__get__(aggregate, _AggregateEvidence)),
        cast("int", _AGGREGATE_ELIGIBLE_SLOT.__get__(aggregate, _AggregateEvidence)),
        cast("int", _AGGREGATE_SATISFIED_SLOT.__get__(aggregate, _AggregateEvidence)),
    )


def _reason_tuple(
    aggregate: _AggregateEvidence,
    policy: AdmissionPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    source, coverage, minimum_files, _, _, _ = _policy_fields(policy)
    similarity, average, eligible, satisfied = _aggregate_fields(aggregate)
    if similarity < source:
        reasons.append("insufficient structural source similarity")
    if average < coverage:
        reasons.append("insufficient stable-anchor coverage")
    if eligible < minimum_files:
        reasons.append("insufficient files with anchor evidence")
    if satisfied < minimum_files:
        reasons.append("stable-anchor evidence is not sufficiently distributed")
    return _NATIVE_TUPLE(reasons)


def evaluate_admission(
    reference: IdentityTree,
    candidate: IdentityTree,
    policy: AdmissionPolicy,
) -> TreeAdmissionEvidence:
    """Evaluate structural and distributed-anchor source lineage.

    Every reference file receives equal weight. Consumers choose which files
    belong to identity before calling this function, so opaque assets cannot
    gain influence merely by being large.

    Returns:
        Deterministic per-file and aggregate admission evidence.

    Raises:
        AdmissionPolicyError: Input trees or policy use foreign runtime types.
        AdmissionError: The reference identity tree is empty.

    """
    if (
        _NATIVE_TYPE(reference) is not IdentityTree
        or _NATIVE_TYPE(candidate) is not IdentityTree
    ):
        message = (
            "admission identity inputs must use the exact IdentityTree type"
        )
        raise AdmissionPolicyError(message)
    if _NATIVE_TYPE(policy) is not AdmissionPolicy:
        message = "admission policy must use the exact AdmissionPolicy type"
        raise AdmissionPolicyError(message)
    reference_files = _tree_files(reference)
    if not reference_files:
        message = "reference identity tree contains no source evidence"
        raise AdmissionError(message)
    candidate_by_path = {
        _identity_fields(item)[0]: item for item in _tree_files(candidate)
    }
    files = _NATIVE_TUPLE(
        _file_evidence(
            item, candidate_by_path.get(_identity_fields(item)[0]), policy
        )
        for item in reference_files
    )
    source_similarity = _mean(
        _NATIVE_TUPLE(_file_evidence_fields(item)[1] for item in files)
    )
    eligible = _NATIVE_TUPLE(
        item for item in files if _file_evidence_fields(item)[2] is not None
    )
    anchor_average = _mean(
        _NATIVE_TUPLE(
            _file_evidence_fields(item)[2] or 0.0 for item in eligible
        )
    )
    _, minimum_coverage, _, _, _, _ = _policy_fields(policy)
    satisfied = _NATIVE_SUM(
        _file_evidence_fields(item)[4] > _ZERO
        and (_file_evidence_fields(item)[2] or 0.0) >= minimum_coverage
        for item in eligible
    )
    aggregate = _AggregateEvidence(
        source_similarity=source_similarity,
        anchor_average=anchor_average,
        eligible_files=_NATIVE_LEN(eligible),
        satisfied_files=satisfied,
    )
    reasons = _reason_tuple(aggregate, policy)
    return TreeAdmissionEvidence(
        source_similarity=source_similarity,
        anchor_coverage=anchor_average,
        eligible_anchor_files=_NATIVE_LEN(eligible),
        satisfied_anchor_files=satisfied,
        files=files,
        reasons=reasons,
        policy=policy,
    )


def require_admission(
    reference: IdentityTree,
    candidate: IdentityTree,
    policy: AdmissionPolicy,
) -> TreeAdmissionEvidence:
    """Require tree admission and return its evidence.

    Returns:
        Passing deterministic source-lineage evidence.

    Raises:
        AdmissionError: Candidate source lineage is insufficient.

    """
    evidence = evaluate_admission(reference, candidate, policy)
    reasons = _TREE_REASONS_SLOT.__get__(evidence, TreeAdmissionEvidence)
    if reasons:
        message = "; ".join(reasons)
        raise AdmissionError(message)
    return evidence
