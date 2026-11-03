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

import builtins
import hashlib
import math
import ntpath
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import generate as generate_module
from algorithms.diff.domain import DomainContractError
from algorithms.diff.exact import ExactTreeError, build_exact_plan
from algorithms.diff.generate import (
    DiffGeneratorUnavailableError,
    DiffRecipe,
    TransformMode,
    write_algorithm,
)
from algorithms.diff.model import FileRecord
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.provenance import SourcePinEvidence

if TYPE_CHECKING:
    from collections.abc import Callable, Sized

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.domain import DiffDomain
    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.protected import ProtectedExactPlan
    from algorithms.diff.source_binding import SourceBindingPolicy

_BLOCKS = 48
_EXACT_PLAN_SOURCE_READS = 2
_SOURCE_TREE = "source"
_ORACLE_TREE = "oracle"
_STD_MARKER = b"use std::"
_LITERAL_MARKER = b"target-only"
_OUTPUT_ALGORITHM = "output_algorithm"
_EXACT_STRING_TYPE = "exact string type"


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


@pytest.mark.parametrize(
    "case",
    [(float("nan"), True, False), (0.5, False, True)],
)
def test_generator_fraction_policy_resists_post_import_math_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[float, bool, bool],
) -> None:
    """A late finite-check swap cannot admit NaN or reject valid policy."""
    fraction, forged_finite, admitted = case
    recipe = replace(
        _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE),
        minimum_source_similarity=fraction,
    )
    reached_writer: list[bool] = []

    def record_writer(_: DiffRecipe) -> None:
        reached_writer.append(True)

    def forged_isfinite(_: float) -> bool:
        return forged_finite

    with monkeypatch.context() as patch:
        patch.setattr(math, "isfinite", forged_isfinite)
        patch.setattr(generate_module, "_write_exact_algorithm", record_writer)
        if not admitted:
            with pytest.raises(ValueError, match="minimum_source_similarity"):
                write_algorithm(recipe)
        else:
            write_algorithm(recipe)

    _expect(
        reached_writer == ([True] if admitted else []),
        "hostile finite checker changed recipe admission or side effects",
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


class _ForeignRecipePath(type(Path())):
    """An override may redirect a transform input before admission."""

    @override
    def __fspath__(self) -> str:
        message = "foreign recipe path conversion executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    "field", ["source_root", "oracle_root", "output_algorithm", "domain_module"]
)
def test_generator_rejects_foreign_path_subclasses_before_access(
    tmp_path: Path, field: str
) -> None:
    """All authoring roots must be native paths before any path method runs."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    candidate = replace(
        recipe, **{field: _ForeignRecipePath(tmp_path / "foreign")}
    )
    with pytest.raises(TypeError, match=f"{field} must use exact pathlib Path"):
        write_algorithm(candidate)
    assert not recipe.output_algorithm.exists()


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


@pytest.mark.parametrize(
    "case",
    [
        (name, failure_type)
        for name in (
            "output_algorithm",
            "source_root",
            "oracle_root",
            "domain_module",
        )
        for failure_type in (PermissionError, ValueError, RuntimeError)
    ],
)
def test_generator_recipe_resolution_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[Exception]],
) -> None:
    """Filesystem resolution cannot escape recipe validation as a host error."""
    name, failure_type = case
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    module = _domain_module(tmp_path)
    recipe = replace(recipe, domain_module=module)
    target = {
        "output_algorithm": recipe.output_algorithm,
        "source_root": recipe.source_root,
        "oracle_root": recipe.oracle_root,
        "domain_module": module,
    }[name]
    original_resolve = Path.resolve

    def blocked_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == target:
            message = "blocked recipe resolution"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(
        generate_module, "_NATIVE_PATH_RESOLVE", blocked_resolve
    )
    with pytest.raises(
        ValueError, match=f"{name} could not be resolved safely"
    ):
        write_algorithm(recipe)
    _expect(not recipe.output_algorithm.exists(), "blocked recipe wrote output")


class _ForgedResolvedRecipePath(type(Path())):
    """A foreign resolved receipt can lie about destination containment."""

    @override
    def is_relative_to(self, other: str | os.PathLike[str]) -> bool:
        del other
        return False


@pytest.mark.parametrize(
    "field", ["source_root", "oracle_root", "output_algorithm", "domain_module"]
)
def test_generator_rejects_foreign_resolved_path_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Resolve must not let a foreign path authorize recipe preflight."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    module = _domain_module(tmp_path)
    recipe = replace(recipe, domain_module=module)
    if field == _OUTPUT_ALGORITHM:
        recipe = replace(
            recipe, output_algorithm=recipe.source_root / "nested" / "main.rs"
        )
    target = {
        "source_root": recipe.source_root,
        "oracle_root": recipe.oracle_root,
        "output_algorithm": recipe.output_algorithm,
        "domain_module": module,
    }[field]
    native_resolve = Path.resolve

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        resolved = native_resolve(path, strict=strict)
        if path == target:
            return _ForgedResolvedRecipePath(resolved)
        return resolved

    def unexpected_preflight(ignored_recipe: DiffRecipe) -> None:
        del ignored_recipe
        message = "foreign resolved path entered domain preflight"
        raise AssertionError(message)

    monkeypatch.setattr(generate_module, "_NATIVE_PATH_RESOLVE", forged_resolve)
    monkeypatch.setattr(
        generate_module, "_preflight_domain", unexpected_preflight
    )
    with pytest.raises(
        ValueError, match=f"{field} could not be resolved safely"
    ):
        write_algorithm(recipe)
    assert not recipe.output_algorithm.exists()


def _input_output_destination(
    tmp_path: Path, input_root: Path, *, via_alias: bool
) -> Path:
    """Locate a synthetic forbidden output via a direct or symlink path.

    Returns:
        A source-or-oracle-contained output path.

    """
    if not via_alias:
        return input_root / "forged-generated.rs"
    alias = tmp_path / "input-alias"
    try:
        alias.symlink_to(input_root, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("directory symlinks unavailable")
    return alias / "forged-generated.rs"


@pytest.mark.parametrize("input_name", ["source_root", "oracle_root"])
@pytest.mark.parametrize("via_alias", [False, True])
def test_generator_rejects_forged_native_output_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    input_name: str,
    *,
    via_alias: bool,
) -> None:
    """A late native Path receipt cannot hide output inside an input tree."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    protected = {
        "source_root": recipe.source_root,
        "oracle_root": recipe.oracle_root,
    }[input_name]
    destination = _input_output_destination(
        tmp_path, protected, via_alias=via_alias
    )
    recipe = replace(recipe, output_algorithm=destination)
    native_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == destination:
            calls += 1
            return tmp_path / "unrelated-safe.rs"
        return native_resolve(path, strict=strict)

    def unexpected_emission(_recipe: DiffRecipe) -> None:
        del _recipe
        message = "forged output resolution reached unsafe generator emission"
        raise AssertionError(message)

    monkeypatch.setattr(Path, "resolve", forged_resolve)
    monkeypatch.setattr(
        generate_module, "_write_exact_algorithm", unexpected_emission
    )
    with pytest.raises(ValueError, match=f"output_algorithm.*{input_name}"):
        write_algorithm(recipe)
    _expect(calls == 0, "mutable global resolver was consulted")
    _expect(
        not (protected / destination.name).exists(), "input tree was changed"
    )


