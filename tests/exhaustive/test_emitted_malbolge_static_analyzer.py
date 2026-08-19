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
#   - Independent regressions for bounded emitted-Malbolge static admission.
# - Must-Not:
#   - Execute guest work or derive expected decode through the checker itself.
# - Allows:
#   - Inputs: fixed valid sources and deliberately invalid source mutations.
#   - Outputs: deterministic report and finding assertions.
#   - Side effects: test-local source files and subprocess output only.
# - Split-When:
#   - Dynamic reachability analysis gains independent fixtures.
# - Merge-When:
#   - Verifier conformance owns these exact initial-image cases directly.
# - Summary:
#   - Bounded static analyzer acceptance and rejection evidence.
# - Description:
#   - Covers lexical, recurrence, capacity, positional decode, and CLI output.
# - Usage:
#   - Collected by the repository Python validation suite.
# - Defaults:
#   - Dynamic analysis limits remain explicit in every report.
#

"""Bounded emitted-Malbolge static analyzer regressions."""

from __future__ import annotations

import ast
from copy import copy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Protocol
from typing import cast

import pytest
from scripts.validate import target_profile

_ROOT = Path(__file__).resolve().parents[2]
_ANALYZER = _ROOT / "verifier" / "emitted_malbolge.py"
_CLASSIC = _ROOT / "verifier" / "emitted_malbolge_classic.py"
_FIXTURE = (
    _ROOT / "tests/compatibility/specification/spec-io-roundtrip.malbolge"
)
_HISTORICAL_INTERPRETER = (
    _ROOT / "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)
_PROFILE_ID = "malbolge-1998"
_PROFILE_MEMORY_WORDS = 59_049
_FIXTURE_SOURCE_WORDS = 3
_TWO_SOURCE_WORDS = 2
_OVERSIZED_SOURCE_WORDS = 59_050
_LEXICAL_CODE = "MALBOLGE-STATIC-001"
_DECODE_CODE = "MALBOLGE-STATIC-004"
_GRAPHICAL_INVALID_BYTE = 33
_FORBIDDEN_DECODE_BYTE = 43
_SCHEMA = "malbolge-static-image/v74"
_ENTRY_CONTINUED = "continued"
_ENTRY_HALTED = "halted"
_ENTRY_INVALID_ENCRYPTION = "rejected-invalid-self-encryption"
_THIRD_STUCK = "stuck-non-graphical-fetch"
_SECOND_INPUT_UNRESOLVED = "unresolved-input-dependent-accumulator"
_FIXTURE_ENCRYPTION_INPUT = 99
_FIXTURE_SECOND_VALUE = 116
_SECOND_SUCCESSOR = 2
_TOTAL_TRANSITION_LIMIT = 16
_CONTINUATION_LIMIT = _TOTAL_TRANSITION_LIMIT - 1
_EXTENDED_TRANSITION_LIMIT = 32
_MAX_TOTAL_TRANSITION_LIMIT = 256
_INVALID_TOTAL_TRANSITION_LIMIT = _MAX_TOTAL_TRANSITION_LIMIT + 1
_MAX_WORKLIST_STATE_LIMIT = 4_096
_INVALID_WORKLIST_STATE_LIMIT = _MAX_WORKLIST_STATE_LIMIT + 1
_WORKLIST_COMPLETE_STATE_LIMIT = 258
_WORKLIST_TRUNCATED_STATE_LIMIT = 257
_WORKLIST_INPUT_VALUE_COUNT = 257
_INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT = 58
_INPUT_CRAZY_ENCRYPTION_INPUT_COUNT = 258
_INPUT_CRAZY_INITIAL_ENCRYPTION_INPUT_COUNT = 1
_INPUT_CRAZY_CHANGED_ENCRYPTION_INPUT_COUNT = 257
_ENTRY_WRAP_SOURCE = b"u'<%$#>=<;:987654321NN"
_ENTRY_WRAP_SOURCE_WITH_WHITESPACE = b" \n" + _ENTRY_WRAP_SOURCE
_ENTRY_WRAP_LOADED_WRITE_ADDRESSES = (0, 1, 2, 3, 4, 5, 6)
_ENTRY_WRAP_RECURRENCE_WRITE_ADDRESS = 40
_ENTRY_WRAP_COMMITTED_WRITE_ADDRESSES = (
    *_ENTRY_WRAP_LOADED_WRITE_ADDRESSES,
    _ENTRY_WRAP_RECURRENCE_WRITE_ADDRESS,
)
_ENTRY_WRAP_SOURCE_OFFSET_SHIFT = 2
_ENTRY_WRAP_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 41),
    (4, 79),
    (5, 40),
)
_ENTRY_WRAP_RESULT_CODE_POINTER = 6
_ENTRY_MUTATION_ACCUMULATOR = 1
_ENTRY_MUTATION_ADDRESS = 40
_ENTRY_MUTATION_PREVIOUS_VALUE = 29_524
_ENTRY_MUTATION_RESULT_VALUE = 29_523
_ENTRY_EFFECTIVE_DATA_MUTATION_COUNT = 256
_ENTRY_DATA_READ_TRANSITION_COUNT = 1_285
_ENTRY_INITIAL_VALUE_DATA_READ_COUNT = 1_029
_ENTRY_INITIAL_VALUE_DATA_READ_ADDRESSES = (1, 40, 41, 79)
_ENTRY_COMMITTED_DATA_WRITE_COUNT = 257
_ENTRY_NOOP_DATA_WRITE_COUNT = 1
_ENTRY_MUTATION_RESULT_DOMAIN_COUNT = 256
_MULTI_MUTATION_SECOND_ADDRESS = 41
_MULTI_MUTATION_SECOND_PREVIOUS_VALUES = (29_409,)
_MULTI_MUTATION_SECOND_RESULT_VALUES = (9_803,)
_LOADED_MUTATION_SOURCE = (
    b"u'<%$#>=<;:987654321NN"
    b".-,+*)('&%$#\"!~}|{z"
)
_LOADED_MUTATION_SOURCE_WITH_WHITESPACE = b" \n" + _LOADED_MUTATION_SOURCE
_LOADED_MUTATION_ADDRESS = 40
_LOADED_MUTATION_BYTE_OFFSET = 42
_LOADED_MUTATION_SOURCE_BYTE = 122
_LOADED_MUTATION_PREVIOUS_VALUE = 122
_LOADED_MUTATION_RESULT_VALUE = 29_525
_MULTI_MUTATION_SOURCE = (
    b"u'<$$#>=<;:987654321NN"
    b".-,+*)('&%$#\"!~}|{z"
)
_MULTI_MUTATION_SOURCE_WITH_WHITESPACE = b" \n" + _MULTI_MUTATION_SOURCE
_MULTI_MUTATION_ADDRESSES = (40, 41)
_MULTI_MUTATION_LOADED_ADDRESS = 40
_MULTI_MUTATION_LOADED_BYTE_OFFSET = 42
_MULTI_MUTATION_LOADED_SOURCE_BYTE = 122
_MULTI_MUTATION_RECURRENCE_ADDRESS = 41
_ENTRY_WRAP_WORKLIST_STATE_LIMIT = 1_544
_ENTRY_WRAP_EXPLORED_STATES = 1_288
_WORKLIST_CLOSED_LIMIT = (
    "input-dependent-reachability:258-state-worklist-closed"
)
_WORKLIST_TRUNCATED_LIMIT = (
    "input-dependent-reachability:257-state-worklist-truncated"
)
_WORKLIST_WRAP_LIMIT = (
    "wraparound-reachability:16-transition-prefix-and-"
    "258-state-worklist-closed"
)
_WORKLIST_ALIAS_LIMIT = (
    "code-data-aliasing:16-transition-prefix-and-"
    "258-state-worklist-closed-explored-only"
)
_WORKLIST_DATAFLOW_LIMIT = (
    "dataflow:16-transition-prefix-and-"
    "258-state-worklist-closed-explored-only"
)
_WORKLIST_MUTATION_LIMIT = (
    "self-modification:16-transition-prefix-and-"
    "258-state-worklist-closed-explored-only"
)
_ENTRY_WRAP_LIMIT = (
    "wraparound-reachability:16-transition-prefix-and-"
    "1544-state-worklist-truncated"
)
_ENTRY_DATAFLOW_LIMIT = (
    "dataflow:16-transition-prefix-and-"
    "1544-state-worklist-truncated-explored-only"
)
_WORKLIST_VALUE_SOURCE_MAP_LIMIT = (
    "source-map-context:16-transition-memory-access-and-"
    "fetch-data-read-and-encryption-input-value-lineage-and-"
    "1544-state-worklist-truncated-worklist-value-and-control-path-evidence"
)
_INPUT_CRAZY_SOURCE = bytes((117, 61))
_INPUT_HALT_SOURCE = bytes((117, 80))
_DOUBLE_INPUT_CYCLE_SOURCE = bytes((117, 116))
_LONG_INPUT_CYCLE_SOURCE = bytes((117, 39, 38, 37))
_LONG_INPUT_CYCLE_STATE_LIMIT = 1_029
_LONG_INPUT_CYCLE_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 29_490),
    (4, 29_489),
)
_DEEP_INPUT_CYCLE_SOURCE = b"u'&%$"
_DEEP_INPUT_CYCLE_STATE_LIMIT = 1_286
_DEEP_INPUT_CYCLE_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 37),
    (4, 29_489),
    (5, 29_489),
)
_NEAR_CAP_INPUT_CYCLE_SOURCE = b"u'&%$#\"!~}|{zyx"
_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT = 3_856
_NEAR_CAP_INPUT_CYCLE_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 121),
    (4, 29_405),
    (5, 29_405),
    (6, 29_405),
    (7, 29_405),
    (8, 29_405),
    (9, 29_405),
    (10, 29_405),
    (11, 29_405),
    (12, 29_405),
    (13, 29_405),
    (14, 29_405),
    (15, 29_405),
)
_NEAR_CAP_INPUT_CYCLE_DATA_POINTER_ADDRESSES = (0, 1, 40, 121, 29_405)
_MERGED_INPUT_CYCLE_SOURCE = b"".join(
    (
        b"u'%%$#\"!~}|{zyxwvutsrqponmlkjihgfedcba`_^]\\",
        b"[ZYXWVUTSRQPONMLKJIHGFED",
    )
)
_MERGED_INPUT_CYCLE_STATE_LIMIT = 591
_MERGED_INPUT_CYCLE_PATH_LENGTH = 41
_MERGED_INPUT_CYCLE_STATE_MERGES = 255
_MERGED_INPUT_CYCLE_CYCLE_CLOSING_REPEATS = 2
_MERGED_INPUT_CYCLE_MERGE_SOURCE_POINTER = (2, 40)
_MERGED_INPUT_CYCLE_MERGE_TARGET_POINTER = (3, 41)
_DOUBLE_JUMP_MERGED_CYCLE_SOURCE = b"".join(
    (
        b"u'&$@?>=<;:9876543210/.-,+*)('&%$#\"!~}|{zyxw",
        b"vutsrqponmlkjihgfedcba`_^]\\[ZYXWVUTSRQPONMLK",
        b"JIHGFEDCBA@?>=<;:9876543210/.-,+*)(",
    )
)
_DOUBLE_JUMP_MERGED_CYCLE_STATE_LIMIT = 1_012
_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH = 124
_DOUBLE_JUMP_MERGED_CYCLIC_COMPONENT_COUNT = 2
_DOUBLE_JUMP_MERGED_CYCLE_ADDRESS = 123
_DOUBLE_JUMP_MERGED_CYCLE_INITIAL_VALUE = 29_486
_DOUBLE_JUMP_MERGED_CYCLE_EVOLVED_VALUE = 49_194
_DOUBLE_JUMP_MERGED_CYCLE_WRITER_TRANSITION = 4
_DOUBLE_JUMP_MERGED_CYCLE_WRITER_CODE_POINTER = 3
_DOUBLE_JUMP_MERGED_LOADED_CYCLE_SOURCE = (
    _DOUBLE_JUMP_MERGED_CYCLE_SOURCE + b"'"
)
_DOUBLE_JUMP_MERGED_LOADED_CYCLE_INITIAL_BYTE = 39
_DOUBLE_JUMP_MERGED_CYCLE_DATA_POINTER = 243
_OVER_CAP_INPUT_CYCLE_SOURCE = b"u'&%$#\"!~}|{zyxw"
_OVER_CAP_EXPLORED_STATES = 3_840
_OVER_CAP_MAXIMUM_FIRST_SEEN_TRANSITION = 17
_OVER_CAP_FRONTIER_ACCUMULATOR = 241
_OVER_CAP_FRONTIER_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 29_407),
    (4, 120),
    (5, 29_407),
    (6, 120),
    (7, 29_407),
    (8, 120),
    (9, 29_407),
    (10, 120),
    (11, 29_407),
    (12, 120),
    (13, 29_407),
    (14, 120),
    (15, 29_407),
)
_MAX_WORKLIST_TRUNCATED_LIMIT = (
    "input-dependent-reachability:4096-state-worklist-truncated"
)
_DOUBLE_INPUT_CYCLE_STATE_LIMIT = 515
_FIXED_CYCLE_POINTER = 2
_FIXED_CYCLE_ENCRYPTED_ZERO = 111
_FIXED_CYCLE_ENCRYPTED_ONE = 69
_MEMORY_SCOPE = "16-transition-prefix"
_EXTENDED_CONTROL_FLOW_LIMIT = (
    "control-flow-reachability:32-transition-prefix-only"
)
_TRANSITION_LIMIT_ERROR = (
    "transition limit must be an exact integer from 1 through 256"
)
_WORKLIST_LIMIT_ERROR = (
    "worklist state limit must be an exact integer from 1 through 4096"
)
_ACCESS_FETCH = "instruction-fetch"
_ACCESS_DATA_READ = "data-read"
_ACCESS_DATA_WRITE = "data-write"
_ACCESS_ENCRYPTION = "self-encryption"
_ORIGIN_LOADED_SOURCE = "loaded-source"
_ORIGIN_RECURRENCE = "recurrence-initialization"
_LINEAGE_WRITE_SOURCE = b"(&&$^"
_WORKLIST_EVOLVED_FETCH_STATE_LIMIT = 6
_WORKLIST_EVOLVED_FETCH_INITIAL_VALUE = 29_430
_WORKLIST_EVOLVED_FETCH_ORIGIN_TRANSITION = 4
_WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_FETCH_COUNT = (
    _WORKLIST_EVOLVED_FETCH_STATE_LIMIT - 1
)
_WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_FETCH_ADDRESSES = (0, 1, 2, 3, 4)
_WORKLIST_EVOLVED_FETCH_DATA_READ_COUNT = 5
_WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_COUNT = 5
_WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_ADDRESSES = (0, 41, 42, 95, 96)
_WORKLIST_EVOLVED_FETCH_WRITER_STATE_INDEX = (
    _WORKLIST_EVOLVED_FETCH_ORIGIN_TRANSITION - 1
)
_WORKLIST_EVOLVED_FETCH_WRITER_SOURCE_OFFSET = (
    _WORKLIST_EVOLVED_FETCH_WRITER_STATE_INDEX + _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
)
_DATA_LINEAGE_WORKLIST_STATE_LIMIT = 5
_DATA_LINEAGE_INITIAL_VALUE = 29_558
_DATA_LINEAGE_ORIGIN_TRANSITION = 2
_DATA_LINEAGE_INITIAL_VALUE_FETCH_COUNT = _DATA_LINEAGE_WORKLIST_STATE_LIMIT
_DATA_LINEAGE_INITIAL_VALUE_FETCH_ADDRESSES = (0, 1, 2, 3, 4)
_DATA_LINEAGE_TOTAL_DATA_READ_COUNT = 4
_DATA_LINEAGE_INITIAL_VALUE_DATA_READ_COUNT = 3
_DATA_LINEAGE_INITIAL_VALUE_DATA_READ_ADDRESSES = (0, 41, 42)
_DATA_LINEAGE_WRITER_STATE_INDEX = _DATA_LINEAGE_ORIGIN_TRANSITION - 1
_DATA_LINEAGE_WRITER_SOURCE_OFFSET = (
    _DATA_LINEAGE_WRITER_STATE_INDEX + _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
)
_WORKLIST_WRITER_DATA_WRITE = "data-write"
_LINEAGE_TRANSITION_LIMIT = 6
_LINEAGE_FETCH_ADDRESS = 95
_LINEAGE_FETCH_VALUE = 9_810
_LINEAGE_WRITE_TRANSITION = 4
_DATA_LINEAGE_WRITE_SOURCE = b"(&&%M"
_DATA_LINEAGE_TRANSITION_LIMIT = 5
_DATA_LINEAGE_READ_TRANSITION = 4
_DATA_LINEAGE_WRITE_TRANSITION = 2
_DATA_LINEAGE_ADDRESS = 41
_DATA_LINEAGE_VALUE = 49_218
_THIRD_PREFIX_WORDS = 3
_SECOND_TRANSITION_INDEX = 2
_THIRD_TRANSITION_INDEX = 3
_RECUR_DATA_ADDRESS = 41
_RECUR_DATA_WORDS = 42
_THIRD_STUCK_SOURCE = b"c'"
_FOURTH_STUCK_SOURCE = b"('&"
_FIFTH_TRANSFER_SOURCE = b"('&%"
_FIFTH_FETCH_ADDRESS = 4
_FIFTH_DATA_ADDRESS = 29_490
_FIFTH_MEMORY_WORDS = 42
_FIFTH_HIGHEST_ADDRESS = 41
_FIFTH_ACCESSES = (0, 1, 2, 3, 4, 38, 39, 41)
_FOURTH_FETCH_ADDRESS = 3
_FOURTH_DATA_ADDRESS = 39
_FOURTH_HIGHEST_ADDRESS = 29_488
_FOURTH_MEMORY_WORDS = 29_489
_FOURTH_ACCESSES = (0, 1, 2, 3, 41, 29_488)
_THIRD_STUCK_VALUE = 29_503
_THIRD_STUCK_DATA_ADDRESS = 40
_ROTATED_ENTRY_VALUE = 13
_JUMP_ENTRY_ADDRESS = 98
_JUMP_ENTRY_ENCRYPTION_INPUT = 29_492
_MISSING_SOURCE_MESSAGE = "static analyzer cannot read source"
_ENTRY_MISMATCH_MESSAGE = (
    "explicit entry transition does not match recomputed state"
)
_PREFIX_SOURCE_MESSAGE = "explicit prefix source cannot seed recurrence memory"
_PREFIX_MISMATCH_MESSAGE = (
    "explicit prefix transition does not match recomputed state"
)
_SNAPSHOT_CANONICAL_MESSAGE = "snapshot memory overrides are not canonical"
_GRAPHICAL_START = 33
_GRAPHICAL_END = 126
_DECODE_PERIOD = 94
_HISTORICAL_XLAT1_DECLARATION = "const char xlat1[] ="
_HISTORICAL_XLAT2_DECLARATION = "const char xlat2[] ="
_HISTORICAL_CRAZY_DECLARATION = "static const unsigned short o[9][9] ="
_HISTORICAL_LOAD_ADMISSION_PREFIX = 'strchr( "'
_HISTORICAL_JUMP_DATA_ASSIGNMENT = "case 'j': d = mem[d]; break;"
_HISTORICAL_JUMP_CODE_ASSIGNMENT = "case 'i': c = mem[d]; break;"
_HISTORICAL_CODE_WRAP = "if ( c == 59048 ) c = 0; else c++;"
_HISTORICAL_DATA_WRAP = "if ( d == 59048 ) d = 0; else d++;"
_HISTORICAL_HALT = "case 'v': return;"
_HISTORICAL_ENCRYPTION = "mem[c] = xlat2[mem[c] - 33];"
_HISTORICAL_NON_GRAPHICAL_CONTINUE = (
    "if ( mem[c] < 33 || mem[c] > 126 ) continue;"
)
_HISTORICAL_RECURRENCE = (
    "while ( i < 59049 ) mem[i] = op( mem[i - 1], mem[i - 2] ), i++;"
)
_HISTORICAL_ROTATE = (
    "case '*': a = mem[d] = mem[d] / 3 + mem[d] % 3 * 19683; break;"
)
_TEST_ALLOWED_INSTRUCTIONS = frozenset(b"ji*p</vo")
_TEST_XLAT1 = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
_TEST_XLAT2_HEX_PARTS = (
    "357a5d2667717479667224287765347b575029482d5a6e2c5b255c33644c2b51",
    "3b3e5521704a53373246684f4131434236765e3d495f302f387c6a7362396d3c",
    "2e545661636075592a4d4b27587e78446c7d52456f6b4e3a233f47226940",
)
_TEST_XLAT2 = bytes.fromhex("".join(_TEST_XLAT2_HEX_PARTS))
_CRAZY_POWERS = (1, 9, 81, 729, 6561)
_CRAZY_TABLE_VALUES = 81
_CRAZY_SAMPLES = (0, 1, 2, 8, 9, 40, 98, 116, 59_048)


