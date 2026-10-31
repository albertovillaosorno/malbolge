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
import os
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import generate as generate_module
from algorithms.diff.domain import DomainContractError
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.generate import DiffGeneratorUnavailableError
from algorithms.diff.generate import DiffRecipe
from algorithms.diff.generate import TransformMode
from algorithms.diff.generate import write_algorithm
import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.model import ExactAuthoringPlan

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


def test_generator_rejects_huge_integer_fractions_before_output(
    tmp_path: Path,
) -> None:
    """Invalid large integers cannot bypass the public policy error type."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    invalid_fractions: tuple[int, ...] = (
        10**400,
        -(10**400),
        10**5000,
        -(10**5000),
    )
    for invalid in invalid_fractions:
        for field, candidate in (
            (
                "minimum_source_similarity",
                replace(recipe, minimum_source_similarity=invalid),
            ),
            (
                "minimum_anchor_coverage",
                replace(recipe, minimum_anchor_coverage=invalid),
            ),
            (
                "minimum_behavior_similarity",
                replace(recipe, minimum_behavior_similarity=invalid),
            ),
            (
                "source_binding_threshold",
                replace(recipe, source_binding_threshold=invalid),
            ),
        ):
            with pytest.raises(ValueError, match=field):
                write_algorithm(candidate)
            _expect(
                not recipe.output_algorithm.exists(),
                "unrepresentable fraction wrote a generated transform",
            )


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


@pytest.mark.parametrize("unsafe_fragment", ["bad\x00path", "bad\ud800path"])
def test_generator_rejects_nonportable_recipe_paths_before_work(
    tmp_path: Path,
    unsafe_fragment: str,
) -> None:
    """Invalid host paths cannot reach preflight, source reads, or output."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    unsafe = tmp_path / unsafe_fragment
    for name, candidate in (
        ("source_root", replace(recipe, source_root=unsafe)),
        ("oracle_root", replace(recipe, oracle_root=unsafe)),
        ("output_algorithm", replace(recipe, output_algorithm=unsafe)),
        ("domain_module", replace(recipe, domain_module=unsafe)),
    ):
        with pytest.raises(ValueError, match=f"{name} must be a usable path"):
            write_algorithm(candidate)
        _expect(
            not recipe.output_algorithm.exists(),
            "invalid path created a transform",
        )


@pytest.mark.parametrize("profile", ["bad\x00profile", "bad\ud800profile"])
def test_generator_rejects_nonportable_profile_before_work(
    tmp_path: Path,
    profile: str,
) -> None:
    """The public profile identity must be canonically UTF-8 encodable."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    with pytest.raises(ValueError, match="profile must be portable UTF-8 text"):
        write_algorithm(replace(recipe, profile=profile))
    _expect(
        not recipe.output_algorithm.exists(),
        "invalid profile wrote output",
    )


@pytest.mark.parametrize("input_name", ["source_root", "oracle_root"])
def test_generator_never_publishes_inside_input_trees(
    tmp_path: Path,
    input_name: str,
) -> None:
    """A generated transform must not become a source or oracle input file."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    input_root = {
        "source_root": recipe.source_root,
        "oracle_root": recipe.oracle_root,
    }[input_name]
    destination = input_root / "nested" / "generated.rs"
    before = {
        path.relative_to(input_root): path.read_bytes()
        for path in input_root.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError, match=f"output_algorithm.*{input_name}"):
        write_algorithm(replace(recipe, output_algorithm=destination))
    after = {
        path.relative_to(input_root): path.read_bytes()
        for path in input_root.rglob("*")
        if path.is_file()
    }
    _expect(before == after, "generated transform mutated input files")
    _expect(not destination.exists(), "generated transform published in input")


