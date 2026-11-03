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
#   - In-memory compatible tree planning and fail-closed materialization.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""In-memory compatible tree planning and fail-closed materialization."""

from __future__ import annotations

import builtins
import hashlib
import io
import os
import pathlib
import shutil
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePath
from stat import S_ISDIR, S_ISLNK
from types import MemberDescriptorType, SimpleNamespace
from typing import TYPE_CHECKING, cast

# jig-ignore-next-line: canonical Ruff import grouping requires one statement
from algorithms.diff.admission import AdmissionPolicy, IdentityTree, evaluate_admission
from algorithms.diff.behavior import BehaviorEvidence
from algorithms.diff.exact import (
    ExactTreeError,
    build_exact_plan,
    read_exact_regular_file,
    snapshot_tree,
)
from algorithms.diff.gate import require_transform_admission
from algorithms.diff.mapped import MappedView
from algorithms.diff.model import (
    ExactInstruction,
    ExactInstructionKind,
    OracleLiteral,
    SourceSlice,
    TreeSnapshot,
    _file_fields,
    _oracle_literal_data,
    _plan_fields,
    _snapshot_files,
    _source_slice_fields,
    reserved_windows_component,
)
from algorithms.diff.model import (
    _instruction_fields as _exact_instruction_fields,
)
from algorithms.diff.publication import publish_directory_no_replace
from algorithms.diff.semantic import (
    SemanticAuthoringPlan,
    SemanticEdit,
    SemanticPlacementError,
    apply_semantic_plan,
    build_semantic_plan,
    read_semantic_plan,
)

if TYPE_CHECKING:
    from algorithms.diff.gate import TransformAdmissionEvidence
    from algorithms.diff.model import ExactAuthoringPlan, FileRecord

_ONE = 1
_STAGING_SUFFIX = ".compatible-staging"
_NUL = "\x00"
_HEX_DIGITS = frozenset("0123456789abcdef")
# Preserve metadata admission against late process-global builtin replacements.
_NATIVE_ANY = builtins.any
_NATIVE_BOOL = builtins.bool
_NATIVE_CALLABLE = builtins.callable
_NATIVE_FROZENSET = builtins.frozenset
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_HASATTR = builtins.hasattr
_NATIVE_LEN = builtins.len
_NATIVE_LIST = builtins.list
_NATIVE_SET = builtins.set
_NATIVE_SORTED = builtins.sorted
_NATIVE_TUPLE = builtins.tuple
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_STR = builtins.str
_NATIVE_BYTES = builtins.bytes
_NATIVE_OBJECT_NEW = object.__new__
_NATIVE_ZIP = builtins.zip
# Late domain callbacks may replace builtin exception names; retain their
# original classes for host error classification and cleanup decisions.
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_FILE_NOT_FOUND_ERROR = builtins.FileNotFoundError
_NATIVE_FILE_EXISTS_ERROR = builtins.FileExistsError
_NATIVE_OS_ERROR = builtins.OSError
_NATIVE_PERMISSION_ERROR = builtins.PermissionError
_NATIVE_VALUE_ERROR = builtins.ValueError
_NATIVE_RUNTIME_ERROR = builtins.RuntimeError
_NATIVE_UNICODE_ERROR = builtins.UnicodeError
_NATIVE_TYPE_ERROR = builtins.TypeError
_NATIVE_EXCEPTION = builtins.Exception
# Capture delegated exception identities before consumer callbacks can rebind them.
_NATIVE_EXACT_TREE_ERROR = ExactTreeError
_NATIVE_SEMANTIC_PLACEMENT_ERROR = SemanticPlacementError
# Keep digest evidence independent of later mutable process-global hooks.
_SHA256_FACTORY = hashlib.sha256
_SHA256_BYTES = _SHA256_FACTORY().digest_size
# Domain callbacks cannot replace host path preflight after module load.
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
_NATIVE_RESOLVE = _NATIVE_PATH_TYPE.resolve
_NATIVE_IS_RELATIVE_TO = _NATIVE_PATH_TYPE.is_relative_to
_NATIVE_RELATIVE_TO = _NATIVE_PATH_TYPE.relative_to
_NATIVE_IS_JUNCTION = _NATIVE_PATH_TYPE.is_junction
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_REALPATH = os.path.realpath
_NATIVE_OS_PATH_MODULE = os.path
_NATIVE_OS_SPLITROOT = os.path.splitroot
_NATIVE_OS_SPLITDRIVE = os.path.splitdrive
_NATIVE_OS_PATH_JOIN = os.path.join
_NATIVE_OS_PATH_SEP = os.path.sep
_NATIVE_OS_PATH_ALTSEP = os.path.altsep
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_OS_READLINK = os.readlink
_NATIVE_OS_GETCWD = os.getcwd
_NATIVE_STAT_ISLNK = stat.S_ISLNK
_NATIVE_STAT_ISDIR = stat.S_ISDIR
# Capturing Path.resolve does not capture its dynamic host and class hooks.
_RESOLVER_HOOK_NAMES = (
    "with_segments",
    # Native path joining happens after root resolution and during linked
    # ancestor checks; forged joins may still resolve inside the root.
    "joinpath",
    "__truediv__",
    "__itruediv__",
    "__new__",
    "__init__",
    "__getattribute__",
    "__fspath__",
    "__str__",
    "_str",
    "_raw_paths",
    "_parse_path",
    "_format_parsed_parts",
    "parents",
    "__eq__",
    "_str_normcase",
    "_str_normcase_cached",
    "_from_parsed_parts",
    "_from_parsed_string",
    "_tail",
    "_tail_cached",
    "_raw_path",
    "_drv",
    "_root",
    "drive",
    "root",
    "parser",
)
_NATIVE_RESOLVER_HOOKS = tuple(
    (
        path_class,
        tuple((name, path_class.__dict__.get(name)) for name in _RESOLVER_HOOK_NAMES),
    )
    for path_class in _NATIVE_PATH_TYPE.__mro__
    if issubclass(path_class, PurePath)
)
# Path.is_relative_to calls the mutable _PathParents membership sequence.
_NATIVE_PATH_PARENTS_TYPE = _NATIVE_TYPE(Path().parents)
_PARENT_SEQUENCE_HOOK_NAMES = (
    "__new__",
    "__init__",
    "__getattribute__",
    "__setattr__",
    "__contains__",
    "__iter__",
    "__getitem__",
    "__len__",
    "_path",
    "_drv",
    "_root",
    "_tail",
)
_NATIVE_PATH_PARENTS_HOOKS = tuple(
    (
        parent_class,
        tuple(
            (name, parent_class.__dict__.get(name))
            for name in _PARENT_SEQUENCE_HOOK_NAMES
        ),
    )
    for parent_class in _NATIVE_PATH_PARENTS_TYPE.__mro__
    if parent_class is not object
)
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_PARENT = cast("Callable[[Path], Path]", Path.parent.fget)
_NATIVE_PATH_NAME = cast("Callable[[Path], str]", Path.name.fget)
_NATIVE_PATH_JOINPATH = Path.joinpath
_NATIVE_IO_OPEN = io.open
_NATIVE_OS_MKDIR = os.mkdir
_NATIVE_FS_ENCODING = sys.getfilesystemencoding()
_NATIVE_FS_ERRORS = sys.getfilesystemencodeerrors()
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_IS_SYMLINK = S_ISLNK
# Cleanup must not use a consumer-replaced global filesystem helper.
_NATIVE_RMTREE = shutil.rmtree


def _require_native_resolution() -> None:
    """Fail closed on late filesystem or pathlib resolution hook changes."""
    if (
        os.path is not _NATIVE_OS_PATH_MODULE
        or os.path.realpath is not _NATIVE_OS_REALPATH
        or os.path.splitroot is not _NATIVE_OS_SPLITROOT
        or os.path.splitdrive is not _NATIVE_OS_SPLITDRIVE
        or os.path.join is not _NATIVE_OS_PATH_JOIN
        or os.path.sep is not _NATIVE_OS_PATH_SEP
        or os.path.altsep is not _NATIVE_OS_PATH_ALTSEP
        or builtins.bytes is not _NATIVE_BYTES
        or builtins.len is not _NATIVE_LEN
        or os.fspath is not _NATIVE_OS_FSPATH
        or os.lstat is not _NATIVE_OS_LSTAT
        or os.readlink is not _NATIVE_OS_READLINK
        or os.getcwd is not _NATIVE_OS_GETCWD
        or stat.S_ISLNK is not _NATIVE_STAT_ISLNK
        or stat.S_ISDIR is not _NATIVE_STAT_ISDIR
        or builtins.isinstance is not _NATIVE_ISINSTANCE
        or builtins.hasattr is not _NATIVE_HASATTR
        or pathlib.__dict__.get("_PathParents") is not _NATIVE_PATH_PARENTS_TYPE
        or _NATIVE_ANY(
            parent_class.__dict__.get(name) is not original
            for parent_class, hooks in _NATIVE_PATH_PARENTS_HOOKS
            for name, original in hooks
        )
        or _NATIVE_ANY(
            path_class.__dict__.get(name) is not original
            for path_class, hooks in _NATIVE_RESOLVER_HOOKS
            for name, original in hooks
        )
    ):
        message = "compatible path resolution hooks changed"
        raise CompatiblePlanError(message)


def _trusted_resolve(path: Path) -> Path:
    """Pin native resolver dependencies before and after resolving a path."""
    _require_native_resolution()
    result = _NATIVE_RESOLVE(path)
    _require_native_resolution()
    return result


