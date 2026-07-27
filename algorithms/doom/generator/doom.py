# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""DOOM-specific source identity and future behavior-probe policy.

The generic diff engine consumes canonical identity bytes without understanding
C. This module owns Linux DOOM source selection and a deterministic C lexical
identity view. Output construction never uses this view to delete provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from algorithms.diff.admission import identity_tree
from algorithms.diff.canonicalize import normalize_line_endings

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.admission import IdentityTree

DOMAIN_ID = "doom-linux-source"
DOOM_IDENTITY_SUBTREE = "linuxdoom-1.10"

_CODE_SUFFIXES = frozenset({".c", ".h"})
_ASCII_WHITESPACE = frozenset(b" \t\n\v\f")
_IDENTIFIER_START = frozenset(
    b"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
_IDENTIFIER_CONTINUE = frozenset(
    b"_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)
_PP_NUMBER_CONTINUE = _IDENTIFIER_CONTINUE | frozenset(b".")
_PP_EXPONENT_MARKERS = frozenset(b"eEpP")
_LITERAL_PREFIXES = (
    b'u8"',
    b"u8'",
    b'L"',
    b'U"',
    b'u"',
    b"L'",
    b"U'",
    b"u'",
    b'"',
    b"'",
)
_PUNCTUATORS = tuple(
    sorted(
        (
            b"%:%:",
            b">>=",
            b"<<=",
            b"...",
            b"##",
            b"->",
            b"++",
            b"--",
            b"<<",
            b">>",
            b"<=",
            b">=",
            b"==",
            b"!=",
            b"&&",
            b"||",
            b"*=",
            b"/=",
            b"%=",
            b"+=",
            b"-=",
            b"&=",
            b"^=",
            b"|=",
            b"<:",
            b":>",
            b"<%",
            b"%>",
            b"%:",
        ),
        key=len,
        reverse=True,
    )
)
_LINE_COMMENT = b"//"
_BLOCK_COMMENT_START = b"/*"
_BLOCK_COMMENT_END = b"*/"
_LINE_SPLICE = b"\\\n"
_DIRECTIVE_MARKERS = frozenset({b"#", b"%:"})
_KIND_IDENTIFIER = b"I"
_KIND_NUMBER = b"N"
_KIND_STRING = b"S"
_KIND_CHARACTER = b"C"
_KIND_PUNCTUATOR = b"P"
_KIND_DIRECTIVE_END = b"E"
_QUOTE_DOUBLE = ord('"')
_QUOTE_SINGLE = ord("'")
_BACKSLASH = ord("\\")
_LINE_FEED = ord("\n")
_DOT = ord(".")
_PLUS = ord("+")
_MINUS = ord("-")
_SPACE = ord(" ")
_ZERO_BYTE = 0
_FRAME_LENGTH_BYTES = 4
_MAX_FRAME_LENGTH = (1 << (8 * _FRAME_LENGTH_BYTES)) - 1


class DoomIdentityError(ValueError):
    """Raised when a DOOM source identity view cannot be built safely."""


@dataclass(slots=True)
class _TokenizeState:
    """Mutable scanner state for one canonical identity pass."""

    cursor: int = 0
    at_line_start: bool = True
    in_directive: bool = False
    output: bytearray = field(default_factory=bytearray)


def _translation_phase_lines(data: bytes) -> bytes:
    return normalize_line_endings(data).replace(_LINE_SPLICE, b"")


def _quoted_end(data: bytes, quote_offset: int) -> int:
    quote = data[quote_offset]
    cursor = quote_offset + 1
    while cursor < len(data):
        value = data[cursor]
        if value == _BACKSLASH:
            cursor += 2
            continue
        if value == quote:
            return cursor + 1
        if value == _LINE_FEED:
            message = "unescaped newline in C string or character literal"
            raise DoomIdentityError(message)
        cursor += 1
    message = "unterminated C string or character literal"
    raise DoomIdentityError(message)


def _strip_block_comment(data: bytes, offset: int, output: bytearray) -> int:
    cursor = offset + len(_BLOCK_COMMENT_START)
    output.append(_SPACE)
    while cursor < len(data):
        if data.startswith(_BLOCK_COMMENT_END, cursor):
            output.append(_SPACE)
            return cursor + len(_BLOCK_COMMENT_END)
        if data[cursor] == _LINE_FEED:
            output.append(_LINE_FEED)
        cursor += 1
    message = "unterminated C block comment"
    raise DoomIdentityError(message)


def _strip_line_comment(data: bytes, offset: int, output: bytearray) -> int:
    output.append(_SPACE)
    cursor = offset + len(_LINE_COMMENT)
    while cursor < len(data) and data[cursor] != _LINE_FEED:
        cursor += 1
    return cursor


def _copy_quoted(data: bytes, offset: int, output: bytearray) -> int:
    end = _quoted_end(data, offset)
    output.extend(data[offset:end])
    return end


def _comment_or_literal_end(
    data: bytes,
    offset: int,
    output: bytearray,
) -> int | None:
    value = data[offset]
    end: int | None = None
    if value in {_QUOTE_DOUBLE, _QUOTE_SINGLE}:
        end = _copy_quoted(data, offset, output)
    elif data.startswith(_LINE_COMMENT, offset):
        end = _strip_line_comment(data, offset, output)
    elif data.startswith(_BLOCK_COMMENT_START, offset):
        end = _strip_block_comment(data, offset, output)
    return end


def _strip_comments(data: bytes) -> bytes:
    output = bytearray()
    cursor = 0
    while cursor < len(data):
        special_end = _comment_or_literal_end(data, cursor, output)
        if special_end is not None:
            cursor = special_end
            continue
        output.append(data[cursor])
        cursor += 1
    return bytes(output)


def _literal_end(data: bytes, offset: int) -> tuple[bytes, int] | None:
    for prefix in _LITERAL_PREFIXES:
        if not data.startswith(prefix, offset):
            continue
        quote_offset = offset + len(prefix) - 1
        end = _quoted_end(data, quote_offset)
        kind = (
            _KIND_CHARACTER
            if data[quote_offset] == _QUOTE_SINGLE
            else _KIND_STRING
        )
        return kind, end
    return None


def _identifier_end(data: bytes, offset: int) -> int:
    cursor = offset + 1
    while cursor < len(data) and data[cursor] in _IDENTIFIER_CONTINUE:
        cursor += 1
    return cursor


def _number_end(data: bytes, offset: int) -> int:
    cursor = offset + 1
    while cursor < len(data):
        value = data[cursor]
        if value in _PP_NUMBER_CONTINUE:
            cursor += 1
            continue
        previous = data[cursor - 1]
        if value in {_PLUS, _MINUS} and previous in _PP_EXPONENT_MARKERS:
            cursor += 1
            continue
        break
    return cursor


def _is_number_start(data: bytes, offset: int) -> bool:
    value = data[offset]
    if ord("0") <= value <= ord("9"):
        return True
    next_offset = offset + 1
    return (
        value == _DOT
        and next_offset < len(data)
        and ord("0") <= data[next_offset] <= ord("9")
    )


def _punctuator_end(data: bytes, offset: int) -> int:
    for punctuator in _PUNCTUATORS:
        if data.startswith(punctuator, offset):
            return offset + len(punctuator)
    return offset + 1


def _next_token(data: bytes, offset: int) -> tuple[bytes, bytes, int]:
    literal = _literal_end(data, offset)
    if literal is not None:
        kind, end = literal
    elif data[offset] in _IDENTIFIER_START:
        kind = _KIND_IDENTIFIER
        end = _identifier_end(data, offset)
    elif _is_number_start(data, offset):
        kind = _KIND_NUMBER
        end = _number_end(data, offset)
    else:
        kind = _KIND_PUNCTUATOR
        end = _punctuator_end(data, offset)
    return kind, data[offset:end], end


def _append_frame(output: bytearray, kind: bytes, token: bytes = b"") -> None:
    if len(token) > _MAX_FRAME_LENGTH:
        message = "C identity token exceeds frame length limit"
        raise DoomIdentityError(message)
    output.extend(kind)
    output.extend(len(token).to_bytes(_FRAME_LENGTH_BYTES, byteorder="big"))
    output.extend(token)


def _finish_logical_line(state: _TokenizeState) -> None:
    if state.in_directive:
        _append_frame(state.output, _KIND_DIRECTIVE_END)
    state.at_line_start = True
    state.in_directive = False


def _consume_whitespace(data: bytes, state: _TokenizeState) -> bool:
    value = data[state.cursor]
    if value not in _ASCII_WHITESPACE:
        return False
    if value == _LINE_FEED:
        _finish_logical_line(state)
    state.cursor += 1
    return True


def _consume_token(data: bytes, state: _TokenizeState) -> None:
    kind, token, end = _next_token(data, state.cursor)
    if state.at_line_start and token in _DIRECTIVE_MARKERS:
        state.in_directive = True
    state.at_line_start = False
    _append_frame(state.output, kind, token)
    state.cursor = end


def _tokenize_identity(data: bytes) -> bytes:
    if _ZERO_BYTE in data:
        message = "NUL byte is not accepted in C source identity"
        raise DoomIdentityError(message)
    state = _TokenizeState()
    while state.cursor < len(data):
        if _consume_whitespace(data, state):
            continue
        _consume_token(data, state)
    if state.in_directive:
        _finish_logical_line(state)
    return bytes(state.output)


def canonicalize_c_identity(data: bytes) -> bytes:
    """Build DOOM C identity while ignoring comments and presentation.

    C line splicing is applied before comment removal. Comments become
    whitespace while their newlines remain, then preprocessing tokens are
    framed explicitly. Normal source newlines are formatting; preprocessing
    directive termination remains identity evidence.

    Returns:
        Deterministic framed preprocessing-token identity bytes.

    """
    translated = _translation_phase_lines(data)
    without_comments = _strip_comments(translated)
    return _tokenize_identity(without_comments)


def _identity_source_files(code_root: Path) -> tuple[Path, ...]:
    selected: list[Path] = []
    for path in sorted(code_root.rglob("*")):
        if path.is_symlink():
            message = f"symlink is not accepted in DOOM source identity: {path}"
            raise DoomIdentityError(message)
        if path.is_file() and path.suffix.lower() in _CODE_SUFFIXES:
            selected.append(path)
    return tuple(selected)


def build_identity_tree(source_root: Path) -> IdentityTree:
    """Build Linux DOOM C/H identity without opaque assets or IPX code.

    Returns:
        Canonical identity for C and header files under `linuxdoom-1.10` only.

    Raises:
        DoomIdentityError: The expected source subtree is missing or contains
        no selected code.

    """
    resolved_root = source_root.resolve()
    code_root = resolved_root / DOOM_IDENTITY_SUBTREE
    if not code_root.is_dir():
        message = f"missing DOOM identity subtree: {code_root}"
        raise DoomIdentityError(message)
    source_files = _identity_source_files(code_root)
    if not source_files:
        message = f"no C/H source identity files found under: {code_root}"
        raise DoomIdentityError(message)
    canonical_files = {
        path.relative_to(resolved_root).as_posix(): canonicalize_c_identity(
            path.read_bytes()
        )
        for path in source_files
    }
    return identity_tree(canonical_files)
