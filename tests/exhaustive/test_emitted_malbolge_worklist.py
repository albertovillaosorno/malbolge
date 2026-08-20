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
#   - Exact bounded-worklist evidence for input-dependent classic reachability.
# - Must-Not:
#   - Claim safety after truncation or permit ordinary input after observed EOF.
# - Allows:
#   - Inputs: small admitted source fixtures and explicit state budgets.
#   - Outputs: deterministic closure, truncation, and EOF-domain assertions.
#   - Side effects: none.
# - Split-When:
#   - Public analyzer report integration gains independent differential
#     evidence.
# - Merge-When:
#   - Worklist implementation tests own the same exact bounded graph contract.
# - Summary:
#   - Tests deterministic exact-state worklist exploration.
# - Description:
#   - Covers all byte/EOF branches, fail-closed caps, and sticky EOF semantics.
# - Usage:
#   - Collected by repository pytest validation.
# - Defaults:
#   - The largest fixture closes after 258 unique exact states.
#

"""Exact bounded-worklist tests for emitted Malbolge reachability."""

# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections import deque
from collections.abc import Callable
import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

type _WorklistStateKey = tuple[
    int,
    int,
    int,
    tuple[tuple[int, int], ...],
    bool,
]


type _WorklistStateEvidence = tuple[
    int,
    tuple[_WorklistStateKey, ...],
    set[_WorklistStateKey],
    int,
]


_INPUT_HALT_SOURCE = (117, 80)
_ENTRY_SELF_ENCRYPTION_OUTPUT = 111
_INPUT_CRAZY_SOURCE = (117, 61)
_DOUBLE_INPUT_HALT_SOURCE = (117, 116, 79)
_DOUBLE_INPUT_FIXED_CYCLE_SOURCE = (117, 116)
_LONG_INPUT_CYCLE_SOURCE = (117, 39, 38, 37)
_LONG_INPUT_CYCLE_STATE_LIMIT = 1_029
_LONG_INPUT_CYCLE_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 29_490),
    (4, 29_489),
)
_DEEP_INPUT_CYCLE_SOURCE = tuple(b"u'&%$")
_DEEP_INPUT_CYCLE_STATE_LIMIT = 1_286
_DEEP_INPUT_CYCLE_POINTER_PATH = (
    (0, 0),
    (1, 1),
    (2, 40),
    (3, 37),
    (4, 29_489),
    (5, 29_489),
)
_NEAR_CAP_INPUT_CYCLE_SOURCE = tuple(b"u'&%$#\"!~}|{zyx")
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
_MERGED_INPUT_CYCLE_SOURCE = tuple(
    b"".join(
        (
            b"u'%%$#\"!~}|{zyxwvutsrqponmlkjihgfedcba`_^]\\",
            b"[ZYXWVUTSRQPONMLKJIHGFED",
        )
    )
)
_MERGED_INPUT_CYCLE_STATE_LIMIT = 591
_MERGED_INPUT_CYCLE_PATH_LENGTH = 41
_MERGED_INPUT_CYCLE_REPEATED_EDGES = 257
_MERGED_INPUT_CYCLE_STATE_MERGES = 255
_MERGED_INPUT_CYCLE_CYCLE_CLOSING_REPEATS = (
    _MERGED_INPUT_CYCLE_REPEATED_EDGES - _MERGED_INPUT_CYCLE_STATE_MERGES
)
_MERGED_INPUT_CYCLE_MERGE_SOURCE_POINTER = (2, 40)
_MERGED_INPUT_CYCLE_MERGE_TARGET_POINTER = (3, 41)
_DOUBLE_JUMP_MERGED_CYCLE_SOURCE = tuple(
    b"".join(
        (
            b"u'&$@?>=<;:9876543210/.-,+*)('&%$#\"!~}|{zyxw",
            b"vutsrqponmlkjihgfedcba`_^]\\[ZYXWVUTSRQPONMLK",
            b"JIHGFEDCBA@?>=<;:9876543210/.-,+*)(",
        )
    )
)
_DOUBLE_JUMP_MERGED_CYCLE_STATE_LIMIT = 1_012
_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH = 124
_DOUBLE_JUMP_MERGED_CYCLE_ADDRESS = 123
_DOUBLE_JUMP_MERGED_CYCLE_INITIAL_VALUE = 29_486
_DOUBLE_JUMP_MERGED_CYCLE_EVOLVED_VALUE = 49_194
_DOUBLE_JUMP_MERGED_CYCLE_WRITER_TRANSITION = 4
_OVER_CAP_INPUT_CYCLE_SOURCE = tuple(b"u'&%$#\"!~}|{zyxw")
_MAX_WORKLIST_STATE_LIMIT = 4_096
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
_OVER_CAP_FRONTIER_LOADED_CODE_POINTER = 15
_OVER_CAP_FRONTIER_RECURRENCE_CODE_POINTER = 16
_OVER_CAP_FRONTIER_LOADED_STATE_COUNT = 16
_OVER_CAP_FRONTIER_RECURRENCE_STATE_COUNT = 241
_EVOLVED_FETCH_SOURCE = tuple(b"(&&$^")
_EVOLVED_FETCH_STATE_LIMIT = 6
_EVOLVED_FETCH_ADDRESS = 95
_EVOLVED_FETCH_INITIAL_VALUE = 29_430
_EVOLVED_FETCH_OBSERVED_VALUE = 9_810
_EVOLVED_FETCH_ORIGIN_TRANSITION = 4
_EVOLVED_FETCH_INITIAL_VALUE_FETCH_COUNT = _EVOLVED_FETCH_STATE_LIMIT - 1
_EVOLVED_FETCH_INITIAL_VALUE_FETCH_ADDRESSES = (0, 1, 2, 3, 4)
_EVOLVED_FETCH_DATA_READ_COUNT = 5
_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_COUNT = 5
_EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_ADDRESSES = (0, 41, 42, 95, 96)
_EVOLVED_FETCH_POINTER_PATH = (
    (0, 0),
    (1, 41),
    (2, 42),
    (3, 95),
    (4, 96),
    (95, 97),
)
_EVOLVED_DATA_READ_SOURCE = tuple(b"(&&%M")
_EVOLVED_DATA_READ_STATE_LIMIT = 5
_EVOLVED_DATA_READ_ADDRESS = 41
_EVOLVED_DATA_READ_INITIAL_VALUE = 29_558
_EVOLVED_DATA_READ_OBSERVED_VALUE = 49_218
_EVOLVED_DATA_READ_ORIGIN_TRANSITION = 2
_EVOLVED_DATA_READ_INITIAL_VALUE_FETCH_COUNT = _EVOLVED_DATA_READ_STATE_LIMIT
_EVOLVED_DATA_READ_INITIAL_VALUE_FETCH_ADDRESSES = (0, 1, 2, 3, 4)
_EVOLVED_DATA_READ_TOTAL_DATA_READ_COUNT = 4
_EVOLVED_DATA_READ_INITIAL_VALUE_DATA_READ_COUNT = 3
_EVOLVED_DATA_READ_INITIAL_VALUE_DATA_READ_ADDRESSES = (0, 41, 42)
_EVOLVED_DATA_READ_POINTER_PATH = ((0, 0), (1, 41), (2, 42), (3, 41))
_WRITER_DATA_WRITE = "data-write"
_RECURRENCE_READ_SOURCE = tuple(b"('")
_RECURRENCE_STATE_LIMIT = 16
_RECURRENCE_HIGHEST_ADDRESS = 41
_RECURRENCE_MINIMUM_WORDS = 42
_RECURRENCE_ACCESSES = (0, 1, 2, 41)
_FULL_STATE_LIMIT = 258
_TRUNCATED_STATE_LIMIT = _FULL_STATE_LIMIT - 1
_TINY_STATE_LIMIT = 2
_DOUBLE_INPUT_UNIQUE_STATES = 515
_DOUBLE_INPUT_REPEATED_EDGES = 65_536
_DOUBLE_INPUT_CYCLE_EDGES = 65_793
_FIXED_CYCLE_POINTER = 2
_FIXED_CYCLE_ENTRY_PATH_STATES = 3
_FIXED_CYCLE_MEMORY_OVERRIDES = ((0, 111), (1, 69))
_FIXED_CYCLE_NON_GRAPHICAL_VALUE = 29_412
_INPUT_VALUE_COUNT = 257
_INVALID_ENCRYPTION_STATUS = "rejected-invalid-self-encryption"
_HALTED_STATUS = "halted"
_BYTE_VALUE_COUNT = 256
_DOUBLE_INPUT_BRANCH_POINTS = 1 + _BYTE_VALUE_COUNT
_EOF_ACCUMULATOR = 59_048
_WRAP_ADDRESS = 59_048
_WRAP_SOURCE_VALUE = 52
_WRAP_STATE_LIMIT = 1
_ENTRY_WRAP_WITNESS_STATE_LIMIT = 1_544
_ENTRY_WRAP_EXPLORED_STATES = 1_288
_ENTRY_WRAP_SOURCE = tuple(b"u'<%$#>=<;:987654321NN")
_ENTRY_WRAP_POINTER_PATH = ((0, 0), (1, 1), (2, 40), (3, 41), (4, 79), (5, 40))
_ENTRY_WRAP_RESULT_CODE_POINTER = 6
_ENTRY_MUTATION_POINTER_PATH = ((0, 0), (1, 1), (2, 40))
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
_ENTRY_NOOP_POINTER_PATH = ((0, 0), (1, 1), (2, 40))
_ENTRY_MUTATION_RESULT_DOMAIN_COUNT = 256
_ENTRY_MUTATION_RESULT_DOMAIN_MINIMUM = 29_269
_ENTRY_MUTATION_RESULT_DOMAIN_MAXIMUM = 59_048
_ENTRY_DATA_READ_DOMAIN_COUNT = 257
_INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT = 58
_INPUT_CRAZY_ENCRYPTION_DOMAIN_MINIMUM = 32
_INPUT_CRAZY_ENCRYPTION_DOMAIN_MAXIMUM = 29_555
_INPUT_CRAZY_ENCRYPTION_INPUT_COUNT = 258
_INPUT_CRAZY_INITIAL_ENCRYPTION_INPUT_COUNT = 1
_INPUT_CRAZY_CHANGED_ENCRYPTION_INPUT_COUNT = 257
_WRAP_WRITE_TRANSITION = 3
_SECOND_TRANSITION = 2
_GRAPH_KEY_A: _WorklistStateKey = (0, 0, 0, (), False)
_GRAPH_KEY_B: _WorklistStateKey = (1, 0, 0, (), False)
_GRAPH_KEY_C: _WorklistStateKey = (2, 0, 0, (), False)
_GRAPH_KEY_D: _WorklistStateKey = (3, 0, 0, (), False)
_SCC_COMPONENT_COUNT = 3
_SCC_CYCLIC_COMPONENT_COUNT = 2
_SCC_CYCLIC_STATE_COUNT = 3
_SCC_LARGEST_CYCLIC_COMPONENT_STATES = 2
_ESCAPING_CYCLIC_COMPONENT_ENTRY_COUNTS = (1, 3)
_ESCAPING_RECURRENT_COMPONENT_ENTRY_COUNTS = (3,)
_STATE_LIMIT_MESSAGE = (
    "worklist state limit must be an exact integer from 1 through 4096"
)
_ADMISSION_MESSAGE = "worklist source is not an admitted classic image"
_ROOT = Path(__file__).resolve().parents[2]
_WORKLIST_MODULE = _ROOT / "verifier" / "emitted_malbolge_worklist.py"


class _Snapshot(Protocol):
    code_pointer: int
    data_pointer: int
    accumulator: int | None
    memory_overrides: tuple[tuple[int, int], ...]


type _SnapshotFactory = Callable[
    [
        int,
        int,
        int,
        int | None,
        tuple[tuple[int, int], ...],
    ],
    _Snapshot,
]


class _Transition(Protocol):
    pointer_wraps: bool
    result_data_pointer: int | None


class _SnapshotStep(Protocol):
    transition: _Transition


class _ClassicModule(Protocol):
    PROFILE_MEMORY_WORDS: int

    def crazy(self, data: int, accumulator: int) -> int: ...


class _PrefixModule(Protocol):
    StateSnapshot: _SnapshotFactory

    def analyze_state_snapshot(
        self,
        words: tuple[int, ...],
        snapshot: _Snapshot,
    ) -> _SnapshotStep: ...


class _ReachabilityNode(Protocol):
    snapshot: _Snapshot
    eof_seen: bool


class _ReachabilityNodeFactory(Protocol):
    def __call__(
        self,
        *,
        snapshot: _Snapshot,
        eof_seen: bool,
    ) -> _ReachabilityNode: ...


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


type _WrapCounts = tuple[int, int, int, int]
type _WrapWitnesses = tuple[
    _WorklistWrapWitness | None,
    _WorklistWrapWitness | None,
    _WorklistWrapWitness | None,
    _WorklistWrapWitness | None,
]


type _WriteCounts = tuple[int, int, int, int, int]
type _WriteAddressSets = tuple[
    set[int],
    set[int],
    set[int],
    set[int],
    set[int],
]


type _CommittedWriteStateSets = tuple[
    set[_WorklistStateKey],
    set[_WorklistStateKey],
    set[_WorklistStateKey],
]


class _WorklistWrapTransitionSignature(Protocol):
    source_code_pointer: int
    source_data_pointer: int
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool


class _WorklistTerminalStateSet(Protocol):
    status: str
    states: tuple[_WorklistCycleState, ...]


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


class _WorklistCodeDataAliasObservation(Protocol):
    state: _WorklistCycleState
    address: int
    memory_value: int


class _WorklistCodeDataAliasWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    memory_value: int


class _WorklistNonGraphicalFetchObservation(Protocol):
    state: _WorklistCycleState
    address: int
    value: int


class _WorklistNonGraphicalFetchWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    value: int


class _WorklistPlannedDataWriteObservation(Protocol):
    state: _WorklistCycleState
    address: int
    value: int


class _WorklistSelfEncryptionObservation(Protocol):
    state: _WorklistCycleState
    address: int
    input_value: int
    output_value: int
    data_write_aliases_encryption: bool


class _WorklistChangedEncryptionInputObservation(Protocol):
    state: _WorklistCycleState
    address: int
    initial_value: int
    observed_value: int


class _WorklistInitialValueObservation(Protocol):
    state: _WorklistCycleState
    address: int
    value: int


class _WorklistEvolvedReadObservation(Protocol):
    state: _WorklistCycleState
    address: int
    initial_value: int
    observed_value: int


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


class _WorklistDataWriteNoopObservation(Protocol):
    state: _WorklistCycleState
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


class _WorklistDataWriteNoopWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


class _WorklistDataMutationObservation(Protocol):
    state: _WorklistCycleState
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
    input_branch_states: tuple[_WorklistCycleState, ...]
    terminal_status_counts: tuple[tuple[str, int], ...]
    terminal_status_state_sets: tuple[_WorklistTerminalStateSet, ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[_WorklistTerminalWitness, ...]
    explored_code_pointer_addresses: tuple[int, ...]
    explored_data_pointer_addresses: tuple[int, ...]
    explored_code_data_alias_transition_count: int
    explored_code_data_alias_addresses: tuple[int, ...]
    explored_code_data_alias_observations: tuple[
        _WorklistCodeDataAliasObservation, ...
    ]
    explored_code_data_alias_witnesses: tuple[
        _WorklistCodeDataAliasWitness, ...
    ]
    explored_committed_write_count: int
    explored_committed_write_addresses: tuple[int, ...]
    explored_planned_data_write_transition_count: int
    explored_planned_data_write_addresses: tuple[int, ...]
    explored_planned_data_write_value_domains: tuple[_WorklistValueDomain, ...]
    explored_planned_data_write_observations: tuple[
        _WorklistPlannedDataWriteObservation, ...
    ]
    explored_committed_data_write_transition_count: int
    explored_committed_data_write_addresses: tuple[int, ...]
    explored_committed_data_write_noop_transition_count: int
    explored_committed_data_write_noop_addresses: tuple[int, ...]
    explored_committed_data_write_noop_observations: tuple[
        _WorklistDataWriteNoopObservation, ...
    ]
    explored_self_encryption_transition_count: int
    explored_self_encryption_addresses: tuple[int, ...]
    explored_self_encryption_observations: tuple[
        _WorklistSelfEncryptionObservation, ...
    ]
    explored_effective_data_mutation_transition_count: int
    explored_effective_data_mutation_addresses: tuple[int, ...]
    explored_effective_data_mutation_value_domains: tuple[
        _WorklistDataMutationValueDomain, ...
    ]
    explored_effective_data_mutation_observations: tuple[
        _WorklistDataMutationObservation, ...
    ]
    explored_fetch_value_domains: tuple[_WorklistValueDomain, ...]
    explored_non_graphical_fetch_transition_count: int
    explored_non_graphical_fetch_addresses: tuple[int, ...]
    explored_non_graphical_fetch_value_domains: tuple[_WorklistValueDomain, ...]
    explored_non_graphical_fetch_observations: tuple[
        _WorklistNonGraphicalFetchObservation, ...
    ]
    explored_non_graphical_fetch_witness: (
        _WorklistNonGraphicalFetchWitness | None
    )
    explored_data_read_value_domains: tuple[_WorklistValueDomain, ...]
    explored_encryption_input_value_domains: tuple[_WorklistValueDomain, ...]
    explored_encryption_input_transition_count: int
    explored_initial_value_encryption_input_transition_count: int
    explored_initial_value_encryption_input_addresses: tuple[int, ...]
    explored_initial_value_encryption_input_observations: tuple[
        _WorklistInitialValueObservation, ...
    ]
    explored_changed_from_initial_encryption_input_transition_count: int
    explored_changed_from_initial_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_changed_from_initial_encryption_input_observations: tuple[
        _WorklistChangedEncryptionInputObservation, ...
    ]
    explored_committed_data_write_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_self_encryption_output_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_initial_value_fetch_transition_count: int
    explored_initial_value_fetch_addresses: tuple[int, ...]
    explored_initial_value_fetch_observations: tuple[
        _WorklistInitialValueObservation, ...
    ]
    explored_evolved_fetch_transition_count: int
    explored_evolved_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_value_domains: tuple[_WorklistValueDomain, ...]
    explored_evolved_fetch_observations: tuple[
        _WorklistEvolvedReadObservation, ...
    ]
    explored_data_read_transition_count: int
    explored_initial_value_data_read_transition_count: int
    explored_initial_value_data_read_addresses: tuple[int, ...]
    explored_initial_value_data_read_observations: tuple[
        _WorklistInitialValueObservation, ...
    ]
    explored_evolved_data_read_transition_count: int
    explored_evolved_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_value_domains: tuple[_WorklistValueDomain, ...]
    explored_evolved_data_read_observations: tuple[
        _WorklistEvolvedReadObservation, ...
    ]
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
    frontier_state_set: tuple[_WorklistCycleState, ...]
    frontier_state_witness: _WorklistCycleState | None
    frontier_entry_path: tuple[_WorklistCycleState, ...] | None
    truncated: bool


class _StrongComponentSummary(Protocol):
    component_count: int
    cyclic_component_count: int
    cyclic_state_count: int
    largest_cyclic_component_states: int
    cyclic_components: tuple[tuple[_WorklistStateKey, ...], ...]
    cyclic_sink_components: tuple[tuple[_WorklistStateKey, ...], ...]


class _Explorer(Protocol):
    def run(self) -> _WorklistAnalysis:
        """Return one exact bounded exploration summary."""
        ...


type _ExplorerFactory = Callable[
    [
        tuple[int, ...],
        int,
        deque[_ReachabilityNode],
        set[_WorklistStateKey],
        dict[_WorklistStateKey, set[_WorklistStateKey]],
        dict[str, int],
        set[int],
    ],
    _Explorer,
]


class _WorklistModule(Protocol):
    classic: _ClassicModule
    prefix_transfer: _PrefixModule
    _ReachabilityNode: _ReachabilityNodeFactory
    _Explorer: _ExplorerFactory

    def analyze_reachability(
        self,
        words: tuple[int, ...],
        *,
        maximum_states: int,
    ) -> _WorklistAnalysis:
        """Return exact bounded reachability evidence."""
        ...

    def _input_successors(
        self,
        snapshot: _Snapshot,
        *,
        eof_seen: bool,
    ) -> tuple[_ReachabilityNode, ...]: ...

    def _successors(
        self,
        node: _ReachabilityNode,
        step: _SnapshotStep,
    ) -> tuple[_ReachabilityNode, ...]: ...

    def _assert_known_graph_integrity(
        self,
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
        nodes: set[_WorklistStateKey],
    ) -> None: ...

    def _assert_worklist_state_partition(
        self,
        evidence: _WorklistStateEvidence,
        *,
        truncated: bool,
    ) -> None: ...

    def _known_graph_strong_components(
        self,
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
        nodes: set[_WorklistStateKey],
    ) -> tuple[tuple[_WorklistStateKey, ...], ...]: ...

    def _known_graph_strong_component_summary(
        self,
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
        nodes: set[_WorklistStateKey],
    ) -> _StrongComponentSummary: ...

    def _known_graph_has_cycle(
        self,
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
        nodes: set[_WorklistStateKey],
    ) -> bool: ...

    def _known_graph_cycle_witness(
        self,
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
        nodes: set[_WorklistStateKey],
    ) -> tuple[_WorklistStateKey, ...]: ...

    def _assert_observed_address_summary(
        self,
        transition_count: int,
        addresses: set[int],
        *,
        label: str,
    ) -> None: ...

    def _assert_observed_value_domains(
        self,
        transition_count: int,
        addresses: set[int],
        values: dict[int, set[int]],
        *,
        label: str,
    ) -> None: ...

    def _assert_planned_data_write_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[_WorklistStateKey, tuple[int, int]],
            set[_WorklistStateKey],
        ],
    ) -> None: ...

    def _assert_committed_data_write_state_partition(
        self,
        evidence: tuple[
            dict[_WorklistStateKey, tuple[int, int]],
            dict[_WorklistStateKey, tuple[int, int, int, int, bool]],
            dict[_WorklistStateKey, tuple[int, int, int, int, bool]],
            dict[int, set[int]],
        ],
    ) -> None: ...

    def _assert_observation_state_partition(
        self,
        initial_states: set[_WorklistStateKey],
        changed_states: set[_WorklistStateKey],
        *,
        label: str,
    ) -> None: ...

    def _assert_initial_value_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[_WorklistStateKey, tuple[int, int]],
            set[_WorklistStateKey],
        ],
        initial_memory: tuple[int, ...],
        *,
        label: str,
    ) -> None: ...

    def _assert_changed_encryption_input_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[_WorklistStateKey, tuple[int, int]],
            set[_WorklistStateKey],
        ],
        initial_memory: tuple[int, ...],
    ) -> None: ...

    def _assert_evolved_read_observation_evidence(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[_WorklistStateKey, tuple[int, int]],
            set[_WorklistStateKey],
        ],
        initial_memory: tuple[int, ...],
        *,
        label: str,
    ) -> None: ...

    def _assert_evolved_read_witness(
        self,
        evidence: tuple[
            int,
            dict[int, set[int]],
            _WorklistEvolvedReadWitness | None,
        ],
        *,
        label: str,
        require_witness: bool,
    ) -> None: ...

    def _assert_code_data_alias_observations(
        self,
        transition_count: int,
        addresses: set[int],
        observations: dict[_WorklistStateKey, int],
        *,
        seen: set[_WorklistStateKey],
    ) -> None: ...

    def _assert_input_branch_evidence(
        self,
        branch_count: int,
        branch_states: set[_WorklistStateKey],
        seen: set[_WorklistStateKey],
    ) -> None: ...

    def _assert_frontier_evidence(
        self,
        frontier_states: int,
        frontier_state_keys: tuple[_WorklistStateKey, ...],
        frontier_path: tuple[_WorklistStateKey, ...] | None,
        *,
        truncated: bool,
    ) -> None: ...

    def _assert_terminal_evidence(
        self,
        counts: dict[str, int],
        terminal_states: dict[str, set[_WorklistStateKey]],
        seen: set[_WorklistStateKey],
    ) -> None: ...

    def _assert_terminal_graph_endpoints(
        self,
        terminal_states: dict[str, set[_WorklistStateKey]],
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
    ) -> None: ...

    def _assert_self_encryption_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[_WorklistStateKey, tuple[int, int, int, bool]],
            set[_WorklistStateKey],
        ],
    ) -> None: ...

    def _assert_data_write_noop_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[_WorklistStateKey, tuple[int, int, int, int, bool]],
            set[_WorklistStateKey],
        ],
    ) -> None: ...

    def _assert_data_mutation_observations(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[int, set[int]],
            dict[_WorklistStateKey, tuple[int, int, int, int, bool]],
            set[_WorklistStateKey],
        ],
    ) -> None: ...

    def _assert_data_mutation_domains(
        self,
        transition_count: int,
        addresses: set[int],
        *,
        previous_values: dict[int, set[int]],
        result_values: dict[int, set[int]],
    ) -> None: ...

    def _assert_committed_write_terminal_partition(
        self,
        state_sets: _CommittedWriteStateSets,
        terminal_states: dict[str, set[_WorklistStateKey]],
    ) -> None: ...

    def _assert_committed_write_count_partition(
        self,
        counts: _WriteCounts,
    ) -> None: ...

    def _assert_committed_write_address_partition(
        self,
        address_sets: _WriteAddressSets,
    ) -> None: ...

    def _assert_non_graphical_fetch_domains(
        self,
        transition_count: int,
        addresses: set[int],
        values: dict[int, set[int]],
    ) -> None: ...

    def _assert_non_graphical_fetch_observation_projection(
        self,
        evidence: tuple[
            int,
            set[int],
            dict[int, set[int]],
            dict[_WorklistStateKey, int],
        ],
        *,
        seen: set[_WorklistStateKey],
    ) -> None: ...

    def _assert_non_graphical_fetch_observation_edges(
        self,
        observations: dict[_WorklistStateKey, int],
        edges: dict[_WorklistStateKey, set[_WorklistStateKey]],
    ) -> None: ...

    def _assert_non_graphical_fetch_witness(
        self,
        values: dict[int, set[int]],
        witness: _WorklistNonGraphicalFetchWitness | None,
    ) -> None: ...

    def _assert_wrap_evidence_invariants(
        self,
        counts: _WrapCounts,
        witnesses: _WrapWitnesses,
    ) -> None: ...

    def _node_key(self, node: _ReachabilityNode) -> _WorklistStateKey: ...


def _load_worklist() -> _WorklistModule:
    spec = importlib.util.spec_from_file_location(
        "emitted_malbolge_worklist_primary_test",
        _WORKLIST_MODULE,
    )
    if spec is None or spec.loader is None:
        message = "worklist verifier module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_WORKLIST_MODULE.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_WorklistModule", cast("object", module))


worklist = _load_worklist()
prefix_transfer = worklist.prefix_transfer


def _assert_no_closed_recurrence(result: _WorklistAnalysis) -> None:
    assert result.closed_recurrent_component_count == 0
    assert result.closed_recurrent_state_count == 0
    assert result.closed_recurrent_largest_component_states == 0
    assert result.closed_recurrent_components == ()
    assert (
        result.closed_recurrent_component_minimum_entry_path_state_counts
        == ()
    )
    assert result.closed_recurrent_cycle_witness == ()
    assert result.closed_recurrent_entry_path == ()


