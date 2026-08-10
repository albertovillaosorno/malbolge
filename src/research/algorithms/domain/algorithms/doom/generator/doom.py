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
#   - DOOM-specific source identity and behavior-probe policy.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""
DOOM-specific source identity and future behavior-probe policy.

The generic diff engine consumes canonical identity bytes without understanding
C. This module owns Linux DOOM source selection and a deterministic C lexical
identity view. Output construction never uses this view to delete provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import PurePosixPath
from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
from typing import TYPE_CHECKING

from algorithms.diff.admission import identity_tree
from algorithms.diff.canonicalize import normalize_line_endings
from algorithms.diff.mapped import MappedUnit
from algorithms.diff.mapped import MappedView
from algorithms.diff.provenance import SourcePin
from algorithms.diff.provenance import SourcePinError
from algorithms.diff.provenance import require_source_pin
from algorithms.doom.generator.behavior_probes import behavior_programs
from algorithms.doom.generator.behavior_probes import pinned_probe_context

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.behavior_programs import BehaviorPrograms
    from algorithms.diff.compatible import CompatibleAuthoringPlan
    from algorithms.diff.compatible import CompatibleCorrectionBinding
    from algorithms.diff.probe_exec import ProbeRunContext
    from algorithms.diff.provenance import SourcePinEvidence

DOMAIN_ID = "doom-linux-source"
DOOM_IDENTITY_SUBTREE = "linuxdoom-1.10"
DOOM_UPSTREAM_REPOSITORY = "https://github.com/id-Software/DOOM.git"
DOOM_UPSTREAM_COMMIT = "a77dfb96cb91780ca334d0d4cfd86957558007e0"
DOOM_UPSTREAM_FILE_COUNT = 165
DOOM_UPSTREAM_SNAPSHOT_SHA256 = (
    "20f6b67369b98c3f62b7c8ff34493ef9647c88bce7b85c82b9ecd72bad336d8b"
)
DOOM_SOURCE_PIN = SourcePin(
    repository=DOOM_UPSTREAM_REPOSITORY,
    commit=DOOM_UPSTREAM_COMMIT,
    roots=(
        "LICENSE-MIT.TXT",
        "README.TXT",
        "ipx",
        DOOM_IDENTITY_SUBTREE,
        "sersrc",
        "sndserv",
    ),
    file_count=DOOM_UPSTREAM_FILE_COUNT,
    snapshot_sha256=DOOM_UPSTREAM_SNAPSHOT_SHA256,
)
_SOURCE_ALLOWED_ROOTS = frozenset((*DOOM_SOURCE_PIN.roots, ".git", "data"))
_QUALITY_ORACLE_ROOTS = frozenset({
    "data",
    DOOM_IDENTITY_SUBTREE,
    "LICENSE-MIT",
})
_QUALITY_ORACLE_DIRECTORIES = frozenset({"data", DOOM_IDENTITY_SUBTREE})
_QUALITY_ORACLE_FILES = frozenset({"LICENSE-MIT"})

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
_CARRIAGE_RETURN = ord("\r")
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


@dataclass(frozen=True, slots=True)
class _LogicalByte:
    """One phase-normalized byte and the raw span that produced it."""

    value: int
    raw_start: int
    raw_end: int


@dataclass(slots=True)
class _MappedTokenizeState:
    """Mutable scanner state for canonical units with raw source spans."""

    cursor: int = 0
    at_line_start: bool = True
    in_directive: bool = False
    units: list[MappedUnit] = field(default_factory=list)


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


def _framed_token(kind: bytes, token: bytes = b"") -> bytes:
    if len(token) > _MAX_FRAME_LENGTH:
        message = "C identity token exceeds frame length limit"
        raise DoomIdentityError(message)
    return b"".join((
        kind,
        len(token).to_bytes(_FRAME_LENGTH_BYTES, byteorder="big"),
        token,
    ))


def _append_frame(output: bytearray, kind: bytes, token: bytes = b"") -> None:
    output.extend(_framed_token(kind, token))


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


def _normalized_logical_bytes(data: bytes) -> tuple[_LogicalByte, ...]:
    logical: list[_LogicalByte] = []
    cursor = 0
    while cursor < len(data):
        value = data[cursor]
        if value == _CARRIAGE_RETURN:
            raw_end = cursor + 1
            if raw_end < len(data) and data[raw_end] == _LINE_FEED:
                raw_end += 1
            logical.append(
                _LogicalByte(
                    value=_LINE_FEED,
                    raw_start=cursor,
                    raw_end=raw_end,
                )
            )
            cursor = raw_end
            continue
        logical.append(
            _LogicalByte(value=value, raw_start=cursor, raw_end=cursor + 1)
        )
        cursor += 1
    return tuple(logical)


