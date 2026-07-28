# File:
#   - test_doom_identity.py
# Path:
#   - algorithms/doom/generator/tests/test_doom_identity.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Synthetic tests for DOOM C source identity.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Synthetic tests for DOOM C source identity."""

from typing import TYPE_CHECKING

import pytest

from algorithms.doom.generator.doom import DOOM_SOURCE_PIN
from algorithms.doom.generator.doom import DOOM_UPSTREAM_COMMIT
from algorithms.doom.generator.doom import DOOM_UPSTREAM_FILE_COUNT
from algorithms.doom.generator.doom import DOOM_UPSTREAM_REPOSITORY
from algorithms.doom.generator.doom import DoomIdentityError
from algorithms.doom.generator.doom import build_identity_tree
from algorithms.doom.generator.doom import canonicalize_c_identity
from algorithms.doom.generator.doom import map_compatible_file
from algorithms.doom.generator.doom import mapped_c_identity
from algorithms.doom.generator.doom import validate_authoring_oracle

if TYPE_CHECKING:
    from pathlib import Path

_DIRECTIVE_END_FRAME = b"E\x00\x00\x00\x00"
_LINE_SPLICE_BYTES = b"\\\n"
_CRLF_BYTES = b"\r\n"


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
        _ = canonicalize_c_identity(b"int x; /* missing end")


def test_identity_tree_selects_linux_c_and_headers_only(tmp_path: Path) -> None:
    """Exclude WADs and non-Linux source families from DOOM source identity."""
    linux = tmp_path / "linuxdoom-1.10"
    linux.mkdir()
    _ = (linux / "main.c").write_bytes(b"int main(void){return 0;}\n")
    _ = (linux / "defs.H").write_bytes(b"#define VALUE 1\n")
    _ = (linux / "asset.wad").write_bytes(b"opaque")
    ipx = tmp_path / "ipx"
    ipx.mkdir()
    _ = (ipx / "DOOMNET.C").write_bytes(b"int ipx;\n")

    tree = build_identity_tree(tmp_path)
    paths = tuple(item.path for item in tree.files)

    _expect(
        paths == ("linuxdoom-1.10/defs.H", "linuxdoom-1.10/main.c"),
        "DOOM identity selected an opaque or non-Linux file",
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"int main(void){/* comment */return 0;}\n",
        b"#define X 1\r\nint y;\r\n",
        b"#define X a \\\n + b\n",
        b'char *s = "/* not comment */"; // comment\n',
        b"x = a + +b;\n",
    ],
)
def test_mapped_identity_matches_existing_canonical_stream(raw: bytes) -> None:
    """Keep mapped tokenization byte-identical to established C identity."""
    view = mapped_c_identity(raw)
    _expect(
        view.canonical == canonicalize_c_identity(raw),
        "mapped C identity drifted from canonical identity",
    )


def test_mapped_identity_preserves_token_keys_across_formatting() -> None:
    """Expose equal canonical units with different raw presentation spans."""
    compact = b"int main(void){return 0;}\n"
    formatted = b"int\tmain ( void ) {\n/* note */ return 0 ;\n}\n"
    first = mapped_c_identity(compact)
    second = mapped_c_identity(formatted)

    _expect(first.keys == second.keys, "formatting changed mapped token keys")
    _expect(
        tuple((unit.raw_start, unit.raw_end) for unit in first.units)
        != tuple((unit.raw_start, unit.raw_end) for unit in second.units),
        "formatting unexpectedly preserved all raw spans",
    )


def test_line_spliced_token_maps_back_across_removed_raw_bytes() -> None:
    """Map one logical identifier across a physical backslash-newline splice."""
    raw = b"int ident\\\nifier;\n"
    view = mapped_c_identity(raw)
    identifier = next(
        unit
        for unit in view.units
        if view.raw[unit.raw_start : unit.raw_end].startswith(b"ident")
    )

    _expect(
        _LINE_SPLICE_BYTES
        in view.raw[identifier.raw_start : identifier.raw_end],
        "spliced raw bytes disappeared from mapped token span",
    )


