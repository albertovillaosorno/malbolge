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
#   - Synthetic tests for DOOM C source identity.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for DOOM C source identity."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from algorithms.diff.provenance import SourcePinError
from algorithms.diff.provenance import SourcePinEvidence
from algorithms.doom.generator import doom as doom_module
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
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

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


def test_identity_root_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible identity root cannot become a weaker missing error."""
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == tmp_path:
            message = "blocked DOOM identity root"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(DoomIdentityError, match="root status failed"):
        _ = build_identity_tree(tmp_path)


def test_identity_rejects_linked_root_when_supported(tmp_path: Path) -> None:
    """Do not resolve a linked source root before C/H identity admission."""
    target = tmp_path / "target"
    linux = target / "linuxdoom-1.10"
    linux.mkdir(parents=True)
    main_source = b"int main(void){return 0;}" + bytes((10,))
    _ = (linux / "main.c").write_bytes(main_source)
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(DoomIdentityError, match="symlink is not accepted"):
        _ = build_identity_tree(linked)


def test_identity_entry_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible C/H entry cannot disappear from source identity."""
    linux = tmp_path / "linuxdoom-1.10"
    linux.mkdir()
    blocked = linux / "main.c"
    _ = blocked.write_bytes(b"int main(void){return 0;}" + bytes((10,)))
    original_lstat = Path.lstat

    def fail_status(path: Path) -> object:
        if path == blocked:
            message = "blocked DOOM identity entry"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_status)
    with pytest.raises(DoomIdentityError, match="entry status failed"):
        _ = build_identity_tree(tmp_path)


def test_identity_entry_read_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable admitted C/H file cannot leak a host exception."""
    linux = tmp_path / "linuxdoom-1.10"
    linux.mkdir()
    blocked = linux / "main.c"
    _ = blocked.write_bytes(b"int main(void){return 0;}" + bytes((10,)))
    original_read = Path.read_bytes

    def fail_read(path: Path) -> bytes:
        if path == blocked:
            message = "blocked DOOM identity read"
            raise PermissionError(message)
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(DoomIdentityError, match="entry read failed"):
        _ = build_identity_tree(tmp_path)


def test_identity_tree_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recursive scan failure cannot disappear from DOOM source identity."""
    linux = tmp_path / "linuxdoom-1.10"
    linux.mkdir()

    def fail_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = path, top_down, follow_symlinks
        assert on_error is not None
        _ = on_error(PermissionError("blocked DOOM identity tree"))
        return iter(())

    monkeypatch.setattr(Path, "walk", fail_walk)
    with pytest.raises(DoomIdentityError, match="identity traversal failed"):
        _ = build_identity_tree(tmp_path)


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


def test_quality_oracle_rejects_linked_root_when_supported(
    tmp_path: Path,
) -> None:
    """Do not resolve a linked oracle root before surface validation."""
    target = tmp_path / "target"
    _quality_oracle_fixture(target)
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(DoomIdentityError, match="root must not be linked"):
        validate_authoring_oracle(linked)


def test_quality_oracle_enumeration_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible oracle scan cannot look like a surface mismatch."""
    _quality_oracle_fixture(tmp_path)
    original_iterdir = Path.iterdir

    def fail_iterdir(path: Path) -> Iterator[Path]:
        if path == tmp_path:
            message = "blocked quality oracle"
            raise PermissionError(message)
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_iterdir)
    with pytest.raises(DoomIdentityError, match="enumeration failed"):
        validate_authoring_oracle(tmp_path)


def test_quality_oracle_entry_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible expected entry cannot degrade to a kind mismatch."""
    _quality_oracle_fixture(tmp_path)
    blocked = tmp_path / "LICENSE"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == blocked:
            message = "blocked quality entry"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(DoomIdentityError, match="entry status failed"):
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


def _accept_source_pin(root: Path, pin: object) -> SourcePinEvidence:
    _ = root, pin
    return SourcePinEvidence(file_count=0, snapshot_sha256="0" * 64)


def test_source_surface_root_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep inaccessible root metadata inside the source-pin boundary."""
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == tmp_path:
            message = "blocked DOOM source root"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(doom_module, "require_source_pin", _accept_source_pin)
    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(SourcePinError, match="root status failed"):
        _ = doom_module.validate_source_provenance(tmp_path)


def test_source_surface_rejects_linked_root_when_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a linked source container before checking its names."""
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    monkeypatch.setattr(doom_module, "require_source_pin", _accept_source_pin)
    with pytest.raises(SourcePinError, match="must not be linked"):
        _ = doom_module.validate_source_provenance(linked)


def test_source_surface_enumeration_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep source-root scan failures distinct from an empty allowlist."""
    original_iterdir = Path.iterdir

    def fail_iterdir(path: Path) -> Iterator[Path]:
        if path == tmp_path:
            message = "blocked DOOM source scan"
            raise PermissionError(message)
        return original_iterdir(path)

    monkeypatch.setattr(doom_module, "require_source_pin", _accept_source_pin)
    monkeypatch.setattr(Path, "iterdir", fail_iterdir)
    with pytest.raises(SourcePinError, match="enumeration failed"):
        _ = doom_module.validate_source_provenance(tmp_path)


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
