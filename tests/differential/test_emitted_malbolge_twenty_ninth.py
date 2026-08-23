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
#   - Independent twenty-ninth-transition differential evidence for the static
#     analyzer.
# - Must-Not:
#   - Import verifier helpers, import another differential semantic model, or
#     execute an unbounded guest loop.
# - Allows:
#   - Inputs: fixed admitted twenty-nine-cell sources and analyzer CLI JSON
#     reports.
#   - Outputs: exact agreement with a self-contained historical
#     twenty-nine-step model.
#   - Side effects: test-local source files and bounded subprocess execution.
# - Split-When:
#   - Thirtieth-step differential reachability needs a separately bounded
#     model.
# - Merge-When:
#   - Another independent verifier differential owns this exact
#     twenty-ninth-step public surface.
# - Summary:
#   - Compares the twenty-ninth bounded CLI transition to independent 1998
#     semantics.
# - Description:
#   - Covers every twenty-ninth opcode after `/oo<jjjjjjj*jjjjjjjjjjjjjjj`,
#     `j*pj*ppppj/*jjjjjjjjjjjjjjj`, and `o<o<<<<<</o<*oooooooooooooo`
#     histories, including a final C=D alias row and two aliased
#     data-write/self-encryption cases.
# - Usage:
#   - Collected by repository pytest validation.
# - Defaults:
#   - Unknown input followed by crazy remains explicitly unresolved.
#

