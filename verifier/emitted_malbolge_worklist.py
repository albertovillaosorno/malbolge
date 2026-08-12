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
_EOF_ACCUMULATOR: Final = classic.PROFILE_MEMORY_WORDS - 1
_RECURRENCE_BASE_WORDS: Final = 2

type _StateKey = tuple[
    int,
    int,
    int,
    tuple[tuple[int, int], ...],
    bool,
]


@dataclass(frozen=True, slots=True)
class WorklistAnalysis:
    """Deterministic summary of one bounded exact-state exploration."""

    state_limit: int
    unique_states: int
    explored_states: int
    repeated_state_edges: int
    input_branch_points: int
    terminal_status_counts: tuple[tuple[str, int], ...]
    maximum_transition_index: int
    frontier_states: int
    truncated: bool


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
        return ()
    if step.transition.decoded_byte == _INPUT_OPCODE:
        return _input_successors(successor, eof_seen=node.eof_seen)
    if successor.accumulator is None:
        message = "non-input worklist successor lost a concrete accumulator"
        raise AssertionError(message)
    return (_ReachabilityNode(snapshot=successor, eof_seen=node.eof_seen),)


@dataclass(slots=True)
class _Explorer:
    words: tuple[int, ...]
    state_limit: int
    queue: deque[_ReachabilityNode]
    seen: set[_StateKey]
    terminal_counts: dict[str, int]
    explored: int = 0
    repeated_edges: int = 0
    input_branch_points: int = 0
    maximum_transition_index: int = 1

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
            terminal_counts={},
        )

    def result(
        self,
        *,
        truncated: bool,
        frontier_states: int = 0,
    ) -> WorklistAnalysis:
        return WorklistAnalysis(
            state_limit=self.state_limit,
            unique_states=len(self.seen),
            explored_states=self.explored,
            repeated_state_edges=self.repeated_edges,
            input_branch_points=self.input_branch_points,
            terminal_status_counts=tuple(sorted(self.terminal_counts.items())),
            maximum_transition_index=self.maximum_transition_index,
            frontier_states=frontier_states,
            truncated=truncated,
        )

    def _record_terminal(self, status: str) -> None:
        self.terminal_counts[status] = self.terminal_counts.get(status, 0) + 1

    def _admit_successors(
        self,
        successors: tuple[_ReachabilityNode, ...],
    ) -> WorklistAnalysis | None:
        for successor in successors:
            key = _node_key(successor)
            if key in self.seen:
                self.repeated_edges += 1
                continue
            if len(self.seen) >= self.state_limit:
                return self.result(
                    truncated=True,
                    frontier_states=len(self.queue) + 1,
                )
            self.seen.add(key)
            self.queue.append(successor)
        return None

    def _process_node(self, node: _ReachabilityNode) -> WorklistAnalysis | None:
        self.explored += 1
        self.maximum_transition_index = max(
            self.maximum_transition_index,
            node.snapshot.before_transition,
        )
        step = prefix_transfer.analyze_state_snapshot(self.words, node.snapshot)
        if step.transition.decoded_byte == _INPUT_OPCODE:
            self.input_branch_points += 1
        successors = _successors(node, step)
        if successors:
            return self._admit_successors(successors)
        self._record_terminal(step.transition.status)
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
