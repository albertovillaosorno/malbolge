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
#   - Finite exact-state reachability over admitted classic Malbolge words.
# - Must-Not:
#   - Explore without an explicit state bound, consume host input, or claim
#     safety beyond the explored graph.
# - Allows:
#   - Inputs: admitted loaded words and one positive exact unique-state limit.
#   - Outputs: deterministic worklist counts and reachable terminal statuses.
#   - Side effects: none.
# - Split-When:
#   - Symbolic input domains or profile-generic reachability need new models.
# - Merge-When:
#   - Another verifier owns the same bounded exact-state graph exploration.
# - Summary:
#   - Bounded worklist exploration for exact classic Malbolge state.
# - Description:
#   - Expands historical byte/EOF input while deduplicating canonical states.
# - Usage:
#   - Called after loaded-word admission or directly by verifier tests.
# - Defaults:
#   - No implicit state budget; callers must supply the bound explicitly.
#

"""Bounded exact-state worklist exploration for classic Malbolge."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import Final

if __package__:
    from verifier import emitted_malbolge_classic as classic
    from verifier import emitted_malbolge_prefix as prefix_transfer
else:
    import emitted_malbolge_classic as classic
    import emitted_malbolge_prefix as prefix_transfer

MAXIMUM_STATE_LIMIT: Final = 4_096

_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_INPUT_OPCODE: Final = ord("/")
_INPUT_BYTES: Final = tuple(range(256))
_DATA_READING_INSTRUCTIONS: Final = frozenset(b"ji*p")
_EOF_ACCUMULATOR: Final = classic.PROFILE_MEMORY_WORDS - 1
_HALTED_STATUS: Final = "halted"
_RECURRENCE_BASE_WORDS: Final = 2
_WRITER_DATA_WRITE: Final = "data-write"
_WRITER_SELF_ENCRYPTION: Final = "self-encryption"

type _StateKey = tuple[
    int,
    int,
    int,
    tuple[tuple[int, int], ...],
    bool,
]

_INITIAL_STATE_KEY: Final[_StateKey] = (0, 0, 0, (), False)


@dataclass(frozen=True, slots=True)
class WorklistCycleState:
    """One exact state in deterministic known-graph witness evidence."""

    code_pointer: int
    data_pointer: int
    accumulator: int
    memory_overrides: tuple[tuple[int, int], ...]
    eof_seen: bool


@dataclass(frozen=True, slots=True)
class WorklistTerminalWitness:
    """One observed terminal status with an exact shortest entry path."""

    status: str
    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]


@dataclass(frozen=True, slots=True)
class WorklistWrapWitness:
    """First exact explored pointer-wrap event and its entry path."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool


@dataclass(frozen=True, slots=True)
class WorklistWrapTransitionSignature:
    """One distinct exact explored pointer-wrap transition shape."""

    source_code_pointer: int
    source_data_pointer: int
    result_code_pointer: int
    result_data_pointer: int
    code_pointer_wrapped: bool
    data_pointer_wrapped: bool


@dataclass(frozen=True, slots=True)
class WorklistTerminalStateSet:
    """Exact explored terminal states for one status."""

    status: str
    states: tuple[WorklistCycleState, ...]


@dataclass(frozen=True, slots=True)
class WorklistValueDomain:
    """Exact observed values for one explored memory address."""

    address: int
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class WorklistCycleClosingRepeatedEdgeWitness:
    """First exact repeated edge whose target lies on the source entry path."""

    source_state: WorklistCycleState
    source_entry_path: tuple[WorklistCycleState, ...]
    target_state: WorklistCycleState
    target_entry_path_state_index: int


@dataclass(frozen=True, slots=True)
class WorklistStateMergeWitness:
    """First exact repeated edge that merges distinct entry paths."""

    source_state: WorklistCycleState
    source_entry_path: tuple[WorklistCycleState, ...]
    target_state: WorklistCycleState
    existing_target_entry_path: tuple[WorklistCycleState, ...]


@dataclass(frozen=True, slots=True)
class WorklistCodeDataAliasObservation:
    """One exact explored C/D alias state and fetched memory value."""

    state: WorklistCycleState
    address: int
    memory_value: int


@dataclass(frozen=True, slots=True)
class WorklistNonGraphicalFetchObservation:
    """One exact explored non-graphical executable fetch state and value."""

    state: WorklistCycleState
    address: int
    value: int


@dataclass(frozen=True, slots=True)
class WorklistCodeDataAliasWitness:
    """First exact entry-reachable C/D alias state for one address."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    memory_value: int


@dataclass(frozen=True, slots=True)
class WorklistNonGraphicalFetchWitness:
    """First exact reachable non-graphical executable fetch."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    value: int


@dataclass(frozen=True, slots=True)
class WorklistPlannedDataWriteObservation:
    """One exact explored planned data-write state and value."""

    state: WorklistCycleState
    address: int
    value: int


@dataclass(frozen=True, slots=True)
class WorklistSelfEncryptionObservation:
    """One exact explored committed self-encryption transition."""

    state: WorklistCycleState
    address: int
    input_value: int
    output_value: int
    data_write_aliases_encryption: bool


@dataclass(frozen=True, slots=True)
class WorklistChangedEncryptionInputObservation:
    """One exact changed-from-initial self-encryption input state."""

    state: WorklistCycleState
    address: int
    initial_value: int
    observed_value: int


@dataclass(frozen=True, slots=True)
class WorklistInitialValueObservation:
    """One exact explored read equal to immutable initial memory."""

    state: WorklistCycleState
    address: int
    value: int


@dataclass(frozen=True, slots=True)
class WorklistEvolvedReadObservation:
    """One exact explored read whose value differs from initial memory."""

    state: WorklistCycleState
    address: int
    initial_value: int
    observed_value: int


@dataclass(frozen=True, slots=True)
class WorklistEvolvedReadWitness:
    """First exact read whose value differs from initial memory."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    initial_value: int
    observed_value: int
    origin_kind: str
    origin_entry_path_transition_index: int
    origin_value: int


@dataclass(frozen=True, slots=True)
class WorklistDataMutationValueDomain:
    """Exact observed pre-write and final values for one mutated address."""

    address: int
    previous_values: tuple[int, ...]
    result_values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class WorklistDataWriteNoopObservation:
    """One exact explored committed data-write final no-op."""

    state: WorklistCycleState
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


@dataclass(frozen=True, slots=True)
class WorklistDataWriteNoopWitness:
    """First exact entry-reachable committed data-write final no-op."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


@dataclass(frozen=True, slots=True)
class WorklistDataMutationObservation:
    """One exact explored effective committed data mutation."""

    state: WorklistCycleState
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