def _splice_logical_bytes(
    logical: tuple[_LogicalByte, ...],
) -> tuple[_LogicalByte, ...]:
    output: list[_LogicalByte] = []
    cursor = 0
    while cursor < len(logical):
        if (
            logical[cursor].value == _BACKSLASH
            and cursor + 1 < len(logical)
            and logical[cursor + 1].value == _LINE_FEED
        ):
            cursor += 2
            continue
        output.append(logical[cursor])
        cursor += 1
    return tuple(output)


def _logical_source(data: bytes) -> tuple[bytes, tuple[_LogicalByte, ...]]:
    logical = _splice_logical_bytes(_normalized_logical_bytes(data))
    return bytes(item.value for item in logical), logical


def _append_mapped_directive_end(
    state: _MappedTokenizeState,
    *,
    raw_start: int,
    raw_end: int,
) -> None:
    if state.in_directive:
        state.units.append(
            MappedUnit(
                canonical=_framed_token(_KIND_DIRECTIVE_END),
                raw_start=raw_start,
                raw_end=raw_end,
            )
        )
    state.at_line_start = True
    state.in_directive = False


def _consume_mapped_whitespace(
    logical_data: bytes,
    logical: tuple[_LogicalByte, ...],
    state: _MappedTokenizeState,
) -> bool:
    value = logical_data[state.cursor]
    if value not in _ASCII_WHITESPACE:
        return False
    if value == _LINE_FEED:
        span = logical[state.cursor]
        _append_mapped_directive_end(
            state,
            raw_start=span.raw_start,
            raw_end=span.raw_end,
        )
    state.cursor += 1
    return True


def _mapped_block_comment_end(
    logical_data: bytes,
    logical: tuple[_LogicalByte, ...],
    state: _MappedTokenizeState,
) -> int:
    cursor = state.cursor + len(_BLOCK_COMMENT_START)
    while cursor < len(logical_data):
        if logical_data.startswith(_BLOCK_COMMENT_END, cursor):
            return cursor + len(_BLOCK_COMMENT_END)
        if logical_data[cursor] == _LINE_FEED:
            span = logical[cursor]
            _append_mapped_directive_end(
                state,
                raw_start=span.raw_start,
                raw_end=span.raw_end,
            )
        cursor += 1
    message = "unterminated C block comment"
    raise DoomIdentityError(message)


def _consume_mapped_comment(
    logical_data: bytes,
    logical: tuple[_LogicalByte, ...],
    state: _MappedTokenizeState,
) -> bool:
    if logical_data.startswith(_LINE_COMMENT, state.cursor):
        cursor = state.cursor + len(_LINE_COMMENT)
        while cursor < len(logical_data) and logical_data[cursor] != _LINE_FEED:
            cursor += 1
        state.cursor = cursor
        return True
    if logical_data.startswith(_BLOCK_COMMENT_START, state.cursor):
        state.cursor = _mapped_block_comment_end(logical_data, logical, state)
        return True
    return False


def _consume_mapped_token(
    logical_data: bytes,
    logical: tuple[_LogicalByte, ...],
    state: _MappedTokenizeState,
) -> None:
    kind, token, end = _next_token(logical_data, state.cursor)
    if state.at_line_start and token in _DIRECTIVE_MARKERS:
        state.in_directive = True
    state.at_line_start = False
    first = logical[state.cursor]
    last = logical[end - 1]
    state.units.append(
        MappedUnit(
            canonical=_framed_token(kind, token),
            raw_start=first.raw_start,
            raw_end=last.raw_end,
        )
    )
    state.cursor = end


def _mapped_units(
    logical_data: bytes,
    logical: tuple[_LogicalByte, ...],
    raw_length: int,
) -> tuple[MappedUnit, ...]:
    state = _MappedTokenizeState()
    while state.cursor < len(logical_data):
        if _consume_mapped_whitespace(logical_data, logical, state):
            continue
        is_literal = _literal_end(logical_data, state.cursor) is not None
        if not is_literal and _consume_mapped_comment(
            logical_data,
            logical,
            state,
        ):
            continue
        _consume_mapped_token(logical_data, logical, state)
    if state.in_directive:
        _append_mapped_directive_end(
            state,
            raw_start=raw_length,
            raw_end=raw_length,
        )
    return tuple(state.units)