def test_generator_rejects_linked_output_alias_into_source(
    tmp_path: Path,
) -> None:
    """A parent symlink cannot conceal a destination inside the input tree."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    link = tmp_path / "source-link"
    try:
        link.symlink_to(recipe.source_root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink fixture unavailable")
    destination = link / "generated.rs"
    with pytest.raises(ValueError, match=r"output_algorithm.*source_root"):
        write_algorithm(replace(recipe, output_algorithm=destination))
    _expect(
        not (recipe.source_root / "generated.rs").exists(),
        "linked generated transform modified the source tree",
    )


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


def test_domain_preflight_requires_void_oracle_result(tmp_path: Path) -> None:
    """Reject oracle validators that return foreign success metadata."""
    module = _domain_module(tmp_path)
    text = module.read_text(encoding="utf-8")
    marker = 'raise RuntimeError("oracle preflight rejected")'
    replacement = marker + chr(10) + "    return object()"
    _ = module.write_text(
        text.replace(marker, replacement, 1),
        encoding="utf-8",
        newline=chr(10),
    )
    recipe = _recipe(tmp_path, mode=TransformMode.COMPATIBLE)
    recipe = replace(recipe, domain_module=module)

    with pytest.raises(
        DomainContractError, match=r"oracle preflight.*return None"
    ):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(),
        "invalid oracle result wrote output",
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
    original_open = os.open
    attempts = 0

    def fail_identity_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal attempts
        if os.fspath(file) == os.fspath(blocked):
            attempts += 1
            if attempts > 1:
                message = "blocked exact identity reread"
                raise PermissionError(message)
        return original_open(file, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_identity_open)
    with pytest.raises(ExactTreeError, match="source identity read failed"):
        write_algorithm(recipe)
    _expect(
        not recipe.output_algorithm.exists(),
        "failed identity wrote output",
    )


def test_exact_generator_rejects_source_rewrite_after_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed post-plan source cannot become the bound input identity."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    original_build = build_exact_plan
    mutated = False

    def mutate_after_plan(
        source_root: Path,
        oracle_root: Path,
        *,
        passthrough_roots: tuple[str, ...] = (),
    ) -> ExactAuthoringPlan:
        nonlocal mutated
        plan = original_build(
            source_root, oracle_root, passthrough_roots=passthrough_roots
        )
        _ = (source_root / "b.bin").write_bytes(_blocks("changed"))
        mutated = True
        return plan

    monkeypatch.setattr(generate_module, "build_exact_plan", mutate_after_plan)
    with pytest.raises(ExactTreeError, match="source identity changed"):
        write_algorithm(recipe)
    _expect(mutated, "post-plan mutation was not exercised")
    _expect(not recipe.output_algorithm.exists(), "changed source was emitted")


def test_exact_generator_rejects_linked_source_identity_after_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A linked replay is not source identity even if its bytes are equal."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    source_file = recipe.source_root / "b.bin"
    foreign = tmp_path / "foreign.bin"
    _ = foreign.write_bytes(source_file.read_bytes())
    original_build = build_exact_plan
    mutated = False

    def replace_after_plan(
        source_root: Path,
        oracle_root: Path,
        *,
        passthrough_roots: tuple[str, ...] = (),
    ) -> ExactAuthoringPlan:
        nonlocal mutated
        plan = original_build(
            source_root, oracle_root, passthrough_roots=passthrough_roots
        )
        source_file.unlink()
        try:
            source_file.symlink_to(foreign)
        except OSError:
            pytest.skip("source symlink fixtures unavailable")
        mutated = True
        return plan

    monkeypatch.setattr(generate_module, "build_exact_plan", replace_after_plan)
    with pytest.raises(ExactTreeError, match="source identity read failed"):
        write_algorithm(recipe)
    _expect(mutated, "post-plan symlink mutation was not exercised")
    _expect(not recipe.output_algorithm.exists(), "linked source was emitted")


def test_exact_generator_rejects_added_static_file_after_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unexpected source path cannot disappear from identity admission."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    original_build = build_exact_plan
    added = False

    def add_after_plan(
        source_root: Path,
        oracle_root: Path,
        *,
        passthrough_roots: tuple[str, ...] = (),
    ) -> ExactAuthoringPlan:
        nonlocal added
        plan = original_build(
            source_root, oracle_root, passthrough_roots=passthrough_roots
        )
        _ = (source_root / "extra.bin").write_bytes(b"new unbound content")
        added = True
        return plan

    monkeypatch.setattr(generate_module, "build_exact_plan", add_after_plan)
    with pytest.raises(ExactTreeError, match="source tree changed"):
        write_algorithm(recipe)
    _expect(added, "post-plan source addition was not exercised")
    _expect(not recipe.output_algorithm.exists(), "unbound source was emitted")


def test_exact_generator_allows_dynamic_passthrough_addition_after_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """New passthrough files remain outside the static identity boundary."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    _write(recipe.source_root, "external/initial.bin", b"original")
    _write(recipe.oracle_root, "external/initial.bin", b"original")
    recipe = replace(recipe, passthrough_roots=("external",))
    original_build = build_exact_plan

    def add_passthrough_after_plan(
        source_root: Path,
        oracle_root: Path,
        *,
        passthrough_roots: tuple[str, ...] = (),
    ) -> ExactAuthoringPlan:
        plan = original_build(
            source_root, oracle_root, passthrough_roots=passthrough_roots
        )
        _write(source_root, "external/runtime.bin", b"late runtime data")
        return plan

    monkeypatch.setattr(
        generate_module, "build_exact_plan", add_passthrough_after_plan
    )
    write_algorithm(recipe)
    _expect(recipe.output_algorithm.exists(), "dynamic addition was rejected")


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
