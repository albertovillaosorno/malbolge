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

_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_INPUT_OPCODE: Final = ord("/")
_INPUT_BYTES: Final = tuple(range(256))
_DATA_READING_INSTRUCTIONS: Final = frozenset(b"ji*p")
_EOF_ACCUMULATOR: Final = classic.PROFILE_MEMORY_WORDS - 1
_HALTED_STATUS: Final = "halted"
_RECURRENCE_BASE_WORDS: Final = 2

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
class WorklistAnalysis:
    """Deterministic summary of one bounded exact-state exploration."""

    state_limit: int
    unique_states: int
    explored_states: int
    repeated_state_edges: int
    reachable_cycle_detected: bool
    reachable_cycle_witness: tuple[WorklistCycleState, ...]
    reachable_cycle_entry_path: tuple[WorklistCycleState, ...]
    known_graph_strong_component_count: int
    known_graph_cyclic_component_count: int
    known_graph_cyclic_state_count: int
    known_graph_largest_cyclic_component_states: int
    closed_recurrent_component_count: int | None
    closed_recurrent_state_count: int | None
    closed_recurrent_largest_component_states: int | None
    closed_recurrent_cycle_witness: tuple[WorklistCycleState, ...] | None
    closed_recurrent_entry_path: tuple[WorklistCycleState, ...] | None
    input_branch_points: int
    terminal_status_counts: tuple[tuple[str, int], ...]
    closed_terminal_status_counts: tuple[tuple[str, int], ...] | None
    closed_all_paths_terminate: bool | None
    closed_all_paths_halt: bool | None
    terminal_status_witnesses: tuple[WorklistTerminalWitness, ...]
    explored_minimum_words: int
    explored_highest_accessed_address: int
    explored_accessed_addresses: tuple[int, ...]
    explored_wraparound_transition_count: int
    maximum_first_seen_transition_index: int
    frontier_states: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class _StrongComponentSummary:
    """Exact SCC counts over only the admitted known directed graph."""

    component_count: int
    cyclic_component_count: int
    cyclic_state_count: int
    largest_cyclic_component_states: int
    cyclic_sink_components: tuple[tuple[_StateKey, ...], ...]


@dataclass(frozen=True, slots=True)
class _ClosedRecurrenceEvidence:
    """Nullable recurrent sink evidence after complete graph closure."""

    component_count: int | None
    state_count: int | None
    largest_component_states: int | None
    cycle_witness: tuple[WorklistCycleState, ...] | None
    entry_path: tuple[WorklistCycleState, ...] | None


@dataclass(frozen=True, slots=True)
class _ReachabilityNode:
    snapshot: prefix_transfer.StateSnapshot
    eof_seen: bool


def _state_limit(value: object) -> int:
    if type(value) is int and value > 0:
        return value
    message = "worklist state limit must be a positive exact integer"
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


def _cycle_state(key: _StateKey) -> WorklistCycleState:
    code_pointer, data_pointer, accumulator, memory_overrides, eof_seen = key
    return WorklistCycleState(
        code_pointer=code_pointer,
        data_pointer=data_pointer,
        accumulator=accumulator,
        memory_overrides=memory_overrides,
        eof_seen=eof_seen,
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
        return _ClosedRecurrenceEvidence(None, None, None, None, None)
    components = summary.cyclic_sink_components
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
        cycle_witness=tuple(_cycle_state(key) for key in witness_keys),
        entry_path=tuple(_cycle_state(key) for key in entry_path_keys),
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
    terminal_states: dict[str, set[_StateKey]] = field(default_factory=dict)
    explored: int = 0
    repeated_edges: int = 0
    input_branch_points: int = 0
    wraparound_transitions: int = 0
    maximum_first_seen_transition_index: int = 1

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

    def result(
        self,
        *,
        truncated: bool,
        frontier_states: int = 0,
    ) -> WorklistAnalysis:
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
        recurrence = _closed_recurrence_evidence(
            component_summary,
            self.edges,
            nodes=self.seen,
            truncated=truncated,
        )
        return WorklistAnalysis(
            state_limit=self.state_limit,
            unique_states=len(self.seen),
            explored_states=self.explored,
            repeated_state_edges=self.repeated_edges,
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
            closed_recurrent_component_count=recurrence.component_count,
            closed_recurrent_state_count=recurrence.state_count,
            closed_recurrent_largest_component_states=(
                recurrence.largest_component_states
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
            explored_minimum_words=max(
                len(self.words),
                highest_address + 1,
            ),
            explored_highest_accessed_address=highest_address,
            explored_accessed_addresses=ordered_addresses,
            explored_wraparound_transition_count=self.wraparound_transitions,
            maximum_first_seen_transition_index=(
                self.maximum_first_seen_transition_index
            ),
            frontier_states=frontier_states,
            truncated=truncated,
        )

    def _record_terminal(self, status: str, node: _ReachabilityNode) -> None:
        self.terminal_counts[status] = self.terminal_counts.get(status, 0) + 1
        states = self.terminal_states.setdefault(status, set())
        states.add(_node_key(node))

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
                source_edges.add(key)
                self.repeated_edges += 1
                continue
            if len(self.seen) >= self.state_limit:
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

    def _process_node(self, node: _ReachabilityNode) -> WorklistAnalysis | None:
        self.explored += 1
        step = prefix_transfer.analyze_state_snapshot(self.words, node.snapshot)
        self.accessed_addresses.update(_transition_accesses(step.transition))
        if step.transition.pointer_wraps:
            self.wraparound_transitions += 1
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