class _Finding(Protocol):
    code: str
    byte_offset: int | None
    loaded_position: int | None
    source_byte: int | None
    decoded_byte: int | None


class _Cell(Protocol):
    position: int
    byte_offset: int
    source_byte: int
    decoded_byte: int
    post_step_encryption_target: str
    data_alias_can_change_encryption_input: bool


class _EntryTransition(Protocol):
    status: str
    fetched_address: int
    decoded_byte: int
    data_address: int
    code_data_alias: bool
    planned_data_write_address: int | None
    planned_data_write_value: int | None
    encryption_address: int | None
    encryption_input: int | None
    encryption_output: int | None
    data_write_aliases_encryption: bool
    input_dependent_accumulator: bool
    result_accumulator: int | None
    result_code_pointer: int
    result_data_pointer: int
    next_fetch_address: int | None
    pointer_wraps: bool
    accepted: bool


class _SecondTransition(Protocol):
    status: str
    fetched_address: int
    fetched_value: int
    decoded_byte: int | None
    data_address: int
    data_value: int | None
    code_data_alias: bool
    planned_data_write_address: int | None
    planned_data_write_value: int | None
    encryption_address: int | None
    encryption_input: int | None
    encryption_output: int | None
    data_write_aliases_encryption: bool
    input_dependent_accumulator: bool
    result_accumulator: int | None
    result_code_pointer: int | None
    result_data_pointer: int | None
    next_fetch_address: int | None
    pointer_wraps: bool
    provable_cycle: bool
    accepted: bool


class _StateSnapshot(Protocol):
    before_transition: int
    code_pointer: int
    data_pointer: int
    accumulator: int | None
    memory_overrides: tuple[tuple[int, int], ...]


class _SnapshotStep(Protocol):
    transition: _SecondTransition
    successor: _StateSnapshot | None


class _WorklistCycleState(Protocol):
    code_pointer: int
    data_pointer: int
    accumulator: int
    memory_overrides: tuple[tuple[int, int], ...]
    eof_seen: bool


class _WorklistTerminalWitness(Protocol):
    status: str
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]


class _WorklistWrapWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool


class _WorklistWrapTransitionSignature(Protocol):
    source_code_pointer: int
    source_data_pointer: int
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool


class _WorklistValueDomain(Protocol):
    address: int
    values: tuple[int, ...]


class _WorklistCycleClosingRepeatedEdgeWitness(Protocol):
    source_state: _WorklistCycleState
    source_entry_path: tuple[_WorklistCycleState, ...]
    target_state: _WorklistCycleState
    target_entry_path_state_index: int


class _WorklistStateMergeWitness(Protocol):
    source_state: _WorklistCycleState
    source_entry_path: tuple[_WorklistCycleState, ...]
    target_state: _WorklistCycleState
    existing_target_entry_path: tuple[_WorklistCycleState, ...]


class _WorklistCodeDataAliasWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    memory_value: int


class _WorklistEvolvedReadWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    initial_value: int
    observed_value: int
    origin_kind: str
    origin_entry_path_transition_index: int
    origin_value: int


class _WorklistDataMutationValueDomain(Protocol):
    address: int
    previous_values: tuple[int, ...]
    result_values: tuple[int, ...]


class _WorklistDataWriteNoopWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


class _WorklistDataMutationWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


class _WorklistDataMutationSourceContext(Protocol):
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    previous_value_matches_initial_source: bool | None


class _WorklistDataMutationValueSourceContext(Protocol):
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    previous_values: tuple[int, ...]
    result_values: tuple[int, ...]
    initial_source_byte_in_previous_values: bool | None


class _WorklistValueSourceContext(Protocol):
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    initial_memory_value: int
    values: tuple[int, ...]
    initial_source_byte_in_values: bool | None
    initial_memory_value_in_values: bool


class _WorklistControlPathSourceContext(Protocol):
    entry_path_state_index: int
    code_pointer: int
    data_pointer: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    data_source_position: int | None
    data_source_byte_offset: int | None
    initial_data_source_byte: int | None


class _WorklistWrapTransitionSourceContext(Protocol):
    source_code_pointer: int
    source_data_pointer: int
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    data_source_position: int | None
    data_source_byte_offset: int | None
    initial_data_source_byte: int | None


class _WorklistCycleStateSourceContext(Protocol):
    cycle_state_index: int
    code_pointer: int
    data_pointer: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    data_source_position: int | None
    data_source_byte_offset: int | None
    initial_data_source_byte: int | None


class _WorklistCycleComponentSourceMap(Protocol):
    component_index: int
    minimum_entry_path_state_count: int
    states: tuple[_WorklistCycleStateSourceContext, ...]


class _WorklistCycleClosingRepeatedEdgeSourceContext(Protocol):
    source_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    target_entry_path_state_index: int
    target_state_source_context: _WorklistControlPathSourceContext


class _WorklistStateMergeSourceContext(Protocol):
    source_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    target_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]


class _WorklistCodeDataAliasSourceContext(Protocol):
    address: int
    memory_value: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    entry_path_source_map: tuple[_WorklistControlPathSourceContext, ...]


class _WorklistEvolvedReadWriterSourceContext(Protocol):
    origin_kind: str
    origin_entry_path_transition_index: int
    origin_value: int
    writer_state_source_context: _WorklistControlPathSourceContext


class _WorklistTerminalControlPathSourceMap(Protocol):
    status: str
    entry_path_source_map: tuple[_WorklistControlPathSourceContext, ...]


class _WorklistMutationAddressSourceContext(Protocol):
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None


class _WorklistAnalysis(Protocol):
    state_limit: int
    unique_states: int
    explored_states: int
    repeated_state_edges: int
    explored_state_merge_transition_count: int
    explored_cycle_closing_repeated_edge_count: int
    explored_cycle_closing_repeated_edge_witness: (
        _WorklistCycleClosingRepeatedEdgeWitness | None
    )
    explored_state_merge_witness: _WorklistStateMergeWitness | None
    reachable_cycle_detected: bool
    reachable_cycle_witness: tuple[_WorklistCycleState, ...]
    reachable_cycle_entry_path: tuple[_WorklistCycleState, ...]
    known_graph_strong_component_count: int
    known_graph_cyclic_component_count: int
    known_graph_cyclic_state_count: int
    known_graph_largest_cyclic_component_states: int
    known_graph_cyclic_components: tuple[
        tuple[_WorklistCycleState, ...], ...
    ]
    known_graph_cyclic_component_minimum_entry_path_state_counts: (
        tuple[int, ...]
    )
    closed_recurrent_component_count: int | None
    closed_recurrent_state_count: int | None
    closed_recurrent_largest_component_states: int | None
    closed_recurrent_components: (
        tuple[tuple[_WorklistCycleState, ...], ...] | None
    )
    closed_recurrent_component_minimum_entry_path_state_counts: (
        tuple[int, ...] | None
    )
    closed_recurrent_cycle_witness: tuple[_WorklistCycleState, ...] | None
    closed_recurrent_entry_path: tuple[_WorklistCycleState, ...] | None
    input_branch_points: int
    terminal_status_counts: tuple[tuple[str, int], ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[_WorklistTerminalWitness, ...]
    explored_code_pointer_addresses: tuple[int, ...]
    explored_data_pointer_addresses: tuple[int, ...]
    explored_code_data_alias_transition_count: int
    explored_code_data_alias_addresses: tuple[int, ...]
    explored_code_data_alias_witnesses: tuple[
        _WorklistCodeDataAliasWitness, ...
    ]
    explored_committed_write_count: int
    explored_committed_write_addresses: tuple[int, ...]
    explored_planned_data_write_transition_count: int
    explored_planned_data_write_addresses: tuple[int, ...]
    explored_planned_data_write_value_domains: tuple[_WorklistValueDomain, ...]
    explored_committed_data_write_transition_count: int
    explored_committed_data_write_addresses: tuple[int, ...]
    explored_committed_data_write_noop_transition_count: int
    explored_committed_data_write_noop_addresses: tuple[int, ...]
    explored_self_encryption_transition_count: int
    explored_self_encryption_addresses: tuple[int, ...]
    explored_effective_data_mutation_transition_count: int
    explored_effective_data_mutation_addresses: tuple[int, ...]
    explored_effective_data_mutation_value_domains: tuple[
        _WorklistDataMutationValueDomain, ...
    ]
    explored_fetch_value_domains: tuple[_WorklistValueDomain, ...]
    explored_data_read_value_domains: tuple[_WorklistValueDomain, ...]
    explored_encryption_input_value_domains: tuple[_WorklistValueDomain, ...]
    explored_encryption_input_transition_count: int
    explored_initial_value_encryption_input_transition_count: int
    explored_initial_value_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_transition_count: int
    explored_changed_from_initial_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_committed_data_write_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_self_encryption_output_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_initial_value_fetch_transition_count: int
    explored_initial_value_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_transition_count: int
    explored_evolved_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_value_domains: tuple[_WorklistValueDomain, ...]
    explored_data_read_transition_count: int
    explored_initial_value_data_read_transition_count: int
    explored_initial_value_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_transition_count: int
    explored_evolved_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_value_domains: tuple[_WorklistValueDomain, ...]
    explored_evolved_fetch_witness: _WorklistEvolvedReadWitness | None
    explored_evolved_data_read_witness: _WorklistEvolvedReadWitness | None
    explored_data_write_noop_witness: _WorklistDataWriteNoopWitness | None
    explored_data_mutation_witness: _WorklistDataMutationWitness | None
    explored_minimum_words: int
    explored_highest_accessed_address: int
    explored_accessed_addresses: tuple[int, ...]
    explored_wraparound_transition_count: int
    explored_code_pointer_wrap_transition_count: int
    explored_data_pointer_wrap_transition_count: int
    explored_simultaneous_pointer_wrap_transition_count: int
    explored_wraparound_transition_signatures: tuple[
        _WorklistWrapTransitionSignature, ...
    ]
    explored_wraparound_witness: _WorklistWrapWitness | None
    explored_code_pointer_wrap_witness: _WorklistWrapWitness | None
    explored_data_pointer_wrap_witness: _WorklistWrapWitness | None
    explored_simultaneous_pointer_wrap_witness: _WorklistWrapWitness | None
    maximum_first_seen_transition_index: int
    frontier_states: int
    frontier_state_witness: _WorklistCycleState | None
    frontier_entry_path: tuple[_WorklistCycleState, ...] | None
    truncated: bool


class _ExactCycleCertificate(Protocol):
    first_seen_before_transition: int
    repeated_before_transition: int
    period_transitions: int
    code_pointer: int
    data_pointer: int
    accumulator: int
    memory_overrides: tuple[tuple[int, int], ...]


class _BoundedMemoryRequirement(Protocol):
    scope: str
    minimum_words: int
    highest_accessed_address: int
    accessed_addresses: tuple[int, ...]


class _BoundedFetchSourceContext(Protocol):
    transition_index: int
    fetched_address: int
    fetched_value: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None
    fetched_value_matches_initial_source: bool | None


class _BoundedFetchValueLineage(Protocol):
    transition_index: int
    fetched_address: int
    fetched_value: int
    origin_kind: str
    origin_transition_index: int | None


class _BoundedDataReadValueLineage(Protocol):
    transition_index: int
    data_address: int
    data_value: int
    origin_kind: str
    origin_transition_index: int | None


class _BoundedEncryptionInputValueLineage(Protocol):
    transition_index: int
    encryption_address: int
    encryption_input: int
    origin_kind: str
    origin_transition_index: int | None


class _BoundedMemoryAccessSourceContext(Protocol):
    transition_index: int
    access_kind: str
    address: int
    source_position: int | None
    source_byte_offset: int | None
    initial_source_byte: int | None


class _Report(Protocol):
    schema: str
    profile_id: str
    profile_version: str
    profile_memory_words: int
    profile_address_domain_closed: bool
    source_sha256: str
    required_source_words: int
    bounded_transition_limit: int
    bounded_continuations: tuple[_SecondTransition, ...]
    bounded_state_snapshots: tuple[_StateSnapshot, ...]
    bounded_worklist: _WorklistAnalysis | None
    bounded_worklist_cycle_closing_repeated_edge_source_context: (
        _WorklistCycleClosingRepeatedEdgeSourceContext | None
    )
    bounded_worklist_state_merge_source_context: (
        _WorklistStateMergeSourceContext | None
    )
    bounded_worklist_explored_code_pointer_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_explored_data_pointer_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_code_data_alias_source_contexts: tuple[
        _WorklistCodeDataAliasSourceContext, ...
    ]
    bounded_worklist_data_mutation_source_context: (
        _WorklistDataMutationSourceContext | None
    )
    bounded_worklist_effective_data_mutation_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_effective_data_mutation_value_source_map: tuple[
        _WorklistDataMutationValueSourceContext, ...
    ]
    bounded_worklist_committed_write_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_committed_data_write_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_self_encryption_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_fetch_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_data_read_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_encryption_input_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_initial_value_encryption_input_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_changed_encryption_input_value_source_map: (
        tuple[_WorklistValueSourceContext, ...]
    )
    bounded_worklist_initial_value_fetch_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_initial_value_data_read_source_map: tuple[
        _WorklistMutationAddressSourceContext, ...
    ]
    bounded_worklist_evolved_data_read_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_planned_data_write_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_committed_data_write_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_self_encryption_output_value_source_map: tuple[
        _WorklistValueSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_evolved_data_read_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_evolved_fetch_writer_source_context: (
        _WorklistEvolvedReadWriterSourceContext | None
    )
    bounded_worklist_evolved_data_read_writer_source_context: (
        _WorklistEvolvedReadWriterSourceContext | None
    )
    bounded_worklist_data_mutation_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_data_write_noop_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_wraparound_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_code_pointer_wrap_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_data_pointer_wrap_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_simultaneous_pointer_wrap_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_wraparound_transition_source_map: tuple[
        _WorklistWrapTransitionSourceContext, ...
    ]
    bounded_worklist_cycle_witness_source_map: tuple[
        _WorklistCycleStateSourceContext, ...
    ]
    bounded_worklist_closed_recurrent_cycle_witness_source_map: tuple[
        _WorklistCycleStateSourceContext, ...
    ]
    bounded_worklist_known_graph_cyclic_component_source_maps: tuple[
        _WorklistCycleComponentSourceMap, ...
    ]
    bounded_worklist_closed_recurrent_component_source_maps: (
        tuple[_WorklistCycleComponentSourceMap, ...] | None
    )
    bounded_worklist_cycle_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_closed_recurrent_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_frontier_entry_path_source_map: tuple[
        _WorklistControlPathSourceContext, ...
    ]
    bounded_worklist_terminal_entry_path_source_maps: tuple[
        _WorklistTerminalControlPathSourceMap, ...
    ]
    bounded_exact_cycle: _ExactCycleCertificate | None
    bounded_memory_requirement: _BoundedMemoryRequirement | None
    bounded_fetch_source_map: tuple[_BoundedFetchSourceContext, ...]
    bounded_fetch_value_lineage: tuple[_BoundedFetchValueLineage, ...]
    bounded_data_read_value_lineage: tuple[_BoundedDataReadValueLineage, ...]
    bounded_encryption_input_value_lineage: tuple[
        _BoundedEncryptionInputValueLineage, ...
    ]
    bounded_memory_access_source_map: tuple[
        _BoundedMemoryAccessSourceContext, ...
    ]
    admitted_initial_image: bool
    initial_cells: tuple[_Cell, ...]
    entry_transition: _EntryTransition | None
    second_transition: _SecondTransition | None
    third_transition: _SecondTransition | None
    fourth_transition: _SecondTransition | None
    fifth_transition: _SecondTransition | None
    findings: tuple[_Finding, ...]
    analysis_limits: tuple[str, ...]


class _ClassicModule(Protocol):
    def crazy(self, data: int, accumulator: int) -> int:
        """Return one classic crazy-operation result."""
        ...


class _EntryModule(Protocol):
    def analyze_entry_transition(
        self,
        words: tuple[int, ...],
        decoded: int,
    ) -> _EntryTransition:
        """Resolve one exact entry transition for a supplied decoded opcode."""
        ...


class _PrefixModule(Protocol):
    def analyze_continuations(
        self,
        words: tuple[int, ...],
        entry: _EntryTransition,
        *,
        maximum_transitions: int,
    ) -> tuple[_SecondTransition, ...]:
        """Resolve a finite exact continuation trace after entry."""
        ...

    def analyze_next_transition(
        self,
        words: tuple[int, ...],
        entry: _EntryTransition,
        prior: tuple[_SecondTransition, ...],
    ) -> _SecondTransition | None:
        """Resolve exactly one step after an explicit finite prefix."""
        ...

    def analyze_state_snapshot(
        self,
        words: tuple[int, ...],
        snapshot: _StateSnapshot,
    ) -> _SnapshotStep:
        """Resolve one validated caller-supplied snapshot transition."""
        ...


class _AnalyzerModule(Protocol):
    entry_transfer: _EntryModule
    prefix_transfer: _PrefixModule

    def analyze_source(
        self,
        source: bytes,
        *,
        transition_limit: int = _TOTAL_TRANSITION_LIMIT,
        worklist_state_limit: int | None = None,
    ) -> _Report:
        """Analyze source without running it."""
        ...

    def render_report(self, report: _Report) -> str:
        """Render canonical report JSON."""
        ...

    def main(self, arguments: list[str] | None = None) -> int:
        """Run the public CLI entry point over explicit arguments."""
        ...


def _load_analyzer() -> _AnalyzerModule:
    spec = importlib.util.spec_from_file_location("emitted_malbolge", _ANALYZER)
    if spec is None or spec.loader is None:
        message = "static analyzer module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ANALYZER.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_AnalyzerModule", cast("object", module))


def _load_classic() -> _ClassicModule:
    spec = importlib.util.spec_from_file_location(
        "emitted_malbolge_classic_primary_test", _CLASSIC
    )
    if spec is None or spec.loader is None:
        message = "classic verifier module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_ClassicModule", cast("object", module))


_ANALYZER_MODULE = _load_analyzer()
_CLASSIC_MODULE = _load_classic()


def _historical_xlat1_literals(tail: str) -> list[str]:
    literals: list[str] = []
    for line in tail.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(";"):
            literals.append(stripped.removesuffix(";"))
            return literals
        literals.append(stripped)
    message = "historical interpreter xlat1 terminator is missing"
    raise AssertionError(message)


