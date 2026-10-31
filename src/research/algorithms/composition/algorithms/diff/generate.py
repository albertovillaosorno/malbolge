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
#   - Public source-bound transformation generation API.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Public source-bound transformation generation API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.admission import identity_tree
from algorithms.diff.domain import DomainContractError
from algorithms.diff.domain import load_diff_domain
from algorithms.diff.emit_rust import write_rust_transform
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import read_exact_regular_file
from algorithms.diff.exact import snapshot_tree_excluding
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.provenance import SourcePinEvidence
from algorithms.diff.source_binding import SourceBindingPolicy

_MAX_SHARES = 255
_NUL = "\x00"
_BACKSLASH = "\\"
_PARENT = ".."
_DOT = "."

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.model import FileRecord
    from algorithms.diff.model import TreeSnapshot


class TransformMode(StrEnum):
    """Runtime admission/materialization contract of a generated transform."""

    EXACT_BASELINE = "exact-baseline"
    COMPATIBLE = "compatible"


@dataclass(frozen=True, slots=True)
class DiffRecipe:
    """Declarative inputs and policy for one generated transform."""

    source_root: Path
    oracle_root: Path
    output_algorithm: Path
    profile: str
    mode: TransformMode
    domain_module: Path | None = None
    passthrough_roots: tuple[str, ...] = ()
    minimum_source_similarity: float = 0.50
    minimum_anchor_coverage: float = 0.66
    minimum_behavior_similarity: float = 0.80
    source_binding_threshold: float = 0.66
    source_binding_maximum_anchors: int = 127
    source_binding_minimum_files: int = 1
    ignore_comments_for_identity: bool = True
    ignore_formatting_for_identity: bool = True


class DiffGeneratorUnavailableError(RuntimeError):
    """Raised when a requested transform mode is not implemented yet."""


def _validate_fraction(name: str, value: object) -> None:
    if type(value) is int:
        # Only zero and one are integral fractions in [0, 1]. Reject other
        # integers before float conversion, which can raise OverflowError.
        if value not in {0, 1}:
            message = f"{name} must be a finite fraction in [0, 1]"
            raise ValueError(message)
        return
    if type(value) is not float:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise TypeError(message)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise ValueError(message)


def _validate_binding_count(
    name: str, value: object, maximum: int | None
) -> int:
    if type(value) is not int:
        message = f"{name} must use the exact integer type"
        raise TypeError(message)
    if value < 1 or (maximum is not None and value > maximum):
        limit = "positive" if maximum is None else f"in [1, {maximum}]"
        message = f"{name} must be {limit}"
        raise ValueError(message)
    return value


def _validate_binding_policy(recipe: DiffRecipe) -> None:
    if recipe.source_binding_threshold <= 0.0:
        message = "source_binding_threshold must be greater than zero"
        raise ValueError(message)
    maximum = _validate_binding_count(
        "source_binding_maximum_anchors",
        recipe.source_binding_maximum_anchors,
        _MAX_SHARES,
    )
    minimum = _validate_binding_count(
        "source_binding_minimum_files",
        recipe.source_binding_minimum_files,
        None,
    )
    if minimum > maximum:
        message = (
            "source_binding_minimum_files cannot exceed "
            "source_binding_maximum_anchors"
        )
        raise ValueError(message)


def _validate_path(value: object, name: str) -> None:
    if not isinstance(value, Path):
        message = f"{name} must be a pathlib Path"
        raise TypeError(message)
    if _NUL in os.fspath(value):
        message = f"{name} must be a usable path without NUL"
        raise ValueError(message)
    try:
        _ = os.fsencode(value)
    except UnicodeError as error:
        message = f"{name} must be a usable path on this host"
        raise ValueError(message) from error


def _resolve_recipe_path(path: Path, name: str) -> Path:
    try:
        return path.resolve()
    except (OSError, ValueError, RuntimeError) as error:
        message = f"{name} could not be resolved safely"
        raise ValueError(message) from error