def mapped_c_identity(data: bytes) -> MappedView:
    """Build C identity units while retaining exact raw candidate byte spans.

    Returns:
        Canonical units whose concatenation matches `canonicalize_c_identity`.

    Raises:
        DoomIdentityError: Source contains NUL or malformed C comments/literals.

    """
    if _ZERO_BYTE in data:
        message = "NUL byte is not accepted in C source identity"
        raise DoomIdentityError(message)
    logical_data, logical = _logical_source(data)
    units = _mapped_units(logical_data, logical, len(data))
    return MappedView(raw=data, units=units)


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


def _raise_identity_walk_error(error: OSError) -> None:
    message = f"DOOM source identity traversal failed: {error}"
    raise DoomIdentityError(message) from error


def _identity_entry_mode(path: Path, description: str) -> int | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        message = f"DOOM identity {description} status failed: {path}: {error}"
        raise DoomIdentityError(message) from error
    if S_ISLNK(mode) or path.is_junction():
        message = f"symlink is not accepted in DOOM source identity: {path}"
        raise DoomIdentityError(message)
    return mode


def _resolved_identity_root(source_root: Path) -> Path:
    mode = _identity_entry_mode(source_root, "root")
    if mode is None or not S_ISDIR(mode):
        message = f"missing DOOM source root: {source_root}"
        raise DoomIdentityError(message)
    try:
        return source_root.resolve(strict=True)
    except OSError as error:
        message = (
            f"DOOM identity root resolution failed: {source_root}: {error}"
        )
        raise DoomIdentityError(message) from error


def _selected_identity_file(path: Path) -> Path | None:
    mode = _identity_entry_mode(path, "entry")
    if mode is None:
        message = f"DOOM source identity entry disappeared: {path}"
        raise DoomIdentityError(message)
    if S_ISDIR(mode):
        return None
    if not S_ISREG(mode):
        message = (
            f"special entry is not accepted in DOOM source identity: {path}"
        )
        raise DoomIdentityError(message)
    return path if path.suffix.lower() in _CODE_SUFFIXES else None