def test_crlf_directive_end_maps_to_raw_newline_span() -> None:
    """Keep directive-end identity tied to the original CRLF bytes."""
    raw = b"#define X 1\r\nint y;\r\n"
    view = mapped_c_identity(raw)
    directive_markers = [
        unit for unit in view.units if unit.canonical == _DIRECTIVE_END_FRAME
    ]

    _expect(len(directive_markers) == 1, "directive-end marker count changed")
    marker = directive_markers[0]
    _expect(
        raw[marker.raw_start : marker.raw_end] == _CRLF_BYTES,
        "directive-end marker lost its CRLF raw span",
    )


def test_eof_directive_end_uses_zero_width_raw_marker() -> None:
    """Represent a directive ending at EOF without inventing source bytes."""
    raw = b"#define X 1"
    view = mapped_c_identity(raw)
    marker = view.units[-1]

    _expect(marker.canonical == _DIRECTIVE_END_FRAME, "EOF marker changed")
    _expect(
        marker.raw_start == len(raw) and marker.raw_end == len(raw),
        "EOF directive marker consumed nonexistent bytes",
    )


def _quality_oracle_fixture(root: Path) -> None:
    (root / "data").mkdir(parents=True)
    (root / "linuxdoom-1.10").mkdir()
    _ = (root / "LICENSE").write_bytes(b"license")


def test_quality_oracle_preflight_accepts_exact_root_surface(
    tmp_path: Path,
) -> None:
    """Accept only the explicit normalized DOOM oracle root contract."""
    _quality_oracle_fixture(tmp_path)

    validate_authoring_oracle(tmp_path)


def test_quality_oracle_preflight_rejects_unexpected_root(
    tmp_path: Path,
) -> None:
    """Never learn an accidental authoring artifact as target-only payload."""
    _quality_oracle_fixture(tmp_path)
    _ = (
        tmp_path / "System.Management.Automation.Internal.Host.InternalHost"
    ).write_bytes(b"accidental")

    with pytest.raises(DoomIdentityError, match="unexpected"):
        validate_authoring_oracle(tmp_path)


def test_quality_oracle_preflight_rejects_missing_or_wrong_kind(
    tmp_path: Path,
) -> None:
    """Reject incomplete or structurally malformed oracle roots."""
    _quality_oracle_fixture(tmp_path)
    (tmp_path / "LICENSE").unlink()

    with pytest.raises(DoomIdentityError, match="missing"):
        validate_authoring_oracle(tmp_path)

    (tmp_path / "LICENSE").mkdir()
    with pytest.raises(DoomIdentityError, match="must be a file"):
        validate_authoring_oracle(tmp_path)


def test_compatible_mapper_selects_only_linux_c_and_headers() -> None:
    """Keep semantic placement scoped to the DOOM C identity surface."""
    code = b"int value;\n"

    _expect(
        map_compatible_file("linuxdoom-1.10/main.c", code) is not None,
        "Linux C file was not mapped",
    )
    _expect(
        map_compatible_file("linuxdoom-1.10/defs.H", code) is not None,
        "Linux header was not mapped",
    )
    _expect(
        map_compatible_file("data/wad/freedoom1.wad", b"opaque") is None,
        "WAD unexpectedly entered semantic placement",
    )
    _expect(
        map_compatible_file("ipx/doomnet.c", code) is None,
        "non-Linux source unexpectedly entered semantic placement",
    )


def test_source_pin_names_exact_official_revision() -> None:
    """Keep the DOOM product profile bound to one verified upstream commit."""
    _expect(
        DOOM_SOURCE_PIN.commit == DOOM_UPSTREAM_COMMIT,
        "source pin commit diverged from domain constant",
    )
    _expect(
        DOOM_SOURCE_PIN.repository == DOOM_UPSTREAM_REPOSITORY,
        "source pin repository diverged from domain constant",
    )
    _expect(
        DOOM_SOURCE_PIN.file_count == DOOM_UPSTREAM_FILE_COUNT,
        "upstream source count changed",
    )
