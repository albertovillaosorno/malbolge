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
class WorklistCodeDataAliasWitness:
    """First exact entry-reachable C/D alias state for one address."""

    state: WorklistCycleState
    entry_path: tuple[WorklistCycleState, ...]
    address: int
    memory_value: int


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
    terminal_status_counts: tuple[tuple[str, int], ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[WorklistTerminalWitness, ...]
    explored_code_pointer_addresses: tuple[int, ...]
    explored_data_pointer_addresses: tuple[int, ...]
    explored_code_data_alias_transition_count: int
    explored_code_data_alias_addresses: tuple[int, ...]
    explored_code_data_alias_witnesses: tuple[WorklistCodeDataAliasWitness, ...]
    explored_committed_write_count: int
    explored_committed_write_addresses: tuple[int, ...]
    explored_planned_data_write_transition_count: int
    explored_planned_data_write_addresses: tuple[int, ...]
    explored_planned_data_write_value_domains: tuple[WorklistValueDomain, ...]
    explored_committed_data_write_transition_count: int
    explored_committed_data_write_addresses: tuple[int, ...]
    explored_committed_data_write_noop_transition_count: int
    explored_committed_data_write_noop_addresses: tuple[int, ...]
    explored_self_encryption_transition_count: int
    explored_self_encryption_addresses: tuple[int, ...]
    explored_effective_data_mutation_transition_count: int
    explored_effective_data_mutation_addresses: tuple[int, ...]
    explored_effective_data_mutation_value_domains: tuple[
        WorklistDataMutationValueDomain, ...
    ]
    explored_fetch_value_domains: tuple[WorklistValueDomain, ...]
    explored_data_read_value_domains: tuple[WorklistValueDomain, ...]
    explored_encryption_input_value_domains: tuple[WorklistValueDomain, ...]
    explored_encryption_input_transition_count: int
    explored_initial_value_encryption_input_transition_count: int
    explored_initial_value_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_transition_count: int
    explored_changed_from_initial_encryption_input_addresses: tuple[int, ...]
    explored_changed_from_initial_encryption_input_value_domains: tuple[
        WorklistValueDomain, ...
    ]
    explored_committed_data_write_value_domains: tuple[WorklistValueDomain, ...]
    explored_self_encryption_output_value_domains: tuple[
        WorklistValueDomain, ...
    ]
    explored_initial_value_fetch_transition_count: int
    explored_initial_value_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_transition_count: int
    explored_evolved_fetch_addresses: tuple[int, ...]
    explored_evolved_fetch_value_domains: tuple[WorklistValueDomain, ...]
    explored_data_read_transition_count: int
    explored_initial_value_data_read_transition_count: int
    explored_initial_value_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_transition_count: int
    explored_evolved_data_read_addresses: tuple[int, ...]
    explored_evolved_data_read_value_domains: tuple[WorklistValueDomain, ...]
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
    explored_wraparound_witness: WorklistWrapWitness | None
    explored_code_pointer_wrap_witness: WorklistWrapWitness | None
    explored_data_pointer_wrap_witness: WorklistWrapWitness | None
    explored_simultaneous_pointer_wrap_witness: WorklistWrapWitness | None
    maximum_first_seen_transition_index: int
    frontier_states: int
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


def _unseen_successor_count(
    successors: tuple[_ReachabilityNode, ...],
    seen: set[_StateKey],
    *,
    start_index: int,
) -> int:
    unseen = {
        _node_key(successor)
        for successor in successors[start_index:]
        if _node_key(successor) not in seen
    }
    return len(unseen)


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
    code_data_alias_witnesses: dict[int, WorklistCodeDataAliasWitness] = field(
        default_factory=dict
    )
    committed_write_addresses: set[int] = field(default_factory=set)
    planned_data_write_addresses: set[int] = field(default_factory=set)
    planned_data_write_values: dict[int, set[int]] = field(default_factory=dict)
    committed_data_write_addresses: set[int] = field(default_factory=set)
    committed_data_write_noop_addresses: set[int] = field(default_factory=set)
    self_encryption_addresses: set[int] = field(default_factory=set)
    effective_data_mutation_addresses: set[int] = field(default_factory=set)
    effective_data_mutation_previous_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    effective_data_mutation_result_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    fetch_values: dict[int, set[int]] = field(default_factory=dict)
    data_read_values: dict[int, set[int]] = field(default_factory=dict)
    encryption_input_values: dict[int, set[int]] = field(default_factory=dict)
    initial_value_encryption_input_addresses: set[int] = field(
        default_factory=set
    )
    changed_from_initial_encryption_input_addresses: set[int] = field(
        default_factory=set
    )
    changed_from_initial_encryption_input_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    committed_data_write_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    self_encryption_output_values: dict[int, set[int]] = field(
        default_factory=dict
    )
    initial_value_fetch_addresses: set[int] = field(default_factory=set)
    evolved_fetch_addresses: set[int] = field(default_factory=set)
    evolved_fetch_values: dict[int, set[int]] = field(default_factory=dict)
    initial_value_data_read_addresses: set[int] = field(default_factory=set)
    evolved_data_read_addresses: set[int] = field(default_factory=set)
    evolved_data_read_values: dict[int, set[int]] = field(default_factory=dict)
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
    wraparound_transitions: int = 0
    code_pointer_wrap_transitions: int = 0
    data_pointer_wrap_transitions: int = 0
    simultaneous_pointer_wrap_transitions: int = 0
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

    def result(
        self,
        *,
        truncated: bool,
        frontier_states: int = 0,
        frontier_path: tuple[_StateKey, ...] | None = None,
    ) -> WorklistAnalysis:
        if truncated != (frontier_path is not None):
            message = "worklist truncation lost its exact frontier path"
            raise AssertionError(message)
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
            terminal_status_counts=tuple(sorted(self.terminal_counts.items())),
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
            explored_self_encryption_transition_count=(
                self.self_encryption_transitions
            ),
            explored_self_encryption_addresses=tuple(
                sorted(self.self_encryption_addresses)
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
            explored_fetch_value_domains=_value_domains(self.fetch_values),
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
            explored_evolved_fetch_transition_count=(
                self.evolved_fetch_transitions
            ),
            explored_evolved_fetch_addresses=tuple(
                sorted(self.evolved_fetch_addresses)
            ),
            explored_evolved_fetch_value_domains=_value_domains(
                self.evolved_fetch_values
            ),
            explored_data_read_transition_count=self.data_read_transitions,
            explored_initial_value_data_read_transition_count=(
                self.initial_value_data_read_transitions
            ),
            explored_initial_value_data_read_addresses=tuple(
                sorted(self.initial_value_data_read_addresses)
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
            frontier_states=frontier_states,
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
                return self.result(
                    truncated=True,
                    frontier_states=(
                        len(self.queue)
                        + _unseen_successor_count(
                            successors,
                            self.seen,
                            start_index=index,
                        )
                    ),
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
            self.initial_value_fetch_transitions += 1
            self.initial_value_fetch_addresses.add(address)
            return
        self.evolved_fetch_transitions += 1
        self.evolved_fetch_addresses.add(address)
        _record_domain_value(
            self.evolved_fetch_values, address, transition.fetched_value
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
            self.initial_value_data_read_transitions += 1
            self.initial_value_data_read_addresses.add(address)
            return
        self.evolved_data_read_transitions += 1
        self.evolved_data_read_addresses.add(address)
        _record_domain_value(self.evolved_data_read_values, address, data_value)
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

    def _record_read_value_evidence(
        self,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
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
                self.initial_value_encryption_input_transitions += 1
                self.initial_value_encryption_input_addresses.add(address)
            else:
                self.changed_from_initial_encryption_input_transitions += 1
                self.changed_from_initial_encryption_input_addresses.add(
                    address
                )
                _record_domain_value(
                    self.changed_from_initial_encryption_input_values,
                    address,
                    value,
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
        self.committed_data_write_noop_transitions += 1
        self.committed_data_write_noop_addresses.add(address)
        if self.data_write_noop_witness is None:
            self.data_write_noop_witness = self._data_write_noop_witness(
                node, mutation
            )
        return True

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
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        address = transition.planned_data_write_address
        if address is None:
            return
        value = _required_exact_value(
            transition.planned_data_write_value, label="planned data write"
        )
        self.planned_data_write_transitions += 1
        self.planned_data_write_addresses.add(address)
        _record_domain_value(self.planned_data_write_values, address, value)

    def _record_code_data_alias_evidence(
        self,
        node: _ReachabilityNode,
        transition: prefix_transfer.SecondTransition,
    ) -> None:
        if not transition.code_data_alias:
            return
        self.code_data_alias_transitions += 1
        address = transition.fetched_address
        if transition.data_address != address:
            message = "code/data alias flag disagrees with exact addresses"
            raise AssertionError(message)
        self.code_data_alias_addresses.add(address)
        if address in self.code_data_alias_witnesses:
            return
        key = _node_key(node)
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
            encryption_value = _required_exact_value(
                transition.encryption_output,
                label="committed self-encryption output",
            )
            self.self_encryption_transitions += 1
            self.self_encryption_addresses.add(encryption)
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
        self._record_read_value_evidence(step.transition)
        self._record_evolved_read_evidence(node, step.transition)
        self._record_planned_data_write_evidence(step.transition)
        self._record_code_data_alias_evidence(node, step.transition)
        self._record_mutation_evidence(step)
        self._record_data_mutation_evidence(node, step)
        if step.transition.pointer_wraps:
            self._record_wraparound(node, step.transition)
        if (
            step.transition.decoded_byte == _INPUT_OPCODE
            and not node.eof_seen
        ):
            self.input_branch_points += 1
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
