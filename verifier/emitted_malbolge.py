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
#   - Bounded static admission analysis for emitted classic Malbolge source.
# - Must-Not:
#   - Execute guest instructions or claim dynamic reachability equivalence.
# - Allows:
#   - Inputs: raw classic Malbolge source bytes.
#   - Outputs: deterministic initial-image findings and profile requirements.
#   - Side effects: CLI-only source reads and report writes.
# - Split-When:
#   - Dynamic control-flow or self-modification analysis gains its own model.
# - Merge-When:
#   - Another verifier owns the exact same initial-image checker boundary.
# - Summary:
#   - Static checker for classic Malbolge initial source images.
# - Description:
#   - Checks whitespace, graphical bytes, capacity, and positional decode.
# - Usage:
#   - Called by verifier tests or as a JSON-report command-line tool.
# - Defaults:
#   - Dynamic behavior remains explicitly not analyzed.
#

"""Bounded static analysis for emitted classic Malbolge source images."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Final
from typing import Never

if __package__:
    from verifier import emitted_malbolge_entry as entry_transfer
    from verifier import emitted_malbolge_prefix as prefix_transfer
else:
    import emitted_malbolge_entry as entry_transfer
    import emitted_malbolge_prefix as prefix_transfer

_PROFILE_ID: Final = "malbolge-1998"
_PROFILE_VERSION: Final = "1998"
_PROFILE_MEMORY_WORDS: Final = 59_049
_RECURRENCE_BASE_WORDS: Final = 2
_SCHEMA: Final = "malbolge-static-image/v4"
_LEXICAL_CODE: Final = "MALBOLGE-STATIC-001"
_RECURRENCE_CODE: Final = "MALBOLGE-STATIC-002"
_CAPACITY_CODE: Final = "MALBOLGE-STATIC-003"
_DECODE_CODE: Final = "MALBOLGE-STATIC-004"
_GRAPHICAL_START: Final = 33
_GRAPHICAL_END: Final = 126
_DECODE_PERIOD: Final = 94
_SOURCE_WHITESPACE: Final = frozenset((0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20))
_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_ENCRYPTION_TARGET_CURRENT: Final = "current-code-pointer"
_ENCRYPTION_TARGET_POST_JUMP: Final = "post-jump-code-pointer"
_ENCRYPTION_TARGET_NONE: Final = "none"
_DATA_WRITING_INSTRUCTIONS: Final = frozenset(b"*p")
_XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
_LIMITS: Final = (
    "code-data-aliasing:two-transition-prefix-only",
    "control-flow-reachability:two-transition-prefix-only",
    "dataflow:two-transition-prefix-only",
    "input-dependent-cycles:not-analyzed",
    "self-modification:two-transition-prefix-only",
    "source-map-context:not-analyzed",
    "wraparound-reachability:two-transition-prefix-only",
)


@dataclass(frozen=True, slots=True)
class StaticFinding:
    """One deterministic initial-image rejection or warning."""

    code: str
    message: str
    byte_offset: int | None = None
    loaded_position: int | None = None
    source_byte: int | None = None
    decoded_byte: int | None = None


@dataclass(frozen=True, slots=True)
class InitialCell:
    """One graphical source cell decoded at its initial loaded position."""

    position: int
    byte_offset: int
    source_byte: int
    decoded_byte: int
    post_step_encryption_target: str
    data_alias_can_change_encryption_input: bool


@dataclass(frozen=True, slots=True)
class StaticImageReport:
    """Bounded report that never implies dynamic guest execution."""

    schema: str
    profile_id: str
    profile_version: str
    profile_memory_words: int
    profile_address_domain_closed: bool
    source_sha256: str
    required_source_words: int
    admitted_initial_image: bool
    initial_cells: tuple[InitialCell, ...]
    entry_transition: entry_transfer.EntryTransition | None
    second_transition: prefix_transfer.SecondTransition | None
    findings: tuple[StaticFinding, ...]
    analysis_limits: tuple[str, ...]


def _loaded_source_words(source: bytes) -> tuple[int, ...]:
    return tuple(byte for byte in source if byte not in _SOURCE_WHITESPACE)


def _lexical_finding(source: bytes) -> StaticFinding | None:
    for offset, byte in enumerate(source):
        if byte in _SOURCE_WHITESPACE:
            continue
        if not _GRAPHICAL_START <= byte <= _GRAPHICAL_END:
            return StaticFinding(
                code=_LEXICAL_CODE,
                message="source byte is outside graphical ASCII",
                byte_offset=offset,
                source_byte=byte,
            )
    return None


def _decoded_byte(source_byte: int, position: int) -> int:
    index = (source_byte - _GRAPHICAL_START + position) % _DECODE_PERIOD
    return _XLAT1[index]


def _encryption_target(decoded_byte: int) -> str:
    if decoded_byte == ord("v"):
        return _ENCRYPTION_TARGET_NONE
    if decoded_byte == ord("i"):
        return _ENCRYPTION_TARGET_POST_JUMP
    return _ENCRYPTION_TARGET_CURRENT


def _initial_cells(source: bytes) -> tuple[InitialCell, ...]:
    words = tuple(
        (offset, byte)
        for offset, byte in enumerate(source)
        if byte not in _SOURCE_WHITESPACE
    )
    return tuple(
        InitialCell(
            position=position,
            byte_offset=offset,
            source_byte=byte,
            decoded_byte=(decoded := _decoded_byte(byte, position)),
            post_step_encryption_target=_encryption_target(decoded),
            data_alias_can_change_encryption_input=(
                decoded in _DATA_WRITING_INSTRUCTIONS
            ),
        )
        for position, (offset, byte) in enumerate(words)
    )


def _decode_findings(
    cells: tuple[InitialCell, ...],
) -> tuple[StaticFinding, ...]:
    return tuple(
        StaticFinding(
            code=_DECODE_CODE,
            message=(
                "initial source cell decodes to a forbidden load instruction"
            ),
            byte_offset=cell.byte_offset,
            loaded_position=cell.position,
            source_byte=cell.source_byte,
            decoded_byte=cell.decoded_byte,
        )
        for cell in cells
        if cell.decoded_byte not in _ALLOWED_INSTRUCTIONS
    )


def _analyze_admitted_cells(
    source: bytes,
    words: tuple[int, ...],
    *,
    can_decode: bool,
) -> tuple[
    tuple[InitialCell, ...],
    entry_transfer.EntryTransition | None,
    prefix_transfer.SecondTransition | None,
    tuple[StaticFinding, ...],
]:
    if not can_decode:
        return (), None, None, ()
    cells = _initial_cells(source)
    findings = _decode_findings(cells)
    entry = (
        None
        if findings
        else entry_transfer.analyze_entry_transition(
            words, cells[0].decoded_byte
        )
    )
    second = (
        None
        if entry is None
        else prefix_transfer.analyze_second_transition(words, entry)
    )
    return cells, entry, second, findings


def analyze_source(source: bytes) -> StaticImageReport:
    """Analyze one classic source image without executing guest instructions.

    Returns:
        Deterministic bounded initial-image analysis.

    """
    words = _loaded_source_words(source)
    required = len(words)
    findings: list[StaticFinding] = []
    lexical = _lexical_finding(source)
    if lexical is not None:
        findings.append(lexical)
    if required < _RECURRENCE_BASE_WORDS:
        findings.append(
            StaticFinding(
                code=_RECURRENCE_CODE,
                message=(
                    "source lacks the two words required by memory recurrence"
                ),
            )
        )
    if required > _PROFILE_MEMORY_WORDS:
        findings.append(
            StaticFinding(
                code=_CAPACITY_CODE,
                message=(
                    "source exceeds the selected historical profile capacity"
                ),
            )
        )
    within_profile = _RECURRENCE_BASE_WORDS <= required <= _PROFILE_MEMORY_WORDS
    cells, entry_transition, second_transition, decode_findings = (
        _analyze_admitted_cells(
            source,
            words,
            can_decode=lexical is None and within_profile,
        )
    )
    findings.extend(decode_findings)
    return StaticImageReport(
        schema=_SCHEMA,
        profile_id=_PROFILE_ID,
        profile_version=_PROFILE_VERSION,
        profile_memory_words=_PROFILE_MEMORY_WORDS,
        profile_address_domain_closed=True,
        source_sha256="sha256:" + sha256(source).hexdigest(),
        required_source_words=required,
        admitted_initial_image=not findings,
        initial_cells=cells,
        entry_transition=entry_transition,
        second_transition=second_transition,
        findings=tuple(findings),
        analysis_limits=_LIMITS,
    )


def render_report(report: StaticImageReport) -> str:
    """Render one canonical JSON line for deterministic evidence.

    Returns:
        Canonical single-line JSON with one trailing newline.

    """
    document = asdict(report)
    return json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"


def _bounded_prefix_accepted(report: StaticImageReport) -> bool:
    entry = report.entry_transition
    if not report.admitted_initial_image or entry is None or not entry.accepted:
        return False
    if entry.next_fetch_address is None:
        return True
    second = report.second_transition
    return second is not None and second.accepted


def _fail(message: str) -> Never:
    raise SystemExit(message)


def main(arguments: list[str] | None = None) -> int:
    """Analyze one source path and print its canonical JSON report.

    Returns:
        Zero when initial-image admission and the bounded entry transition both
        succeed, otherwise one after writing the canonical report.

    """
    argv = sys.argv[1:] if arguments is None else arguments
    if len(argv) != 1:
        _fail("usage: emitted_malbolge.py SOURCE.malbolge")
    source_path = Path(argv[0])
    try:
        source = source_path.read_bytes()
    except OSError as error:
        _fail(f"static analyzer cannot read source: {error}")
    report = analyze_source(source)
    payload = render_report(report).encode("utf-8")
    _ = sys.stdout.buffer.write(payload)
    return 0 if _bounded_prefix_accepted(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