@pytest.mark.parametrize("input_name", ["source_root", "oracle_root"])
def test_generator_output_containment_resists_mutable_path_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    input_name: str,
) -> None:
    """A late host path hook cannot authorize writing into authoring inputs."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    input_root = {
        "source_root": recipe.source_root,
        "oracle_root": recipe.oracle_root,
    }[input_name]
    recipe = replace(recipe, output_algorithm=input_root / "nested" / "main.rs")

    def forged_is_relative_to(_path: Path, _other: Path) -> bool:
        del _path, _other
        return False

    def unexpected_emission(ignored_recipe: DiffRecipe) -> None:
        del ignored_recipe
        message = "forged containment allowed writing into an input tree"
        raise AssertionError(message)

    monkeypatch.setattr(Path, "is_relative_to", forged_is_relative_to)
    monkeypatch.setattr(
        generate_module, "_write_exact_algorithm", unexpected_emission
    )
    with pytest.raises(ValueError, match=f"output_algorithm.*{input_name}"):
        write_algorithm(recipe)
    assert not recipe.output_algorithm.exists()


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


def test_exact_generator_does_not_overwrite_domain_policy(
    tmp_path: Path,
) -> None:
    """The preflight module is a read-only input, not a valid Rust output."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    module = _domain_module(tmp_path)
    original = module.read_bytes()
    with pytest.raises(ValueError, match=r"output_algorithm.*domain_module"):
        write_algorithm(
            replace(recipe, domain_module=module, output_algorithm=module)
        )
    _expect(module.read_bytes() == original, "domain policy was overwritten")


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
            # Planning snapshots each source file before and after replay.
            # Fail the following source-binding identity read, not planning.
            if attempts > _EXACT_PLAN_SOURCE_READS:
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