def _historical_xlat1() -> bytes:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, declaration, tail = source.partition(_HISTORICAL_XLAT1_DECLARATION)
    if not declaration:
        message = "historical interpreter xlat1 declaration is missing"
        raise AssertionError(message)
    literals = _historical_xlat1_literals(tail)
    try:
        decoded = "".join(ast.literal_eval(literal) for literal in literals)
    except (SyntaxError, ValueError) as error:
        message = "historical interpreter xlat1 literal is malformed"
        raise AssertionError(message) from error
    return decoded.encode("ascii")


def _historical_xlat2() -> bytes:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, declaration, tail = source.partition(_HISTORICAL_XLAT2_DECLARATION)
    if not declaration:
        message = "historical interpreter xlat2 declaration is missing"
        raise AssertionError(message)
    literals = _historical_xlat1_literals(tail)
    try:
        decoded = "".join(ast.literal_eval(literal) for literal in literals)
    except (SyntaxError, ValueError) as error:
        message = "historical interpreter xlat2 literal is malformed"
        raise AssertionError(message) from error
    return decoded.encode("ascii")


def _parse_crazy_values(body: str) -> tuple[int, ...]:
    parsed: list[int] = []
    for line in body.splitlines():
        row = line.strip().strip("{}, ")
        if row:
            parsed.extend(int(value.strip()) for value in row.split(","))
    return tuple(parsed)


def _historical_crazy_matrix() -> tuple[tuple[int, ...], ...]:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, declaration, tail = source.partition(_HISTORICAL_CRAZY_DECLARATION)
    if not declaration:
        message = "historical interpreter crazy table is missing"
        raise AssertionError(message)
    body, terminator, _ = tail.partition("};")
    if not terminator:
        message = "historical interpreter crazy table terminator is missing"
        raise AssertionError(message)
    values = _parse_crazy_values(body)
    if len(values) != _CRAZY_TABLE_VALUES:
        message = "historical interpreter crazy table shape is invalid"
        raise AssertionError(message)
    return tuple(
        values[offset : offset + 9] for offset in range(0, len(values), 9)
    )


