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

import pytest

from verifier import emitted_malbolge_prefix as prefix_transfer
from verifier import emitted_malbolge_worklist as worklist

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
_INPUT_VALUE_COUNT = 257
_EOF_ACCUMULATOR = 59_048
_WRAP_ADDRESS = 59_048
_WRAP_SOURCE_VALUE = 52
_WRAP_STATE_LIMIT = 1
_SECOND_TRANSITION = 2
_GRAPH_KEY_A: _WorklistStateKey = (0, 0, 0, (), False)
_GRAPH_KEY_B: _WorklistStateKey = (1, 0, 0, (), False)
_STATE_LIMIT_MESSAGE = "worklist state limit must be a positive exact integer"
_ADMISSION_MESSAGE = "worklist source is not an admitted classic image"


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
    assert result.truncated


def test_tiny_cap_counts_all_pending_input_frontier_states() -> None:
    """Truncation counts unadmitted alternatives, not only the first one."""
    result = worklist.analyze_reachability(
        _INPUT_HALT_SOURCE,
        maximum_states=_TINY_STATE_LIMIT,
    )
    assert result.unique_states == _TINY_STATE_LIMIT
    assert result.frontier_states == _INPUT_VALUE_COUNT
    assert result.truncated


def test_double_input_merges_are_not_silently_discarded() -> None:
    """Second input creates many exact merges while the graph still closes."""
    result = worklist.analyze_reachability(
        _DOUBLE_INPUT_HALT_SOURCE,
        maximum_states=_DOUBLE_INPUT_UNIQUE_STATES,
    )
    assert result.unique_states == _DOUBLE_INPUT_UNIQUE_STATES
    assert result.repeated_state_edges == _DOUBLE_INPUT_REPEATED_EDGES
    assert not result.reachable_cycle_detected
    assert result.input_branch_points == _FULL_STATE_LIMIT
    assert result.terminal_status_counts == (
        ("halted", _INPUT_VALUE_COUNT),
    )
    assert not result.truncated


def test_fixed_fetch_becomes_an_exact_worklist_self_cycle() -> None:
    """Historical non-graphical continue is an exact self-loop edge."""
    result = worklist.analyze_reachability(
        _DOUBLE_INPUT_FIXED_CYCLE_SOURCE,
        maximum_states=_DOUBLE_INPUT_UNIQUE_STATES,
    )
    assert result.unique_states == _DOUBLE_INPUT_UNIQUE_STATES
    assert result.repeated_state_edges == _DOUBLE_INPUT_CYCLE_EDGES
    assert result.reachable_cycle_detected
    assert result.terminal_status_counts == ()
    assert not result.truncated


def test_input_domain_becomes_eof_only_after_eof() -> None:
    """Historical EOF state cannot branch back to later ordinary bytes."""
    snapshot = prefix_transfer.StateSnapshot(
        before_transition=_SECOND_TRANSITION,
        code_pointer=1,
        data_pointer=1,
        accumulator=None,
        memory_overrides=(),
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
    assert worklist._known_graph_has_cycle(
        cycle_edges,
        {_GRAPH_KEY_A, _GRAPH_KEY_B},
    )


def test_explorer_counts_exact_pointer_wrap_transition() -> None:
    """A canonical near-boundary state records C/D wrap to zero."""
    snapshot = prefix_transfer.StateSnapshot(
        before_transition=1,
        code_pointer=_WRAP_ADDRESS,
        data_pointer=_WRAP_ADDRESS,
        accumulator=0,
        memory_overrides=((_WRAP_ADDRESS, _WRAP_SOURCE_VALUE),),
    )
    node = worklist._ReachabilityNode(snapshot=snapshot, eof_seen=False)
    key = worklist._node_key(node)
    explorer = worklist._Explorer(
        words=_INPUT_HALT_SOURCE,
        state_limit=_WRAP_STATE_LIMIT,
        queue=deque((node,)),
        seen={key},
        edges={key: set()},
        terminal_counts={},
        accessed_addresses=set(),
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