def _assert_fixed_cycle_closed_recurrence(result: _WorklistAnalysis) -> None:
    assert result.closed_recurrent_component_count == _INPUT_VALUE_COUNT
    assert result.closed_recurrent_state_count == _INPUT_VALUE_COUNT
    assert result.closed_recurrent_largest_component_states == 1
    components = result.closed_recurrent_components
    assert components is not None
    assert len(components) == _INPUT_VALUE_COUNT
    assert all(len(component) == 1 for component in components)
    witness = result.closed_recurrent_cycle_witness
    assert witness is not None
    assert len(witness) == 1
    state = witness[0]
    assert state.code_pointer == _FIXED_CYCLE_POINTER
    assert state.data_pointer == _FIXED_CYCLE_POINTER
    assert state.memory_overrides == _FIXED_CYCLE_MEMORY_OVERRIDES
    path = result.closed_recurrent_entry_path
    assert path is not None
    _assert_fixed_cycle_entry_path(path, state)


def _assert_initial_input_branch_state(result: _WorklistAnalysis) -> None:
    assert result.input_branch_points == 1
    assert len(result.input_branch_states) == 1
    branch = result.input_branch_states[0]
    assert (branch.code_pointer, branch.data_pointer, branch.accumulator) == (
        0,
        0,
        0,
    )
    assert branch.memory_overrides == ()
    assert not branch.eof_seen


def test_input_halt_worklist_closes_all_byte_and_eof_states() -> None:
    """One input then halt closes exactly 256 byte states plus EOF."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    assert result.state_limit == _FULL_STATE_LIMIT
    assert result.unique_states == _FULL_STATE_LIMIT
    assert result.explored_states == _FULL_STATE_LIMIT
    assert result.repeated_state_edges == 0
    assert not result.reachable_cycle_detected
    assert result.reachable_cycle_witness == ()
    assert result.known_graph_strong_component_count == _FULL_STATE_LIMIT
    assert result.known_graph_cyclic_component_count == 0
    assert result.known_graph_cyclic_state_count == 0
    assert result.known_graph_largest_cyclic_component_states == 0
    assert result.known_graph_cyclic_components == ()
    _assert_no_closed_recurrence(result)
    _assert_initial_input_branch_state(result)
    assert result.terminal_status_counts == (("halted", _INPUT_VALUE_COUNT),)
    assert result.closed_terminal_status_counts == ((
        "halted",
        _INPUT_VALUE_COUNT,
    ),)
    assert result.closed_all_paths_terminate is True
    assert result.closed_all_paths_halt is True
    _assert_input_halt_terminal_state_set(result)
    assert result.maximum_first_seen_transition_index == _SECOND_TRANSITION
    assert result.frontier_states == 0
    assert result.frontier_state_set == ()
    assert not result.truncated


def _domain_values(
    domains: tuple[_WorklistValueDomain, ...],
    address: int,
) -> tuple[int, ...]:
    matches = tuple(
        domain.values for domain in domains if domain.address == address
    )
    assert len(matches) == 1
    return matches[0]


def test_input_halt_reports_exact_read_value_domains() -> None:
    """Closed input reachability publishes exact explored read values."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    fetch_addresses = tuple(
        domain.address for domain in result.explored_fetch_value_domains
    )
    assert fetch_addresses == (0, 1)
    assert _domain_values(result.explored_fetch_value_domains, 0) == (117,)
    assert _domain_values(result.explored_fetch_value_domains, 1) == (80,)
    assert result.explored_data_read_value_domains == ()
    assert result.explored_planned_data_write_transition_count == 0
    assert result.explored_planned_data_write_addresses == ()
    assert result.explored_planned_data_write_value_domains == ()
    assert result.explored_planned_data_write_observations == ()
    assert result.explored_committed_data_write_value_domains == ()
    encryption_outputs = _domain_values(
        result.explored_self_encryption_output_value_domains, 0
    )
    assert encryption_outputs == (111,)
    encryption_values = _domain_values(
        result.explored_encryption_input_value_domains, 0
    )
    assert encryption_values == (117,)
    assert result.explored_encryption_input_transition_count == 1
    assert result.explored_initial_value_encryption_input_transition_count == 1
    assert result.explored_initial_value_encryption_input_addresses == (0,)
    assert (
        result.explored_changed_from_initial_encryption_input_transition_count
        == 0
    )
    assert result.explored_changed_from_initial_encryption_input_addresses == ()
    assert (
        result.explored_changed_from_initial_encryption_input_value_domains
        == ()
    )


def _assert_input_crazy_planned_write_observations(
    result: _WorklistAnalysis,
    values: tuple[int, ...],
) -> None:
    planned = result.explored_planned_data_write_observations
    changed = result.explored_changed_from_initial_encryption_input_observations
    assert len(planned) == _INPUT_VALUE_COUNT
    assert len(changed) == len(planned)
    assert all(item.address == 1 for item in planned)
    assert {item.value for item in planned} == set(values)
    planned_projection = tuple(
        (item.state, item.address, item.value) for item in planned
    )
    changed_projection = tuple(
        (item.state, item.address, item.observed_value) for item in changed
    )
    assert planned_projection == changed_projection
    assert planned[-1].state.eof_seen


def _assert_changed_encryption_input_observations(
    result: _WorklistAnalysis,
    values: tuple[int, ...],
) -> None:
    observations = (
        result.explored_changed_from_initial_encryption_input_observations
    )
    assert len(observations) == _INPUT_CRAZY_CHANGED_ENCRYPTION_INPUT_COUNT
    assert all(item.address == 1 for item in observations)
    assert all(
        item.initial_value == _INPUT_CRAZY_SOURCE[1] for item in observations
    )
    assert all(
        (item.state.code_pointer, item.state.data_pointer) == (1, 1)
        for item in observations
    )
    assert {item.observed_value for item in observations} == set(values)
    assert observations[0].state.accumulator == 0
    assert not observations[0].state.eof_seen
    assert observations[-1].state.accumulator == _EOF_ACCUMULATOR
    assert observations[-1].state.eof_seen


def _assert_input_crazy_initial_value_observations(
    result: _WorklistAnalysis,
) -> None:
    fetches = result.explored_initial_value_fetch_observations
    assert len(fetches) == _FULL_STATE_LIMIT
    assert (fetches[0].address, fetches[0].value) == (0, _INPUT_CRAZY_SOURCE[0])
    assert (
        fetches[0].state.code_pointer,
        fetches[0].state.data_pointer,
    ) == (0, 0)
    remaining_fetches = fetches[1:]
    assert len(remaining_fetches) == _INPUT_VALUE_COUNT
    assert all(item.address == 1 for item in remaining_fetches)
    assert all(
        item.value == _INPUT_CRAZY_SOURCE[1] for item in remaining_fetches
    )
    assert all(
        (item.state.code_pointer, item.state.data_pointer) == (1, 1)
        for item in remaining_fetches
    )
    reads = result.explored_initial_value_data_read_observations
    assert len(reads) == _INPUT_VALUE_COUNT
    assert all(item.address == 1 for item in reads)
    assert all(item.value == _INPUT_CRAZY_SOURCE[1] for item in reads)
    encryption = result.explored_initial_value_encryption_input_observations
    assert len(encryption) == 1
    assert (encryption[0].address, encryption[0].value) == (
        0,
        _INPUT_CRAZY_SOURCE[0],
    )
    assert (
        encryption[0].state.code_pointer,
        encryption[0].state.data_pointer,
    ) == (0, 0)


