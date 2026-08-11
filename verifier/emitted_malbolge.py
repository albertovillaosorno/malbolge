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
#   - Initial-image admission and explicit finite-prefix classic analysis.
# - Must-Not:
#   - Execute guest instructions or claim reachability beyond the requested
#     bound.
# - Allows:
#   - Inputs: raw classic Malbolge source bytes plus one finite transition
#     limit.
#   - Outputs: deterministic image findings, profile needs, and prefix evidence.
#   - Side effects: CLI-only source reads and report writes.
# - Split-When:
#   - Cyclic worklists or abstract-state reachability gain their own model.
# - Merge-When:
#   - Another verifier owns the exact same initial-image checker boundary.
# - Summary:
#   - Bounded checker for classic Malbolge images and exact finite prefixes.
# - Description:
#   - Checks loading plus bounded evolving memory/control-flow transitions.
# - Usage:
#   - Called by verifier tests or as a JSON-report command-line tool.
# - Defaults:
#   - Sixteen transitions; callers may request at most 256 exact transitions.
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
    from verifier import emitted_malbolge_classic as classic
    from verifier import emitted_malbolge_entry as entry_transfer
    from verifier import emitted_malbolge_prefix as prefix_transfer
else:
    import emitted_malbolge_classic as classic
    import emitted_malbolge_entry as entry_transfer
    import emitted_malbolge_prefix as prefix_transfer

_PROFILE_ID: Final = "malbolge-1998"
_PROFILE_VERSION: Final = "1998"
_RECURRENCE_BASE_WORDS: Final = 2
_SCHEMA: Final = "malbolge-static-image/v12"
_LEXICAL_CODE: Final = "MALBOLGE-STATIC-001"
_RECURRENCE_CODE: Final = "MALBOLGE-STATIC-002"
_CAPACITY_CODE: Final = "MALBOLGE-STATIC-003"
_DECODE_CODE: Final = "MALBOLGE-STATIC-004"
_SOURCE_WHITESPACE: Final = frozenset((0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20))
_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_ENCRYPTION_TARGET_CURRENT: Final = "current-code-pointer"
_ENCRYPTION_TARGET_POST_JUMP: Final = "post-jump-code-pointer"
_ENCRYPTION_TARGET_NONE: Final = "none"
_DATA_WRITING_INSTRUCTIONS: Final = frozenset(b"*p")
_DATA_READING_INSTRUCTIONS: Final = frozenset(b"ji*p")
_ACCESS_FETCH: Final = "instruction-fetch"
_ACCESS_DATA_READ: Final = "data-read"
_ACCESS_DATA_WRITE: Final = "data-write"
_ACCESS_ENCRYPTION: Final = "self-encryption"
_DEFAULT_TOTAL_TRANSITION_LIMIT: Final = 16
_MAX_TOTAL_TRANSITION_LIMIT: Final = 256
_TRANSITION_LIMIT_OPTION: Final = "--transition-limit"
_CLI_LIMIT_ARGUMENT_COUNT: Final = 3


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
class BoundedMemoryRequirement:
    """Exact memory footprint needed by the analyzed bounded prefix."""

    scope: str
    minimum_words: int
    highest_accessed_address: int
    accessed_addresses: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BoundedFetchSourceContext:
    """Exact source-image context for one resolved bounded instruction fetch."""

    transition_index: int
    fetched_address: int
    fetched_value: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    fetched_value_matches_initial_source: bool | None


@dataclass(frozen=True, slots=True)
class BoundedMemoryAccessSourceContext:
    """Exact source-image coordinates for one bounded memory access role."""

    transition_index: int
    access_kind: str
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None


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
    bounded_transition_limit: int
    bounded_continuations: tuple[prefix_transfer.SecondTransition, ...]
    bounded_memory_requirement: BoundedMemoryRequirement | None
    bounded_fetch_source_map: tuple[BoundedFetchSourceContext, ...]
    bounded_memory_access_source_map: tuple[
        BoundedMemoryAccessSourceContext, ...
    ]
    admitted_initial_image: bool
    initial_cells: tuple[InitialCell, ...]
    entry_transition: entry_transfer.EntryTransition | None
    second_transition: prefix_transfer.SecondTransition | None
    third_transition: prefix_transfer.SecondTransition | None
    fourth_transition: prefix_transfer.SecondTransition | None
    fifth_transition: prefix_transfer.SecondTransition | None
    findings: tuple[StaticFinding, ...]
    analysis_limits: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PrefixAnalysis:
    """Internal bounded-prefix evidence before final report assembly."""

    cells: tuple[InitialCell, ...]
    entry: entry_transfer.EntryTransition | None
    continuations: tuple[prefix_transfer.SecondTransition, ...]
    findings: tuple[StaticFinding, ...]


