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
#   - Public generation-mode tests for source-bound diff transforms.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Public generation-mode tests for source-bound diff transforms."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from typing import cast

from algorithms.diff.domain import DomainContractError
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.generate import DiffGeneratorUnavailableError
from algorithms.diff.generate import DiffRecipe
from algorithms.diff.generate import TransformMode
from algorithms.diff.generate import write_algorithm
import pytest

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
    _ = path.write_bytes(data)


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


def _domain_module(tmp_path: Path) -> Path:
    module = tmp_path / "domain.py"
    _ = module.write_text(
        """\
from algorithms.diff.provenance import SourcePinEvidence


def validate_source_provenance(root):
    if (root / "reject-source").exists():
        raise RuntimeError("source pin rejected")
    return SourcePinEvidence(file_count=1, snapshot_sha256="0" * 64)


def validate_authoring_oracle(root):
    if (root / "reject-oracle").exists():
        raise RuntimeError("oracle preflight rejected")


def build_identity_tree(root):
    return None


def map_compatible_file(path, data):
    return None


def build_compatible_correction_bindings(plan):
    return ()


def build_behavior_programs():
    return None


def build_behavior_probe_context(source_root, repository_root):
    return None
""",
        encoding="utf-8",
        newline="\n",
    )
    return module


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


def test_compatible_mode_runs_domain_preflight_then_fails_emission(
    tmp_path: Path,
) -> None:
    """Require domain provenance checks before unfinished emission."""
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)
    recipe = replace(recipe, domain_module=_domain_module(tmp_path))

    with pytest.raises(DiffGeneratorUnavailableError, match="preflight passed"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(), "compatible mode wrote output"
    )


def test_domain_preflight_requires_source_pin_evidence(tmp_path: Path) -> None:
    """Reject provenance callbacks that return no typed snapshot evidence."""
    module = _domain_module(tmp_path)
    text = module.read_text(encoding="utf-8")
    valid = 'return SourcePinEvidence(file_count=1, snapshot_sha256="0" * 64)'
    _ = module.write_text(
        text.replace(valid, "return None", 1),
        encoding="utf-8",
        newline=chr(10),
    )
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)
    recipe = replace(recipe, domain_module=module)

    with pytest.raises(DomainContractError, match="return SourcePinEvidence"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(), "invalid provenance wrote output"
    )


def test_compatible_mode_propagates_source_preflight_failure(
    tmp_path: Path,
) -> None:
    """Reject the candidate source before compatible emission is considered."""
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)
    _write(recipe.source_root, "reject-source", b"")
    recipe = replace(recipe, domain_module=_domain_module(tmp_path))

    with pytest.raises(RuntimeError, match="source pin rejected"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(), "rejected source wrote output"
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


def test_exact_identity_second_read_failure_stays_in_exact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source-binding identity reread cannot leak a host I/O exception."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    blocked = recipe.source_root / "b.bin"
    original_read = Path.read_bytes
    reads = 0

    def fail_second_read(path: Path) -> bytes:
        nonlocal reads
        if path == blocked:
            reads += 1
            if reads > 1:
                message = "blocked exact identity reread"
                raise PermissionError(message)
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", fail_second_read)
    with pytest.raises(ExactTreeError, match="source identity read failed"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(),
        "failed identity wrote output",
    )


def test_exact_mode_runs_domain_preflight_with_passthrough(
    tmp_path: Path,
) -> None:
    """Use domain gates while keeping external roots outside static identity."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    _write(recipe.source_root, "external/game.bin", b"external")
    _write(recipe.oracle_root, "external/game.bin", b"external")
    recipe = replace(
        recipe,
        domain_module=_domain_module(tmp_path),
        passthrough_roots=("external",),
    )

    write_algorithm(recipe)

    _expect(
        recipe.output_algorithm.is_file(),
        "domain-aware exact mode wrote nothing",
    )


def test_generator_rejects_foreign_recipe_fields_before_output(
    tmp_path: Path,
) -> None:
    """Every public recipe field is admitted before preflight or generation."""
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)
    malformed = (
        replace(recipe, source_root=cast("Path", object())),
        replace(recipe, oracle_root=cast("Path", object())),
        replace(recipe, output_algorithm=cast("Path", object())),
        replace(recipe, profile=cast("str", object())),
        replace(recipe, mode=cast("TransformMode", object())),
        replace(recipe, domain_module=cast("Path", object())),
        replace(
            recipe,
            passthrough_roots=cast(
                "tuple[str, ...]",
                cast("object", ["external"]),
            ),
        ),
        replace(recipe, minimum_source_similarity=True),
        replace(recipe, minimum_anchor_coverage=True),
        replace(recipe, minimum_behavior_similarity=True),
        replace(recipe, source_binding_threshold=True),
        replace(recipe, source_binding_maximum_anchors=True),
        replace(recipe, source_binding_minimum_files=True),
        replace(
            recipe,
            ignore_comments_for_identity=cast("bool", object()),
        ),
        replace(
            recipe,
            ignore_formatting_for_identity=cast("bool", object()),
        ),
    )
    for candidate in malformed:
        with pytest.raises(TypeError, match="must"):
            write_algorithm(candidate)
        _expect(
            not recipe.output_algorithm.exists(),
            "invalid recipe field wrote output",
        )
    with pytest.raises(TypeError, match="exact DiffRecipe"):
        write_algorithm(cast("DiffRecipe", object()))


def test_generator_rejects_out_of_range_binding_counts(
    tmp_path: Path,
) -> None:
    """Source-binding count bounds fail before exact generation."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    for candidate in (
        replace(recipe, source_binding_maximum_anchors=0),
        replace(recipe, source_binding_maximum_anchors=256),
        replace(recipe, source_binding_minimum_files=0),
        replace(recipe, source_binding_minimum_files=9),
    ):
        with pytest.raises(ValueError, match=r"must|cannot"):
            write_algorithm(candidate)
        _expect(
            not recipe.output_algorithm.exists(),
            "invalid binding count wrote output",
        )