def _native_path_lstat(path: Path) -> os.stat_result:
    # Avoid mutable pathlib and os delegation after policy callbacks run.
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat

Mapper = Callable[[str, bytes], MappedView | None]
Postcondition = Callable[[Path], bool]


class CompatiblePlanError(RuntimeError):
    """Raised when compatible planning or materialization cannot fail safely."""


class CompatibleFileKind(StrEnum):
    """Supported in-memory compatible file transformation forms."""

    COPY_CANDIDATE = "copy-candidate"
    SEMANTIC_PATCH = "semantic-patch"
    EXACT_GATED = "exact-gated"
    CREATE_LITERAL = "create-literal"


@dataclass(frozen=True, slots=True, order=True, init=False)
class CompatibleCorrectionBinding:
    """One named bug correction attached to one semantic edit index."""

    output_path: str
    edit_index: int
    correction_id: str

    def __init__(
        self, output_path: str, edit_index: int, correction_id: str
    ) -> None:
        """Validate correction routing with the captured original guard."""
        _CORRECTION_PATH_SLOT.__set__(self, output_path)
        _CORRECTION_INDEX_SLOT.__set__(self, edit_index)
        _CORRECTION_ID_SLOT.__set__(self, correction_id)
        _CORRECTION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require deterministic path, edit index, and correction identity.

        Raises:
            CompatiblePlanError: Correction metadata is malformed.

        """
        output_path = _CORRECTION_PATH_SLOT.__get__(self, CompatibleCorrectionBinding)
        edit_index = _CORRECTION_INDEX_SLOT.__get__(self, CompatibleCorrectionBinding)
        correction_id = _CORRECTION_ID_SLOT.__get__(self, CompatibleCorrectionBinding)
        if _NATIVE_TYPE(output_path) is not _NATIVE_STR:
            message = (
                "compatible correction path must use the exact string type"
            )
            raise CompatiblePlanError(message)
        _ = _validate_relative_path(output_path)
        if (
            _NATIVE_TYPE(edit_index) is not _NATIVE_INT
            or edit_index < 0
        ):
            message = "compatible correction edit index must be non-negative"
            raise CompatiblePlanError(message)
        if (
            _NATIVE_TYPE(correction_id) is not _NATIVE_STR
            or not correction_id
        ):
            message = "compatible correction ID must be a non-empty string"
            raise CompatiblePlanError(message)


# Capture original admission and slot readers before consumer class hooks.
_CORRECTION_VALIDATOR = cast(
    "Callable[[CompatibleCorrectionBinding], None]",
    CompatibleCorrectionBinding.__dict__["__post_init__"],
)
_CORRECTION_PATH_SLOT = cast(
    "MemberDescriptorType", CompatibleCorrectionBinding.__dict__["output_path"]
)
_CORRECTION_INDEX_SLOT = cast(
    "MemberDescriptorType", CompatibleCorrectionBinding.__dict__["edit_index"]
)
_CORRECTION_ID_SLOT = cast(
    "MemberDescriptorType", CompatibleCorrectionBinding.__dict__["correction_id"]
)


@dataclass(frozen=True, slots=True, init=False)
class CompatibleInstruction:
    """One target-path instruction for compatible authoring."""

    output_path: str
    kind: CompatibleFileKind
    source_path: str | None = None
    source_sha256: str | None = None
    semantic: SemanticAuthoringPlan | None = None
    exact: ExactInstruction | None = None
    literal: bytes | None = None
    correction_ids: tuple[str | None, ...] = ()

    def __init__(
        self,
        output_path: str,
        kind: CompatibleFileKind,
        source_path: str | None = None,
        source_sha256: str | None = None,
        semantic: SemanticAuthoringPlan | None = None,
        exact: ExactInstruction | None = None,
        literal: bytes | None = None,
        correction_ids: tuple[str | None, ...] = (),
    ) -> None:
        """Validate stored instruction values with the original guard."""
        for name, value in (
            ("output_path", output_path),
            ("kind", kind),
            ("source_path", source_path),
            ("source_sha256", source_sha256),
            ("semantic", semantic),
            ("exact", exact),
            ("literal", literal),
            ("correction_ids", correction_ids),
        ):
            _COMPATIBLE_RECORD_SLOT_MAP[_NATIVE_TYPE(self)][name].__set__(
                self, value
            )
        _INSTRUCTION_VALIDATOR(
            cast(
                "CompatibleInstruction",
                cast("object", _pinned_validation_view(self, CompatibleInstruction)),
            )
        )

    def __post_init__(self) -> None:
        """Reject incomplete instruction forms."""
        _validate_instruction(self)


@dataclass(frozen=True, slots=True, init=False)
class CompatibleBuildRequest:
    """Inputs required to author one in-memory compatible tree plan."""

    source_root: Path
    oracle_root: Path
    reference_identity: IdentityTree
    admission_policy: AdmissionPolicy
    mapper: Mapper
    preserve_candidate_only: bool = True

    def __init__(
        self,
        source_root: Path,
        oracle_root: Path,
        reference_identity: IdentityTree,
        admission_policy: AdmissionPolicy,
        mapper: Mapper,
        preserve_candidate_only: bool = True,
    ) -> None:
        """Validate stored build request values with the original guard."""
        for name, value in (
            ("source_root", source_root),
            ("oracle_root", oracle_root),
            ("reference_identity", reference_identity),
            ("admission_policy", admission_policy),
            ("mapper", mapper),
            ("preserve_candidate_only", preserve_candidate_only),
        ):
            _COMPATIBLE_RECORD_SLOT_MAP[_NATIVE_TYPE(self)][name].__set__(
                self, value
            )
        _BUILD_REQUEST_VALIDATOR(
            cast(
                "CompatibleBuildRequest",
                cast("object", _pinned_validation_view(self, CompatibleBuildRequest)),
            )
        )

    def __post_init__(self) -> None:
        """Reject malformed compatible authoring request envelopes."""
        _validate_build_request(self)


@dataclass(frozen=True, slots=True, init=False)
class CompatibleAuthoringPlan:
    """Non-distributable tree plan around admission and semantic placement."""

    source: TreeSnapshot
    target: TreeSnapshot
    reference_identity: IdentityTree
    admission_policy: AdmissionPolicy
    instructions: tuple[CompatibleInstruction, ...]
    preserve_candidate_only: bool = True

    def __init__(
        self,
        source: TreeSnapshot,
        target: TreeSnapshot,
        reference_identity: IdentityTree,
        admission_policy: AdmissionPolicy,
        instructions: tuple[CompatibleInstruction, ...],
        preserve_candidate_only: bool = True,
    ) -> None:
        """Validate stored plan values with the original guard."""
        for name, value in (
            ("source", source),
            ("target", target),
            ("reference_identity", reference_identity),
            ("admission_policy", admission_policy),
            ("instructions", instructions),
            ("preserve_candidate_only", preserve_candidate_only),
        ):
            _COMPATIBLE_RECORD_SLOT_MAP[_NATIVE_TYPE(self)][name].__set__(
                self, value
            )
        _AUTHORING_PLAN_VALIDATOR(
            cast(
                "CompatibleAuthoringPlan",
                cast("object", _pinned_validation_view(self, CompatibleAuthoringPlan)),
            )
        )

    def __post_init__(self) -> None:
        """Require one self-consistent immutable compatible authoring plan."""
        _validate_authoring_plan(self)


@dataclass(frozen=True, slots=True, init=False)
class CompatibleMaterializeRequest:
    """Candidate evidence and hooks for compatible materialization."""

    candidate_root: Path
    candidate_identity: IdentityTree
    behavior: BehaviorEvidence
    plan: CompatibleAuthoringPlan
    mapper: Mapper
    output_root: Path
    postcondition: Postcondition | None = None

    def __init__(
        self,
        candidate_root: Path,
        candidate_identity: IdentityTree,
        behavior: BehaviorEvidence,
        plan: CompatibleAuthoringPlan,
        mapper: Mapper,
        output_root: Path,
        postcondition: Postcondition | None = None,
    ) -> None:
        """Validate stored materialization values with the original guard."""
        for name, value in (
            ("candidate_root", candidate_root),
            ("candidate_identity", candidate_identity),
            ("behavior", behavior),
            ("plan", plan),
            ("mapper", mapper),
            ("output_root", output_root),
            ("postcondition", postcondition),
        ):
            _COMPATIBLE_RECORD_SLOT_MAP[_NATIVE_TYPE(self)][name].__set__(
                self, value
            )
        _MATERIALIZE_REQUEST_VALIDATOR(
            cast(
                "CompatibleMaterializeRequest",
                cast(
                    "object",
                    _pinned_validation_view(self, CompatibleMaterializeRequest),
                ),
            )
        )

    def __post_init__(self) -> None:
        """Reject malformed compatible materialization request envelopes."""
        _validate_materialize_request(self)


# Pinned constructor validators cannot be replaced by late class hooks.
_INSTRUCTION_VALIDATOR = cast(
    "Callable[[CompatibleInstruction], None]",
    CompatibleInstruction.__dict__["__post_init__"],
)
_BUILD_REQUEST_VALIDATOR = cast(
    "Callable[[CompatibleBuildRequest], None]",
    CompatibleBuildRequest.__dict__["__post_init__"],
)
_AUTHORING_PLAN_VALIDATOR = cast(
    "Callable[[CompatibleAuthoringPlan], None]",
    CompatibleAuthoringPlan.__dict__["__post_init__"],
)
_MATERIALIZE_REQUEST_VALIDATOR = cast(
    "Callable[[CompatibleMaterializeRequest], None]",
    CompatibleMaterializeRequest.__dict__["__post_init__"],
)


# Dataclass slot readers are immutable, unlike later class getters. The
# validation proxy is a short-lived internal view, never admitted as a record.
_COMPATIBLE_RECORD_SLOTS = {
    record_type: _NATIVE_TUPLE(
        (name, cast("MemberDescriptorType", record_type.__dict__[name]))
        for name in record_type.__dataclass_fields__
    )
    for record_type in (
        CompatibleInstruction,
        CompatibleBuildRequest,
        CompatibleAuthoringPlan,
        CompatibleMaterializeRequest,
    )
}


# Original slot writers avoid property-setter dispatch when consumers modify
# a record class before construction. The tuple readers above remain pinned
# for validation and later public provenance checks.
_COMPATIBLE_RECORD_SLOT_MAP = {
    record_type: dict(fields)
    for record_type, fields in _COMPATIBLE_RECORD_SLOTS.items()
}


def _pinned_validation_view(record: object, record_type: type) -> SimpleNamespace:
    """Read native slots, rejecting uninitialized records at admission."""
    try:
        return SimpleNamespace(
            **{
                name: descriptor.__get__(record, record_type)
                for name, descriptor in _COMPATIBLE_RECORD_SLOTS[record_type]
            }
        )
    except _NATIVE_ATTRIBUTE_ERROR as error:
        message = "compatible native record is missing required fields"
        raise CompatiblePlanError(message) from error


@dataclass(frozen=True, slots=True, init=False)
class _BuildContext:
    request: CompatibleBuildRequest
    exact: ExactAuthoringPlan
    source_records: dict[str, FileRecord]

    def __init__(
        self,
        request: CompatibleBuildRequest,
        exact: ExactAuthoringPlan,
        source_records: dict[str, FileRecord],
    ) -> None:
        """Keep internal authoring inputs independent of class setters."""
        _BUILD_CONTEXT_SLOTS["request"].__set__(self, request)
        _BUILD_CONTEXT_SLOTS["exact"].__set__(self, exact)
        _BUILD_CONTEXT_SLOTS["source_records"].__set__(self, source_records)


@dataclass(frozen=True, slots=True, init=False)
class _MaterializeContext:
    candidate_root: Path
    mapper: Mapper
    corrections_to_apply: frozenset[str]
    corrections_to_skip: frozenset[str]

    def __init__(
        self,
        candidate_root: Path,
        mapper: Mapper,
        corrections_to_apply: frozenset[str],
        corrections_to_skip: frozenset[str],
    ) -> None:
        """Keep admitted materialization inputs in original native slots."""
        _MATERIALIZE_CONTEXT_SLOTS["candidate_root"].__set__(self, candidate_root)
        _MATERIALIZE_CONTEXT_SLOTS["mapper"].__set__(self, mapper)
        _MATERIALIZE_CONTEXT_SLOTS["corrections_to_apply"].__set__(
            self, corrections_to_apply
        )
        _MATERIALIZE_CONTEXT_SLOTS["corrections_to_skip"].__set__(
            self, corrections_to_skip
        )


_BUILD_CONTEXT_SLOTS = {
    name: cast("MemberDescriptorType", _BuildContext.__dict__[name])
    for name in _BuildContext.__dataclass_fields__
}
_MATERIALIZE_CONTEXT_SLOTS = {
    name: cast("MemberDescriptorType", _MaterializeContext.__dict__[name])
    for name in _MaterializeContext.__dataclass_fields__
}


# Internal authoring and materialization receipts must not dispatch through
# mutable record-class constructors after a mapper or filesystem callback.
_COMPATIBLE_INSTRUCTION_INIT = cast(
    "Callable[[CompatibleInstruction, str, CompatibleFileKind, str | None, str | None, SemanticAuthoringPlan | None, ExactInstruction | None, bytes | None, tuple[str | None, ...]], None]",
    CompatibleInstruction.__dict__["__init__"],
)
_COMPATIBLE_PLAN_INIT = cast(
    "Callable[[CompatibleAuthoringPlan, TreeSnapshot, TreeSnapshot, IdentityTree, AdmissionPolicy, tuple[CompatibleInstruction, ...], bool], None]",
    CompatibleAuthoringPlan.__dict__["__init__"],
)
_BUILD_CONTEXT_INIT = cast(
    "Callable[[_BuildContext, CompatibleBuildRequest, ExactAuthoringPlan, dict[str, FileRecord]], None]",
    _BuildContext.__dict__["__init__"],
)
_MATERIALIZE_CONTEXT_INIT = cast(
    "Callable[[_MaterializeContext, Path, Mapper, frozenset[str], frozenset[str]], None]",
    _MaterializeContext.__dict__["__init__"],
)
_ROUTED_SEMANTIC_PLAN_INIT = cast(
    "Callable[[SemanticAuthoringPlan, tuple[SemanticEdit, ...]], None]",
    SemanticAuthoringPlan.__dict__["__init__"],
)


def _new_compatible_instruction(
    output_path: str,
    kind: CompatibleFileKind,
    source_path: str | None = None,
    source_sha256: str | None = None,
    semantic: SemanticAuthoringPlan | None = None,
    exact: ExactInstruction | None = None,
    literal: bytes | None = None,
    correction_ids: tuple[str | None, ...] = (),
) -> CompatibleInstruction:
    instruction = _NATIVE_OBJECT_NEW(CompatibleInstruction)
    _COMPATIBLE_INSTRUCTION_INIT(
        instruction,
        output_path,
        kind,
        source_path,
        source_sha256,
        semantic,
        exact,
        literal,
        correction_ids,
    )
    return instruction


def _new_compatible_plan(
    source: TreeSnapshot,
    target: TreeSnapshot,
    reference_identity: IdentityTree,
    admission_policy: AdmissionPolicy,
    instructions: tuple[CompatibleInstruction, ...],
    preserve_candidate_only: bool = True,
) -> CompatibleAuthoringPlan:
    plan = _NATIVE_OBJECT_NEW(CompatibleAuthoringPlan)
    _COMPATIBLE_PLAN_INIT(
        plan,
        source,
        target,
        reference_identity,
        admission_policy,
        instructions,
        preserve_candidate_only,
    )
    return plan


def _new_build_context(
    request: CompatibleBuildRequest,
    exact: ExactAuthoringPlan,
    source_records: dict[str, FileRecord],
) -> _BuildContext:
    context = _NATIVE_OBJECT_NEW(_BuildContext)
    _BUILD_CONTEXT_INIT(context, request, exact, source_records)
    return context


def _new_materialize_context(
    candidate_root: Path,
    mapper: Mapper,
    corrections_to_apply: frozenset[str],
    corrections_to_skip: frozenset[str],
) -> _MaterializeContext:
    context = _NATIVE_OBJECT_NEW(_MaterializeContext)
    _MATERIALIZE_CONTEXT_INIT(
        context, candidate_root, mapper, corrections_to_apply, corrections_to_skip
    )
    return context


def _new_routed_semantic_plan(
    edits: tuple[SemanticEdit, ...],
) -> SemanticAuthoringPlan:
    plan = _NATIVE_OBJECT_NEW(SemanticAuthoringPlan)
    _ROUTED_SEMANTIC_PLAN_INIT(plan, edits)
    return plan


def _build_request(context: _BuildContext) -> CompatibleBuildRequest:
    return cast(
        "CompatibleBuildRequest",
        _BUILD_CONTEXT_SLOTS["request"].__get__(context, _BuildContext),
    )


def _build_source_records(context: _BuildContext) -> dict[str, FileRecord]:
    return cast(
        "dict[str, FileRecord]",
        _BUILD_CONTEXT_SLOTS["source_records"].__get__(context, _BuildContext),
    )


def _materialize_candidate_root(context: _MaterializeContext) -> Path:
    return cast(
        "Path",
        _MATERIALIZE_CONTEXT_SLOTS["candidate_root"].__get__(
            context, _MaterializeContext
        ),
    )


def _materialize_mapper(context: _MaterializeContext) -> Mapper:
    return cast(
        "Mapper",
        _MATERIALIZE_CONTEXT_SLOTS["mapper"].__get__(context, _MaterializeContext),
    )


def _materialize_apply(context: _MaterializeContext) -> frozenset[str]:
    return cast(
        "frozenset[str]",
        _MATERIALIZE_CONTEXT_SLOTS["corrections_to_apply"].__get__(
            context, _MaterializeContext
        ),
    )


def _validate_request_path(value: object, context: str) -> None:
    # Request paths authorize both source reads and output publication.
    # Reject user-defined Path overrides before any conversion or resolution.
    if _NATIVE_TYPE(value) is not _NATIVE_PATH_TYPE:
        message = f"{context} must use exact pathlib Path"
        raise CompatiblePlanError(message)
    _require_native_resolution()
    raw = _NATIVE_PATH_STRING(value)
    if _NUL in raw:
        message = f"{context} path cannot contain NUL"
        raise CompatiblePlanError(message)
    try:
        _ = raw.encode("utf-8")
        _ = raw.encode(_NATIVE_FS_ENCODING, _NATIVE_FS_ERRORS)
    except (_NATIVE_UNICODE_ERROR, _NATIVE_TYPE_ERROR) as error:
        message = f"{context} path cannot be encoded"
        raise CompatiblePlanError(message) from error


def _resolve_request_root(path: Path, context: str) -> Path:
    try:
        resolved = _trusted_resolve(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"compatible {context} root resolution failed: {detail}"
        raise CompatiblePlanError(message) from error
    if _NATIVE_TYPE(resolved) is not _NATIVE_PATH_TYPE:
        message = f"compatible {context} root requires native resolved Path"
        raise CompatiblePlanError(message)
    return resolved


def _require_output_outside_candidate(
    request: CompatibleMaterializeRequest,
) -> None:
    candidate = _resolve_request_root(request.candidate_root, "candidate")
    output = _resolve_request_root(request.output_root, "output")
    _require_native_resolution()
    contained = _NATIVE_IS_RELATIVE_TO(output, candidate)
    _require_native_resolution()
    if contained:
        message = "compatible output root must remain outside candidate tree"
        raise CompatiblePlanError(message)


def _validate_mapper(value: object) -> None:
    if not _NATIVE_CALLABLE(value):
        message = "compatible mapper must be callable"
        raise CompatiblePlanError(message)


def _validate_build_request(request: CompatibleBuildRequest) -> None:
    _validate_request_path(request.source_root, "compatible source root")
    _validate_request_path(request.oracle_root, "compatible oracle root")
    if _NATIVE_TYPE(request.reference_identity) is not IdentityTree:
        message = "compatible reference identity must use exact IdentityTree"
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(request.admission_policy) is not AdmissionPolicy:
        message = "compatible admission policy must use exact AdmissionPolicy"
        raise CompatiblePlanError(message)
    _validate_mapper(request.mapper)
    if _NATIVE_TYPE(request.preserve_candidate_only) is not _NATIVE_BOOL:
        message = "compatible candidate-only policy must use an exact boolean"
        raise CompatiblePlanError(message)


def _validate_materialize_request(
    request: CompatibleMaterializeRequest,
) -> None:
    _validate_request_path(request.candidate_root, "compatible candidate root")
    _validate_request_path(request.output_root, "compatible output root")
    if _NATIVE_TYPE(request.candidate_identity) is not IdentityTree:
        message = "compatible candidate identity must use exact IdentityTree"
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(request.behavior) is not BehaviorEvidence:
        message = "compatible behavior evidence must use exact BehaviorEvidence"
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(request.plan) is not CompatibleAuthoringPlan:
        message = "compatible plan must use exact CompatibleAuthoringPlan"
        raise CompatiblePlanError(message)
    _validate_mapper(request.mapper)
    if request.postcondition is not None and not _NATIVE_CALLABLE(
        request.postcondition
    ):
        message = "compatible postcondition must be callable or None"
        raise CompatiblePlanError(message)


def _require_source(instruction: CompatibleInstruction) -> None:
    if instruction.source_path is None:
        message = "compatible source-backed instruction lost source path"
        raise CompatiblePlanError(message)


def _validate_copy(instruction: CompatibleInstruction) -> None:
    _require_source(instruction)
    if _NATIVE_ANY(
        value is not None
        for value in (
            instruction.source_sha256,
            instruction.semantic,
            instruction.exact,
            instruction.literal,
            instruction.correction_ids or None,
        )
    ):
        message = "compatible candidate copy carries unrelated payload evidence"
        raise CompatiblePlanError(message)


def _validate_semantic(instruction: CompatibleInstruction) -> None:
    _require_source(instruction)
    if instruction.semantic is None:
        message = "compatible semantic patch lost its semantic plan"
        raise CompatiblePlanError(message)
    # A native plan can bypass its constructor; validate even when no named
    # correction IDs are attached to this semantic patch.
    try:
        edits = read_semantic_plan(instruction.semantic)
    except _NATIVE_SEMANTIC_PLACEMENT_ERROR as error:
        message = "compatible semantic evidence is invalid"
        raise CompatiblePlanError(message) from error
    if instruction.correction_ids and _NATIVE_LEN(
        instruction.correction_ids
    ) != _NATIVE_LEN(edits):
        message = "compatible correction IDs must align with semantic edits"
        raise CompatiblePlanError(message)
    if _NATIVE_ANY(
        value is not None
        for value in (
            instruction.source_sha256,
            instruction.exact,
            instruction.literal,
        )
    ):
        message = "compatible semantic patch carries unrelated exact evidence"
        raise CompatiblePlanError(message)


def _validate_exact(instruction: CompatibleInstruction) -> None:
    _require_source(instruction)
    if instruction.exact is None or instruction.source_sha256 is None:
        message = "exact-gated compatible instruction is incomplete"
        raise CompatiblePlanError(message)
    if (
        instruction.semantic is not None
        or instruction.literal is not None
        or instruction.correction_ids
    ):
        message = "exact-gated instruction carries unrelated semantic evidence"
        raise CompatiblePlanError(message)


def _validate_literal(instruction: CompatibleInstruction) -> None:
    if instruction.literal is None or instruction.source_path is not None:
        message = "compatible literal creation has invalid source state"
        raise CompatiblePlanError(message)
    if _NATIVE_ANY(
        value is not None
        for value in (
            instruction.source_sha256,
            instruction.semantic,
            instruction.exact,
            instruction.correction_ids or None,
        )
    ):
        message = "compatible literal creation carries source-only evidence"
        raise CompatiblePlanError(message)


_INSTRUCTION_VALIDATORS = {
    CompatibleFileKind.COPY_CANDIDATE: _validate_copy,
    CompatibleFileKind.SEMANTIC_PATCH: _validate_semantic,
    CompatibleFileKind.EXACT_GATED: _validate_exact,
    CompatibleFileKind.CREATE_LITERAL: _validate_literal,
}


# jig-ignore-next-line: exact Ruff suppression is indivisible
def _validate_instruction_metadata(instruction: CompatibleInstruction) -> None:  # ruff: ignore[complex-structure, too-many-branches, too-many-statements] -- independent metadata invariants.
    if _NATIVE_TYPE(instruction.output_path) is not _NATIVE_STR:
        message = "compatible output path must use the exact string type"
        raise CompatiblePlanError(message)
    _ = _validate_relative_path(instruction.output_path)
    if _NATIVE_TYPE(instruction.kind) is not CompatibleFileKind:
        message = "compatible instruction kind must use the exact enum type"
        raise CompatiblePlanError(message)
    if instruction.source_path is not None:
        if _NATIVE_TYPE(instruction.source_path) is not _NATIVE_STR:
            message = "compatible source path must use the exact string type"
            raise CompatiblePlanError(message)
        _ = _validate_relative_path(instruction.source_path)
    if instruction.source_sha256 is not None:
        value = instruction.source_sha256
        if (
            _NATIVE_TYPE(value) is not _NATIVE_STR
            or _NATIVE_LEN(value) != _SHA256_BYTES * 2
            or _NATIVE_ANY(char not in _HEX_DIGITS for char in value)
        ):
            message = "compatible source sha256 must be 64 lowercase hex digits"
            raise CompatiblePlanError(message)
    if (
        instruction.semantic is not None
        and _NATIVE_TYPE(instruction.semantic) is not SemanticAuthoringPlan
    ):
        message = "compatible semantic evidence must use the exact plan type"
        raise CompatiblePlanError(message)
    if (
        instruction.exact is not None
        and _NATIVE_TYPE(instruction.exact) is not ExactInstruction
    ):
        message = (
            "compatible exact evidence must use the exact instruction type"
        )
        raise CompatiblePlanError(message)
    if (
        instruction.literal is not None
        and _NATIVE_TYPE(instruction.literal) is not _NATIVE_BYTES
    ):
        message = "compatible literal evidence must use exact bytes"
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(instruction.correction_ids) is not _NATIVE_TUPLE:
        message = "compatible correction IDs must use an immutable tuple"
        raise CompatiblePlanError(message)
    if _NATIVE_ANY(
        value is not None
        and (_NATIVE_TYPE(value) is not _NATIVE_STR or not value)
        for value in instruction.correction_ids
    ):
        message = "compatible correction IDs must be non-empty strings or None"
        raise CompatiblePlanError(message)


def _validate_instruction(instruction: CompatibleInstruction) -> None:
    _validate_instruction_metadata(instruction)
    validator = _INSTRUCTION_VALIDATORS.get(instruction.kind)
    if validator is None:
        message = f"unknown compatible instruction kind: {instruction.kind}"
        raise CompatiblePlanError(message)
    validator(instruction)


# jig-ignore-next-line: exact Ruff suppression is indivisible
def _validate_plan_records(plan: CompatibleAuthoringPlan) -> None:  # ruff: ignore[complex-structure] -- independent plan record invariants.
    if (
        _NATIVE_TYPE(plan.source) is not TreeSnapshot
        or _NATIVE_TYPE(plan.target) is not TreeSnapshot
    ):
        message = (
            "compatible plan snapshots must use exact TreeSnapshot records"
        )
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(plan.reference_identity) is not IdentityTree:
        message = (
            "compatible plan identity must use the exact IdentityTree type"
        )
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(plan.admission_policy) is not AdmissionPolicy:
        message = (
            "compatible plan policy must use the exact AdmissionPolicy type"
        )
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(plan.instructions) is not _NATIVE_TUPLE or _NATIVE_ANY(
        _NATIVE_TYPE(item) is not CompatibleInstruction
        for item in plan.instructions
    ):
        message = "compatible plan instructions must be exact immutable records"
        raise CompatiblePlanError(message)
    if _NATIVE_TYPE(plan.preserve_candidate_only) is not _NATIVE_BOOL:
        message = "compatible candidate-only policy must use an exact boolean"
        raise CompatiblePlanError(message)


def _validate_plan_topology(plan: CompatibleAuthoringPlan) -> None:
    target_paths = _NATIVE_TUPLE(record.path for record in plan.target.files)
    instruction_paths = _NATIVE_TUPLE(
        _original_instruction_view(item).output_path for item in plan.instructions
    )
    if instruction_paths != target_paths:
        message = "compatible plan instructions must exactly cover target paths"
        raise CompatiblePlanError(message)


def _source_record_for_instruction(
    instruction: CompatibleInstruction,
    source_records: dict[str, FileRecord],
) -> FileRecord | None:
    if instruction.source_path is None:
        return None
    record = source_records.get(instruction.source_path)
    if record is None:
        message = (
            "compatible instruction source path is absent from plan source"
        )
        raise CompatiblePlanError(message)
    return record


def _validate_exact_plan_binding(
    instruction: CompatibleInstruction,
    source_record: FileRecord | None,
    target_record: FileRecord,
) -> None:
    if instruction.kind is not CompatibleFileKind.EXACT_GATED:
        return
    if (
        source_record is None
        or instruction.source_sha256 != _file_fields(source_record)[1]
    ):
        message = "compatible exact gate does not match plan source hash"
        raise CompatiblePlanError(message)
    exact = instruction.exact
    if exact is None:
        message = "compatible exact gate does not match plan target evidence"
        raise CompatiblePlanError(message)
    output, _, expected, source, _, _ = _exact_instruction_fields(exact)
    if output != instruction.output_path or expected != _file_fields(target_record)[1]:
        message = "compatible exact gate does not match plan target evidence"
        raise CompatiblePlanError(message)
    if source is not None and source != instruction.source_path:
        message = "compatible exact gate source path differs from plan source"
        raise CompatiblePlanError(message)


def _validate_plan_instruction_binding(
    instruction: CompatibleInstruction,
    source_records: dict[str, FileRecord],
    target_records: dict[str, FileRecord],
) -> None:
    source_record = _source_record_for_instruction(instruction, source_records)
    target_record = target_records[instruction.output_path]
    _validate_exact_plan_binding(instruction, source_record, target_record)
    if instruction.kind is CompatibleFileKind.CREATE_LITERAL and (
        instruction.literal is None
        or _sha256(instruction.literal) != target_record.sha256
    ):
        message = "compatible literal does not match plan target snapshot"
        raise CompatiblePlanError(message)


def _validate_authoring_plan(plan: CompatibleAuthoringPlan) -> None:
    _validate_plan_records(plan)
    # An exact native child may be allocated without its constructor; the
    # outer plan's exact-type check does not authenticate its stored metadata.
    for instruction in plan.instructions:
        _INSTRUCTION_VALIDATOR(_original_instruction_view(instruction))
    _validate_plan_topology(plan)
    source_records = {record.path: record for record in plan.source.files}
    target_records = {record.path: record for record in plan.target.files}
    for instruction in plan.instructions:
        _validate_plan_instruction_binding(
            _original_instruction_view(instruction),
            source_records,
            target_records,
        )


def _normalized_correction_ids(
    instruction: CompatibleInstruction,
) -> tuple[str | None, ...]:
    if instruction.semantic is None:
        return ()
    if instruction.correction_ids:
        return instruction.correction_ids
    return (None,) * _NATIVE_LEN(read_semantic_plan(instruction.semantic))


def _validate_correction_bindings(
    bindings: object,
) -> tuple[CompatibleCorrectionBinding, ...]:
    if _NATIVE_TYPE(bindings) is not _NATIVE_TUPLE:
        message = "compatible correction bindings must use an immutable tuple"
        raise CompatiblePlanError(message)
    items = cast("tuple[object, ...]", bindings)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not CompatibleCorrectionBinding for item in items
    ):
        message = "compatible correction bindings contain a foreign record"
        raise CompatiblePlanError(message)
    try:
        for item in cast("tuple[CompatibleCorrectionBinding, ...]", bindings):
            _CORRECTION_VALIDATOR(item)
        admitted = _NATIVE_TUPLE(
            _original_correction_view(item)
            for item in cast("tuple[CompatibleCorrectionBinding, ...]", bindings)
        )
    except _NATIVE_ATTRIBUTE_ERROR as error:
        message = "compatible correction binding is missing native fields"
        raise CompatiblePlanError(message) from error
    locations = _NATIVE_TUPLE(
        (item.output_path, item.edit_index) for item in admitted
    )
    if locations != _NATIVE_TUPLE(_NATIVE_SORTED(locations)):
        message = (
            "compatible correction bindings must be sorted by edit location"
        )
        raise CompatiblePlanError(message)
    if _NATIVE_LEN(locations) != _NATIVE_LEN(_NATIVE_SET(locations)):
        message = (
            "compatible correction bindings must use unique edit locations"
        )
        raise CompatiblePlanError(message)
    return admitted


def _apply_correction_binding(
    correction_ids: list[str | None], binding: CompatibleCorrectionBinding
) -> None:
    if binding.edit_index >= _NATIVE_LEN(correction_ids):
        message = "compatible correction edit index exceeds semantic plan"
        raise CompatiblePlanError(message)
    existing = correction_ids[binding.edit_index]
    if existing is not None and existing != binding.correction_id:
        message = "compatible semantic edit already has another correction ID"
        raise CompatiblePlanError(message)
    correction_ids[binding.edit_index] = binding.correction_id


def _bind_instruction_corrections(
    instruction: CompatibleInstruction,
    bindings: tuple[CompatibleCorrectionBinding, ...],
) -> CompatibleInstruction:
    if not bindings:
        return instruction
    fields = _original_instruction_view(instruction)
    if fields.semantic is None:
        message = (
            "compatible correction binding requires a semantic instruction"
        )
        raise CompatiblePlanError(message)
    correction_ids = _NATIVE_LIST(_normalized_correction_ids(fields))
    for binding in bindings:
        _apply_correction_binding(correction_ids, binding)
    return _new_compatible_instruction(
        output_path=fields.output_path,
        kind=fields.kind,
        source_path=fields.source_path,
        source_sha256=fields.source_sha256,
        semantic=fields.semantic,
        exact=fields.exact,
        literal=fields.literal,
        correction_ids=_NATIVE_TUPLE(correction_ids),
    )


def bind_compatible_corrections(
    plan: CompatibleAuthoringPlan,
    bindings: tuple[CompatibleCorrectionBinding, ...],
) -> CompatibleAuthoringPlan:
    """Attach named behavior corrections to deterministic semantic edit indexes.

    Returns:
        A new compatible authoring plan with correction IDs aligned to edits.

    Raises:
        CompatiblePlanError: Plan or correction metadata is invalid.

    """
    if _NATIVE_TYPE(plan) is not CompatibleAuthoringPlan:
        message = "compatible correction binding requires the exact plan type"
        raise CompatiblePlanError(message)
    fields = cast(
        "CompatibleAuthoringPlan",
        cast("object", _pinned_validation_view(plan, CompatibleAuthoringPlan)),
    )
    _AUTHORING_PLAN_VALIDATOR(fields)
    admitted = _validate_correction_bindings(bindings)
    by_path: dict[str, list[CompatibleCorrectionBinding]] = {}
    for binding in admitted:
        by_path.setdefault(binding.output_path, []).append(binding)
    instruction_views = _NATIVE_TUPLE(
        (item, _original_instruction_view(item)) for item in fields.instructions
    )
    known_paths = {view.output_path for _, view in instruction_views}
    if _NATIVE_SET(by_path) - known_paths:
        message = "compatible correction binding targets an unknown output path"
        raise CompatiblePlanError(message)
    instructions = _NATIVE_TUPLE(
        _bind_instruction_corrections(
            item, _NATIVE_TUPLE(by_path.get(view.output_path, ()))
        )
        for item, view in instruction_views
    )
    return _new_compatible_plan(
        source=fields.source,
        target=fields.target,
        reference_identity=fields.reference_identity,
        admission_policy=fields.admission_policy,
        instructions=instructions,
        preserve_candidate_only=fields.preserve_candidate_only,
    )


def _record_map(snapshot: TreeSnapshot) -> dict[str, FileRecord]:
    return {record.path: record for record in snapshot.files}


def _validate_relative_path(relative_path: str) -> str:
    # Native string components are the path authority. PurePath delegates to
    # mutable class and parser hooks that domain callbacks can replace.
    unsafe = (
        not relative_path
        or _NUL in relative_path
        or _NATIVE_ANY(
            component in ("", ".", "..")
            or reserved_windows_component(component)
            for component in relative_path.split("/")
        )
    )
    if unsafe:
        message = f"unsafe compatible tree path: {relative_path!r}"
        raise CompatiblePlanError(message)
    try:
        _ = relative_path.encode("utf-8")
    except _NATIVE_UNICODE_ERROR as error:
        message = f"unsafe compatible tree path: {relative_path!r}"
        raise CompatiblePlanError(message) from error
    return relative_path


def _is_linked_ancestor(path: Path, status: os.stat_result) -> bool:
    try:
        if _NATIVE_IS_SYMLINK(status.st_mode):
            return True
        junction = _NATIVE_IS_JUNCTION(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"ancestor inspection failed: {path}: {detail}"
        raise CompatiblePlanError(message) from error
    if _NATIVE_TYPE(junction) is not _NATIVE_BOOL:
        message = "ancestor inspection requires native boolean"
        raise CompatiblePlanError(message)
    return junction


def _reject_linked_ancestors(root: Path, relative_path: str) -> None:
    current = root
    for component in relative_path.split("/")[:-1]:
        # A previous status call may have mutated class hooks between steps.
        _require_native_resolution()
        current /= component
        _require_native_resolution()
        status = _path_status(current, "compatible path ancestor")
        if status is not None and _is_linked_ancestor(current, status):
            message = (
                f"compatible linked path component is unsupported: {current}"
            )
            raise CompatiblePlanError(message)
    _require_native_resolution()


def _safe_path(root: Path, relative_path: str) -> Path:
    normalized = _validate_relative_path(relative_path)
    _require_native_resolution()
    path = root.joinpath(*normalized.split("/"))
    try:
        resolved_path = _trusted_resolve(path)
        resolved_root = _trusted_resolve(root)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = (
            f"compatible path resolution failed: {relative_path!r}: {detail}"
        )
        raise CompatiblePlanError(message) from error
    try:
        _ = _NATIVE_RELATIVE_TO(resolved_path, resolved_root)
    except _NATIVE_VALUE_ERROR as error:
        message = f"compatible path escapes tree root: {relative_path!r}"
        raise CompatiblePlanError(message) from error
    _reject_linked_ancestors(root, normalized)
    return path


def _path_status(path: Path, context: str) -> os.stat_result | None:
    try:
        status = _NATIVE_PATH_LSTAT(path)
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        return None
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"{context} status failed: {path}: {detail}"
        raise CompatiblePlanError(message) from error
    if _NATIVE_TYPE(status) is not _NATIVE_STAT_RESULT:
        message = f"{context} requires native filesystem status: {path}"
        raise CompatiblePlanError(message)
    return status


def _path_present(path: Path, context: str) -> bool:
    return _path_status(path, context) is not None


def _read_compatible_bytes(path: Path, context: str) -> bytes:
    try:
        return read_exact_regular_file(path, context)
    except _NATIVE_EXACT_TREE_ERROR as error:
        detail = _safe_compatible_error_detail(error)
        message = f"{context} read failed: {path}: {detail}"
        failure = CompatiblePlanError(message)
        if _NATIVE_TYPE(error) is _NATIVE_EXACT_TREE_ERROR:
            # Native note access bypasses late exact-error class getters.
            try:
                notes = cast(
                    "object",
                    BaseException.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
                        error, "__notes__"
                    ),
                )
            except _NATIVE_ATTRIBUTE_ERROR:
                notes = None
            if _NATIVE_TYPE(notes) is _NATIVE_LIST:
                for note in cast("list[object]", notes):
                    if _NATIVE_TYPE(note) is _NATIVE_STR:
                        BaseException.add_note(failure, note)
        raise failure from error


def _native_write_compatible_bytes(path: Path, data: bytes) -> int:
    """Exclusively create staged bytes without late Path/io.open hooks."""
    with _NATIVE_IO_OPEN(_NATIVE_PATH_STRING(path), "xb") as stream:
        return stream.write(data)


_NATIVE_WRITE_COMPATIBLE_BYTES = _native_write_compatible_bytes


def _native_make_compatible_directory(
    path: Path, *, parents: bool, exist_ok: bool
) -> None:
    """Create compatible directories without mutable pathlib/os.mkdir hooks."""
    try:
        _NATIVE_OS_MKDIR(_NATIVE_PATH_STRING(path))
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        parent = _NATIVE_PATH_PARENT(path)
        if not parents or _NATIVE_PATH_STRING(parent) == _NATIVE_PATH_STRING(path):
            raise
        _native_make_compatible_directory(parent, parents=True, exist_ok=True)
        _native_make_compatible_directory(path, parents=False, exist_ok=exist_ok)
    except _NATIVE_FILE_EXISTS_ERROR:
        if not exist_ok:
            raise
        status = _path_status(path, "compatible directory")
        if (
            status is None
            or not S_ISDIR(status.st_mode)
            or _is_linked_ancestor(path, status)
        ):
            raise


def _write_compatible_bytes(path: Path, data: bytes, context: str) -> None:
    try:
        _native_make_compatible_directory(
            _NATIVE_PATH_PARENT(path), parents=True, exist_ok=True
        )
        written = _NATIVE_WRITE_COMPATIBLE_BYTES(path, data)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"{context} write failed: {path}: {detail}"
        raise CompatiblePlanError(message) from error
    if _NATIVE_TYPE(written) is not _NATIVE_INT or written != _NATIVE_LEN(data):
        message = f"{context} short or invalid byte count: {path}"
        raise CompatiblePlanError(message)


def _make_compatible_directory(
    path: Path,
    context: str,
    *,
    parents: bool,
    exist_ok: bool,
) -> None:
    try:
        _native_make_compatible_directory(path, parents=parents, exist_ok=exist_ok)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"{context} creation failed: {path}: {detail}"
        raise CompatiblePlanError(message) from error


def _tree_bytes(root: Path, relative_path: str) -> bytes:
    path = _safe_path(root, relative_path)
    return _read_compatible_bytes(path, "compatible tree file")


def _map_compatible_file(
    mapper: Mapper,
    path: str,
    data: bytes,
) -> MappedView | None:
    try:
        view = mapper(path, data)
    except _NATIVE_EXCEPTION as error:
        # Preserve the callback cause without evaluating a foreign __str__.
        message = f"compatible mapper failed for {path!r}"
        raise CompatiblePlanError(message) from error
    if view is not None and _NATIVE_TYPE(view) is not MappedView:
        message = "compatible mapper must return exact MappedView or None"
        raise CompatiblePlanError(message)
    return view


def _source_path(
    instruction: ExactInstruction,
    source_records: dict[str, FileRecord],
) -> str | None:
    if instruction.source_path is not None:
        return instruction.source_path
    if instruction.output_path in source_records:
        return instruction.output_path
    return None


def _mapped_pair(
    context: _BuildContext,
    instruction: ExactInstruction,
    source_path: str,
) -> tuple[MappedView, MappedView] | None:
    source_bytes = _tree_bytes(_build_request(context).source_root, source_path)
    target_bytes = _tree_bytes(
        _build_request(context).oracle_root,
        instruction.output_path,
    )
    source_view = _map_compatible_file(
        _build_request(context).mapper, source_path, source_bytes
    )
    target_view = _map_compatible_file(
        _build_request(context).mapper, instruction.output_path, target_bytes
    )
    if (source_view is None) != (target_view is None):
        message = "compatible mapper disagrees between source and target file"
        raise CompatiblePlanError(message)
    if source_view is None or target_view is None:
        return None
    return source_view, target_view


def _literal_instruction(
    context: _BuildContext,
    instruction: ExactInstruction,
) -> CompatibleInstruction:
    return _new_compatible_instruction(
        output_path=instruction.output_path,
        kind=CompatibleFileKind.CREATE_LITERAL,
        literal=_tree_bytes(
            _build_request(context).oracle_root,
            instruction.output_path,
        ),
    )


def _mapped_instruction(
    instruction: ExactInstruction,
    source_path: str,
    mapped: tuple[MappedView, MappedView],
) -> CompatibleInstruction:
    semantic = build_semantic_plan(*mapped)
    if not read_semantic_plan(semantic):
        return _new_compatible_instruction(
            output_path=instruction.output_path,
            kind=CompatibleFileKind.COPY_CANDIDATE,
            source_path=source_path,
        )
    return _new_compatible_instruction(
        output_path=instruction.output_path,
        kind=CompatibleFileKind.SEMANTIC_PATCH,
        source_path=source_path,
        semantic=semantic,
    )


def _exact_instruction(
    context: _BuildContext,
    instruction: ExactInstruction,
    source_path: str,
) -> CompatibleInstruction:
    record = _build_source_records(context)[source_path]
    return _new_compatible_instruction(
        output_path=instruction.output_path,
        kind=CompatibleFileKind.EXACT_GATED,
        source_path=source_path,
        source_sha256=record.sha256,
        exact=instruction,
    )


def _compatible_instruction(
    context: _BuildContext,
    instruction: ExactInstruction,
) -> CompatibleInstruction:
    source_path = _source_path(instruction, _build_source_records(context))
    if source_path is None:
        return _literal_instruction(context, instruction)
    mapped = _mapped_pair(context, instruction, source_path)
    if mapped is not None:
        return _mapped_instruction(instruction, source_path, mapped)
    return _exact_instruction(context, instruction, source_path)


def _original_instruction_view(
    instruction: CompatibleInstruction,
) -> CompatibleInstruction:
    return cast(
        "CompatibleInstruction",
        cast("object", _pinned_validation_view(instruction, CompatibleInstruction)),
    )


def _original_correction_view(
    binding: CompatibleCorrectionBinding,
) -> CompatibleCorrectionBinding:
    return cast(
        "CompatibleCorrectionBinding",
        cast(
            "object",
            SimpleNamespace(
                output_path=_CORRECTION_PATH_SLOT.__get__(
                    binding, CompatibleCorrectionBinding
                ),
                edit_index=_CORRECTION_INDEX_SLOT.__get__(
                    binding, CompatibleCorrectionBinding
                ),
                correction_id=_CORRECTION_ID_SLOT.__get__(
                    binding, CompatibleCorrectionBinding
                ),
            ),
        ),
    )


def _admitted_plan_view(plan: CompatibleAuthoringPlan) -> CompatibleAuthoringPlan:
    """Freeze the admitted plan and instruction slots for one replay."""
    view = _pinned_validation_view(plan, CompatibleAuthoringPlan)
    original_instructions = cast(
        "tuple[CompatibleInstruction, ...]", view.instructions
    )
    if _NATIVE_TYPE(original_instructions) is not _NATIVE_TUPLE:
        message = "compatible plan instructions must use an immutable tuple"
        raise CompatiblePlanError(message)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not CompatibleInstruction
        for item in original_instructions
    ):
        message = "compatible plan instructions must be exact immutable records"
        raise CompatiblePlanError(message)
    _AUTHORING_PLAN_VALIDATOR(
        cast("CompatibleAuthoringPlan", cast("object", view))
    )
    view.instructions = _NATIVE_TUPLE(
        cast(
            "CompatibleInstruction",
            cast("object", _pinned_validation_view(item, CompatibleInstruction)),
        )
        for item in original_instructions
    )
    return cast("CompatibleAuthoringPlan", cast("object", view))


def _admitted_materialize_view(
    request: CompatibleMaterializeRequest,
) -> CompatibleMaterializeRequest:
    """Freeze original request and nested plan values before callbacks."""
    view = _pinned_validation_view(request, CompatibleMaterializeRequest)
    _MATERIALIZE_REQUEST_VALIDATOR(
        cast("CompatibleMaterializeRequest", cast("object", view))
    )
    plan = cast("CompatibleAuthoringPlan", view.plan)
    if _NATIVE_TYPE(plan) is not CompatibleAuthoringPlan:
        message = "compatible plan must use exact CompatibleAuthoringPlan"
        raise CompatiblePlanError(message)
    view.plan = _admitted_plan_view(plan)
    return cast("CompatibleMaterializeRequest", cast("object", view))


def _require_build_request(value: object) -> CompatibleBuildRequest:
    if _NATIVE_TYPE(value) is not CompatibleBuildRequest:
        message = "compatible authoring requires exact CompatibleBuildRequest"
        raise CompatiblePlanError(message)
    admitted = cast(
        "CompatibleBuildRequest",
        cast("object", _pinned_validation_view(value, CompatibleBuildRequest)),
    )
    _BUILD_REQUEST_VALIDATOR(admitted)
    return admitted


def _require_materialize_request(
    value: object,
) -> CompatibleMaterializeRequest:
    if _NATIVE_TYPE(value) is not CompatibleMaterializeRequest:
        message = (
            "compatible materialization requires exact "
            "CompatibleMaterializeRequest"
        )
        raise CompatiblePlanError(message)
    return _admitted_materialize_view(value)


def build_compatible_plan(
    request: CompatibleBuildRequest,
) -> CompatibleAuthoringPlan:
    """Build an in-memory compatible tree plan from local source and oracle.

    Returns:
        Plan combining target topology, semantic placement, and conservative
        exact gates for unmapped files.

    """
    request = _require_build_request(request)
    exact = build_exact_plan(request.source_root, request.oracle_root)
    # Consumer mappers run during instruction construction and can replace
    # ExactAuthoringPlan class getters. Keep the admitted original snapshots
    # and instructions for both drift checks and returned plan provenance.
    planned_source, planned_target, planned_instructions, _ = _plan_fields(exact)
    context = _new_build_context(
        request=request,
        exact=exact,
        source_records=_record_map(planned_source),
    )
    instructions = _NATIVE_TUPLE(
        _compatible_instruction(context, instruction)
        for instruction in planned_instructions
    )
    _require_tree_unchanged(
        request.source_root, planned_source, "source", phase="authoring"
    )
    _require_tree_unchanged(
        request.oracle_root, planned_target, "target", phase="authoring"
    )
    return _new_compatible_plan(
        source=planned_source,
        target=planned_target,
        reference_identity=request.reference_identity,
        admission_policy=request.admission_policy,
        instructions=instructions,
        preserve_candidate_only=request.preserve_candidate_only,
    )


def _sha256(data: bytes) -> str:
    return _SHA256_FACTORY(data).hexdigest()


def _exact_literal(instruction: ExactInstruction) -> bytes:
    literal = _exact_instruction_fields(instruction)[4]
    if literal is None:
        message = "exact-gated literal lost target bytes"
        raise CompatiblePlanError(message)
    return literal


def _exact_patch(candidate: bytes, instruction: ExactInstruction) -> bytes:
    parts: list[bytes] = []
    for segment in _exact_instruction_fields(instruction)[5]:
        if _NATIVE_TYPE(segment) is OracleLiteral:
            parts.append(_oracle_literal_data(cast("OracleLiteral", segment)))
            continue
        if _NATIVE_TYPE(segment) is not SourceSlice:
            message = "exact-gated patch contains foreign segment"
            raise CompatiblePlanError(message)
        offset, length = _source_slice_fields(cast("SourceSlice", segment))
        end = offset + length
        if end > _NATIVE_LEN(candidate):
            message = "exact-gated source slice exceeds candidate file"
            raise CompatiblePlanError(message)
        parts.append(candidate[offset:end])
    return b"".join(parts)


def _exact_bytes(candidate: bytes, instruction: ExactInstruction) -> bytes:
    kind = _exact_instruction_fields(instruction)[1]
    if kind is ExactInstructionKind.COPY_SOURCE:
        return candidate
    if kind is ExactInstructionKind.LITERAL_ORACLE:
        return _exact_literal(instruction)
    if kind is not ExactInstructionKind.PATCH_SOURCE:
        message = "exact-gated instruction has unsupported kind"
        raise CompatiblePlanError(message)
    return _exact_patch(candidate, instruction)


def _require_mapped(mapper: Mapper, path: str, data: bytes) -> MappedView:
    view = _map_compatible_file(mapper, path, data)
    if view is None:
        message = "compatible output lost required semantic mapper support"
        raise CompatiblePlanError(message)
    return view


def _candidate_bytes(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    if instruction.source_path is None:
        message = "compatible instruction lost candidate source path"
        raise CompatiblePlanError(message)
    return _tree_bytes(_materialize_candidate_root(context), instruction.source_path)


def _materialize_copy(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    return _candidate_bytes(context, instruction)


def _routed_semantic_plan(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> SemanticAuthoringPlan:
    if instruction.semantic is None:
        message = "compatible semantic instruction lost its authoring plan"
        raise CompatiblePlanError(message)
    edits = _NATIVE_TUPLE(
        edit
        for edit, correction_id in _NATIVE_ZIP(
            read_semantic_plan(instruction.semantic),
            _normalized_correction_ids(instruction),
            strict=True,
        )
        if correction_id is None or correction_id in _materialize_apply(context)
    )
    return _new_routed_semantic_plan(edits)


def _materialize_semantic(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    candidate = _candidate_bytes(context, instruction)
    if instruction.source_path is None or instruction.semantic is None:
        message = "compatible semantic instruction is incomplete"
        raise CompatiblePlanError(message)
    view = _require_mapped(
        _materialize_mapper(context), instruction.source_path, candidate
    )
    return apply_semantic_plan(
        view,
        _routed_semantic_plan(context, instruction),
        lambda data: _require_mapped(
            _materialize_mapper(context),
            instruction.output_path,
            data,
        ),
    )


def _materialize_exact(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    candidate = _candidate_bytes(context, instruction)
    if instruction.exact is None or instruction.source_sha256 is None:
        message = "compatible exact-gated instruction is incomplete"
        raise CompatiblePlanError(message)
    if _sha256(candidate) != instruction.source_sha256:
        message = "opaque compatible source changed beyond exact-gated support"
        raise CompatiblePlanError(message)
    transformed = _exact_bytes(candidate, instruction.exact)
    if _sha256(transformed) != _exact_instruction_fields(instruction.exact)[2]:
        message = "compatible exact-gated output differs from target snapshot"
        raise CompatiblePlanError(message)
    return transformed


def _materialize_literal(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    _ = context
    if instruction.literal is None:
        message = "compatible target creation lost literal bytes"
        raise CompatiblePlanError(message)
    return instruction.literal


_MATERIALIZERS = {
    CompatibleFileKind.COPY_CANDIDATE: _materialize_copy,
    CompatibleFileKind.SEMANTIC_PATCH: _materialize_semantic,
    CompatibleFileKind.EXACT_GATED: _materialize_exact,
    CompatibleFileKind.CREATE_LITERAL: _materialize_literal,
}


def _instruction_bytes(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    materializer = _MATERIALIZERS.get(instruction.kind)
    if materializer is None:
        message = f"unknown compatible materializer: {instruction.kind}"
        raise CompatiblePlanError(message)
    return materializer(context, instruction)


def _prepare_staging(output_root: Path) -> Path:
    if _path_present(output_root, "compatible output root"):
        message = f"compatible output root already exists: {output_root}"
        raise CompatiblePlanError(message)
    staging = _NATIVE_PATH_JOINPATH(
        _NATIVE_PATH_PARENT(output_root),
        f".{_NATIVE_PATH_NAME(output_root)}{_STAGING_SUFFIX}",
    )
    if _path_present(staging, "compatible staging root"):
        message = f"compatible staging root already exists: {staging}"
        raise CompatiblePlanError(message)
    _make_compatible_directory(
        staging,
        "compatible staging root",
        parents=True,
        exist_ok=False,
    )
    return staging


def _target_paths(plan: CompatibleAuthoringPlan) -> frozenset[str]:
    return _NATIVE_FROZENSET(item.output_path for item in plan.instructions)


def _source_paths(plan: CompatibleAuthoringPlan) -> frozenset[str]:
    return _NATIVE_FROZENSET(item.path for item in plan.source.files)


def _candidate_only_paths(
    candidate: TreeSnapshot,
    plan: CompatibleAuthoringPlan,
) -> tuple[str, ...]:
    if not plan.preserve_candidate_only:
        return ()
    source_paths = _source_paths(plan)
    target_paths = _target_paths(plan)
    return _NATIVE_TUPLE(
        record.path
        for record in candidate.files
        if record.path not in source_paths and record.path not in target_paths
    )


def _copy_candidate_only(
    candidate_root: Path,
    staging: Path,
    paths: tuple[str, ...],
) -> None:
    for path in paths:
        source = _safe_path(candidate_root, path)
        output = _safe_path(staging, path)
        data = _read_compatible_bytes(source, "candidate-only source")
        _write_compatible_bytes(output, data, "candidate-only output")


def _require_literal_conflict_absent(
    request: CompatibleMaterializeRequest,
    candidate_paths: frozenset[str],
    instruction: CompatibleInstruction,
) -> None:
    conflict_candidate = (
        instruction.kind is CompatibleFileKind.CREATE_LITERAL
        and instruction.output_path in candidate_paths
    )
    if not conflict_candidate:
        return
    if instruction.literal is None:
        message = "compatible literal conflict check lost target bytes"
        raise CompatiblePlanError(message)
    existing = _tree_bytes(request.candidate_root, instruction.output_path)
    if existing != instruction.literal:
        message = (
            "candidate-added file conflicts with required target-only path"
        )
        raise CompatiblePlanError(message)


def _require_literal_conflicts_absent(
    request: CompatibleMaterializeRequest,
    candidate_paths: frozenset[str],
) -> None:
    for instruction in request.plan.instructions:
        _require_literal_conflict_absent(request, candidate_paths, instruction)


def _plan_correction_ids(
    plan: CompatibleAuthoringPlan,
) -> frozenset[str]:
    return _NATIVE_FROZENSET(
        correction_id
        for instruction in plan.instructions
        for correction_id in _normalized_correction_ids(instruction)
        if correction_id is not None
    )


def _require_correction_routes(
    plan: CompatibleAuthoringPlan,
    behavior: BehaviorEvidence,
) -> None:
    attached = _plan_correction_ids(plan)
    routed = _NATIVE_FROZENSET((
        *behavior.corrections_to_apply,
        *behavior.corrections_to_skip,
    ))
    if routed - attached:
        message = "behavior routes an unbound compatible correction ID"
        raise CompatiblePlanError(message)
    if attached - routed:
        message = "compatible correction binding lacks a behavior route"
        raise CompatiblePlanError(message)


def _populate_staging(
    request: CompatibleMaterializeRequest,
    candidate: TreeSnapshot,
    staging: Path,
) -> None:
    context = _new_materialize_context(
        candidate_root=request.candidate_root,
        mapper=request.mapper,
        corrections_to_apply=_NATIVE_FROZENSET(
            request.behavior.corrections_to_apply
        ),
        corrections_to_skip=_NATIVE_FROZENSET(
            request.behavior.corrections_to_skip
        ),
    )
    for instruction in request.plan.instructions:
        data = _instruction_bytes(context, instruction)
        output = _safe_path(staging, instruction.output_path)
        _write_compatible_bytes(output, data, "compatible instruction output")
    _copy_candidate_only(
        request.candidate_root,
        staging,
        _candidate_only_paths(candidate, request.plan),
    )


def _require_postcondition(
    postcondition: Postcondition | None,
    staging: Path,
) -> None:
    if postcondition is None:
        return
    try:
        accepted = postcondition(staging)
    except _NATIVE_EXCEPTION as error:
        # A consumer callback may supply a hostile exception formatter.
        message = "compatible output postcondition failed"
        raise CompatiblePlanError(message) from error
    if _NATIVE_TYPE(accepted) is not _NATIVE_BOOL:
        message = "compatible output postcondition must return an exact boolean"
        raise CompatiblePlanError(message)
    if not accepted:
        message = "compatible output postcondition rejected staging tree"
        raise CompatiblePlanError(message)


def _admit(request: CompatibleMaterializeRequest) -> TransformAdmissionEvidence:
    source_evidence = evaluate_admission(
        request.plan.reference_identity,
        request.candidate_identity,
        request.plan.admission_policy,
    )
    return require_transform_admission(source_evidence, request.behavior)


def _snapshot_compatible_tree(root: Path, context: str) -> TreeSnapshot:
    try:
        return snapshot_tree(root)
    except _NATIVE_EXACT_TREE_ERROR as error:
        detail = _safe_compatible_error_detail(error)
        message = f"compatible {context} snapshot failed: {detail}"
        raise CompatiblePlanError(message) from error


def _require_tree_unchanged(
    root: Path,
    baseline: TreeSnapshot,
    context: str,
    *,
    phase: str = "staging",
) -> None:
    """Reject observable tree changes during authoring or publication.

    Raises:
        CompatiblePlanError: The file tree changed or became invalid.

    """
    try:
        current = snapshot_tree(root)
    except _NATIVE_EXACT_TREE_ERROR as error:
        detail = _safe_compatible_error_detail(error)
        message = f"compatible {context} tree changed during {phase}: {detail}"
        raise CompatiblePlanError(message) from error
    # Dataclass equality is a mutable class hook. Compare original stored
    # identity fields rather than calling an overridden TreeSnapshot.__eq__.
    current_fields = _NATIVE_TUPLE(
        _file_fields(record) for record in _snapshot_files(current)
    )
    baseline_fields = _NATIVE_TUPLE(
        _file_fields(record) for record in _snapshot_files(baseline)
    )
    if current_fields != baseline_fields:
        message = f"compatible {context} tree changed during {phase}"
        raise CompatiblePlanError(message)


def _check_staged_output(
    request: CompatibleMaterializeRequest,
    candidate: TreeSnapshot,
    staging: Path,
) -> TreeSnapshot:
    """Run quality checks and retain the accepted staging byte snapshot."""
    staged = _snapshot_compatible_tree(staging, "staging")
    _require_postcondition(request.postcondition, staging)
    _require_tree_unchanged(request.candidate_root, candidate, "candidate")
    _require_tree_unchanged(staging, staged, "staging")
    return staged


def _safe_compatible_error_detail(error: Exception) -> str:
    """Retain native fault messages without executing foreign formatters.

    Returns:
        An exact native single-string reason or an exception class name.

    """
    if _NATIVE_TYPE(error) in {
        CompatiblePlanError,
        ExactTreeError,
        _NATIVE_OS_ERROR,
        _NATIVE_PERMISSION_ERROR,
        _NATIVE_RUNTIME_ERROR,
        _NATIVE_VALUE_ERROR,
    }:
        arguments = cast(
            "tuple[object, ...]",
            BaseException.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
                error, "args"
            ),
        )
        if _NATIVE_LEN(arguments) == 1:
            reason = arguments[0]
            if _NATIVE_TYPE(reason) is _NATIVE_STR:
                return reason
    return _NATIVE_TYPE(error).__name__


def _cleanup_compatible_staging(path: Path) -> str | None:
    try:
        _NATIVE_RMTREE(path)
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        return None
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        return _safe_compatible_error_detail(error)
    return None


def _raise_compatible_cleanup_failure(
    error: Exception, cleanup_error: str
) -> None:
    detail = _safe_compatible_error_detail(error)
    message = f"{detail}; compatible staging cleanup failed: {cleanup_error}"
    raise CompatiblePlanError(message) from error


def _publish_compatible_output(staging: Path, destination: Path) -> None:
    try:
        publish_directory_no_replace(staging, destination)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_compatible_error_detail(error)
        message = f"compatible output publication failed: {detail}"
        raise CompatiblePlanError(message) from error


def materialize_compatible_plan(
    request: CompatibleMaterializeRequest,
) -> TransformAdmissionEvidence:
    """Materialize an admitted in-memory compatible tree transactionally.

    Returns:
        Passing conjunctive source-lineage and behavior evidence.

    Raises:
        CompatiblePlanError: Late publication drift is rejected; a renamed
            output may remain on disk when a post-rename check fails.

    """
    request = _require_materialize_request(request)
    _require_output_outside_candidate(request)
    admitted = _admit(request)
    _require_correction_routes(request.plan, request.behavior)
    candidate = _snapshot_compatible_tree(request.candidate_root, "candidate")
    candidate_paths = _NATIVE_FROZENSET(item.path for item in candidate.files)
    _require_literal_conflicts_absent(request, candidate_paths)
    staging = _prepare_staging(request.output_root)
    try:
        _populate_staging(request, candidate, staging)
        staged = _check_staged_output(request, candidate, staging)
        _publish_compatible_output(staging, request.output_root)
        # Publication can take time or invoke host callbacks; do not report
        # success if the candidate or published bytes drifted during rename.
        _require_tree_unchanged(
            request.output_root, staged, "published", phase="publication"
        )
        _require_tree_unchanged(
            request.candidate_root, candidate, "candidate", phase="publication"
        )
    except _NATIVE_EXCEPTION as error:
        cleanup_error = _cleanup_compatible_staging(staging)
        if cleanup_error is not None:
            _raise_compatible_cleanup_failure(error, cleanup_error)
        raise
    return admitted
