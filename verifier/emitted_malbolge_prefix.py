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
#   - Exact static transfer for the second classic Malbolge transition.
# - Must-Not:
#   - Iterate a worklist, execute an unbounded loop, or infer later
#     reachability.
# - Allows:
#   - Inputs: admitted initial words and one accepted entry-transition record.
#   - Outputs: exact second-step state or an explicit bounded unresolved status.
#   - Side effects: none.
# - Split-When:
#   - Third-step or cyclic reachability requires a general abstract-state model.
# - Merge-When:
#   - A bounded-prefix verifier owns both entry and second transfer directly.
# - Summary:
#   - Exact second-transition analysis after one admitted classic entry step.
# - Description:
#   - Replays committed entry writes, then resolves one more historical step.
# - Usage:
#   - Called after entry transfer succeeds and does not halt.
# - Defaults:
#   - Input-dependent crazy state is reported unresolved rather than guessed.
#

"""Exact second-step transfer for bounded classic Malbolge prefix analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if __package__:
    from verifier import emitted_malbolge_classic as classic
else:
    import emitted_malbolge_classic as classic

if TYPE_CHECKING:
    from collections.abc import Callable

    if __package__:
        from verifier import emitted_malbolge_entry as entry_transfer
    else:
        import emitted_malbolge_entry as entry_transfer

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


def _read_after_entry(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    address: int,
) -> int:
    if (
        entry.encryption_address == address
        and entry.encryption_output is not None
    ):
        return entry.encryption_output
    if (
        entry.planned_data_write_address == address
        and entry.planned_data_write_value is not None
        and entry.planned_data_write_address != entry.encryption_address
    ):
        return entry.planned_data_write_value
    return classic.initial_memory_value(words, address)


def _fetch_state(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> _FetchedState:
    address = entry.next_fetch_address
    if address is None:
        message = "accepted continued entry must name a second fetch"
        raise AssertionError(message)
    value = _read_after_entry(words, entry, address)
    decoded = classic.decode(value, address)
    data_address = entry.result_data_pointer
    data_value = (
        None
        if decoded is None
        else _read_after_entry(words, entry, data_address)
    )
    return _FetchedState(
        address,
        value,
        decoded,
        data_address,
        data_value,
        entry.result_accumulator,
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
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    plan: _StepPlan,
) -> tuple[int, bool]:
    aliases = plan.data_write_address == plan.code_pointer
    if aliases and plan.data_write_value is not None:
        return plan.data_write_value, True
    return _read_after_entry(words, entry, plan.code_pointer), False


def _resolved(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    fetched: _FetchedState,
    *,
    plan: _StepPlan,
) -> SecondTransition:
    encryption_input, aliases = _encryption_input(words, entry, plan)
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


def analyze_second_transition(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> SecondTransition | None:
    """Resolve one exact second transition after an accepted entry step.

    Returns:
        Second-step evidence, or ``None`` when entry has no successor fetch.

    """
    result: SecondTransition | None = None
    if entry.accepted and entry.next_fetch_address is not None:
        fetched = _fetch_state(words, entry)
        if fetched.decoded is None:
            result = _terminal(fetched, _STATUS_STUCK, provable_cycle=True)
        else:
            plan = _plan(fetched)
            if plan.halted:
                result = _terminal(fetched, _STATUS_HALTED)
            elif plan.unresolved:
                result = _unresolved(fetched)
            else:
                result = _resolved(words, entry, fetched, plan=plan)
    return result