def _validate_output_location(recipe: DiffRecipe) -> None:
    output = _resolve_recipe_path(recipe.output_algorithm, "output_algorithm")
    for name, root in (
        ("source_root", recipe.source_root),
        ("oracle_root", recipe.oracle_root),
    ):
        if output.is_relative_to(_resolve_recipe_path(root, name)):
            message = f"output_algorithm must be outside {name}"
            raise ValueError(message)
    if recipe.domain_module is not None and output == _resolve_recipe_path(
        recipe.domain_module, "domain_module"
    ):
        message = "output_algorithm must not overwrite domain_module"
        raise ValueError(message)


def _validate_recipe_paths(recipe: DiffRecipe) -> None:
    for value, name in (
        (recipe.source_root, "source_root"),
        (recipe.oracle_root, "oracle_root"),
        (recipe.output_algorithm, "output_algorithm"),
    ):
        _validate_path(value, name)
    if recipe.domain_module is not None:
        _validate_path(recipe.domain_module, "domain_module")
    _validate_output_location(recipe)


def _validate_profile_text(value: object) -> None:
    if type(value) is not str:
        message = "profile must use the exact string type"
        raise TypeError(message)
    if not value:
        message = "profile must be non-empty"
        raise ValueError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeEncodeError as error:
        message = "profile must be portable UTF-8 text"
        raise ValueError(message) from error
    if _NUL in value:
        message = "profile must be portable UTF-8 text without NUL"
        raise ValueError(message)


def _validate_recipe_identity(recipe: DiffRecipe) -> None:
    _validate_profile_text(recipe.profile)
    if type(recipe.mode) is not TransformMode:
        message = "mode must use the exact TransformMode type"
        raise TypeError(message)


def _canonical_passthrough_root(root: str) -> bool:
    candidate = PurePosixPath(root)
    unsafe_text = root == _DOT or any(
        char in root for char in (_BACKSLASH, _NUL)
    )
    unsafe_shape = (
        candidate.is_absolute()
        or PureWindowsPath(root).drive
        or _PARENT in candidate.parts
        or candidate.as_posix() != root
    )
    if unsafe_text or unsafe_shape:
        return False
    try:
        _ = root.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _validate_passthrough_topology(roots: tuple[str, ...]) -> None:
    if roots != tuple(sorted(set(roots))):
        message = "passthrough_roots must be canonical, sorted and disjoint"
        raise ValueError(message)
    for index, root in enumerate(roots):
        if any(other.startswith(root + "/") for other in roots[index + 1 :]):
            message = "passthrough_roots must be canonical, sorted and disjoint"
            raise ValueError(message)


def _validate_passthrough_roots(value: object) -> None:
    if type(value) is not tuple:
        message = "passthrough_roots must use the exact immutable tuple type"
        raise TypeError(message)
    items = cast("tuple[object, ...]", value)
    if any(type(root) is not str for root in items):
        message = "passthrough_roots entries must use the exact string type"
        raise TypeError(message)
    roots = cast("tuple[str, ...]", value)
    if any(not root for root in roots):
        message = "passthrough_roots entries must be non-empty"
        raise ValueError(message)
    if any(not _canonical_passthrough_root(root) for root in roots):
        message = "passthrough_roots must be canonical, sorted and disjoint"
        raise ValueError(message)
    _validate_passthrough_topology(roots)


def _validate_identity_flags(recipe: DiffRecipe) -> None:
    for name, value in (
        ("ignore_comments_for_identity", recipe.ignore_comments_for_identity),
        (
            "ignore_formatting_for_identity",
            recipe.ignore_formatting_for_identity,
        ),
    ):
        if type(value) is not bool:
            message = f"{name} must be an exact boolean"
            raise TypeError(message)


def _validate_recipe(recipe: DiffRecipe) -> None:
    if type(recipe) is not DiffRecipe:
        message = "diff recipe must use the exact DiffRecipe type"
        raise TypeError(message)
    _validate_recipe_paths(recipe)
    _validate_recipe_identity(recipe)
    _validate_passthrough_roots(recipe.passthrough_roots)
    _validate_identity_flags(recipe)
    for name, value in (
        ("minimum_source_similarity", recipe.minimum_source_similarity),
        ("minimum_anchor_coverage", recipe.minimum_anchor_coverage),
        ("minimum_behavior_similarity", recipe.minimum_behavior_similarity),
        ("source_binding_threshold", recipe.source_binding_threshold),
    ):
        _validate_fraction(name, value)
    _validate_binding_policy(recipe)


