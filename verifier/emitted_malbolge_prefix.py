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
#   - Exact static transfer for one continuation after an explicit finite
#     classic Malbolge prefix.
# - Must-Not:
#   - Iterate a worklist, execute an unbounded loop, or infer later
#     reachability.
# - Allows:
#   - Inputs: admitted initial words plus accepted bounded-prefix records.
#   - Outputs: exact second/third/fourth-step state or bounded unresolved
#     status.
#   - Side effects: none.
# - Split-When:
#   - General cyclic reachability or abstract-state exploration gains ownership.
# - Merge-When:
#   - A bounded-prefix verifier owns both entry and second transfer directly.
# - Summary:
#   - Exact bounded continuation after the classic entry step.
# - Description:
#   - Replays caller-supplied committed prefix writes and resolves one next
#     step.
# - Usage:
#   - Called after entry transfer succeeds and does not halt.
# - Defaults:
#   - Input-dependent crazy state is reported unresolved rather than guessed.
#

"""Exact next-step transfer after explicit bounded classic prefixes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if __package__:
    from verifier import emitted_malbolge_classic as classic
    from verifier import emitted_malbolge_entry as entry_transfer
else:
    import emitted_malbolge_classic as classic
    import emitted_malbolge_entry as entry_transfer

if TYPE_CHECKING:
    from collections.abc import Callable

_STATUS_CONTINUED = "continued"
_STATUS_HALTED = "halted"
_STATUS_STUCK = "stuck-non-graphical-fetch"
_STATUS_INVALID_ENCRYPTION = "rejected-invalid-self-encryption"
_STATUS_INPUT_UNRESOLVED = "unresolved-input-dependent-accumulator"


@dataclass(frozen=True, slots=True)
class SecondTransition:
    """Exact or explicitly unresolved second historical transition."""

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

    @property
    def accepted(self) -> bool:
        """Bounded second-step acceptance.

        Returns:
            Whether the second step is exactly safe or halts.

        """
        return self.status in {_STATUS_CONTINUED, _STATUS_HALTED}


@dataclass(frozen=True, slots=True)
class ExactCycleCertificate:
    """One exact repeated concrete state inside a bounded classic trace."""

    first_seen_before_transition: int
    repeated_before_transition: int
    period_transitions: int
    code_pointer: int
    data_pointer: int
    accumulator: int
    memory_overrides: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class ContinuationAnalysis:
    """Bounded continuation transitions plus an optional exact cycle proof."""

    transitions: tuple[SecondTransition, ...]
    exact_cycle: ExactCycleCertificate | None


@dataclass(frozen=True, slots=True)
class _FetchedState:
    address: int
    value: int
    decoded: int | None
    data_address: int
    data_value: int | None
    accumulator: int | None


@dataclass(frozen=True, slots=True)
class _PlanContext:
    code_pointer: int
    data_pointer: int
    accumulator: int | None
    data_value: int


@dataclass(frozen=True, slots=True)
class _StepPlan:
    code_pointer: int
    data_pointer: int
    accumulator: int | None
    data_write_address: int | None = None
    data_write_value: int | None = None
    input_dependent: bool = False
    halted: bool = False
    unresolved: bool = False


@dataclass(frozen=True, slots=True)
class _MemoryState:
    words: tuple[int, ...]
    overrides: tuple[tuple[int, int], ...] = ()

    def read(self, address: int) -> int:
        """Read one address after replaying bounded committed writes.

        Returns:
            Current override or the exact immutable initial-memory value.

        """
        for override_address, value in self.overrides:
            if override_address == address:
                return value
        return classic.initial_memory_value(self.words, address)


@dataclass(frozen=True, slots=True)
class _MachineState:
    code_pointer: int
    data_pointer: int
    accumulator: int | None


def _commit_write(
    memory: _MemoryState,
    address: int | None,
    value: int | None,
) -> _MemoryState:
    if address is None or value is None:
        return memory
    overrides = dict(memory.overrides)
    initial = classic.initial_memory_value(memory.words, address)
    if value == initial:
        _ = overrides.pop(address, None)
    else:
        overrides[address] = value
    return _MemoryState(memory.words, tuple(sorted(overrides.items())))


def _memory_after_entry(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> _MemoryState:
    memory = _MemoryState(words)
    memory = _commit_write(
        memory,
        entry.planned_data_write_address,
        entry.planned_data_write_value,
    )
    return _commit_write(
        memory,
        entry.encryption_address,
        entry.encryption_output,
    )


def _memory_after_transition(
    memory: _MemoryState,
    transition: SecondTransition,
) -> _MemoryState:
    result = _commit_write(
        memory,
        transition.planned_data_write_address,
        transition.planned_data_write_value,
    )
    return _commit_write(
        result,
        transition.encryption_address,
        transition.encryption_output,
    )


def _fetch_state(
    memory: _MemoryState,
    state: _MachineState,
) -> _FetchedState:
    address = state.code_pointer
    value = memory.read(address)
    decoded = classic.decode(value, address)
    data_value = None if decoded is None else memory.read(state.data_pointer)
    return _FetchedState(
        address,
        value,
        decoded,
        state.data_pointer,
        data_value,
        state.accumulator,
    )


def _plan_noop(context: _PlanContext) -> _StepPlan:
    return _StepPlan(
        context.code_pointer,
        context.data_pointer,
        context.accumulator,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_data(context: _PlanContext) -> _StepPlan:
    return _StepPlan(
        context.code_pointer,
        context.data_value,
        context.accumulator,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_code(context: _PlanContext) -> _StepPlan:
    return _StepPlan(
        context.data_value,
        context.data_pointer,
        context.accumulator,
        input_dependent=context.accumulator is None,
    )


def _plan_rotate(context: _PlanContext) -> _StepPlan:
    value = classic.rotate(context.data_value)
    return _StepPlan(
        context.code_pointer,
        context.data_pointer,
        value,
        data_write_address=context.data_pointer,
        data_write_value=value,
    )


def _plan_crazy(context: _PlanContext) -> _StepPlan:
    accumulator = context.accumulator
    if accumulator is None:
        return _StepPlan(
            context.code_pointer,
            context.data_pointer,
            None,
            input_dependent=True,
            unresolved=True,
        )
    value = classic.crazy(context.data_value, accumulator)
    return _StepPlan(
        context.code_pointer,
        context.data_pointer,
        value,
        data_write_address=context.data_pointer,
        data_write_value=value,
    )


def _plan_input(context: _PlanContext) -> _StepPlan:
    return _StepPlan(
        context.code_pointer,
        context.data_pointer,
        None,
        input_dependent=True,
    )


def _plan_halt(context: _PlanContext) -> _StepPlan:
    return _StepPlan(
        context.code_pointer,
        context.data_pointer,
        context.accumulator,
        halted=True,
    )


_PLANNERS: dict[int, Callable[[_PlanContext], _StepPlan]] = {
    ord("j"): _plan_jump_data,
    ord("i"): _plan_jump_code,
    ord("*"): _plan_rotate,
    ord("p"): _plan_crazy,
    ord("/"): _plan_input,
    ord("v"): _plan_halt,
}


def _plan(fetched: _FetchedState) -> _StepPlan:
    if fetched.decoded is None or fetched.data_value is None:
        message = "graphical second fetch must have decoded data state"
        raise AssertionError(message)
    context = _PlanContext(
        fetched.address,
        fetched.data_address,
        fetched.accumulator,
        fetched.data_value,
    )
    planner = _PLANNERS.get(fetched.decoded, _plan_noop)
    return planner(context)


def _terminal(
    fetched: _FetchedState,
    status: str,
    *,
    provable_cycle: bool = False,
) -> SecondTransition:
    next_fetch = fetched.address if provable_cycle else None
    return SecondTransition(
        status=status,
        fetched_address=fetched.address,
        fetched_value=fetched.value,
        decoded_byte=fetched.decoded,
        data_address=fetched.data_address,
        data_value=fetched.data_value,
        code_data_alias=fetched.address == fetched.data_address,
        planned_data_write_address=None,
        planned_data_write_value=None,
        encryption_address=None,
        encryption_input=None,
        encryption_output=None,
        data_write_aliases_encryption=False,
        input_dependent_accumulator=fetched.accumulator is None,
        result_accumulator=fetched.accumulator,
        result_code_pointer=fetched.address,
        result_data_pointer=fetched.data_address,
        next_fetch_address=next_fetch,
        pointer_wraps=False,
        provable_cycle=provable_cycle,
    )


def _unresolved(fetched: _FetchedState) -> SecondTransition:
    return SecondTransition(
        status=_STATUS_INPUT_UNRESOLVED,
        fetched_address=fetched.address,
        fetched_value=fetched.value,
        decoded_byte=fetched.decoded,
        data_address=fetched.data_address,
        data_value=fetched.data_value,
        code_data_alias=fetched.address == fetched.data_address,
        planned_data_write_address=None,
        planned_data_write_value=None,
        encryption_address=None,
        encryption_input=None,
        encryption_output=None,
        data_write_aliases_encryption=False,
        input_dependent_accumulator=True,
        result_accumulator=None,
        result_code_pointer=None,
        result_data_pointer=None,
        next_fetch_address=None,
        pointer_wraps=False,
        provable_cycle=False,
    )


def _encryption_input(
    memory: _MemoryState,
    plan: _StepPlan,
) -> tuple[int, bool]:
    aliases = plan.data_write_address == plan.code_pointer
    if aliases and plan.data_write_value is not None:
        return plan.data_write_value, True
    return memory.read(plan.code_pointer), False


def _resolved(
    memory: _MemoryState,
    fetched: _FetchedState,
    *,
    plan: _StepPlan,
) -> SecondTransition:
    encryption_input, aliases = _encryption_input(memory, plan)
    encrypted = classic.encrypt(encryption_input)
    if encrypted is None:
        return SecondTransition(
            status=_STATUS_INVALID_ENCRYPTION,
            fetched_address=fetched.address,
            fetched_value=fetched.value,
            decoded_byte=fetched.decoded,
            data_address=fetched.data_address,
            data_value=fetched.data_value,
            code_data_alias=fetched.address == fetched.data_address,
            planned_data_write_address=plan.data_write_address,
            planned_data_write_value=plan.data_write_value,
            encryption_address=plan.code_pointer,
            encryption_input=encryption_input,
            encryption_output=None,
            data_write_aliases_encryption=aliases,
            input_dependent_accumulator=plan.input_dependent,
            result_accumulator=plan.accumulator,
            result_code_pointer=fetched.address,
            result_data_pointer=fetched.data_address,
            next_fetch_address=None,
            pointer_wraps=False,
            provable_cycle=False,
        )
    result_code = classic.pointer_successor(plan.code_pointer)
    result_data = classic.pointer_successor(plan.data_pointer)
    return SecondTransition(
        status=_STATUS_CONTINUED,
        fetched_address=fetched.address,
        fetched_value=fetched.value,
        decoded_byte=fetched.decoded,
        data_address=fetched.data_address,
        data_value=fetched.data_value,
        code_data_alias=fetched.address == fetched.data_address,
        planned_data_write_address=plan.data_write_address,
        planned_data_write_value=plan.data_write_value,
        encryption_address=plan.code_pointer,
        encryption_input=encryption_input,
        encryption_output=encrypted,
        data_write_aliases_encryption=aliases,
        input_dependent_accumulator=plan.input_dependent,
        result_accumulator=plan.accumulator,
        result_code_pointer=result_code,
        result_data_pointer=result_data,
        next_fetch_address=result_code,
        pointer_wraps=(
            plan.code_pointer == classic.PROFILE_MEMORY_WORDS - 1
            or plan.data_pointer == classic.PROFILE_MEMORY_WORDS - 1
        ),
        provable_cycle=False,
    )


def _analyze_state(
    memory: _MemoryState,
    state: _MachineState,
) -> SecondTransition:
    fetched = _fetch_state(memory, state)
    if fetched.decoded is None:
        result = _terminal(fetched, _STATUS_STUCK, provable_cycle=True)
    else:
        plan = _plan(fetched)
        if plan.halted:
            result = _terminal(fetched, _STATUS_HALTED)
        elif plan.unresolved:
            result = _unresolved(fetched)
        else:
            result = _resolved(memory, fetched, plan=plan)
    return result


def _state_after_entry(
    entry: entry_transfer.EntryTransition,
) -> _MachineState | None:
    if not entry.accepted or entry.next_fetch_address is None:
        return None
    return _MachineState(
        entry.next_fetch_address,
        entry.result_data_pointer,
        entry.result_accumulator,
    )


def _state_after_transition(
    transition: SecondTransition,
) -> _MachineState | None:
    if not transition.accepted or transition.next_fetch_address is None:
        return None
    data_pointer = transition.result_data_pointer
    if data_pointer is None:
        message = "accepted continued prefix step must retain a data pointer"
        raise AssertionError(message)
    return _MachineState(
        transition.next_fetch_address,
        data_pointer,
        transition.result_accumulator,
    )


def _exact_state_key(
    memory: _MemoryState,
    state: _MachineState | None,
) -> tuple[int, int, int, tuple[tuple[int, int], ...]] | None:
    if state is None:
        return None
    accumulator = state.accumulator
    if accumulator is None:
        return None
    return (
        state.code_pointer,
        state.data_pointer,
        accumulator,
        memory.overrides,
    )


def _cycle_certificate(
    first_seen: int,
    repeated: int,
    *,
    memory: _MemoryState,
    state: _MachineState,
) -> ExactCycleCertificate:
    accumulator = state.accumulator
    if accumulator is None:
        message = "exact cycle certificate requires a concrete accumulator"
        raise AssertionError(message)
    return ExactCycleCertificate(
        first_seen_before_transition=first_seen,
        repeated_before_transition=repeated,
        period_transitions=repeated - first_seen,
        code_pointer=state.code_pointer,
        data_pointer=state.data_pointer,
        accumulator=accumulator,
        memory_overrides=memory.overrides,
    )


def _remember_exact_state(
    seen: dict[tuple[int, int, int, tuple[tuple[int, int], ...]], int],
    memory: _MemoryState,
    state: _MachineState | None,
    *,
    before_transition: int,
) -> ExactCycleCertificate | None:
    key = _exact_state_key(memory, state)
    if key is None:
        return None
    first_seen = seen.get(key)
    if first_seen is None:
        seen[key] = before_transition
        return None
    if state is None:
        message = "remembered exact state unexpectedly lost machine state"
        raise AssertionError(message)
    return _cycle_certificate(
        first_seen,
        before_transition,
        memory=memory,
        state=state,
    )


def _validate_entry_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> None:
    expected = entry_transfer.analyze_entry_transition(
        words,
        entry.decoded_byte,
    )
    if entry != expected:
        message = "explicit entry transition does not match recomputed state"
        raise AssertionError(message)


def analyze_next_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    prior: tuple[SecondTransition, ...],
) -> SecondTransition | None:
    """Resolve exactly one transition after an explicit accepted prefix.

    Returns:
        Next-step evidence, or ``None`` when the supplied prefix is terminal.

    Raises:
        AssertionError: If a supplied transition is not the exact next state.

    """
    _validate_entry_transition(words, entry)
    memory = _memory_after_entry(words, entry)
    state = _state_after_entry(entry)
    for transition in prior:
        if state is None:
            return None
        expected = _analyze_state(memory, state)
        if transition != expected:
            message = (
                "explicit prefix transition does not match recomputed state"
            )
            raise AssertionError(message)
        memory = _memory_after_transition(memory, transition)
        state = _state_after_transition(transition)
    if state is None:
        return None
    return _analyze_state(memory, state)


def analyze_continuation_trace(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    *,
    maximum_transitions: int,
) -> ContinuationAnalysis:
    """Resolve a finite continuation and prove any repeated concrete state.

    Returns:
        Ordered transitions plus the first exact concrete-state cycle, if any.

    Raises:
        ValueError: If ``maximum_transitions`` is not a positive exact integer.

    """
    if type(maximum_transitions) is not int or maximum_transitions <= 0:
        message = "maximum transitions must be a positive exact integer"
        raise ValueError(message)
    _validate_entry_transition(words, entry)
    memory = _memory_after_entry(words, entry)
    state = _state_after_entry(entry)
    transitions: list[SecondTransition] = []
    seen: dict[
        tuple[int, int, int, tuple[tuple[int, int], ...]],
        int,
    ] = {}
    _ = _remember_exact_state(seen, memory, state, before_transition=2)
    for _ in range(maximum_transitions):
        if state is None:
            break
        transition = _analyze_state(memory, state)
        transitions.append(transition)
        memory = _memory_after_transition(memory, transition)
        state = _state_after_transition(transition)
        cycle = _remember_exact_state(
            seen,
            memory,
            state,
            before_transition=len(transitions) + 2,
        )
        if cycle is not None:
            return ContinuationAnalysis(tuple(transitions), cycle)
    return ContinuationAnalysis(tuple(transitions), None)


def analyze_continuations(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    *,
    maximum_transitions: int,
) -> tuple[SecondTransition, ...]:
    """Resolve up to ``maximum_transitions`` exact steps after entry.

    Returns:
        Ordered evidence, stopping at terminal, unresolved, or exact cycle.

    """
    return analyze_continuation_trace(
        words,
        entry,
        maximum_transitions=maximum_transitions,
    ).transitions


def analyze_second_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> SecondTransition | None:
    """Resolve one exact second transition after an accepted entry step.

    Returns:
        Second-step evidence, or ``None`` when entry has no successor fetch.

    """
    return analyze_next_transition(words, entry, ())


def analyze_third_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    second: SecondTransition,
) -> SecondTransition | None:
    """Resolve one exact third transition after two accepted prefix steps.

    Returns:
        Third-step evidence, or ``None`` when the second step has no successor.

    """
    return analyze_next_transition(words, entry, (second,))


def analyze_fourth_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    second: SecondTransition,
    *,
    third: SecondTransition,
) -> SecondTransition | None:
    """Resolve one exact fourth transition after three accepted prefix steps.

    Returns:
        Fourth-step evidence, or ``None`` when the third step has no successor.

    """
    return analyze_next_transition(words, entry, (second, third))