def _transition_limit(value: object) -> int:
    if (
        type(value) is not int
        or value < 1
        or value > _MAX_TOTAL_TRANSITION_LIMIT
    ):
        message = (
            "transition limit must be an exact integer from 1 through "
            f"{_MAX_TOTAL_TRANSITION_LIMIT}"
        )
        raise ValueError(message)
    return value


def _memory_scope(transition_limit: int) -> str:
    return f"{transition_limit}-transition-prefix"


def _analysis_limits(transition_limit: int) -> tuple[str, ...]:
    prefix = f"{transition_limit}-transition-prefix-only"
    return (
        f"code-data-aliasing:{prefix}",
        f"control-flow-reachability:{prefix}",
        f"dataflow:{prefix}",
        "input-dependent-cycles:not-analyzed",
        f"self-modification:{prefix}",
        (
            "source-map-context:"
            f"{transition_limit}-transition-memory-access-origin-only"
        ),
        f"wraparound-reachability:{prefix}",
    )


def _loaded_source_words(source: bytes) -> tuple[int, ...]:
    return tuple(byte for byte in source if byte not in _SOURCE_WHITESPACE)


def _lexical_finding(source: bytes) -> StaticFinding | None:
    for offset, byte in enumerate(source):
        if byte in _SOURCE_WHITESPACE:
            continue
        if not classic.is_graphical(byte):
            return StaticFinding(
                code=_LEXICAL_CODE,
                message="source byte is outside graphical ASCII",
                byte_offset=offset,
                source_byte=byte,
            )
    return None


def _decoded_byte(source_byte: int, position: int) -> int:
    decoded = classic.decode(source_byte, position)
    if decoded is None:
        message = "graphical initial source cell must decode"
        raise AssertionError(message)
    return decoded


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
    transition_limit: int,
) -> _PrefixAnalysis:
    if not can_decode:
        return _PrefixAnalysis((), None, (), ())
    cells = _initial_cells(source)
    findings = _decode_findings(cells)
    entry = (
        None
        if findings
        else entry_transfer.analyze_entry_transition(
            words, cells[0].decoded_byte
        )
    )
    continuation_limit = transition_limit - 1
    continuations = (
        ()
        if entry is None or continuation_limit == 0
        else prefix_transfer.analyze_continuations(
            words,
            entry,
            maximum_transitions=continuation_limit,
        )
    )
    return _PrefixAnalysis(cells, entry, continuations, findings)


def _continuation_at(
    prefix: _PrefixAnalysis,
    index: int,
) -> prefix_transfer.SecondTransition | None:
    if index >= len(prefix.continuations):
        return None
    return prefix.continuations[index]


def _entry_memory_accesses(
    entry: entry_transfer.EntryTransition,
) -> set[int]:
    accesses = {entry.fetched_address}
    if entry.decoded_byte in _DATA_READING_INSTRUCTIONS:
        accesses.add(entry.data_address)
    if entry.planned_data_write_address is not None:
        accesses.add(entry.planned_data_write_address)
    if entry.encryption_address is not None:
        accesses.add(entry.encryption_address)
    return accesses


def _prefix_memory_accesses(
    transition: prefix_transfer.SecondTransition,
) -> set[int]:
    accesses = {transition.fetched_address}
    if transition.decoded_byte in _DATA_READING_INSTRUCTIONS:
        accesses.add(transition.data_address)
    if transition.planned_data_write_address is not None:
        accesses.add(transition.planned_data_write_address)
    if transition.encryption_address is not None:
        accesses.add(transition.encryption_address)
    return accesses


def _bounded_memory_requirement(
    source_words: int,
    entry: entry_transfer.EntryTransition | None,
    transitions: tuple[prefix_transfer.SecondTransition, ...],
    *,
    transition_limit: int,
) -> BoundedMemoryRequirement | None:
    if entry is None:
        return None
    accesses = _entry_memory_accesses(entry)
    for transition in transitions:
        accesses.update(_prefix_memory_accesses(transition))
    ordered = tuple(sorted(accesses))
    highest = ordered[-1]
    return BoundedMemoryRequirement(
        scope=_memory_scope(transition_limit),
        minimum_words=max(source_words, highest + 1),
        highest_accessed_address=highest,
        accessed_addresses=ordered,
    )


