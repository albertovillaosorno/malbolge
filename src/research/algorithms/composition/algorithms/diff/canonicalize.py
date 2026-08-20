# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
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

_ASCII_WHITESPACE = frozenset(b" \t\n\r\v\f")
_CRLF = b"\r\n"
_CR = b"\r"
_LF = b"\n"
_SPACE = 0x20


def normalize_line_endings(data: bytes) -> bytes:
    """Normalize CRLF and bare CR to LF without other byte changes.

    Returns:
        Bytes with deterministic LF line endings.

    """
    return data.replace(_CRLF, _LF).replace(_CR, _LF)


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
    normalized = normalize_line_endings(data)
    output = bytearray()
    pending_space = False
    for value in normalized:
        if value in _ASCII_WHITESPACE:
            pending_space = bool(output)
            continue
        if pending_space:
            output.append(_SPACE)
        output.append(value)
        pending_space = False
    return bytes(output)


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
    if ignore_formatting:
        return collapse_ascii_whitespace(data)
    return normalize_line_endings(data)
