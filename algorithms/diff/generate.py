# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Public scaffold for source-bound transformation generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DiffRecipe:
    """Declarative inputs and admission policy for one generated transform."""

    source_root: Path
    oracle_root: Path
    output_algorithm: Path
    profile: str
    domain_module: Path | None = None
    minimum_source_similarity: float = 0.50
    minimum_anchor_coverage: float = 0.66
    minimum_behavior_similarity: float = 0.80
    ignore_comments_for_identity: bool = True
    ignore_formatting_for_identity: bool = True


class DiffGeneratorUnavailableError(RuntimeError):
    """Raised while the checked-in scaffold has no generation engine yet."""


def _validate_fraction(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        message = f"{name} must be between 0.0 and 1.0, got {value}"
        raise ValueError(message)


def write_algorithm(recipe: DiffRecipe) -> None:
    """Validate one recipe and fail closed until implementation.

    Raises:
        DiffGeneratorUnavailableError: The checked-in engine is only a scaffold.

    """
    _validate_fraction(
        "minimum_source_similarity", recipe.minimum_source_similarity
    )
    _validate_fraction(
        "minimum_anchor_coverage", recipe.minimum_anchor_coverage
    )
    _validate_fraction(
        "minimum_behavior_similarity", recipe.minimum_behavior_similarity
    )
    message = (
        "algorithms/diff is scaffolded but not implemented; no output was "
        "materialized"
    )
    raise DiffGeneratorUnavailableError(message)