def test_input_crazy_reports_exact_encryption_input_domain() -> None:
    """Rejected branches retain exact explored encryption-input values."""
    result = worklist.analyze_reachability(
        _INPUT_CRAZY_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    _assert_input_crazy_initial_value_observations(result)
    values = _domain_values(result.explored_encryption_input_value_domains, 1)
    assert len(values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert values[0] == _INPUT_CRAZY_ENCRYPTION_DOMAIN_MINIMUM
    assert values[-1] == _INPUT_CRAZY_ENCRYPTION_DOMAIN_MAXIMUM
    assert (
        result.explored_encryption_input_transition_count
        == _INPUT_CRAZY_ENCRYPTION_INPUT_COUNT
    )
    assert (
        result.explored_initial_value_encryption_input_transition_count
        == _INPUT_CRAZY_INITIAL_ENCRYPTION_INPUT_COUNT
    )
    assert result.explored_initial_value_encryption_input_addresses == (0,)
    assert (
        result.explored_changed_from_initial_encryption_input_transition_count
        == _INPUT_CRAZY_CHANGED_ENCRYPTION_INPUT_COUNT
    )
    assert (
        result.explored_changed_from_initial_encryption_input_addresses == (1,)
    )
    changed = _domain_values(
        result.explored_changed_from_initial_encryption_input_value_domains, 1
    )
    assert changed == values
    _assert_changed_encryption_input_observations(result, values)
    assert (
        result.explored_initial_value_encryption_input_transition_count
        + result.explored_changed_from_initial_encryption_input_transition_count
        == result.explored_encryption_input_transition_count
    )
    assert _domain_values(result.explored_data_read_value_domains, 1) == (61,)
    assert result.explored_planned_data_write_transition_count == (
        _INPUT_VALUE_COUNT
    )
    assert result.explored_planned_data_write_addresses == (1,)
    planned_values = _domain_values(
        result.explored_planned_data_write_value_domains, 1
    )
    assert planned_values == values
    _assert_input_crazy_planned_write_observations(result, values)
    assert result.explored_committed_data_write_value_domains == ()
    encryption_outputs = _domain_values(
        result.explored_self_encryption_output_value_domains, 0
    )
    assert encryption_outputs == (111,)


def _assert_two_word_alias_observations(
    result: _WorklistAnalysis,
    second_value: int,
) -> None:
    observations = result.explored_code_data_alias_observations
    assert len(observations) == _FULL_STATE_LIMIT
    assert observations[0].address == 0
    assert observations[0].memory_value == _INPUT_HALT_SOURCE[0]
    first_state = observations[0].state
    assert (first_state.code_pointer, first_state.data_pointer) == (0, 0)
    remaining = observations[1:]
    assert len(remaining) == _INPUT_VALUE_COUNT
    assert all(item.address == 1 for item in remaining)
    assert all(item.memory_value == second_value for item in remaining)
    assert all(
        (item.state.code_pointer, item.state.data_pointer) == (1, 1)
        for item in remaining
    )
    assert remaining[-1].state.accumulator == _EOF_ACCUMULATOR
    assert remaining[-1].state.eof_seen


def _assert_two_word_alias_witnesses(
    result: _WorklistAnalysis,
    second_value: int,
) -> None:
    assert result.explored_code_data_alias_addresses == (0, 1)
    _assert_two_word_alias_observations(result, second_value)
    witnesses = result.explored_code_data_alias_witnesses
    assert tuple(witness.address for witness in witnesses) == (0, 1)
    assert witnesses[0].memory_value == _INPUT_HALT_SOURCE[0]
    assert len(witnesses[0].entry_path) == 1
    assert witnesses[0].entry_path[-1] == witnesses[0].state
    assert witnesses[1].memory_value == second_value
    assert len(witnesses[1].entry_path) == len(witnesses)
    assert witnesses[1].entry_path[-1] == witnesses[1].state


def _assert_single_committed_self_encryption(
    result: _WorklistAnalysis,
) -> None:
    observations = result.explored_self_encryption_observations
    assert len(observations) == 1
    observation = observations[0]
    assert observation.address == 0
    assert observation.input_value == _INPUT_HALT_SOURCE[0]
    assert observation.output_value == _ENTRY_SELF_ENCRYPTION_OUTPUT
    assert not observation.data_write_aliases_encryption
    state = observation.state
    assert (state.code_pointer, state.data_pointer) == (0, 0)
    assert state.accumulator == 0
    assert not state.eof_seen


def test_input_halt_reports_exact_explored_mutation_footprint() -> None:
    """Closed input reachability publishes exact committed mutation evidence."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    assert result.explored_code_data_alias_transition_count == (
        _FULL_STATE_LIMIT
    )
    _assert_two_word_alias_witnesses(result, _INPUT_HALT_SOURCE[1])
    assert result.explored_committed_write_count == 1
    assert result.explored_committed_write_addresses == (0,)
    assert result.explored_committed_data_write_transition_count == 0
    assert result.explored_committed_data_write_addresses == ()
    assert result.explored_committed_data_write_noop_transition_count == 0
    assert result.explored_committed_data_write_noop_addresses == ()
    assert result.explored_committed_data_write_noop_observations == ()
    assert result.explored_data_write_noop_witness is None
    assert result.explored_self_encryption_transition_count == 1
    assert result.explored_self_encryption_addresses == (0,)
    _assert_single_committed_self_encryption(result)
    assert result.explored_effective_data_mutation_transition_count == 0
    assert result.explored_effective_data_mutation_addresses == ()
    assert result.explored_effective_data_mutation_value_domains == ()
    assert result.explored_effective_data_mutation_observations == ()
    assert result.explored_data_mutation_witness is None


def test_rejected_planned_writes_are_not_reported_as_committed() -> None:
    """Rejected crazy writes remain planned rather than committed evidence."""
    result = worklist.analyze_reachability(
        _INPUT_CRAZY_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    assert result.terminal_status_counts == (
        (_INVALID_ENCRYPTION_STATUS, _INPUT_VALUE_COUNT),
    )
    assert result.explored_code_data_alias_transition_count == (
        _FULL_STATE_LIMIT
    )
    _assert_two_word_alias_witnesses(result, _INPUT_CRAZY_SOURCE[1])
    assert result.explored_committed_write_count == 1
    assert result.explored_committed_write_addresses == (0,)
    assert result.explored_committed_data_write_transition_count == 0
    assert result.explored_committed_data_write_addresses == ()
    assert result.explored_committed_data_write_noop_transition_count == 0
    assert result.explored_committed_data_write_noop_addresses == ()
    assert result.explored_committed_data_write_noop_observations == ()
    assert result.explored_data_write_noop_witness is None
    assert result.explored_self_encryption_transition_count == 1
    assert result.explored_self_encryption_addresses == (0,)
    _assert_single_committed_self_encryption(result)
    assert result.explored_effective_data_mutation_transition_count == 0
    assert result.explored_effective_data_mutation_addresses == ()
    assert result.explored_effective_data_mutation_value_domains == ()
    assert result.explored_data_mutation_witness is None


def test_worklist_memory_requirement_includes_recurrence_reads() -> None:
    """Explored graph memory evidence includes exact recurrence addresses."""
    result = worklist.analyze_reachability(
        _RECURRENCE_READ_SOURCE,
        maximum_states=_RECURRENCE_STATE_LIMIT,
    )
    assert result.explored_minimum_words == _RECURRENCE_MINIMUM_WORDS
    assert (
        result.explored_highest_accessed_address
        == _RECURRENCE_HIGHEST_ADDRESS
    )
    assert result.explored_accessed_addresses == _RECURRENCE_ACCESSES


def _assert_input_crazy_terminal_state_set(result: _WorklistAnalysis) -> None:
    state_sets = result.terminal_status_state_sets
    assert len(state_sets) == 1
    assert state_sets[0].status == _INVALID_ENCRYPTION_STATUS
    states = state_sets[0].states
    assert len(states) == _INPUT_VALUE_COUNT
    assert (states[0].code_pointer, states[0].data_pointer) == (1, 1)
    assert states[0].accumulator == 0
    assert not states[0].eof_seen
    assert states[-1].accumulator == _EOF_ACCUMULATOR
    assert states[-1].eof_seen


def _assert_input_halt_terminal_state_set(result: _WorklistAnalysis) -> None:
    state_sets = result.terminal_status_state_sets
    assert len(state_sets) == 1
    assert state_sets[0].status == _HALTED_STATUS
    states = state_sets[0].states
    assert len(states) == _INPUT_VALUE_COUNT
    assert (states[0].code_pointer, states[0].data_pointer) == (1, 1)
    assert states[0].accumulator == 0
    assert not states[0].eof_seen
    assert states[-1].accumulator == _EOF_ACCUMULATOR
    assert states[-1].eof_seen


def test_input_crazy_worklist_resolves_every_input_branch() -> None:
    """Input-dependent crazy becomes concrete over byte plus EOF states."""
    result = worklist.analyze_reachability(
        _INPUT_CRAZY_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    assert result.unique_states == _FULL_STATE_LIMIT
    assert result.explored_states == _FULL_STATE_LIMIT
    assert result.terminal_status_counts == (
        ("rejected-invalid-self-encryption", _INPUT_VALUE_COUNT),
    )
    assert result.closed_terminal_status_counts == (
        ("rejected-invalid-self-encryption", _INPUT_VALUE_COUNT),
    )
    assert result.closed_all_paths_terminate is True
    assert result.closed_all_paths_halt is False
    _assert_input_crazy_terminal_state_set(result)
    witnesses = result.terminal_status_witnesses
    assert len(witnesses) == 1
    witness = witnesses[0]
    assert witness.status == _INVALID_ENCRYPTION_STATUS
    assert (witness.state.code_pointer, witness.state.data_pointer) == (1, 1)
    assert witness.state.accumulator == 0
    assert witness.state.memory_overrides == ((0, 111),)
    assert not witness.state.eof_seen
    assert witness.entry_path[0].code_pointer == 0
    assert witness.entry_path[-1] == witness.state
    assert not result.truncated


def _assert_truncated_alias_observation(result: _WorklistAnalysis) -> None:
    observations = result.explored_code_data_alias_observations
    assert len(observations) == 1
    alias = observations[0]
    alias_identity = (
        alias.address,
        alias.state.code_pointer,
        alias.state.data_pointer,
    )
    assert alias_identity == (0, 0, 0)
    assert not alias.state.eof_seen


def test_input_worklist_truncates_before_unadmitted_eof_state() -> None:
    """The exact unique-state cap stops before silently dropping a branch."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_TRUNCATED_STATE_LIMIT,
    )
    assert result.unique_states == _TRUNCATED_STATE_LIMIT
    assert result.explored_states == 1
    assert result.input_branch_points == 1
    _assert_truncated_alias_observation(result)
    assert result.terminal_status_counts == ()
    assert result.terminal_status_state_sets == ()
    assert result.closed_terminal_status_counts is None
    assert result.closed_all_paths_terminate is None
    assert result.closed_all_paths_halt is None
    assert result.frontier_states == _INPUT_VALUE_COUNT
    assert len(result.frontier_state_set) == _INPUT_VALUE_COUNT
    assert result.frontier_state_set[0].accumulator == 0
    assert result.frontier_state_set[-1].accumulator == _EOF_ACCUMULATOR
    assert result.frontier_state_set[-1].eof_seen
    assert result.closed_recurrent_component_count is None
    assert result.closed_recurrent_state_count is None
    assert result.closed_recurrent_largest_component_states is None
    assert result.closed_recurrent_cycle_witness is None
    assert result.closed_recurrent_entry_path is None
    assert result.truncated


def test_tiny_cap_counts_all_pending_input_frontier_states() -> None:
    """Truncation counts unadmitted alternatives, not only the first one."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_TINY_STATE_LIMIT,
    )
    assert result.unique_states == _TINY_STATE_LIMIT
    assert result.explored_states == 1
    assert result.maximum_first_seen_transition_index == _SECOND_TRANSITION
    assert result.frontier_states == _INPUT_VALUE_COUNT
    assert len(result.frontier_state_set) == _INPUT_VALUE_COUNT
    assert result.truncated


def test_minimum_cap_reports_exact_first_unexplored_frontier_path() -> None:
    """Truncation identifies one exact frontier state and how it was reached."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=1,
    )
    assert result.frontier_states == _INPUT_VALUE_COUNT
    witness = result.frontier_state_witness
    path = result.frontier_entry_path
    assert witness is not None
    assert path is not None
    assert witness.accumulator == 0
    assert not witness.eof_seen
    assert witness in result.frontier_state_set
    assert path[-1] == witness
    pointers = tuple(
        (state.code_pointer, state.data_pointer) for state in path
    )
    assert pointers == ((0, 0), (1, 1))
    assert result.explored_committed_write_count == 1
    assert result.explored_self_encryption_transition_count == 1
    assert result.terminal_status_counts == ()
    assert result.terminal_status_state_sets == ()
    assert result.truncated


def test_double_input_merges_are_not_silently_discarded() -> None:
    """Only non-EOF input states branch while the merged graph still closes."""
    result = worklist.analyze_reachability(
        _DOUBLE_INPUT_HALT_SOURCE,
        maximum_states=_DOUBLE_INPUT_UNIQUE_STATES,
    )
    assert result.unique_states == _DOUBLE_INPUT_UNIQUE_STATES
    assert result.repeated_state_edges == _DOUBLE_INPUT_REPEATED_EDGES
    assert not result.reachable_cycle_detected
    assert result.reachable_cycle_witness == ()
    assert (
        result.known_graph_strong_component_count
        == _DOUBLE_INPUT_UNIQUE_STATES
    )
    assert result.known_graph_cyclic_component_count == 0
    assert result.known_graph_cyclic_state_count == 0
    assert result.known_graph_largest_cyclic_component_states == 0
    _assert_no_closed_recurrence(result)
    assert result.input_branch_points == _DOUBLE_INPUT_BRANCH_POINTS
    assert len(result.input_branch_states) == _DOUBLE_INPUT_BRANCH_POINTS
    assert result.input_branch_states[0].code_pointer == 0
    second_branch_states = result.input_branch_states[1:]
    assert all(state.code_pointer == 1 for state in second_branch_states)
    assert all(not state.eof_seen for state in result.input_branch_states)
    assert result.terminal_status_counts == (
        ("halted", _INPUT_VALUE_COUNT),
    )
    assert not result.truncated


def _assert_fixed_cycle_entry_path(
    path: tuple[_WorklistCycleState, ...],
    cycle: _WorklistCycleState,
) -> None:
    assert len(path) == _FIXED_CYCLE_ENTRY_PATH_STATES
    assert (path[0].code_pointer, path[0].data_pointer) == (0, 0)
    assert path[0].accumulator == 0
    assert path[0].memory_overrides == ()
    assert (path[1].code_pointer, path[1].data_pointer) == (1, 1)
    assert path[1].accumulator == 0
    assert path[1].memory_overrides == ((0, 111),)
    assert path[2] == cycle


def _assert_fixed_non_graphical_fetch_evidence(
    result: _WorklistAnalysis,
) -> None:
    assert (
        result.explored_non_graphical_fetch_transition_count
        == _INPUT_VALUE_COUNT
    )
    assert result.explored_non_graphical_fetch_addresses == (
        _FIXED_CYCLE_POINTER,
    )
    assert _domain_values(
        result.explored_non_graphical_fetch_value_domains,
        _FIXED_CYCLE_POINTER,
    ) == (_FIXED_CYCLE_NON_GRAPHICAL_VALUE,)
    observations = result.explored_non_graphical_fetch_observations
    assert len(observations) == _INPUT_VALUE_COUNT
    assert all(item.address == _FIXED_CYCLE_POINTER for item in observations)
    assert all(
        item.value == _FIXED_CYCLE_NON_GRAPHICAL_VALUE for item in observations
    )
    assert all(
        (item.state.code_pointer, item.state.data_pointer)
        == (_FIXED_CYCLE_POINTER, _FIXED_CYCLE_POINTER)
        for item in observations
    )
    assert observations[0].state.accumulator == 0
    assert not observations[0].state.eof_seen
    assert observations[-1].state.accumulator == _EOF_ACCUMULATOR
    assert observations[-1].state.eof_seen
    witness = result.explored_non_graphical_fetch_witness
    assert witness is not None
    assert witness.address == _FIXED_CYCLE_POINTER
    assert witness.value == _FIXED_CYCLE_NON_GRAPHICAL_VALUE
    assert len(witness.entry_path) == _FIXED_CYCLE_ENTRY_PATH_STATES
    assert witness.entry_path[-1] == witness.state
    assert witness.state.code_pointer == _FIXED_CYCLE_POINTER


def test_changed_read_invariant_rejects_domain_address_drift() -> None:
    """Changed-read address summaries must equal their value-domain keys."""
    with pytest.raises(AssertionError, match="addresses disagree"):
        worklist._assert_observed_value_domains(
            1,
            {_EVOLVED_FETCH_ADDRESS},
            {_EVOLVED_FETCH_ADDRESS + 1: {_EVOLVED_FETCH_OBSERVED_VALUE}},
            label="evolved fetch",
        )


def test_changed_read_invariant_rejects_under_counted_values() -> None:
    """A transition count must cover every distinct changed value observed."""
    with pytest.raises(AssertionError, match="cannot cover"):
        worklist._assert_observed_value_domains(
            1,
            {1},
            {1: {32, 33}},
            label="changed encryption input",
        )


def test_planned_write_observation_invariant_rejects_count_drift() -> None:
    """Planned-write counts must match exact explored write states."""
    with pytest.raises(AssertionError, match="exact states"):
        worklist._assert_planned_data_write_observations(
            (1, {0}, {0: {1}}, {}, {_GRAPH_KEY_A})
        )


def test_changed_encryption_observation_rejects_count_drift() -> None:
    """Changed encryption counts must match exact explored states."""
    with pytest.raises(AssertionError, match="exact states"):
        worklist._assert_changed_encryption_input_observations(
            (1, {0}, {0: {1}}, {}, {_GRAPH_KEY_A}),
            (0,),
        )


def test_changed_encryption_observation_rejects_initial_value() -> None:
    """Changed encryption observations cannot equal initial memory."""
    with pytest.raises(AssertionError, match="equals initial memory"):
        worklist._assert_changed_encryption_input_observations(
            (1, {0}, {0: {0}}, {_GRAPH_KEY_A: (0, 0)}, {_GRAPH_KEY_A}),
            (0,),
        )


def test_evolved_read_observation_invariant_rejects_count_drift() -> None:
    """Changed-read counts must equal their exact explored state set."""
    with pytest.raises(AssertionError, match="exact observed states"):
        worklist._assert_evolved_read_observation_evidence(
            (1, {0}, {0: {1}}, {}, {_GRAPH_KEY_A}),
            (0,),
            label="evolved read",
        )


def test_evolved_read_observation_rejects_initial_value() -> None:
    """Changed-read observations cannot equal immutable initial memory."""
    with pytest.raises(AssertionError, match="differs from initial memory"):
        worklist._assert_evolved_read_observation_evidence(
            (1, {0}, {0: {0}}, {_GRAPH_KEY_A: (0, 0)}, {_GRAPH_KEY_A}),
            (0,),
            label="evolved read",
        )


def test_evolved_read_invariant_rejects_missing_witness() -> None:
    """Observed evolved reads cannot silently lose their first exact witness."""
    with pytest.raises(AssertionError, match="witness presence"):
        worklist._assert_evolved_read_witness(
            (
                1,
                {
                    _EVOLVED_DATA_READ_ADDRESS: {
                        _EVOLVED_DATA_READ_OBSERVED_VALUE
                    }
                },
                None,
            ),
            label="evolved data read",
            require_witness=True,
        )


def test_committed_write_partition_rejects_terminal_overlap() -> None:
    """A terminal endpoint cannot also publish a committed write."""
    with pytest.raises(AssertionError, match="terminal endpoints"):
        worklist._assert_committed_write_terminal_partition(
            ({_GRAPH_KEY_A}, set(), set()),
            {_HALTED_STATUS: {_GRAPH_KEY_A}},
        )