def _read_exact_identity_file(path: Path, record: FileRecord) -> bytes:
    replay = read_exact_regular_file(path, "exact source identity")
    if len(replay) != record.size or hashlib.sha256(replay).hexdigest() != (
        record.sha256
    ):
        message = f"exact source identity changed after planning: {record.path}"
        raise ExactTreeError(message)
    return replay


def _raw_exact_identity(
    recipe: DiffRecipe,
    source: TreeSnapshot,
) -> IdentityTree:
    files = {
        record.path: _read_exact_identity_file(
            recipe.source_root / record.path, record
        )
        for record in source.files
    }
    return identity_tree(files)


def _write_exact_algorithm(recipe: DiffRecipe) -> None:
    exact = build_exact_plan(
        recipe.source_root,
        recipe.oracle_root,
        passthrough_roots=recipe.passthrough_roots,
    )
    identity = _raw_exact_identity(recipe, exact.source)
    replayed_source = snapshot_tree_excluding(
        recipe.source_root, recipe.passthrough_roots
    )
    if replayed_source != exact.source:
        message = "exact source tree changed after identity replay"
        raise ExactTreeError(message)
    policy = SourceBindingPolicy(
        threshold_fraction=recipe.source_binding_threshold,
        maximum_anchors=recipe.source_binding_maximum_anchors,
        minimum_anchor_files=recipe.source_binding_minimum_files,
        anchor_policy=AnchorPolicy(),
    )
    context = f"{recipe.profile}:exact-baseline-v1".encode()
    protected = protect_exact_plan(
        exact,
        identity,
        binding_policy=policy,
        context=context,
    )
    # Protection can take time; reject persistent input drift before emitting
    # a distributable transform bound to a stale source or oracle snapshot.
    for name, root, expected in (
        ("source", recipe.source_root, exact.source),
        ("oracle", recipe.oracle_root, exact.target),
    ):
        if snapshot_tree_excluding(root, recipe.passthrough_roots) != expected:
            message = f"exact {name} tree changed during payload protection"
            raise ExactTreeError(message)
    write_rust_transform(
        protected,
        f"{recipe.profile}-exact-baseline-v1",
        recipe.output_algorithm,
    )


def _preflight_domain(recipe: DiffRecipe) -> None:
    if recipe.domain_module is None:
        message = "domain preflight requires a domain module"
        raise DiffGeneratorUnavailableError(message)
    domain = load_diff_domain(recipe.domain_module)
    evidence = domain.validate_source_provenance(recipe.source_root)
    if type(evidence) is not SourcePinEvidence:
        message = "domain source provenance hook must return SourcePinEvidence"
        raise DomainContractError(message)
    oracle_result = domain.validate_authoring_oracle(recipe.oracle_root)
    if oracle_result is not None:
        message = "domain oracle preflight hook must return None"
        raise DomainContractError(message)


def write_algorithm(recipe: DiffRecipe) -> None:
    """Generate one requested transform mode or fail closed.

    Exact-baseline mode is implemented and may exclude explicit passthrough
    roots from its static source snapshot. Domain-aware recipes execute source
    provenance and oracle preflights before either mode continues.
    Compatible mode executes those preflights and then remains unavailable.
    It then remains unavailable until compatible protected serialization and
    runtime emission are complete.

    Raises:
        DiffGeneratorUnavailableError: Compatible emission is not implemented.

    """
    _validate_recipe(recipe)
    if recipe.domain_module is not None:
        _preflight_domain(recipe)
    elif recipe.mode is TransformMode.COMPATIBLE:
        message = "compatible generation requires a domain module"
        raise DiffGeneratorUnavailableError(message)
    if recipe.mode is TransformMode.EXACT_BASELINE:
        _write_exact_algorithm(recipe)
        return
    message = (
        "compatible source-bound Rust emission is not implemented; "
        "preflight passed but no output was materialized"
    )
    raise DiffGeneratorUnavailableError(message)
