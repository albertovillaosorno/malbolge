# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Fail-closed tests for the source-bound diff generator scaffold."""

from pathlib import Path

import pytest

from algorithms.diff.generate import DiffGeneratorUnavailableError
from algorithms.diff.generate import DiffRecipe
from algorithms.diff.generate import write_algorithm


def _recipe(*, source_similarity: float = 0.50) -> DiffRecipe:
    return DiffRecipe(
        source_root=Path("source"),
        oracle_root=Path("oracle"),
        output_algorithm=Path("main.rs"),
        profile="synthetic-v1",
        minimum_source_similarity=source_similarity,
    )


def test_scaffold_rejects_invalid_fraction() -> None:
    """Reject admission thresholds outside the closed unit interval."""
    with pytest.raises(ValueError, match="minimum_source_similarity"):
        write_algorithm(_recipe(source_similarity=1.01))


def test_scaffold_never_materializes_before_engine_exists() -> None:
    """Fail explicitly rather than pretending the transformation was emitted."""
    with pytest.raises(DiffGeneratorUnavailableError, match="not implemented"):
        write_algorithm(_recipe())