def test_write_partition_rejects_committed_count_drift() -> None:
    """Committed mutation slots must equal data-write plus encryption slots."""
    with pytest.raises(AssertionError, match="mutation classes"):
        worklist._assert_committed_write_count_partition(
            (2, 1, 0, 0, 1)
        )


def test_write_partition_rejects_committed_address_drift() -> None:
    """Committed addresses must equal data-write/self-encryption union."""
    with pytest.raises(AssertionError, match="addresses disagree"):
        worklist._assert_committed_write_address_partition(
            ({0}, {40}, set(), {0}, {40})
        )


def test_write_partition_rejects_unclassified_data_write_address() -> None:
    """Every committed data-write address must belong to its final class."""
    with pytest.raises(AssertionError, match="no-op/effective classes"):
        worklist._assert_committed_write_address_partition(
            ({0, 40}, {40}, set(), {0}, set())
        )


def test_write_state_partition_rejects_overlapping_outcomes() -> None:
    """A committed data-write state cannot be both no-op and effective."""
    with pytest.raises(AssertionError, match="exact state classes overlap"):
        worklist._assert_committed_data_write_state_partition(
            (
                {_GRAPH_KEY_A: (40, 29_524)},
                {_GRAPH_KEY_A: (40, 29_524, 29_524, 29_524, False)},
                {_GRAPH_KEY_A: (40, 29_524, 29_524, 29_523, False)},
                {40: {29_524}},
            )
        )


def test_write_state_partition_rejects_unplanned_commit() -> None:
    """Every committed data-write state must have exact planning evidence."""
    with pytest.raises(AssertionError, match="states escape planned writes"):
        worklist._assert_committed_data_write_state_partition(
            (
                {_GRAPH_KEY_A: (40, 29_524)},
                {},
                {_GRAPH_KEY_B: (40, 29_524, 29_523, 29_522, False)},
                {40: {29_523}},
            )
        )


def test_write_state_partition_rejects_planned_value_drift() -> None:
    """Committed address/value evidence must match its exact planned write."""
    with pytest.raises(AssertionError, match="disagrees with planned write"):
        worklist._assert_committed_data_write_state_partition(
            (
                {_GRAPH_KEY_A: (40, 29_523)},
                {_GRAPH_KEY_A: (40, 29_524, 29_524, 29_524, False)},
                {},
                {40: {29_524}},
            )
        )


def test_write_state_partition_rejects_committed_value_domain_drift() -> None:
    """Committed value domains must project from exact final observations."""
    with pytest.raises(AssertionError, match="domains disagree"):
        worklist._assert_committed_data_write_state_partition(
            (
                {_GRAPH_KEY_A: (40, 29_524)},
                {_GRAPH_KEY_A: (40, 29_524, 29_524, 29_524, False)},
                {},
                {40: {29_523}},
            )
        )


def test_read_partition_rejects_overlapping_exact_state_classes() -> None:
    """Value-equality complements cannot classify the same state twice."""
    with pytest.raises(AssertionError, match="exact state classes overlap"):
        worklist._assert_observation_state_partition(
            {_GRAPH_KEY_A},
            {_GRAPH_KEY_A},
            label="fetch value partition",
        )


def test_initial_value_observations_reject_count_drift() -> None:
    """Initial-value counts must match their exact state observations."""
    with pytest.raises(AssertionError, match="exact states"):
        worklist._assert_initial_value_observations(
            (1, {0}, {}, {_GRAPH_KEY_A}),
            (117,),
            label="initial-value fetch",
        )


def test_initial_value_observations_reject_changed_value() -> None:
    """Initial-value observations must equal immutable initial memory."""
    with pytest.raises(AssertionError, match="differs from initial memory"):
        worklist._assert_initial_value_observations(
            (1, {0}, {_GRAPH_KEY_A: (0, 116)}, {_GRAPH_KEY_A}),
            (117,),
            label="initial-value fetch",
        )


def test_self_encryption_observations_reject_count_drift() -> None:
    """Committed self-encryption counts must match exact explored states."""
    with pytest.raises(AssertionError, match="exact committed states"):
        worklist._assert_self_encryption_observations(
            (1, {0}, {0: {111}}, {}, {_GRAPH_KEY_A})
        )


def test_self_encryption_observations_reject_output_drift() -> None:
    """Committed self-encryption output must match classic encryption."""
    with pytest.raises(AssertionError, match="classic encryption"):
        worklist._assert_self_encryption_observations(
            (
                1,
                {0},
                {0: {111}},
                {_GRAPH_KEY_A: (0, 117, 112, False)},
                {_GRAPH_KEY_A},
            )
        )


def test_data_write_noop_observations_reject_count_drift() -> None:
    """Final no-op counts must match exact explored states."""
    with pytest.raises(AssertionError, match="exact states"):
        worklist._assert_data_write_noop_observations(
            (1, {40}, {}, {_GRAPH_KEY_A})
        )


def test_data_write_noop_observations_reject_memory_change() -> None:
    """Final no-op observations cannot retain an effective mutation."""
    with pytest.raises(AssertionError, match="changed memory"):
        worklist._assert_data_write_noop_observations(
            (
                1,
                {40},
                {_GRAPH_KEY_A: (40, 29_524, 29_523, 29_523, False)},
                {_GRAPH_KEY_A},
            )
        )


def test_data_mutation_observations_reject_count_drift() -> None:
    """Effective mutation counts must match exact explored states."""
    with pytest.raises(AssertionError, match="exact states"):
        worklist._assert_data_mutation_observations(
            (1, {40}, {40: {29_524}}, {40: {29_523}}, {}, {_GRAPH_KEY_A})
        )


def test_data_mutation_domains_reject_result_address_drift() -> None:
    """Effective mutation domains must retain identical exact addresses."""
    with pytest.raises(AssertionError, match="addresses disagree"):
        worklist._assert_data_mutation_domains(
            1,
            {40},
            previous_values={40: {29_524}},
            result_values={41: {29_523}},
        )


def test_non_graphical_fetch_invariant_rejects_domain_address_drift() -> None:
    """Invalid-fetch address summaries cannot diverge from value domains."""
    with pytest.raises(AssertionError, match="addresses disagree"):
        worklist._assert_non_graphical_fetch_domains(
            1,
            {_FIXED_CYCLE_POINTER},
            {_FIXED_CYCLE_POINTER + 1: {_FIXED_CYCLE_NON_GRAPHICAL_VALUE}},
        )


def test_non_graphical_fetch_invariant_rejects_graphical_domain_value() -> None:
    """Invalid-fetch domains fail closed if a graphical value is retained."""
    with pytest.raises(AssertionError, match="graphical value"):
        worklist._assert_non_graphical_fetch_domains(
            1,
            {_FIXED_CYCLE_POINTER},
            {_FIXED_CYCLE_POINTER: {ord("A")}},
        )


def test_non_graphical_fetch_observation_rejects_count_drift() -> None:
    """Invalid-fetch counts must equal exact explored fetch states."""
    with pytest.raises(AssertionError, match="exact fetch states"):
        worklist._assert_non_graphical_fetch_observation_projection(
            (
                1,
                {_GRAPH_KEY_A[0]},
                {_GRAPH_KEY_A[0]: {_FIXED_CYCLE_NON_GRAPHICAL_VALUE}},
                {},
            ),
            seen=set(),
        )


def test_non_graphical_fetch_observation_rejects_unknown_state() -> None:
    """Invalid-fetch observations must belong to the explored graph."""
    with pytest.raises(AssertionError, match="unknown graph state"):
        worklist._assert_non_graphical_fetch_observation_projection(
            (
                1,
                {_GRAPH_KEY_A[0]},
                {_GRAPH_KEY_A[0]: {_FIXED_CYCLE_NON_GRAPHICAL_VALUE}},
                {_GRAPH_KEY_A: _FIXED_CYCLE_NON_GRAPHICAL_VALUE},
            ),
            seen={_GRAPH_KEY_B},
        )


def test_non_graphical_fetch_observation_requires_self_loop() -> None:
    """Invalid executable fetches must retain exact non-progress edges."""
    with pytest.raises(AssertionError, match="self-loop edge"):
        worklist._assert_non_graphical_fetch_observation_edges(
            {_GRAPH_KEY_A: _FIXED_CYCLE_NON_GRAPHICAL_VALUE},
            {_GRAPH_KEY_A: {_GRAPH_KEY_B}, _GRAPH_KEY_B: set()},
        )


def test_non_graphical_fetch_invariant_rejects_missing_witness() -> None:
    """Observed invalid fetches cannot silently lose the first exact witness."""
    with pytest.raises(AssertionError, match="witness presence"):
        worklist._assert_non_graphical_fetch_witness(
            {_FIXED_CYCLE_POINTER: {_FIXED_CYCLE_NON_GRAPHICAL_VALUE}},
            None,
        )


def test_fixed_fetch_becomes_an_exact_worklist_self_cycle() -> None:
    """Historical non-graphical continue is an exact self-loop edge."""
    result = worklist.analyze_reachability(
        _DOUBLE_INPUT_FIXED_CYCLE_SOURCE,
        maximum_states=_DOUBLE_INPUT_UNIQUE_STATES,
    )
    assert result.unique_states == _DOUBLE_INPUT_UNIQUE_STATES
    assert result.repeated_state_edges == _DOUBLE_INPUT_CYCLE_EDGES
    assert result.reachable_cycle_detected
    assert len(result.reachable_cycle_witness) == 1
    cycle = result.reachable_cycle_witness[0]
    assert cycle.code_pointer == _FIXED_CYCLE_POINTER
    assert cycle.data_pointer == _FIXED_CYCLE_POINTER
    assert cycle.accumulator == 0
    assert cycle.memory_overrides == _FIXED_CYCLE_MEMORY_OVERRIDES
    assert not cycle.eof_seen
    _assert_fixed_cycle_entry_path(result.reachable_cycle_entry_path, cycle)
    _assert_fixed_non_graphical_fetch_evidence(result)
    assert (
        result.known_graph_strong_component_count
        == _DOUBLE_INPUT_UNIQUE_STATES
    )
    assert result.known_graph_cyclic_component_count == _INPUT_VALUE_COUNT
    assert result.known_graph_cyclic_state_count == _INPUT_VALUE_COUNT
    assert result.known_graph_largest_cyclic_component_states == 1
    _assert_fixed_cycle_closed_recurrence(result)
    assert result.terminal_status_counts == ()
    assert result.closed_terminal_status_counts == ()
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated


def test_worklist_materializes_initial_memory_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recurrence initialization is shared across exact worklist states."""
    original_crazy = worklist.classic.crazy
    crazy_calls = 0

    def counting_crazy(data: int, accumulator: int) -> int:
        nonlocal crazy_calls
        crazy_calls += 1
        return original_crazy(data, accumulator)

    monkeypatch.setattr(worklist.classic, "crazy", counting_crazy)
    result = worklist.analyze_reachability(
        _LONG_INPUT_CYCLE_SOURCE,
        maximum_states=_LONG_INPUT_CYCLE_STATE_LIMIT,
    )
    assert not result.truncated
    assert crazy_calls == (
        worklist.classic.PROFILE_MEMORY_WORDS - len(_LONG_INPUT_CYCLE_SOURCE)
    )


def test_long_input_dependent_jump_chain_reaches_exact_cycle() -> None:
    """One input plus three jumps reaches a cycle after five exact states."""
    result = worklist.analyze_reachability(
        _LONG_INPUT_CYCLE_SOURCE,
        maximum_states=_LONG_INPUT_CYCLE_STATE_LIMIT,
    )
    assert result.unique_states == _LONG_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_states == _LONG_INPUT_CYCLE_STATE_LIMIT
    assert result.reachable_cycle_detected
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated
    path = result.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _LONG_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == result.reachable_cycle_witness[0]
    recurrent = result.closed_recurrent_entry_path
    assert recurrent is not None
    assert recurrent == path
    assert result.closed_recurrent_component_count == _INPUT_VALUE_COUNT


def test_deeper_input_dependent_jump_chain_closes_exact_cycle() -> None:
    """One input plus four jumps closes at a six-state cycle entry path."""
    result = worklist.analyze_reachability(
        _DEEP_INPUT_CYCLE_SOURCE,
        maximum_states=_DEEP_INPUT_CYCLE_STATE_LIMIT,
    )
    assert result.unique_states == _DEEP_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_states == _DEEP_INPUT_CYCLE_STATE_LIMIT
    assert result.reachable_cycle_detected
    assert result.maximum_first_seen_transition_index == len(
        _DEEP_INPUT_CYCLE_POINTER_PATH
    )
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated
    path = result.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _DEEP_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == result.reachable_cycle_witness[0]
    recurrent = result.closed_recurrent_entry_path
    assert recurrent is not None
    assert recurrent == path
    assert result.closed_recurrent_component_count == _INPUT_VALUE_COUNT


def _assert_cycle_closing_self_loop_witness(
    witness: _WorklistCycleClosingRepeatedEdgeWitness | None,
) -> None:
    assert witness is not None
    assert witness.source_state == witness.target_state
    assert witness.source_entry_path[-1] == witness.source_state
    assert witness.target_entry_path_state_index == (
        len(witness.source_entry_path) - 1
    )


def test_near_cap_input_dependent_jump_chain_closes_exact_cycle() -> None:
    """Fourteen post-input jumps close within the reviewed state ceiling."""
    result = worklist.analyze_reachability(
        _NEAR_CAP_INPUT_CYCLE_SOURCE,
        maximum_states=_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT,
    )
    assert result.unique_states == _NEAR_CAP_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_states == _NEAR_CAP_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_code_pointer_addresses == tuple(range(16))
    assert (
        result.explored_data_pointer_addresses
        == _NEAR_CAP_INPUT_CYCLE_DATA_POINTER_ADDRESSES
    )
    assert result.explored_state_merge_transition_count == 0
    assert (
        result.explored_cycle_closing_repeated_edge_count == _INPUT_VALUE_COUNT
    )
    _assert_cycle_closing_self_loop_witness(
        result.explored_cycle_closing_repeated_edge_witness
    )
    assert result.explored_state_merge_witness is None
    assert result.reachable_cycle_detected
    assert result.maximum_first_seen_transition_index == len(
        _NEAR_CAP_INPUT_CYCLE_POINTER_PATH
    )
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated
    path = result.reachable_cycle_entry_path
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _NEAR_CAP_INPUT_CYCLE_POINTER_PATH
    assert path[-1] == result.reachable_cycle_witness[0]
    assert result.closed_recurrent_entry_path == path
    assert result.closed_recurrent_component_count == _INPUT_VALUE_COUNT
    assert (
        result.known_graph_cyclic_component_minimum_entry_path_state_counts
        == (
            (len(_NEAR_CAP_INPUT_CYCLE_POINTER_PATH),) * _INPUT_VALUE_COUNT
        )
    )
    assert (
        result.closed_recurrent_component_minimum_entry_path_state_counts
        == (len(_NEAR_CAP_INPUT_CYCLE_POINTER_PATH),) * _INPUT_VALUE_COUNT
    )


def _assert_merged_repeated_edge_partition(result: _WorklistAnalysis) -> None:
    assert (
        result.explored_state_merge_transition_count
        == _MERGED_INPUT_CYCLE_STATE_MERGES
    )
    assert (
        result.explored_cycle_closing_repeated_edge_count
        == _MERGED_INPUT_CYCLE_CYCLE_CLOSING_REPEATS
    )
    assert (
        result.explored_state_merge_transition_count
        + result.explored_cycle_closing_repeated_edge_count
        == result.repeated_state_edges
    )
    _assert_cycle_closing_self_loop_witness(
        result.explored_cycle_closing_repeated_edge_witness
    )


def test_input_branch_merge_closes_deeper_cycle_with_small_graph() -> None:
    """Rotate after input merges branches before a deeper exact cycle."""
    result = worklist.analyze_reachability(
        _MERGED_INPUT_CYCLE_SOURCE,
        maximum_states=_MAX_WORKLIST_STATE_LIMIT,
    )
    assert result.unique_states == _MERGED_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_states == _MERGED_INPUT_CYCLE_STATE_LIMIT
    assert result.input_branch_points == 1
    assert result.repeated_state_edges == _MERGED_INPUT_CYCLE_REPEATED_EDGES
    _assert_merged_repeated_edge_partition(result)
    merge = result.explored_state_merge_witness
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
    assert merge.source_entry_path[-1] == merge.source_state
    assert merge.existing_target_entry_path[-1] == merge.target_state
    assert result.maximum_first_seen_transition_index == (
        _MERGED_INPUT_CYCLE_PATH_LENGTH
    )
    assert result.reachable_cycle_detected
    path = result.reachable_cycle_entry_path
    assert len(path) == _MERGED_INPUT_CYCLE_PATH_LENGTH
    assert tuple(state.code_pointer for state in path) == tuple(
        range(_MERGED_INPUT_CYCLE_PATH_LENGTH)
    )
    assert path[-1] == result.reachable_cycle_witness[0]
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated


def test_double_jump_branch_merge_closes_124_state_cycle() -> None:
    """A second pre-merge jump pushes the evolved fixed fetch to C=123."""
    result = worklist.analyze_reachability(
        _DOUBLE_JUMP_MERGED_CYCLE_SOURCE,
        maximum_states=_MAX_WORKLIST_STATE_LIMIT,
    )
    assert result.unique_states == _DOUBLE_JUMP_MERGED_CYCLE_STATE_LIMIT
    assert result.explored_states == _DOUBLE_JUMP_MERGED_CYCLE_STATE_LIMIT
    assert result.input_branch_points == 1
    assert (
        result.explored_state_merge_transition_count
        == _MERGED_INPUT_CYCLE_STATE_MERGES
    )
    assert (
        result.explored_cycle_closing_repeated_edge_count
        == _MERGED_INPUT_CYCLE_CYCLE_CLOSING_REPEATS
    )
    assert result.maximum_first_seen_transition_index == (
        _DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH
    )
    path = result.reachable_cycle_entry_path
    assert len(path) == _DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH
    assert tuple(state.code_pointer for state in path) == tuple(
        range(_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH)
    )
    assert path[-1] == result.reachable_cycle_witness[0]
    assert (
        result.known_graph_cyclic_component_minimum_entry_path_state_counts
        == (
            (_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH,) * 2
        )
    )
    assert (
        result.closed_recurrent_component_minimum_entry_path_state_counts
        == (_DOUBLE_JUMP_MERGED_CYCLE_PATH_LENGTH,) * 2
    )
    evolved = result.explored_evolved_fetch_witness
    assert evolved is not None
    assert evolved.state == path[-1]
    assert evolved.address == _DOUBLE_JUMP_MERGED_CYCLE_ADDRESS
    assert evolved.initial_value == _DOUBLE_JUMP_MERGED_CYCLE_INITIAL_VALUE
    assert evolved.observed_value == _DOUBLE_JUMP_MERGED_CYCLE_EVOLVED_VALUE
    assert evolved.origin_kind == _WRITER_DATA_WRITE
    assert (
        evolved.origin_entry_path_transition_index
        == _DOUBLE_JUMP_MERGED_CYCLE_WRITER_TRANSITION
    )
    assert result.closed_all_paths_terminate is False
    assert result.closed_all_paths_halt is False
    assert not result.truncated


def _assert_over_cap_frontier_state_set(result: _WorklistAnalysis) -> None:
    frontier = result.frontier_state_set
    assert len(frontier) == _INPUT_VALUE_COUNT
    assert sum(
        state.code_pointer == _OVER_CAP_FRONTIER_LOADED_CODE_POINTER
        for state in frontier
    ) == _OVER_CAP_FRONTIER_LOADED_STATE_COUNT
    assert sum(
        state.code_pointer == _OVER_CAP_FRONTIER_RECURRENCE_CODE_POINTER
        for state in frontier
    ) == _OVER_CAP_FRONTIER_RECURRENCE_STATE_COUNT


def test_reviewed_state_ceiling_truncates_deeper_jump_chain() -> None:
    """The 4,096-state maximum stops before silently closing a deeper graph."""
    result = worklist.analyze_reachability(
        _OVER_CAP_INPUT_CYCLE_SOURCE,
        maximum_states=_MAX_WORKLIST_STATE_LIMIT,
    )
    assert result.unique_states == _MAX_WORKLIST_STATE_LIMIT
    assert result.explored_states == _OVER_CAP_EXPLORED_STATES
    assert result.frontier_states == _INPUT_VALUE_COUNT
    _assert_over_cap_frontier_state_set(result)
    assert result.maximum_first_seen_transition_index == (
        _OVER_CAP_MAXIMUM_FIRST_SEEN_TRANSITION
    )
    assert not result.reachable_cycle_detected
    assert result.reachable_cycle_witness == ()
    assert result.known_graph_cyclic_components == ()
    assert (
        result.known_graph_cyclic_component_minimum_entry_path_state_counts
        == ()
    )
    assert result.closed_recurrent_components is None
    assert (
        result.closed_recurrent_component_minimum_entry_path_state_counts
        is None
    )
    assert result.closed_all_paths_terminate is None
    assert result.closed_all_paths_halt is None
    assert result.truncated
    witness = result.frontier_state_witness
    path = result.frontier_entry_path
    assert witness is not None
    assert path is not None
    assert witness.accumulator == _OVER_CAP_FRONTIER_ACCUMULATOR
    assert not witness.eof_seen
    assert path[-1] == witness
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in path
    ) == _OVER_CAP_FRONTIER_POINTER_PATH


def test_input_domain_becomes_eof_only_after_eof() -> None:
    """Historical EOF state cannot branch back to later ordinary bytes."""
    snapshot = prefix_transfer.StateSnapshot(
        _SECOND_TRANSITION,
        1,
        1,
        None,
        (),
    )
    successors = worklist._input_successors(snapshot, eof_seen=True)
    assert len(successors) == 1
    successor = successors[0]
    assert successor.eof_seen
    assert successor.snapshot.accumulator == _EOF_ACCUMULATOR


def test_alias_observation_invariant_rejects_count_state_drift() -> None:
    """Alias transition totals must equal the exact observed alias states."""
    with pytest.raises(AssertionError, match="exact alias states"):
        worklist._assert_code_data_alias_observations(
            1,
            {0},
            {},
            seen=set(),
        )


def test_alias_observation_invariant_rejects_unknown_state() -> None:
    """Alias observations must belong to the explored graph."""
    with pytest.raises(AssertionError, match="unknown graph state"):
        worklist._assert_code_data_alias_observations(
            1,
            {_GRAPH_KEY_A[0]},
            {_GRAPH_KEY_A: 0},
            seen={_GRAPH_KEY_B},
        )


def test_input_branch_invariant_rejects_count_state_drift() -> None:
    """Input branch totals cannot diverge from their exact state set."""
    with pytest.raises(AssertionError, match="branch count"):
        worklist._assert_input_branch_evidence(
            1,
            set(),
            {_GRAPH_KEY_A},
        )


def test_frontier_invariant_rejects_truncation_without_states() -> None:
    """Truncation cannot be published with an empty numeric frontier."""
    with pytest.raises(AssertionError, match="frontier state count"):
        worklist._assert_frontier_evidence(
            0,
            (_GRAPH_KEY_A,),
            (_GRAPH_KEY_A,),
            truncated=True,
        )


def test_frontier_invariant_rejects_count_set_drift() -> None:
    """Numeric frontier size must equal the exact frontier state set."""
    with pytest.raises(AssertionError, match="exact frontier set"):
        worklist._assert_frontier_evidence(
            2,
            (_GRAPH_KEY_A,),
            (_GRAPH_KEY_A,),
            truncated=True,
        )


def test_frontier_invariant_rejects_duplicate_exact_states() -> None:
    """The published exact frontier state tuple must remain deduplicated."""
    with pytest.raises(AssertionError, match="canonical and deduplicated"):
        worklist._assert_frontier_evidence(
            2,
            (_GRAPH_KEY_A, _GRAPH_KEY_A),
            (_GRAPH_KEY_A,),
            truncated=True,
        )


def test_frontier_invariant_rejects_empty_exact_path() -> None:
    """A truncated frontier must fail closed on an empty path witness."""
    with pytest.raises(AssertionError, match="frontier path is empty"):
        worklist._assert_frontier_evidence(
            1,
            (_GRAPH_KEY_A,),
            (),
            truncated=True,
        )


def test_terminal_invariant_rejects_count_state_drift() -> None:
    """Terminal status totals must equal their exact terminal-state sets."""
    with pytest.raises(AssertionError, match="exact terminal states"):
        worklist._assert_terminal_evidence(
            {"halted": 2},
            {"halted": {_GRAPH_KEY_A}},
            {_GRAPH_KEY_A},
        )


def test_known_graph_integrity_rejects_missing_admitted_node() -> None:
    """Every admitted state must retain its exact graph node."""
    with pytest.raises(AssertionError, match="nodes disagree"):
        worklist._assert_known_graph_integrity(
            {_GRAPH_KEY_A: set()},
            {_GRAPH_KEY_A, _GRAPH_KEY_B},
        )


def test_known_graph_integrity_rejects_unadmitted_edge_target() -> None:
    """Known graph edges cannot silently point outside admitted states."""
    with pytest.raises(AssertionError, match="unadmitted state"):
        worklist._assert_known_graph_integrity(
            {_GRAPH_KEY_A: {_GRAPH_KEY_B}},
            {_GRAPH_KEY_A},
        )


def test_worklist_state_partition_rejects_unaccounted_admission() -> None:
    """Admitted states must equal explored plus pending queue states."""
    with pytest.raises(AssertionError, match="do not partition"):
        worklist._assert_worklist_state_partition(
            (1, (), {_GRAPH_KEY_A, _GRAPH_KEY_B}, 2),
            truncated=True,
        )


def test_worklist_state_partition_rejects_early_truncation() -> None:
    """Truncation is valid only after the exact state cap is reached."""
    with pytest.raises(AssertionError, match="state limit"):
        worklist._assert_worklist_state_partition(
            (1, (_GRAPH_KEY_B,), {_GRAPH_KEY_A, _GRAPH_KEY_B}, 3),
            truncated=True,
        )


def test_terminal_invariant_rejects_overlapping_state_classes() -> None:
    """One explored terminal state cannot carry two terminal statuses."""
    with pytest.raises(AssertionError, match="terminal state classes overlap"):
        worklist._assert_terminal_evidence(
            {"halted": 1, "invalid": 1},
            {
                "halted": {_GRAPH_KEY_A},
                "invalid": {_GRAPH_KEY_A},
            },
            {_GRAPH_KEY_A},
        )


def test_terminal_graph_invariant_rejects_missing_node() -> None:
    """Terminal evidence cannot refer to a state absent from the graph."""
    with pytest.raises(AssertionError, match="missing its graph node"):
        worklist._assert_terminal_graph_endpoints(
            {"halted": {_GRAPH_KEY_A}},
            {},
        )


def test_terminal_graph_invariant_rejects_outgoing_edge() -> None:
    """A terminal endpoint cannot retain an outgoing graph edge."""
    with pytest.raises(AssertionError, match="outgoing edge"):
        worklist._assert_terminal_graph_endpoints(
            {"halted": {_GRAPH_KEY_A}},
            {_GRAPH_KEY_A: {_GRAPH_KEY_B}, _GRAPH_KEY_B: set()},
        )


def test_known_graph_cycle_detection_rejects_merge_only_heuristics() -> None:
    """Cycle detection uses graph structure rather than repeat-edge count."""
    cycle_edges = {
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
        _GRAPH_KEY_B: {_GRAPH_KEY_A},
    }
    nodes = {_GRAPH_KEY_A, _GRAPH_KEY_B}
    assert worklist._known_graph_has_cycle(cycle_edges, nodes)
    assert worklist._known_graph_cycle_witness(cycle_edges, nodes) == (
        _GRAPH_KEY_A,
        _GRAPH_KEY_B,
    )


def test_known_graph_scc_summary_counts_cycle_components_exactly() -> None:
    """SCC counts separate a two-state cycle, self-loop, and acyclic tail."""
    edges: dict[_WorklistStateKey, set[_WorklistStateKey]] = {
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
        _GRAPH_KEY_B: {_GRAPH_KEY_A},
        _GRAPH_KEY_C: {_GRAPH_KEY_C},
        _GRAPH_KEY_D: {_GRAPH_KEY_C},
    }
    nodes = {_GRAPH_KEY_D, _GRAPH_KEY_C, _GRAPH_KEY_B, _GRAPH_KEY_A}
    assert worklist._known_graph_strong_components(edges, nodes) == (
        (_GRAPH_KEY_A, _GRAPH_KEY_B),
        (_GRAPH_KEY_C,),
        (_GRAPH_KEY_D,),
    )
    summary = worklist._known_graph_strong_component_summary(edges, nodes)
    assert summary.component_count == _SCC_COMPONENT_COUNT
    assert summary.cyclic_component_count == _SCC_CYCLIC_COMPONENT_COUNT
    assert summary.cyclic_state_count == _SCC_CYCLIC_STATE_COUNT
    assert (
        summary.largest_cyclic_component_states
        == _SCC_LARGEST_CYCLIC_COMPONENT_STATES
    )
    assert summary.cyclic_components == (
        (_GRAPH_KEY_A, _GRAPH_KEY_B),
        (_GRAPH_KEY_C,),
    )
    assert summary.cyclic_sink_components == (
        (_GRAPH_KEY_A, _GRAPH_KEY_B),
        (_GRAPH_KEY_C,),
    )


def test_closed_recurrence_path_targets_sink_cycle_not_first_cycle() -> None:
    """Closed recurrence path targets the sink cycle, not an escaping cycle."""
    edges: dict[_WorklistStateKey, set[_WorklistStateKey]] = {
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
        _GRAPH_KEY_B: {_GRAPH_KEY_A, _GRAPH_KEY_C},
        _GRAPH_KEY_C: {_GRAPH_KEY_C},
    }
    nodes = {_GRAPH_KEY_A, _GRAPH_KEY_B, _GRAPH_KEY_C}
    explorer = worklist._Explorer(
        _INPUT_HALT_SOURCE,
        len(nodes),
        deque(),
        nodes,
        edges,
        {},
        {0},
    )
    result = explorer.run()
    known_components = tuple(
        tuple(state.code_pointer for state in component)
        for component in result.known_graph_cyclic_components
    )
    assert known_components == ((0, 1), (2,))
    recurrent_components = result.closed_recurrent_components
    assert recurrent_components is not None
    assert tuple(
        tuple(state.code_pointer for state in component)
        for component in recurrent_components
    ) == ((2,),)
    assert (
        result.known_graph_cyclic_component_minimum_entry_path_state_counts
        == (
            _ESCAPING_CYCLIC_COMPONENT_ENTRY_COUNTS
        )
    )
    assert (
        result.closed_recurrent_component_minimum_entry_path_state_counts
        == _ESCAPING_RECURRENT_COMPONENT_ENTRY_COUNTS
    )
    cycle_pointers = tuple(
        state.code_pointer for state in result.reachable_cycle_witness
    )
    assert cycle_pointers == (0, 1)
    assert tuple(
        state.code_pointer for state in result.reachable_cycle_entry_path
    ) == (0,)
    recurrent = result.closed_recurrent_cycle_witness
    assert recurrent is not None
    assert tuple(state.code_pointer for state in recurrent) == (2,)
    path = result.closed_recurrent_entry_path
    assert path is not None
    assert tuple(state.code_pointer for state in path) == (0, 1, 2)


def test_cyclic_scc_with_known_escape_is_not_closed_recurrent() -> None:
    """A cycle with a known outgoing edge is not a recurrent sink SCC."""
    edges: dict[_WorklistStateKey, set[_WorklistStateKey]] = {
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
        _GRAPH_KEY_B: {_GRAPH_KEY_A, _GRAPH_KEY_C},
        _GRAPH_KEY_C: set(),
    }
    nodes = {_GRAPH_KEY_A, _GRAPH_KEY_B, _GRAPH_KEY_C}
    summary = worklist._known_graph_strong_component_summary(edges, nodes)
    assert summary.cyclic_component_count == 1
    assert summary.cyclic_sink_components == ()


def test_cycle_witness_is_stable_across_graph_insertion_order() -> None:
    """Sorted exact keys make a later disconnected cycle deterministic."""
    nodes = {_GRAPH_KEY_D, _GRAPH_KEY_C, _GRAPH_KEY_B, _GRAPH_KEY_A}
    first_edges: dict[_WorklistStateKey, set[_WorklistStateKey]] = {
        _GRAPH_KEY_D: {_GRAPH_KEY_C},
        _GRAPH_KEY_C: {_GRAPH_KEY_D},
        _GRAPH_KEY_B: set(),
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
    }
    second_edges: dict[_WorklistStateKey, set[_WorklistStateKey]] = {
        _GRAPH_KEY_A: {_GRAPH_KEY_B},
        _GRAPH_KEY_B: set(),
        _GRAPH_KEY_C: {_GRAPH_KEY_D},
        _GRAPH_KEY_D: {_GRAPH_KEY_C},
    }
    expected = (_GRAPH_KEY_C, _GRAPH_KEY_D)
    assert worklist._known_graph_cycle_witness(first_edges, nodes) == expected
    assert worklist._known_graph_cycle_witness(second_edges, nodes) == expected


def _assert_wrap_signature(
    signature: _WorklistWrapTransitionSignature,
    expected: tuple[int, int, int, int, bool, bool],
) -> None:
    actual = (
        signature.source_code_pointer,
        signature.source_data_pointer,
        signature.result_code_pointer,
        signature.result_data_pointer,
        signature.code_pointer_wrapped,
        signature.data_pointer_wrapped,
    )
    assert actual == expected


def _assert_simultaneous_wrap_evidence(result: _WorklistAnalysis) -> None:
    assert result.explored_wraparound_transition_count == 1
    assert result.explored_code_pointer_wrap_transition_count == 1
    assert result.explored_data_pointer_wrap_transition_count == 1
    assert result.explored_simultaneous_pointer_wrap_transition_count == 1
    signatures = result.explored_wraparound_transition_signatures
    assert len(signatures) == 1
    _assert_wrap_signature(
        signatures[0],
        (_WRAP_ADDRESS, _WRAP_ADDRESS, 0, 0, True, True),
    )
    generic = result.explored_wraparound_witness
    code = result.explored_code_pointer_wrap_witness
    data = result.explored_data_pointer_wrap_witness
    simultaneous = result.explored_simultaneous_pointer_wrap_witness
    assert generic is not None
    assert code == generic
    assert data == generic
    assert simultaneous == generic
    assert generic.entry_path == ()
    assert generic.code_pointer_wrapped
    assert generic.data_pointer_wrapped


def test_wrap_evidence_rejects_inconsistent_class_counts() -> None:
    """Wrap class inclusion-exclusion is checked before publication."""
    with pytest.raises(AssertionError, match="class counts disagree"):
        worklist._assert_wrap_evidence_invariants(
            (2, 1, 1, 1),
            (None, None, None, None),
        )


def test_wrap_evidence_rejects_missing_class_witness() -> None:
    """A nonzero wrap class cannot silently lose its first exact witness."""
    with pytest.raises(AssertionError, match="witness presence"):
        worklist._assert_wrap_evidence_invariants(
            (1, 0, 1, 0),
            (None, None, None, None),
        )


def test_explorer_counts_exact_pointer_wrap_transition() -> None:
    """A canonical near-boundary state records C/D wrap to zero."""
    snapshot = prefix_transfer.StateSnapshot(
        1,
        _WRAP_ADDRESS,
        _WRAP_ADDRESS,
        0,
        ((_WRAP_ADDRESS, _WRAP_SOURCE_VALUE),),
    )
    node = worklist._ReachabilityNode(snapshot=snapshot, eof_seen=False)
    key = worklist._node_key(node)
    explorer = worklist._Explorer(
        _INPUT_HALT_SOURCE,
        _WRAP_STATE_LIMIT,
        deque((node,)),
        {key},
        {key: set()},
        {},
        set(),
    )
    result = explorer.run()
    _assert_simultaneous_wrap_evidence(result)
    assert result.explored_highest_accessed_address == _WRAP_ADDRESS
    assert result.explored_minimum_words == _WRAP_ADDRESS + 1
    assert result.truncated


def _assert_single_evolved_read_observation(
    observations: tuple[_WorklistEvolvedReadObservation, ...],
    expected: tuple[int, int, int, tuple[int, int, int]],
) -> None:
    address, initial_value, observed_value, pointers = expected
    assert len(observations) == 1
    observation = observations[0]
    assert observation.address == address
    assert observation.initial_value == initial_value
    assert observation.observed_value == observed_value
    state = observation.state
    actual = (state.code_pointer, state.data_pointer, state.accumulator)
    assert actual == pointers
    assert not state.eof_seen


def _assert_evolved_read_witness(
    witness: _WorklistEvolvedReadWitness | None,
    expected: tuple[int, int, int, tuple[tuple[int, int], ...]],
) -> None:
    address, initial_value, observed_value, pointer_path = expected
    assert witness is not None
    assert witness.address == address
    assert witness.initial_value == initial_value
    assert witness.observed_value == observed_value
    assert witness.origin_value == observed_value
    assert witness.entry_path[-1] == witness.state
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in witness.entry_path
    ) == pointer_path


def test_worklist_witnesses_fetch_from_evolved_memory() -> None:
    """Closed worklist proves a later instruction fetch uses a prior write."""
    result = worklist.analyze_reachability(
        _EVOLVED_FETCH_SOURCE,
        maximum_states=_EVOLVED_FETCH_STATE_LIMIT,
    )
    assert not result.truncated
    assert result.reachable_cycle_detected
    assert result.explored_initial_value_fetch_transition_count == (
        _EVOLVED_FETCH_INITIAL_VALUE_FETCH_COUNT
    )
    assert result.explored_initial_value_fetch_addresses == (
        _EVOLVED_FETCH_INITIAL_VALUE_FETCH_ADDRESSES
    )
    assert (
        result.explored_initial_value_fetch_transition_count
        + result.explored_evolved_fetch_transition_count
        == result.explored_states
    )
    assert result.explored_evolved_fetch_transition_count == 1
    assert result.explored_evolved_fetch_addresses == (_EVOLVED_FETCH_ADDRESS,)
    assert _domain_values(
        result.explored_evolved_fetch_value_domains, _EVOLVED_FETCH_ADDRESS
    ) == (_EVOLVED_FETCH_OBSERVED_VALUE,)
    _assert_single_evolved_read_observation(
        result.explored_evolved_fetch_observations,
        (
            _EVOLVED_FETCH_ADDRESS,
            _EVOLVED_FETCH_INITIAL_VALUE,
            _EVOLVED_FETCH_OBSERVED_VALUE,
            (95, 97, _EVOLVED_FETCH_OBSERVED_VALUE),
        ),
    )
    assert result.explored_evolved_data_read_observations == ()
    assert result.explored_data_read_transition_count == (
        _EVOLVED_FETCH_DATA_READ_COUNT
    )
    assert result.explored_initial_value_data_read_transition_count == (
        _EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert result.explored_initial_value_data_read_addresses == (
        _EVOLVED_FETCH_INITIAL_VALUE_DATA_READ_ADDRESSES
    )
    assert result.explored_evolved_data_read_transition_count == 0
    assert result.explored_evolved_data_read_addresses == ()
    _assert_evolved_read_witness(
        result.explored_evolved_fetch_witness,
        (
            _EVOLVED_FETCH_ADDRESS,
            _EVOLVED_FETCH_INITIAL_VALUE,
            _EVOLVED_FETCH_OBSERVED_VALUE,
            _EVOLVED_FETCH_POINTER_PATH,
        ),
    )
    witness = result.explored_evolved_fetch_witness
    assert witness is not None
    assert witness.origin_kind == _WRITER_DATA_WRITE
    assert (
        witness.origin_entry_path_transition_index
        == _EVOLVED_FETCH_ORIGIN_TRANSITION
    )


def test_worklist_witnesses_data_read_from_evolved_memory() -> None:
    """Closed worklist proves a semantic data read uses a prior write."""
    result = worklist.analyze_reachability(
        _EVOLVED_DATA_READ_SOURCE,
        maximum_states=_EVOLVED_DATA_READ_STATE_LIMIT,
    )
    assert not result.truncated
    assert result.terminal_status_counts == (("halted", 1),)
    assert result.explored_initial_value_fetch_transition_count == (
        _EVOLVED_DATA_READ_INITIAL_VALUE_FETCH_COUNT
    )
    assert result.explored_initial_value_fetch_addresses == (
        _EVOLVED_DATA_READ_INITIAL_VALUE_FETCH_ADDRESSES
    )
    assert result.explored_evolved_fetch_transition_count == 0
    assert result.explored_evolved_fetch_addresses == ()
    assert result.explored_data_read_transition_count == (
        _EVOLVED_DATA_READ_TOTAL_DATA_READ_COUNT
    )
    assert result.explored_initial_value_data_read_transition_count == (
        _EVOLVED_DATA_READ_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert result.explored_initial_value_data_read_addresses == (
        _EVOLVED_DATA_READ_INITIAL_VALUE_DATA_READ_ADDRESSES
    )
    assert (
        result.explored_initial_value_data_read_transition_count
        + result.explored_evolved_data_read_transition_count
        == result.explored_data_read_transition_count
    )
    assert result.explored_evolved_data_read_transition_count == 1
    assert result.explored_evolved_data_read_addresses == (
        _EVOLVED_DATA_READ_ADDRESS,
    )
    assert _domain_values(
        result.explored_evolved_data_read_value_domains,
        _EVOLVED_DATA_READ_ADDRESS,
    ) == (_EVOLVED_DATA_READ_OBSERVED_VALUE,)
    assert result.explored_evolved_fetch_observations == ()
    _assert_single_evolved_read_observation(
        result.explored_evolved_data_read_observations,
        (
            _EVOLVED_DATA_READ_ADDRESS,
            _EVOLVED_DATA_READ_INITIAL_VALUE,
            _EVOLVED_DATA_READ_OBSERVED_VALUE,
            (3, 41, _EVOLVED_DATA_READ_OBSERVED_VALUE),
        ),
    )
    _assert_evolved_read_witness(
        result.explored_evolved_data_read_witness,
        (
            _EVOLVED_DATA_READ_ADDRESS,
            _EVOLVED_DATA_READ_INITIAL_VALUE,
            _EVOLVED_DATA_READ_OBSERVED_VALUE,
            _EVOLVED_DATA_READ_POINTER_PATH,
        ),
    )
    witness = result.explored_evolved_data_read_witness
    assert witness is not None
    assert witness.origin_kind == _WRITER_DATA_WRITE
    assert (
        witness.origin_entry_path_transition_index
        == _EVOLVED_DATA_READ_ORIGIN_TRANSITION
    )


def _assert_entry_noop_observations(result: _WorklistAnalysis) -> None:
    observations = result.explored_committed_data_write_noop_observations
    assert len(observations) == _ENTRY_NOOP_DATA_WRITE_COUNT
    observation = observations[0]
    assert observation.address == _ENTRY_MUTATION_ADDRESS
    assert observation.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert observation.written_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert observation.result_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert not observation.aliases_self_encryption
    state = observation.state
    assert (state.code_pointer, state.data_pointer) == (
        _ENTRY_NOOP_POINTER_PATH[-1]
    )
    assert state.accumulator == 0
    assert not state.eof_seen


def _assert_entry_noop_witness(result: _WorklistAnalysis) -> None:
    witness = result.explored_data_write_noop_witness
    assert witness is not None
    assert witness.address == _ENTRY_MUTATION_ADDRESS
    assert witness.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert witness.written_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert witness.result_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert not witness.aliases_self_encryption
    assert witness.entry_path[-1] == witness.state
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in witness.entry_path
    ) == _ENTRY_NOOP_POINTER_PATH


def _assert_entry_mutation_observations(
    result: _WorklistAnalysis,
) -> None:
    observations = result.explored_effective_data_mutation_observations
    assert len(observations) == _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    assert all(item.address == _ENTRY_MUTATION_ADDRESS for item in observations)
    assert all(
        item.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
        for item in observations
    )
    assert all(
        (item.state.code_pointer, item.state.data_pointer) == (2, 40)
        for item in observations
    )
    assert all(not item.aliases_self_encryption for item in observations)
    assert all(item.written_value == item.result_value for item in observations)
    domain = result.explored_effective_data_mutation_value_domains[0]
    observed_results = {item.result_value for item in observations}
    assert observed_results == set(domain.result_values)
    assert observations[-1].state.eof_seen
    assert observations[-1].result_value == _EOF_ACCUMULATOR


def _assert_entry_mutation_value_domain(result: _WorklistAnalysis) -> None:
    domains = result.explored_effective_data_mutation_value_domains
    assert len(domains) == 1
    domain = domains[0]
    assert domain.address == _ENTRY_MUTATION_ADDRESS
    assert domain.previous_values == (_ENTRY_MUTATION_PREVIOUS_VALUE,)
    assert len(domain.result_values) == _ENTRY_MUTATION_RESULT_DOMAIN_COUNT
    assert domain.result_values[0] == _ENTRY_MUTATION_RESULT_DOMAIN_MINIMUM
    assert domain.result_values[-1] == _ENTRY_MUTATION_RESULT_DOMAIN_MAXIMUM
    assert _ENTRY_MUTATION_RESULT_VALUE in domain.result_values
    _assert_entry_mutation_observations(result)


def _assert_entry_write_value_domains(result: _WorklistAnalysis) -> None:
    data_values = _domain_values(
        result.explored_data_read_value_domains, _ENTRY_MUTATION_ADDRESS
    )
    assert len(data_values) == _ENTRY_DATA_READ_DOMAIN_COUNT
    assert data_values[0] == _ENTRY_MUTATION_RESULT_DOMAIN_MINIMUM
    assert data_values[-1] == _ENTRY_MUTATION_RESULT_DOMAIN_MAXIMUM
    assert _ENTRY_MUTATION_PREVIOUS_VALUE in data_values
    planned_values = _domain_values(
        result.explored_planned_data_write_value_domains,
        _ENTRY_MUTATION_ADDRESS,
    )
    write_values = _domain_values(
        result.explored_committed_data_write_value_domains,
        _ENTRY_MUTATION_ADDRESS,
    )
    assert result.explored_planned_data_write_transition_count == (
        _ENTRY_COMMITTED_DATA_WRITE_COUNT
    )
    assert result.explored_planned_data_write_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    assert planned_values == write_values == data_values
    encryption_outputs = _domain_values(
        result.explored_self_encryption_output_value_domains, 0
    )
    assert encryption_outputs == (111,)


def _assert_entry_evolved_data_read_observations(
    result: _WorklistAnalysis,
) -> None:
    observations = result.explored_evolved_data_read_observations
    assert len(observations) == _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    assert all(item.address == _ENTRY_MUTATION_ADDRESS for item in observations)
    assert all(
        item.initial_value == _ENTRY_MUTATION_PREVIOUS_VALUE
        for item in observations
    )
    assert all(
        (item.state.code_pointer, item.state.data_pointer) == (5, 40)
        for item in observations
    )
    observed_values = tuple(item.observed_value for item in observations)
    mutation_domain = result.explored_effective_data_mutation_value_domains[0]
    assert set(observed_values) == set(mutation_domain.result_values)
    assert observations[-1].state.eof_seen
    assert observations[-1].observed_value == _EOF_ACCUMULATOR


def _assert_entry_evolved_read_counts(result: _WorklistAnalysis) -> None:
    assert result.explored_initial_value_fetch_transition_count == (
        _ENTRY_WRAP_EXPLORED_STATES
    )
    assert result.explored_evolved_fetch_transition_count == 0
    assert result.explored_evolved_fetch_addresses == ()
    assert result.explored_data_read_transition_count == (
        _ENTRY_DATA_READ_TRANSITION_COUNT
    )
    assert result.explored_initial_value_data_read_transition_count == (
        _ENTRY_INITIAL_VALUE_DATA_READ_COUNT
    )
    assert result.explored_initial_value_data_read_addresses == (
        _ENTRY_INITIAL_VALUE_DATA_READ_ADDRESSES
    )
    assert (
        result.explored_initial_value_data_read_transition_count
        + result.explored_evolved_data_read_transition_count
        == result.explored_data_read_transition_count
    )
    assert result.explored_evolved_data_read_transition_count == (
        _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    )
    assert result.explored_evolved_data_read_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    evolved_values = _domain_values(
        result.explored_evolved_data_read_value_domains,
        _ENTRY_MUTATION_ADDRESS,
    )
    mutation_domain = result.explored_effective_data_mutation_value_domains[0]
    assert evolved_values == mutation_domain.result_values
    assert result.explored_evolved_fetch_observations == ()
    _assert_entry_evolved_data_read_observations(result)


def _assert_entry_data_mutation_evidence(result: _WorklistAnalysis) -> None:
    assert result.explored_committed_write_addresses == (
        0, 1, 2, 3, 4, 5, 6, 40
    )
    assert result.explored_self_encryption_addresses == (0, 1, 2, 3, 4, 5, 6)
    assert result.explored_committed_data_write_transition_count == (
        _ENTRY_COMMITTED_DATA_WRITE_COUNT
    )
    assert result.explored_committed_data_write_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    assert result.explored_committed_data_write_noop_transition_count == (
        _ENTRY_NOOP_DATA_WRITE_COUNT
    )
    assert result.explored_committed_data_write_noop_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    _assert_entry_noop_observations(result)
    _assert_entry_noop_witness(result)
    assert (
        result.explored_effective_data_mutation_transition_count
        + result.explored_committed_data_write_noop_transition_count
        == result.explored_committed_data_write_transition_count
    )
    assert result.explored_effective_data_mutation_transition_count == (
        _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    )
    _assert_entry_evolved_read_counts(result)
    assert result.explored_effective_data_mutation_addresses == (
        _ENTRY_MUTATION_ADDRESS,
    )
    _assert_entry_mutation_value_domain(result)
    _assert_entry_write_value_domains(result)
    mutation = result.explored_data_mutation_witness
    assert mutation is not None
    assert tuple(
        (state.code_pointer, state.data_pointer)
        for state in mutation.entry_path
    ) == _ENTRY_MUTATION_POINTER_PATH
    assert mutation.entry_path[-1] == mutation.state
    assert mutation.state.accumulator == _ENTRY_MUTATION_ACCUMULATOR
    assert not mutation.state.eof_seen
    assert mutation.address == _ENTRY_MUTATION_ADDRESS
    assert mutation.previous_value == _ENTRY_MUTATION_PREVIOUS_VALUE
    assert mutation.written_value == _ENTRY_MUTATION_RESULT_VALUE
    assert mutation.result_value == _ENTRY_MUTATION_RESULT_VALUE
    assert not mutation.aliases_self_encryption


def test_entry_reachable_wrap_publishes_exact_event_witness() -> None:
    """The first reachable wrap binds its source path and result pointers."""
    result = worklist.analyze_reachability(
        _ENTRY_WRAP_SOURCE,
        maximum_states=_ENTRY_WRAP_WITNESS_STATE_LIMIT,
    )
    assert result.explored_wraparound_transition_count == 1
    assert result.explored_code_pointer_wrap_transition_count == 0
    assert result.explored_data_pointer_wrap_transition_count == 1
    assert result.explored_simultaneous_pointer_wrap_transition_count == 0
    signatures = result.explored_wraparound_transition_signatures
    assert len(signatures) == 1
    source_code, source_data = _ENTRY_WRAP_POINTER_PATH[-1]
    _assert_wrap_signature(
        signatures[0],
        (
            source_code,
            source_data,
            _ENTRY_WRAP_RESULT_CODE_POINTER,
            0,
            False,
            True,
        ),
    )
    witness = result.explored_wraparound_witness
    assert witness is not None
    assert result.explored_code_pointer_wrap_witness is None
    assert result.explored_data_pointer_wrap_witness == witness
    assert result.explored_simultaneous_pointer_wrap_witness is None
    assert tuple(
        (state.code_pointer, state.data_pointer) for state in witness.entry_path
    ) == _ENTRY_WRAP_POINTER_PATH
    assert witness.entry_path[-1] == witness.state
    assert witness.state.eof_seen
    assert witness.result_code_pointer == _ENTRY_WRAP_RESULT_CODE_POINTER
    assert witness.result_data_pointer == 0
    assert not witness.code_pointer_wrapped
    assert witness.data_pointer_wrapped
    _assert_entry_data_mutation_evidence(result)


def test_eof_branch_reaches_exact_pointer_wrap_from_entry() -> None:
    """EOF self-modification reaches a real D=59048 successor wrap."""
    admission = worklist.analyze_reachability(
        _ENTRY_WRAP_SOURCE,
        maximum_states=_WRAP_STATE_LIMIT,
    )
    assert admission.truncated
    node = worklist._ReachabilityNode(
        snapshot=prefix_transfer.StateSnapshot(1, 0, 0, 0, ()),
        eof_seen=False,
    )
    final_step: _SnapshotStep | None = None
    for transition_index, expected_pointers in enumerate(
        _ENTRY_WRAP_POINTER_PATH,
        start=1,
    ):
        assert (node.snapshot.code_pointer, node.snapshot.data_pointer) == (
            expected_pointers
        )
        step = prefix_transfer.analyze_state_snapshot(
            _ENTRY_WRAP_SOURCE,
            node.snapshot,
        )
        final_step = step
        successors = worklist._successors(node, step)
        if transition_index == 1:
            node = next(
                successor for successor in successors if successor.eof_seen
            )
        else:
            assert len(successors) == 1
            node = successors[0]
        if transition_index == _WRAP_WRITE_TRANSITION:
            assert (40, _WRAP_ADDRESS) in node.snapshot.memory_overrides
    assert final_step is not None
    assert final_step.transition.pointer_wraps
    assert final_step.transition.result_data_pointer == 0


def test_worklist_state_limit_is_fail_closed() -> None:
    """State budgets accept only the reviewed exact interval."""
    for invalid in (4_097, 0, -1, True):
        with pytest.raises(ValueError, match=_STATE_LIMIT_MESSAGE):
            _ = worklist.analyze_reachability(
                _INPUT_HALT_SOURCE,
                maximum_states=invalid,
            )


def test_worklist_rejects_nonadmitted_loaded_image() -> None:
    """Graph exploration never bypasses classic load-decode admission."""
    with pytest.raises(AssertionError, match=_ADMISSION_MESSAGE):
        _ = worklist.analyze_reachability((33, 38), maximum_states=1)