def _fetch_source_context(
    transition_index: int,
    fetched_address: int,
    *,
    fetched_value: int,
    cells: tuple[InitialCell, ...],
) -> BoundedFetchSourceContext:
    if fetched_address >= len(cells):
        return BoundedFetchSourceContext(
            transition_index=transition_index,
            fetched_address=fetched_address,
            fetched_value=fetched_value,
            source_position=None,
            source_byte_offset=None,
            initial_source_byte=None,
            fetched_value_matches_initial_source=None,
        )
    cell = cells[fetched_address]
    return BoundedFetchSourceContext(
        transition_index=transition_index,
        fetched_address=fetched_address,
        fetched_value=fetched_value,
        source_position=cell.position,
        source_byte_offset=cell.byte_offset,
        initial_source_byte=cell.source_byte,
        fetched_value_matches_initial_source=(
            fetched_value == cell.source_byte
        ),
    )


def _bounded_fetch_source_map(
    words: tuple[int, ...],
    prefix: _PrefixAnalysis,
) -> tuple[BoundedFetchSourceContext, ...]:
    contexts: list[BoundedFetchSourceContext] = []
    entry = prefix.entry
    if entry is None:
        return ()
    contexts.append(
        _fetch_source_context(
            1,
            entry.fetched_address,
            fetched_value=words[0],
            cells=prefix.cells,
        )
    )
    for transition_index, transition in enumerate(
        prefix.continuations,
        start=2,
    ):
        contexts.append(
            _fetch_source_context(
                transition_index,
                transition.fetched_address,
                fetched_value=transition.fetched_value,
                cells=prefix.cells,
            )
        )
    return tuple(contexts)


def _entry_accesses(
    transition: entry_transfer.EntryTransition,
) -> tuple[tuple[str, int], ...]:
    accesses: list[tuple[str, int]] = [
        (_ACCESS_FETCH, transition.fetched_address)
    ]
    if transition.decoded_byte in _DATA_READING_INSTRUCTIONS:
        accesses.append((_ACCESS_DATA_READ, transition.data_address))
    if transition.planned_data_write_address is not None:
        accesses.append(
            (_ACCESS_DATA_WRITE, transition.planned_data_write_address)
        )
    if transition.encryption_address is not None:
        accesses.append((_ACCESS_ENCRYPTION, transition.encryption_address))
    return tuple(accesses)


def _prefix_accesses(
    transition: prefix_transfer.SecondTransition,
) -> tuple[tuple[str, int], ...]:
    accesses: list[tuple[str, int]] = [
        (_ACCESS_FETCH, transition.fetched_address)
    ]
    if transition.decoded_byte in _DATA_READING_INSTRUCTIONS:
        accesses.append((_ACCESS_DATA_READ, transition.data_address))
    if transition.planned_data_write_address is not None:
        accesses.append(
            (_ACCESS_DATA_WRITE, transition.planned_data_write_address)
        )
    if transition.encryption_address is not None:
        accesses.append((_ACCESS_ENCRYPTION, transition.encryption_address))
    return tuple(accesses)


def _memory_access_source_context(
    transition_index: int,
    access_kind: str,
    address: int,
    *,
    cells: tuple[InitialCell, ...],
) -> BoundedMemoryAccessSourceContext:
    if address >= len(cells):
        return BoundedMemoryAccessSourceContext(
            transition_index=transition_index,
            access_kind=access_kind,
            address=address,
            source_position=None,
            source_byte_offset=None,
            initial_source_byte=None,
        )
    cell = cells[address]
    return BoundedMemoryAccessSourceContext(
        transition_index=transition_index,
        access_kind=access_kind,
        address=address,
        source_position=cell.position,
        source_byte_offset=cell.byte_offset,
        initial_source_byte=cell.source_byte,
    )


def _access_source_contexts(
    transition_index: int,
    accesses: tuple[tuple[str, int], ...],
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedMemoryAccessSourceContext, ...]:
    return tuple(
        _memory_access_source_context(
            transition_index,
            access_kind,
            address,
            cells=cells,
        )
        for access_kind, address in accesses
    )


def _bounded_memory_access_source_map(
    prefix: _PrefixAnalysis,
) -> tuple[BoundedMemoryAccessSourceContext, ...]:
    entry = prefix.entry
    if entry is None:
        return ()
    contexts = list(
        _access_source_contexts(1, _entry_accesses(entry), prefix.cells)
    )
    for transition_index, transition in enumerate(
        prefix.continuations,
        start=2,
    ):
        contexts.extend(
            _access_source_contexts(
                transition_index,
                _prefix_accesses(transition),
                prefix.cells,
            )
        )
    return tuple(contexts)


