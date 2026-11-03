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
#   - Tests for generic canonical identity helpers.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for generic canonical identity helpers."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest
from algorithms.diff.canonicalize import (
    CanonicalIdentityError,
    canonicalize_text_identity,
    collapse_ascii_whitespace,
    normalize_line_endings,
)

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


class _DiscardedCanonicalBuffer:
    """Simulate a consumer-controlled byte accumulator."""

    def append(self, value: int) -> None:
        _ = value

    def __bool__(self) -> bool:
        return False

    def __bytes__(self) -> bytes:
        return b""


def test_canonicalization_ignores_late_bytearray_collector_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late builtin mutation cannot erase canonical source identity."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytearray", _DiscardedCanonicalBuffer)
        observed = collapse_ascii_whitespace(b"alpha   beta")
    _expect(observed == b"alpha beta", "forged collector erased identity")


def test_canonicalization_ignores_late_bool_space_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late builtin mutation cannot remove meaningful token boundaries."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", lambda _: False)
        observed = collapse_ascii_whitespace(b"alpha  beta")
    _expect(observed == b"alpha beta", "forged bool removed token boundary")


def test_late_bool_substitution_cannot_reclassify_formatting_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-boolean policy value cannot become a boolean by builtin swap."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", int)
        with pytest.raises(CanonicalIdentityError, match="exact bool"):
            _ = canonicalize_text_identity(
                b"alpha", ignore_formatting=cast("bool", cast("object", 1))
            )


@pytest.mark.parametrize(
    "identity_helper",
    [normalize_line_endings, collapse_ascii_whitespace],
)
def test_canonicalization_rejects_foreign_bytes(
    identity_helper: Callable[[bytes], bytes],
) -> None:
    """Canonical content must not coerce arbitrary text or mutable buffers."""
    for invalid in ("text", bytearray(b"text"), None):
        with pytest.raises(CanonicalIdentityError, match="exact bytes"):
            _ = identity_helper(cast("bytes", cast("object", invalid)))


@pytest.mark.parametrize("ignore_formatting", [1, 0, "false", None, object()])
def test_canonicalization_rejects_foreign_formatting_policy(
    ignore_formatting: object,
) -> None:
    """Foreign policy values must not silently select identity semantics."""
    with pytest.raises(CanonicalIdentityError, match="exact bool"):
        _ = canonicalize_text_identity(
            b"alpha  beta\n",
            ignore_formatting=cast("bool", ignore_formatting),
        )


def test_canonicalization_text_entry_requires_exact_bytes() -> None:
    """Text identity admission rejects input without implicit coercion."""
    with pytest.raises(CanonicalIdentityError, match="exact bytes"):
        _ = canonicalize_text_identity(
            cast("bytes", cast("object", "not-bytes")),
            ignore_formatting=False,
        )
