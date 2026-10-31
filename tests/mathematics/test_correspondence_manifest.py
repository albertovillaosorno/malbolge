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
#   - Regression tests for equation-to-executable correspondence traceability.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for equation-to-executable correspondence traceability."""

from __future__ import annotations

# Focused tests intentionally exercise the validator's private admission path.
# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false
import os
from pathlib import Path

import pytest

from scripts.validate import math_correspondence as validator

EXPECTED_EQUATIONS = 275
SOURCE_RECHECK = 3
EQUATION_KIND = "equation"
LEAF_KIND = "leaf"
TEX_LEAF_KIND = "tex-leaf"
REPOSITORY_RELATIVE_ERROR = "must be repository-relative"


def _expect_invalid(text: str) -> None:
    try:
        _ = validator.validate_text(text)
    except validator.CorrespondenceError:
        return
    message = "invalid mathematical correspondence unexpectedly succeeded"
    raise AssertionError(message)


def test_repository_correspondence_graph_is_closed() -> None:
    """Every normative equation label maps to existing executable evidence."""
    entries = validator.validate_repository()
    assert len(entries) == EXPECTED_EQUATIONS


def test_drive_relative_equation_path_is_not_repository_relative() -> None:
    """Windows drive-relative syntax cannot escape equation-source authority."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    marker = next(
        line for line in text.splitlines() if line.startswith("tex = ")
    )
    changed = text.replace(marker, 'tex = "D:escape"', 1)
    with pytest.raises(
        validator.CorrespondenceError,
        match=REPOSITORY_RELATIVE_ERROR,
    ):
        _ = validator.validate_text(changed)


def test_unknown_manifest_label_leaves_equation_unmapped() -> None:
    """A renamed manifest label cannot orphan the normative equation."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        'label = "eq:classic-crazy"',
        'label = "eq:classic-crazy-missing"',
        1,
    )
    _expect_invalid(changed)


def test_unknown_test_function_fails_closed() -> None:
    """A stale test-function reference is a correspondence failure."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        "crazy_chunks_match_scalar_definition_in_both_positions",
        "test_function_that_does_not_exist",
        1,
    )
    _expect_invalid(changed)


def test_duplicate_toml_key_fails_closed() -> None:
    """Duplicate manifest authority cannot be silently overwritten."""
    text = validator.MANIFEST.read_text(encoding="utf-8")
    changed = text.replace(
        "schema_version = 1",
        "schema_version = 1\nschema_version = 1",
        1,
    )
    _expect_invalid(changed)


def test_research_mirror_test_surface_is_admitted() -> None:
    """Algorithm-owned research tests are valid correspondence evidence."""
    path = "algorithms/example-research/tests/evidence.rs"
    assert validator.evidence_path_allowed(path)


def test_non_test_algorithm_surface_is_rejected() -> None:
    """Research implementation files cannot masquerade as test evidence."""
    path = "algorithms/example-research/state_graph.rs"
    assert not validator.evidence_path_allowed(path)


@pytest.mark.parametrize("kind", ["equation", "evidence"])
@pytest.mark.parametrize("redirected", ["leaf", "parent"])
def test_correspondence_rejects_redirected_repository_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    *,
    redirected: str,
) -> None:
    """An external alias cannot count as a real equation or test source."""
    directory = tmp_path / ("math" if kind == EQUATION_KIND else "tests")
    directory.mkdir()
    source = directory / (
        "model.tex" if kind == EQUATION_KIND else "evidence.rs"
    )
    _ = source.write_text("fn test_example() {}", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    relative = source.relative_to(tmp_path).as_posix()
    assert validator._repository_path(relative, kind) == source
    external = tmp_path / "external"
    external.mkdir()
    victim = source if redirected == LEAF_KIND else directory
    outside = external / victim.name
    _ = victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.CorrespondenceError, match="redirect"):
        _ = validator._repository_path(relative, kind)


def test_correspondence_rejects_redirected_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The source of the traceability graph is itself physical evidence."""
    outside = tmp_path / "outside.toml"
    _ = outside.write_text("schema_version = 1", encoding="utf-8")
    manifest = tmp_path / "correspondence.toml"
    manifest.symlink_to(outside)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MANIFEST", manifest)

    def skip_validation(_text: str) -> tuple[()]:
        _ = _text
        return ()

    monkeypatch.setattr(validator, "validate_text", skip_validation)
    with pytest.raises(validator.CorrespondenceError, match="redirect"):
        _ = validator.validate_repository()