def analyze_source(
    source: bytes,
    *,
    transition_limit: int = _DEFAULT_TOTAL_TRANSITION_LIMIT,
) -> StaticImageReport:
    """Analyze one classic source image under one explicit finite step bound.

    Returns:
        Deterministic bounded initial-image analysis.

    """
    admitted_limit = _transition_limit(transition_limit)
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
    if required > classic.PROFILE_MEMORY_WORDS:
        findings.append(
            StaticFinding(
                code=_CAPACITY_CODE,
                message=(
                    "source exceeds the selected historical profile capacity"
                ),
            )
        )
    within_profile = (
        _RECURRENCE_BASE_WORDS <= required <= classic.PROFILE_MEMORY_WORDS
    )
    prefix = _analyze_admitted_cells(
        source,
        words,
        can_decode=lexical is None and within_profile,
        transition_limit=admitted_limit,
    )
    findings.extend(prefix.findings)
    return StaticImageReport(
        schema=_SCHEMA,
        profile_id=_PROFILE_ID,
        profile_version=_PROFILE_VERSION,
        profile_memory_words=classic.PROFILE_MEMORY_WORDS,
        profile_address_domain_closed=True,
        source_sha256="sha256:" + sha256(source).hexdigest(),
        required_source_words=required,
        bounded_transition_limit=admitted_limit,
        bounded_continuations=prefix.continuations,
        bounded_memory_requirement=_bounded_memory_requirement(
            required,
            prefix.entry,
            prefix.continuations,
            transition_limit=admitted_limit,
        ),
        bounded_fetch_source_map=_bounded_fetch_source_map(words, prefix),
        bounded_memory_access_source_map=(
            _bounded_memory_access_source_map(prefix)
        ),
        admitted_initial_image=not findings,
        initial_cells=prefix.cells,
        entry_transition=prefix.entry,
        second_transition=_continuation_at(prefix, 0),
        third_transition=_continuation_at(prefix, 1),
        fourth_transition=_continuation_at(prefix, 2),
        fifth_transition=_continuation_at(prefix, 3),
        findings=tuple(findings),
        analysis_limits=_analysis_limits(admitted_limit),
    )


def render_report(report: StaticImageReport) -> str:
    """Render one canonical JSON line for deterministic evidence.

    Returns:
        Canonical single-line JSON with one trailing newline.

    """
    document = asdict(report)
    return json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"


def _continuations_accepted(
    transitions: tuple[prefix_transfer.SecondTransition, ...],
) -> bool:
    if not transitions:
        return False
    accepted = True
    for transition in transitions:
        if not transition.accepted:
            accepted = False
            break
        if transition.next_fetch_address is None:
            break
    return accepted


def _bounded_prefix_accepted(report: StaticImageReport) -> bool:
    entry = report.entry_transition
    if not report.admitted_initial_image or entry is None or not entry.accepted:
        return False
    if entry.next_fetch_address is None or report.bounded_transition_limit == 1:
        return True
    return _continuations_accepted(report.bounded_continuations)


def _fail(message: str) -> Never:
    raise SystemExit(message)


def _cli_request(arguments: list[str]) -> tuple[Path, int]:
    usage = (
        "usage: emitted_malbolge.py [--transition-limit N] SOURCE.malbolge"
    )
    if len(arguments) == 1:
        return Path(arguments[0]), _DEFAULT_TOTAL_TRANSITION_LIMIT
    if (
        len(arguments) != _CLI_LIMIT_ARGUMENT_COUNT
        or arguments[0] != _TRANSITION_LIMIT_OPTION
    ):
        _fail(usage)
    try:
        requested = int(arguments[1], 10)
    except ValueError:
        _fail("transition limit must be a decimal integer")
    try:
        admitted = _transition_limit(requested)
    except ValueError as error:
        _fail(str(error))
    return Path(arguments[2]), admitted


def main(arguments: list[str] | None = None) -> int:
    """Analyze one source path and print its canonical JSON report.

    Returns:
        Zero when initial-image admission and the requested finite prefix
        succeed, otherwise one after writing the canonical report.

    """
    argv = sys.argv[1:] if arguments is None else arguments
    source_path, transition_limit = _cli_request(argv)
    try:
        source = source_path.read_bytes()
    except OSError as error:
        _fail(f"static analyzer cannot read source: {error}")
    report = analyze_source(source, transition_limit=transition_limit)
    payload = render_report(report).encode("utf-8")
    _ = sys.stdout.buffer.write(payload)
    return 0 if _bounded_prefix_accepted(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
