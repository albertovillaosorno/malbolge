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
#   - Exact static transfer for the first classic Malbolge transition.
# - Must-Not:
#   - Iterate guest execution or claim reachability beyond the entry step.
# - Allows:
#   - Inputs: admitted initial source words and the decoded entry instruction.
#   - Outputs: deterministic entry transition and rejection evidence.
#   - Side effects: none.
# - Split-When:
#   - Multi-step control-flow requires a worklist, abstract state, or widening.
# - Merge-When:
#   - Initial-image admission owns dynamic transfer semantics directly.
# - Summary:
#   - Exact one-step static transfer from the historical all-zero entry state.
# - Description:
#   - Resolves entry aliases, recurrence reads, self-encryption, and pointers.
# - Usage:
#   - Called only after classic initial-image admission succeeds.
# - Defaults:
#   - Later control flow and input-dependent cycles remain unknown.
#

"""Exact bounded entry transfer for admitted classic Malbolge images."""

from __future__ import annotations

from dataclasses import dataclass

if __package__:
    from verifier import emitted_malbolge_classic as classic
else:
    import emitted_malbolge_classic as classic

_ENTRY_CONTINUED = "continued"
_ENTRY_HALTED = "halted"
_ENTRY_INVALID_ENCRYPTION = "rejected-invalid-self-encryption"


@dataclass(frozen=True, slots=True)
class EntryTransition:
    """Exact first transition from the historical all-zero register state."""

    status: str
    fetched_address: int
    decoded_byte: int
    data_address: int
    code_data_alias: bool
    planned_data_write_address: int | None
    planned_data_write_value: int | None
    encryption_address: int | None
    encryption_input: int | None
    encryption_output: int | None
    data_write_aliases_encryption: bool
    input_dependent_accumulator: bool
    result_accumulator: int | None
    result_code_pointer: int
    result_data_pointer: int
    next_fetch_address: int | None
    pointer_wraps: bool

    @property
    def accepted(self) -> bool:
        """Bounded entry-step acceptance status."""
        return self.status != _ENTRY_INVALID_ENCRYPTION


def _halted(decoded: int) -> EntryTransition:
    return EntryTransition(
        status=_ENTRY_HALTED,
        fetched_address=0,
        decoded_byte=decoded,
        data_address=0,
        code_data_alias=True,
        planned_data_write_address=None,
        planned_data_write_value=None,
        encryption_address=None,
        encryption_input=None,
        encryption_output=None,
        data_write_aliases_encryption=False,
        input_dependent_accumulator=False,
        result_accumulator=0,
        result_code_pointer=0,
        result_data_pointer=0,
        next_fetch_address=None,
        pointer_wraps=False,
    )


@dataclass(frozen=True, slots=True)
class _EntryPlan:
    code_pointer: int = 0
    data_pointer: int = 0
    accumulator: int | None = 0
    data_write_address: int | None = None
    data_write_value: int | None = None
    input_dependent: bool = False
    halted: bool = False


@dataclass(frozen=True, slots=True)
class _EncryptionState:
    address: int
    input_value: int
    aliases_data_write: bool


def _plan_noop(_: int) -> _EntryPlan:
    return _EntryPlan()


def _plan_halt(_: int) -> _EntryPlan:
    return _EntryPlan(halted=True)


def _plan_jump_data(data_value: int) -> _EntryPlan:
    return _EntryPlan(data_pointer=data_value)


def _plan_jump_code(data_value: int) -> _EntryPlan:
    return _EntryPlan(code_pointer=data_value)


def _plan_rotate(data_value: int) -> _EntryPlan:
    rotated = classic.rotate(data_value)
    return _EntryPlan(
        accumulator=rotated,
        data_write_address=0,
        data_write_value=rotated,
    )


def _plan_crazy(data_value: int) -> _EntryPlan:
    result = classic.crazy(data_value, 0)
    return _EntryPlan(
        accumulator=result,
        data_write_address=0,
        data_write_value=result,
    )


def _plan_input(_: int) -> _EntryPlan:
    return _EntryPlan(accumulator=None, input_dependent=True)


_ENTRY_PLANNERS = {
    ord("j"): _plan_jump_data,
    ord("i"): _plan_jump_code,
    ord("*"): _plan_rotate,
    ord("p"): _plan_crazy,
    ord("/"): _plan_input,
    ord("v"): _plan_halt,
}


def _instruction_plan(decoded: int, data_value: int) -> _EntryPlan:
    return _ENTRY_PLANNERS.get(decoded, _plan_noop)(data_value)


def _encryption_state(
    words: tuple[int, ...], plan: _EntryPlan
) -> _EncryptionState:
    address = plan.code_pointer
    aliases = plan.data_write_address == address
    input_value = (
        plan.data_write_value
        if aliases and plan.data_write_value is not None
        else classic.initial_memory_value(words, address)
    )
    return _EncryptionState(address, input_value, aliases)


def _rejected(
    decoded: int,
    plan: _EntryPlan,
    encryption: _EncryptionState,
) -> EntryTransition:
    return EntryTransition(
        status=_ENTRY_INVALID_ENCRYPTION,
        fetched_address=0,
        decoded_byte=decoded,
        data_address=0,
        code_data_alias=True,
        planned_data_write_address=plan.data_write_address,
        planned_data_write_value=plan.data_write_value,
        encryption_address=encryption.address,
        encryption_input=encryption.input_value,
        encryption_output=None,
        data_write_aliases_encryption=encryption.aliases_data_write,
        input_dependent_accumulator=plan.input_dependent,
        result_accumulator=0,
        result_code_pointer=0,
        result_data_pointer=0,
        next_fetch_address=None,
        pointer_wraps=False,
    )


def _continued(
    decoded: int,
    plan: _EntryPlan,
    encryption: _EncryptionState,
) -> EntryTransition:
    result_code = classic.pointer_successor(plan.code_pointer)
    result_data = classic.pointer_successor(plan.data_pointer)
    return EntryTransition(
        status=_ENTRY_CONTINUED,
        fetched_address=0,
        decoded_byte=decoded,
        data_address=0,
        code_data_alias=True,
        planned_data_write_address=plan.data_write_address,
        planned_data_write_value=plan.data_write_value,
        encryption_address=encryption.address,
        encryption_input=encryption.input_value,
        encryption_output=classic.encrypt(encryption.input_value),
        data_write_aliases_encryption=encryption.aliases_data_write,
        input_dependent_accumulator=plan.input_dependent,
        result_accumulator=plan.accumulator,
        result_code_pointer=result_code,
        result_data_pointer=result_data,
        next_fetch_address=result_code,
        pointer_wraps=(
            plan.code_pointer == classic.PROFILE_MEMORY_WORDS - 1
            or plan.data_pointer == classic.PROFILE_MEMORY_WORDS - 1
        ),
    )


def analyze_entry_transition(
    words: tuple[int, ...], decoded: int
) -> EntryTransition:
    """Resolve one exact entry transition without executing a guest loop.

    Returns:
        Entry-state transfer or atomic invalid-self-encryption rejection.

    """
    plan = _instruction_plan(decoded, words[0])
    if plan.halted:
        return _halted(decoded)
    encryption = _encryption_state(words, plan)
    if not classic.is_graphical(encryption.input_value):
        return _rejected(decoded, plan, encryption)
    return _continued(decoded, plan, encryption)
