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
    from verifier import emitted_malbolge_worklist as worklist_transfer
else:
    import emitted_malbolge_classic as classic
    import emitted_malbolge_entry as entry_transfer
    import emitted_malbolge_prefix as prefix_transfer
    import emitted_malbolge_worklist as worklist_transfer

_PROFILE_ID: Final = "malbolge-1998"
_PROFILE_VERSION: Final = "1998"
_RECURRENCE_BASE_WORDS: Final = 2
_SCHEMA: Final = "malbolge-static-image/v66"
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
_ORIGIN_LOADED_SOURCE: Final = "loaded-source"
_ORIGIN_RECURRENCE: Final = "recurrence-initialization"
_DEFAULT_TOTAL_TRANSITION_LIMIT: Final = 16
_MAX_TOTAL_TRANSITION_LIMIT: Final = 256
_TRANSITION_LIMIT_OPTION: Final = "--transition-limit"
_WORKLIST_LIMIT_OPTION: Final = "--worklist-state-limit"
_MAX_WORKLIST_STATE_LIMIT: Final = worklist_transfer.MAXIMUM_STATE_LIMIT


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
class BoundedFetchValueLineage:
    """Exact bounded origin of one resolved instruction-fetch value."""

    transition_index: int
    fetched_address: int
    fetched_value: int
    origin_kind: str
    origin_transition_index: int | None


@dataclass(frozen=True, slots=True)
class BoundedDataReadValueLineage:
    """Exact bounded origin of one semantically consumed data value."""

    transition_index: int
    data_address: int
    data_value: int
    origin_kind: str
    origin_transition_index: int | None


@dataclass(frozen=True, slots=True)
class BoundedEncryptionInputValueLineage:
    """Exact bounded origin of one self-encryption input value."""

    transition_index: int
    encryption_address: int
    encryption_input: int
    origin_kind: str
    origin_transition_index: int | None


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
class BoundedWorklistDataMutationSourceContext:
    """Source-image coordinates for the first worklist data mutation."""

    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    previous_value_matches_initial_source: bool | None


@dataclass(frozen=True, slots=True)
class BoundedWorklistDataMutationValueSourceContext:
    """Source coordinates and exact observed values for one mutation address."""

    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    previous_values: tuple[int, ...]
    result_values: tuple[int, ...]
    initial_source_byte_in_previous_values: bool | None


@dataclass(frozen=True, slots=True)
class BoundedWorklistValueSourceContext:
    """Source coordinates for one exact explored worklist value domain."""

    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    initial_memory_value: int
    values: tuple[int, ...]
    initial_source_byte_in_values: bool | None
    initial_memory_value_in_values: bool


@dataclass(frozen=True, slots=True)
class BoundedWorklistControlPathSourceContext:
    """Source coordinates for one state on a worklist witness entry path."""

    entry_path_state_index: int
    code_pointer: int
    data_pointer: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    data_source_position: int | None
    data_source_byte_offset: int | None
    initial_data_source_byte: int | None


@dataclass(frozen=True, slots=True)
class BoundedWorklistStateMergeSourceContext:
    """Source maps for the first exact non-cycle repeated-state merge edge."""

    source_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    target_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]


@dataclass(frozen=True, slots=True)
class BoundedWorklistCodeDataAliasSourceContext:
    """Source-linked first exact C/D alias witness for one address."""

    address: int
    memory_value: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    entry_path_source_map: tuple[BoundedWorklistControlPathSourceContext, ...]


@dataclass(frozen=True, slots=True)
class BoundedWorklistEvolvedReadWriterSourceContext:
    """Source-mapped exact last writer for one evolved worklist read."""

    origin_kind: str
    origin_entry_path_transition_index: int
    origin_value: int
    writer_state_source_context: BoundedWorklistControlPathSourceContext


@dataclass(frozen=True, slots=True)
class BoundedWorklistTerminalControlPathSourceMap:
    """Status-labeled source map for one exact terminal witness entry path."""

    status: str
    entry_path_source_map: tuple[BoundedWorklistControlPathSourceContext, ...]