@pytest.mark.parametrize("redirected", ["tex-leaf", "tex-parent"])
def test_correspondence_label_scan_rejects_redirects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    """Label closure cannot silently adopt or omit redirected TeX trees."""
    root = tmp_path / "math"
    source_directory = root / "algorithms"
    source_directory.mkdir(parents=True)
    original = source_directory / "paper.tex"
    _ = original.write_text(r"\label{eq:fixture}", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", root)
    assert validator._equation_labels() == frozenset({"eq:fixture"})
    external = tmp_path / "external"
    external.mkdir()
    victim = original if redirected == TEX_LEAF_KIND else source_directory
    outside = external / victim.name
    _ = victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.CorrespondenceError, match="redirect"):
        _ = validator._equation_labels()


def test_correspondence_invalid_utf8_is_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed TeX source is a typed traceability failure."""
    math_root = tmp_path / "math"
    math_root.mkdir()
    _ = (math_root / "paper.tex").write_bytes(b"\xff")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    with pytest.raises(validator.CorrespondenceError, match="UTF-8"):
        _ = validator._equation_labels()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO requires POSIX")
def test_correspondence_rejects_fifo_test_evidence_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A named pipe cannot become an executable-equation test witness."""
    evidence = tmp_path / "tests" / "witness.py"
    evidence.parent.mkdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO creation unsupported on host")
    mkfifo(evidence)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(validator.CorrespondenceError, match="physical regular"):
        _ = validator._repository_path("tests/witness.py", "evidence path")


def test_correspondence_rejects_repository_root_as_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty relative path is not evidence of an equation."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(
        validator.CorrespondenceError, match="regular repository file"
    ):
        _ = validator._repository_path(".", "equation source")


def test_correspondence_source_rejects_replaced_inode_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Physical path admission cannot authorize a different opened inode."""
    source = tmp_path / "witness.rs"
    _ = source.write_text("fn test_example() {}", encoding="utf-8")
    replacement = tmp_path / "replacement.rs"
    _ = replacement.write_bytes(source.read_bytes())
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = replacement.replace(source)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(
        validator.CorrespondenceError, match="changed before read"
    ):
        _ = validator._read_source_text(source, "witness")
    assert swapped


def test_correspondence_source_rejects_replaced_inode_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical bytes from a renamed source do not preserve file identity."""
    source = tmp_path / "witness.rs"
    _ = source.write_text("fn test_example() {}", encoding="utf-8")
    replacement = tmp_path / "replacement.rs"
    _ = replacement.write_bytes(source.read_bytes())
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    real_lstat = Path.lstat
    seen = 0

    def replace_at_recheck(path: Path) -> os.stat_result:
        nonlocal seen
        if path == source:
            seen += 1
            if seen == SOURCE_RECHECK:
                _ = replacement.replace(source)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", replace_at_recheck)
    with pytest.raises(validator.CorrespondenceError, match="changed"):
        _ = validator._read_source_text(source, "witness")
    assert seen >= SOURCE_RECHECK


def test_correspondence_source_rejects_directory_redirect_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parent symlink inserted after admission does not supply test evidence."""
    parent = tmp_path / "tests"
    parent.mkdir()
    source = parent / "witness.rs"
    _ = source.write_text("fn test_example() {}", encoding="utf-8")
    restored = tmp_path / "physical-tests"
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    real_open = os.open
    swapped = False

    def redirect_at_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = parent.rename(restored)
            _ = parent.symlink_to(restored, target_is_directory=True)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", redirect_at_open)
    with pytest.raises(validator.CorrespondenceError, match="redirect"):
        _ = validator._read_source_text(source, "witness")
    assert swapped


def test_correspondence_source_rejects_oversized_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository evidence reads are bounded before UTF-8 decoding."""
    source = tmp_path / "huge.rs"
    with source.open("wb") as stream:
        _ = stream.truncate(4 * 1024 * 1024 + 1)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(validator.CorrespondenceError, match="byte limit"):
        _ = validator._read_source_text(source, "witness")


def test_correspondence_source_rejects_in_place_mutation_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-inode write during validation cannot preserve evidence."""
    source = tmp_path / "witness.rs"
    _ = source.write_text("fn test_example() {}", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    real_lstat = Path.lstat
    seen = 0

    def mutate_at_recheck(path: Path) -> os.stat_result:
        nonlocal seen
        if path == source:
            seen += 1
            if seen == SOURCE_RECHECK:
                with source.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", mutate_at_recheck)
    with pytest.raises(validator.CorrespondenceError, match="changed"):
        _ = validator._read_source_text(source, "witness")
    assert seen >= SOURCE_RECHECK


def test_correspondence_source_rejects_nonregular_read_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct source reading never opens directories or writerless FIFOs."""
    source = tmp_path / "witness.rs"
    source.mkdir()
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(validator.CorrespondenceError, match="physical regular"):
        _ = validator._read_source_text(source, "witness")
    source.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO creation unsupported on host")
    mkfifo(source)
    with pytest.raises(validator.CorrespondenceError, match="physical regular"):
        _ = validator._read_source_text(source, "witness")
