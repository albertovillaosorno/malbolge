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

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import shutil
from typing import TYPE_CHECKING

from algorithms.diff.admission import evaluate_admission
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.gate import require_transform_admission
from algorithms.diff.mapped import MappedView
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral
from algorithms.diff.publication import publish_directory_no_replace
from algorithms.diff.semantic import apply_semantic_plan
from algorithms.diff.semantic import build_semantic_plan

if TYPE_CHECKING:
    from algorithms.diff.admission import AdmissionPolicy
    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.behavior import BehaviorEvidence
    from algorithms.diff.gate import TransformAdmissionEvidence
    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.model import ExactInstruction
    from algorithms.diff.model import FileRecord
    from algorithms.diff.model import TreeSnapshot
    from algorithms.diff.semantic import SemanticAuthoringPlan

_ONE = 1
_STAGING_SUFFIX = ".compatible-staging"
_PARENT = ".."
_DOT = "."
_BACKSLASH = "\\"

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


@dataclass(frozen=True, slots=True)
class CompatibleInstruction:
    """One target-path instruction for compatible authoring."""

    output_path: str
    kind: CompatibleFileKind
    source_path: str | None = None
    source_sha256: str | None = None
    semantic: SemanticAuthoringPlan | None = None
    exact: ExactInstruction | None = None
    literal: bytes | None = None

    def __post_init__(self) -> None:
        """Reject incomplete instruction forms."""
        _validate_instruction(self)


@dataclass(frozen=True, slots=True)
class CompatibleBuildRequest:
    """Inputs required to author one in-memory compatible tree plan."""

    source_root: Path
    oracle_root: Path
    reference_identity: IdentityTree
    admission_policy: AdmissionPolicy
    mapper: Mapper
    preserve_candidate_only: bool = True


@dataclass(frozen=True, slots=True)
class CompatibleAuthoringPlan:
    """Non-distributable tree plan around admission and semantic placement."""

    source: TreeSnapshot
    target: TreeSnapshot
    reference_identity: IdentityTree
    admission_policy: AdmissionPolicy
    instructions: tuple[CompatibleInstruction, ...]
    preserve_candidate_only: bool = True


@dataclass(frozen=True, slots=True)
class CompatibleMaterializeRequest:
    """Candidate evidence and hooks for compatible materialization."""

    candidate_root: Path
    candidate_identity: IdentityTree
    behavior: BehaviorEvidence
    plan: CompatibleAuthoringPlan
    mapper: Mapper
    output_root: Path
    postcondition: Postcondition | None = None


@dataclass(frozen=True, slots=True)
class _BuildContext:
    request: CompatibleBuildRequest
    exact: ExactAuthoringPlan
    source_records: dict[str, FileRecord]


@dataclass(frozen=True, slots=True)
class _MaterializeContext:
    candidate_root: Path
    mapper: Mapper


def _require_source(instruction: CompatibleInstruction) -> None:
    if instruction.source_path is None:
        message = "compatible source-backed instruction lost source path"
        raise CompatiblePlanError(message)


def _validate_copy(instruction: CompatibleInstruction) -> None:
    _require_source(instruction)
    if any(
        value is not None
        for value in (
            instruction.source_sha256,
            instruction.semantic,
            instruction.exact,
            instruction.literal,
        )
    ):
        message = "compatible candidate copy carries unrelated payload evidence"
        raise CompatiblePlanError(message)


