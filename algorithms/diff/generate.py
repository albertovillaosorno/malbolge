# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Public source-bound transformation generation API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import TYPE_CHECKING

from algorithms.diff.admission import identity_tree
from algorithms.diff.domain import load_compatible_domain
from algorithms.diff.emit_rust import write_rust_transform
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.source_binding import SourceBindingPolicy

if TYPE_CHECKING:
    from pathlib import Path

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


def _validate_fraction(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise ValueError(message)


def _validate_binding_policy(recipe: DiffRecipe) -> None:
    if recipe.source_binding_threshold <= 0.0:
        message = "source_binding_threshold must be greater than zero"
        raise ValueError(message)
    if recipe.source_binding_maximum_anchors < 1:
        message = "source_binding_maximum_anchors must be positive"
        raise ValueError(message)
    if recipe.source_binding_minimum_files < 1:
        message = "source_binding_minimum_files must be positive"
        raise ValueError(message)
    if (
        recipe.source_binding_minimum_files
        > recipe.source_binding_maximum_anchors
    ):
        message = (
            "source_binding_minimum_files cannot exceed "
            "source_binding_maximum_anchors"
        )
        raise ValueError(message)


def _validate_recipe(recipe: DiffRecipe) -> None:
    fractions = (
        ("minimum_source_similarity", recipe.minimum_source_similarity),
        ("minimum_anchor_coverage", recipe.minimum_anchor_coverage),
        ("minimum_behavior_similarity", recipe.minimum_behavior_similarity),
        ("source_binding_threshold", recipe.source_binding_threshold),
    )
    for name, value in fractions:
        _validate_fraction(name, value)
    _validate_binding_policy(recipe)
    if not recipe.profile:
        message = "profile must be non-empty"
        raise ValueError(message)


def _raw_exact_identity(
    recipe: DiffRecipe,
    source_paths: tuple[str, ...],
) -> IdentityTree:
    files = {
        relative: (recipe.source_root / relative).read_bytes()
        for relative in source_paths
    }
    return identity_tree(files)


def _write_exact_algorithm(recipe: DiffRecipe) -> None:
    exact = build_exact_plan(recipe.source_root, recipe.oracle_root)
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


def _preflight_compatible(recipe: DiffRecipe) -> None:
    if recipe.domain_module is None:
        message = "compatible generation requires a domain module"
        raise DiffGeneratorUnavailableError(message)
    domain = load_compatible_domain(recipe.domain_module)
    domain.validate_source_provenance(recipe.source_root)
    domain.validate_authoring_oracle(recipe.oracle_root)


def write_algorithm(recipe: DiffRecipe) -> None:
    """Generate one requested transform mode or fail closed.

    Exact-baseline mode is implemented and intentionally binds raw source
    bytes because it also requires the exact authoring source snapshot.
    Compatible mode executes consumer source-provenance and oracle preflights.
    It then remains unavailable until compatible protected serialization and
    runtime emission are complete.

    Raises:
        DiffGeneratorUnavailableError: Compatible emission is not implemented.

    """
    _validate_recipe(recipe)
    if recipe.mode is TransformMode.EXACT_BASELINE:
        _write_exact_algorithm(recipe)
        return
    _preflight_compatible(recipe)
    message = (
        "compatible source-bound Rust emission is not implemented; "
        "preflight passed but no output was materialized"
    )
    raise DiffGeneratorUnavailableError(message)
