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

import pytest
from scripts.validate import math_specifications as validator

HISTORICAL_TRITS = "N=10"
HISTORICAL_WORDS = "W_{10}=59049"
CURRENT_TRITS = "N=14"
CURRENT_WORDS = "W_{14}=4782969"

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