def _validate_semantic(instruction: CompatibleInstruction) -> None:
    _require_source(instruction)
    if instruction.semantic is None:
        message = "compatible semantic patch lost its semantic plan"
        raise CompatiblePlanError(message)
    if any(
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
    if instruction.semantic is not None or instruction.literal is not None:
        message = "exact-gated instruction carries unrelated semantic evidence"
        raise CompatiblePlanError(message)


def _validate_literal(instruction: CompatibleInstruction) -> None:
    if instruction.literal is None or instruction.source_path is not None:
        message = "compatible literal creation has invalid source state"
        raise CompatiblePlanError(message)
    if any(
        value is not None
        for value in (
            instruction.source_sha256,
            instruction.semantic,
            instruction.exact,
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


def _validate_instruction(instruction: CompatibleInstruction) -> None:
    validator = _INSTRUCTION_VALIDATORS.get(instruction.kind)
    if validator is None:
        message = f"unknown compatible instruction kind: {instruction.kind}"
        raise CompatiblePlanError(message)
    validator(instruction)


def _record_map(snapshot: TreeSnapshot) -> dict[str, FileRecord]:
    return {record.path: record for record in snapshot.files}


def _validate_relative_path(relative_path: str) -> str:
    candidate = PurePosixPath(relative_path)
    unsafe = (
        not relative_path
        or _BACKSLASH in relative_path
        or relative_path == _DOT
        or candidate.is_absolute()
        or _PARENT in candidate.parts
        or candidate.as_posix() != relative_path
    )
    if unsafe:
        message = f"unsafe compatible tree path: {relative_path!r}"
        raise CompatiblePlanError(message)
    return relative_path


def _safe_path(root: Path, relative_path: str) -> Path:
    normalized = _validate_relative_path(relative_path)
    path = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except OSError as error:
        message = (
            f"compatible path resolution failed: {relative_path!r}: {error}"
        )
        raise CompatiblePlanError(message) from error
    try:
        _ = resolved_path.relative_to(resolved_root)
    except ValueError as error:
        message = f"compatible path escapes tree root: {relative_path!r}"
        raise CompatiblePlanError(message) from error
    return path


def _path_present(path: Path, context: str) -> bool:
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        message = f"{context} status failed: {path}: {error}"
        raise CompatiblePlanError(message) from error
    return True


def _read_compatible_bytes(path: Path, context: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        message = f"{context} read failed: {path}: {error}"
        raise CompatiblePlanError(message) from error


def _write_compatible_bytes(path: Path, data: bytes, context: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(data)
    except OSError as error:
        message = f"{context} write failed: {path}: {error}"
        raise CompatiblePlanError(message) from error


def _make_compatible_directory(
    path: Path,
    context: str,
    *,
    parents: bool,
    exist_ok: bool,
) -> None:
    try:
        path.mkdir(parents=parents, exist_ok=exist_ok)
    except OSError as error:
        message = f"{context} creation failed: {path}: {error}"
        raise CompatiblePlanError(message) from error


def _tree_bytes(root: Path, relative_path: str) -> bytes:
    path = _safe_path(root, relative_path)
    return _read_compatible_bytes(path, "compatible tree file")


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
    source_bytes = _tree_bytes(context.request.source_root, source_path)
    target_bytes = _tree_bytes(
        context.request.oracle_root,
        instruction.output_path,
    )
    source_view = context.request.mapper(source_path, source_bytes)
    target_view = context.request.mapper(instruction.output_path, target_bytes)
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
    return CompatibleInstruction(
        output_path=instruction.output_path,
        kind=CompatibleFileKind.CREATE_LITERAL,
        literal=_tree_bytes(
            context.request.oracle_root,
            instruction.output_path,
        ),
    )


def _mapped_instruction(
    instruction: ExactInstruction,
    source_path: str,
    mapped: tuple[MappedView, MappedView],
) -> CompatibleInstruction:
    semantic = build_semantic_plan(*mapped)
    if not semantic.edits:
        return CompatibleInstruction(
            output_path=instruction.output_path,
            kind=CompatibleFileKind.COPY_CANDIDATE,
            source_path=source_path,
        )
    return CompatibleInstruction(
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
    record = context.source_records[source_path]
    return CompatibleInstruction(
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
    source_path = _source_path(instruction, context.source_records)
    if source_path is None:
        return _literal_instruction(context, instruction)
    mapped = _mapped_pair(context, instruction, source_path)
    if mapped is not None:
        return _mapped_instruction(instruction, source_path, mapped)
    return _exact_instruction(context, instruction, source_path)


def build_compatible_plan(
    request: CompatibleBuildRequest,
) -> CompatibleAuthoringPlan:
    """Build an in-memory compatible tree plan from local source and oracle.

    Returns:
        Plan combining target topology, semantic placement, and conservative
        exact gates for unmapped files.

    """
    exact = build_exact_plan(request.source_root, request.oracle_root)
    context = _BuildContext(
        request=request,
        exact=exact,
        source_records=_record_map(exact.source),
    )
    instructions = tuple(
        _compatible_instruction(context, instruction)
        for instruction in exact.instructions
    )
    return CompatibleAuthoringPlan(
        source=exact.source,
        target=exact.target,
        reference_identity=request.reference_identity,
        admission_policy=request.admission_policy,
        instructions=instructions,
        preserve_candidate_only=request.preserve_candidate_only,
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_literal(instruction: ExactInstruction) -> bytes:
    if instruction.literal is None:
        message = "exact-gated literal lost target bytes"
        raise CompatiblePlanError(message)
    return instruction.literal


def _exact_patch(candidate: bytes, instruction: ExactInstruction) -> bytes:
    parts: list[bytes] = []
    for segment in instruction.segments:
        if isinstance(segment, OracleLiteral):
            parts.append(segment.data)
            continue
        end = segment.offset + segment.length
        if end > len(candidate):
            message = "exact-gated source slice exceeds candidate file"
            raise CompatiblePlanError(message)
        parts.append(candidate[segment.offset : end])
    return b"".join(parts)


def _exact_bytes(candidate: bytes, instruction: ExactInstruction) -> bytes:
    if instruction.kind is ExactInstructionKind.COPY_SOURCE:
        return candidate
    if instruction.kind is ExactInstructionKind.LITERAL_ORACLE:
        return _exact_literal(instruction)
    return _exact_patch(candidate, instruction)


def _require_mapped(mapper: Mapper, path: str, data: bytes) -> MappedView:
    view = mapper(path, data)
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
    return _tree_bytes(context.candidate_root, instruction.source_path)


def _materialize_copy(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    return _candidate_bytes(context, instruction)


def _materialize_semantic(
    context: _MaterializeContext,
    instruction: CompatibleInstruction,
) -> bytes:
    candidate = _candidate_bytes(context, instruction)
    if instruction.source_path is None or instruction.semantic is None:
        message = "compatible semantic instruction is incomplete"
        raise CompatiblePlanError(message)
    view = _require_mapped(context.mapper, instruction.source_path, candidate)
    return apply_semantic_plan(
        view,
        instruction.semantic,
        lambda data: _require_mapped(
            context.mapper,
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
    return _exact_bytes(candidate, instruction.exact)


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
    staging = output_root.with_name(f".{output_root.name}{_STAGING_SUFFIX}")
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
    return frozenset(item.output_path for item in plan.instructions)


def _source_paths(plan: CompatibleAuthoringPlan) -> frozenset[str]:
    return frozenset(item.path for item in plan.source.files)


def _candidate_only_paths(
    candidate: TreeSnapshot,
    plan: CompatibleAuthoringPlan,
) -> tuple[str, ...]:
    if not plan.preserve_candidate_only:
        return ()
    source_paths = _source_paths(plan)
    target_paths = _target_paths(plan)
    return tuple(
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


def _require_bug_routing_wired(behavior: BehaviorEvidence) -> None:
    if behavior.corrections_to_apply or behavior.corrections_to_skip:
        message = (
            "compatible bug correction routing is not wired to tree edits yet"
        )
        raise CompatiblePlanError(message)


def _populate_staging(
    request: CompatibleMaterializeRequest,
    candidate: TreeSnapshot,
    staging: Path,
) -> None:
    context = _MaterializeContext(
        candidate_root=request.candidate_root,
        mapper=request.mapper,
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
    if postcondition is not None and not postcondition(staging):
        message = "compatible output postcondition rejected staging tree"
        raise CompatiblePlanError(message)


def _admit(request: CompatibleMaterializeRequest) -> TransformAdmissionEvidence:
    source_evidence = evaluate_admission(
        request.plan.reference_identity,
        request.candidate_identity,
        request.plan.admission_policy,
    )
    return require_transform_admission(source_evidence, request.behavior)


def _cleanup_compatible_staging(path: Path) -> str | None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        return str(error)
    return None


def _raise_compatible_cleanup_failure(
    error: Exception, cleanup_error: str
) -> None:
    message = f"{error}; compatible staging cleanup failed: {cleanup_error}"
    raise CompatiblePlanError(message) from error


def _publish_compatible_output(staging: Path, destination: Path) -> None:
    try:
        publish_directory_no_replace(staging, destination)
    except OSError as error:
        message = f"compatible output publication failed: {error}"
        raise CompatiblePlanError(message) from error


def materialize_compatible_plan(
    request: CompatibleMaterializeRequest,
) -> TransformAdmissionEvidence:
    """Materialize an admitted in-memory compatible tree transactionally.

    Returns:
        Passing conjunctive source-lineage and behavior evidence.

    """
    admitted = _admit(request)
    _require_bug_routing_wired(request.behavior)
    candidate = snapshot_tree(request.candidate_root)
    candidate_paths = frozenset(item.path for item in candidate.files)
    _require_literal_conflicts_absent(request, candidate_paths)
    staging = _prepare_staging(request.output_root)
    try:
        _populate_staging(request, candidate, staging)
        _require_postcondition(request.postcondition, staging)
        _publish_compatible_output(staging, request.output_root)
    except Exception as error:
        cleanup_error = _cleanup_compatible_staging(staging)
        if cleanup_error is not None:
            _raise_compatible_cleanup_failure(error, cleanup_error)
        raise
    return admitted
