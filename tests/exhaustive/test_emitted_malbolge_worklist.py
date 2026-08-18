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


_INPUT_HALT_SOURCE = (117, 80)
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
_EVOLVED_FETCH_SOURCE = tuple(b"(&&$^")
_EVOLVED_FETCH_STATE_LIMIT = 6
_EVOLVED_FETCH_ADDRESS = 95
_EVOLVED_FETCH_INITIAL_VALUE = 29_430
_EVOLVED_FETCH_OBSERVED_VALUE = 9_810
_EVOLVED_FETCH_ORIGIN_TRANSITION = 4
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
_INPUT_VALUE_COUNT = 257
_INVALID_ENCRYPTION_STATUS = "rejected-invalid-self-encryption"
_BYTE_VALUE_COUNT = 256
_DOUBLE_INPUT_BRANCH_POINTS = 1 + _BYTE_VALUE_COUNT
_EOF_ACCUMULATOR = 59_048
_WRAP_ADDRESS = 59_048
_WRAP_SOURCE_VALUE = 52
_WRAP_STATE_LIMIT = 1
_ENTRY_WRAP_WITNESS_STATE_LIMIT = 1_544
_ENTRY_WRAP_SOURCE = tuple(b"u'<%$#>=<;:987654321NN")
_ENTRY_WRAP_POINTER_PATH = ((0, 0), (1, 1), (2, 40), (3, 41), (4, 79), (5, 40))
_ENTRY_WRAP_RESULT_CODE_POINTER = 6
_ENTRY_MUTATION_POINTER_PATH = ((0, 0), (1, 1), (2, 40))
_ENTRY_MUTATION_ACCUMULATOR = 1
_ENTRY_MUTATION_ADDRESS = 40
_ENTRY_MUTATION_PREVIOUS_VALUE = 29_524
_ENTRY_MUTATION_RESULT_VALUE = 29_523
_ENTRY_EFFECTIVE_DATA_MUTATION_COUNT = 256
_ENTRY_COMMITTED_DATA_WRITE_COUNT = 257
_ENTRY_MUTATION_RESULT_DOMAIN_COUNT = 256
_ENTRY_MUTATION_RESULT_DOMAIN_MINIMUM = 29_269
_ENTRY_MUTATION_RESULT_DOMAIN_MAXIMUM = 59_048
_ENTRY_DATA_READ_DOMAIN_COUNT = 257
_INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT = 58
_INPUT_CRAZY_ENCRYPTION_DOMAIN_MINIMUM = 32
_INPUT_CRAZY_ENCRYPTION_DOMAIN_MAXIMUM = 29_555
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


class _WorklistValueDomain(Protocol):
    address: int
    values: tuple[int, ...]


class _WorklistEvolvedReadWitness(Protocol):
    state: _WorklistCycleState
    entry_path: tuple[_WorklistCycleState, ...]
    address: int
    initial_value: int
    observed_value: int
    origin_kind: str
    origin_entry_path_transition_index: int


