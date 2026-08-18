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
_SECOND_TRANSITION = 2
_GRAPH_KEY_A: _WorklistStateKey = (0, 0, 0, (), False)
_GRAPH_KEY_B: _WorklistStateKey = (1, 0, 0, (), False)
_GRAPH_KEY_C: _WorklistStateKey = (2, 0, 0, (), False)
_GRAPH_KEY_D: _WorklistStateKey = (3, 0, 0, (), False)
_SCC_COMPONENT_COUNT = 3
_SCC_CYCLIC_COMPONENT_COUNT = 2
_SCC_CYCLIC_STATE_COUNT = 3
_SCC_LARGEST_CYCLIC_COMPONENT_STATES = 2
_STATE_LIMIT_MESSAGE = "worklist state limit must be a positive exact integer"
_ADMISSION_MESSAGE = "worklist source is not an admitted classic image"
_ROOT = Path(__file__).resolve().parents[2]
_WORKLIST_MODULE = _ROOT / "verifier" / "emitted_malbolge_worklist.py"


class _Snapshot(Protocol):
    accumulator: int | None


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


class _PrefixModule(Protocol):
    StateSnapshot: _SnapshotFactory


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
    terminal_status_witnesses: tuple[_WorklistTerminalWitness, ...]
    explored_minimum_words: int
    explored_highest_accessed_address: int
    explored_accessed_addresses: tuple[int, ...]
    explored_wraparound_transition_count: int
    maximum_first_seen_transition_index: int
    frontier_states: int
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
    assert result.maximum_first_seen_transition_index == _SECOND_TRANSITION
    assert result.frontier_states == 0
    assert not result.truncated


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
    assert not result.truncated


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


def test_worklist_state_limit_is_fail_closed() -> None:
    """State budgets accept positive exact integers only."""
    for invalid in (0, -1, True):
        with pytest.raises(ValueError, match=_STATE_LIMIT_MESSAGE):
            _ = worklist.analyze_reachability(
                _INPUT_HALT_SOURCE,
                maximum_states=invalid,
            )


def test_worklist_rejects_nonadmitted_loaded_image() -> None:
    """Graph exploration never bypasses classic load-decode admission."""
    with pytest.raises(AssertionError, match=_ADMISSION_MESSAGE):
        _ = worklist.analyze_reachability((33, 38), maximum_states=1)
