# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
#   - Generic canonical identity helpers for source admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Generic canonical identity helpers for source admission."""

from __future__ import annotations

import builtins

_ASCII_WHITESPACE = frozenset(b" \t\n\r\v\f")
_CRLF = b"\r\n"
_CR = b"\r"
_LF = b"\n"
_SPACE = 0x20
_NATIVE_BYTEARRAY = bytearray
_NATIVE_BOOL = bool
_NATIVE_BYTES = bytes
_NATIVE_TYPE = builtins.type


class CanonicalIdentityError(ValueError):
    """Raised when generic identity canonicalization inputs are invalid."""


# Retain typed native rejection after a consumer rebinds the public export.
_NATIVE_CANONICAL_IDENTITY_ERROR = CanonicalIdentityError


def normalize_line_endings(data: bytes) -> bytes:
    """Normalize CRLF and bare CR to LF without other byte changes.

    Returns:
        Bytes with deterministic LF line endings.

    Raises:
        CanonicalIdentityError: Input does not use exact bytes.

    """
    if _NATIVE_TYPE(data) is not _NATIVE_BYTES:
        message = "canonical identity input must use exact bytes"
        raise _NATIVE_CANONICAL_IDENTITY_ERROR(message)
    return data.replace(_CRLF, _LF).replace(_CR, _LF)


# The exported helper name may be rebound by consumers after import.
_NATIVE_NORMALIZE_LINE_ENDINGS = normalize_line_endings


def collapse_ascii_whitespace(data: bytes) -> bytes:
    """Collapse ASCII whitespace runs after line-ending normalization.

    This helper is intentionally syntax-agnostic. Consumers must only use it
    where whitespace-insensitive identity is valid; language-aware tokenization
    belongs in the consumer when whitespace can occur inside literals or other
    semantic constructs.

    Returns:
        Canonical bytes with leading/trailing whitespace removed and internal
        runs replaced by one ASCII space.

    """
    normalized = _NATIVE_NORMALIZE_LINE_ENDINGS(data)
    output = _NATIVE_BYTEARRAY()
    pending_space = False
    for value in normalized:
        if value in _ASCII_WHITESPACE:
            pending_space = _NATIVE_BOOL(output)
            continue
        if pending_space:
            output.append(_SPACE)
        output.append(value)
        pending_space = False
    return _NATIVE_BYTES(output)


_NATIVE_COLLAPSE_ASCII_WHITESPACE = collapse_ascii_whitespace


def _require_formatting_policy(value: object) -> bool:
    if _NATIVE_TYPE(value) is not _NATIVE_BOOL:
        message = "identity formatting policy must use exact bool"
        raise _NATIVE_CANONICAL_IDENTITY_ERROR(message)
    return value


_NATIVE_REQUIRE_FORMATTING_POLICY = _require_formatting_policy


def canonicalize_text_identity(
    data: bytes,
    *,
    ignore_formatting: bool,
) -> bytes:
    """Build a generic textual identity view.

    Returns:
        Line-ending-normalized bytes, optionally with ASCII whitespace runs
        collapsed.

    """
    admitted_formatting = _NATIVE_REQUIRE_FORMATTING_POLICY(ignore_formatting)
    if admitted_formatting:
        return _NATIVE_COLLAPSE_ASCII_WHITESPACE(data)
    return _NATIVE_NORMALIZE_LINE_ENDINGS(data)
