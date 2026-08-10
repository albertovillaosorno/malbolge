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
import math
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.admission import identity_tree
from algorithms.diff.domain import DomainContractError
from algorithms.diff.domain import load_diff_domain
from algorithms.diff.emit_rust import write_rust_transform
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.provenance import SourcePinEvidence
from algorithms.diff.source_binding import SourceBindingPolicy

_MAX_SHARES = 255

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityTree


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
        number = float(value)
    elif type(value) is float:
        number = value
    else:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise TypeError(message)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
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


def _validate_recipe_paths(recipe: DiffRecipe) -> None:
    for value, name in (
        (recipe.source_root, "source_root"),
        (recipe.oracle_root, "oracle_root"),
        (recipe.output_algorithm, "output_algorithm"),
    ):
        _validate_path(value, name)
    if recipe.domain_module is not None:
        _validate_path(recipe.domain_module, "domain_module")


def _validate_recipe_identity(recipe: DiffRecipe) -> None:
    if type(recipe.profile) is not str:
        message = "profile must use the exact string type"
        raise TypeError(message)
    if not recipe.profile:
        message = "profile must be non-empty"
        raise ValueError(message)
    if type(recipe.mode) is not TransformMode:
        message = "mode must use the exact TransformMode type"
        raise TypeError(message)


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


def _read_exact_identity_file(path: Path, relative: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        message = f"exact source identity read failed: {relative}: {error}"
        raise ExactTreeError(message) from error


def _raw_exact_identity(
    recipe: DiffRecipe,
    source_paths: tuple[str, ...],
) -> IdentityTree:
    files = {
        relative: _read_exact_identity_file(
            recipe.source_root / relative,
            relative,
        )
        for relative in source_paths
    }
    return identity_tree(files)


def _write_exact_algorithm(recipe: DiffRecipe) -> None:
    exact = build_exact_plan(
        recipe.source_root,
        recipe.oracle_root,
        passthrough_roots=recipe.passthrough_roots,
    )
    source_paths = tuple(record.path for record in exact.source.files)
    identity = _raw_exact_identity(recipe, source_paths)
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
    domain.validate_authoring_oracle(recipe.oracle_root)


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
