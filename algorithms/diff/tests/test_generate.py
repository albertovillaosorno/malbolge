# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Public generation-mode tests for source-bound diff transforms."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.generate import DiffGeneratorUnavailableError
from algorithms.diff.generate import DiffRecipe
from algorithms.diff.generate import TransformMode
from algorithms.diff.generate import write_algorithm

if TYPE_CHECKING:
    from pathlib import Path

_BLOCKS = 48
_STD_MARKER = b"use std::"
_LITERAL_MARKER = b"target-only"


def _blocks(label: str) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCKS)
    )


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _recipe(
    tmp_path: Path,
    *,
    mode: TransformMode,
    source_similarity: float = 0.50,
) -> DiffRecipe:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    base = _blocks("base")
    other = _blocks("other")
    _write(source, "a.bin", base)
    _write(source, "b.bin", other)
    _write(oracle, "a.bin", base[:512] + b"target-only" + base[512:])
    _write(oracle, "b.bin", other)
    return DiffRecipe(
        source_root=source,
        oracle_root=oracle,
        output_algorithm=tmp_path / "main.rs",
        profile="synthetic-generator-v1",
        mode=mode,
        minimum_source_similarity=source_similarity,
        source_binding_threshold=0.50,
        source_binding_maximum_anchors=8,
        source_binding_minimum_files=2,
    )


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_generator_rejects_invalid_fraction_before_output(
    tmp_path: Path,
) -> None:
    """Reject invalid policy before creating a generated transform."""
    recipe = _recipe(
        tmp_path,
        mode=TransformMode.EXACT_BASELINE,
        source_similarity=1.01,
    )

    with pytest.raises(ValueError, match="minimum_source_similarity"):
        write_algorithm(recipe)
    _expect(not recipe.output_algorithm.exists(), "invalid recipe wrote output")


def test_compatible_mode_remains_fail_closed(tmp_path: Path) -> None:
    """Keep fuzzy generation unavailable until runtime gates exist."""
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)

    with pytest.raises(DiffGeneratorUnavailableError, match="compatible"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(), "compatible mode wrote output"
    )


def test_exact_mode_writes_deterministic_standalone_rust(
    tmp_path: Path,
) -> None:
    """Generate the implemented exact baseline deterministically."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)

    write_algorithm(recipe)
    first = recipe.output_algorithm.read_bytes()
    recipe.output_algorithm.unlink()
    write_algorithm(recipe)
    second = recipe.output_algorithm.read_bytes()

    _expect(first == second, "exact generator output changed across runs")
    _expect(_STD_MARKER in first, "exact generator did not emit Rust runtime")
    _expect(_LITERAL_MARKER not in first, "plaintext oracle literal leaked")