@dataclass(frozen=True, slots=True)
class WorklistDataMutationWitness:
    """First exact explored effective data mutation and its entry path."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    previous_value: int
    written_value: int
    result_value: int
    aliases_self_encryption: bool


@dataclass(frozen=True, slots=True)
class WorklistAnalysis:
    """Deterministic summary of one bounded exact-state exploration."""

    state_limit: int
    unique_states: int
    explored_states: int
    repeated_state_edges: int
    explored_state_merge_transition_count: int
    explored_cycle_closing_repeated_edge_count: int
    explored_cycle_closing_repeated_edge_witness: (
        WorklistCycleClosingRepeatedEdgeWitness | None
    )
    explored_state_merge_witness: WorklistStateMergeWitness | None
    reachable_cycle_detected: bool
    reachable_cycle_witness: tuple[WorklistCycleState, ...]
    reachable_cycle_entry_path: tuple[WorklistCycleState, ...]
    known_graph_strong_component_count: int
    known_graph_cyclic_component_count: int
    known_graph_cyclic_state_count: int
    known_graph_largest_cyclic_component_states: int
    known_graph_cyclic_components: tuple[
        tuple[WorklistCycleState, ...], ...
    ]
    known_graph_cyclic_component_minimum_entry_path_state_counts: (
        tuple[int, ...]
    )
    closed_recurrent_component_count: int | None
    closed_recurrent_state_count: int | None
    closed_recurrent_largest_component_states: int | None
    closed_recurrent_components: (
        tuple[tuple[WorklistCycleState, ...], ...] | None
    )
    closed_recurrent_component_minimum_entry_path_state_counts: (
        tuple[int, ...] | None
    )
    closed_recurrent_cycle_witness: tuple[WorklistCycleState, ...] | None
    closed_recurrent_entry_path: tuple[WorklistCycleState, ...] | None
    input_branch_points: int
    input_branch_states: tuple[WorklistCycleState, ...]
    terminal_status_counts: tuple[tuple[str, int], ...]
    terminal_status_state_sets: tuple[WorklistTerminalStateSet, ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[WorklistTerminalWitness, ...]
    explored_code_pointer_addresses: tuple[int, ...]
    explored_data_pointer_addresses: tuple[int, ...]
    explored_code_data_alias_transition_count: int
    explored_code_data_alias_addresses: tuple[int, ...]
    explored_code_data_alias_observations: tuple[
        WorklistCodeDataAliasObservation, ...
    ]
    explored_code_data_alias_witnesses: tuple[WorklistCodeDataAliasWitness, ...]
    explored_committed_write_count: int
    explored_committed_write_addresses: tuple[int, ...]
    explored_planned_data_write_transition_count: int
    explored_planned_data_write_addresses: tuple[int, ...]
    explored_planned_data_write_value_domains: tuple[WorklistValueDomain, ...]
    explored_planned_data_write_observations: tuple[
        WorklistPlannedDataWriteObservation, ...
    ]
    explored_committed_data_write_transition_count: int
    explored_committed_data_write_addresses: tuple[int, ...]
    explored_committed_data_write_noop_transition_count: int
    explored_committed_data_write_noop_addresses: tuple[int, ...]
    explored_committed_data_write_noop_observations: tuple[
        WorklistDataWriteNoopObservation, ...
    ]
    explored_self_encryption_transition_count: int
    explored_self_encryption_addresses: tuple[int, ...]
    explored_self_encryption_observations: tuple[
        WorklistSelfEncryptionObservation, ...
    ]
    explored_effective_data_mutation_transition_count: int
    explored_effective_data_mutation_addresses: tuple[int, ...]
    explored_effective_data_mutation_value_domains: tuple[
        WorklistDataMutationValueDomain, ...
    ]
    explored_effective_data_mutation_observations: tuple[
        WorklistDataMutationObservation, ...
    ]
    explored_fetch_value_domains: tuple[WorklistValueDomain, ...]
    explored_non_graphical_fetch_transition_count: int
    explored_non_graphical_fetch_addresses: tuple[int, ...]
    explored_non_graphical_fetch_value_domains: tuple[WorklistValueDomain, ...]
    explored_non_graphical_fetch_observations: tuple[
        WorklistNonGraphicalFetchObservation, ...
    ]
    explored_non_graphical_fetch_witness: (
        WorklistNonGraphicalFetchWitness | None
    )
    explored_data_read_value_domains: tuple[WorklistValueDomain, ...]
    explored_encryption_input_value_domains: tuple[WorklistValueDomain, ...]
    explored_encryption_input_transition_count: int
    explored_initial_value_encryption_input_transition_count: int
    explored_initial_value_encryption_input_addresses: tuple[int, ...]
    explored_initial_value_encryption_input_observations: tuple[
        WorklistInitialValueObservation, ...
    ]
    explored_changed_from_initial_encryption_input_transition_count: int
    explored_changed_from_initial_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_value_domains: tuple[
        WorklistValueDomain, ...
    ]
    explored_changed_from_initial_encryption_input_observations: tuple[
        WorklistChangedEncryptionInputObservation, ...
    ]
    explored_committed_data_write_value_domains: tuple[WorklistValueDomain, ...]
    explored_self_encryption_output_value_domains: tuple[
        WorklistValueDomain, ...
    ]
    explored_initial_value_fetch_transition_count: int
    explored_initial_value_fetch_addresses: tuple[int, ...]
    explored_initial_value_fetch_observations: tuple[
        WorklistInitialValueObservation, ...
    ]
    explored_evolved_fetch_transition_count: int
    explored_evolved_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_value_domains: tuple[WorklistValueDomain, ...]
    explored_evolved_fetch_observations: tuple[
        WorklistEvolvedReadObservation, ...
    ]
    explored_data_read_transition_count: int
    explored_initial_value_data_read_transition_count: int
    explored_initial_value_data_read_addresses: tuple[int, ...]
    explored_initial_value_data_read_observations: tuple[
        WorklistInitialValueObservation, ...
    ]
    explored_evolved_data_read_transition_count: int
    explored_evolved_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_value_domains: tuple[WorklistValueDomain, ...]
    explored_evolved_data_read_observations: tuple[
        WorklistEvolvedReadObservation, ...
    ]
    explored_evolved_fetch_witness: WorklistEvolvedReadWitness | None
    explored_evolved_data_read_witness: WorklistEvolvedReadWitness | None
    explored_data_write_noop_witness: WorklistDataWriteNoopWitness | None
    explored_data_mutation_witness: WorklistDataMutationWitness | None
    explored_minimum_words: int
    explored_highest_accessed_address: int
    explored_accessed_addresses: tuple[int, ...]
    explored_wraparound_transition_count: int
    explored_code_pointer_wrap_transition_count: int
    explored_data_pointer_wrap_transition_count: int
    explored_simultaneous_pointer_wrap_transition_count: int
    explored_wraparound_transition_signatures: tuple[
        WorklistWrapTransitionSignature, ...
    ]
    explored_wraparound_witness: WorklistWrapWitness | None
    explored_code_pointer_wrap_witness: WorklistWrapWitness | None
    explored_data_pointer_wrap_witness: WorklistWrapWitness | None
    explored_simultaneous_pointer_wrap_witness: WorklistWrapWitness | None
    maximum_first_seen_transition_index: int
    frontier_states: int
    frontier_state_set: tuple[WorklistCycleState, ...]
    frontier_state_witness: WorklistCycleState | None
    frontier_entry_path: tuple[WorklistCycleState, ...] | None
    truncated: bool


@dataclass(frozen=True, slots=True)
class _StrongComponentSummary:
    """Exact SCC counts over only the admitted known directed graph."""

    component_count: int
    cyclic_component_count: int
    cyclic_state_count: int
    largest_cyclic_component_states: int
    cyclic_components: tuple[tuple[_StateKey, ...], ...]
    cyclic_sink_components: tuple[tuple[_StateKey, ...], ...]


@dataclass(frozen=True, slots=True)
class _ClosedRecurrenceEvidence:
    """Nullable recurrent sink evidence after complete graph closure."""

    component_count: int | None
    state_count: int | None
    largest_component_states: int | None
    components: tuple[tuple[WorklistCycleState, ...], ...] | None
    minimum_entry_path_state_counts: tuple[int, ...] | None
    cycle_witness: tuple[WorklistCycleState, ...] | None
    entry_path: tuple[WorklistCycleState, ...] | None


@dataclass(frozen=True, slots=True)
class _ReachabilityNode:
    snapshot: prefix_transfer.StateSnapshot
    eof_seen: bool


def _state_limit(value: object) -> int:
    if type(value) is int and 1 <= value <= MAXIMUM_STATE_LIMIT:
        return value
    message = (
        "worklist state limit must be an exact integer from 1 through "
        f"{MAXIMUM_STATE_LIMIT}"
    )
    raise ValueError(message)


def _validate_words(words: tuple[int, ...]) -> None:
    if not _RECURRENCE_BASE_WORDS <= len(words) <= classic.PROFILE_MEMORY_WORDS:
        message = "worklist source is outside historical loader capacity"
        raise AssertionError(message)
    for position, value in enumerate(words):
        decoded = classic.decode(value, position)
        if decoded not in _ALLOWED_INSTRUCTIONS:
            message = "worklist source is not an admitted classic image"
            raise AssertionError(message)


def _expanded_initial_memory(words: tuple[int, ...]) -> tuple[int, ...]:
    memory = list(words)
    while len(memory) < classic.PROFILE_MEMORY_WORDS:
        memory.append(classic.crazy(memory[-2], memory[-1]))
    return tuple(memory)


def _node_key(node: _ReachabilityNode) -> _StateKey:
    snapshot = node.snapshot
    accumulator = snapshot.accumulator
    if accumulator is None:
        message = "worklist queue cannot retain an unknown accumulator"
        raise AssertionError(message)
    return (
        snapshot.code_pointer,
        snapshot.data_pointer,
        accumulator,
        snapshot.memory_overrides,
        node.eof_seen,
    )


def _with_accumulator(
    snapshot: prefix_transfer.StateSnapshot,
    accumulator: int,
) -> prefix_transfer.StateSnapshot:
    return prefix_transfer.StateSnapshot(
        before_transition=snapshot.before_transition,
        code_pointer=snapshot.code_pointer,
        data_pointer=snapshot.data_pointer,
        accumulator=accumulator,
        memory_overrides=snapshot.memory_overrides,
    )


def _input_successors(
    snapshot: prefix_transfer.StateSnapshot,
    *,
    eof_seen: bool,
) -> tuple[_ReachabilityNode, ...]:
    eof_snapshot = _with_accumulator(snapshot, _EOF_ACCUMULATOR)
    if eof_seen:
        return (_ReachabilityNode(snapshot=eof_snapshot, eof_seen=True),)
    byte_nodes = tuple(
        _ReachabilityNode(
            snapshot=_with_accumulator(snapshot, value),
            eof_seen=False,
        )
        for value in _INPUT_BYTES
    )
    eof_node = _ReachabilityNode(snapshot=eof_snapshot, eof_seen=True)
    return (*byte_nodes, eof_node)


def _successors(
    node: _ReachabilityNode,
    step: prefix_transfer.SnapshotStep,
) -> tuple[_ReachabilityNode, ...]:
    successor = step.successor
    if successor is None:
        return (node,) if step.transition.provable_cycle else ()
    if step.transition.decoded_byte == _INPUT_OPCODE:
        return _input_successors(successor, eof_seen=node.eof_seen)
    if successor.accumulator is None:
        message = "non-input worklist successor lost a concrete accumulator"
        raise AssertionError(message)
    return (_ReachabilityNode(snapshot=successor, eof_seen=node.eof_seen),)


def _transition_accesses(
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


def _unseen_successor_keys(
    successors: tuple[_ReachabilityNode, ...],
    seen: set[_StateKey],
    *,
    start_index: int,
) -> tuple[_StateKey, ...]:
    unseen = {
        _node_key(successor)
        for successor in successors[start_index:]
        if _node_key(successor) not in seen
    }
    return tuple(sorted(unseen))


def _known_targets(
    source: _StateKey,
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> tuple[_StateKey, ...]:
    return tuple(
        sorted(
            target
            for target in edges.get(source, set())
            if target in nodes
        )
    )


def _finish_order_component(
    root: _StateKey,
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    visited: set[_StateKey],
) -> tuple[_StateKey, ...]:
    finished: list[_StateKey] = []
    visited.add(root)
    stack: list[tuple[_StateKey, bool]] = [(root, False)]
    while stack:
        source, expanded = stack.pop()
        if expanded:
            finished.append(source)
            continue
        stack.append((source, True))
        for target in reversed(_known_targets(source, edges, nodes)):
            if target in visited:
                continue
            visited.add(target)
            stack.append((target, False))
    return tuple(finished)


def _known_graph_finish_order(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> tuple[_StateKey, ...]:
    visited: set[_StateKey] = set()
    finished: list[_StateKey] = []
    for root in sorted(nodes):
        if root in visited:
            continue
        finished.extend(
            _finish_order_component(root, edges, nodes, visited=visited)
        )
    return tuple(finished)


def _reverse_known_edges(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> dict[_StateKey, set[_StateKey]]:
    reverse: dict[_StateKey, set[_StateKey]] = {
        node: set() for node in nodes
    }
    for source in sorted(nodes):
        for target in _known_targets(source, edges, nodes):
            reverse[target].add(source)
    return reverse


def _reverse_component(
    root: _StateKey,
    reverse_edges: dict[_StateKey, set[_StateKey]],
    visited: set[_StateKey],
) -> tuple[_StateKey, ...]:
    component: list[_StateKey] = []
    visited.add(root)
    stack = [root]
    while stack:
        source = stack.pop()
        component.append(source)
        for target in reversed(tuple(sorted(reverse_edges[source]))):
            if target in visited:
                continue
            visited.add(target)
            stack.append(target)
    return tuple(sorted(component))


def _known_graph_strong_components(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> tuple[tuple[_StateKey, ...], ...]:
    finish_order = _known_graph_finish_order(edges, nodes)
    reverse_edges = _reverse_known_edges(edges, nodes)
    visited: set[_StateKey] = set()
    components: list[tuple[_StateKey, ...]] = []
    for root in reversed(finish_order):
        if root in visited:
            continue
        components.append(_reverse_component(root, reverse_edges, visited))
    return tuple(sorted(components))


def _component_is_cyclic(
    component: tuple[_StateKey, ...],
    edges: dict[_StateKey, set[_StateKey]],
) -> bool:
    if len(component) > 1:
        return True
    if not component:
        return False
    node = component[0]
    return node in edges.get(node, set())


def _component_is_sink(
    component: tuple[_StateKey, ...],
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> bool:
    members = set(component)
    return all(
        target in members
        for source in component
        for target in _known_targets(source, edges, nodes)
    )


def _known_graph_strong_component_summary(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> _StrongComponentSummary:
    components = _known_graph_strong_components(edges, nodes)
    cyclic_components = tuple(
        component
        for component in components
        if _component_is_cyclic(component, edges)
    )
    cyclic_sizes = tuple(map(len, cyclic_components))
    cyclic_sinks = tuple(
        component
        for component in cyclic_components
        if _component_is_sink(component, edges, nodes)
    )
    return _StrongComponentSummary(
        component_count=len(components),
        cyclic_component_count=len(cyclic_sizes),
        cyclic_state_count=sum(cyclic_sizes),
        largest_cyclic_component_states=max(cyclic_sizes, default=0),
        cyclic_components=cyclic_components,
        cyclic_sink_components=cyclic_sinks,
    )


def _cycle_from_back_edge(
    source: _StateKey,
    target: _StateKey,
    parents: dict[_StateKey, _StateKey],
) -> tuple[_StateKey, ...]:
    path = [source]
    cursor = source
    while cursor != target:
        cursor = parents[cursor]
        path.append(cursor)
    path.reverse()
    return tuple(path)


def _cycle_component_witness(
    root: _StateKey,
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    colors: dict[_StateKey, int],
) -> tuple[_StateKey, ...]:
    parents: dict[_StateKey, _StateKey] = {}
    colors[root] = 1
    stack = [(root, _known_targets(root, edges, nodes), 0)]
    while stack:
        source, targets, index = stack[-1]
        if index >= len(targets):
            colors[source] = 2
            _ = stack.pop()
            continue
        target = targets[index]
        stack[-1] = (source, targets, index + 1)
        target_color = colors.get(target, 0)
        if target_color == 0:
            parents[target] = source
            colors[target] = 1
            stack.append((target, _known_targets(target, edges, nodes), 0))
        elif target_color == 1:
            return _cycle_from_back_edge(source, target, parents)
    return ()


def _known_graph_cycle_witness(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
) -> tuple[_StateKey, ...]:
    colors: dict[_StateKey, int] = {}
    for root in sorted(nodes):
        if colors.get(root, 0) != 0:
            continue
        witness = _cycle_component_witness(
            root, edges, nodes, colors=colors
        )
        if witness:
            return witness
    return ()


def _known_graph_has_cycle(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    witness: tuple[_StateKey, ...] | None = None,
) -> bool:
    cycle = (
        _known_graph_cycle_witness(edges, nodes)
        if witness is None
        else witness
    )
    return bool(cycle)


def _reconstruct_known_path(
    parents: dict[_StateKey, _StateKey | None],
    target: _StateKey,
) -> tuple[_StateKey, ...]:
    if target not in parents:
        return ()
    reverse_path: list[_StateKey] = []
    cursor: _StateKey | None = target
    while cursor is not None:
        reverse_path.append(cursor)
        cursor = parents[cursor]
    return tuple(reversed(reverse_path))


def _known_graph_shortest_path(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    start: _StateKey,
    target: _StateKey,
) -> tuple[_StateKey, ...]:
    if start not in nodes or target not in nodes:
        return ()
    parents: dict[_StateKey, _StateKey | None] = {start: None}
    queue = deque((start,))
    while queue and target not in parents:
        source = queue.popleft()
        for successor in _known_targets(source, edges, nodes):
            if successor in parents:
                continue
            parents[successor] = source
            queue.append(successor)
    return _reconstruct_known_path(parents, target)


def _known_graph_shortest_path_to_any(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    start: _StateKey,
    targets: set[_StateKey],
) -> tuple[_StateKey, ...]:
    parents: dict[_StateKey, _StateKey | None] = {start: None}
    queue = deque((start,))
    while queue:
        source = queue.popleft()
        if source in targets:
            return _reconstruct_known_path(parents, source)
        for successor in _known_targets(source, edges, nodes):
            if successor in parents:
                continue
            parents[successor] = source
            queue.append(successor)
    return ()


def _known_graph_shortest_distances(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    *,
    start: _StateKey,
) -> dict[_StateKey, int]:
    if start not in nodes:
        return {}
    distances = {start: 0}
    queue = deque((start,))
    while queue:
        source = queue.popleft()
        distance = distances[source] + 1
        for successor in _known_targets(source, edges, nodes):
            if successor in distances:
                continue
            distances[successor] = distance
            queue.append(successor)
    return distances


def _component_minimum_entry_path_state_counts(
    components: tuple[tuple[_StateKey, ...], ...],
    distances: dict[_StateKey, int],
) -> tuple[int, ...]:
    counts: list[int] = []
    for component in components:
        component_distances = tuple(
            distances[key] for key in component if key in distances
        )
        if not component_distances:
            message = "cyclic SCC lost entry reachability"
            raise AssertionError(message)
        counts.append(min(component_distances) + 1)
    return tuple(counts)


def _cycle_state(key: _StateKey) -> WorklistCycleState:
    code_pointer, data_pointer, accumulator, memory_overrides, eof_seen = key
    return WorklistCycleState(
        code_pointer=code_pointer,
        data_pointer=data_pointer,
        accumulator=accumulator,
        memory_overrides=memory_overrides,
        eof_seen=eof_seen,
    )


def _cycle_components(
    components: tuple[tuple[_StateKey, ...], ...],
) -> tuple[tuple[WorklistCycleState, ...], ...]:
    return tuple(
        tuple(_cycle_state(key) for key in component)
        for component in components
    )


def _terminal_state_sets(
    terminal_states: dict[str, set[_StateKey]],
) -> tuple[WorklistTerminalStateSet, ...]:
    return tuple(
        WorklistTerminalStateSet(
            status=status,
            states=tuple(_cycle_state(key) for key in sorted(states)),
        )
        for status, states in sorted(terminal_states.items())
    )


def _terminal_witnesses(
    edges: dict[_StateKey, set[_StateKey]],
    nodes: set[_StateKey],
    terminal_states: dict[str, set[_StateKey]],
) -> tuple[WorklistTerminalWitness, ...]:
    witnesses: list[WorklistTerminalWitness] = []
    for status, targets in sorted(terminal_states.items()):
        path = _known_graph_shortest_path_to_any(
            edges,
            nodes,
            start=_INITIAL_STATE_KEY,
            targets=targets,
        )
        if not path:
            message = "observed terminal lost its exact entry path"
            raise AssertionError(message)
        witnesses.append(
            WorklistTerminalWitness(
                status=status,
                state=_cycle_state(path[-1]),
                entry_path=tuple(_cycle_state(key) for key in path),
            )
        )
    return tuple(witnesses)


def _closed_recurrence_evidence(
    summary: _StrongComponentSummary,
    edges: dict[_StateKey, set[_StateKey]],
    *,
    nodes: set[_StateKey],
    truncated: bool,
) -> _ClosedRecurrenceEvidence:
    if truncated:
        return _ClosedRecurrenceEvidence(
            None, None, None, None, None, None, None
        )
    components = summary.cyclic_sink_components
    distances = _known_graph_shortest_distances(
        edges,
        nodes,
        start=_INITIAL_STATE_KEY,
    )
    witness_keys = (
        _known_graph_cycle_witness(edges, set(components[0]))
        if components
        else ()
    )
    if bool(witness_keys) != bool(components):
        message = "closed recurrent SCC lost deterministic witness"
        raise AssertionError(message)
    entry_path_keys = (
        _known_graph_shortest_path(
            edges,
            nodes,
            start=_INITIAL_STATE_KEY,
            target=witness_keys[0],
        )
        if witness_keys
        else ()
    )
    if bool(entry_path_keys) != bool(witness_keys):
        message = "closed recurrent SCC lost exact entry path"
        raise AssertionError(message)
    return _ClosedRecurrenceEvidence(
        component_count=len(components),
        state_count=sum(map(len, components)),
        largest_component_states=max(map(len, components), default=0),
        components=_cycle_components(components),
        minimum_entry_path_state_counts=(
            _component_minimum_entry_path_state_counts(components, distances)
        ),
        cycle_witness=tuple(_cycle_state(key) for key in witness_keys),
        entry_path=tuple(_cycle_state(key) for key in entry_path_keys),
    )


def _exact_committed_write_address(
    address: int | None,
    value: int | None,
    *,
    label: str,
) -> int | None:
    if address is None:
        return None
    if value is None:
        message = f"committed {label} lost its exact value"
        raise AssertionError(message)
    return address


def _committed_mutation_addresses(
    step: prefix_transfer.SnapshotStep,
) -> tuple[int | None, int | None]:
    if step.successor is None:
        return None, None
    transition = step.transition
    return (
        _exact_committed_write_address(
            transition.planned_data_write_address,
            transition.planned_data_write_value,
            label="data write",
        ),
        _exact_committed_write_address(
            transition.encryption_address,
            transition.encryption_output,
            label="self-encryption",
        ),
    )


def _snapshot_from_key(
    key: _StateKey,
    *,
    before_transition: int,
) -> prefix_transfer.StateSnapshot:
    code_pointer, data_pointer, accumulator, overrides, _ = key
    return prefix_transfer.StateSnapshot(
        before_transition=before_transition,
        code_pointer=code_pointer,
        data_pointer=data_pointer,
        accumulator=accumulator,
        memory_overrides=overrides,
    )


def _required_exact_value(value: int | None, *, label: str) -> int:
    if value is None:
        message = f"{label} lost its exact value"
        raise AssertionError(message)
    return value


def _entry_path_last_writer(
    initial_memory: tuple[int, ...],
    path: tuple[_StateKey, ...],
    address: int,
) -> tuple[str, int, int] | None:
    writer: tuple[str, int, int] | None = None
    for transition_index, key in enumerate(path[:-1], start=1):
        step = prefix_transfer.analyze_state_snapshot(
            initial_memory,
            _snapshot_from_key(key, before_transition=transition_index),
        )
        transition = step.transition
        data_write, encryption = _committed_mutation_addresses(step)
        if data_write == address:
            value = _required_exact_value(
                transition.planned_data_write_value, label="writer data write"
            )
            writer = (_WRITER_DATA_WRITE, transition_index, value)
        if encryption == address:
            value = _required_exact_value(
                transition.encryption_output, label="writer self-encryption"
            )
            writer = (_WRITER_SELF_ENCRYPTION, transition_index, value)
    return writer


def _pointer_wrap_result(
    transition: prefix_transfer.SecondTransition,
) -> tuple[int, int, bool, bool]:
    result_code = transition.result_code_pointer
    result_data = transition.result_data_pointer
    if result_code is None or result_data is None:
        message = "pointer wrap lost exact successor pointers"
        raise AssertionError(message)
    code_wrapped = result_code == 0
    data_wrapped = result_data == 0
    if not code_wrapped and not data_wrapped:
        message = "pointer-wrap flag lacks an exact wrapped pointer"
        raise AssertionError(message)
    return result_code, result_data, code_wrapped, data_wrapped


def _wrap_transition_signature_key(
    signature: WorklistWrapTransitionSignature,
) -> tuple[int, int, int, int, bool, bool]:
    return (
        signature.source_code_pointer,
        signature.source_data_pointer,
        signature.result_code_pointer,
        signature.result_data_pointer,
        signature.code_pointer_wrapped,
        signature.data_pointer_wrapped,
    )


type _WrapCounts = tuple[int, int, int, int]
type _WrapWitnesses = tuple[
    WorklistWrapWitness | None,
    WorklistWrapWitness | None,
    WorklistWrapWitness | None,
    WorklistWrapWitness | None,
]


type _WriteCounts = tuple[int, int, int, int, int]
type _WriteAddressSets = tuple[
    set[int],
    set[int],
    set[int],
    set[int],
    set[int],
]


def _assert_wrap_witness_flags(
    witness: WorklistWrapWitness,
    *,
    require_code_wrap: bool = False,
    require_data_wrap: bool = False,
) -> None:
    code_result_wrapped = witness.result_code_pointer == 0
    data_result_wrapped = witness.result_data_pointer == 0
    if (
        code_result_wrapped != witness.code_pointer_wrapped
        or data_result_wrapped != witness.data_pointer_wrapped
    ):
        message = "pointer-wrap witness flags disagree with result pointers"
        raise AssertionError(message)
    if not witness.code_pointer_wrapped and not witness.data_pointer_wrapped:
        message = "pointer-wrap witness lacks a wrapped pointer"
        raise AssertionError(message)
    if require_code_wrap and not witness.code_pointer_wrapped:
        message = "code-pointer wrap witness lacks a code-pointer wrap"
        raise AssertionError(message)
    if require_data_wrap and not witness.data_pointer_wrapped:
        message = "data-pointer wrap witness lacks a data-pointer wrap"
        raise AssertionError(message)


def _assert_wrap_count_partition(counts: _WrapCounts) -> None:
    total, code, data, simultaneous = counts
    if simultaneous > min(code, data):
        message = "simultaneous wrap count exceeds a pointer-wrap class"
        raise AssertionError(message)
    if code + data - simultaneous != total:
        message = "pointer-wrap class counts disagree with total wraps"
        raise AssertionError(message)


def _assert_wrap_witness_presence(
    counts: _WrapCounts,
    witnesses: _WrapWitnesses,
) -> None:
    labels = ("generic", "code-pointer", "data-pointer", "simultaneous")
    for label, count, witness in zip(labels, counts, witnesses, strict=True):
        if (count > 0) != (witness is not None):
            message = f"{label} wrap count disagrees with witness presence"
            raise AssertionError(message)


def _assert_wrap_evidence_invariants(
    counts: _WrapCounts,
    witnesses: _WrapWitnesses,
) -> None:
    _assert_wrap_count_partition(counts)
    _assert_wrap_witness_presence(counts, witnesses)
    generic, code, data, simultaneous = witnesses
    if generic is not None:
        _assert_wrap_witness_flags(generic)
    if code is not None:
        _assert_wrap_witness_flags(code, require_code_wrap=True)
    if data is not None:
        _assert_wrap_witness_flags(data, require_data_wrap=True)
    if simultaneous is not None:
        _assert_wrap_witness_flags(
            simultaneous,
            require_code_wrap=True,
            require_data_wrap=True,
        )


def _committed_data_mutation(
    step: prefix_transfer.SnapshotStep,
) -> tuple[int, int, int, int, bool] | None:
    transition = step.transition
    address = transition.planned_data_write_address
    written = transition.planned_data_write_value
    if step.successor is None or address is None:
        return None
    previous = transition.data_value
    if (
        written is None
        or previous is None
        or address != transition.data_address
    ):
        message = "committed data mutation lost exact data values"
        raise AssertionError(message)
    aliases = transition.data_write_aliases_encryption
    result = transition.encryption_output if aliases else written
    if result is None:
        message = "committed data mutation lost its final value"
        raise AssertionError(message)
    return address, previous, written, result, aliases


def _assert_code_data_alias_observations(
    transition_count: int,
    addresses: set[int],
    observations: dict[_StateKey, int],
) -> None:
    if transition_count != len(observations):
        message = "code/data alias count disagrees with exact alias states"
        raise AssertionError(message)
    observed_addresses = {state[0] for state in observations}
    if addresses != observed_addresses:
        message = "code/data alias addresses disagree with exact alias states"
        raise AssertionError(message)
    if any(state[0] != state[1] for state in observations):
        message = "code/data alias observation lost exact C=D identity"
        raise AssertionError(message)


def _assert_input_branch_evidence(
    branch_count: int,
    branch_states: set[_StateKey],
    seen: set[_StateKey],
) -> None:
    if branch_count != len(branch_states):
        message = "input branch count disagrees with exact branch states"
        raise AssertionError(message)
    if not branch_states <= seen:
        message = "input branch evidence retained an unknown graph state"
        raise AssertionError(message)
    if any(state[-1] for state in branch_states):
        message = "input branch evidence retained an EOF-seen state"
        raise AssertionError(message)


def _assert_frontier_evidence(
    frontier_states: int,
    frontier_state_keys: tuple[_StateKey, ...],
    frontier_path: tuple[_StateKey, ...] | None,
    *,
    truncated: bool,
) -> None:
    if frontier_states != len(frontier_state_keys):
        message = "frontier state count disagrees with exact frontier set"
        raise AssertionError(message)
    if truncated != bool(frontier_state_keys):
        message = "worklist truncation disagrees with exact frontier states"
        raise AssertionError(message)
    if truncated != (frontier_path is not None):
        message = "worklist truncation lost its exact frontier path"
        raise AssertionError(message)
    if (
        frontier_path is not None
        and frontier_path[-1] not in frontier_state_keys
    ):
        message = "worklist frontier path endpoint is outside exact frontier"
        raise AssertionError(message)


def _assert_terminal_evidence(
    counts: dict[str, int],
    terminal_states: dict[str, set[_StateKey]],
    seen: set[_StateKey],
) -> None:
    if set(counts) != set(terminal_states):
        message = "terminal status counts disagree with terminal state classes"
        raise AssertionError(message)
    if any(count <= 0 for count in counts.values()):
        message = "terminal status count must remain positive"
        raise AssertionError(message)
    if any(
        count != len(terminal_states[status])
        for status, count in counts.items()
    ):
        message = "terminal status count disagrees with exact terminal states"
        raise AssertionError(message)
    if any(not states <= seen for states in terminal_states.values()):
        message = "terminal evidence retained an unknown graph state"
        raise AssertionError(message)


def _assert_terminal_graph_endpoints(
    terminal_states: dict[str, set[_StateKey]],
    edges: dict[_StateKey, set[_StateKey]],
) -> None:
    for states in terminal_states.values():
        for state in states:
            if state not in edges:
                message = "terminal evidence is missing its graph node"
                raise AssertionError(message)
            if edges[state]:
                message = "terminal graph endpoint retained an outgoing edge"
                raise AssertionError(message)


def _planned_data_write_projection(
    observations: dict[_StateKey, tuple[int, int]],
) -> tuple[set[int], dict[int, set[int]]]:
    addresses = {address for address, _ in observations.values()}
    values: dict[int, set[int]] = {}
    for address, value in observations.values():
        values.setdefault(address, set()).add(value)
    return addresses, values


def _assert_planned_data_write_observations(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
) -> None:
    transition_count, addresses, values, observations, seen = evidence
    if transition_count != len(observations):
        message = "planned data-write count disagrees with exact states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = "planned data-write evidence retained an unknown state"
        raise AssertionError(message)
    projected_addresses, projected_values = _planned_data_write_projection(
        observations
    )
    if addresses != projected_addresses:
        message = "planned data-write addresses disagree with exact states"
        raise AssertionError(message)
    if values != projected_values:
        message = "planned data-write domains disagree with exact states"
        raise AssertionError(message)


def _changed_encryption_input_projection(
    observations: dict[_StateKey, tuple[int, int]],
) -> tuple[set[int], dict[int, set[int]]]:
    addresses = {address for address, _ in observations.values()}
    values: dict[int, set[int]] = {}
    for address, observed_value in observations.values():
        values.setdefault(address, set()).add(observed_value)
    return addresses, values


def _assert_changed_encryption_input_projection(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
) -> None:
    transition_count, addresses, values, observations, seen = evidence
    if transition_count != len(observations):
        message = (
            "changed encryption-input count disagrees with exact states"
        )
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = "changed encryption-input evidence retained an unknown state"
        raise AssertionError(message)
    projected_addresses, projected_values = (
        _changed_encryption_input_projection(observations)
    )
    if addresses != projected_addresses:
        message = (
            "changed encryption-input addresses disagree with exact states"
        )
        raise AssertionError(message)
    if values != projected_values:
        message = "changed encryption-input domains disagree with exact states"
        raise AssertionError(message)


def _assert_changed_encryption_input_initial_difference(
    observations: dict[_StateKey, tuple[int, int]],
    initial_memory: tuple[int, ...],
) -> None:
    if any(
        observed_value == initial_memory[address]
        for address, observed_value in observations.values()
    ):
        message = "changed encryption-input observation equals initial memory"
        raise AssertionError(message)


def _initial_value_observation_addresses(
    observations: dict[_StateKey, tuple[int, int]],
    initial_memory: tuple[int, ...],
    *,
    label: str,
) -> set[int]:
    addresses: set[int] = set()
    for address, value in observations.values():
        if value != initial_memory[address]:
            message = f"{label} observation differs from initial memory"
            raise AssertionError(message)
        addresses.add(address)
    return addresses


def _assert_observation_state_partition(
    initial_states: set[_StateKey],
    changed_states: set[_StateKey],
    *,
    label: str,
) -> None:
    if initial_states & changed_states:
        message = f"{label} exact state classes overlap"
        raise AssertionError(message)


def _committed_data_write_value_projection(
    planned: dict[_StateKey, tuple[int, int]],
    committed: dict[_StateKey, tuple[int, int, int, int, bool]],
) -> dict[int, set[int]]:
    projected: dict[int, set[int]] = {}
    for state, observation in committed.items():
        address = observation[0]
        written = observation[2]
        if planned[state] != (address, written):
            message = "committed data-write disagrees with planned write"
            raise AssertionError(message)
        projected.setdefault(address, set()).add(written)
    return projected


def _assert_committed_data_write_state_partition(
    evidence: tuple[
        dict[_StateKey, tuple[int, int]],
        dict[_StateKey, tuple[int, int, int, int, bool]],
        dict[_StateKey, tuple[int, int, int, int, bool]],
        dict[int, set[int]],
    ],
) -> None:
    planned, noops, effective, committed_values = evidence
    _assert_observation_state_partition(
        set(noops),
        set(effective),
        label="committed data-write outcome partition",
    )
    committed = noops | effective
    if not set(committed) <= set(planned):
        message = "committed data-write states escape planned writes"
        raise AssertionError(message)
    projected_values = _committed_data_write_value_projection(
        planned, committed
    )
    if committed_values != projected_values:
        message = "committed data-write domains disagree with exact states"
        raise AssertionError(message)


def _assert_read_observation_state_partitions(
    partitions: tuple[tuple[set[_StateKey], set[_StateKey], str], ...],
) -> None:
    for initial_states, changed_states, label in partitions:
        _assert_observation_state_partition(
            initial_states, changed_states, label=label
        )


def _assert_initial_value_observations(
    evidence: tuple[
        int,
        set[int],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
    initial_memory: tuple[int, ...],
    *,
    label: str,
) -> None:
    count, addresses, observations, seen = evidence
    if count != len(observations):
        message = f"{label} count disagrees with exact states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = f"{label} evidence retained an unknown graph state"
        raise AssertionError(message)
    projected = _initial_value_observation_addresses(
        observations, initial_memory, label=label
    )
    if addresses != projected:
        message = f"{label} addresses disagree with exact states"
        raise AssertionError(message)


def _assert_changed_encryption_input_observations(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
    initial_memory: tuple[int, ...],
) -> None:
    _assert_changed_encryption_input_projection(evidence)
    _assert_changed_encryption_input_initial_difference(
        evidence[3], initial_memory
    )


def _assert_observed_address_summary(
    transition_count: int,
    addresses: set[int],
    *,
    label: str,
) -> None:
    if transition_count < len(addresses):
        message = f"{label} count cannot cover its distinct addresses"
        raise AssertionError(message)
    if (transition_count > 0) != bool(addresses):
        message = f"{label} count disagrees with observed addresses"
        raise AssertionError(message)


def _assert_observed_value_domains(
    transition_count: int,
    addresses: set[int],
    values: dict[int, set[int]],
    *,
    label: str,
) -> None:
    _assert_observed_address_summary(
        transition_count,
        addresses,
        label=label,
    )
    if addresses != set(values):
        message = f"{label} addresses disagree with value domains"
        raise AssertionError(message)
    distinct_observations = sum(len(domain) for domain in values.values())
    if transition_count < distinct_observations:
        message = f"{label} count cannot cover its value domains"
        raise AssertionError(message)


def _evolved_read_observation_projection(
    observations: dict[_StateKey, tuple[int, int]],
) -> tuple[set[int], dict[int, set[int]]]:
    addresses = {address for address, _ in observations.values()}
    values: dict[int, set[int]] = {}
    for address, observed_value in observations.values():
        values.setdefault(address, set()).add(observed_value)
    return addresses, values


def _assert_evolved_read_observation_projection(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
    *,
    label: str,
) -> None:
    transition_count, addresses, values, observations, seen = evidence
    if transition_count != len(observations):
        message = f"{label} count disagrees with exact observed states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = f"{label} retained an unknown explored state"
        raise AssertionError(message)
    projected_addresses, projected_values = (
        _evolved_read_observation_projection(observations)
    )
    if addresses != projected_addresses:
        message = f"{label} addresses disagree with exact observed states"
        raise AssertionError(message)
    if values != projected_values:
        message = f"{label} value domains disagree with exact observed states"
        raise AssertionError(message)


def _assert_evolved_read_observation_initial_difference(
    observations: dict[_StateKey, tuple[int, int]],
    initial_memory: tuple[int, ...],
    *,
    label: str,
) -> None:
    if any(
        observed_value == initial_memory[address]
        for address, observed_value in observations.values()
    ):
        message = f"{label} observation no longer differs from initial memory"
        raise AssertionError(message)


def _assert_evolved_read_observation_evidence(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int]],
        set[_StateKey],
    ],
    initial_memory: tuple[int, ...],
    *,
    label: str,
) -> None:
    _assert_evolved_read_observation_projection(evidence, label=label)
    _assert_evolved_read_observation_initial_difference(
        evidence[3], initial_memory, label=label
    )


def _assert_evolved_read_witness_endpoint(
    values: dict[int, set[int]],
    witness: WorklistEvolvedReadWitness,
    *,
    label: str,
) -> None:
    if not witness.entry_path or witness.entry_path[-1] != witness.state:
        message = f"{label} witness lost its exact entry endpoint"
        raise AssertionError(message)
    if witness.observed_value not in values.get(witness.address, set()):
        message = f"{label} witness value is outside observed domains"
        raise AssertionError(message)
    if witness.initial_value == witness.observed_value:
        message = f"{label} witness no longer differs from initial memory"
        raise AssertionError(message)
    if witness.origin_value != witness.observed_value:
        message = f"{label} witness value disagrees with its exact writer"
        raise AssertionError(message)


def _assert_evolved_read_witness(
    evidence: tuple[
        int,
        dict[int, set[int]],
        WorklistEvolvedReadWitness | None,
    ],
    *,
    label: str,
    require_witness: bool,
) -> None:
    transition_count, values, witness = evidence
    if witness is not None and transition_count == 0:
        message = f"{label} witness exists without evolved read evidence"
        raise AssertionError(message)
    if require_witness and transition_count > 0 and witness is None:
        message = f"{label} evidence disagrees with witness presence"
        raise AssertionError(message)
    if witness is not None:
        _assert_evolved_read_witness_endpoint(values, witness, label=label)


def _data_mutation_observation_projection(
    observations: dict[_StateKey, tuple[int, int, int, int, bool]],
) -> tuple[set[int], dict[int, set[int]], dict[int, set[int]]]:
    addresses: set[int] = set()
    previous_values: dict[int, set[int]] = {}
    result_values: dict[int, set[int]] = {}
    for address, previous, _, result, _ in observations.values():
        addresses.add(address)
        previous_values.setdefault(address, set()).add(previous)
        result_values.setdefault(address, set()).add(result)
    return addresses, previous_values, result_values


def _self_encryption_observation_projection(
    observations: dict[_StateKey, tuple[int, int, int, bool]],
) -> tuple[set[int], dict[int, set[int]]]:
    addresses: set[int] = set()
    outputs: dict[int, set[int]] = {}
    for address, input_value, output_value, _ in observations.values():
        if classic.encrypt(input_value) != output_value:
            message = "self-encryption observation violates classic encryption"
            raise AssertionError(message)
        addresses.add(address)
        _record_domain_value(outputs, address, output_value)
    return addresses, outputs


def _assert_self_encryption_observations(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int, int, bool]],
        set[_StateKey],
    ],
) -> None:
    count, addresses, output_values, observations, seen = evidence
    if count != len(observations):
        message = "self-encryption count disagrees with exact committed states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = "self-encryption evidence retained an unknown graph state"
        raise AssertionError(message)
    projected_addresses, projected_outputs = (
        _self_encryption_observation_projection(observations)
    )
    if addresses != projected_addresses:
        message = (
            "self-encryption addresses disagree with exact committed states"
        )
        raise AssertionError(message)
    if output_values != projected_outputs:
        message = "self-encryption outputs disagree with exact committed states"
        raise AssertionError(message)


def _assert_data_write_noop_observations(
    evidence: tuple[
        int,
        set[int],
        dict[_StateKey, tuple[int, int, int, int, bool]],
        set[_StateKey],
    ],
) -> None:
    count, addresses, observations, seen = evidence
    if count != len(observations):
        message = "final no-op count disagrees with exact states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = "final no-op evidence retained an unknown state"
        raise AssertionError(message)
    if any(
        previous != result
        for _, previous, _, result, _ in observations.values()
    ):
        message = "final no-op observation changed memory"
        raise AssertionError(message)
    projected_addresses = {item[0] for item in observations.values()}
    if addresses != projected_addresses:
        message = "final no-op addresses disagree with exact states"
        raise AssertionError(message)


def _assert_data_mutation_observations(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[int, set[int]],
        dict[_StateKey, tuple[int, int, int, int, bool]],
        set[_StateKey],
    ],
) -> None:
    (
        count,
        addresses,
        previous_values,
        result_values,
        observations,
        seen,
    ) = evidence
    if count != len(observations):
        message = "effective mutation count disagrees with exact states"
        raise AssertionError(message)
    if not set(observations) <= seen:
        message = "effective mutation evidence retained an unknown state"
        raise AssertionError(message)
    if any(
        previous == result
        for _, previous, _, result, _ in observations.values()
    ):
        message = "effective mutation observation became a final no-op"
        raise AssertionError(message)
    projected = _data_mutation_observation_projection(observations)
    if projected != (addresses, previous_values, result_values):
        message = "effective mutation domains disagree with exact states"
        raise AssertionError(message)


def _assert_data_mutation_domains(
    transition_count: int,
    addresses: set[int],
    *,
    previous_values: dict[int, set[int]],
    result_values: dict[int, set[int]],
) -> None:
    _assert_observed_value_domains(
        transition_count,
        addresses,
        previous_values,
        label="effective data mutation previous value",
    )
    _assert_observed_value_domains(
        transition_count,
        addresses,
        result_values,
        label="effective data mutation result value",
    )


def _assert_committed_write_count_partition(
    counts: _WriteCounts,
) -> None:
    committed, data_write, noop, self_encryption, effective = counts
    if committed != data_write + self_encryption:
        message = "committed write count disagrees with mutation classes"
        raise AssertionError(message)
    if data_write != noop + effective:
        message = (
            "committed data writes disagree with no-op/effective partition"
        )
        raise AssertionError(message)


def _assert_committed_write_address_partition(
    address_sets: _WriteAddressSets,
) -> None:
    committed, data_write, noop, self_encryption, effective = address_sets
    if committed != data_write | self_encryption:
        message = "committed write addresses disagree with mutation classes"
        raise AssertionError(message)
    if data_write != noop | effective:
        message = (
            "committed data-write addresses disagree with "
            "no-op/effective classes"
        )
        raise AssertionError(message)


def _assert_non_graphical_fetch_domains(
    transition_count: int,
    addresses: set[int],
    values: dict[int, set[int]],
) -> None:
    if addresses != set(values):
        message = "non-graphical fetch addresses disagree with value domains"
        raise AssertionError(message)
    distinct_observations = sum(len(domain) for domain in values.values())
    if transition_count < distinct_observations:
        message = "non-graphical fetch count cannot cover its value domains"
        raise AssertionError(message)
    if (transition_count > 0) != bool(values):
        message = "non-graphical fetch count disagrees with observed domains"
        raise AssertionError(message)
    if any(
        classic.is_graphical(value)
        for domain in values.values()
        for value in domain
    ):
        message = "non-graphical fetch domain retained a graphical value"
        raise AssertionError(message)


def _assert_non_graphical_fetch_observation_projection(
    evidence: tuple[
        int,
        set[int],
        dict[int, set[int]],
        dict[_StateKey, int],
    ],
) -> None:
    transition_count, addresses, values, observations = evidence
    if transition_count != len(observations):
        message = (
            "non-graphical fetch count disagrees with exact fetch states"
        )
        raise AssertionError(message)
    observed_addresses = {state[0] for state in observations}
    if addresses != observed_addresses:
        message = (
            "non-graphical fetch addresses disagree with exact fetch states"
        )
        raise AssertionError(message)
    projected_values: dict[int, set[int]] = {}
    for state, value in observations.items():
        projected_values.setdefault(state[0], set()).add(value)
    if values != projected_values:
        message = (
            "non-graphical fetch value domains disagree with exact fetch states"
        )
        raise AssertionError(message)


def _assert_non_graphical_fetch_observation_edges(
    observations: dict[_StateKey, int],
    edges: dict[_StateKey, set[_StateKey]],
) -> None:
    if any(edges.get(state) != {state} for state in observations):
        message = "non-graphical fetch state lost its exact self-loop edge"
        raise AssertionError(message)


def _assert_non_graphical_fetch_witness_endpoint(
    values: dict[int, set[int]],
    witness: WorklistNonGraphicalFetchWitness,
) -> None:
    if not witness.entry_path or witness.entry_path[-1] != witness.state:
        message = "non-graphical fetch witness lost its exact entry endpoint"
        raise AssertionError(message)
    if witness.state.code_pointer != witness.address:
        message = (
            "non-graphical fetch witness address disagrees with code pointer"
        )
        raise AssertionError(message)
    if witness.value not in values.get(witness.address, set()):
        message = (
            "non-graphical fetch witness value is outside observed domains"
        )
        raise AssertionError(message)


def _assert_non_graphical_fetch_witness(
    values: dict[int, set[int]],
    witness: WorklistNonGraphicalFetchWitness | None,
) -> None:
    if bool(values) != (witness is not None):
        message = "non-graphical fetch evidence disagrees with witness presence"
        raise AssertionError(message)
    if witness is not None:
        _assert_non_graphical_fetch_witness_endpoint(values, witness)


def _record_domain_value(
    domains: dict[int, set[int]],
    address: int,
    value: int,
) -> None:
    domains.setdefault(address, set()).add(value)


def _value_domains(
    observed: dict[int, set[int]],
) -> tuple[WorklistValueDomain, ...]:
    return tuple(
        WorklistValueDomain(
            address=address,
            values=tuple(sorted(observed[address])),
        )
        for address in sorted(observed)
    )


def _data_mutation_value_domains(
    previous_values: dict[int, set[int]],
    result_values: dict[int, set[int]],
) -> tuple[WorklistDataMutationValueDomain, ...]:
    if previous_values.keys() != result_values.keys():
        message = "data mutation value domains lost an observed address"
        raise AssertionError(message)
    return tuple(
        WorklistDataMutationValueDomain(
            address=address,
            previous_values=tuple(sorted(previous_values[address])),
            result_values=tuple(sorted(result_values[address])),
        )
        for address in sorted(previous_values)
    )


def _record_initial_value_observation(
    node: _ReachabilityNode,
    observations: dict[_StateKey, tuple[int, int]],
    evidence: tuple[int, int, str],
) -> None:
    address, value, label = evidence
    key = _node_key(node)
    if key in observations:
        message = f"{label} state was explored more than once"
        raise AssertionError(message)
    observations[key] = (address, value)


@dataclass(slots=True)
class _Explorer:
    words: tuple[int, ...]
    state_limit: int
    queue: deque[_ReachabilityNode]
    seen: set[_StateKey]
    edges: dict[_StateKey, set[_StateKey]]
    terminal_counts: dict[str, int]
    accessed_addresses: set[int]
    initial_memory: tuple[int, ...] = field(init=False, repr=False)
    terminal_states: dict[str, set[_StateKey]] = field(default_factory=dict)
    explored_code_pointer_addresses: set[int] = field(default_factory=set)
    explored_data_pointer_addresses: set[int] = field(default_factory=set)
    code_data_alias_addresses: set[int] = field(default_factory=set)
    code_data_alias_state_values: dict[_StateKey, int] = field(
        default_factory=dict
    )
    code_data_alias_witnesses: dict[int, WorklistCodeDataAliasWitness] = field(
        default_factory=dict
    )
    committed_write_addresses: set[int] = field(default_factory=set)
    planned_data_write_addresses: set[int] = field(default_factory=set)
    planned_data_write_values: dict[int, set[int]] = field(default_factory=dict)
    planned_data_write_state_values: dict[_StateKey, tuple[int, int]] = field(
        default_factory=dict
    )
    committed_data_write_addresses: set[int] = field(default_factory=set)
    committed_data_write_noop_addresses: set[int] = field(default_factory=set)
    committed_data_write_noop_state_values: dict[
        _StateKey, tuple[int, int, int, int, bool]
    ] = field(default_factory=dict)
    self_encryption_addresses: set[int] = field(default_factory=set)
    self_encryption_state_values: dict[
        _StateKey, tuple[int, int, int, bool]
    ] = field(default_factory=dict)
    effective_data_mutation_addresses: set[int] = field(default_factory=set)
    effective_data_mutation_previous_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    effective_data_mutation_result_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    effective_data_mutation_state_values: dict[
        _StateKey, tuple[int, int, int, int, bool]
    ] = field(default_factory=dict)
    fetch_values: dict[int, set[int]] = field(default_factory=dict)
    non_graphical_fetch_addresses: set[int] = field(default_factory=set)
    non_graphical_fetch_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    non_graphical_fetch_state_values: dict[_StateKey, int] = field(
        default_factory=dict
    )
    non_graphical_fetch_witness: WorklistNonGraphicalFetchWitness | None = None
    data_read_values: dict[int, set[int]] = field(default_factory=dict)
    encryption_input_values: dict[int, set[int]] = field(default_factory=dict)
    initial_value_encryption_input_addresses: set[int] = field(
        default_factory=set
    )
    initial_value_encryption_input_state_values: dict[
        _StateKey, tuple[int, int]
    ] = field(default_factory=dict)
    changed_from_initial_encryption_input_addresses: set[int] = field(
        default_factory=set
    )
    changed_from_initial_encryption_input_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    changed_from_initial_encryption_input_state_values: dict[
        _StateKey, tuple[int, int]
    ] = field(default_factory=dict)
    committed_data_write_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    self_encryption_output_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    initial_value_fetch_addresses: set[int] = field(default_factory=set)
    initial_value_fetch_state_values: dict[
        _StateKey, tuple[int, int]
    ] = field(default_factory=dict)
    evolved_fetch_addresses: set[int] = field(default_factory=set)
    evolved_fetch_values: dict[int, set[int]] = field(default_factory=dict)
    evolved_fetch_state_values: dict[_StateKey, tuple[int, int]] = field(
        default_factory=dict
    )
    initial_value_data_read_addresses: set[int] = field(default_factory=set)
    initial_value_data_read_state_values: dict[
        _StateKey, tuple[int, int]
    ] = field(default_factory=dict)
    evolved_data_read_addresses: set[int] = field(default_factory=set)
    evolved_data_read_values: dict[int, set[int]] = field(default_factory=dict)
    evolved_data_read_state_values: dict[_StateKey, tuple[int, int]] = field(
        default_factory=dict
    )
    evolved_fetch_witness: WorklistEvolvedReadWitness | None = None
    evolved_data_read_witness: WorklistEvolvedReadWitness | None = None
    data_write_noop_witness: WorklistDataWriteNoopWitness | None = None
    data_mutation_witness: WorklistDataMutationWitness | None = None
    explored: int = 0
    code_data_alias_transitions: int = 0
    committed_writes: int = 0
    planned_data_write_transitions: int = 0
    committed_data_write_transitions: int = 0
    committed_data_write_noop_transitions: int = 0
    self_encryption_transitions: int = 0
    effective_data_mutation_transitions: int = 0
    non_graphical_fetch_transitions: int = 0
    encryption_input_transitions: int = 0
    initial_value_encryption_input_transitions: int = 0
    changed_from_initial_encryption_input_transitions: int = 0
    initial_value_fetch_transitions: int = 0
    evolved_fetch_transitions: int = 0
    data_read_transitions: int = 0
    initial_value_data_read_transitions: int = 0
    evolved_data_read_transitions: int = 0
    repeated_edges: int = 0
    state_merge_transitions: int = 0
    cycle_closing_repeated_edges: int = 0
    cycle_closing_repeated_edge_witness: (
        WorklistCycleClosingRepeatedEdgeWitness | None
    ) = None
    state_merge_witness: WorklistStateMergeWitness | None = None
    input_branch_points: int = 0
    input_branch_states: set[_StateKey] = field(default_factory=set)
    wraparound_transitions: int = 0
    code_pointer_wrap_transitions: int = 0
    data_pointer_wrap_transitions: int = 0
    simultaneous_pointer_wrap_transitions: int = 0
    wraparound_transition_signatures: set[
        WorklistWrapTransitionSignature
    ] = field(default_factory=set)
    wraparound_witness: WorklistWrapWitness | None = None
    code_pointer_wrap_witness: WorklistWrapWitness | None = None
    data_pointer_wrap_witness: WorklistWrapWitness | None = None
    simultaneous_pointer_wrap_witness: WorklistWrapWitness | None = None
    maximum_first_seen_transition_index: int = 1

    def __post_init__(self) -> None:
        self.initial_memory = _expanded_initial_memory(self.words)

    @classmethod
    def create(cls, words: tuple[int, ...], state_limit: int) -> _Explorer:
        initial = _ReachabilityNode(
            snapshot=prefix_transfer.StateSnapshot(
                before_transition=1,
                code_pointer=0,
                data_pointer=0,
                accumulator=0,
                memory_overrides=(),
            ),
            eof_seen=False,
        )
        return cls(
            words=words,
            state_limit=state_limit,
            queue=deque((initial,)),
            seen={_node_key(initial)},
            edges={_node_key(initial): set()},
            terminal_counts={},
            accessed_addresses=set(),
        )

    def _assert_read_partition_invariants(self) -> None:
        fetch_partition = self.initial_value_fetch_transitions + (
            self.evolved_fetch_transitions
        )
        if fetch_partition != self.explored:
            message = "explored fetch partition disagrees with explored states"
            raise AssertionError(message)
        data_partition = (
            self.initial_value_data_read_transitions
            + self.evolved_data_read_transitions
        )
        if data_partition != self.data_read_transitions:
            message = "explored data-read partition disagrees with total reads"
            raise AssertionError(message)
        encryption_partition = (
            self.initial_value_encryption_input_transitions
            + self.changed_from_initial_encryption_input_transitions
        )
        if encryption_partition != self.encryption_input_transitions:
            message = (
                "explored encryption-input partition disagrees with "
                "total inputs"
            )
            raise AssertionError(message)
        _assert_initial_value_observations(
            (
                self.initial_value_fetch_transitions,
                self.initial_value_fetch_addresses,
                self.initial_value_fetch_state_values,
                self.seen,
            ),
            self.initial_memory,
            label="initial-value fetch",
        )
        _assert_observed_value_domains(
            self.evolved_fetch_transitions,
            self.evolved_fetch_addresses,
            self.evolved_fetch_values,
            label="evolved fetch",
        )
        _assert_evolved_read_observation_evidence(
            (
                self.evolved_fetch_transitions,
                self.evolved_fetch_addresses,
                self.evolved_fetch_values,
                self.evolved_fetch_state_values,
                self.seen,
            ),
            self.initial_memory,
            label="evolved fetch",
        )
        _assert_evolved_read_witness(
            (
                self.evolved_fetch_transitions,
                self.evolved_fetch_values,
                self.evolved_fetch_witness,
            ),
            label="evolved fetch",
            require_witness=_INITIAL_STATE_KEY in self.seen,
        )
        _assert_initial_value_observations(
            (
                self.initial_value_data_read_transitions,
                self.initial_value_data_read_addresses,
                self.initial_value_data_read_state_values,
                self.seen,
            ),
            self.initial_memory,
            label="initial-value data read",
        )
        _assert_observed_value_domains(
            self.evolved_data_read_transitions,
            self.evolved_data_read_addresses,
            self.evolved_data_read_values,
            label="evolved data read",
        )
        _assert_evolved_read_observation_evidence(
            (
                self.evolved_data_read_transitions,
                self.evolved_data_read_addresses,
                self.evolved_data_read_values,
                self.evolved_data_read_state_values,
                self.seen,
            ),
            self.initial_memory,
            label="evolved data read",
        )
        _assert_evolved_read_witness(
            (
                self.evolved_data_read_transitions,
                self.evolved_data_read_values,
                self.evolved_data_read_witness,
            ),
            label="evolved data read",
            require_witness=_INITIAL_STATE_KEY in self.seen,
        )
        _assert_initial_value_observations(
            (
                self.initial_value_encryption_input_transitions,
                self.initial_value_encryption_input_addresses,
                self.initial_value_encryption_input_state_values,
                self.seen,
            ),
            self.initial_memory,
            label="initial-value encryption input",
        )
        _assert_observed_value_domains(
            self.changed_from_initial_encryption_input_transitions,
            self.changed_from_initial_encryption_input_addresses,
            self.changed_from_initial_encryption_input_values,
            label="changed encryption input",
        )
        _assert_changed_encryption_input_observations(
            (
                self.changed_from_initial_encryption_input_transitions,
                self.changed_from_initial_encryption_input_addresses,
                self.changed_from_initial_encryption_input_values,
                self.changed_from_initial_encryption_input_state_values,
                self.seen,
            ),
            self.initial_memory,
        )
        _assert_read_observation_state_partitions(
            (
                (
                    set(self.initial_value_fetch_state_values),
                    set(self.evolved_fetch_state_values),
                    "fetch value partition",
                ),
                (
                    set(self.initial_value_data_read_state_values),
                    set(self.evolved_data_read_state_values),
                    "data-read value partition",
                ),
                (
                    set(self.initial_value_encryption_input_state_values),
                    set(
                        self.changed_from_initial_encryption_input_state_values
                    ),
                    "encryption-input value partition",
                ),
            )
        )

    def _assert_write_evidence_invariants(self) -> None:
        _assert_observed_address_summary(
            self.committed_writes,
            self.committed_write_addresses,
            label="committed write",
        )
        _assert_observed_value_domains(
            self.planned_data_write_transitions,
            self.planned_data_write_addresses,
            self.planned_data_write_values,
            label="planned data write",
        )
        _assert_planned_data_write_observations(
            (
                self.planned_data_write_transitions,
                self.planned_data_write_addresses,
                self.planned_data_write_values,
                self.planned_data_write_state_values,
                self.seen,
            )
        )
        _assert_observed_value_domains(
            self.committed_data_write_transitions,
            self.committed_data_write_addresses,
            self.committed_data_write_values,
            label="committed data write",
        )
        _assert_data_write_noop_observations(
            (
                self.committed_data_write_noop_transitions,
                self.committed_data_write_noop_addresses,
                self.committed_data_write_noop_state_values,
                self.seen,
            )
        )
        _assert_observed_value_domains(
            self.self_encryption_transitions,
            self.self_encryption_addresses,
            self.self_encryption_output_values,
            label="self-encryption output",
        )
        _assert_self_encryption_observations(
            (
                self.self_encryption_transitions,
                self.self_encryption_addresses,
                self.self_encryption_output_values,
                self.self_encryption_state_values,
                self.seen,
            )
        )
        _assert_data_mutation_domains(
            self.effective_data_mutation_transitions,
            self.effective_data_mutation_addresses,
            previous_values=self.effective_data_mutation_previous_values,
            result_values=self.effective_data_mutation_result_values,
        )
        _assert_data_mutation_observations(
            (
                self.effective_data_mutation_transitions,
                self.effective_data_mutation_addresses,
                self.effective_data_mutation_previous_values,
                self.effective_data_mutation_result_values,
                self.effective_data_mutation_state_values,
                self.seen,
            )
        )
        _assert_committed_data_write_state_partition(
            (
                self.planned_data_write_state_values,
                self.committed_data_write_noop_state_values,
                self.effective_data_mutation_state_values,
                self.committed_data_write_values,
            )
        )
        _assert_committed_write_count_partition(
            (
                self.committed_writes,
                self.committed_data_write_transitions,
                self.committed_data_write_noop_transitions,
                self.self_encryption_transitions,
                self.effective_data_mutation_transitions,
            )
        )
        _assert_committed_write_address_partition(
            (
                self.committed_write_addresses,
                self.committed_data_write_addresses,
                self.committed_data_write_noop_addresses,
                self.self_encryption_addresses,
                self.effective_data_mutation_addresses,
            )
        )
        if (
            self.committed_data_write_transitions
            > self.planned_data_write_transitions
        ):
            message = "committed data writes exceed planned write evidence"
            raise AssertionError(message)
        if not (
            self.committed_data_write_addresses
            <= self.planned_data_write_addresses
        ):
            message = "committed data-write addresses escape planned writes"
            raise AssertionError(message)

    def _assert_non_graphical_fetch_evidence(self) -> None:
        evidence = (
            self.non_graphical_fetch_transitions,
            self.non_graphical_fetch_addresses,
            self.non_graphical_fetch_values,
            self.non_graphical_fetch_state_values,
        )
        _assert_non_graphical_fetch_domains(*evidence[:3])
        _assert_non_graphical_fetch_observation_projection(evidence)
        _assert_non_graphical_fetch_observation_edges(
            self.non_graphical_fetch_state_values, self.edges
        )
        _assert_non_graphical_fetch_witness(
            self.non_graphical_fetch_values, self.non_graphical_fetch_witness
        )

    def result(
        self,
        *,
        truncated: bool,
        frontier_state_keys: tuple[_StateKey, ...] = (),
        frontier_path: tuple[_StateKey, ...] | None = None,
    ) -> WorklistAnalysis:
        _assert_frontier_evidence(
            len(frontier_state_keys),
            frontier_state_keys,
            frontier_path,
            truncated=truncated,
        )
        _assert_terminal_evidence(
            self.terminal_counts,
            self.terminal_states,
            self.seen,
        )
        _assert_terminal_graph_endpoints(
            self.terminal_states,
            self.edges,
        )
        _assert_input_branch_evidence(
            self.input_branch_points,
            self.input_branch_states,
            self.seen,
        )
        _assert_code_data_alias_observations(
            self.code_data_alias_transitions,
            self.code_data_alias_addresses,
            self.code_data_alias_state_values,
        )
        ordered_addresses = tuple(sorted(self.accessed_addresses))
        highest_address = ordered_addresses[-1]
        cycle_keys = _known_graph_cycle_witness(self.edges, self.seen)
        entry_path_keys = (
            _known_graph_shortest_path(
                self.edges,
                self.seen,
                start=_INITIAL_STATE_KEY,
                target=cycle_keys[0],
            )
            if cycle_keys
            else ()
        )
        if bool(entry_path_keys) != bool(cycle_keys):
            message = "reachable cycle lost its exact entry path"
            raise AssertionError(message)
        component_summary = _known_graph_strong_component_summary(
            self.edges, self.seen
        )
        has_cycle = _known_graph_has_cycle(
            self.edges, self.seen, witness=cycle_keys
        )
        if has_cycle != bool(component_summary.cyclic_component_count):
            message = "known-graph cycle and SCC evidence disagree"
            raise AssertionError(message)
        distances = _known_graph_shortest_distances(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
        )
        cyclic_component_entry_counts = (
            _component_minimum_entry_path_state_counts(
                component_summary.cyclic_components,
                distances,
            )
        )
        recurrence = _closed_recurrence_evidence(
            component_summary,
            self.edges,
            nodes=self.seen,
            truncated=truncated,
        )
        self._assert_read_partition_invariants()
        self._assert_write_evidence_invariants()
        self._assert_non_graphical_fetch_evidence()
        _assert_wrap_evidence_invariants(
            (
                self.wraparound_transitions,
                self.code_pointer_wrap_transitions,
                self.data_pointer_wrap_transitions,
                self.simultaneous_pointer_wrap_transitions,
            ),
            (
                self.wraparound_witness,
                self.code_pointer_wrap_witness,
                self.data_pointer_wrap_witness,
                self.simultaneous_pointer_wrap_witness,
            ),
        )
        return WorklistAnalysis(
            state_limit=self.state_limit,
            unique_states=len(self.seen),
            explored_states=self.explored,
            repeated_state_edges=self.repeated_edges,
            explored_state_merge_transition_count=self.state_merge_transitions,
            explored_cycle_closing_repeated_edge_count=(
                self.cycle_closing_repeated_edges
            ),
            explored_cycle_closing_repeated_edge_witness=(
                self.cycle_closing_repeated_edge_witness
            ),
            explored_state_merge_witness=self.state_merge_witness,
            reachable_cycle_detected=has_cycle,
            reachable_cycle_witness=tuple(
                _cycle_state(key) for key in cycle_keys
            ),
            reachable_cycle_entry_path=tuple(
                _cycle_state(key) for key in entry_path_keys
            ),
            known_graph_strong_component_count=(
                component_summary.component_count
            ),
            known_graph_cyclic_component_count=(
                component_summary.cyclic_component_count
            ),
            known_graph_cyclic_state_count=component_summary.cyclic_state_count,
            known_graph_largest_cyclic_component_states=(
                component_summary.largest_cyclic_component_states
            ),
            known_graph_cyclic_components=_cycle_components(
                component_summary.cyclic_components
            ),
            known_graph_cyclic_component_minimum_entry_path_state_counts=(
                cyclic_component_entry_counts
            ),
            closed_recurrent_component_count=recurrence.component_count,
            closed_recurrent_state_count=recurrence.state_count,
            closed_recurrent_largest_component_states=(
                recurrence.largest_component_states
            ),
            closed_recurrent_components=recurrence.components,
            closed_recurrent_component_minimum_entry_path_state_counts=(
                recurrence.minimum_entry_path_state_counts
            ),
            closed_recurrent_cycle_witness=recurrence.cycle_witness,
            closed_recurrent_entry_path=recurrence.entry_path,
            input_branch_points=self.input_branch_points,
            input_branch_states=tuple(
                _cycle_state(key) for key in sorted(self.input_branch_states)
            ),
            terminal_status_counts=tuple(sorted(self.terminal_counts.items())),
            terminal_status_state_sets=_terminal_state_sets(
                self.terminal_states
            ),
            closed_terminal_status_counts=(
                None
                if truncated
                else tuple(sorted(self.terminal_counts.items()))
            ),
            closed_all_paths_terminate=None if truncated else not has_cycle,
            closed_all_paths_halt=(
                None
                if truncated
                else not has_cycle
                and set(self.terminal_counts) == {_HALTED_STATUS}
            ),
            terminal_status_witnesses=_terminal_witnesses(
                self.edges,
                self.seen,
                self.terminal_states,
            ),
            explored_code_pointer_addresses=tuple(
                sorted(self.explored_code_pointer_addresses)
            ),
            explored_data_pointer_addresses=tuple(
                sorted(self.explored_data_pointer_addresses)
            ),
            explored_code_data_alias_transition_count=(
                self.code_data_alias_transitions
            ),
            explored_code_data_alias_addresses=tuple(
                sorted(self.code_data_alias_addresses)
            ),
            explored_code_data_alias_observations=tuple(
                WorklistCodeDataAliasObservation(
                    state=_cycle_state(key),
                    address=key[0],
                    memory_value=self.code_data_alias_state_values[key],
                )
                for key in sorted(self.code_data_alias_state_values)
            ),
            explored_code_data_alias_witnesses=tuple(
                self.code_data_alias_witnesses[address]
                for address in sorted(self.code_data_alias_witnesses)
            ),
            explored_committed_write_count=self.committed_writes,
            explored_committed_write_addresses=tuple(
                sorted(self.committed_write_addresses)
            ),
            explored_planned_data_write_transition_count=(
                self.planned_data_write_transitions
            ),
            explored_planned_data_write_addresses=tuple(
                sorted(self.planned_data_write_addresses)
            ),
            explored_planned_data_write_value_domains=_value_domains(
                self.planned_data_write_values
            ),
            explored_planned_data_write_observations=tuple(
                WorklistPlannedDataWriteObservation(
                    state=_cycle_state(key),
                    address=self.planned_data_write_state_values[key][0],
                    value=self.planned_data_write_state_values[key][1],
                )
                for key in sorted(self.planned_data_write_state_values)
            ),
            explored_committed_data_write_transition_count=(
                self.committed_data_write_transitions
            ),
            explored_committed_data_write_addresses=tuple(
                sorted(self.committed_data_write_addresses)
            ),
            explored_committed_data_write_noop_transition_count=(
                self.committed_data_write_noop_transitions
            ),
            explored_committed_data_write_noop_addresses=tuple(
                sorted(self.committed_data_write_noop_addresses)
            ),
            explored_committed_data_write_noop_observations=tuple(
                WorklistDataWriteNoopObservation(
                    state=_cycle_state(key),
                    address=self.committed_data_write_noop_state_values[key][0],
                    previous_value=(
                        self.committed_data_write_noop_state_values[key][1]
                    ),
                    written_value=(
                        self.committed_data_write_noop_state_values[key][2]
                    ),
                    result_value=(
                        self.committed_data_write_noop_state_values[key][3]
                    ),
                    aliases_self_encryption=(
                        self.committed_data_write_noop_state_values[key][4]
                    ),
                )
                for key in sorted(self.committed_data_write_noop_state_values)
            ),
            explored_self_encryption_transition_count=(
                self.self_encryption_transitions
            ),
            explored_self_encryption_addresses=tuple(
                sorted(self.self_encryption_addresses)
            ),
            explored_self_encryption_observations=tuple(
                WorklistSelfEncryptionObservation(
                    state=_cycle_state(key),
                    address=self.self_encryption_state_values[key][0],
                    input_value=self.self_encryption_state_values[key][1],
                    output_value=self.self_encryption_state_values[key][2],
                    data_write_aliases_encryption=(
                        self.self_encryption_state_values[key][3]
                    ),
                )
                for key in sorted(self.self_encryption_state_values)
            ),
            explored_effective_data_mutation_transition_count=(
                self.effective_data_mutation_transitions
            ),
            explored_effective_data_mutation_addresses=tuple(
                sorted(self.effective_data_mutation_addresses)
            ),
            explored_effective_data_mutation_value_domains=(
                _data_mutation_value_domains(
                    self.effective_data_mutation_previous_values,
                    self.effective_data_mutation_result_values,
                )
            ),
            explored_effective_data_mutation_observations=tuple(
                WorklistDataMutationObservation(
                    state=_cycle_state(key),
                    address=self.effective_data_mutation_state_values[key][0],
                    previous_value=(
                        self.effective_data_mutation_state_values[key][1]
                    ),
                    written_value=(
                        self.effective_data_mutation_state_values[key][2]
                    ),
                    result_value=(
                        self.effective_data_mutation_state_values[key][3]
                    ),
                    aliases_self_encryption=(
                        self.effective_data_mutation_state_values[key][4]
                    ),
                )
                for key in sorted(self.effective_data_mutation_state_values)
            ),
            explored_fetch_value_domains=_value_domains(self.fetch_values),
            explored_non_graphical_fetch_transition_count=(
                self.non_graphical_fetch_transitions
            ),
            explored_non_graphical_fetch_addresses=tuple(
                sorted(self.non_graphical_fetch_addresses)
            ),
            explored_non_graphical_fetch_value_domains=_value_domains(
                self.non_graphical_fetch_values
            ),
            explored_non_graphical_fetch_observations=tuple(
                WorklistNonGraphicalFetchObservation(
                    state=_cycle_state(key),
                    address=key[0],
                    value=self.non_graphical_fetch_state_values[key],
                )
                for key in sorted(self.non_graphical_fetch_state_values)
            ),
            explored_non_graphical_fetch_witness=(
                self.non_graphical_fetch_witness
            ),
            explored_data_read_value_domains=_value_domains(
                self.data_read_values
            ),
            explored_encryption_input_value_domains=_value_domains(
                self.encryption_input_values
            ),
            explored_encryption_input_transition_count=(
                self.encryption_input_transitions
            ),
            explored_initial_value_encryption_input_transition_count=(
                self.initial_value_encryption_input_transitions
            ),
            explored_initial_value_encryption_input_addresses=tuple(
                sorted(self.initial_value_encryption_input_addresses)
            ),
            explored_initial_value_encryption_input_observations=tuple(
                WorklistInitialValueObservation(
                    state=_cycle_state(key),
                    address=(
                        self.initial_value_encryption_input_state_values[key][0]
                    ),
                    value=(
                        self.initial_value_encryption_input_state_values[key][1]
                    ),
                )
                for key in sorted(
                    self.initial_value_encryption_input_state_values
                )
            ),
            explored_changed_from_initial_encryption_input_transition_count=(
                self.changed_from_initial_encryption_input_transitions
            ),
            explored_changed_from_initial_encryption_input_addresses=tuple(
                sorted(self.changed_from_initial_encryption_input_addresses)
            ),
            explored_changed_from_initial_encryption_input_value_domains=(
                _value_domains(
                    self.changed_from_initial_encryption_input_values
                )
            ),
            explored_changed_from_initial_encryption_input_observations=tuple(
                WorklistChangedEncryptionInputObservation(
                    state=_cycle_state(key),
                    address=(
                        self.changed_from_initial_encryption_input_state_values[
                            key
                        ][0]
                    ),
                    initial_value=self.initial_memory[
                        self.changed_from_initial_encryption_input_state_values[
                            key
                        ][0]
                    ],
                    observed_value=(
                        self.changed_from_initial_encryption_input_state_values[
                            key
                        ][1]
                    ),
                )
                for key in sorted(
                    self.changed_from_initial_encryption_input_state_values
                )
            ),
            explored_committed_data_write_value_domains=_value_domains(
                self.committed_data_write_values
            ),
            explored_self_encryption_output_value_domains=_value_domains(
                self.self_encryption_output_values
            ),
            explored_initial_value_fetch_transition_count=(
                self.initial_value_fetch_transitions
            ),
            explored_initial_value_fetch_addresses=tuple(
                sorted(self.initial_value_fetch_addresses)
            ),
            explored_initial_value_fetch_observations=tuple(
                WorklistInitialValueObservation(
                    state=_cycle_state(key),
                    address=self.initial_value_fetch_state_values[key][0],
                    value=self.initial_value_fetch_state_values[key][1],
                )
                for key in sorted(self.initial_value_fetch_state_values)
            ),
            explored_evolved_fetch_transition_count=(
                self.evolved_fetch_transitions
            ),
            explored_evolved_fetch_addresses=tuple(
                sorted(self.evolved_fetch_addresses)
            ),
            explored_evolved_fetch_value_domains=_value_domains(
                self.evolved_fetch_values
            ),
            explored_evolved_fetch_observations=tuple(
                WorklistEvolvedReadObservation(
                    state=_cycle_state(key),
                    address=self.evolved_fetch_state_values[key][0],
                    initial_value=self.initial_memory[
                        self.evolved_fetch_state_values[key][0]
                    ],
                    observed_value=self.evolved_fetch_state_values[key][1],
                )
                for key in sorted(self.evolved_fetch_state_values)
            ),
            explored_data_read_transition_count=self.data_read_transitions,
            explored_initial_value_data_read_transition_count=(
                self.initial_value_data_read_transitions
            ),
            explored_initial_value_data_read_addresses=tuple(
                sorted(self.initial_value_data_read_addresses)
            ),
            explored_initial_value_data_read_observations=tuple(
                WorklistInitialValueObservation(
                    state=_cycle_state(key),
                    address=self.initial_value_data_read_state_values[key][0],
                    value=self.initial_value_data_read_state_values[key][1],
                )
                for key in sorted(self.initial_value_data_read_state_values)
            ),
            explored_evolved_data_read_transition_count=(
                self.evolved_data_read_transitions
            ),
            explored_evolved_data_read_addresses=tuple(
                sorted(self.evolved_data_read_addresses)
            ),
            explored_evolved_data_read_value_domains=_value_domains(
                self.evolved_data_read_values
            ),
            explored_evolved_data_read_observations=tuple(
                WorklistEvolvedReadObservation(
                    state=_cycle_state(key),
                    address=self.evolved_data_read_state_values[key][0],
                    initial_value=self.initial_memory[
                        self.evolved_data_read_state_values[key][0]
                    ],
                    observed_value=self.evolved_data_read_state_values[key][1],
                )
                for key in sorted(self.evolved_data_read_state_values)
            ),
            explored_evolved_fetch_witness=self.evolved_fetch_witness,
            explored_evolved_data_read_witness=self.evolved_data_read_witness,
            explored_data_write_noop_witness=self.data_write_noop_witness,
            explored_data_mutation_witness=self.data_mutation_witness,
            explored_minimum_words=max(
                len(self.words),
                highest_address + 1,
            ),
            explored_highest_accessed_address=highest_address,
            explored_accessed_addresses=ordered_addresses,
            explored_wraparound_transition_count=self.wraparound_transitions,
            explored_code_pointer_wrap_transition_count=(
                self.code_pointer_wrap_transitions
            ),
            explored_data_pointer_wrap_transition_count=(
                self.data_pointer_wrap_transitions
            ),
            explored_simultaneous_pointer_wrap_transition_count=(
                self.simultaneous_pointer_wrap_transitions
            ),
            explored_wraparound_transition_signatures=tuple(
                sorted(
                    self.wraparound_transition_signatures,
                    key=_wrap_transition_signature_key,
                )
            ),
            explored_wraparound_witness=self.wraparound_witness,
            explored_code_pointer_wrap_witness=(
                self.code_pointer_wrap_witness
            ),
            explored_data_pointer_wrap_witness=(
                self.data_pointer_wrap_witness
            ),
            explored_simultaneous_pointer_wrap_witness=(
                self.simultaneous_pointer_wrap_witness
            ),
            maximum_first_seen_transition_index=(
                self.maximum_first_seen_transition_index
            ),
            frontier_states=len(frontier_state_keys),
            frontier_state_set=tuple(
                _cycle_state(key) for key in frontier_state_keys
            ),
            frontier_state_witness=(
                _cycle_state(frontier_path[-1]) if frontier_path else None
            ),
            frontier_entry_path=(
                tuple(_cycle_state(key) for key in frontier_path)
                if frontier_path
                else None
            ),
            truncated=truncated,
        )

    def _record_terminal(self, status: str, node: _ReachabilityNode) -> None:
        self.terminal_counts[status] = self.terminal_counts.get(status, 0) + 1
        states = self.terminal_states.setdefault(status, set())
        states.add(_node_key(node))

    def _frontier_path(
        self,
        *,
        source_key: _StateKey,
        successor_key: _StateKey,
    ) -> tuple[_StateKey, ...]:
        if self.queue:
            frontier_key = _node_key(self.queue[0])
            path = _known_graph_shortest_path(
                self.edges,
                self.seen,
                start=_INITIAL_STATE_KEY,
                target=frontier_key,
            )
        else:
            source_path = _known_graph_shortest_path(
                self.edges,
                self.seen,
                start=_INITIAL_STATE_KEY,
                target=source_key,
            )
            path = (*source_path, successor_key)
        if not path:
            message = "worklist frontier lost its exact entry path"
            raise AssertionError(message)
        return path

    def _record_state_merge(
        self,
        source_key: _StateKey,
        target_key: _StateKey,
    ) -> None:
        source_path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=source_key,
        )
        if target_key in source_path:
            self.cycle_closing_repeated_edges += 1
            if self.cycle_closing_repeated_edge_witness is None:
                target_index = source_path.index(target_key)
                self.cycle_closing_repeated_edge_witness = (
                    WorklistCycleClosingRepeatedEdgeWitness(
                        source_state=_cycle_state(source_key),
                        source_entry_path=tuple(
                            _cycle_state(item) for item in source_path
                        ),
                        target_state=_cycle_state(target_key),
                        target_entry_path_state_index=target_index,
                    )
                )
            return
        self.state_merge_transitions += 1
        if self.state_merge_witness is not None:
            return
        target_path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=target_key,
        )
        if not source_path or not target_path:
            message = "state merge lost an exact known entry path"
            raise AssertionError(message)
        self.state_merge_witness = WorklistStateMergeWitness(
            source_state=_cycle_state(source_key),
            source_entry_path=tuple(_cycle_state(item) for item in source_path),
            target_state=_cycle_state(target_key),
            existing_target_entry_path=tuple(
                _cycle_state(item) for item in target_path
            ),
        )

    def _admit_successors(
        self,
        source: _ReachabilityNode,
        successors: tuple[_ReachabilityNode, ...],
    ) -> WorklistAnalysis | None:
        source_key = _node_key(source)
        source_edges = self.edges[source_key]
        for index, successor in enumerate(successors):
            key = _node_key(successor)
            if key in self.seen:
                self._record_state_merge(source_key, key)
                source_edges.add(key)
                self.repeated_edges += 1
                continue
            if len(self.seen) >= self.state_limit:
                frontier_path = self._frontier_path(
                    source_key=source_key,
                    successor_key=key,
                )
                frontier_state_keys = tuple(
                    sorted(
                        {
                            *(_node_key(node) for node in self.queue),
                            *_unseen_successor_keys(
                                successors,
                                self.seen,
                                start_index=index,
                            ),
                        }
                    )
                )
                return self.result(
                    truncated=True,
                    frontier_state_keys=frontier_state_keys,
                    frontier_path=frontier_path,
                )
            self.seen.add(key)
            self.maximum_first_seen_transition_index = max(
                self.maximum_first_seen_transition_index,
                successor.snapshot.before_transition,
            )
            source_edges.add(key)
            self.edges[key] = set()
            self.queue.append(successor)
        return None

    def _record_wrap_counts(
        self,
        *,
        code_wrapped: bool,
        data_wrapped: bool,
    ) -> None:
        if code_wrapped:
            self.code_pointer_wrap_transitions += 1
        if data_wrapped:
            self.data_pointer_wrap_transitions += 1
        if code_wrapped and data_wrapped:
            self.simultaneous_pointer_wrap_transitions += 1

    def _wrap_witness_needed(
        self,
        *,
        code_wrapped: bool,
        data_wrapped: bool,
    ) -> bool:
        simultaneous = code_wrapped and data_wrapped
        return (
            self.wraparound_witness is None
            or (code_wrapped and self.code_pointer_wrap_witness is None)
            or (data_wrapped and self.data_pointer_wrap_witness is None)
            or (
                simultaneous
                and self.simultaneous_pointer_wrap_witness is None
            )
        )

    def _remember_wrap_witness(self, witness: WorklistWrapWitness) -> None:
        if self.wraparound_witness is None:
            self.wraparound_witness = witness
        if (
            witness.code_pointer_wrapped
            and self.code_pointer_wrap_witness is None
        ):
            self.code_pointer_wrap_witness = witness
        if (
            witness.data_pointer_wrapped
            and self.data_pointer_wrap_witness is None
        ):
            self.data_pointer_wrap_witness = witness
        if (
            witness.code_pointer_wrapped
            and witness.data_pointer_wrapped
            and self.simultaneous_pointer_wrap_witness is None
        ):
            self.simultaneous_pointer_wrap_witness = witness

    def _record_wraparound(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        self.wraparound_transitions += 1
        result_code, result_data, code_wrapped, data_wrapped = (
            _pointer_wrap_result(transition)
        )
        self._record_wrap_counts(
            code_wrapped=code_wrapped,
            data_wrapped=data_wrapped,
        )
        self.wraparound_transition_signatures.add(
            WorklistWrapTransitionSignature(
                source_code_pointer=node.snapshot.code_pointer,
                source_data_pointer=node.snapshot.data_pointer,
                result_code_pointer=result_code,
                result_data_pointer=result_data,
                code_pointer_wrapped=code_wrapped,
                data_pointer_wrapped=data_wrapped,
            )
        )
        if not self._wrap_witness_needed(
            code_wrapped=code_wrapped,
            data_wrapped=data_wrapped,
        ):
            return
        key = _node_key(node)
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        self._remember_wrap_witness(
            WorklistWrapWitness(
                state=_cycle_state(key),
                entry_path=tuple(_cycle_state(item) for item in path),
                result_code_pointer=result_code,
                result_data_pointer=result_data,
                code_pointer_wrapped=code_wrapped,
                data_pointer_wrapped=data_wrapped,
            )
        )

    def _evolved_read_witness(
        self,
        node: _ReachabilityNode,
        *,
        address: int,
        observed_value: int,
    ) -> WorklistEvolvedReadWitness | None:
        initial_value = self.initial_memory[address]
        if observed_value == initial_value:
            return None
        key = _node_key(node)
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        if not path:
            return None
        writer = _entry_path_last_writer(self.initial_memory, path, address)
        if writer is None:
            message = "evolved read witness has no committed entry-path writer"
            raise AssertionError(message)
        origin_kind, origin_transition, origin_value = writer
        if origin_value != observed_value:
            message = (
                "evolved read value disagrees with its last committed writer"
            )
            raise AssertionError(message)
        return WorklistEvolvedReadWitness(
            state=_cycle_state(key),
            entry_path=tuple(_cycle_state(item) for item in path),
            address=address,
            initial_value=initial_value,
            observed_value=observed_value,
            origin_kind=origin_kind,
            origin_entry_path_transition_index=origin_transition,
            origin_value=origin_value,
        )

    def _record_evolved_fetch_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        address = transition.fetched_address
        if transition.fetched_value == self.initial_memory[address]:
            _record_initial_value_observation(
                node,
                self.initial_value_fetch_state_values,
                (address, transition.fetched_value, "initial-value fetch"),
            )
            self.initial_value_fetch_transitions += 1
            self.initial_value_fetch_addresses.add(address)
            return
        key = _node_key(node)
        if key in self.evolved_fetch_state_values:
            message = "evolved fetch state was explored more than once"
            raise AssertionError(message)
        self.evolved_fetch_transitions += 1
        self.evolved_fetch_addresses.add(address)
        _record_domain_value(
            self.evolved_fetch_values, address, transition.fetched_value
        )
        self.evolved_fetch_state_values[key] = (
            address,
            transition.fetched_value,
        )
        if self.evolved_fetch_witness is None:
            self.evolved_fetch_witness = self._evolved_read_witness(
                node,
                address=address,
                observed_value=transition.fetched_value,
            )

    def _record_evolved_data_read_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        if transition.decoded_byte not in _DATA_READING_INSTRUCTIONS:
            return
        self.data_read_transitions += 1
        data_value = _required_exact_value(
            transition.data_value, label="semantic data read"
        )
        address = transition.data_address
        if data_value == self.initial_memory[address]:
            _record_initial_value_observation(
                node,
                self.initial_value_data_read_state_values,
                (address, data_value, "initial-value data read"),
            )
            self.initial_value_data_read_transitions += 1
            self.initial_value_data_read_addresses.add(address)
            return
        key = _node_key(node)
        if key in self.evolved_data_read_state_values:
            message = "evolved data-read state was explored more than once"
            raise AssertionError(message)
        self.evolved_data_read_transitions += 1
        self.evolved_data_read_addresses.add(address)
        _record_domain_value(self.evolved_data_read_values, address, data_value)
        self.evolved_data_read_state_values[key] = (address, data_value)
        if self.evolved_data_read_witness is None:
            self.evolved_data_read_witness = self._evolved_read_witness(
                node,
                address=address,
                observed_value=data_value,
            )

    def _record_evolved_read_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        self._record_evolved_fetch_evidence(node, transition)
        self._record_evolved_data_read_evidence(node, transition)

    def _record_non_graphical_fetch_observation(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> tuple[_StateKey, int, int] | None:
        if transition.decoded_byte is not None:
            return None
        if classic.is_graphical(transition.fetched_value):
            message = "non-graphical fetch retained a graphical memory value"
            raise AssertionError(message)
        key = _node_key(node)
        if key in self.non_graphical_fetch_state_values:
            message = "non-graphical fetch state was explored more than once"
            raise AssertionError(message)
        address = transition.fetched_address
        value = transition.fetched_value
        self.non_graphical_fetch_transitions += 1
        self.non_graphical_fetch_addresses.add(address)
        _record_domain_value(self.non_graphical_fetch_values, address, value)
        self.non_graphical_fetch_state_values[key] = value
        return key, address, value

    def _record_non_graphical_fetch_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        observation = self._record_non_graphical_fetch_observation(
            node, transition
        )
        if observation is None or self.non_graphical_fetch_witness is not None:
            return
        key, address, value = observation
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        if not path:
            message = "non-graphical fetch witness lost its exact entry path"
            raise AssertionError(message)
        self.non_graphical_fetch_witness = WorklistNonGraphicalFetchWitness(
            state=_cycle_state(key),
            entry_path=tuple(_cycle_state(item) for item in path),
            address=address,
            value=value,
        )

    def _record_changed_encryption_input_observation(
        self,
        node: _ReachabilityNode,
        address: int,
        value: int,
    ) -> None:
        key = _node_key(node)
        states = self.changed_from_initial_encryption_input_state_values
        if key in states:
            message = (
                "changed encryption-input state was explored more than once"
            )
            raise AssertionError(message)
        self.changed_from_initial_encryption_input_transitions += 1
        self.changed_from_initial_encryption_input_addresses.add(address)
        _record_domain_value(
            self.changed_from_initial_encryption_input_values, address, value
        )
        states[key] = (address, value)

    def _record_read_value_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        self._record_non_graphical_fetch_evidence(node, transition)
        _record_domain_value(
            self.fetch_values,
            transition.fetched_address,
            transition.fetched_value,
        )
        if transition.decoded_byte in _DATA_READING_INSTRUCTIONS:
            data_value = transition.data_value
            if data_value is None:
                message = "semantic data read lost its exact value"
                raise AssertionError(message)
            _record_domain_value(
                self.data_read_values, transition.data_address, data_value
            )
        if (
            transition.encryption_address is not None
            and transition.encryption_input is not None
        ):
            address = transition.encryption_address
            value = transition.encryption_input
            self.encryption_input_transitions += 1
            _record_domain_value(self.encryption_input_values, address, value)
            if value == self.initial_memory[address]:
                _record_initial_value_observation(
                    node,
                    self.initial_value_encryption_input_state_values,
                    (address, value, "initial-value encryption input"),
                )
                self.initial_value_encryption_input_transitions += 1
                self.initial_value_encryption_input_addresses.add(address)
            else:
                self._record_changed_encryption_input_observation(
                    node, address, value
                )

    def _data_write_noop_witness(
        self,
        node: _ReachabilityNode,
        mutation: tuple[int, int, int, int, bool],
    ) -> WorklistDataWriteNoopWitness | None:
        address, previous, written, result, aliases = mutation
        key = _node_key(node)
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        if not path:
            return None
        return WorklistDataWriteNoopWitness(
            state=_cycle_state(key),
            entry_path=tuple(_cycle_state(item) for item in path),
            address=address,
            previous_value=previous,
            written_value=written,
            result_value=result,
            aliases_self_encryption=aliases,
        )

    def _record_data_write_noop_evidence(
        self,
        node: _ReachabilityNode,
        mutation: tuple[int, int, int, int, bool],
    ) -> bool:
        address, previous, _, result, _ = mutation
        if result != previous:
            return False
        key = _node_key(node)
        if key in self.committed_data_write_noop_state_values:
            message = "final no-op state was explored more than once"
            raise AssertionError(message)
        self.committed_data_write_noop_transitions += 1
        self.committed_data_write_noop_addresses.add(address)
        self.committed_data_write_noop_state_values[key] = mutation
        if self.data_write_noop_witness is None:
            self.data_write_noop_witness = self._data_write_noop_witness(
                node, mutation
            )
        return True

    def _record_data_mutation_observation(
        self,
        node: _ReachabilityNode,
        mutation: tuple[int, int, int, int, bool],
    ) -> None:
        address, previous, written, result, aliases = mutation
        key = _node_key(node)
        if key in self.effective_data_mutation_state_values:
            message = "effective mutation state was explored more than once"
            raise AssertionError(message)
        self.effective_data_mutation_state_values[key] = (
            address, previous, written, result, aliases
        )

    def _record_data_mutation_evidence(
        self,
        node: _ReachabilityNode,
        step: prefix_transfer.SnapshotStep,
    ) -> None:
        mutation = _committed_data_mutation(step)
        if mutation is None:
            return
        if self._record_data_write_noop_evidence(node, mutation):
            return
        address, previous, written, result, aliases = mutation
        self.effective_data_mutation_transitions += 1
        self.effective_data_mutation_addresses.add(address)
        _record_domain_value(
            self.effective_data_mutation_previous_values, address, previous
        )
        _record_domain_value(
            self.effective_data_mutation_result_values, address, result
        )
        self._record_data_mutation_observation(node, mutation)
        if self.data_mutation_witness is not None:
            return
        key = _node_key(node)
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        if not path:
            message = "data mutation witness lost its exact entry path"
            raise AssertionError(message)
        self.data_mutation_witness = WorklistDataMutationWitness(
            state=_cycle_state(key),
            entry_path=tuple(_cycle_state(item) for item in path),
            address=address,
            previous_value=previous,
            written_value=written,
            result_value=result,
            aliases_self_encryption=aliases,
        )

    def _record_planned_data_write_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        address = transition.planned_data_write_address
        if address is None:
            return
        value = _required_exact_value(
            transition.planned_data_write_value, label="planned data write"
        )
        key = _node_key(node)
        if key in self.planned_data_write_state_values:
            message = "planned data-write state was explored more than once"
            raise AssertionError(message)
        self.planned_data_write_transitions += 1
        self.planned_data_write_addresses.add(address)
        _record_domain_value(self.planned_data_write_values, address, value)
        self.planned_data_write_state_values[key] = (address, value)

    def _record_code_data_alias_observation(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> tuple[int, _StateKey] | None:
        if not transition.code_data_alias:
            return None
        address = transition.fetched_address
        if transition.data_address != address:
            message = "code/data alias flag disagrees with exact addresses"
            raise AssertionError(message)
        key = _node_key(node)
        if key in self.code_data_alias_state_values:
            message = "code/data alias state was explored more than once"
            raise AssertionError(message)
        self.code_data_alias_transitions += 1
        self.code_data_alias_addresses.add(address)
        self.code_data_alias_state_values[key] = transition.fetched_value
        return address, key

    def _record_code_data_alias_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        observation = self._record_code_data_alias_observation(node, transition)
        if observation is None:
            return
        address, key = observation
        if address in self.code_data_alias_witnesses:
            return
        path = _known_graph_shortest_path(
            self.edges,
            self.seen,
            start=_INITIAL_STATE_KEY,
            target=key,
        )
        if not path:
            return
        self.code_data_alias_witnesses[address] = WorklistCodeDataAliasWitness(
            state=_cycle_state(key),
            entry_path=tuple(_cycle_state(item) for item in path),
            address=address,
            memory_value=transition.fetched_value,
        )

    def _record_mutation_evidence(
        self,
        node: _ReachabilityNode,
        step: prefix_transfer.SnapshotStep,
    ) -> None:
        transition = step.transition
        data_write, encryption = _committed_mutation_addresses(step)
        writes = tuple(
            address
            for address in (data_write, encryption)
            if address is not None
        )
        self.committed_writes += len(writes)
        self.committed_write_addresses.update(writes)
        if data_write is not None:
            data_value = _required_exact_value(
                transition.planned_data_write_value,
                label="committed data write",
            )
            self.committed_data_write_transitions += 1
            self.committed_data_write_addresses.add(data_write)
            _record_domain_value(
                self.committed_data_write_values, data_write, data_value
            )
        if encryption is not None:
            encryption_input = _required_exact_value(
                transition.encryption_input,
                label="committed self-encryption input",
            )
            encryption_value = _required_exact_value(
                transition.encryption_output,
                label="committed self-encryption output",
            )
            key = _node_key(node)
            if key in self.self_encryption_state_values:
                message = "committed self-encryption state was explored twice"
                raise AssertionError(message)
            self.self_encryption_transitions += 1
            self.self_encryption_addresses.add(encryption)
            self.self_encryption_state_values[key] = (
                encryption,
                encryption_input,
                encryption_value,
                transition.data_write_aliases_encryption,
            )
            _record_domain_value(
                self.self_encryption_output_values, encryption, encryption_value
            )

    def _process_node(self, node: _ReachabilityNode) -> WorklistAnalysis | None:
        self.explored += 1
        self.explored_code_pointer_addresses.add(node.snapshot.code_pointer)
        self.explored_data_pointer_addresses.add(node.snapshot.data_pointer)
        step = prefix_transfer.analyze_state_snapshot(
            self.initial_memory,
            node.snapshot,
        )
        self.accessed_addresses.update(_transition_accesses(step.transition))
        self._record_read_value_evidence(node, step.transition)
        self._record_evolved_read_evidence(node, step.transition)
        self._record_planned_data_write_evidence(node, step.transition)
        self._record_code_data_alias_evidence(node, step.transition)
        self._record_mutation_evidence(node, step)
        self._record_data_mutation_evidence(node, step)
        if step.transition.pointer_wraps:
            self._record_wraparound(node, step.transition)
        if (
            step.transition.decoded_byte == _INPUT_OPCODE
            and not node.eof_seen
        ):
            self.input_branch_points += 1
            self.input_branch_states.add(_node_key(node))
        successors = _successors(node, step)
        if successors:
            return self._admit_successors(node, successors)
        self._record_terminal(step.transition.status, node)
        return None

    def run(self) -> WorklistAnalysis:
        while self.queue:
            result = self._process_node(self.queue.popleft())
            if result is not None:
                return result
        return self.result(truncated=False)


def analyze_reachability(
    words: tuple[int, ...],
    *,
    maximum_states: int,
) -> WorklistAnalysis:
    """Explore exact reachable states until closure or the explicit state cap.

    Returns:
        Deterministic bounded worklist evidence over all admitted input values.

    """
    state_limit = _state_limit(maximum_states)
    _validate_words(words)
    return _Explorer.create(words, state_limit).run()
