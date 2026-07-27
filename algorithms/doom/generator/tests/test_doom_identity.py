# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Synthetic tests for DOOM C source identity."""

from typing import TYPE_CHECKING

import pytest

from algorithms.doom.generator.doom import DoomIdentityError
from algorithms.doom.generator.doom import build_identity_tree
from algorithms.doom.generator.doom import canonicalize_c_identity

if TYPE_CHECKING:
    from pathlib import Path


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_comments_and_formatting_do_not_change_c_identity() -> None:
    """Ignore comment text and ordinary C presentation changes."""
    compact = b"int main(void){/* old comment */return 0;}\n"
    formatted = b"int\tmain ( void ) {\n// new comment\nreturn 0 ;\n}\n"
    _expect(
        canonicalize_c_identity(compact) == canonicalize_c_identity(formatted),
        "comment/format-only variant changed identity",
    )


def test_comment_markers_inside_literals_remain_semantic() -> None:
    """Never strip comment-looking bytes from C literals."""
    first = canonicalize_c_identity(b'char *s = "/* alpha */";\n')
    second = canonicalize_c_identity(b'char *s = "/* beta */";\n')
    _expect(first != second, "literal contents were treated as comments")


def test_whitespace_that_changes_tokenization_changes_identity() -> None:
    """Distinguish two plus tokens from the increment punctuator."""
    separated = canonicalize_c_identity(b"x = a + +b;\n")
    increment = canonicalize_c_identity(b"x = a++ + b;\n")
    _expect(separated != increment, "token-boundary change was ignored")


def test_preprocessor_line_end_is_identity_evidence() -> None:
    """Preserve directive termination while ignoring ordinary newlines."""
    two_lines = canonicalize_c_identity(b"#define X 1\nint y;\n")
    one_line = canonicalize_c_identity(b"#define X 1 int y;\n")
    _expect(two_lines != one_line, "preprocessor newline was discarded")


def test_backslash_newline_splicing_precedes_tokenization() -> None:
    """Treat a physically split directive as its logical source line."""
    spliced = canonicalize_c_identity(b"#define X a \\\n + b\n")
    logical = canonicalize_c_identity(b"#define X a + b\n")
    _expect(spliced == logical, "C line splicing changed logical identity")


def test_unterminated_comment_fails_closed() -> None:
    """Reject malformed C instead of guessing an identity stream."""
    with pytest.raises(DoomIdentityError, match="unterminated C block comment"):
        canonicalize_c_identity(b"int x; /* missing end")


def test_identity_tree_selects_linux_c_and_headers_only(tmp_path: Path) -> None:
    """Exclude WADs and non-Linux source families from DOOM source identity."""
    linux = tmp_path / "linuxdoom-1.10"
    linux.mkdir()
    (linux / "main.c").write_bytes(b"int main(void){return 0;}\n")
    (linux / "defs.H").write_bytes(b"#define VALUE 1\n")
    (linux / "asset.wad").write_bytes(b"opaque")
    ipx = tmp_path / "ipx"
    ipx.mkdir()
    (ipx / "DOOMNET.C").write_bytes(b"int ipx;\n")

    tree = build_identity_tree(tmp_path)
    paths = tuple(item.path for item in tree.files)

    _expect(
        paths == ("linuxdoom-1.10/defs.H", "linuxdoom-1.10/main.c"),
        "DOOM identity selected an opaque or non-Linux file",
    )