def _identity_source_files(code_root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in code_root.walk(
        on_error=_raise_identity_walk_error
    ):
        paths.extend(directory / name for name in directories)
        paths.extend(directory / name for name in filenames)
    return tuple(
        selected
        for path in sorted(paths)
        if (selected := _selected_identity_file(path)) is not None
    )


def _read_identity_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        message = f"DOOM identity entry read failed: {path}: {error}"
        raise DoomIdentityError(message) from error


def build_identity_tree(source_root: Path) -> IdentityTree:
    """Build Linux DOOM C/H identity without opaque assets or IPX code.

    Returns:
        Canonical identity for C and header files under `linuxdoom-1.10` only.

    Raises:
        DoomIdentityError: The expected source subtree is missing or contains
        no selected code.

    """
    resolved_root = _resolved_identity_root(source_root)
    code_root = resolved_root / DOOM_IDENTITY_SUBTREE
    mode = _identity_entry_mode(code_root, "subtree")
    if mode is None or not S_ISDIR(mode):
        message = f"missing DOOM identity subtree: {code_root}"
        raise DoomIdentityError(message)
    source_files = _identity_source_files(code_root)
    if not source_files:
        message = f"no C/H source identity files found under: {code_root}"
        raise DoomIdentityError(message)
    canonical_files = {
        path.relative_to(resolved_root).as_posix(): canonicalize_c_identity(
            _read_identity_bytes(path)
        )
        for path in source_files
    }
    return identity_tree(canonical_files)


def _require_source_root_directory(source_root: Path) -> None:
    try:
        mode = source_root.lstat().st_mode
    except FileNotFoundError as error:
        message = f"missing DOOM source root: {source_root}"
        raise SourcePinError(message) from error
    except OSError as error:
        message = f"DOOM source root status failed: {source_root}: {error}"
        raise SourcePinError(message) from error
    if S_ISLNK(mode) or source_root.is_junction():
        message = f"DOOM source root must not be linked: {source_root}"
        raise SourcePinError(message)
    if not S_ISDIR(mode):
        message = f"missing DOOM source root: {source_root}"
        raise SourcePinError(message)


def _source_root_names(source_root: Path) -> frozenset[str]:
    try:
        return frozenset(entry.name for entry in source_root.iterdir())
    except OSError as error:
        message = f"DOOM source root enumeration failed: {source_root}: {error}"
        raise SourcePinError(message) from error


def _require_source_root_surface(source_root: Path) -> None:
    _require_source_root_directory(source_root)
    names = _source_root_names(source_root)
    unexpected = tuple(sorted(names - _SOURCE_ALLOWED_ROOTS))
    if unexpected:
        message = f"unexpected DOOM source root entries: {unexpected!r}"
        raise SourcePinError(message)


def validate_source_provenance(source_root: Path) -> SourcePinEvidence:
    """Require the exact official DOOM source revision used by this profile.

    Returns:
        Matching deterministic source snapshot evidence.

    """
    _require_source_root_surface(source_root)
    return require_source_pin(source_root, DOOM_SOURCE_PIN)


def _quality_oracle_mode(path: Path, description: str) -> int | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        message = (
            f"DOOM quality oracle {description} status failed: {path}: {error}"
        )
        raise DoomIdentityError(message) from error
    if S_ISLNK(mode) or path.is_junction():
        message = (
            f"DOOM quality oracle {description} must not be linked: {path}"
        )
        raise DoomIdentityError(message)
    return mode


def _quality_oracle_entries(oracle_root: Path) -> dict[str, Path]:
    mode = _quality_oracle_mode(oracle_root, "root")
    if mode is None or not S_ISDIR(mode):
        message = f"missing DOOM quality oracle root: {oracle_root}"
        raise DoomIdentityError(message)
    try:
        return {entry.name: entry for entry in oracle_root.iterdir()}
    except OSError as error:
        message = (
            f"DOOM quality oracle enumeration failed: {oracle_root}: {error}"
        )
        raise DoomIdentityError(message) from error


def _require_quality_oracle_names(entries: dict[str, Path]) -> None:
    names = frozenset(entries)
    if names == _QUALITY_ORACLE_ROOTS:
        return
    missing = tuple(sorted(_QUALITY_ORACLE_ROOTS - names))
    unexpected = tuple(sorted(names - _QUALITY_ORACLE_ROOTS))
    message = (
        "DOOM quality oracle root surface mismatch: "
        f"missing={missing!r}; unexpected={unexpected!r}"
    )
    raise DoomIdentityError(message)


def _require_quality_oracle_kinds(entries: dict[str, Path]) -> None:
    for name in _QUALITY_ORACLE_DIRECTORIES:
        mode = _quality_oracle_mode(entries[name], "entry")
        if mode is None or not S_ISDIR(mode):
            message = f"DOOM quality oracle root must be a directory: {name}"
            raise DoomIdentityError(message)
    for name in _QUALITY_ORACLE_FILES:
        mode = _quality_oracle_mode(entries[name], "entry")
        if mode is None or not S_ISREG(mode):
            message = f"DOOM quality oracle root must be a file: {name}"
            raise DoomIdentityError(message)


def validate_authoring_oracle(oracle_root: Path) -> None:
    """Require the expected normalized DOOM oracle root surface."""
    entries = _quality_oracle_entries(oracle_root)
    _require_quality_oracle_names(entries)
    _require_quality_oracle_kinds(entries)


def map_compatible_file(path: str, data: bytes) -> MappedView | None:
    """Map Linux DOOM C/header files for semantic compatible placement.

    Returns:
        Mapped C identity for selected Linux source files, otherwise ``None``.

    """
    candidate = PurePosixPath(path)
    is_linux_code = (
        bool(candidate.parts)
        and candidate.parts[0] == DOOM_IDENTITY_SUBTREE
        and candidate.suffix.lower() in _CODE_SUFFIXES
    )
    return mapped_c_identity(data) if is_linux_code else None


def build_compatible_correction_bindings(
    plan: CompatibleAuthoringPlan,
) -> tuple[CompatibleCorrectionBinding, ...]:
    """Return currently authored semantic correction bindings for DOOM.

    DOOM has no validated bug behavior probes yet, so no semantic edit is
    conditional. The explicit hook keeps that absence part of the domain
    contract rather than letting generic code guess.

    Returns:
        No correction bindings until a DOOM bug probe is independently validated.

    """
    _ = plan
    return ()


def build_behavior_programs() -> BehaviorPrograms:
    """Return the executable behavior programs for this DOOM domain profile.

    Returns:
        Domain-owned portable behavior programs consumed by the generic engine.

    """
    return behavior_programs()


def build_behavior_probe_context(
    source_root: Path,
    repository_root: Path,
) -> ProbeRunContext:
    """Resolve pinned tools for the current DOOM behavior profile.

    Returns:
        Generic probe execution context bound to the candidate source tree.

    """
    return pinned_probe_context(source_root, repository_root)