class _SpoofedGeneratorDigest:
    """A replaced constructor always certifies a stale source digest."""

    def __init__(self, result: str) -> None:
        self.result: str = result

    def hexdigest(self) -> str:
        """Return a false source identity digest.

        Returns:
            An attacker-selected stale digest.

        """
        return self.result


@pytest.mark.parametrize("changed", [False, True])
def test_generator_identity_ignores_hostile_sha256_constructor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, changed: bool
) -> None:
    """Hostile hash callbacks must not approve changed source replay bytes."""
    original = b"first"
    tampered = b"other"
    file = tmp_path / "source.bin"
    _ = file.write_bytes(tampered if changed else original)
    expected = hashlib.sha256(original).hexdigest()
    record = FileRecord(path="source.bin", sha256=expected, size=len(original))
    read_identity = cast(
        "Callable[[Path, FileRecord], bytes]",
        vars(generate_module)["_read_exact_identity_file"],
    )

    def forged_constructor(data: bytes = b"") -> _SpoofedGeneratorDigest:
        del data
        return _SpoofedGeneratorDigest(expected)

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", forged_constructor)
        if changed:
            with pytest.raises(ExactTreeError, match="source identity changed"):
                _ = read_identity(file, record)
        else:
            observed = read_identity(file, record)
            _expect(observed == original, "genuine source replay was rejected")


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


@pytest.mark.parametrize(
    "case",
    [
        (_SOURCE_TREE, "b.bin"),
        (_ORACLE_TREE, "b.bin"),
        (_SOURCE_TREE, "new.bin"),
        (_ORACLE_TREE, "new.bin"),
    ],
)
def test_exact_generator_rechecks_static_trees_after_protection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str],
) -> None:
    """Changes during key protection must not produce a stale transform."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    original_protect = protect_exact_plan
    tree_name, relative = case
    changed_root = (
        recipe.source_root if tree_name == _SOURCE_TREE else recipe.oracle_root
    )
    changed = False

    def change_during_protection(
        exact: ExactAuthoringPlan,
        identity: IdentityTree,
        *,
        binding_policy: SourceBindingPolicy,
        context: bytes,
    ) -> ProtectedExactPlan:
        nonlocal changed
        protected = original_protect(
            exact,
            identity,
            binding_policy=binding_policy,
            context=context,
        )
        _write(changed_root, relative, b"changed during payload protection")
        changed = True
        return protected

    monkeypatch.setattr(
        generate_module, "protect_exact_plan", change_during_protection
    )
    with pytest.raises(ExactTreeError, match=f"{tree_name} tree changed"):
        write_algorithm(recipe)
    _expect(changed, "post-protection mutation was not exercised")
    _expect(not recipe.output_algorithm.exists(), "stale transform was emitted")


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


@pytest.mark.parametrize(
    "invalid_roots",
    [
        ("../escape",),
        ("/absolute",),
        ("src//file",),
        ("src\\file",),
        ("C:/drive",),
        ("C:relative",),
        ("CON",),
        ("src/COM1/child.bin",),
        ("src/stream:fork",),
        ("src/trailing.",),
        ("src\x00file",),
        ("src\ud800file",),
        ("z", "a"),
        ("assets", "assets"),
        ("assets", "assets/nested"),
    ],
)
def test_generator_rejects_unsafe_passthrough_roots_before_domain(
    tmp_path: Path,
    invalid_roots: tuple[str, ...],
) -> None:
    """Unsafe dynamic-root labels cannot reach consumer callbacks."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    _write(recipe.source_root, "reject-source", b"")
    recipe = replace(
        recipe,
        domain_module=_domain_module(tmp_path),
        passthrough_roots=invalid_roots,
    )
    with pytest.raises(ValueError, match=r"passthrough_roots.*canonical"):
        write_algorithm(recipe)
    _expect(not recipe.output_algorithm.exists(), "bad roots wrote output")


@pytest.mark.parametrize(
    "reserved_root", ["CON", "src/COM1/child.bin", "src/trailing."]
)
def test_generator_passthrough_policy_resists_host_checker_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reserved_root: str,
) -> None:
    """A domain hook cannot redefine portable dynamic-root identities."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    recipe = replace(recipe, passthrough_roots=(reserved_root,))

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    def unexpected_preflight(ignored_recipe: DiffRecipe) -> None:
        del ignored_recipe
        message = "reserved root reached domain preflight"
        raise AssertionError(message)

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    monkeypatch.setattr(
        generate_module, "_preflight_domain", unexpected_preflight
    )
    with pytest.raises(ValueError, match=r"passthrough_roots.*canonical"):
        write_algorithm(recipe)
    assert not recipe.output_algorithm.exists()


@pytest.mark.parametrize(
    "invalid_roots", [("src\\unsafe",), ("assets", "assets/child")]
)
def test_generator_recipe_ignores_late_any_hook(
    monkeypatch: pytest.MonkeyPatch, invalid_roots: tuple[str, ...],
) -> None:
    """Recipe preflight rejects unsafe/overlapping dynamic paths under hooks."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            generate_module._validate_passthrough_roots(invalid_roots)
        except ValueError:
            rejected = True
    assert rejected, "late any hook admitted an invalid passthrough root"