class _WorklistDataMutationValueDomain(Protocol):
    address: int
    previous_values: tuple[int, ...]
    result_values: tuple[int, ...]


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
    reachable_cycle_detected: bool
    reachable_cycle_witness: tuple[_WorklistCycleState, ...]
    reachable_cycle_entry_path: tuple[_WorklistCycleState, ...]
    known_graph_strong_component_count: int
    known_graph_cyclic_component_count: int
    known_graph_cyclic_state_count: int
    known_graph_largest_cyclic_component_states: int
    closed_recurrent_component_count: int | None
    closed_recurrent_state_count: int | None
    closed_recurrent_largest_component_states: int | None
    closed_recurrent_cycle_witness: tuple[_WorklistCycleState, ...] | None
    closed_recurrent_entry_path: tuple[_WorklistCycleState, ...] | None
    input_branch_points: int
    terminal_status_counts: tuple[tuple[str, int], ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[_WorklistTerminalWitness, ...]
    explored_code_data_alias_transition_count: int
    explored_committed_write_count: int
    explored_committed_write_addresses: tuple[int, ...]
    explored_planned_data_write_transition_count: int
    explored_planned_data_write_addresses: tuple[int, ...]
    explored_planned_data_write_value_domains: tuple[_WorklistValueDomain, ...]
    explored_committed_data_write_transition_count: int
    explored_committed_data_write_addresses: tuple[int, ...]
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
    explored_committed_data_write_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_self_encryption_output_value_domains: tuple[
        _WorklistValueDomain, ...
    ]
    explored_evolved_fetch_witness: _WorklistEvolvedReadWitness | None
    explored_evolved_data_read_witness: _WorklistEvolvedReadWitness | None
    explored_data_mutation_witness: _WorklistDataMutationWitness | None
    explored_minimum_words: int
    explored_highest_accessed_address: int
    explored_accessed_addresses: tuple[int, ...]
    explored_wraparound_transition_count: int
    explored_wraparound_witness: _WorklistWrapWitness | None
    maximum_first_seen_transition_index: int
    frontier_states: int
    frontier_state_witness: _WorklistCycleState | None
    frontier_entry_path: tuple[_WorklistCycleState, ...] | None
    truncated: bool


class _StrongComponentSummary(Protocol):
    component_count: int
    cyclic_component_count: int
    cyclic_state_count: int
    largest_cyclic_component_states: int
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
    assert result.closed_recurrent_cycle_witness == ()
    assert result.closed_recurrent_entry_path == ()


def _assert_fixed_cycle_closed_recurrence(result: _WorklistAnalysis) -> None:
    assert result.closed_recurrent_component_count == _INPUT_VALUE_COUNT
    assert result.closed_recurrent_state_count == _INPUT_VALUE_COUNT
    assert result.closed_recurrent_largest_component_states == 1
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
    _assert_no_closed_recurrence(result)
    assert result.input_branch_points == 1
    assert result.terminal_status_counts == (("halted", _INPUT_VALUE_COUNT),)
    assert result.closed_terminal_status_counts == ((
        "halted",
        _INPUT_VALUE_COUNT,
    ),)
    assert result.closed_all_paths_terminate is True
    assert result.closed_all_paths_halt is True
    assert result.maximum_first_seen_transition_index == _SECOND_TRANSITION
    assert result.frontier_states == 0
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
    assert result.explored_committed_data_write_value_domains == ()
    encryption_outputs = _domain_values(
        result.explored_self_encryption_output_value_domains, 0
    )
    assert encryption_outputs == (111,)
    encryption_values = _domain_values(
        result.explored_encryption_input_value_domains, 0
    )
    assert encryption_values == (117,)


def test_input_crazy_reports_exact_encryption_input_domain() -> None:
    """Rejected branches retain exact explored encryption-input values."""
    result = worklist.analyze_reachability(
        _INPUT_CRAZY_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    values = _domain_values(result.explored_encryption_input_value_domains, 1)
    assert len(values) == _INPUT_CRAZY_ENCRYPTION_DOMAIN_COUNT
    assert values[0] == _INPUT_CRAZY_ENCRYPTION_DOMAIN_MINIMUM
    assert values[-1] == _INPUT_CRAZY_ENCRYPTION_DOMAIN_MAXIMUM
    assert _domain_values(result.explored_data_read_value_domains, 1) == (61,)
    assert result.explored_planned_data_write_transition_count == (
        _INPUT_VALUE_COUNT
    )
    assert result.explored_planned_data_write_addresses == (1,)
    planned_values = _domain_values(
        result.explored_planned_data_write_value_domains, 1
    )
    assert planned_values == values
    assert result.explored_committed_data_write_value_domains == ()
    encryption_outputs = _domain_values(
        result.explored_self_encryption_output_value_domains, 0
    )
    assert encryption_outputs == (111,)


def test_input_halt_reports_exact_explored_mutation_footprint() -> None:
    """Closed input reachability publishes exact committed mutation evidence."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_FULL_STATE_LIMIT,
    )
    assert result.explored_code_data_alias_transition_count == (
        _FULL_STATE_LIMIT
    )
    assert result.explored_committed_write_count == 1
    assert result.explored_committed_write_addresses == (0,)
    assert result.explored_committed_data_write_transition_count == 0
    assert result.explored_committed_data_write_addresses == ()
    assert result.explored_self_encryption_transition_count == 1
    assert result.explored_self_encryption_addresses == (0,)
    assert result.explored_effective_data_mutation_transition_count == 0
    assert result.explored_effective_data_mutation_addresses == ()
    assert result.explored_effective_data_mutation_value_domains == ()
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
    assert result.explored_committed_write_count == 1
    assert result.explored_committed_write_addresses == (0,)
    assert result.explored_committed_data_write_transition_count == 0
    assert result.explored_committed_data_write_addresses == ()
    assert result.explored_self_encryption_transition_count == 1
    assert result.explored_self_encryption_addresses == (0,)
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


def test_input_worklist_truncates_before_unadmitted_eof_state() -> None:
    """The exact unique-state cap stops before silently dropping a branch."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_TRUNCATED_STATE_LIMIT,
    )
    assert result.unique_states == _TRUNCATED_STATE_LIMIT
    assert result.explored_states == 1
    assert result.input_branch_points == 1
    assert result.terminal_status_counts == ()
    assert result.closed_terminal_status_counts is None
    assert result.closed_all_paths_terminate is None
    assert result.closed_all_paths_halt is None
    assert result.frontier_states == _INPUT_VALUE_COUNT
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
    assert path[-1] == witness
    pointers = tuple(
        (state.code_pointer, state.data_pointer) for state in path
    )
    assert pointers == ((0, 0), (1, 1))
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


def test_near_cap_input_dependent_jump_chain_closes_exact_cycle() -> None:
    """Fourteen post-input jumps close within the reviewed state ceiling."""
    result = worklist.analyze_reachability(
        _NEAR_CAP_INPUT_CYCLE_SOURCE,
        maximum_states=_NEAR_CAP_INPUT_CYCLE_STATE_LIMIT,
    )
    assert result.unique_states == _NEAR_CAP_INPUT_CYCLE_STATE_LIMIT
    assert result.explored_states == _NEAR_CAP_INPUT_CYCLE_STATE_LIMIT
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


def test_reviewed_state_ceiling_truncates_deeper_jump_chain() -> None:
    """The 4,096-state maximum stops before silently closing a deeper graph."""
    result = worklist.analyze_reachability(
        _OVER_CAP_INPUT_CYCLE_SOURCE,
        maximum_states=_MAX_WORKLIST_STATE_LIMIT,
    )
    assert result.unique_states == _MAX_WORKLIST_STATE_LIMIT
    assert result.explored_states == _OVER_CAP_EXPLORED_STATES
    assert result.frontier_states == _INPUT_VALUE_COUNT
    assert result.maximum_first_seen_transition_index == (
        _OVER_CAP_MAXIMUM_FIRST_SEEN_TRANSITION
    )
    assert not result.reachable_cycle_detected
    assert result.reachable_cycle_witness == ()
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
    assert result.explored_wraparound_transition_count == 1
    assert result.explored_highest_accessed_address == _WRAP_ADDRESS
    assert result.explored_minimum_words == _WRAP_ADDRESS + 1
    assert result.truncated


def _assert_evolved_read_witness(
    witness: _WorklistEvolvedReadWitness | None,
    expected: tuple[int, int, int, tuple[tuple[int, int], ...]],
) -> None:
    address, initial_value, observed_value, pointer_path = expected
    assert witness is not None
    assert witness.address == address
    assert witness.initial_value == initial_value
    assert witness.observed_value == observed_value
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
    assert result.explored_effective_data_mutation_transition_count == (
        _ENTRY_EFFECTIVE_DATA_MUTATION_COUNT
    )
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
    witness = result.explored_wraparound_witness
    assert witness is not None
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
