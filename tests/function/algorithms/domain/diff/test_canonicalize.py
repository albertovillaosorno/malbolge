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
#   - Tests for generic canonical identity helpers.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for generic canonical identity helpers."""

from algorithms.diff.canonicalize import canonicalize_text_identity
from algorithms.diff.canonicalize import collapse_ascii_whitespace
from algorithms.diff.canonicalize import normalize_line_endings

_NORMALIZED_LINES = b"alpha\nbeta\ngamma\n"
_PRESERVED_SPACING = b"alpha  beta\n"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_line_endings_normalize_without_other_changes() -> None:
    """Treat CRLF, CR, and LF as the same textual line boundary."""
    observed = normalize_line_endings(b"alpha\r\nbeta\rgamma\n")
    _expect(observed == _NORMALIZED_LINES, "line endings differ")


def test_ascii_whitespace_collapse_is_deterministic() -> None:
    """Ignore formatting only when a consumer explicitly selects the helper."""
    source = b"  alpha\t beta\r\n gamma  "
    expected = b"alpha beta gamma"
    _expect(collapse_ascii_whitespace(source) == expected, "collapse mismatch")
    _expect(
        canonicalize_text_identity(source, ignore_formatting=True) == expected,
        "identity helper ignored its formatting policy",
    )


def test_formatting_preservation_mode_keeps_spacing() -> None:
    """Line-ending normalization alone must not silently collapse spacing."""
    source = b"alpha  beta\r\n"
    observed = canonicalize_text_identity(source, ignore_formatting=False)
    _expect(observed == _PRESERVED_SPACING, "formatting changed unexpectedly")