def _historical_c_op(accumulator: int, data: int) -> int:
    matrix = _historical_crazy_matrix()
    return sum(
        matrix[(data // place) % 9][(accumulator // place) % 9] * place
        for place in _CRAZY_POWERS
    )


def _historical_load_instructions() -> frozenset[int]:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, marker, tail = source.partition(_HISTORICAL_LOAD_ADMISSION_PREFIX)
    if not marker:
        message = "historical interpreter load-admission set is missing"
        raise AssertionError(message)
    literal, terminator, _ = tail.partition('"')
    if not terminator:
        message = "historical interpreter load-admission literal is malformed"
        raise AssertionError(message)
    return frozenset(literal.encode("ascii"))


def _source_byte_for_decode(decoded: int, position: int) -> int:
    index = _TEST_XLAT1.index(decoded)
    return ((index - position) % _DECODE_PERIOD) + _GRAPHICAL_START


def test_report_hash_binds_exact_source_bytes() -> None:
    """Report identity includes the exact raw source byte hash."""
    source = _FIXTURE.read_bytes()
    report = _ANALYZER_MODULE.analyze_source(source)
    expected = "sha256:" + sha256(source).hexdigest()
    assert report.source_sha256 == expected

    mutated = source + b" "
    mutated_report = _ANALYZER_MODULE.analyze_source(mutated)
    assert mutated_report.required_source_words == report.required_source_words
    assert mutated_report.source_sha256 != report.source_sha256


def test_report_profile_identity_matches_canonical_authority() -> None:
    """Historical report identity is a projection of canonical malbolge.json."""
    canonical = cast(
        "dict[str, object]",
        json.loads((_ROOT / "malbolge.json").read_text(encoding="utf-8")),
    )
    profiles = cast("dict[str, object]", canonical["profiles"])
    historical = cast("dict[str, object]", profiles[_PROFILE_ID])
    memory = cast("dict[str, object]", historical["memory"])
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_version == historical["version"]
    assert report.profile_memory_words == memory["words"]


def test_independent_decode_table_matches_preserved_interpreter() -> None:
    """Independent decode expectations are anchored to primary evidence."""
    assert _historical_xlat1() == _TEST_XLAT1


def test_independent_encryption_table_matches_preserved_interpreter() -> None:
    """Independent encryption expectations are anchored to primary evidence."""
    assert _historical_xlat2() == _TEST_XLAT2


def test_crazy_operand_orientation_matches_preserved_interpreter() -> None:
    """Anchor VM data/accumulator orientation to the historical C `op`."""
    for data in _CRAZY_SAMPLES:
        for accumulator in _CRAZY_SAMPLES:
            expected = _historical_c_op(accumulator, data)
            assert _CLASSIC_MODULE.crazy(data, accumulator) == expected


def test_load_admission_set_matches_preserved_interpreter() -> None:
    """Anchor independent load-admission expectations to primary evidence."""
    assert _historical_load_instructions() == _TEST_ALLOWED_INSTRUCTIONS


def test_known_valid_fixture_has_exact_initial_decode() -> None:
    """Historical roundtrip source is admitted with fixed independent decode."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.admitted_initial_image
    assert report.profile_id == _PROFILE_ID
    assert report.profile_memory_words == _PROFILE_MEMORY_WORDS
    assert report.profile_address_domain_closed
    assert report.required_source_words == _FIXTURE_SOURCE_WORDS
    assert [cell.source_byte for cell in report.initial_cells] == [99, 116, 79]
    assert [cell.decoded_byte for cell in report.initial_cells] == [60, 47, 118]
    assert report.findings == ()


def test_bounded_fetch_source_map_preserves_raw_offsets() -> None:
    """Bounded fetches map loaded addresses back to exact raw source offsets."""
    source = bytes((ord("c"), 10, ord("'")))
    report = _ANALYZER_MODULE.analyze_source(source)
    contexts = report.bounded_fetch_source_map
    assert len(contexts) == _THIRD_PREFIX_WORDS
    first, second, third = contexts
    assert (
        first.transition_index,
        first.fetched_address,
        first.source_position,
        first.source_byte_offset,
        first.initial_source_byte,
        first.fetched_value_matches_initial_source,
    ) == (1, 0, 0, 0, ord("c"), True)
    assert (
        second.transition_index,
        second.fetched_address,
        second.source_position,
        second.source_byte_offset,
        second.initial_source_byte,
        second.fetched_value_matches_initial_source,
    ) == (2, 1, 1, 2, ord("'"), True)
    assert third.transition_index == _THIRD_TRANSITION_INDEX
    assert third.fetched_address == _SECOND_SUCCESSOR
    assert third.fetched_value == _THIRD_STUCK_VALUE
    assert third.source_position is None
    assert third.source_byte_offset is None
    assert third.initial_source_byte is None
    assert third.fetched_value_matches_initial_source is None


def test_bounded_state_snapshots_track_evolved_memory() -> None:
    """Pre-step snapshots preserve registers and sparse evolved memory."""
    report = _ANALYZER_MODULE.analyze_source(
        _DATA_LINEAGE_WRITE_SOURCE,
        transition_limit=_DATA_LINEAGE_TRANSITION_LIMIT,
    )
    snapshots = report.bounded_state_snapshots
    assert len(snapshots) == _DATA_LINEAGE_TRANSITION_LIMIT
    initial = snapshots[0]
    assert (
        initial.before_transition,
        initial.code_pointer,
        initial.data_pointer,
        initial.accumulator,
        initial.memory_overrides,
    ) == (1, 0, 0, 0, ())
    before_read = snapshots[_DATA_LINEAGE_READ_TRANSITION - 1]
    assert before_read.before_transition == _DATA_LINEAGE_READ_TRANSITION
    assert before_read.code_pointer == _THIRD_TRANSITION_INDEX
    assert before_read.data_pointer == _DATA_LINEAGE_ADDRESS
    assert before_read.accumulator == _DATA_LINEAGE_VALUE
    assert before_read.memory_overrides == (
        (0, 121),
        (1, 113),
        (2, 113),
        (_DATA_LINEAGE_ADDRESS, _DATA_LINEAGE_VALUE),
    )


def test_bounded_state_snapshots_preserve_unknown_input_accumulator() -> None:
    """Input dependency remains explicit in the next pre-step snapshot."""
    source = bytes((
        _source_byte_for_decode(ord("/"), 0),
        _source_byte_for_decode(ord("p"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    snapshots = report.bounded_state_snapshots
    assert len(snapshots) == _TWO_SOURCE_WORDS
    after_input = snapshots[1]
    assert after_input.before_transition == _SECOND_TRANSITION_INDEX
    assert after_input.code_pointer == 1
    assert after_input.data_pointer == 1
    assert after_input.accumulator is None
    assert after_input.memory_overrides


def test_bounded_fetch_value_lineage_tracks_initial_origins_and_write() -> None:
    """Fetch lineage distinguishes initial values from a prior data write."""
    recurrence = _ANALYZER_MODULE.analyze_source(bytes((ord("c"), ord("'"))))
    recurrence_lineage = recurrence.bounded_fetch_value_lineage
    assert recurrence_lineage[0].origin_kind == _ORIGIN_LOADED_SOURCE
    assert recurrence_lineage[0].origin_transition_index is None
    assert recurrence_lineage[2].origin_kind == _ORIGIN_RECURRENCE
    assert recurrence_lineage[2].origin_transition_index is None

    written = _ANALYZER_MODULE.analyze_source(
        _LINEAGE_WRITE_SOURCE,
        transition_limit=_LINEAGE_TRANSITION_LIMIT,
    )
    final = written.bounded_fetch_value_lineage[-1]
    assert final.transition_index == _LINEAGE_TRANSITION_LIMIT
    assert final.fetched_address == _LINEAGE_FETCH_ADDRESS
    assert final.fetched_value == _LINEAGE_FETCH_VALUE
    assert final.origin_kind == _ACCESS_DATA_WRITE
    assert final.origin_transition_index == _LINEAGE_WRITE_TRANSITION


def test_bounded_data_read_lineage_tracks_recurrence_and_prior_write() -> None:
    """Data reads distinguish recurrence values from evolved-memory writes."""
    recurrence = _ANALYZER_MODULE.analyze_source(b"('")
    recurrence_lineage = recurrence.bounded_data_read_value_lineage
    assert recurrence_lineage[0].origin_kind == _ORIGIN_LOADED_SOURCE
    assert recurrence_lineage[0].origin_transition_index is None
    assert recurrence_lineage[1].data_address == _RECUR_DATA_ADDRESS
    assert recurrence_lineage[1].origin_kind == _ORIGIN_RECURRENCE
    assert recurrence_lineage[1].origin_transition_index is None

    written = _ANALYZER_MODULE.analyze_source(
        _DATA_LINEAGE_WRITE_SOURCE,
        transition_limit=_DATA_LINEAGE_TRANSITION_LIMIT,
    )
    final = written.bounded_data_read_value_lineage[-1]
    assert final.transition_index == _DATA_LINEAGE_READ_TRANSITION
    assert final.data_address == _DATA_LINEAGE_ADDRESS
    assert final.data_value == _DATA_LINEAGE_VALUE
    assert final.origin_kind == _ACCESS_DATA_WRITE
    assert final.origin_transition_index == _DATA_LINEAGE_WRITE_TRANSITION


def _assert_evolved_fetch_writer_source_context(report: _Report) -> None:
    context = report.bounded_worklist_evolved_fetch_writer_source_context
    assert context is not None
    assert context.origin_kind == _WORKLIST_WRITER_DATA_WRITE
    assert (
        context.origin_entry_path_transition_index
        == _WORKLIST_EVOLVED_FETCH_ORIGIN_TRANSITION
    )
    assert context.origin_value == _LINEAGE_FETCH_VALUE
    writer = context.writer_state_source_context
    assert (
        writer.entry_path_state_index
        == _WORKLIST_EVOLVED_FETCH_WRITER_STATE_INDEX
    )
    assert writer.code_pointer == _WORKLIST_EVOLVED_FETCH_WRITER_STATE_INDEX
    assert writer.source_position == _WORKLIST_EVOLVED_FETCH_WRITER_STATE_INDEX
    assert (
        writer.source_byte_offset
        == _WORKLIST_EVOLVED_FETCH_WRITER_SOURCE_OFFSET
    )
    assert writer.data_pointer == _LINEAGE_FETCH_ADDRESS
    assert writer.data_source_position is None


def _assert_evolved_data_writer_source_context(report: _Report) -> None:
    context = report.bounded_worklist_evolved_data_read_writer_source_context
    assert context is not None
    assert context.origin_kind == _WORKLIST_WRITER_DATA_WRITE
    assert (
        context.origin_entry_path_transition_index
        == _DATA_LINEAGE_ORIGIN_TRANSITION
    )
    assert context.origin_value == _DATA_LINEAGE_VALUE
    writer = context.writer_state_source_context
    assert writer.entry_path_state_index == _DATA_LINEAGE_WRITER_STATE_INDEX
    assert writer.code_pointer == _DATA_LINEAGE_WRITER_STATE_INDEX
    assert writer.source_position == _DATA_LINEAGE_WRITER_STATE_INDEX
    assert writer.source_byte_offset == _DATA_LINEAGE_WRITER_SOURCE_OFFSET
    assert writer.data_pointer == _DATA_LINEAGE_ADDRESS
    assert writer.data_source_position is None


def _assert_evolved_fetch_control_source_map(report: _Report) -> None:
    contexts = report.bounded_worklist_evolved_fetch_entry_path_source_map
    path_indexes = tuple(context.entry_path_state_index for context in contexts)
    assert path_indexes == tuple(range(len(contexts)))
    assert tuple(context.code_pointer for context in contexts) == (
        0, 1, 2, 3, 4, 95
    )
    assert tuple(context.source_byte_offset for context in contexts) == (
        0, 1, 2, 3, 4, None
    )
    assert tuple(context.initial_source_byte for context in contexts) == (
        *_LINEAGE_WRITE_SOURCE,
        None,
    )


def _assert_evolved_data_control_source_map(report: _Report) -> None:
    contexts = report.bounded_worklist_evolved_data_read_entry_path_source_map
    assert tuple(context.entry_path_state_index for context in contexts) == (
        0, 1, 2, 3
    )
    assert tuple(context.code_pointer for context in contexts) == (0, 1, 2, 3)
    source_positions = tuple(context.source_position for context in contexts)
    assert source_positions == (0, 1, 2, 3)
    assert tuple(context.source_byte_offset for context in contexts) == (
        0, 1, 2, 3
    )


def test_worklist_maps_initial_value_equal_read_addresses() -> None:
    """Equality partitions map loaded addresses without implying provenance."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.explored_data_read_transition_count == (
        _ENTRY_DATA_READ_TRANSITION_COUNT
    )
    assert worklist.explored_initial_value_data_read_transition_count == (
        _ENTRY_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert worklist.explored_initial_value_data_read_addresses == (
        _ENTRY_INITIAL_VALUE_DATA_READ_ADDRESSES
    )
    fetch_map = report.bounded_worklist_initial_value_fetch_source_map
    assert tuple(context.address for context in fetch_map) == tuple(range(7))
    assert tuple(context.source_byte_offset for context in fetch_map) == tuple(
        range(2, 9)
    )
    data_map = report.bounded_worklist_initial_value_data_read_source_map
    assert tuple(context.address for context in data_map) == (
        _ENTRY_INITIAL_VALUE_DATA_READ_ADDRESSES
    )
    assert tuple(context.source_byte_offset for context in data_map) == (
        3,
        None,
        None,
        None,
    )


def test_worklist_maps_evolved_value_domains_against_initial_memory() -> None:
    """Changed-only value maps retain recurrence initial-memory baselines."""
    fetch_report = _ANALYZER_MODULE.analyze_source(
        _LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_WORKLIST_EVOLVED_FETCH_STATE_LIMIT,
    )
    fetch = _value_source_context(
        fetch_report.bounded_worklist_evolved_fetch_value_source_map,
        _LINEAGE_FETCH_ADDRESS,
    )
    assert fetch.source_position is None
    assert fetch.initial_source_byte is None
    assert fetch.initial_memory_value == _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE
    assert fetch.values == (_LINEAGE_FETCH_VALUE,)
    assert fetch.initial_source_byte_in_values is None
    assert fetch.initial_memory_value_in_values is False

    data_report = _ANALYZER_MODULE.analyze_source(
        _DATA_LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_DATA_LINEAGE_WORKLIST_STATE_LIMIT,
    )
    data = _value_source_context(
        data_report.bounded_worklist_evolved_data_read_value_source_map,
        _DATA_LINEAGE_ADDRESS,
    )
    assert data.source_position is None
    assert data.initial_source_byte is None
    assert data.initial_memory_value == _DATA_LINEAGE_INITIAL_VALUE
    assert data.values == (_DATA_LINEAGE_VALUE,)
    assert data.initial_source_byte_in_values is None
    assert data.initial_memory_value_in_values is False


def test_worklist_maps_evolved_read_writer_states_to_source() -> None:
    """Last-writer state source maps preserve C offsets and recurrence D."""
    fetch = _ANALYZER_MODULE.analyze_source(
        b" \n" + _LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_WORKLIST_EVOLVED_FETCH_STATE_LIMIT,
    )
    _assert_evolved_fetch_writer_source_context(fetch)
    data = _ANALYZER_MODULE.analyze_source(
        b" \n" + _DATA_LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_DATA_LINEAGE_WORKLIST_STATE_LIMIT,
    )
    _assert_evolved_data_writer_source_context(data)


def _assert_evolved_fetch_read_partition(worklist: _WorklistAnalysis) -> None:
    assert worklist.explored_initial_value_fetch_transition_count == (
        _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_FETCH_COUNT
    )
    assert worklist.explored_initial_value_fetch_addresses == (
        _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_FETCH_ADDRESSES
    )
    assert worklist.explored_data_read_transition_count == (
        _WORKLIST_EVOLVED_FETCH_DATA_READ_COUNT
    )
    assert worklist.explored_initial_value_data_read_transition_count == (
        _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert worklist.explored_initial_value_data_read_addresses == (
        _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_ADDRESSES
    )


def _assert_evolved_data_read_partition(worklist: _WorklistAnalysis) -> None:
    assert worklist.explored_initial_value_fetch_transition_count == (
        _DATA_LINEAGE_INITIAL_VALUE_FETCH_COUNT
    )
    assert worklist.explored_initial_value_fetch_addresses == (
        _DATA_LINEAGE_INITIAL_VALUE_FETCH_ADDRESSES
    )
    assert worklist.explored_data_read_transition_count == (
        _DATA_LINEAGE_TOTAL_DATA_READ_COUNT
    )
    assert worklist.explored_initial_value_data_read_transition_count == (
        _DATA_LINEAGE_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert worklist.explored_initial_value_data_read_addresses == (
        _DATA_LINEAGE_INITIAL_VALUE_DATA_READ_ADDRESSES
    )


def test_worklist_report_witnesses_evolved_fetch() -> None:
    """Public worklist report exposes the first changed instruction fetch."""
    report = _ANALYZER_MODULE.analyze_source(
        _LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_WORKLIST_EVOLVED_FETCH_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    witness = worklist.explored_evolved_fetch_witness
    assert witness is not None
    assert witness.address == _LINEAGE_FETCH_ADDRESS
    assert witness.initial_value == _WORKLIST_EVOLVED_FETCH_INITIAL_VALUE
    _assert_evolved_fetch_read_partition(worklist)
    assert worklist.explored_evolved_fetch_transition_count == 1
    assert worklist.explored_evolved_fetch_addresses == (
        _LINEAGE_FETCH_ADDRESS,
    )
    fetch_domain = worklist.explored_evolved_fetch_value_domains[0]
    assert fetch_domain.address == _LINEAGE_FETCH_ADDRESS
    assert fetch_domain.values == (_LINEAGE_FETCH_VALUE,)
    assert worklist.explored_evolved_data_read_transition_count == 0
    assert worklist.explored_evolved_data_read_addresses == ()
    assert witness.observed_value == _LINEAGE_FETCH_VALUE
    assert witness.origin_value == _LINEAGE_FETCH_VALUE
    assert witness.origin_kind == _WORKLIST_WRITER_DATA_WRITE
    assert (
        witness.origin_entry_path_transition_index
        == _WORKLIST_EVOLVED_FETCH_ORIGIN_TRANSITION
    )
    assert witness.entry_path[-1] == witness.state
    _assert_evolved_fetch_control_source_map(report)
    assert not worklist.truncated


def test_worklist_report_witnesses_evolved_data_read() -> None:
    """Public worklist report exposes the first changed semantic data read."""
    report = _ANALYZER_MODULE.analyze_source(
        _DATA_LINEAGE_WRITE_SOURCE,
        worklist_state_limit=_DATA_LINEAGE_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    witness = worklist.explored_evolved_data_read_witness
    assert witness is not None
    assert witness.address == _DATA_LINEAGE_ADDRESS
    assert witness.initial_value == _DATA_LINEAGE_INITIAL_VALUE
    _assert_evolved_data_read_partition(worklist)
    assert worklist.explored_evolved_fetch_transition_count == 0
    assert worklist.explored_evolved_fetch_addresses == ()
    assert worklist.explored_evolved_data_read_transition_count == 1
    assert worklist.explored_evolved_data_read_addresses == (
        _DATA_LINEAGE_ADDRESS,
    )
    data_domain = worklist.explored_evolved_data_read_value_domains[0]
    assert data_domain.address == _DATA_LINEAGE_ADDRESS
    assert data_domain.values == (_DATA_LINEAGE_VALUE,)
    assert witness.observed_value == _DATA_LINEAGE_VALUE
    assert witness.origin_value == _DATA_LINEAGE_VALUE
    assert witness.origin_kind == _WORKLIST_WRITER_DATA_WRITE
    assert (
        witness.origin_entry_path_transition_index
        == _DATA_LINEAGE_ORIGIN_TRANSITION
    )
    assert witness.entry_path[-1] == witness.state
    _assert_evolved_data_control_source_map(report)
    assert not worklist.truncated


def _assert_source_access(
    context: _BoundedMemoryAccessSourceContext,
    expected: tuple[int, str, int, int, int],
) -> None:
    assert (
        context.transition_index,
        context.access_kind,
        context.address,
        context.source_position,
        context.source_byte_offset,
        context.initial_source_byte,
    ) == (*expected[:4], expected[3], expected[4])


def test_memory_access_map_unmaps_recurrence_encryption() -> None:
    """Recurrence encryption receives no invented source context."""
    report = _ANALYZER_MODULE.analyze_source(b"b'")
    fetch, data_read, encryption = report.bounded_memory_access_source_map
    _assert_source_access(
        fetch,
        (1, _ACCESS_FETCH, 0, 0, ord("b")),
    )
    _assert_source_access(
        data_read,
        (1, _ACCESS_DATA_READ, 0, 0, ord("b")),
    )
    assert encryption.transition_index == 1
    assert encryption.access_kind == _ACCESS_ENCRYPTION
    assert encryption.address == _JUMP_ENTRY_ADDRESS
    assert encryption.source_position is None
    assert encryption.source_byte_offset is None
    assert encryption.initial_source_byte is None


def test_bounded_memory_access_map_tracks_source_write_roles() -> None:
    """A rotate maps read, write, and encryption to source byte one."""
    source = bytes((
        _source_byte_for_decode(ord("<"), 0),
        _source_byte_for_decode(ord("*"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    second_contexts = tuple(
        context
        for context in report.bounded_memory_access_source_map
        if context.transition_index == _SECOND_TRANSITION_INDEX
    )
    assert tuple(context.access_kind for context in second_contexts) == (
        _ACCESS_FETCH,
        _ACCESS_DATA_READ,
        _ACCESS_DATA_WRITE,
        _ACCESS_ENCRYPTION,
    )
    for context in second_contexts:
        assert context.address == 1
        assert context.source_position == 1
        assert context.source_byte_offset == 1
        assert context.initial_source_byte == source[1]


def test_bounded_memory_requirement_tracks_exact_fixture_accesses() -> None:
    """Known fixture needs only its three loaded/fetched prefix words."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.scope == _MEMORY_SCOPE
    assert memory.minimum_words == _FIXTURE_SOURCE_WORDS
    assert memory.highest_accessed_address == _SECOND_SUCCESSOR
    assert memory.accessed_addresses == (0, 1, 2)


def test_bounded_memory_includes_recurrence_encryption_target() -> None:
    """Entry jump encryption proves the recurrence footprint through M[98]."""
    report = _ANALYZER_MODULE.analyze_source(b"b'")
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.minimum_words == _JUMP_ENTRY_ADDRESS + 1
    assert memory.highest_accessed_address == _JUMP_ENTRY_ADDRESS
    assert memory.accessed_addresses == (0, _JUMP_ENTRY_ADDRESS)


def test_bounded_memory_excludes_unread_stuck_data_pointer() -> None:
    """A non-graphical fetch does not read D before historical continue."""
    report = _ANALYZER_MODULE.analyze_source(_THIRD_STUCK_SOURCE)
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.minimum_words == _THIRD_PREFIX_WORDS
    assert memory.highest_accessed_address == _SECOND_SUCCESSOR
    assert _THIRD_STUCK_DATA_ADDRESS not in memory.accessed_addresses
    assert memory.accessed_addresses == (0, 1, 2)


def test_bounded_memory_includes_recurrence_data_read() -> None:
    """A reachable second j includes its recurrence-backed D read."""
    report = _ANALYZER_MODULE.analyze_source(b"('")
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.minimum_words == _RECUR_DATA_WORDS
    assert memory.highest_accessed_address == _RECUR_DATA_ADDRESS
    assert memory.accessed_addresses == (0, 1, 2, _RECUR_DATA_ADDRESS)


def test_rejected_initial_decode_has_no_bounded_memory_claim() -> None:
    """No dynamic memory footprint is claimed before load admission succeeds."""
    report = _ANALYZER_MODULE.analyze_source(bytes((33, 38)))
    assert not report.admitted_initial_image
    assert report.entry_transition is None
    assert report.bounded_memory_requirement is None


def test_report_profile_capacity_matches_canonical_authority() -> None:
    """Historical capacity agrees with validated `malbolge.json`."""
    canonical = target_profile.load_document(target_profile.DEFAULT_PROFILE)
    geometry = target_profile.profile_geometry(canonical, _PROFILE_ID)
    profiles = cast("dict[str, object]", canonical["profiles"])
    historical = cast("dict[str, object]", profiles[_PROFILE_ID])
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_id == geometry.profile_id
    assert report.profile_version == historical["version"]
    assert report.profile_memory_words == geometry.memory_words


def test_exact_c_locale_whitespace_does_not_consume_source_words() -> None:
    """All six specified whitespace bytes preserve loaded positions."""
    source = bytes((39, 9, 10, 11, 12, 13, 32, 38))
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    assert report.required_source_words == _TWO_SOURCE_WORDS
    assert [cell.position for cell in report.initial_cells] == [0, 1]
    assert [cell.byte_offset for cell in report.initial_cells] == [0, 7]
    assert [cell.decoded_byte for cell in report.initial_cells] == [42, 42]


def test_non_graphical_source_byte_is_reported_with_offset() -> None:
    """A non-whitespace non-graphical byte fails lexical image admission."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39, 0, 38)))
    assert not report.admitted_initial_image
    assert report.required_source_words == _FIXTURE_SOURCE_WORDS
    assert report.initial_cells == ()
    finding = report.findings[0]
    assert finding.code == _LEXICAL_CODE
    assert finding.byte_offset == 1
    assert finding.source_byte == 0


def test_recurrence_underflow_is_reported_without_guest_execution() -> None:
    """One loaded word cannot supply the recurrence base."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39,)))
    assert not report.admitted_initial_image
    codes = [finding.code for finding in report.findings]
    assert codes == ["MALBOLGE-STATIC-002"]


def test_exact_historical_capacity_can_be_fully_admitted() -> None:
    """The 59,049-word historical ceiling is inclusive for valid source."""
    target_decode = ord("o")
    target_index = _TEST_XLAT1.index(target_decode)
    source = bytes(
        ((target_index - position) % _DECODE_PERIOD) + _GRAPHICAL_START
        for position in range(_PROFILE_MEMORY_WORDS)
    )
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    assert report.required_source_words == _PROFILE_MEMORY_WORDS
    assert len(report.initial_cells) == _PROFILE_MEMORY_WORDS
    assert report.findings == ()
    assert all(
        cell.decoded_byte == target_decode for cell in report.initial_cells
    )


def test_profile_capacity_prevents_initial_decode_of_oversized_source() -> None:
    """An oversized graphical source reports historical capacity explicitly."""
    report = _ANALYZER_MODULE.analyze_source(b"!" * _OVERSIZED_SOURCE_WORDS)
    assert not report.admitted_initial_image
    assert report.required_source_words == _OVERSIZED_SOURCE_WORDS
    assert report.initial_cells == ()
    codes = [finding.code for finding in report.findings]
    assert codes == ["MALBOLGE-STATIC-003"]


def test_every_graphical_byte_and_phase_matches_independent_decode() -> None:
    """All 8,836 initial decode pairs match the independent historical table."""
    assert len(_TEST_XLAT1) == _DECODE_PERIOD
    filler = bytes((_GRAPHICAL_START,))
    for position in range(_DECODE_PERIOD):
        prefix = filler * position
        for source_byte in range(_GRAPHICAL_START, _GRAPHICAL_END + 1):
            source = prefix + bytes((source_byte,))
            if len(source) < _TWO_SOURCE_WORDS:
                source += filler
            report = _ANALYZER_MODULE.analyze_source(source)
            cell = report.initial_cells[position]
            expected_index = (
                source_byte - _GRAPHICAL_START + position
            ) % _DECODE_PERIOD
            expected_decode = _TEST_XLAT1[expected_index]
            assert cell.source_byte == source_byte
            assert cell.decoded_byte == expected_decode
            rejected_positions = {
                finding.loaded_position
                for finding in report.findings
                if finding.code == _DECODE_CODE
            }
            assert (position in rejected_positions) == (
                expected_decode not in _TEST_ALLOWED_INSTRUCTIONS
            )


def test_graphical_but_forbidden_initial_decode_reports_position() -> None:
    """Graphical source can still fail positional decode."""
    report = _ANALYZER_MODULE.analyze_source(bytes((33, 38)))
    assert not report.admitted_initial_image
    assert len(report.initial_cells) == _TWO_SOURCE_WORDS
    finding = report.findings[0]
    assert finding.code == _DECODE_CODE
    assert finding.byte_offset == 0
    assert finding.loaded_position == 0
    assert finding.source_byte == _GRAPHICAL_INVALID_BYTE
    assert finding.decoded_byte == _FORBIDDEN_DECODE_BYTE


def test_initial_cells_classify_self_modification_target() -> None:
    """Classify encryption target shape without a reachability claim."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_HALT in interpreter
    assert _HISTORICAL_JUMP_CODE_ASSIGNMENT in interpreter
    assert _HISTORICAL_ENCRYPTION in interpreter
    expected = {
        ord("i"): ("post-jump-code-pointer", False),
        ord("v"): ("none", False),
        ord("*"): ("current-code-pointer", True),
        ord("p"): ("current-code-pointer", True),
        ord("j"): ("current-code-pointer", False),
        ord("<"): ("current-code-pointer", False),
        ord("/"): ("current-code-pointer", False),
        ord("o"): ("current-code-pointer", False),
    }
    for decoded_byte, classification in expected.items():
        index = _TEST_XLAT1.index(decoded_byte)
        first = index + _GRAPHICAL_START
        second_index = _TEST_XLAT1.index(ord("o"))
        second = ((second_index - 1) % _DECODE_PERIOD) + _GRAPHICAL_START
        report = _ANALYZER_MODULE.analyze_source(bytes((first, second)))
        cell = report.initial_cells[0]
        assert cell.decoded_byte == decoded_byte
        assert (
            cell.post_step_encryption_target,
            cell.data_alias_can_change_encryption_input,
        ) == classification


def test_entry_transition_resolves_known_fixture() -> None:
    """Resolve the exact first transition without executing a guest loop."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    transition = report.entry_transition
    assert transition is not None
    assert transition.status == _ENTRY_CONTINUED
    assert transition.fetched_address == 0
    assert transition.decoded_byte == ord("<")
    assert transition.data_address == 0
    assert transition.code_data_alias
    assert transition.encryption_address == 0
    assert transition.encryption_input == _FIXTURE_ENCRYPTION_INPUT
    assert (
        transition.encryption_output
        == _TEST_XLAT2[_FIXTURE_ENCRYPTION_INPUT - 33]
    )
    assert transition.result_accumulator == 0
    assert transition.result_code_pointer == 1
    assert transition.result_data_pointer == 1
    assert transition.next_fetch_address == 1
    assert not transition.pointer_wraps


def test_entry_rotate_alias_detects_invalid_self_encryption() -> None:
    """Resolve the entry C/D alias before historical xlat2 table access."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_ROTATE in interpreter
    report = _ANALYZER_MODULE.analyze_source(bytes((39, 38)))
    assert report.admitted_initial_image
    transition = report.entry_transition
    assert transition is not None
    assert transition.decoded_byte == ord("*")
    assert transition.status == _ENTRY_INVALID_ENCRYPTION
    assert transition.planned_data_write_address == 0
    assert transition.planned_data_write_value == _ROTATED_ENTRY_VALUE
    assert transition.data_write_aliases_encryption
    assert transition.encryption_address == 0
    assert transition.encryption_input == _ROTATED_ENTRY_VALUE
    assert transition.encryption_output is None
    assert transition.result_accumulator == 0
    assert transition.result_code_pointer == 0
    assert transition.result_data_pointer == 0
    assert transition.next_fetch_address is None


def test_entry_jump_resolves_initial_recurrence_encryption_target() -> None:
    """Resolve one post-jump encryption target through initial recurrence."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_RECURRENCE in interpreter
    assert _HISTORICAL_JUMP_CODE_ASSIGNMENT in interpreter
    report = _ANALYZER_MODULE.analyze_source(b"b'")
    assert report.admitted_initial_image
    transition = report.entry_transition
    assert transition is not None
    assert transition.decoded_byte == ord("i")
    assert transition.status == _ENTRY_INVALID_ENCRYPTION
    assert transition.encryption_address == _JUMP_ENTRY_ADDRESS
    assert transition.encryption_input == _JUMP_ENTRY_ENCRYPTION_INPUT
    assert transition.encryption_output is None
    assert transition.result_code_pointer == 0
    assert transition.result_data_pointer == 0
    assert transition.next_fetch_address is None


def test_encryption_input_lineage_tracks_memory_and_alias_write() -> None:
    """Encryption input observes memory after same-step data writes."""
    loaded = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    loaded_lineage = loaded.bounded_encryption_input_value_lineage[0]
    assert loaded_lineage.transition_index == 1
    assert loaded_lineage.encryption_address == 0
    assert loaded_lineage.encryption_input == _FIXTURE_ENCRYPTION_INPUT
    assert loaded_lineage.origin_kind == _ORIGIN_LOADED_SOURCE
    assert loaded_lineage.origin_transition_index is None

    recurrence = _ANALYZER_MODULE.analyze_source(b"b'")
    recurrence_lineage = recurrence.bounded_encryption_input_value_lineage[0]
    assert recurrence_lineage.encryption_address == _JUMP_ENTRY_ADDRESS
    assert recurrence_lineage.encryption_input == _JUMP_ENTRY_ENCRYPTION_INPUT
    assert recurrence_lineage.origin_kind == _ORIGIN_RECURRENCE
    assert recurrence_lineage.origin_transition_index is None

    alias = _ANALYZER_MODULE.analyze_source(bytes((39, 38)))
    alias_lineage = alias.bounded_encryption_input_value_lineage[0]
    assert alias_lineage.encryption_address == 0
    assert alias_lineage.encryption_input == _ROTATED_ENTRY_VALUE
    assert alias_lineage.origin_kind == _ACCESS_DATA_WRITE
    assert alias_lineage.origin_transition_index == 1


def test_entry_halt_skips_encryption_and_pointer_advance() -> None:
    """Halt is an exact terminal entry transition with unchanged registers."""
    report = _ANALYZER_MODULE.analyze_source(bytes((81, 80)))
    assert report.admitted_initial_image
    transition = report.entry_transition
    assert transition is not None
    assert transition.decoded_byte == ord("v")
    assert transition.status == _ENTRY_HALTED
    assert transition.encryption_address is None
    assert transition.encryption_input is None
    assert transition.result_accumulator == 0
    assert transition.result_code_pointer == 0
    assert transition.result_data_pointer == 0
    assert transition.next_fetch_address is None


def test_entry_input_marks_only_accumulator_as_input_dependent() -> None:
    """Unknown first input does not make entry pointer flow unknown."""
    report = _ANALYZER_MODULE.analyze_source(bytes((117, 116)))
    assert report.admitted_initial_image
    transition = report.entry_transition
    assert transition is not None
    assert transition.decoded_byte == ord("/")
    assert transition.status == _ENTRY_CONTINUED
    assert transition.input_dependent_accumulator
    assert transition.result_accumulator is None
    assert transition.result_code_pointer == 1
    assert transition.result_data_pointer == 1
    assert transition.next_fetch_address == 1


def test_second_transition_resolves_known_fixture() -> None:
    """Resolve the fixture's reachable input step without consuming input."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    transition = report.second_transition
    assert transition is not None
    assert transition.status == _ENTRY_CONTINUED
    assert transition.fetched_address == 1
    assert transition.fetched_value == _FIXTURE_SECOND_VALUE
    assert transition.decoded_byte == ord("/")
    assert transition.data_address == 1
    assert transition.data_value == _FIXTURE_SECOND_VALUE
    assert transition.code_data_alias
    assert transition.encryption_address == 1
    assert transition.encryption_input == _FIXTURE_SECOND_VALUE
    expected_encryption = _TEST_XLAT2[
        _FIXTURE_SECOND_VALUE - _GRAPHICAL_START
    ]
    assert transition.encryption_output == expected_encryption
    assert transition.input_dependent_accumulator
    assert transition.result_accumulator is None
    assert transition.result_code_pointer == _SECOND_SUCCESSOR
    assert transition.result_data_pointer == _SECOND_SUCCESSOR
    assert transition.next_fetch_address == _SECOND_SUCCESSOR
    assert transition.accepted


def _assert_third_fixed_fetch_cycle(transition: _SecondTransition) -> None:
    assert transition.status == _THIRD_STUCK
    assert transition.fetched_address == _SECOND_SUCCESSOR
    assert transition.fetched_value == _THIRD_STUCK_VALUE
    assert transition.decoded_byte is None
    assert transition.data_address == _THIRD_STUCK_DATA_ADDRESS
    assert transition.data_value is None
    assert not transition.code_data_alias
    assert transition.encryption_address is None
    assert transition.encryption_input is None
    assert transition.encryption_output is None
    assert transition.result_code_pointer == _SECOND_SUCCESSOR
    assert transition.result_data_pointer == _THIRD_STUCK_DATA_ADDRESS
    assert transition.next_fetch_address == _SECOND_SUCCESSOR
    assert not transition.input_dependent_accumulator
    assert transition.provable_cycle
    assert not transition.accepted


def test_third_transition_proves_fixed_fetch_cycle() -> None:
    """A non-graphical third fetch cannot advance in the 1998 interpreter."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_NON_GRAPHICAL_CONTINUE in interpreter
    report = _ANALYZER_MODULE.analyze_source(_THIRD_STUCK_SOURCE)
    assert report.admitted_initial_image
    entry = report.entry_transition
    assert entry is not None
    assert entry.accepted
    second = report.second_transition
    assert second is not None
    assert second.accepted
    transition = report.third_transition
    assert transition is not None
    _assert_third_fixed_fetch_cycle(transition)


def _assert_fourth_fixed_fetch_cycle(
    transition: _SecondTransition,
    expected_fetch: int,
) -> None:
    assert transition.status == _THIRD_STUCK
    assert transition.fetched_address == _FOURTH_FETCH_ADDRESS
    assert transition.fetched_value == expected_fetch
    assert transition.decoded_byte is None
    assert transition.data_address == _FOURTH_DATA_ADDRESS
    assert transition.data_value is None
    assert transition.result_code_pointer == _FOURTH_FETCH_ADDRESS
    assert transition.result_data_pointer == _FOURTH_DATA_ADDRESS
    assert transition.next_fetch_address == _FOURTH_FETCH_ADDRESS
    assert transition.provable_cycle
    assert not transition.accepted


def _assert_fourth_memory(memory: _BoundedMemoryRequirement) -> None:
    assert memory.scope == _MEMORY_SCOPE
    assert memory.minimum_words == _FOURTH_MEMORY_WORDS
    assert memory.highest_accessed_address == _FOURTH_HIGHEST_ADDRESS
    assert memory.accessed_addresses == _FOURTH_ACCESSES


def test_fourth_transition_proves_recurrence_fixed_fetch_cycle() -> None:
    """Fourth-step recurrence fetch is exact after three committed steps."""
    report = _ANALYZER_MODULE.analyze_source(_FOURTH_STUCK_SOURCE)
    assert report.admitted_initial_image
    third = report.third_transition
    assert third is not None
    assert third.status == _ENTRY_CONTINUED
    assert third.next_fetch_address == _FOURTH_FETCH_ADDRESS
    transition = report.fourth_transition
    assert transition is not None
    expected_fetch = _historical_c_op(
        _FOURTH_STUCK_SOURCE[2],
        _FOURTH_STUCK_SOURCE[1],
    )
    _assert_fourth_fixed_fetch_cycle(transition, expected_fetch)
    memory = report.bounded_memory_requirement
    assert memory is not None
    _assert_fourth_memory(memory)


def _assert_fifth_fixed_fetch_cycle(
    transition: _SecondTransition,
    expected_fetch: int,
) -> None:
    assert transition.status == _THIRD_STUCK
    assert transition.fetched_address == _FIFTH_FETCH_ADDRESS
    assert transition.fetched_value == expected_fetch
    assert transition.decoded_byte is None
    assert transition.data_address == _FIFTH_DATA_ADDRESS
    assert transition.next_fetch_address == _FIFTH_FETCH_ADDRESS
    assert transition.provable_cycle
    assert not transition.accepted


def _assert_fifth_memory(memory: _BoundedMemoryRequirement) -> None:
    assert memory.scope == _MEMORY_SCOPE
    assert memory.minimum_words == _FIFTH_MEMORY_WORDS
    assert memory.highest_accessed_address == _FIFTH_HIGHEST_ADDRESS
    assert memory.accessed_addresses == _FIFTH_ACCESSES


def test_next_transfer_resolves_fifth_fixed_fetch_cycle() -> None:
    """Public v8 fifth step matches the generic exact transfer."""
    report = _ANALYZER_MODULE.analyze_source(_FIFTH_TRANSFER_SOURCE)
    entry = report.entry_transition
    second = report.second_transition
    third = report.third_transition
    fourth = report.fourth_transition
    reported = report.fifth_transition
    assert entry is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert reported is not None
    assert fourth.status == _ENTRY_CONTINUED
    transition = _ANALYZER_MODULE.prefix_transfer.analyze_next_transition(
        tuple(_FIFTH_TRANSFER_SOURCE),
        entry,
        (second, third, fourth),
    )
    assert transition is not None
    assert reported == transition
    expected_fetch = _historical_c_op(
        _FIFTH_TRANSFER_SOURCE[3],
        _FIFTH_TRANSFER_SOURCE[2],
    )
    _assert_fifth_fixed_fetch_cycle(reported, expected_fetch)
    memory = report.bounded_memory_requirement
    assert memory is not None
    _assert_fifth_memory(memory)


def test_snapshot_transfer_replays_reported_evolved_state() -> None:
    """Public snapshot transfer reproduces the reported next transition."""
    source = _DATA_LINEAGE_WRITE_SOURCE
    report = _ANALYZER_MODULE.analyze_source(
        source,
        transition_limit=_DATA_LINEAGE_TRANSITION_LIMIT,
    )
    snapshot = report.bounded_state_snapshots[
        _DATA_LINEAGE_READ_TRANSITION - 1
    ]
    step = _ANALYZER_MODULE.prefix_transfer.analyze_state_snapshot(
        tuple(source),
        snapshot,
    )
    assert step.transition == report.fourth_transition
    successor = step.successor
    assert successor is not None
    assert successor == report.bounded_state_snapshots[
        _DATA_LINEAGE_READ_TRANSITION
    ]


def test_snapshot_transfer_rejects_noncanonical_memory() -> None:
    """Caller-supplied snapshots cannot retain redundant initial values."""
    source = _FIXTURE.read_bytes()
    report = _ANALYZER_MODULE.analyze_source(source)
    snapshot = copy(report.bounded_state_snapshots[0])
    object.__setattr__(  # ruff: ignore[unnecessary-dunder-call]
        snapshot,
        "memory_overrides",
        ((0, source[0]),),
    )
    with pytest.raises(AssertionError, match=_SNAPSHOT_CANONICAL_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_state_snapshot(
            tuple(source),
            snapshot,
        )


def test_next_transfer_rejects_forged_entry_transition() -> None:
    """Caller-supplied entry state must match exact recomputation."""
    source = _FIXTURE.read_bytes()
    report = _ANALYZER_MODULE.analyze_source(source)
    entry = report.entry_transition
    assert entry is not None
    forged = copy(entry)
    object.__setattr__(  # ruff: ignore[unnecessary-dunder-call]
        forged,
        "next_fetch_address",
        (entry.result_code_pointer + 1) % _PROFILE_MEMORY_WORDS,
    )
    words = tuple(source)
    with pytest.raises(AssertionError, match=_ENTRY_MISMATCH_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_next_transition(
            words,
            forged,
            (),
        )
    with pytest.raises(AssertionError, match=_ENTRY_MISMATCH_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_continuations(
            words,
            forged,
            maximum_transitions=1,
        )


def test_next_transfer_rejects_forged_entry_decode() -> None:
    """Entry replay derives decode from source rather than caller metadata."""
    source = _FIXTURE.read_bytes()
    words = tuple(source)
    report = _ANALYZER_MODULE.analyze_source(source)
    entry = report.entry_transition
    assert entry is not None
    alternate_decoded = (
        ord("o") if entry.decoded_byte != ord("o") else ord("<")
    )
    assert alternate_decoded != entry.decoded_byte
    forged = _ANALYZER_MODULE.entry_transfer.analyze_entry_transition(
        words,
        alternate_decoded,
    )
    assert forged.decoded_byte == alternate_decoded
    with pytest.raises(AssertionError, match=_ENTRY_MISMATCH_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_next_transition(
            words,
            forged,
            (),
        )
    with pytest.raises(AssertionError, match=_ENTRY_MISMATCH_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_continuations(
            words,
            forged,
            maximum_transitions=1,
        )


def test_next_transfer_rejects_missing_recurrence_base() -> None:
    """Explicit replay rejects empty and one-word recurrence bases."""
    source = _FIXTURE.read_bytes()
    report = _ANALYZER_MODULE.analyze_source(source)
    entry = report.entry_transition
    assert entry is not None
    for words in ((), (source[0],)):
        with pytest.raises(AssertionError, match=_PREFIX_SOURCE_MESSAGE):
            _ = _ANALYZER_MODULE.prefix_transfer.analyze_next_transition(
                words,
                entry,
                (),
            )
        with pytest.raises(AssertionError, match=_PREFIX_SOURCE_MESSAGE):
            _ = _ANALYZER_MODULE.prefix_transfer.analyze_continuations(
                words,
                entry,
                maximum_transitions=1,
            )


def test_next_transfer_rejects_noncontiguous_explicit_prefix() -> None:
    """Caller-supplied bounded prefix records must be exact and contiguous."""
    report = _ANALYZER_MODULE.analyze_source(_FIFTH_TRANSFER_SOURCE)
    entry = report.entry_transition
    third = report.third_transition
    assert entry is not None
    assert third is not None
    with pytest.raises(AssertionError, match=_PREFIX_MISMATCH_MESSAGE):
        _ = _ANALYZER_MODULE.prefix_transfer.analyze_next_transition(
            tuple(_FIFTH_TRANSFER_SOURCE),
            entry,
            (third,),
        )


def test_second_transition_rejects_reachable_rotate_alias() -> None:
    """A valid initial image can fail exact self-encryption on step two."""
    source = bytes((
        _source_byte_for_decode(ord("<"), 0),
        _source_byte_for_decode(ord("*"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    entry = report.entry_transition
    assert entry is not None
    assert entry.accepted
    transition = report.second_transition
    assert transition is not None
    assert transition.decoded_byte == ord("*")
    assert transition.status == _ENTRY_INVALID_ENCRYPTION
    assert transition.planned_data_write_address == 1
    assert transition.data_write_aliases_encryption
    expected = source[1] // 3 + source[1] % 3 * 19_683
    assert transition.planned_data_write_value == expected
    assert transition.encryption_input == expected
    assert transition.encryption_output is None
    assert not transition.accepted


def test_second_transition_keeps_input_dependent_crazy_unresolved() -> None:
    """Unknown input accumulator never gets guessed for reachable crazy."""
    source = bytes((
        _source_byte_for_decode(ord("/"), 0),
        _source_byte_for_decode(ord("p"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    transition = report.second_transition
    assert transition is not None
    assert transition.decoded_byte == ord("p")
    assert transition.status == _SECOND_INPUT_UNRESOLVED
    assert transition.input_dependent_accumulator
    assert transition.result_accumulator is None
    assert transition.result_code_pointer is None
    assert transition.result_data_pointer is None
    assert transition.next_fetch_address is None
    assert not transition.accepted


def test_second_transition_preserves_input_dependency_through_noop() -> None:
    """Keep an input-dependent accumulator unknown through an exact no-op."""
    source = bytes((
        _source_byte_for_decode(ord("/"), 0),
        _source_byte_for_decode(ord("o"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    transition = report.second_transition
    assert transition is not None
    assert transition.decoded_byte == ord("o")
    assert transition.status == _ENTRY_CONTINUED
    assert transition.input_dependent_accumulator
    assert transition.result_accumulator is None
    assert transition.result_code_pointer == _SECOND_SUCCESSOR
    assert transition.result_data_pointer == _SECOND_SUCCESSOR
    assert transition.accepted


def test_second_transition_halt_is_exact_terminal_state() -> None:
    """A reachable second-step halt needs no later transition proof."""
    source = bytes((
        _source_byte_for_decode(ord("<"), 0),
        _source_byte_for_decode(ord("v"), 1),
    ))
    report = _ANALYZER_MODULE.analyze_source(source)
    transition = report.second_transition
    assert transition is not None
    assert transition.status == _ENTRY_HALTED
    assert transition.decoded_byte == ord("v")
    assert transition.result_code_pointer == 1
    assert transition.result_data_pointer == 1
    assert transition.next_fetch_address is None
    assert transition.accepted


def _sequential_output_source(words: int) -> bytes:
    return bytes(
        _source_byte_for_decode(ord("<"), position)
        for position in range(words)
    )


def test_report_reaches_exact_sixteen_transition_bound() -> None:
    """Sequential output cells exercise the complete reviewed trace bound."""
    source = _sequential_output_source(_TOTAL_TRANSITION_LIMIT)
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    assert report.bounded_transition_limit == _TOTAL_TRANSITION_LIMIT
    assert len(report.bounded_continuations) == _CONTINUATION_LIMIT
    assert report.bounded_exact_cycle is None
    assert report.second_transition == report.bounded_continuations[0]
    assert report.third_transition == report.bounded_continuations[1]
    assert report.fourth_transition == report.bounded_continuations[2]
    assert report.fifth_transition == report.bounded_continuations[3]
    assert all(item.accepted for item in report.bounded_continuations)
    last = report.bounded_continuations[-1]
    assert last.fetched_address == _TOTAL_TRANSITION_LIMIT - 1
    assert last.next_fetch_address == _TOTAL_TRANSITION_LIMIT
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.scope == _MEMORY_SCOPE
    assert memory.minimum_words == _TOTAL_TRANSITION_LIMIT
    assert memory.accessed_addresses == tuple(range(_TOTAL_TRANSITION_LIMIT))
    assert len(report.bounded_fetch_source_map) == _TOTAL_TRANSITION_LIMIT
    assert all(
        context.fetched_value_matches_initial_source is True
        for context in report.bounded_fetch_source_map
    )
    assert len(report.bounded_memory_access_source_map) == (
        _TOTAL_TRANSITION_LIMIT * 2
    )


def test_exact_cycle_certificate_causes_cli_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A proven repeated state makes the bounded CLI result nonzero."""
    payload = _sequential_output_source(_TWO_SOURCE_WORDS)
    source_path = tmp_path / "exact-cycle.malbolge"
    _ = source_path.write_bytes(payload)
    report = _ANALYZER_MODULE.analyze_source(
        payload,
        transition_limit=_TWO_SOURCE_WORDS,
    )
    cycle = cast(
        "_ExactCycleCertificate",
        cast("object", {"period_transitions": 1}),
    )
    cycled = copy(report)
    # Mutate only the isolated copy of the frozen production report.
    object.__setattr__(  # ruff: ignore[unnecessary-dunder-call]
        cycled,
        "bounded_exact_cycle",
        cycle,
    )

    def analyze_cycle(
        source: bytes,
        *,
        transition_limit: int = _TOTAL_TRANSITION_LIMIT,
        worklist_state_limit: int | None = None,
    ) -> _Report:
        assert source == payload
        assert transition_limit == _TWO_SOURCE_WORDS
        assert worklist_state_limit is None
        return cycled

    monkeypatch.setattr(_ANALYZER_MODULE, "analyze_source", analyze_cycle)
    result = _ANALYZER_MODULE.main(
        ["--transition-limit", str(_TWO_SOURCE_WORDS), str(source_path)]
    )
    assert result == 1
    document = cast(
        "dict[str, object]",
        json.loads(capsys.readouterr().out),
    )
    assert document["bounded_exact_cycle"] == {"period_transitions": 1}


def _assert_closed_recurrent_cycle_json(
    bounded: dict[str, object],
) -> None:
    assert (
        bounded["closed_recurrent_component_count"]
        == _WORKLIST_INPUT_VALUE_COUNT
    )
    assert (
        bounded["closed_recurrent_state_count"]
        == _WORKLIST_INPUT_VALUE_COUNT
    )
    assert bounded["closed_recurrent_largest_component_states"] == 1
    recurrent = cast(
        "list[dict[str, object]]",
        bounded["closed_recurrent_cycle_witness"],
    )
    assert len(recurrent) == 1
    assert recurrent[0]["code_pointer"] == _FIXED_CYCLE_POINTER
    assert recurrent[0]["data_pointer"] == _FIXED_CYCLE_POINTER
    path = cast(
        "list[dict[str, object]]",
        bounded["closed_recurrent_entry_path"],
    )
    assert [state["code_pointer"] for state in path] == [0, 1, 2]
    assert path[-1] == recurrent[0]
    assert bounded["closed_all_paths_terminate"] is False
    assert bounded["closed_all_paths_halt"] is False


def _assert_reachable_cycle_entry_path_json(
    bounded: dict[str, object],
    cycle: dict[str, object],
) -> None:
    entry_path = cast(
        "list[dict[str, object]]",
        bounded["reachable_cycle_entry_path"],
    )
    assert [state["code_pointer"] for state in entry_path] == [0, 1, 2]
    assert [state["data_pointer"] for state in entry_path] == [0, 1, 2]
    assert entry_path[-1] == cycle


def test_worklist_cycle_detection_causes_cli_failure(tmp_path: Path) -> None:
    """A cycle beyond the prefix bound still makes requested CLI nonzero."""
    source_path = tmp_path / "worklist-cycle.malbolge"
    _ = source_path.write_bytes(_DOUBLE_INPUT_CYCLE_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--transition-limit",
            str(_TWO_SOURCE_WORDS),
            "--worklist-state-limit",
            str(_DOUBLE_INPUT_CYCLE_STATE_LIMIT),
            str(source_path),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["bounded_transition_limit"] == _TWO_SOURCE_WORDS
    bounded = cast("dict[str, object]", document["bounded_worklist"])
    assert bounded["reachable_cycle_detected"] is True
    witness = cast(
        "list[dict[str, object]]",
        bounded["reachable_cycle_witness"],
    )
    assert len(witness) == 1
    assert witness[0]["code_pointer"] == _FIXED_CYCLE_POINTER
    assert witness[0]["data_pointer"] == _FIXED_CYCLE_POINTER
    assert witness[0]["accumulator"] == 0
    assert witness[0]["memory_overrides"] == [
        [0, _FIXED_CYCLE_ENCRYPTED_ZERO],
        [1, _FIXED_CYCLE_ENCRYPTED_ONE],
    ]
    assert witness[0]["eof_seen"] is False
    _assert_reachable_cycle_entry_path_json(bounded, witness[0])
    assert (
        bounded["known_graph_strong_component_count"]
        == _DOUBLE_INPUT_CYCLE_STATE_LIMIT
    )
    assert (
        bounded["known_graph_cyclic_component_count"]
        == _WORKLIST_INPUT_VALUE_COUNT
    )
    assert (
        bounded["known_graph_cyclic_state_count"]
        == _WORKLIST_INPUT_VALUE_COUNT
    )
    assert bounded["known_graph_largest_cyclic_component_states"] == 1
    _assert_closed_recurrent_cycle_json(bounded)
    assert bounded["truncated"] is False


def test_report_reaches_requested_transition_beyond_default_bound() -> None:
    """Prove transition 17 and later under one explicit finite depth."""
    source = _sequential_output_source(_EXTENDED_TRANSITION_LIMIT)
    report = _ANALYZER_MODULE.analyze_source(
        source,
        transition_limit=_EXTENDED_TRANSITION_LIMIT,
    )
    assert report.admitted_initial_image
    assert report.bounded_transition_limit == _EXTENDED_TRANSITION_LIMIT
    assert len(report.bounded_continuations) == _EXTENDED_TRANSITION_LIMIT - 1
    last = report.bounded_continuations[-1]
    assert last.fetched_address == _EXTENDED_TRANSITION_LIMIT - 1
    assert last.next_fetch_address == _EXTENDED_TRANSITION_LIMIT
    memory = report.bounded_memory_requirement
    assert memory is not None
    assert memory.scope == f"{_EXTENDED_TRANSITION_LIMIT}-transition-prefix"
    assert memory.accessed_addresses == tuple(range(_EXTENDED_TRANSITION_LIMIT))
    assert len(report.bounded_fetch_source_map) == _EXTENDED_TRANSITION_LIMIT
    assert report.analysis_limits[1] == _EXTENDED_CONTROL_FLOW_LIMIT


def test_report_accepts_reviewed_maximum_transition_limit() -> None:
    """The explicit safety ceiling itself remains a valid finite proof depth."""
    source = _sequential_output_source(_MAX_TOTAL_TRANSITION_LIMIT)
    report = _ANALYZER_MODULE.analyze_source(
        source,
        transition_limit=_MAX_TOTAL_TRANSITION_LIMIT,
    )
    assert report.bounded_transition_limit == _MAX_TOTAL_TRANSITION_LIMIT
    assert len(report.bounded_continuations) == _MAX_TOTAL_TRANSITION_LIMIT - 1
    last = report.bounded_continuations[-1]
    assert last.fetched_address == _MAX_TOTAL_TRANSITION_LIMIT - 1
    assert last.next_fetch_address == _MAX_TOTAL_TRANSITION_LIMIT


def _assert_terminal_witness_object(worklist: _WorklistAnalysis) -> None:
    assert len(worklist.terminal_status_witnesses) == 1
    witness = worklist.terminal_status_witnesses[0]
    assert witness.status == _ENTRY_INVALID_ENCRYPTION
    assert (witness.state.code_pointer, witness.state.data_pointer) == (1, 1)
    assert witness.state.accumulator == 0
    assert witness.entry_path[-1] == witness.state


def _assert_no_data_write_noop_evidence(worklist: _WorklistAnalysis) -> None:
    assert worklist.explored_committed_data_write_noop_transition_count == 0
    assert worklist.explored_committed_data_write_noop_addresses == ()
    assert worklist.explored_data_write_noop_witness is None


def _assert_input_crazy_alias_evidence(worklist: _WorklistAnalysis) -> None:
    assert worklist.explored_code_data_alias_transition_count == (
        _WORKLIST_COMPLETE_STATE_LIMIT
    )
    assert worklist.explored_code_data_alias_addresses == (0, 1)
    witnesses = worklist.explored_code_data_alias_witnesses
    assert tuple(witness.address for witness in witnesses) == (0, 1)
    assert witnesses[0].memory_value == _INPUT_CRAZY_SOURCE[0]
    assert witnesses[1].memory_value == _INPUT_CRAZY_SOURCE[1]


def _assert_worklist_mutation_evidence(worklist: _WorklistAnalysis) -> None:
    _assert_input_crazy_alias_evidence(worklist)
    assert worklist.explored_committed_write_count == 1
    assert worklist.explored_committed_write_addresses == (0,)
    assert worklist.explored_planned_data_write_transition_count == (
        _WORKLIST_INPUT_VALUE_COUNT
    )
    assert worklist.explored_planned_data_write_addresses == (1,)
    planned_domain = worklist.explored_planned_data_write_value_domains[0]
    assert len(planned_domain.values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert worklist.explored_committed_data_write_transition_count == 0
    assert worklist.explored_committed_data_write_addresses == ()
    _assert_no_data_write_noop_evidence(worklist)
    assert worklist.explored_self_encryption_transition_count == 1
    assert worklist.explored_self_encryption_addresses == (0,)
    assert worklist.explored_effective_data_mutation_transition_count == 0
    assert worklist.explored_effective_data_mutation_addresses == ()
    assert worklist.explored_effective_data_mutation_value_domains == ()
    fetch_addresses = tuple(
        domain.address for domain in worklist.explored_fetch_value_domains
    )
    assert fetch_addresses == (0, 1)
    assert worklist.explored_data_read_value_domains[0].values == (61,)
    encryption_domain = worklist.explored_encryption_input_value_domains[1]
    encryption_values = encryption_domain.values
    assert len(encryption_values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert worklist.explored_committed_data_write_value_domains == ()
    assert worklist.explored_self_encryption_output_value_domains[0].values == (
        111,
    )
    assert worklist.explored_data_mutation_witness is None


def test_worklist_maps_changed_encryption_inputs_without_commit_claim() -> None:
    """Rejected changed encryption inputs remain value-only bounded evidence."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _INPUT_CRAZY_SOURCE,
        worklist_state_limit=_WORKLIST_COMPLETE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert (
        worklist.explored_encryption_input_transition_count
        == _INPUT_CRAZY_ENCRYPTION_INPUT_COUNT
    )
    assert (
        worklist.explored_initial_value_encryption_input_transition_count
        == _INPUT_CRAZY_INITIAL_ENCRYPTION_INPUT_COUNT
    )
    assert (
        worklist.explored_changed_from_initial_encryption_input_transition_count
        == _INPUT_CRAZY_CHANGED_ENCRYPTION_INPUT_COUNT
    )
    initial_map = (
        report.bounded_worklist_initial_value_encryption_input_source_map
    )
    assert tuple(item.address for item in initial_map) == (0,)
    assert initial_map[0].source_byte_offset == _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
    changed_map = (
        report.bounded_worklist_changed_encryption_input_value_source_map
    )
    assert len(changed_map) == 1
    changed = changed_map[0]
    assert changed.address == 1
    assert changed.source_byte_offset == _ENTRY_WRAP_SOURCE_OFFSET_SHIFT + 1
    assert changed.initial_memory_value == _INPUT_CRAZY_SOURCE[1]
    assert len(changed.values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert changed.initial_memory_value_in_values is False
    assert worklist.explored_committed_data_write_transition_count == 0
    assert worklist.explored_committed_data_write_value_domains == ()


def test_worklist_alias_witnesses_map_loaded_source_and_paths() -> None:
    """C/D alias addresses and shortest paths map to loaded source exactly."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _INPUT_CRAZY_SOURCE,
        worklist_state_limit=_WORKLIST_COMPLETE_STATE_LIMIT,
    )
    contexts = report.bounded_worklist_code_data_alias_source_contexts
    assert tuple(context.address for context in contexts) == (0, 1)
    assert tuple(context.memory_value for context in contexts) == tuple(
        _INPUT_CRAZY_SOURCE
    )
    assert tuple(context.source_byte_offset for context in contexts) == (2, 3)
    assert len(contexts[0].entry_path_source_map) == 1
    assert len(contexts[1].entry_path_source_map) == len(contexts)
    first_path = contexts[0].entry_path_source_map
    second_path = contexts[1].entry_path_source_map
    assert first_path[0].code_pointer == 0
    assert first_path[0].data_pointer == 0
    assert tuple(item.code_pointer for item in second_path) == (0, 1)
    assert tuple(item.data_pointer for item in second_path) == (0, 1)
    assert tuple(item.source_byte_offset for item in second_path) == (2, 3)
    assert tuple(item.data_source_byte_offset for item in second_path) == (2, 3)


def test_report_worklist_resolves_input_dependent_crazy() -> None:
    """Opt-in worklist resolves every byte/EOF branch after input."""
    report = _ANALYZER_MODULE.analyze_source(
        _INPUT_CRAZY_SOURCE,
        worklist_state_limit=_WORKLIST_COMPLETE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _WORKLIST_COMPLETE_STATE_LIMIT
    assert worklist.explored_states == _WORKLIST_COMPLETE_STATE_LIMIT
    assert not worklist.reachable_cycle_detected
    assert worklist.explored_minimum_words == _TWO_SOURCE_WORDS
    assert worklist.explored_accessed_addresses == (0, 1)
    assert worklist.explored_wraparound_transition_count == 0
    assert worklist.explored_wraparound_witness is None
    _assert_worklist_mutation_evidence(worklist)
    assert report.bounded_worklist_data_mutation_source_context is None
    assert report.bounded_worklist_effective_data_mutation_source_map == ()
    assert (
        report.bounded_worklist_effective_data_mutation_value_source_map == ()
    )
    assert report.bounded_worklist_fetch_value_source_map
    assert report.bounded_worklist_data_read_value_source_map
    assert report.bounded_worklist_encryption_input_value_source_map
    assert worklist.terminal_status_counts == (
        ("rejected-invalid-self-encryption", _WORKLIST_INPUT_VALUE_COUNT),
    )
    assert worklist.closed_terminal_status_counts == (
        ("rejected-invalid-self-encryption", _WORKLIST_INPUT_VALUE_COUNT),
    )
    assert worklist.closed_all_paths_terminate is True
    assert worklist.closed_all_paths_halt is False
    _assert_terminal_witness_object(worklist)
    assert not worklist.truncated
    assert {
        _WORKLIST_CLOSED_LIMIT,
        _WORKLIST_ALIAS_LIMIT,
        _WORKLIST_DATAFLOW_LIMIT,
        _WORKLIST_MUTATION_LIMIT,
        _WORKLIST_WRAP_LIMIT,
    }.issubset(report.analysis_limits)


def _assert_entry_noop_context(worklist: _WorklistAnalysis) -> None:
    assert worklist.explored_committed_data_write_noop_transition_count == (
        _ENTRY_NOOP_DATA_WRITE_COUNT
    )
    assert worklist.explored_committed_data_write_noop_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    witness = worklist.explored_data_write_noop_witness
    assert witness is not None
    assert witness.address == _ENTRY_MUTATION_ADDRESS
    assert witness.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert witness.written_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert witness.result_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert witness.entry_path[-1] == witness.state


def _assert_entry_wrap_mutation_context(
    report: _Report,
    worklist: _WorklistAnalysis,
) -> None:
    mutation = worklist.explored_data_mutation_witness
    assert mutation is not None
    assert mutation.address == _ENTRY_MUTATION_ADDRESS
    assert mutation.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert mutation.result_value == _ENTRY_MUTATION_RESULT_VALUE
    assert mutation.entry_path[-1] == mutation.state
    assert mutation.state.accumulator == _ENTRY_MUTATION_ACCUMULATOR
    assert worklist.explored_committed_data_write_transition_count == (
        _ENTRY_COMMITTED_DATA_WRITE_COUNT
    )
    assert worklist.explored_committed_data_write_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    _assert_entry_noop_context(worklist)
    assert worklist.explored_effective_data_mutation_transition_count == (
        _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    )
    assert worklist.explored_effective_data_mutation_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    domains = worklist.explored_effective_data_mutation_value_domains
    assert len(domains) == 1
    assert domains[0].previous_values == (_ENTRY_MUTATION_PREVIOUS_VALUE,)
    assert len(domains[0].result_values) == _ENTRY_MUTATION_RESULT_DOMAIN_COUNT
    context = report.bounded_worklist_data_mutation_source_context
    assert context is not None
    assert context.address == _ENTRY_MUTATION_ADDRESS
    assert context.source_position is None
    assert context.source_byte_offset is None
    assert context.initial_source_byte is None
    assert context.previous_value_matches_initial_source is None


def _assert_entry_wrap_signature_source_map(report: _Report) -> None:
    signatures = report.bounded_worklist_wraparound_transition_source_map
    assert len(signatures) == 1
    signature = signatures[0]
    source_code, source_data = _ENTRY_WRAP_POINTER_PATH[-1]
    assert signature.source_code_pointer == source_code
    assert signature.source_data_pointer == source_data
    assert signature.result_code_pointer == _ENTRY_WRAP_RESULT_CODE_POINTER
    assert signature.result_data_pointer == 0
    assert not signature.code_pointer_wrapped
    assert signature.data_pointer_wrapped
    assert signature.source_position == source_code
    assert signature.source_byte_offset == (
        _ENTRY_WRAP_SOURCE_OFFSET_SHIFT + source_code
    )
    assert signature.data_source_position is None
    assert signature.data_source_byte_offset is None


def _assert_entry_wrap_control_source_maps(report: _Report) -> None:
    noop = report.bounded_worklist_data_write_noop_entry_path_source_map
    mutation = report.bounded_worklist_data_mutation_entry_path_source_map
    wrap = report.bounded_worklist_wraparound_entry_path_source_map
    data_wrap = report.bounded_worklist_data_pointer_wrap_entry_path_source_map
    assert data_wrap == wrap
    assert report.bounded_worklist_code_pointer_wrap_entry_path_source_map == ()
    assert (
        report.bounded_worklist_simultaneous_pointer_wrap_entry_path_source_map
        == ()
    )
    assert tuple(context.code_pointer for context in noop) == (0, 1, 2)
    assert tuple(context.source_byte_offset for context in noop) == (2, 3, 4)
    assert tuple(context.code_pointer for context in mutation) == (0, 1, 2)
    mutation_offsets = tuple(context.source_byte_offset for context in mutation)
    assert mutation_offsets == (2, 3, 4)
    assert tuple(context.data_source_byte_offset for context in noop) == (
        2, 3, None
    )
    assert tuple(context.data_source_byte_offset for context in mutation) == (
        2, 3, None
    )
    assert tuple(context.code_pointer for context in wrap) == (0, 1, 2, 3, 4, 5)
    assert tuple(context.source_byte_offset for context in wrap) == (
        2, 3, 4, 5, 6, 7
    )


def test_worklist_maps_mutation_noop_and_wrap_control_paths() -> None:
    """Mutation and wrap witness C paths preserve loaded source offsets."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    _assert_entry_wrap_control_source_maps(report)
    _assert_entry_wrap_signature_source_map(report)
    assert _WORKLIST_VALUE_SOURCE_MAP_LIMIT in report.analysis_limits


def test_control_path_maps_loaded_data_pointer_source() -> None:
    """Control-path D source mapping reaches loaded position 40 exactly."""
    report = _ANALYZER_MODULE.analyze_source(
        _LOADED_MUTATION_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    contexts = report.bounded_worklist_data_mutation_entry_path_source_map
    final = contexts[-1]
    assert final.data_pointer == _LOADED_MUTATION_ADDRESS
    assert final.data_source_position == _LOADED_MUTATION_ADDRESS
    assert final.data_source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert final.initial_data_source_byte == _LOADED_MUTATION_SOURCE_BYTE


def _assert_data_only_wrap_witness(worklist: _WorklistAnalysis) -> None:
    witness = worklist.explored_wraparound_witness
    assert witness is not None
    assert worklist.explored_code_pointer_wrap_witness is None
    assert worklist.explored_data_pointer_wrap_witness == witness
    assert worklist.explored_simultaneous_pointer_wrap_witness is None


def test_report_worklist_observes_entry_reachable_eof_wrap() -> None:
    """Public bounded worklist counts the exact EOF-branch pointer wrap."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _ENTRY_WRAP_WORKLIST_STATE_LIMIT
    assert worklist.explored_states == _ENTRY_WRAP_EXPLORED_STATES
    assert worklist.explored_wraparound_transition_count == 1
    assert worklist.explored_code_pointer_wrap_transition_count == 0
    assert worklist.explored_data_pointer_wrap_transition_count == 1
    assert worklist.explored_simultaneous_pointer_wrap_transition_count == 0
    _assert_data_only_wrap_witness(worklist)
    witness = worklist.explored_wraparound_witness
    assert witness is not None
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in witness.entry_path
    ) == _ENTRY_WRAP_POINTER_PATH
    assert witness.entry_path[-1] == witness.state
    assert witness.result_code_pointer == _ENTRY_WRAP_RESULT_CODE_POINTER
    assert witness.result_data_pointer == 0
    assert not witness.code_pointer_wrapped
    assert witness.data_pointer_wrapped
    _assert_entry_wrap_mutation_context(report, worklist)
    assert worklist.frontier_states == _WORKLIST_INPUT_VALUE_COUNT
    assert worklist.truncated
    assert _ENTRY_WRAP_LIMIT in report.analysis_limits
    assert _ENTRY_DATAFLOW_LIMIT in report.analysis_limits


def _assert_loaded_mutation_value_source_context(report: _Report) -> None:
    value_contexts = (
        report.bounded_worklist_effective_data_mutation_value_source_map
    )
    assert len(value_contexts) == 1
    context = value_contexts[0]
    assert context.address == _LOADED_MUTATION_ADDRESS
    assert context.source_position == _LOADED_MUTATION_ADDRESS
    assert context.source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert context.initial_source_byte == _LOADED_MUTATION_SOURCE_BYTE
    assert context.previous_values == (_LOADED_MUTATION_SOURCE_BYTE,)
    assert context.result_values
    assert context.initial_source_byte_in_previous_values is True


def test_worklist_data_mutation_maps_back_to_loaded_source_byte() -> None:
    """Worklist mutation context preserves loaded and raw source offsets."""
    report = _ANALYZER_MODULE.analyze_source(
        _LOADED_MUTATION_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    mutation = worklist.explored_data_mutation_witness
    assert mutation is not None
    assert mutation.address == _LOADED_MUTATION_ADDRESS
    assert mutation.previous_value == _LOADED_MUTATION_PREVIOUS_VALUE
    assert mutation.result_value == _LOADED_MUTATION_RESULT_VALUE
    context = report.bounded_worklist_data_mutation_source_context
    assert context is not None
    assert context.address == _LOADED_MUTATION_ADDRESS
    assert context.source_position == _LOADED_MUTATION_ADDRESS
    assert context.source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert context.initial_source_byte == _LOADED_MUTATION_SOURCE_BYTE
    assert context.previous_value_matches_initial_source is True
    aggregate = report.bounded_worklist_effective_data_mutation_source_map
    assert len(aggregate) == 1
    assert aggregate[0].address == _LOADED_MUTATION_ADDRESS
    assert aggregate[0].source_position == _LOADED_MUTATION_ADDRESS
    assert aggregate[0].source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert aggregate[0].initial_source_byte == _LOADED_MUTATION_SOURCE_BYTE
    _assert_loaded_mutation_value_source_context(report)
    assert _WORKLIST_VALUE_SOURCE_MAP_LIMIT in report.analysis_limits


def _value_source_context(
    contexts: tuple[_WorklistValueSourceContext, ...],
    address: int,
) -> _WorklistValueSourceContext:
    matches = tuple(
        context for context in contexts if context.address == address
    )
    assert len(matches) == 1
    return matches[0]


def _assert_loaded_fetch_value_source_context(report: _Report) -> None:
    fetch = _value_source_context(
        report.bounded_worklist_fetch_value_source_map, 0
    )
    assert fetch.source_position == 0
    assert fetch.source_byte_offset == _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
    assert fetch.initial_source_byte == _ENTRY_WRAP_SOURCE[0]
    assert fetch.initial_memory_value == _ENTRY_WRAP_SOURCE[0]
    assert fetch.values == (_ENTRY_WRAP_SOURCE[0],)
    assert fetch.initial_source_byte_in_values is True
    assert fetch.initial_memory_value_in_values is True


def test_worklist_read_domains_map_loaded_and_recurrence_source() -> None:
    """Read value domains preserve loaded offsets and recurrence nullability."""
    report = _ANALYZER_MODULE.analyze_source(
        _LOADED_MUTATION_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    _assert_loaded_fetch_value_source_context(report)
    loaded = _value_source_context(
        report.bounded_worklist_data_read_value_source_map,
        _LOADED_MUTATION_ADDRESS,
    )
    assert loaded.source_position == _LOADED_MUTATION_ADDRESS
    assert loaded.source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert loaded.initial_source_byte == _LOADED_MUTATION_SOURCE_BYTE
    assert loaded.values == (_LOADED_MUTATION_SOURCE_BYTE,)
    assert loaded.initial_source_byte_in_values is True
    recurrence = _value_source_context(
        report.bounded_worklist_data_read_value_source_map,
        _MULTI_MUTATION_RECURRENCE_ADDRESS,
    )
    assert recurrence.source_position is None
    assert recurrence.source_byte_offset is None
    assert recurrence.initial_source_byte is None
    assert recurrence.values == (_MULTI_MUTATION_SECOND_PREVIOUS_VALUES)
    assert recurrence.initial_source_byte_in_values is None
    encryption = _value_source_context(
        report.bounded_worklist_encryption_input_value_source_map, 0
    )
    assert encryption.source_byte_offset == _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
    assert encryption.initial_source_byte_in_values is True
    assert _WORKLIST_VALUE_SOURCE_MAP_LIMIT in report.analysis_limits


def test_rejected_planned_write_domain_maps_loaded_source() -> None:
    """Rejected planned writes retain source context without committing."""
    report = _ANALYZER_MODULE.analyze_source(
        _INPUT_CRAZY_SOURCE,
        worklist_state_limit=_WORKLIST_COMPLETE_STATE_LIMIT,
    )
    context = _value_source_context(
        report.bounded_worklist_planned_data_write_value_source_map, 1
    )
    assert context.source_position == 1
    assert context.source_byte_offset == 1
    assert context.initial_source_byte == _INPUT_CRAZY_SOURCE[1]
    assert len(context.values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert context.initial_source_byte_in_values is False
    assert report.bounded_worklist_committed_data_write_value_source_map == ()


def test_recurrence_planned_write_domain_stays_unmapped() -> None:
    """Recurrence-targeted plans do not invent loaded source coordinates."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    context = _value_source_context(
        report.bounded_worklist_planned_data_write_value_source_map,
        _ENTRY_MUTATION_ADDRESS,
    )
    assert context.source_position is None
    assert context.source_byte_offset is None
    assert context.initial_source_byte is None
    assert context.values
    assert context.initial_source_byte_in_values is None


def test_worklist_write_domains_map_loaded_source() -> None:
    """Committed output domains preserve loaded source coordinates."""
    report = _ANALYZER_MODULE.analyze_source(
        _LOADED_MUTATION_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    data = _value_source_context(
        report.bounded_worklist_committed_data_write_value_source_map,
        _LOADED_MUTATION_ADDRESS,
    )
    assert data.source_position == _LOADED_MUTATION_ADDRESS
    assert data.source_byte_offset == _LOADED_MUTATION_BYTE_OFFSET
    assert data.initial_source_byte == _LOADED_MUTATION_SOURCE_BYTE
    assert data.values
    assert data.initial_source_byte_in_values is False
    encryption = _value_source_context(
        report.bounded_worklist_self_encryption_output_value_source_map, 0
    )
    assert encryption.source_position == 0
    assert encryption.source_byte_offset == _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
    assert encryption.initial_source_byte == _ENTRY_WRAP_SOURCE[0]
    assert encryption.values == (111,)
    assert encryption.initial_source_byte_in_values is False


def test_worklist_write_domains_keep_recurrence_unmapped() -> None:
    """Committed recurrence writes do not invent loaded source coordinates."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    data = _value_source_context(
        report.bounded_worklist_committed_data_write_value_source_map,
        _ENTRY_MUTATION_ADDRESS,
    )
    assert data.source_position is None
    assert data.source_byte_offset is None
    assert data.initial_source_byte is None
    assert data.values
    assert data.initial_source_byte_in_values is None


def _assert_committed_write_role_maps(report: _Report) -> None:
    data_contexts = report.bounded_worklist_committed_data_write_source_map
    assert len(data_contexts) == 1
    assert data_contexts[0].address == _ENTRY_WRAP_RECURRENCE_WRITE_ADDRESS
    assert data_contexts[0].source_position is None
    encryption_contexts = report.bounded_worklist_self_encryption_source_map
    assert tuple(context.address for context in encryption_contexts) == (
        _ENTRY_WRAP_LOADED_WRITE_ADDRESSES
    )
    encryption_offsets = tuple(
        context.source_byte_offset for context in encryption_contexts
    )
    expected_offsets = tuple(
        address + _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
        for address in _ENTRY_WRAP_LOADED_WRITE_ADDRESSES
    )
    assert encryption_offsets == expected_offsets


def test_worklist_maps_every_committed_write_address() -> None:
    """Committed data and encryption writes retain exact source coordinates."""
    report = _ANALYZER_MODULE.analyze_source(
        _ENTRY_WRAP_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.explored_committed_write_addresses == (
        _ENTRY_WRAP_COMMITTED_WRITE_ADDRESSES
    )
    contexts = report.bounded_worklist_committed_write_source_map
    assert tuple(context.address for context in contexts) == (
        _ENTRY_WRAP_COMMITTED_WRITE_ADDRESSES
    )
    loaded = contexts[:-1]
    recurrence = contexts[-1]
    assert tuple(context.source_position for context in loaded) == (
        _ENTRY_WRAP_LOADED_WRITE_ADDRESSES
    )
    assert tuple(context.source_byte_offset for context in loaded) == tuple(
        address + _ENTRY_WRAP_SOURCE_OFFSET_SHIFT
        for address in _ENTRY_WRAP_LOADED_WRITE_ADDRESSES
    )
    assert tuple(context.initial_source_byte for context in loaded) == tuple(
        _ENTRY_WRAP_SOURCE[address]
        for address in _ENTRY_WRAP_LOADED_WRITE_ADDRESSES
    )
    assert recurrence.address == _ENTRY_WRAP_RECURRENCE_WRITE_ADDRESS
    assert recurrence.source_position is None
    assert recurrence.source_byte_offset is None
    assert recurrence.initial_source_byte is None
    _assert_committed_write_role_maps(report)
    assert _WORKLIST_VALUE_SOURCE_MAP_LIMIT in report.analysis_limits


def _assert_recurrence_mutation_value_source_context(report: _Report) -> None:
    contexts = report.bounded_worklist_effective_data_mutation_value_source_map
    context = contexts[-1]
    assert context.address == _MULTI_MUTATION_SECOND_ADDRESS
    assert context.source_position is None
    assert context.source_byte_offset is None
    assert context.initial_source_byte is None
    assert context.previous_values == _MULTI_MUTATION_SECOND_PREVIOUS_VALUES
    assert context.result_values == _MULTI_MUTATION_SECOND_RESULT_VALUES
    assert context.initial_source_byte_in_previous_values is None


def test_worklist_maps_every_effective_mutation_address() -> None:
    """Aggregate source mapping preserves loaded versus recurrence addresses."""
    report = _ANALYZER_MODULE.analyze_source(
        _MULTI_MUTATION_SOURCE_WITH_WHITESPACE,
        worklist_state_limit=_ENTRY_WRAP_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.explored_effective_data_mutation_addresses == (
        _MULTI_MUTATION_ADDRESSES
    )
    contexts = report.bounded_worklist_effective_data_mutation_source_map
    assert len(contexts) == len(_MULTI_MUTATION_ADDRESSES)
    loaded, recurrence = contexts
    assert loaded.address == _MULTI_MUTATION_LOADED_ADDRESS
    assert loaded.source_position == _MULTI_MUTATION_LOADED_ADDRESS
    assert loaded.source_byte_offset == _MULTI_MUTATION_LOADED_BYTE_OFFSET
    assert loaded.initial_source_byte == _MULTI_MUTATION_LOADED_SOURCE_BYTE
    assert recurrence.address == _MULTI_MUTATION_RECURRENCE_ADDRESS
    assert recurrence.source_position is None
    assert recurrence.source_byte_offset is None
    assert recurrence.initial_source_byte is None
    domains = worklist.explored_effective_data_mutation_value_domains
    assert tuple(domain.address for domain in domains) == (
        _MULTI_MUTATION_ADDRESSES
    )
    second = domains[-1]
    assert second.address == _MULTI_MUTATION_SECOND_ADDRESS
    assert second.previous_values == _MULTI_MUTATION_SECOND_PREVIOUS_VALUES
    assert second.result_values == _MULTI_MUTATION_SECOND_RESULT_VALUES
    _assert_recurrence_mutation_value_source_context(report)
    assert _WORKLIST_VALUE_SOURCE_MAP_LIMIT in report.analysis_limits


def test_report_worklist_proves_long_input_dependent_cycle() -> None:
    """Public worklist evidence reaches a cycle after three post-input jumps."""
    report = _ANALYZER_MODULE.analyze_source(
        _LONG_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_LONG_INPUT_CYCLE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _LONG_INPUT_CYCLE_STATE_LIMIT
    assert worklist.reachable_cycle_detected
    path = worklist.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _LONG_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == worklist.reachable_cycle_witness[0]
    assert worklist.closed_all_paths_terminate is False
    assert worklist.closed_all_paths_halt is False
    assert not worklist.truncated


def test_report_worklist_proves_deeper_input_dependent_cycle() -> None:
    """Public worklist closes a six-state input-dependent cycle path."""
    report = _ANALYZER_MODULE.analyze_source(
        _DEEP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_DEEP_INPUT_CYCLE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _DEEP_INPUT_CYCLE_STATE_LIMIT
    assert worklist.reachable_cycle_detected
    assert worklist.maximum_first_seen_transition_index == len(
        _DEEP_INPUT_CYCLE_POINTER_PATH
    )
    path = worklist.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _DEEP_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == worklist.reachable_cycle_witness[0]
    assert worklist.closed_all_paths_terminate is False
    assert worklist.closed_all_paths_halt is False
    assert not worklist.truncated


def test_worklist_maps_all_explored_control_pointer_addresses() -> None:
    """Explored C/D domains map loaded addresses without mapping recurrence."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _NEAR_CAP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.explored_code_pointer_addresses == tuple(range(16))
    assert (
        worklist.explored_data_pointer_addresses
        == _NEAR_CAP_INPUT_CYCLE_DATA_POINTER_ADDRESSES
    )
    code_map = report.bounded_worklist_explored_code_pointer_source_map
    assert tuple(context.address for context in code_map) == tuple(range(16))
    assert tuple(context.source_byte_offset for context in code_map) == (
        *range(2, 17),
        None,
    )
    data_map = report.bounded_worklist_explored_data_pointer_source_map
    assert tuple(context.address for context in data_map) == (
        _NEAR_CAP_INPUT_CYCLE_DATA_POINTER_ADDRESSES
    )
    assert tuple(context.source_byte_offset for context in data_map) == (
        2,
        3,
        None,
        None,
        None,
    )


def _assert_recurrence_cycle_body_source_map(report: _Report) -> None:
    cycle_body = report.bounded_worklist_cycle_witness_source_map
    recurrent_body = (
        report.bounded_worklist_closed_recurrent_cycle_witness_source_map
    )
    assert len(cycle_body) == 1
    assert cycle_body == recurrent_body
    body = cycle_body[0]
    assert body.cycle_state_index == 0
    assert body.code_pointer == _NEAR_CAP_INPUT_CYCLE_POINTER_PATH[-1][0]
    assert body.data_pointer == _NEAR_CAP_INPUT_CYCLE_POINTER_PATH[-1][1]
    assert body.source_position is None
    assert body.data_source_position is None
    known = report.bounded_worklist_known_graph_cyclic_component_source_maps
    closed = report.bounded_worklist_closed_recurrent_component_source_maps
    assert closed is not None
    assert known == closed
    assert len(known) == _WORKLIST_INPUT_VALUE_COUNT
    assert tuple(item.component_index for item in known) == tuple(
        range(_WORKLIST_INPUT_VALUE_COUNT)
    )
    assert all(len(item.states) == 1 for item in known)
    assert all(
        item.minimum_entry_path_state_count
        == len(_NEAR_CAP_INPUT_CYCLE_POINTER_PATH)
        for item in known
    )
    assert all(item.states[0].source_position is None for item in known)


def test_worklist_maps_closed_cycle_and_recurrent_control_paths() -> None:
    """Closed cycle paths distinguish loaded and recurrence source."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _NEAR_CAP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT,
    )
    cycle = report.bounded_worklist_cycle_entry_path_source_map
    recurrent = report.bounded_worklist_closed_recurrent_entry_path_source_map
    expected_pointers = tuple(range(16))
    expected_offsets = (*range(2, 17), None)
    assert tuple(context.code_pointer for context in cycle) == expected_pointers
    cycle_offsets = tuple(context.source_byte_offset for context in cycle)
    assert cycle_offsets == expected_offsets
    recurrent_pointers = tuple(context.code_pointer for context in recurrent)
    assert recurrent_pointers == expected_pointers
    recurrent_offsets = tuple(
        context.source_byte_offset for context in recurrent
    )
    assert recurrent_offsets == expected_offsets
    _assert_recurrence_cycle_body_source_map(report)


def test_worklist_maps_loaded_explored_control_pointer_boundary() -> None:
    """Deep loaded C domain stays source-linked while later D values do not."""
    report = _ANALYZER_MODULE.analyze_source(
        _DOUBLE_JUMP_MERGED_LOADED_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    code_map = report.bounded_worklist_explored_code_pointer_source_map
    assert tuple(context.address for context in code_map) == tuple(range(124))
    assert tuple(context.source_position for context in code_map) == tuple(
        range(124)
    )
    data_map = {
        context.address: context
        for context in report.bounded_worklist_explored_data_pointer_source_map
    }
    assert data_map[_DOUBLE_JUMP_MERGED_CYCLE_ADDRESS].source_position == (
        _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    )
    assert (
        data_map[_DOUBLE_JUMP_MERGED_CYCLE_DATA_POINTER].source_position is None
    )


def test_worklist_maps_loaded_cycle_body_with_recurrence_data_pointer() -> None:
    """Cycle-body mapping keeps loaded C and recurrence D independent."""
    report = _ANALYZER_MODULE.analyze_source(
        _DOUBLE_JUMP_MERGED_LOADED_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    cycle = report.bounded_worklist_cycle_witness_source_map
    recurrent = (
        report.bounded_worklist_closed_recurrent_cycle_witness_source_map
    )
    assert len(cycle) == 1
    assert cycle == recurrent
    context = cycle[0]
    assert context.cycle_state_index == 0
    assert context.code_pointer == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert context.data_pointer == _DOUBLE_JUMP_MERGED_CYCLE_DATA_POINTER
    assert context.source_position == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert context.source_byte_offset == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert (
        context.initial_source_byte
        == _DOUBLE_JUMP_MERGED_LOADED_CYCLE_INITIAL_BYTE
    )
    assert context.data_source_position is None
    assert context.data_source_byte_offset is None
    assert context.initial_data_source_byte is None
    known = report.bounded_worklist_known_graph_cyclic_component_source_maps
    closed = report.bounded_worklist_closed_recurrent_component_source_maps
    assert closed is not None
    assert known == closed
    assert len(known) == _DOUBLE_JUMP_MERGED_CYCLIC_COMPONENT_COUNT
    assert all(len(item.states) == 1 for item in known)
    assert all(
        item.minimum_entry_path_state_count
        == _DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH
        for item in known
    )
    assert all(
        item.states[0].source_position == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
        for item in known
    )
    assert all(item.states[0].data_source_position is None for item in known)


def test_worklist_maps_truncated_frontier_control_path() -> None:
    """Truncated frontier C path keeps every loaded source position exact."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _OVER_CAP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    frontier = report.bounded_worklist_frontier_entry_path_source_map
    frontier_pointers = tuple(context.code_pointer for context in frontier)
    assert frontier_pointers == tuple(range(16))
    assert tuple(context.source_byte_offset for context in frontier) == tuple(
        range(2, 18)
    )
    known_components = (
        report.bounded_worklist_known_graph_cyclic_component_source_maps
    )
    closed_components = (
        report.bounded_worklist_closed_recurrent_component_source_maps
    )
    assert known_components == ()
    assert closed_components is None
    worklist = report.bounded_worklist
    assert worklist is not None
    assert (
        worklist.known_graph_cyclic_component_minimum_entry_path_state_counts
        == ()
    )
    assert (
        worklist.closed_recurrent_component_minimum_entry_path_state_counts
        is None
    )


def test_worklist_maps_terminal_control_path_with_status() -> None:
    """Terminal source paths remain status-labeled and source-linked."""
    report = _ANALYZER_MODULE.analyze_source(
        b" \n" + _INPUT_CRAZY_SOURCE,
        worklist_state_limit=_WORKLIST_COMPLETE_STATE_LIMIT,
    )
    maps = report.bounded_worklist_terminal_entry_path_source_maps
    assert len(maps) == 1
    assert maps[0].status == _ENTRY_INVALID_ENCRYPTION
    contexts = maps[0].entry_path_source_map
    assert tuple(context.code_pointer for context in contexts) == (0, 1)
    assert tuple(context.source_byte_offset for context in contexts) == (2, 3)
    assert tuple(context.data_source_byte_offset for context in contexts) == (
        2, 3
    )
    assert report.bounded_worklist_cycle_entry_path_source_map == ()
    assert report.bounded_worklist_frontier_entry_path_source_map == ()


def _assert_cycle_closing_source_context(
    report: _Report,
    worklist: _WorklistAnalysis,
    *,
    expected_code_pointer: int,
    expected_source_position: int | None,
) -> None:
    closing = worklist.explored_cycle_closing_repeated_edge_witness
    assert closing is not None
    source = report.bounded_worklist_cycle_closing_repeated_edge_source_context
    assert source is not None
    assert source.target_entry_path_state_index == (
        len(source.source_entry_path_source_map) - 1
    )
    target_source = source.target_state_source_context
    assert target_source.code_pointer == expected_code_pointer
    assert target_source.source_position == expected_source_position


def test_report_worklist_proves_near_cap_input_cycle() -> None:
    """Public worklist closes a 16-state cycle path near its state cap."""
    report = _ANALYZER_MODULE.analyze_source(
        _NEAR_CAP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _NEAR_CAP_INPUT_CYCLE_STATE_LIMIT
    assert worklist.explored_state_merge_transition_count == 0
    assert (
        worklist.explored_cycle_closing_repeated_edge_count
        == _WORKLIST_INPUT_VALUE_COUNT
    )
    assert worklist.explored_state_merge_witness is None
    assert report.bounded_worklist_state_merge_source_context is None
    _assert_cycle_closing_source_context(
        report,
        worklist,
        expected_code_pointer=_NEAR_CAP_INPUT_CYCLE_POINTER_PATH[-1][0],
        expected_source_position=None,
    )
    assert worklist.reachable_cycle_detected
    assert worklist.maximum_first_seen_transition_index == len(
        _NEAR_CAP_INPUT_CYCLE_POINTER_PATH
    )
    path = worklist.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _NEAR_CAP_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == worklist.reachable_cycle_witness[0]
    assert worklist.closed_all_paths_terminate is False
    assert worklist.closed_all_paths_halt is False
    assert not worklist.truncated


def _assert_branch_merge_evidence(
    report: _Report,
    worklist: _WorklistAnalysis,
) -> None:
    assert (
        worklist.explored_state_merge_transition_count
        == _MERGED_INPUT_CYCLE_STATE_MERGES
    )
    assert (
        worklist.explored_cycle_closing_repeated_edge_count
        == _MERGED_INPUT_CYCLE_CYCLE_CLOSING_REPEATS
    )
    assert (
        worklist.explored_state_merge_transition_count
        + worklist.explored_cycle_closing_repeated_edge_count
        == worklist.repeated_state_edges
    )
    _assert_cycle_closing_source_context(
        report,
        worklist,
        expected_code_pointer=_MERGED_INPUT_CYCLE_PATH_LENGTH - 1,
        expected_source_position=_MERGED_INPUT_CYCLE_PATH_LENGTH - 1,
    )
    merge = worklist.explored_state_merge_witness
    assert merge is not None
    source_pointer = (
        merge.source_state.code_pointer,
        merge.source_state.data_pointer,
    )
    target_pointer = (
        merge.target_state.code_pointer,
        merge.target_state.data_pointer,
    )
    assert source_pointer == _MERGED_INPUT_CYCLE_MERGE_SOURCE_POINTER
    assert target_pointer == _MERGED_INPUT_CYCLE_MERGE_TARGET_POINTER
    source_context = report.bounded_worklist_state_merge_source_context
    assert source_context is not None
    source_path = source_context.source_entry_path_source_map
    target_path = source_context.target_entry_path_source_map
    assert tuple(item.code_pointer for item in source_path) == (0, 1, 2)
    assert tuple(item.data_pointer for item in source_path) == (0, 1, 40)
    assert tuple(item.code_pointer for item in target_path) == (0, 1, 2, 3)
    assert tuple(item.data_pointer for item in target_path) == (0, 1, 40, 41)
    assert (
        source_path[-1].data_source_position
        == _MERGED_INPUT_CYCLE_MERGE_SOURCE_POINTER[1]
    )
    assert (
        target_path[-1].data_source_position
        == _MERGED_INPUT_CYCLE_MERGE_TARGET_POINTER[1]
    )


def test_report_worklist_proves_branch_merged_deeper_cycle() -> None:
    """Public worklist closes a 41-state input-dependent cycle path."""
    report = _ANALYZER_MODULE.analyze_source(
        _MERGED_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _MERGED_INPUT_CYCLE_STATE_LIMIT
    assert worklist.input_branch_points == 1
    _assert_branch_merge_evidence(report, worklist)
    assert worklist.reachable_cycle_detected
    path = worklist.reachable_cycle_entry_path
    assert len(path) == _MERGED_INPUT_CYCLE_PATH_LENGTH
    assert tuple(state.code_pointer for state in path) == tuple(
        range(_MERGED_INPUT_CYCLE_PATH_LENGTH)
    )
    source_map = report.bounded_worklist_cycle_entry_path_source_map
    assert tuple(context.source_position for context in source_map) == tuple(
        range(_MERGED_INPUT_CYCLE_PATH_LENGTH)
    )
    assert worklist.closed_all_paths_terminate is False
    assert worklist.closed_all_paths_halt is False
    assert not worklist.truncated


def _assert_124_state_evolved_fetch_evidence(
    report: _Report,
    worklist: _WorklistAnalysis,
) -> None:
    path = worklist.reachable_cycle_entry_path
    evolved = worklist.explored_evolved_fetch_witness
    assert evolved is not None
    assert evolved.state == path[-1]
    assert evolved.address == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert evolved.initial_value == _DOUBLE_JUMP_MERGED_CYCLE_INITIAL_VALUE
    assert evolved.observed_value == _DOUBLE_JUMP_MERGED_CYCLE_EVOLVED_VALUE
    assert (
        evolved.origin_entry_path_transition_index
        == _DOUBLE_JUMP_MERGED_CYCLE_WRITER_TRANSITION
    )
    source_map = report.bounded_worklist_cycle_entry_path_source_map
    assert len(source_map) == _DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH
    assert source_map[-2].source_position == (
        _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS - 1
    )
    assert source_map[-1].code_pointer == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert source_map[-1].source_position is None
    writer = report.bounded_worklist_evolved_fetch_writer_source_context
    assert writer is not None
    assert writer.origin_entry_path_transition_index == (
        _DOUBLE_JUMP_MERGED_CYCLE_WRITER_TRANSITION
    )
    assert writer.origin_value == _DOUBLE_JUMP_MERGED_CYCLE_EVOLVED_VALUE
    writer_state = writer.writer_state_source_context
    assert writer_state.code_pointer == (
        _DOUBLE_JUMP_MERGED_CYCLE_WRITER_CODE_POINTER
    )
    assert writer_state.data_pointer == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS


def test_report_worklist_proves_124_state_input_cycle() -> None:
    """Public worklist links a deep evolved fetch back to its exact writer."""
    report = _ANALYZER_MODULE.analyze_source(
        _DOUBLE_JUMP_MERGED_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _DOUBLE_JUMP_MERGED_CYCLE_STATE_LIMIT
    assert worklist.maximum_first_seen_transition_index == (
        _DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH
    )
    path = worklist.reachable_cycle_entry_path
    assert tuple(state.code_pointer for state in path) == tuple(
        range(_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH)
    )
    _assert_124_state_evolved_fetch_evidence(report, worklist)
    assert not worklist.truncated


def test_report_worklist_truncates_at_reviewed_maximum() -> None:
    """Public maximum keeps deeper input reachability explicitly unknown."""
    report = _ANALYZER_MODULE.analyze_source(
        _OVER_CAP_INPUT_CYCLE_SOURCE,
        worklist_state_limit=_MAX_WORKLIST_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.unique_states == _MAX_WORKLIST_STATE_LIMIT
    assert worklist.explored_states == _OVER_CAP_EXPLORED_STATES
    assert worklist.frontier_states == _WORKLIST_TRUNCATED_STATE_LIMIT
    assert worklist.maximum_first_seen_transition_index == (
        _OVER_CAP_MAXIMUM_FIRST_SEEN_TRANSITION
    )
    assert not worklist.reachable_cycle_detected
    assert worklist.closed_all_paths_terminate is None
    assert worklist.closed_all_paths_halt is None
    assert worklist.truncated
    witness = worklist.frontier_state_witness
    path = worklist.frontier_entry_path
    assert witness is not None
    assert path is not None
    assert witness.accumulator == _OVER_CAP_FRONTIER_ACCUMULATOR
    assert not witness.eof_seen
    assert path[-1] == witness
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _OVER_CAP_FRONTIER_POINTER_PATH
    assert _MAX_WORKLIST_TRUNCATED_LIMIT in report.analysis_limits


def test_report_worklist_truncation_is_explicit() -> None:
    """A too-small state budget records frontier truncation fail-closed."""
    report = _ANALYZER_MODULE.analyze_source(
        _INPUT_HALT_SOURCE,
        worklist_state_limit=_WORKLIST_TRUNCATED_STATE_LIMIT,
    )
    worklist = report.bounded_worklist
    assert worklist is not None
    assert worklist.truncated
    assert worklist.frontier_states == _WORKLIST_TRUNCATED_STATE_LIMIT
    assert worklist.closed_recurrent_component_count is None
    assert worklist.closed_recurrent_state_count is None
    assert worklist.closed_recurrent_largest_component_states is None
    assert worklist.closed_recurrent_cycle_witness is None
    assert worklist.closed_recurrent_entry_path is None
    assert worklist.closed_terminal_status_counts is None
    assert worklist.closed_all_paths_terminate is None
    assert worklist.closed_all_paths_halt is None
    assert _WORKLIST_TRUNCATED_LIMIT in report.analysis_limits


def test_report_worklist_state_limit_is_fail_closed() -> None:
    """Public worklist budget accepts only its reviewed exact interval."""
    for invalid in (0, -1, True, _INVALID_WORKLIST_STATE_LIMIT):
        with pytest.raises(ValueError, match=_WORKLIST_LIMIT_ERROR):
            _ = _ANALYZER_MODULE.analyze_source(
                _INPUT_HALT_SOURCE,
                worklist_state_limit=cast("int", invalid),
            )


def test_report_transition_limit_is_fail_closed() -> None:
    """Public report depth accepts only the reviewed finite integer interval."""
    source = _sequential_output_source(2)
    for invalid in (0, -1, True, _INVALID_TOTAL_TRANSITION_LIMIT):
        with pytest.raises(
            ValueError,
            match=_TRANSITION_LIMIT_ERROR,
        ):
            _ = _ANALYZER_MODULE.analyze_source(
                source,
                transition_limit=cast("int", invalid),
            )


def test_continuation_bound_rejects_nonpositive_or_foreign_integer() -> None:
    """Finite prefix iteration accepts only positive exact integer bounds."""
    source = _sequential_output_source(2)
    report = _ANALYZER_MODULE.analyze_source(source)
    entry = report.entry_transition
    assert entry is not None
    for invalid in (0, -1, True):
        with pytest.raises(
            ValueError,
            match="maximum transitions must be a positive exact integer",
        ):
            _ = _ANALYZER_MODULE.prefix_transfer.analyze_continuations(
                tuple(source),
                entry,
                maximum_transitions=cast("int", invalid),
            )


def test_historical_address_domain_is_structurally_closed() -> None:
    """Classic pointers stay inside the fixed 59,049-word memory domain."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_JUMP_DATA_ASSIGNMENT in interpreter
    assert _HISTORICAL_JUMP_CODE_ASSIGNMENT in interpreter
    assert _HISTORICAL_CODE_WRAP in interpreter
    assert _HISTORICAL_DATA_WRAP in interpreter
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_memory_words == _PROFILE_MEMORY_WORDS
    assert report.profile_address_domain_closed


def test_dynamic_analysis_limits_are_explicit_and_stable() -> None:
    """Initial-image admission never implies dynamic reachability proof."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39, 38)))
    assert report.analysis_limits == (
        "code-data-aliasing:16-transition-prefix-only",
        "control-flow-reachability:16-transition-prefix-only",
        "dataflow:16-transition-prefix-only",
        "input-dependent-reachability:not-analyzed",
        "self-modification:16-transition-prefix-only",
        (
            "source-map-context:16-transition-memory-access-and-"
            "fetch-data-read-and-encryption-input-value-lineage"
        ),
        "wraparound-reachability:16-transition-prefix-only",
    )


def test_report_rendering_is_canonical_and_replayable() -> None:
    """Canonical JSON output is byte-stable for one report."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    first = _ANALYZER_MODULE.render_report(report)
    second = _ANALYZER_MODULE.render_report(report)
    assert first == second
    assert first.endswith("\n")
    parsed = cast("dict[str, object]", json.loads(first))
    assert parsed["schema"] == _SCHEMA
    assert parsed["admitted_initial_image"] is True
    assert parsed["bounded_exact_cycle"] is None
    assert parsed["bounded_worklist"] is None
    snapshots = cast(
        "list[dict[str, object]]",
        parsed["bounded_state_snapshots"],
    )
    assert snapshots[0]["before_transition"] == 1
    assert snapshots[0]["memory_overrides"] == []
    assert parsed["bounded_data_read_value_lineage"] == []
    encryption_lineage = cast(
        "list[dict[str, object]]",
        parsed["bounded_encryption_input_value_lineage"],
    )
    assert encryption_lineage[0]["origin_kind"] == _ORIGIN_LOADED_SOURCE


def test_cli_prints_same_report_as_library() -> None:
    """The command-line surface emits the exact canonical report bytes."""
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(_FIXTURE)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    expected = _ANALYZER_MODULE.render_report(
        _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    ).encode("utf-8")
    assert completed.stdout == expected
    assert not completed.stderr


def test_cli_accepts_closed_worklist_request(tmp_path: Path) -> None:
    """CLI publishes a closed exact input worklist under an explicit cap."""
    source = tmp_path / "input-halt.malbolge"
    _ = source.write_bytes(_INPUT_HALT_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--worklist-state-limit",
            str(_WORKLIST_COMPLETE_STATE_LIMIT),
            str(source),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    bounded = cast("dict[str, object]", document["bounded_worklist"])
    assert bounded["unique_states"] == _WORKLIST_COMPLETE_STATE_LIMIT
    assert bounded["closed_terminal_status_counts"] == [
        [_ENTRY_HALTED, _WORKLIST_INPUT_VALUE_COUNT]
    ]
    assert bounded["closed_all_paths_terminate"] is True
    assert bounded["closed_all_paths_halt"] is True
    witnesses = cast(
        "list[dict[str, object]]",
        bounded["terminal_status_witnesses"],
    )
    assert len(witnesses) == 1
    assert witnesses[0]["status"] == _ENTRY_HALTED
    entry_path = cast("list[dict[str, object]]", witnesses[0]["entry_path"])
    assert entry_path[0]["code_pointer"] == 0
    assert entry_path[-1] == witnesses[0]["state"]
    assert bounded["truncated"] is False


def test_cli_rejects_closed_worklist_that_proves_only_rejections(
    tmp_path: Path,
) -> None:
    """Closed worklist rejection proof overrides a shallow accepted prefix."""
    source = tmp_path / "input-crazy.malbolge"
    _ = source.write_bytes(_INPUT_CRAZY_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--transition-limit",
            "1",
            "--worklist-state-limit",
            str(_WORKLIST_COMPLETE_STATE_LIMIT),
            str(source),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    bounded = cast("dict[str, object]", document["bounded_worklist"])
    assert bounded["closed_all_paths_terminate"] is True
    assert bounded["closed_all_paths_halt"] is False
    assert bounded["truncated"] is False


def test_cli_rejects_truncated_worklist_request(tmp_path: Path) -> None:
    """Requested graph exploration cannot succeed after state truncation."""
    source = tmp_path / "input-halt-truncated.malbolge"
    _ = source.write_bytes(_INPUT_HALT_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--worklist-state-limit",
            str(_WORKLIST_TRUNCATED_STATE_LIMIT),
            str(source),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["schema"] == _SCHEMA
    bounded = cast("dict[str, object]", document["bounded_worklist"])
    assert bounded["closed_terminal_status_counts"] is None
    assert bounded["closed_all_paths_terminate"] is None
    assert bounded["closed_all_paths_halt"] is None
    witness = cast("dict[str, object]", bounded["frontier_state_witness"])
    path = cast("list[dict[str, object]]", bounded["frontier_entry_path"])
    assert witness["accumulator"] == 0
    assert witness["eof_seen"] is False
    assert path[-1] == witness
    assert bounded["truncated"] is True


def test_cli_rejects_maximum_truncated_worklist(tmp_path: Path) -> None:
    """CLI maximum publishes exact frontier evidence and exits nonzero."""
    source = tmp_path / "maximum-truncated.malbolge"
    _ = source.write_bytes(_OVER_CAP_INPUT_CYCLE_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--worklist-state-limit",
            str(_MAX_WORKLIST_STATE_LIMIT),
            str(source),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    bounded = cast("dict[str, object]", document["bounded_worklist"])
    assert bounded["unique_states"] == _MAX_WORKLIST_STATE_LIMIT
    assert bounded["explored_states"] == _OVER_CAP_EXPLORED_STATES
    assert bounded["frontier_states"] == _WORKLIST_INPUT_VALUE_COUNT
    assert bounded["maximum_first_seen_transition_index"] == (
        _OVER_CAP_MAXIMUM_FIRST_SEEN_TRANSITION
    )
    assert bounded["reachable_cycle_detected"] is False
    assert bounded["closed_all_paths_terminate"] is None
    assert bounded["closed_all_paths_halt"] is None
    witness = cast("dict[str, object]", bounded["frontier_state_witness"])
    path = cast("list[dict[str, object]]", bounded["frontier_entry_path"])
    assert witness["accumulator"] == _OVER_CAP_FRONTIER_ACCUMULATOR
    assert witness["eof_seen"] is False
    assert path[-1] == witness
    pointers = tuple(
        (state["code_pointer"], state["data_pointer"]) for state in path
    )
    assert pointers == _OVER_CAP_FRONTIER_POINTER_PATH
    assert bounded["truncated"] is True
    limits = cast("list[str]", document["analysis_limits"])
    assert _MAX_WORKLIST_TRUNCATED_LIMIT in limits


def test_cli_accepts_explicit_extended_transition_limit(tmp_path: Path) -> None:
    """CLI can request exact reachability beyond the default sixteen steps."""
    source = tmp_path / "extended-prefix.malbolge"
    payload = _sequential_output_source(_EXTENDED_TRANSITION_LIMIT)
    _ = source.write_bytes(payload)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--transition-limit",
            str(_EXTENDED_TRANSITION_LIMIT),
            str(source),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["bounded_transition_limit"] == _EXTENDED_TRANSITION_LIMIT
    transitions = cast(
        "list[dict[str, object]]",
        document["bounded_continuations"],
    )
    assert len(transitions) == _EXTENDED_TRANSITION_LIMIT - 1
    assert transitions[-1]["fetched_address"] == _EXTENDED_TRANSITION_LIMIT - 1


def test_cli_rejects_worklist_limit_above_safety_ceiling() -> None:
    """CLI rejects a worklist budget above the reviewed safety ceiling."""
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--worklist-state-limit",
            str(_INVALID_WORKLIST_STATE_LIMIT),
            str(_FIXTURE),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stdout
    assert completed.stderr.strip() == _WORKLIST_LIMIT_ERROR


def test_cli_rejects_transition_limit_above_safety_ceiling() -> None:
    """CLI rejects a requested depth above the reviewed safety ceiling."""
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--transition-limit",
            str(_INVALID_TOTAL_TRANSITION_LIMIT),
            str(_FIXTURE),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stdout
    assert completed.stderr.strip() == _TRANSITION_LIMIT_ERROR


def test_cli_rejects_statically_invalid_entry_transition(
    tmp_path: Path,
) -> None:
    """A loadable image cannot pass when entry analysis proves rejection."""
    source = tmp_path / "invalid-entry.malbolge"
    _ = source.write_bytes(bytes((39, 38)))
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["admitted_initial_image"] is True
    transition = cast("dict[str, object]", document["entry_transition"])
    assert transition["status"] == _ENTRY_INVALID_ENCRYPTION


def test_cli_rejects_provable_third_step_fixed_fetch_cycle(
    tmp_path: Path,
) -> None:
    """CLI rejects a bounded third fetch proven unable to advance."""
    source = tmp_path / "third-step-stuck.malbolge"
    _ = source.write_bytes(_THIRD_STUCK_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["admitted_initial_image"] is True
    transition = cast("dict[str, object]", document["third_transition"])
    assert transition["status"] == _THIRD_STUCK
    assert transition["provable_cycle"] is True


def test_cli_rejects_provable_fourth_step_fixed_fetch_cycle(
    tmp_path: Path,
) -> None:
    """CLI rejects a bounded fourth fetch proven unable to advance."""
    source = tmp_path / "fourth-step-stuck.malbolge"
    _ = source.write_bytes(_FOURTH_STUCK_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    transition = cast("dict[str, object]", document["fourth_transition"])
    assert transition["status"] == _THIRD_STUCK
    assert transition["provable_cycle"] is True


def test_cli_rejects_provable_fifth_step_fixed_fetch_cycle(
    tmp_path: Path,
) -> None:
    """CLI rejects a bounded fifth fetch proven unable to advance."""
    source = tmp_path / "fifth-step-stuck.malbolge"
    _ = source.write_bytes(_FIFTH_TRANSFER_SOURCE)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    transition = cast("dict[str, object]", document["fifth_transition"])
    assert transition["status"] == _THIRD_STUCK
    assert transition["fetched_address"] == _FIFTH_FETCH_ADDRESS
    assert transition["provable_cycle"] is True


def test_cli_rejects_statically_invalid_second_transition(
    tmp_path: Path,
) -> None:
    """CLI failure includes a reachable second-step rejection in JSON."""
    source = tmp_path / "invalid-second-step.malbolge"
    _ = source.write_bytes(bytes((
        _source_byte_for_decode(ord("<"), 0),
        _source_byte_for_decode(ord("*"), 1),
    )))
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["admitted_initial_image"] is True
    transition = cast("dict[str, object]", document["second_transition"])
    assert transition["status"] == _ENTRY_INVALID_ENCRYPTION


def test_cli_rejected_image_returns_failure_with_report(
    tmp_path: Path,
) -> None:
    """Semantic rejection is visible in JSON and process status."""
    source = tmp_path / "invalid.malbolge"
    _ = source.write_bytes(bytes((_GRAPHICAL_INVALID_BYTE, 38)))
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["admitted_initial_image"] is False


def test_cli_rejects_missing_source(tmp_path: Path) -> None:
    """Filesystem failures remain outside the semantic report."""
    missing = tmp_path / "missing.malbolge"
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(missing)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode != 0
    assert _MISSING_SOURCE_MESSAGE in completed.stderr
