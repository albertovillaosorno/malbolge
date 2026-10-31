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
#   - Regression tests for the shared LaTeX mathematics framework.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for the shared LaTeX mathematics framework."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.validate import math_specifications as validator

HISTORICAL_TRITS = "N=10"
HISTORICAL_WORDS = "W_{10}=59049"
CURRENT_TRITS = "N=15"
CURRENT_WORDS = "W_{15}=14348907"

EXPECTED_DOCUMENTS = (
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/adaptive-accelerator-resource-budgeting.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/compact-guest-bytecode-strategy.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/malbolge-specific-optimization-mathematics.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/pytorch-search-orchestration.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/search-pruning-and-state-canonicalization.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/self-modification-state-graph-optimizer.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/stochastic-and-guided-search.tex",
    "src/specification/formal-model/math/specification/malbolge-1998.tex",
    "src/specification/formal-model/math/specification/profile-model.tex",
)


def _relative_documents() -> tuple[str, ...]:
    return tuple(
        path.relative_to(validator.ROOT).as_posix()
        for path in validator.validate_source_layout()
    )


def test_all_math_documents_share_one_notation_framework() -> None:
    """Every standalone document imports the shared notation include."""
    assert _relative_documents() == EXPECTED_DOCUMENTS


def test_shared_notation_is_not_a_standalone_document() -> None:
    """The common macro surface cannot accidentally become another paper."""
    text = validator.NOTATION.read_text(encoding="utf-8")
    assert validator.DOCUMENT_MARKER not in text


def test_math_documents_do_not_double_escape_control_words() -> None:
    """LaTeX commands remain commands rather than escaped line-break text."""
    forbidden = (r"\\begin", r"\\binom")
    for source in validator.document_sources():
        text = source.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), source


def test_build_outputs_are_cache_only_and_source_specific() -> None:
    """Map LaTeX artifacts beneath cache, never beside source."""
    for source in validator.document_sources():
        output = validator.output_directory(source)
        assert output.is_relative_to(validator.CACHE_ROOT)
        assert output.name == source.stem


def test_generic_profile_math_names_historical_and_current_widths() -> None:
    """Specialize the generic model to both canonical widths."""
    path = validator.MATH_ROOT / "specification" / "profile-model.tex"
    text = path.read_text(encoding="utf-8")
    assert HISTORICAL_TRITS in text
    assert HISTORICAL_WORDS in text
    assert CURRENT_TRITS in text
    assert CURRENT_WORDS in text


def _missing_compiler(name: str) -> None:
    _ = name


def test_missing_latex_compiler_fails_with_stable_diagnostic() -> None:
    """Direct validation names the missing tool instead of leaking WinError."""
    with pytest.raises(
        validator.MathSpecificationError,
        match="LaTeX compiler not found: pdflatex",
    ):
        _ = validator.latex_compiler(_missing_compiler)


@pytest.mark.parametrize(
    "redirected",
    ("notation", "document", "document-parent", "math-root"),
)
def test_math_source_layout_rejects_redirected_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    """TeX evidence must be physical under the configured mathematics root."""
    math_root = tmp_path / "math"
    document_root = math_root / "specification"
    document_root.mkdir(parents=True)
    notation = math_root / "malbolge-notation.tex"
    notation.write_text("\n".join(validator.REQUIRED_MACROS), encoding="utf-8")
    document = document_root / "proof.tex"
    document.write_text(
        validator.DOCUMENT_MARKER + "{article}\n" + validator.NOTATION_INCLUDE,
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", notation)
    assert validator.validate_source_layout() == (document,)

    victim = {
        "notation": notation,
        "document": document,
        "document-parent": document_root,
        "math-root": math_root,
    }[redirected]
    external = tmp_path / "external"
    external.mkdir()
    outside = external / victim.name
    victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.MathSpecificationError, match="redirect"):
        _ = validator.validate_source_layout()


def test_math_output_path_rejects_parent_segment_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct build request cannot use a parent segment in its cache path."""
    monkeypatch.setattr(validator, "MATH_ROOT", tmp_path / "math")
    with pytest.raises(validator.MathSpecificationError, match="escape"):
        _ = validator.output_directory(validator.MATH_ROOT / ".." / "outside.tex")


@pytest.mark.parametrize("redirected", ["cache-root", "cache-parent"])
def test_math_compilation_rejects_redirected_cache_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    """A cache alias cannot redirect TeX compiler side effects out of cache."""
    math_root = tmp_path / "math"
    source = math_root / "specification" / "proof.tex"
    source.parent.mkdir(parents=True)
    source.write_text(r"\documentclass{article}", encoding="utf-8")
    cache_root = tmp_path / ".cache" / "latex"
    cache_root.parent.mkdir()
    outside = tmp_path / "external"
    outside.mkdir()
    if redirected == "cache-root":
        cache_root.symlink_to(outside, target_is_directory=True)
    else:
        cache_root.mkdir()
        (cache_root / "specification").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "CACHE_ROOT", cache_root)
    with pytest.raises(validator.MathSpecificationError, match="cache.*redirect"):
        validator._compile_document(source)
    assert not (outside / "proof").exists()


@pytest.mark.parametrize("bad_input", ["notation", "document"])
def test_math_invalid_utf8_is_typed_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_input: str,
) -> None:
    """Malformed TeX never escapes through an uncaught Unicode exception."""
    math_root = tmp_path / "math"
    math_root.mkdir()
    notation = math_root / "malbolge-notation.tex"
    notation.write_text("\n".join(validator.REQUIRED_MACROS), encoding="utf-8")
    document = math_root / "proof.tex"
    document.write_text(
        validator.DOCUMENT_MARKER + "{article}\n" + validator.NOTATION_INCLUDE,
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", notation)
    victim = notation if bad_input == "notation" else document
    victim.write_bytes(b"\xff")
    with pytest.raises(validator.MathSpecificationError, match="UTF-8"):
        validator.validate_source_layout()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixture needs POSIX")
def test_math_discovery_rejects_fifo_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An untrusted TeX pipe is rejected without blocking the validator."""
    math_root = tmp_path / "math"
    math_root.mkdir()
    os.mkfifo(math_root / "untrusted.tex")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    with pytest.raises(validator.MathSpecificationError, match="physical regular"):
        _ = validator.document_sources()


@pytest.mark.parametrize("missing", ["root", "notation"])
def test_math_missing_inputs_retain_explicit_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    """A missing root/include stays distinguishable from a redirect."""
    math_root = tmp_path / "math"
    if missing != "root":
        math_root.mkdir()
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", math_root / "malbolge-notation.tex")
    if missing == "root":
        with pytest.raises(validator.MathSpecificationError, match="root not found"):
            _ = validator.document_sources()
    else:
        with pytest.raises(
            validator.MathSpecificationError, match="notation file is missing"
        ):
            validator.validate_source_layout()