@pytest.mark.parametrize(
    "invalid_roots", [("zeta", "alpha"), ("assets", "assets")]
)
def test_generator_recipe_ignores_late_sort_and_set_hooks(
    monkeypatch: pytest.MonkeyPatch, invalid_roots: tuple[str, ...],
) -> None:
    """Recipe preflight rejects duplicated and unordered root identities."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "sorted", lambda values: list(values))
        patched.setattr(builtins, "set", lambda values: list(values))
        try:
            generate_module._validate_passthrough_roots(invalid_roots)
        except ValueError:
            rejected = True
    assert rejected, "late sorted/set hook admitted invalid passthrough roots"


class _ForeignProfile(str):
    """An inexact profile label that still supports text operations."""


@pytest.mark.parametrize(
    ("field", "foreign", "pretend"),
    [
        ("minimum_source_similarity", True, float),
        ("source_binding_maximum_anchors", True, int),
        ("ignore_formatting_for_identity", 7, bool),
        ("profile", _ForeignProfile("synthetic"), str),
        ("mode", object(), TransformMode),
    ],
)
def test_generator_recipe_rejects_late_type_spoofed_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    foreign: object,
    pretend: type,
) -> None:
    """Hostile type hooks cannot admit foreign recipe policy values."""
    recipe = replace(
        _recipe(tmp_path, mode=TransformMode.COMPATIBLE), **{field: foreign}
    )
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return pretend if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            if field == "minimum_source_similarity":
                generate_module._validate_fraction(field, foreign)
            elif field == "source_binding_maximum_anchors":
                _ = generate_module._validate_binding_count(field, foreign, 255)
            elif field == "ignore_formatting_for_identity":
                generate_module._validate_identity_flags(recipe)
            else:
                generate_module._validate_recipe_identity(recipe)
        except TypeError as error:
            rejected = field in str(error)
    assert rejected, f"late type hook admitted foreign {field}"


def test_generator_recipe_rejects_late_type_spoofed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject foreign source paths before executing their fspath hooks."""
    foreign = _ForeignRecipePath(tmp_path / "redirect")
    native_type = type
    path_type = type(Path())
    rejected = False

    def forged_type(value: object) -> type:
        return path_type if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            generate_module._validate_path(foreign, "source_root")
        except TypeError as error:
            rejected = "source_root must use exact pathlib Path" in str(error)
    assert rejected, "late type hook accessed a foreign path"


def test_generator_recipe_rejects_late_type_spoofed_resolve_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign resolved path cannot be approved by a late type hook."""
    path = tmp_path / "source"
    foreign = _ForgedResolvedRecipePath(path)
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return native_type(path) if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(
            generate_module, "_NATIVE_PATH_RESOLVE", lambda _: foreign
        )
        patch.setattr(builtins, "type", forged_type)
        try:
            _ = generate_module._resolve_recipe_path(path, "source_root")
        except ValueError:
            rejected = True
    assert rejected, "late type hook accepted a foreign path resolution"


def test_generator_recipe_rejects_late_tuple_hook_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late tuple replacement must not reorder untrusted root labels."""
    unordered = ("zeta", "alpha")
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", lambda _: unordered)
        try:
            generate_module._validate_passthrough_topology(unordered)
        except ValueError:
            rejected = True
    assert rejected, "late tuple hook admitted unordered passthrough roots"