"""Twenty-ninth-transition differential tests for emitted Malbolge."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Final
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

_ROOT = Path(__file__).resolve().parents[2]
_ANALYZER = _ROOT / "verifier" / "emitted_malbolge.py"
_GRAPHICAL_START: Final = 33
_GRAPHICAL_END: Final = 126
_MEMORY_WORDS: Final = 59_049
_XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
_XLAT2_HEX_PARTS: Final = (
    "357a5d2667717479667224287765347b575029482d5a6e2c5b255c33644c2b51",
    "3b3e5521704a53373246684f4131434236765e3d495f302f387c6a7362396d3c",
    "2e545661636075592a4d4b27587e78446c7d52456f6b4e3a233f47226940",
)
_XLAT2: Final = bytes.fromhex("".join(_XLAT2_HEX_PARTS))
_CRAZY_TRIT: Final = ((1, 0, 0), (1, 0, 2), (2, 2, 1))
_OPCODES: Final = tuple(b"ji*p</vo")
_STATUS_CONTINUED: Final = "continued"
_STATUS_HALTED: Final = "halted"
_STATUS_REJECTED: Final = "rejected-invalid-self-encryption"
_STATUS_UNRESOLVED: Final = "unresolved-input-dependent-accumulator"
_TRANSITION_LIMIT: Final = 29
_ALIAS_HISTORY: Final = tuple(b"o<o<<<<<</o<*oooooooooooooo")
_ALIAS_WRITING_OPCODES: Final = frozenset((ord("*"), ord("p")))
_HISTORIES: Final = (
    tuple(b"/oo<jjjjjjj*jjjjjjjjjjjjjjj"),
    tuple(b"j*pj*ppppj/*jjjjjjjjjjjjjjj"),
    _ALIAS_HISTORY,
)
_CASES: Final = tuple(
    (history, twenty_ninth)
    for history in _HISTORIES
    for twenty_ninth in _OPCODES
)


@dataclass(frozen=True, slots=True)
class _Memory:
    source: tuple[int, ...]
    writes: tuple[tuple[int, int], ...] = ()

    def read(self, address: int) -> int:
        for write_address, value in reversed(self.writes):
            if write_address == address:
                return value
        return _initial_memory(self.source, address)

    def commit(self, address: int | None, value: int | None) -> _Memory:
        if address is None or value is None:
            return self
        return _Memory(self.source, (*self.writes, (address, value)))


@dataclass(frozen=True, slots=True)
class _State:
    code_pointer: int
    data_pointer: int
    accumulator: int | None


@dataclass(frozen=True, slots=True)
class _Plan:
    accumulator: int | None
    code_pointer: int
    data_pointer: int
    write_address: int | None = None
    write_value: int | None = None
    input_dependent: bool = False
    halted: bool = False
    unresolved: bool = False


@dataclass(frozen=True, slots=True)
class _Transition:
    status: str
    decoded: int
    fetched_address: int
    fetched_value: int
    data_address: int
    data_value: int
    code_data_alias: bool
    write_address: int | None
    write_value: int | None
    encryption_address: int | None
    encryption_input: int | None
    encryption_output: int | None
    write_aliases_encryption: bool
    input_dependent: bool
    accumulator: int | None
    code_pointer: int | None
    data_pointer: int | None
    next_fetch: int | None
    pointer_wraps: bool = False
    provable_cycle: bool = False


@dataclass(frozen=True, slots=True)
class _Trace:
    transitions: tuple[_Transition, ...]


@dataclass(frozen=True, slots=True)
class _StepContext:
    state: _State
    decoded: int
    fetched: int
    data: int
    plan: _Plan


def _source_byte(decoded: int, position: int) -> int:
    index = _XLAT1.index(decoded)
    return ((index - position) % len(_XLAT1)) + _GRAPHICAL_START


def _crazy(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(10):
        result += _CRAZY_TRIT[data % 3][accumulator % 3] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


def _rotate(value: int) -> int:
    return value // 3 + value % 3 * 19_683


def _initial_memory(source: tuple[int, ...], address: int) -> int:
    memory = list(source)
    while len(memory) <= address:
        memory.append(_crazy(memory[-2], memory[-1]))
    return memory[address]


def _decode(value: int, code_pointer: int) -> int:
    if not _GRAPHICAL_START <= value <= _GRAPHICAL_END:
        message = (
            "selected twenty-ninth-step fixture reached a non-graphical fetch"
        )
        raise AssertionError(message)
    return _XLAT1[(value - _GRAPHICAL_START + code_pointer) % len(_XLAT1)]


def _base_plan(data: int, state: _State) -> _Plan:
    del data
    return _Plan(
        state.accumulator,
        state.code_pointer,
        state.data_pointer,
        input_dependent=state.accumulator is None,
    )


def _plan_jump_data(data: int, state: _State) -> _Plan:
    return _Plan(
        state.accumulator,
        state.code_pointer,
        data,
        input_dependent=state.accumulator is None,
    )


def _plan_jump_code(data: int, state: _State) -> _Plan:
    return _Plan(
        state.accumulator,
        data,
        state.data_pointer,
        input_dependent=state.accumulator is None,
    )


def _plan_rotate(data: int, state: _State) -> _Plan:
    value = _rotate(data)
    return _Plan(
        value,
        state.code_pointer,
        state.data_pointer,
        write_address=state.data_pointer,
        write_value=value,
    )


def _plan_crazy(data: int, state: _State) -> _Plan:
    accumulator = state.accumulator
    if accumulator is None:
        return _Plan(
            None,
            state.code_pointer,
            state.data_pointer,
            input_dependent=True,
            unresolved=True,
        )
    value = _crazy(data, accumulator)
    return _Plan(
        value,
        state.code_pointer,
        state.data_pointer,
        write_address=state.data_pointer,
        write_value=value,
    )


def _plan_input(data: int, state: _State) -> _Plan:
    del data
    return _Plan(
        None,
        state.code_pointer,
        state.data_pointer,
        input_dependent=True,
    )


def _plan_halt(data: int, state: _State) -> _Plan:
    del data
    return _Plan(
        state.accumulator,
        state.code_pointer,
        state.data_pointer,
        input_dependent=state.accumulator is None,
        halted=True,
    )


_PLANNERS: Final[dict[int, Callable[[int, _State], _Plan]]] = {
    ord("j"): _plan_jump_data,
    ord("i"): _plan_jump_code,
    ord("*"): _plan_rotate,
    ord("p"): _plan_crazy,
    ord("/"): _plan_input,
    ord("v"): _plan_halt,
}


def _plan(decoded: int, data: int, state: _State) -> _Plan:
    return _PLANNERS.get(decoded, _base_plan)(data, state)


def _terminal_transition(context: _StepContext) -> _Transition:
    plan = context.plan
    state = context.state
    status = _STATUS_HALTED if plan.halted else _STATUS_UNRESOLVED
    return _Transition(
        status=status,
        decoded=context.decoded,
        fetched_address=state.code_pointer,
        fetched_value=context.fetched,
        data_address=state.data_pointer,
        data_value=context.data,
        code_data_alias=state.code_pointer == state.data_pointer,
        write_address=None,
        write_value=None,
        encryption_address=None,
        encryption_input=None,
        encryption_output=None,
        write_aliases_encryption=False,
        input_dependent=plan.input_dependent,
        accumulator=plan.accumulator,
        code_pointer=None if plan.unresolved else plan.code_pointer,
        data_pointer=None if plan.unresolved else plan.data_pointer,
        next_fetch=None,
    )


def _rejected_transition(
    context: _StepContext,
    *,
    encryption_input: int,
    aliases: bool,
) -> _Transition:
    state = context.state
    plan = context.plan
    return _Transition(
        status=_STATUS_REJECTED,
        decoded=context.decoded,
        fetched_address=state.code_pointer,
        fetched_value=context.fetched,
        data_address=state.data_pointer,
        data_value=context.data,
        code_data_alias=state.code_pointer == state.data_pointer,
        write_address=plan.write_address,
        write_value=plan.write_value,
        encryption_address=plan.code_pointer,
        encryption_input=encryption_input,
        encryption_output=None,
        write_aliases_encryption=aliases,
        input_dependent=plan.input_dependent,
        accumulator=plan.accumulator,
        code_pointer=state.code_pointer,
        data_pointer=state.data_pointer,
        next_fetch=None,
    )


def _resolved_transition(
    memory: _Memory,
    context: _StepContext,
) -> tuple[_Transition, _Memory, _State | None]:
    plan = context.plan
    state = context.state
    aliases = (
        plan.write_address is not None
        and plan.write_address == plan.code_pointer
    )
    encryption_input = (
        plan.write_value
        if aliases and plan.write_value is not None
        else memory.read(plan.code_pointer)
    )
    if not _GRAPHICAL_START <= encryption_input <= _GRAPHICAL_END:
        return (
            _rejected_transition(
                context, encryption_input=encryption_input, aliases=aliases
            ),
            memory,
            None,
        )
    encryption_output = _XLAT2[encryption_input - _GRAPHICAL_START]
    result_code = (plan.code_pointer + 1) % _MEMORY_WORDS
    result_data = (plan.data_pointer + 1) % _MEMORY_WORDS
    transition = _Transition(
        status=_STATUS_CONTINUED,
        decoded=context.decoded,
        fetched_address=state.code_pointer,
        fetched_value=context.fetched,
        data_address=state.data_pointer,
        data_value=context.data,
        code_data_alias=state.code_pointer == state.data_pointer,
        write_address=plan.write_address,
        write_value=plan.write_value,
        encryption_address=plan.code_pointer,
        encryption_input=encryption_input,
        encryption_output=encryption_output,
        write_aliases_encryption=aliases,
        input_dependent=plan.input_dependent,
        accumulator=plan.accumulator,
        code_pointer=result_code,
        data_pointer=result_data,
        next_fetch=result_code,
        pointer_wraps=(
            plan.code_pointer == _MEMORY_WORDS - 1
            or plan.data_pointer == _MEMORY_WORDS - 1
        ),
    )
    updated = memory.commit(plan.write_address, plan.write_value).commit(
        plan.code_pointer, encryption_output
    )
    successor = _State(result_code, result_data, plan.accumulator)
    return transition, updated, successor


def _step(
    memory: _Memory,
    state: _State,
) -> tuple[_Transition, _Memory, _State | None]:
    fetched = memory.read(state.code_pointer)
    decoded = _decode(fetched, state.code_pointer)
    data = memory.read(state.data_pointer)
    plan = _plan(decoded, data, state)
    context = _StepContext(state, decoded, fetched, data, plan)
    if plan.halted or plan.unresolved:
        return _terminal_transition(context), memory, None
    return _resolved_transition(memory, context)


def _expected_trace(
    source: tuple[int, ...], opcodes: tuple[int, ...]
) -> _Trace:
    memory = _Memory(source)
    state: _State | None = _State(0, 0, 0)
    transitions: list[_Transition] = []
    for index, opcode in enumerate(opcodes):
        assert state is not None
        transition, memory, state = _step(memory, state)
        assert transition.decoded == opcode
        transitions.append(transition)
        if index < _TRANSITION_LIMIT - 1:
            assert transition.status == _STATUS_CONTINUED
            assert state is not None
    return _Trace(tuple(transitions))


def _report(tmp_path: Path, source: bytes) -> tuple[int, dict[str, object]]:
    path = tmp_path / "twenty-ninth.malbolge"
    _ = path.write_bytes(source)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(_ANALYZER),
            "--transition-limit",
            str(_TRANSITION_LIMIT),
            str(path),
        ],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    return completed.returncode, document


def _assert_entry(observed: dict[str, object], expected: _Transition) -> None:
    assert observed["status"] == expected.status
    assert observed["decoded_byte"] == expected.decoded
    assert observed["fetched_address"] == expected.fetched_address
    assert observed["data_address"] == expected.data_address
    assert observed["code_data_alias"] == expected.code_data_alias
    assert observed["planned_data_write_address"] == expected.write_address
    assert observed["planned_data_write_value"] == expected.write_value
    assert observed["encryption_address"] == expected.encryption_address
    assert observed["encryption_input"] == expected.encryption_input
    assert observed["encryption_output"] == expected.encryption_output
    assert (
        observed["data_write_aliases_encryption"]
        == expected.write_aliases_encryption
    )
    assert observed["input_dependent_accumulator"] == expected.input_dependent
    assert observed["result_accumulator"] == expected.accumulator
    assert observed["result_code_pointer"] == expected.code_pointer
    assert observed["result_data_pointer"] == expected.data_pointer
    assert observed["next_fetch_address"] == expected.next_fetch
    assert observed["pointer_wraps"] == expected.pointer_wraps


def _assert_followup(
    observed: dict[str, object], expected: _Transition
) -> None:
    _assert_entry(observed, expected)
    assert observed["fetched_value"] == expected.fetched_value
    assert observed["data_value"] == expected.data_value
    assert observed["provable_cycle"] == expected.provable_cycle


@pytest.mark.parametrize(("history", "twenty_ninth"), _CASES)
def test_twenty_ninth_transition_cli_matches_independent_historical_model(
    tmp_path: Path,
    history: tuple[
        int, int, int, int, int, int, int, int, int, int, int, int, int, int,
        int, int, int, int, int, int, int, int, int, int, int, int, int,
    ],
    twenty_ninth: int,
) -> None:
    """Compare every twenty-ninth opcode across three carried histories."""
    opcodes = (ord("<"), *history, twenty_ninth)
    source_tuple = tuple(
        _source_byte(opcode, position)
        for position, opcode in enumerate(opcodes)
    )
    expected = _expected_trace(source_tuple, opcodes)
    final_expected = expected.transitions[-1]
    if history == _ALIAS_HISTORY:
        assert final_expected.code_data_alias
        assert final_expected.write_aliases_encryption == (
            twenty_ninth in _ALIAS_WRITING_OPCODES
        )
    returncode, document = _report(tmp_path, bytes(source_tuple))
    _assert_entry(
        cast("dict[str, object]", document["entry_transition"]),
        expected.transitions[0],
    )
    assert document["bounded_transition_limit"] == _TRANSITION_LIMIT
    continuations = cast(
        "list[dict[str, object]]", document["bounded_continuations"]
    )
    assert len(continuations) == _TRANSITION_LIMIT - 1
    for observed, transition in zip(
        continuations, expected.transitions[1:], strict=True
    ):
        _assert_followup(observed, transition)
    for index, key in enumerate(
        (
            "second_transition",
            "third_transition",
            "fourth_transition",
            "fifth_transition",
        )
    ):
        assert document[key] == continuations[index]
    for key in (
        "sixth_transition",
        "seventh_transition",
        "eighth_transition",
        "ninth_transition",
        "tenth_transition",
        "eleventh_transition",
        "twelfth_transition",
        "thirteenth_transition",
        "fourteenth_transition",
        "fifteenth_transition",
        "sixteenth_transition",
        "seventeenth_transition",
        "eighteenth_transition",
        "nineteenth_transition",
        "twentieth_transition",
        "twenty_first_transition",
        "twenty_second_transition",
        "twenty_third_transition",
        "twenty_fourth_transition",
        "twenty_fifth_transition",
        "twenty_sixth_transition",
        "twenty_seventh_transition",
        "twenty_eighth_transition",
        "twenty_ninth_transition",
    ):
        assert key not in document
    final_status = expected.transitions[-1].status
    expected_success = final_status in {_STATUS_CONTINUED, _STATUS_HALTED}
    assert returncode == (0 if expected_success else 1)
