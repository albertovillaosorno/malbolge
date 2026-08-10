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
from typing import Final

_PROFILE_MEMORY_WORDS: Final = 59_049
_GRAPHICAL_START: Final = 33
_GRAPHICAL_END: Final = 126
_ENTRY_CONTINUED: Final = "continued"
_ENTRY_HALTED: Final = "halted"
_ENTRY_INVALID_ENCRYPTION: Final = "rejected-invalid-self-encryption"
_CRAZY_TRIT: Final = ((1, 0, 0), (1, 0, 2), (2, 2, 1))
_XLAT2: Final = bytes.fromhex(
    "357a5d2667717479667224287765347b575029482d5a6e2c5b255c33644c2b51"
    "3b3e5521704a53373246684f4131434236765e3d495f302f387c6a7362396d3c"
    "2e545661636075592a4d4b27587e78446c7d52456f6b4e3a233f47226940"
)


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


def _crazy(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(10):
        data_trit = data % 3
        accumulator_trit = accumulator % 3
        result += _CRAZY_TRIT[data_trit][accumulator_trit] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


def _rotate(value: int) -> int:
    return value // 3 + value % 3 * 19_683


def _initial_memory_value(words: tuple[int, ...], address: int) -> int:
    if address < len(words):
        return words[address]
    memory = list(words)
    while len(memory) <= address:
        memory.append(_crazy(memory[-2], memory[-1]))
    return memory[address]


def _pointer_successor(pointer: int) -> int:
    return (pointer + 1) % _PROFILE_MEMORY_WORDS


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


def _rejected(
    decoded: int,
    data_write_address: int | None,
    data_write_value: int | None,
    encryption_address: int,
    encryption_input: int,
    aliases_encryption: bool,
    input_dependent: bool,
) -> EntryTransition:
    return EntryTransition(
        status=_ENTRY_INVALID_ENCRYPTION,
        fetched_address=0,
        decoded_byte=decoded,
        data_address=0,
        code_data_alias=True,
        planned_data_write_address=data_write_address,
        planned_data_write_value=data_write_value,
        encryption_address=encryption_address,
        encryption_input=encryption_input,
        encryption_output=None,
        data_write_aliases_encryption=aliases_encryption,
        input_dependent_accumulator=input_dependent,
        result_accumulator=0,
        result_code_pointer=0,
        result_data_pointer=0,
        next_fetch_address=None,
        pointer_wraps=False,
    )


def analyze_entry_transition(
    words: tuple[int, ...], decoded: int
) -> EntryTransition:
    """Resolve one exact entry transition without executing a guest loop.

    Returns:
        Entry-state transfer or atomic invalid-self-encryption rejection.

    """
    data_value = words[0]
    planned_code = 0
    planned_data = 0
    planned_accumulator: int | None = 0
    data_write_address: int | None = None
    data_write_value: int | None = None
    input_dependent = False

    if decoded == ord("v"):
        return _halted(decoded)
    if decoded == ord("j"):
        planned_data = data_value
    elif decoded == ord("i"):
        planned_code = data_value
    elif decoded == ord("*"):
        planned_accumulator = _rotate(data_value)
        data_write_address = 0
        data_write_value = planned_accumulator
    elif decoded == ord("p"):
        planned_accumulator = _crazy(data_value, 0)
        data_write_address = 0
        data_write_value = planned_accumulator
    elif decoded == ord("/"):
        planned_accumulator = None
        input_dependent = True

    encryption_address = planned_code
    aliases_encryption = data_write_address == encryption_address
    encryption_input = (
        data_write_value
        if aliases_encryption and data_write_value is not None
        else _initial_memory_value(words, encryption_address)
    )
    if not _GRAPHICAL_START <= encryption_input <= _GRAPHICAL_END:
        return _rejected(
            decoded,
            data_write_address,
            data_write_value,
            encryption_address,
            encryption_input,
            aliases_encryption,
            input_dependent,
        )

    result_code = _pointer_successor(planned_code)
    result_data = _pointer_successor(planned_data)
    return EntryTransition(
        status=_ENTRY_CONTINUED,
        fetched_address=0,
        decoded_byte=decoded,
        data_address=0,
        code_data_alias=True,
        planned_data_write_address=data_write_address,
        planned_data_write_value=data_write_value,
        encryption_address=encryption_address,
        encryption_input=encryption_input,
        encryption_output=_XLAT2[encryption_input - _GRAPHICAL_START],
        data_write_aliases_encryption=aliases_encryption,
        input_dependent_accumulator=input_dependent,
        result_accumulator=planned_accumulator,
        result_code_pointer=result_code,
        result_data_pointer=result_data,
        next_fetch_address=result_code,
        pointer_wraps=(
            planned_code == _PROFILE_MEMORY_WORDS - 1
            or planned_data == _PROFILE_MEMORY_WORDS - 1
        ),
    )