def test_generator_recipe_rejects_late_type_spoofed_domain_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foreign provenance results cannot masquerade as admitted records."""
    foreign = SimpleNamespace(file_count=1, snapshot_sha256="0" * 64)
    fake_domain = cast(
        "DiffDomain",
        cast(
            "object",
            SimpleNamespace(
                validate_source_provenance=lambda _: foreign,
                validate_authoring_oracle=lambda _: None,
            ),
        ),
    )
    recipe = replace(
        _recipe(tmp_path, mode=TransformMode.COMPATIBLE),
        domain_module=tmp_path / "domain.py",
    )
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return SourcePinEvidence if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(
            generate_module, "load_diff_domain", lambda _: fake_domain
        )
        patch.setattr(builtins, "type", forged_type)
        try:
            generate_module._preflight_domain(recipe)
        except DomainContractError:
            rejected = True
    assert rejected, "late type hook admitted foreign source provenance"


def test_generator_replay_rejects_late_len_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged length cannot approve wrong snapshot size metadata."""
    content = b"immutable replay"
    file = tmp_path / "source.bin"
    record = FileRecord(
        path="source.bin",
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content) + 1,
    )
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is content:
            return record.size
        return native_len(cast("Sized", value))

    with monkeypatch.context() as patch:
        patch.setattr(
            generate_module,
            "read_exact_regular_file",
            lambda _path, _name: content,
        )
        patch.setattr(builtins, "len", forged_len)
        try:
            _ = generate_module._read_exact_identity_file(file, record)
        except ExactTreeError:
            rejected = True
    assert rejected, "late len hook admitted incorrect source size"

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


# Fixed private preflight entrypoints: test the real checks without a writer.
_VALIDATE_FRACTION = cast(
    "Callable[[str, object], None]",
    generate_module.__dict__["_validate_fraction"],
)
_VALIDATE_BINDING_COUNT = cast(
    "Callable[[str, object, int | None], int]",
    generate_module.__dict__["_validate_binding_count"],
)
_VALIDATE_PROFILE_TEXT = cast(
    "Callable[[object], None]",
    generate_module.__dict__["_validate_profile_text"],
)
_VALIDATE_PASSTHROUGH_ROOTS = cast(
    "Callable[[object], None]",
    generate_module.__dict__["_validate_passthrough_roots"],
)
_VALIDATE_IDENTITY_FLAGS = cast(
    "Callable[[DiffRecipe], None]",
    generate_module.__dict__["_validate_identity_flags"],
)


@pytest.mark.parametrize(
    ("native_name", "invalid"),
    [("int", True), ("float", True)],
)
def test_recipe_fraction_rejects_late_numeric_alias_for_boolean(
    monkeypatch: pytest.MonkeyPatch,
    native_name: str,
    invalid: object,
) -> None:
    """Late number aliases cannot certify Boolean policy thresholds."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, native_name, bool)
        try:
            _VALIDATE_FRACTION("minimum_source_similarity", invalid)
        except TypeError, ValueError:
            rejected = True
    assert rejected, "Boolean fraction passed a late numeric alias"


def test_recipe_binding_count_rejects_late_integer_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Boolean cannot become an exact share count through an int alias."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            invalid_count: object = True
            _ = _VALIDATE_BINDING_COUNT(
                "source_binding_maximum_anchors", invalid_count, 255
            )
        except TypeError:
            rejected = True
    assert rejected, "Boolean share count passed late integer alias"


def test_recipe_profile_rejects_late_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign profile strings cannot authenticate a public target identity."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignProfile)
        try:
            _VALIDATE_PROFILE_TEXT(_ForeignProfile("foreign"))
        except TypeError as error:
            rejected = _EXACT_STRING_TYPE in error.args[0]
    assert rejected, "subclassed profile passed late string alias"


def test_recipe_passthrough_rejects_late_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign root strings cannot pass exact passthrough admission."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignProfile)
        try:
            _VALIDATE_PASSTHROUGH_ROOTS((_ForeignProfile("assets"),))
        except TypeError as error:
            rejected = _EXACT_STRING_TYPE in error.args[0]
    assert rejected, "foreign passthrough path passed late string alias"


def test_recipe_identity_flags_reject_late_boolean_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integers cannot masquerade as formatting flags after a late alias."""
    recipe = replace(
        _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE),
        ignore_comments_for_identity=cast("bool", cast("object", 1)),
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bool", int)
        try:
            _VALIDATE_IDENTITY_FLAGS(recipe)
        except TypeError:
            rejected = True
    assert rejected, "integer formatting flag passed late bool alias"


def test_recipe_native_metadata_survives_late_type_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid native fields remain valid despite foreign builtin names."""
    recipe = _recipe(tmp_path, mode=TransformMode.EXACT_BASELINE)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        _VALIDATE_FRACTION("minimum_source_similarity", 1)
        _ = _VALIDATE_BINDING_COUNT("source_binding_maximum_anchors", 2, 255)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "float", bool)
        _VALIDATE_FRACTION("minimum_source_similarity", 0.5)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignProfile)
        _VALIDATE_PROFILE_TEXT("native-profile")
    _VALIDATE_PASSTHROUGH_ROOTS(("assets",))
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bool", int)
        _VALIDATE_IDENTITY_FLAGS(recipe)