@dataclass(frozen=True, slots=True)
class BoundedWorklistMutationAddressSourceContext:
    """Source-image coordinates for one worklist mutation address."""

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
    bounded_state_snapshots: tuple[prefix_transfer.StateSnapshot, ...]
    bounded_worklist: worklist_transfer.WorklistAnalysis | None
    bounded_worklist_state_merge_source_context: (
        BoundedWorklistStateMergeSourceContext | None
    )
    bounded_worklist_code_data_alias_source_contexts: tuple[
        BoundedWorklistCodeDataAliasSourceContext, ...
    ]
    bounded_worklist_data_mutation_source_context: (
        BoundedWorklistDataMutationSourceContext | None
    )
    bounded_worklist_effective_data_mutation_source_map: tuple[
        BoundedWorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_effective_data_mutation_value_source_map: tuple[
        BoundedWorklistDataMutationValueSourceContext, ...
    ]
    bounded_worklist_committed_write_source_map: tuple[
        BoundedWorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_committed_data_write_source_map: tuple[
        BoundedWorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_self_encryption_source_map: tuple[
        BoundedWorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_fetch_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_data_read_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_encryption_input_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_evolved_data_read_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_planned_data_write_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_committed_data_write_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_self_encryption_output_value_source_map: tuple[
        BoundedWorklistValueSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_evolved_data_read_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_writer_source_context: (
        BoundedWorklistEvolvedReadWriterSourceContext | None
    )
    bounded_worklist_evolved_data_read_writer_source_context: (
        BoundedWorklistEvolvedReadWriterSourceContext | None
    )
    bounded_worklist_data_mutation_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_data_write_noop_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_wraparound_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_cycle_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_closed_recurrent_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_frontier_entry_path_source_map: tuple[
        BoundedWorklistControlPathSourceContext, ...
    ]
    bounded_worklist_terminal_entry_path_source_maps: tuple[
        BoundedWorklistTerminalControlPathSourceMap, ...
    ]
    bounded_exact_cycle: prefix_transfer.ExactCycleCertificate | None
    bounded_memory_requirement: BoundedMemoryRequirement | None
    bounded_fetch_source_map: tuple[BoundedFetchSourceContext, ...]
    bounded_fetch_value_lineage: tuple[BoundedFetchValueLineage, ...]
    bounded_data_read_value_lineage: tuple[BoundedDataReadValueLineage, ...]
    bounded_encryption_input_value_lineage: tuple[
        BoundedEncryptionInputValueLineage, ...
    ]
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
    state_snapshots: tuple[prefix_transfer.StateSnapshot, ...]
    exact_cycle: prefix_transfer.ExactCycleCertificate | None
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


def _worklist_state_limit(value: object) -> int | None:
    if value is None:
        return None
    if (
        type(value) is not int
        or value < 1
        or value > _MAX_WORKLIST_STATE_LIMIT
    ):
        message = (
            "worklist state limit must be an exact integer from 1 through "
            f"{_MAX_WORKLIST_STATE_LIMIT}"
        )
        raise ValueError(message)
    return value


def _memory_scope(transition_limit: int) -> str:
    return f"{transition_limit}-transition-prefix"


def _worklist_status(
    analysis: worklist_transfer.WorklistAnalysis,
) -> str:
    return "truncated" if analysis.truncated else "closed"


def _worklist_limit_label(
    analysis: worklist_transfer.WorklistAnalysis | None,
) -> str:
    if analysis is None:
        return "input-dependent-reachability:not-analyzed"
    status = _worklist_status(analysis)
    return (
        "input-dependent-reachability:"
        f"{analysis.state_limit}-state-worklist-{status}"
    )


def _explored_worklist_limit_label(
    dimension: str,
    transition_limit: int,
    worklist: worklist_transfer.WorklistAnalysis | None,
) -> str:
    prefix = f"{transition_limit}-transition-prefix-only"
    if worklist is None:
        return f"{dimension}:{prefix}"
    return (
        f"{dimension}:{transition_limit}-transition-prefix-and-"
        f"{worklist.state_limit}-state-worklist-{_worklist_status(worklist)}-"
        "explored-only"
    )


def _source_map_limit_label(
    transition_limit: int,
    worklist: worklist_transfer.WorklistAnalysis | None,
) -> str:
    prefix = (
        f"source-map-context:{transition_limit}-transition-memory-access-and-"
        "fetch-data-read-and-encryption-input-value-lineage"
    )
    if worklist is None:
        return prefix
    return (
        f"{prefix}-and-{worklist.state_limit}-state-worklist-"
        f"{_worklist_status(worklist)}-worklist-value-and-control-path-evidence"
    )


def _wraparound_limit_label(
    transition_limit: int,
    worklist: worklist_transfer.WorklistAnalysis | None,
) -> str:
    prefix = f"{transition_limit}-transition-prefix-only"
    if worklist is None:
        return f"wraparound-reachability:{prefix}"
    return (
        "wraparound-reachability:"
        f"{transition_limit}-transition-prefix-and-"
        f"{worklist.state_limit}-state-worklist-{_worklist_status(worklist)}"
    )


def _analysis_limits(
    transition_limit: int,
    worklist: worklist_transfer.WorklistAnalysis | None,
) -> tuple[str, ...]:
    prefix = f"{transition_limit}-transition-prefix-only"
    return (
        _explored_worklist_limit_label(
            "code-data-aliasing", transition_limit, worklist
        ),
        f"control-flow-reachability:{prefix}",
        _explored_worklist_limit_label("dataflow", transition_limit, worklist),
        _worklist_limit_label(worklist),
        _explored_worklist_limit_label(
            "self-modification", transition_limit, worklist
        ),
        _source_map_limit_label(transition_limit, worklist),
        _wraparound_limit_label(transition_limit, worklist),
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
        return _PrefixAnalysis((), None, (), (), None, ())
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
    if entry is None:
        state_snapshots = ()
        continuations = ()
        exact_cycle = None
    elif continuation_limit == 0:
        state_snapshots = (
            prefix_transfer.StateSnapshot(1, 0, 0, 0, ()),
        )
        continuations = ()
        exact_cycle = None
    else:
        trace = prefix_transfer.analyze_continuation_trace(
            words,
            entry,
            maximum_transitions=continuation_limit,
        )
        continuations = trace.transitions
        state_snapshots = (
            prefix_transfer.StateSnapshot(1, 0, 0, 0, ()),
            *trace.state_snapshots,
        )
        exact_cycle = trace.exact_cycle
    return _PrefixAnalysis(
        cells,
        entry,
        continuations,
        state_snapshots,
        exact_cycle,
        findings,
    )


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


def _memory_value_origin(
    address: int,
    source_word_count: int,
    writers: dict[int, tuple[int, str]],
) -> tuple[str, int | None]:
    writer = writers.get(address)
    if writer is not None:
        origin_transition_index, origin_kind = writer
        return origin_kind, origin_transition_index
    origin_kind = (
        _ORIGIN_LOADED_SOURCE
        if address < source_word_count
        else _ORIGIN_RECURRENCE
    )
    return origin_kind, None


def _fetch_value_origin(
    transition_index: int,
    fetched: tuple[int, int],
    *,
    source_word_count: int,
    writers: dict[int, tuple[int, str]],
) -> BoundedFetchValueLineage:
    fetched_address, fetched_value = fetched
    origin_kind, origin_transition_index = _memory_value_origin(
        fetched_address,
        source_word_count,
        writers,
    )
    return BoundedFetchValueLineage(
        transition_index=transition_index,
        fetched_address=fetched_address,
        fetched_value=fetched_value,
        origin_kind=origin_kind,
        origin_transition_index=origin_transition_index,
    )


def _data_read_value_origin(
    transition_index: int,
    data_read: tuple[int, int],
    *,
    source_word_count: int,
    writers: dict[int, tuple[int, str]],
) -> BoundedDataReadValueLineage:
    data_address, data_value = data_read
    origin_kind, origin_transition_index = _memory_value_origin(
        data_address,
        source_word_count,
        writers,
    )
    return BoundedDataReadValueLineage(
        transition_index=transition_index,
        data_address=data_address,
        data_value=data_value,
        origin_kind=origin_kind,
        origin_transition_index=origin_transition_index,
    )


def _encryption_input_value_origin(
    transition_index: int,
    encryption_read: tuple[int, int],
    *,
    source_word_count: int,
    writers: dict[int, tuple[int, str]],
) -> BoundedEncryptionInputValueLineage:
    encryption_address, encryption_input = encryption_read
    origin_kind, origin_transition_index = _memory_value_origin(
        encryption_address,
        source_word_count,
        writers,
    )
    return BoundedEncryptionInputValueLineage(
        transition_index=transition_index,
        encryption_address=encryption_address,
        encryption_input=encryption_input,
        origin_kind=origin_kind,
        origin_transition_index=origin_transition_index,
    )


def _remember_data_write(
    writers: dict[int, tuple[int, str]],
    transition_index: int,
    transition: (
        entry_transfer.EntryTransition | prefix_transfer.SecondTransition
    ),
) -> None:
    data_address = transition.planned_data_write_address
    data_value = transition.planned_data_write_value
    if data_address is not None and data_value is not None:
        writers[data_address] = (transition_index, _ACCESS_DATA_WRITE)


def _remember_encryption_write(
    writers: dict[int, tuple[int, str]],
    transition_index: int,
    transition: (
        entry_transfer.EntryTransition | prefix_transfer.SecondTransition
    ),
) -> None:
    encryption_address = transition.encryption_address
    if (
        encryption_address is not None
        and transition.encryption_output is not None
    ):
        writers[encryption_address] = (transition_index, _ACCESS_ENCRYPTION)


def _remember_transition_writes(
    writers: dict[int, tuple[int, str]],
    transition_index: int,
    transition: (
        entry_transfer.EntryTransition | prefix_transfer.SecondTransition
    ),
) -> None:
    _remember_data_write(writers, transition_index, transition)
    _remember_encryption_write(writers, transition_index, transition)


def _bounded_fetch_value_lineage(
    source_word_count: int,
    prefix: _PrefixAnalysis,
) -> tuple[BoundedFetchValueLineage, ...]:
    entry = prefix.entry
    if entry is None:
        return ()
    writers: dict[int, tuple[int, str]] = {}
    lineage = [
        _fetch_value_origin(
            1,
            (
                entry.fetched_address,
                prefix.cells[entry.fetched_address].source_byte,
            ),
            source_word_count=source_word_count,
            writers=writers,
        )
    ]
    _remember_transition_writes(writers, 1, entry)
    for transition_index, transition in enumerate(
        prefix.continuations,
        start=2,
    ):
        lineage.append(
            _fetch_value_origin(
                transition_index,
                (transition.fetched_address, transition.fetched_value),
                source_word_count=source_word_count,
                writers=writers,
            )
        )
        _remember_transition_writes(writers, transition_index, transition)
    return tuple(lineage)


def _bounded_data_read_value_lineage(
    words: tuple[int, ...],
    prefix: _PrefixAnalysis,
) -> tuple[BoundedDataReadValueLineage, ...]:
    entry = prefix.entry
    if entry is None:
        return ()
    source_word_count = len(words)
    writers: dict[int, tuple[int, str]] = {}
    lineage: list[BoundedDataReadValueLineage] = []
    if entry.decoded_byte in _DATA_READING_INSTRUCTIONS:
        data_value = classic.initial_memory_value(words, entry.data_address)
        lineage.append(
            _data_read_value_origin(
                1,
                (entry.data_address, data_value),
                source_word_count=source_word_count,
                writers=writers,
            )
        )
    _remember_transition_writes(writers, 1, entry)
    for transition_index, transition in enumerate(
        prefix.continuations,
        start=2,
    ):
        data_value = transition.data_value
        if (
            transition.decoded_byte in _DATA_READING_INSTRUCTIONS
            and data_value is not None
        ):
            lineage.append(
                _data_read_value_origin(
                    transition_index,
                    (transition.data_address, data_value),
                    source_word_count=source_word_count,
                    writers=writers,
                )
            )
        _remember_transition_writes(writers, transition_index, transition)
    return tuple(lineage)


def _bounded_encryption_input_value_lineage(
    prefix: _PrefixAnalysis,
) -> tuple[BoundedEncryptionInputValueLineage, ...]:
    entry = prefix.entry
    if entry is None:
        return ()
    source_word_count = len(prefix.cells)
    writers: dict[int, tuple[int, str]] = {}
    lineage: list[BoundedEncryptionInputValueLineage] = []
    _remember_data_write(writers, 1, entry)
    if (
        entry.encryption_address is not None
        and entry.encryption_input is not None
    ):
        lineage.append(
            _encryption_input_value_origin(
                1,
                (entry.encryption_address, entry.encryption_input),
                source_word_count=source_word_count,
                writers=writers,
            )
        )
    _remember_encryption_write(writers, 1, entry)
    for transition_index, transition in enumerate(
        prefix.continuations,
        start=2,
    ):
        _remember_data_write(writers, transition_index, transition)
        if (
            transition.encryption_address is not None
            and transition.encryption_input is not None
        ):
            lineage.append(
                _encryption_input_value_origin(
                    transition_index,
                    (
                        transition.encryption_address,
                        transition.encryption_input,
                    ),
                    source_word_count=source_word_count,
                    writers=writers,
                )
            )
        _remember_encryption_write(writers, transition_index, transition)
    return tuple(lineage)


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


def _worklist_data_mutation_source_context(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> BoundedWorklistDataMutationSourceContext | None:
    witness = (
        None if worklist is None else worklist.explored_data_mutation_witness
    )
    if witness is None:
        return None
    address = witness.address
    if address >= len(cells):
        source_position = None
        source_byte_offset = None
        initial_source_byte = None
        previous_matches = None
    else:
        cell = cells[address]
        source_position = cell.position
        source_byte_offset = cell.byte_offset
        initial_source_byte = cell.source_byte
        previous_matches = witness.previous_value == cell.source_byte
    return BoundedWorklistDataMutationSourceContext(
        address=address,
        source_position=source_position,
        source_byte_offset=source_byte_offset,
        initial_source_byte=initial_source_byte,
        previous_value_matches_initial_source=previous_matches,
    )


def _worklist_mutation_address_source_context(
    address: int,
    cells: tuple[InitialCell, ...],
) -> BoundedWorklistMutationAddressSourceContext:
    if address >= len(cells):
        return BoundedWorklistMutationAddressSourceContext(
            address=address,
            source_position=None,
            source_byte_offset=None,
            initial_source_byte=None,
        )
    cell = cells[address]
    return BoundedWorklistMutationAddressSourceContext(
        address=address,
        source_position=cell.position,
        source_byte_offset=cell.byte_offset,
        initial_source_byte=cell.source_byte,
    )


def _worklist_effective_data_mutation_source_map(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistMutationAddressSourceContext, ...]:
    if worklist is None:
        return ()
    return tuple(
        _worklist_mutation_address_source_context(address, cells)
        for address in worklist.explored_effective_data_mutation_addresses
    )


def _worklist_data_mutation_value_source_map(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistDataMutationValueSourceContext, ...]:
    if worklist is None:
        return ()
    contexts: list[BoundedWorklistDataMutationValueSourceContext] = []
    for domain in worklist.explored_effective_data_mutation_value_domains:
        source = _worklist_mutation_address_source_context(
            domain.address, cells
        )
        initial = source.initial_source_byte
        contexts.append(
            BoundedWorklistDataMutationValueSourceContext(
                address=domain.address,
                source_position=source.source_position,
                source_byte_offset=source.source_byte_offset,
                initial_source_byte=initial,
                previous_values=domain.previous_values,
                result_values=domain.result_values,
                initial_source_byte_in_previous_values=(
                    None
                    if initial is None
                    else initial in domain.previous_values
                ),
            )
        )
    return tuple(contexts)


def _worklist_value_source_map(
    domains: tuple[worklist_transfer.WorklistValueDomain, ...],
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistValueSourceContext, ...]:
    contexts: list[BoundedWorklistValueSourceContext] = []
    words = tuple(cell.source_byte for cell in cells)
    for domain in domains:
        source = _worklist_mutation_address_source_context(
            domain.address, cells
        )
        initial = source.initial_source_byte
        initial_memory = classic.initial_memory_value(words, domain.address)
        contexts.append(
            BoundedWorklistValueSourceContext(
                address=domain.address,
                source_position=source.source_position,
                source_byte_offset=source.source_byte_offset,
                initial_source_byte=initial,
                initial_memory_value=initial_memory,
                values=domain.values,
                initial_source_byte_in_values=(
                    None if initial is None else initial in domain.values
                ),
                initial_memory_value_in_values=(
                    initial_memory in domain.values
                ),
            )
        )
    return tuple(contexts)


def _worklist_control_path_source_map(
    path: tuple[worklist_transfer.WorklistCycleState, ...] | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistControlPathSourceContext, ...]:
    if path is None:
        return ()
    contexts: list[BoundedWorklistControlPathSourceContext] = []
    for index, state in enumerate(path):
        code_pointer = state.code_pointer
        data_pointer = state.data_pointer
        source = _worklist_mutation_address_source_context(code_pointer, cells)
        data_source = _worklist_mutation_address_source_context(
            data_pointer, cells
        )
        contexts.append(
            BoundedWorklistControlPathSourceContext(
                entry_path_state_index=index,
                code_pointer=code_pointer,
                data_pointer=data_pointer,
                source_position=source.source_position,
                source_byte_offset=source.source_byte_offset,
                initial_source_byte=source.initial_source_byte,
                data_source_position=data_source.source_position,
                data_source_byte_offset=data_source.source_byte_offset,
                initial_data_source_byte=data_source.initial_source_byte,
            )
        )
    return tuple(contexts)


def _worklist_state_merge_source_context(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> BoundedWorklistStateMergeSourceContext | None:
    if worklist is None or worklist.explored_state_merge_witness is None:
        return None
    witness = worklist.explored_state_merge_witness
    return BoundedWorklistStateMergeSourceContext(
        source_entry_path_source_map=_worklist_control_path_source_map(
            witness.source_entry_path, cells
        ),
        target_entry_path_source_map=_worklist_control_path_source_map(
            witness.existing_target_entry_path, cells
        ),
    )


def _worklist_code_data_alias_source_contexts(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistCodeDataAliasSourceContext, ...]:
    if worklist is None:
        return ()
    contexts: list[BoundedWorklistCodeDataAliasSourceContext] = []
    for witness in worklist.explored_code_data_alias_witnesses:
        source = _worklist_mutation_address_source_context(
            witness.address, cells
        )
        contexts.append(
            BoundedWorklistCodeDataAliasSourceContext(
                address=witness.address,
                memory_value=witness.memory_value,
                source_position=source.source_position,
                source_byte_offset=source.source_byte_offset,
                initial_source_byte=source.initial_source_byte,
                entry_path_source_map=_worklist_control_path_source_map(
                    witness.entry_path, cells
                ),
            )
        )
    return tuple(contexts)


def _worklist_evolved_read_writer_source_context(
    witness: worklist_transfer.WorklistEvolvedReadWitness | None,
    cells: tuple[InitialCell, ...],
) -> BoundedWorklistEvolvedReadWriterSourceContext | None:
    if witness is None:
        return None
    state_index = witness.origin_entry_path_transition_index - 1
    if state_index < 0 or state_index >= len(witness.entry_path) - 1:
        message = "evolved read writer transition is outside its entry path"
        raise AssertionError(message)
    source_map = _worklist_control_path_source_map(witness.entry_path, cells)
    writer_source = source_map[state_index]
    if writer_source.entry_path_state_index != state_index:
        message = "evolved read writer source map lost its path index"
        raise AssertionError(message)
    return BoundedWorklistEvolvedReadWriterSourceContext(
        origin_kind=witness.origin_kind,
        origin_entry_path_transition_index=(
            witness.origin_entry_path_transition_index
        ),
        origin_value=witness.origin_value,
        writer_state_source_context=writer_source,
    )


def _worklist_terminal_control_path_source_maps(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistTerminalControlPathSourceMap, ...]:
    if worklist is None:
        return ()
    return tuple(
        BoundedWorklistTerminalControlPathSourceMap(
            status=witness.status,
            entry_path_source_map=_worklist_control_path_source_map(
                witness.entry_path, cells
            ),
        )
        for witness in worklist.terminal_status_witnesses
    )


def _worklist_committed_write_source_map(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistMutationAddressSourceContext, ...]:
    if worklist is None:
        return ()
    return tuple(
        _worklist_mutation_address_source_context(address, cells)
        for address in worklist.explored_committed_write_addresses
    )


def _worklist_committed_data_write_source_map(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistMutationAddressSourceContext, ...]:
    if worklist is None:
        return ()
    return tuple(
        _worklist_mutation_address_source_context(address, cells)
        for address in worklist.explored_committed_data_write_addresses
    )


def _worklist_self_encryption_source_map(
    worklist: worklist_transfer.WorklistAnalysis | None,
    cells: tuple[InitialCell, ...],
) -> tuple[BoundedWorklistMutationAddressSourceContext, ...]:
    if worklist is None:
        return ()
    return tuple(
        _worklist_mutation_address_source_context(address, cells)
        for address in worklist.explored_self_encryption_addresses
    )


def analyze_source(
    source: bytes,
    *,
    transition_limit: int = _DEFAULT_TOTAL_TRANSITION_LIMIT,
    worklist_state_limit: int | None = None,
) -> StaticImageReport:
    """Analyze one classic source image under one explicit finite step bound.

    Returns:
        Deterministic bounded initial-image analysis.

    """
    admitted_limit = _transition_limit(transition_limit)
    admitted_worklist_limit = _worklist_state_limit(worklist_state_limit)
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
    worklist = (
        worklist_transfer.analyze_reachability(
            words,
            maximum_states=admitted_worklist_limit,
        )
        if not findings and admitted_worklist_limit is not None
        else None
    )
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
        bounded_state_snapshots=prefix.state_snapshots,
        bounded_worklist=worklist,
        bounded_worklist_state_merge_source_context=(
            _worklist_state_merge_source_context(worklist, prefix.cells)
        ),
        bounded_worklist_code_data_alias_source_contexts=(
            _worklist_code_data_alias_source_contexts(worklist, prefix.cells)
        ),
        bounded_worklist_data_mutation_source_context=(
            _worklist_data_mutation_source_context(worklist, prefix.cells)
        ),
        bounded_worklist_effective_data_mutation_source_map=(
            _worklist_effective_data_mutation_source_map(worklist, prefix.cells)
        ),
        bounded_worklist_effective_data_mutation_value_source_map=(
            _worklist_data_mutation_value_source_map(worklist, prefix.cells)
        ),
        bounded_worklist_committed_write_source_map=(
            _worklist_committed_write_source_map(worklist, prefix.cells)
        ),
        bounded_worklist_committed_data_write_source_map=(
            _worklist_committed_data_write_source_map(worklist, prefix.cells)
        ),
        bounded_worklist_self_encryption_source_map=(
            _worklist_self_encryption_source_map(worklist, prefix.cells)
        ),
        bounded_worklist_fetch_value_source_map=(
            _worklist_value_source_map(
                (
                    ()
                    if worklist is None
                    else worklist.explored_fetch_value_domains
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_data_read_value_source_map=(
            _worklist_value_source_map(
                (
                    ()
                    if worklist is None
                    else worklist.explored_data_read_value_domains
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_encryption_input_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_encryption_input_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_fetch_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_evolved_fetch_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_data_read_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_evolved_data_read_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_planned_data_write_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_planned_data_write_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_committed_data_write_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_committed_data_write_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_self_encryption_output_value_source_map=(
            _worklist_value_source_map(
                ()
                if worklist is None
                else worklist.explored_self_encryption_output_value_domains,
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_fetch_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    else (
                        worklist.explored_evolved_fetch_witness.entry_path
                        if worklist.explored_evolved_fetch_witness is not None
                        else None
                    )
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_data_read_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    else (
                        worklist.explored_evolved_data_read_witness.entry_path
                        if (
                            worklist.explored_evolved_data_read_witness
                            is not None
                        )
                        else None
                    )
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_fetch_writer_source_context=(
            _worklist_evolved_read_writer_source_context(
                (
                    None
                    if worklist is None
                    else worklist.explored_evolved_fetch_witness
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_evolved_data_read_writer_source_context=(
            _worklist_evolved_read_writer_source_context(
                (
                    None
                    if worklist is None
                    else worklist.explored_evolved_data_read_witness
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_data_mutation_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    or worklist.explored_data_mutation_witness is None
                    else worklist.explored_data_mutation_witness.entry_path
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_data_write_noop_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    or worklist.explored_data_write_noop_witness is None
                    else worklist.explored_data_write_noop_witness.entry_path
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_wraparound_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    or worklist.explored_wraparound_witness is None
                    else worklist.explored_wraparound_witness.entry_path
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_cycle_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    else worklist.reachable_cycle_entry_path
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_closed_recurrent_entry_path_source_map=(
            _worklist_control_path_source_map(
                (
                    None
                    if worklist is None
                    else worklist.closed_recurrent_entry_path
                ),
                prefix.cells,
            )
        ),
        bounded_worklist_frontier_entry_path_source_map=(
            _worklist_control_path_source_map(
                None if worklist is None else worklist.frontier_entry_path,
                prefix.cells,
            )
        ),
        bounded_worklist_terminal_entry_path_source_maps=(
            _worklist_terminal_control_path_source_maps(worklist, prefix.cells)
        ),
        bounded_exact_cycle=prefix.exact_cycle,
        bounded_memory_requirement=_bounded_memory_requirement(
            required,
            prefix.entry,
            prefix.continuations,
            transition_limit=admitted_limit,
        ),
        bounded_fetch_source_map=_bounded_fetch_source_map(words, prefix),
        bounded_fetch_value_lineage=_bounded_fetch_value_lineage(
            required,
            prefix,
        ),
        bounded_data_read_value_lineage=(
            _bounded_data_read_value_lineage(words, prefix)
        ),
        bounded_encryption_input_value_lineage=(
            _bounded_encryption_input_value_lineage(prefix)
        ),
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
        analysis_limits=_analysis_limits(admitted_limit, worklist),
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


def _bounded_worklist_accepted(report: StaticImageReport) -> bool:
    worklist = report.bounded_worklist
    return worklist is None or worklist.closed_all_paths_halt is True


def _bounded_prefix_accepted(report: StaticImageReport) -> bool:
    entry = report.entry_transition
    if not report.admitted_initial_image or entry is None or not entry.accepted:
        return False
    if (
        report.bounded_exact_cycle is not None
        or not _bounded_worklist_accepted(report)
    ):
        return False
    return (
        entry.next_fetch_address is None
        or report.bounded_transition_limit == 1
        or _continuations_accepted(report.bounded_continuations)
    )


def _fail(message: str) -> Never:
    raise SystemExit(message)


def _decimal_cli_value(value: str, *, label: str) -> int:
    try:
        return int(value, 10)
    except ValueError:
        _fail(f"{label} must be a decimal integer")


def _cli_option_values(arguments: list[str], usage: str) -> dict[str, str]:
    options = arguments[:-1]
    if len(options) % 2 != 0:
        _fail(usage)
    values: dict[str, str] = {}
    allowed = {_TRANSITION_LIMIT_OPTION, _WORKLIST_LIMIT_OPTION}
    for index in range(0, len(options), 2):
        option = options[index]
        if option not in allowed or option in values:
            _fail(usage)
        values[option] = options[index + 1]
    return values


def _cli_transition_limit(values: dict[str, str]) -> int:
    raw = values.get(_TRANSITION_LIMIT_OPTION)
    if raw is None:
        return _DEFAULT_TOTAL_TRANSITION_LIMIT
    requested = _decimal_cli_value(raw, label="transition limit")
    try:
        return _transition_limit(requested)
    except ValueError as error:
        _fail(str(error))


def _cli_worklist_limit(values: dict[str, str]) -> int | None:
    raw = values.get(_WORKLIST_LIMIT_OPTION)
    if raw is None:
        return None
    requested = _decimal_cli_value(raw, label="worklist state limit")
    try:
        return _worklist_state_limit(requested)
    except ValueError as error:
        _fail(str(error))


def _cli_request(arguments: list[str]) -> tuple[Path, int, int | None]:
    usage = (
        "usage: emitted_malbolge.py [--transition-limit N] "
        "[--worklist-state-limit N] SOURCE.malbolge"
    )
    if not arguments:
        _fail(usage)
    values = _cli_option_values(arguments, usage)
    return (
        Path(arguments[-1]),
        _cli_transition_limit(values),
        _cli_worklist_limit(values),
    )


def main(arguments: list[str] | None = None) -> int:
    """Analyze one source path and print its canonical JSON report.

    Returns:
        Zero when initial-image admission and the requested finite prefix
        succeed, otherwise one after writing the canonical report.

    """
    argv = sys.argv[1:] if arguments is None else arguments
    source_path, transition_limit, worklist_state_limit = _cli_request(argv)
    try:
        source = source_path.read_bytes()
    except OSError as error:
        _fail(f"static analyzer cannot read source: {error}")
    report = analyze_source(
        source,
        transition_limit=transition_limit,
        worklist_state_limit=worklist_state_limit,
    )
    payload = render_report(report).encode("utf-8")
    _ = sys.stdout.buffer.write(payload)
    return 0 if _bounded_prefix_accepted(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
