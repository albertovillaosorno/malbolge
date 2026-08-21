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
#   - Independent bounded-prefix differential evidence for the static
#     analyzer.
# - Must-Not:
#   - Import verifier transition helpers or execute an unbounded guest loop.
# - Allows:
#   - Inputs: fixed admitted bounded sources and the analyzer CLI JSON report.
#   - Outputs: exact agreement with a test-local historical bounded-prefix
#     model.
#   - Side effects: test-local source files and bounded subprocess execution.
# - Split-When:
#   - Fifth-step differential reachability needs a separately bounded model.
# - Merge-When:
#   - Another verifier differential owns the same bounded public surface.
# - Summary:
#   - Compares schema-v7 bounded transitions to independent 1998 semantics.
# - Description:
#   - Covers every admitted second opcode after exact output or input entry.
# - Usage:
#   - Collected by repository pytest validation.
# - Defaults:
#   - Unknown input followed by crazy remains explicitly unresolved.
#

"""Independent bounded-prefix differential tests for emitted Malbolge."""

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
_FIRST_INSTRUCTIONS: Final = (ord("<"), ord("/"), ord("j"))
_SECOND_INSTRUCTIONS: Final = tuple(b"ji*p</vo")
_STATUS_CONTINUED: Final = "continued"
_STATUS_HALTED: Final = "halted"
_STATUS_REJECTED: Final = "rejected-invalid-self-encryption"
_STATUS_UNRESOLVED: Final = "unresolved-input-dependent-accumulator"
_STATUS_STUCK: Final = "stuck-non-graphical-fetch"
_FOURTH_SOURCE: Final = (40, 39, 38)
_FOURTH_FETCH_ADDRESS: Final = 3
_FOURTH_SECOND_DATA_ADDRESS: Final = 41
_FOURTH_THIRD_DATA_ADDRESS: Final = 29_488
_FOURTH_FINAL_DATA_ADDRESS: Final = 39


@dataclass(frozen=True, slots=True)
class _ReferenceMemory:
    source: tuple[int, ...]
    writes: tuple[tuple[int, int], ...] = ()

    def read(self, address: int) -> int:
        """Read one value after bounded reference-model writes.

        Returns:
            Latest written value or exact initial recurrence memory.

        """
        for write_address, value in reversed(self.writes):
            if write_address == address:
                return value
        return _initial_memory(self.source, address)

    def commit(
        self, address: int | None, value: int | None
    ) -> _ReferenceMemory:
        """Append one known write to immutable reference memory.

        Returns:
            Updated immutable memory state, or self for an absent write.

        """
        if address is None or value is None:
            return self
        return _ReferenceMemory(self.source, (*self.writes, (address, value)))


@dataclass(frozen=True, slots=True)
class _PlanContext:
    code_pointer: int
    data: int
    data_pointer: int
    accumulator: int | None


@dataclass(frozen=True, slots=True)
class _ReferenceState:
    code_pointer: int
    data_pointer: int
    accumulator: int | None


@dataclass(frozen=True, slots=True)
class _ReferencePlan:
    accumulator: int | None
    code_pointer: int
    data_pointer: int
    write_address: int | None = None
    write_value: int | None = None
    input_dependent: bool = False
    halted: bool = False
    unresolved: bool = False


@dataclass(frozen=True, slots=True)
class _ExpectedSecond:
    status: str
    decoded: int
    write_address: int | None
    write_value: int | None
    encryption_address: int | None
    encryption_input: int | None
    encryption_output: int | None
    aliases_encryption: bool
    input_dependent: bool
    accumulator: int | None
    code_pointer: int | None
    data_pointer: int | None
    next_fetch: int | None


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


def _base_plan(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        context.code_pointer,
        context.data_pointer,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_data(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        context.code_pointer,
        context.data,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_code(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        context.data,
        context.data_pointer,
        input_dependent=context.accumulator is None,
    )


def _plan_rotate(context: _PlanContext) -> _ReferencePlan:
    value = _rotate(context.data)
    return _ReferencePlan(
        value,
        context.code_pointer,
        context.data_pointer,
        context.data_pointer,
        value,
    )


def _plan_crazy(context: _PlanContext) -> _ReferencePlan:
    accumulator = context.accumulator
    if accumulator is None:
        return _ReferencePlan(
            None,
            context.code_pointer,
            context.data_pointer,
            input_dependent=True,
            unresolved=True,
        )
    value = _crazy(context.data, accumulator)
    return _ReferencePlan(
        value,
        context.code_pointer,
        context.data_pointer,
        context.data_pointer,
        value,
    )


def _plan_input(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        None,
        context.code_pointer,
        context.data_pointer,
        input_dependent=True,
    )


def _plan_halt(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        context.code_pointer,
        context.data_pointer,
        input_dependent=context.accumulator is None,
        halted=True,
    )


_PLANNERS: Final[dict[int, Callable[[_PlanContext], _ReferencePlan]]] = {
    ord("j"): _plan_jump_data,
    ord("i"): _plan_jump_code,
    ord("*"): _plan_rotate,
    ord("p"): _plan_crazy,
    ord("/"): _plan_input,
    ord("v"): _plan_halt,
}


def _plan_transition(
    decoded: int,
    data: int,
    state: _ReferenceState,
) -> _ReferencePlan:
    context = _PlanContext(
        state.code_pointer, data, state.data_pointer, state.accumulator
    )
    planner = _PLANNERS.get(decoded, _base_plan)
    return planner(context)


def _terminal_expected(decoded: int, plan: _ReferencePlan) -> _ExpectedSecond:
    status = _STATUS_HALTED if plan.halted else _STATUS_UNRESOLVED
    return _ExpectedSecond(
        status=status,
        decoded=decoded,
        write_address=None,
        write_value=None,
        encryption_address=None,
        encryption_input=None,
        encryption_output=None,
        aliases_encryption=False,
        input_dependent=plan.input_dependent,
        accumulator=plan.accumulator,
        code_pointer=None if plan.unresolved else plan.code_pointer,
        data_pointer=None if plan.unresolved else plan.data_pointer,
        next_fetch=None,
    )


def _resolved_expected(
    memory: _ReferenceMemory,
    decoded: int,
    plan: _ReferencePlan,
    *,
    initial_state: _ReferenceState,
) -> _ExpectedSecond:
    aliases = plan.write_address == plan.code_pointer
    if aliases and plan.write_value is not None:
        encryption_input = plan.write_value
    else:
        encryption_input = memory.read(plan.code_pointer)
    if not _GRAPHICAL_START <= encryption_input <= _GRAPHICAL_END:
        return _ExpectedSecond(
            status=_STATUS_REJECTED,
            decoded=decoded,
            write_address=plan.write_address,
            write_value=plan.write_value,
            encryption_address=plan.code_pointer,
            encryption_input=encryption_input,
            encryption_output=None,
            aliases_encryption=aliases,
            input_dependent=plan.input_dependent,
            accumulator=plan.accumulator,
            code_pointer=initial_state.code_pointer,
            data_pointer=initial_state.data_pointer,
            next_fetch=None,
        )
    encryption_output = _XLAT2[encryption_input - _GRAPHICAL_START]
    code_pointer = (plan.code_pointer + 1) % _MEMORY_WORDS
    data_pointer = (plan.data_pointer + 1) % _MEMORY_WORDS
    return _ExpectedSecond(
        status=_STATUS_CONTINUED,
        decoded=decoded,
        write_address=plan.write_address,
        write_value=plan.write_value,
        encryption_address=plan.code_pointer,
        encryption_input=encryption_input,
        encryption_output=encryption_output,
        aliases_encryption=aliases,
        input_dependent=plan.input_dependent,
        accumulator=plan.accumulator,
        code_pointer=code_pointer,
        data_pointer=data_pointer,
        next_fetch=code_pointer,
    )


def _expected_second(
    first: int,
    second: int,
    source: tuple[int, ...],
) -> _ExpectedSecond:
    accumulator = None if first == ord("/") else 0
    data_pointer = source[0] + 1 if first == ord("j") else 1
    data = _initial_memory(source, data_pointer)
    initial_state = _ReferenceState(1, data_pointer, accumulator)
    plan = _plan_transition(second, data, initial_state)
    if plan.halted or plan.unresolved:
        return _terminal_expected(second, plan)
    entry_encryption = _XLAT2[source[0] - _GRAPHICAL_START]
    memory = _ReferenceMemory(source).commit(0, entry_encryption)
    return _resolved_expected(
        memory,
        second,
        plan,
        initial_state=initial_state,
    )


def _memory_after_second(
    source: tuple[int, ...],
    expected: _ExpectedSecond,
) -> _ReferenceMemory:
    entry_encryption = _XLAT2[source[0] - _GRAPHICAL_START]
    memory = _ReferenceMemory(source).commit(0, entry_encryption)
    memory = memory.commit(expected.write_address, expected.write_value)
    return memory.commit(
        expected.encryption_address,
        expected.encryption_output,
    )


def _decode_memory_value(value: int, address: int) -> int | None:
    if not _GRAPHICAL_START <= value <= _GRAPHICAL_END:
        return None
    return _XLAT1[(value - _GRAPHICAL_START + address) % len(_XLAT1)]


def _expected_followup(
    memory: _ReferenceMemory,
    state: _ReferenceState,
) -> tuple[_ExpectedSecond, int, int]:
    fetched = memory.read(state.code_pointer)
    decoded = _decode_memory_value(fetched, state.code_pointer)
    if decoded is None:
        message = "graphical followup fixture decoded non-graphically"
        raise AssertionError(message)
    data = memory.read(state.data_pointer)
    plan = _plan_transition(decoded, data, state)
    if plan.halted or plan.unresolved:
        return _terminal_expected(decoded, plan), fetched, data
    expected = _resolved_expected(
        memory,
        decoded,
        plan,
        initial_state=state,
    )
    return expected, fetched, data


def _assert_stuck_addresses(
    document: dict[str, object],
    expected: _ExpectedSecond,
    data_pointer: int,
) -> None:
    assert document["fetched_address"] == expected.next_fetch
    assert document["data_address"] == data_pointer
    assert document["code_data_alias"] == (expected.next_fetch == data_pointer)
    assert document["result_code_pointer"] == expected.next_fetch
    assert document["result_data_pointer"] == data_pointer
    assert document["next_fetch_address"] == expected.next_fetch


def _assert_stuck_effects(document: dict[str, object]) -> None:
    assert document["decoded_byte"] is None
    assert document["data_value"] is None
    assert document["planned_data_write_address"] is None
    assert document["planned_data_write_value"] is None
    assert document["encryption_address"] is None
    assert document["encryption_input"] is None
    assert document["encryption_output"] is None
    assert document["provable_cycle"] is True


def _assert_third_prefix(
    observed: object,
    source: tuple[int, int],
    expected: _ExpectedSecond,
) -> None:
    if expected.status != _STATUS_CONTINUED or expected.next_fetch is None:
        assert observed is None
        return
    document = cast("dict[str, object]", observed)
    data_pointer = expected.data_pointer
    assert data_pointer is not None
    memory = _memory_after_second(source, expected)
    fetched = memory.read(expected.next_fetch)
    assert not _GRAPHICAL_START <= fetched <= _GRAPHICAL_END
    assert document["status"] == _STATUS_STUCK
    assert document["fetched_value"] == fetched
    _assert_stuck_addresses(document, expected, data_pointer)
    _assert_stuck_effects(document)
    assert document["input_dependent_accumulator"] == (
        expected.accumulator is None
    )
    assert document["result_accumulator"] == expected.accumulator


def _expected_cli_code(expected: _ExpectedSecond) -> int:
    if expected.status == _STATUS_HALTED:
        return 0
    return 1


def _report(
    tmp_path: Path,
    source: bytes,
    *,
    transition_limit: int | None = None,
) -> tuple[int, dict[str, object]]:
    path = tmp_path / "prefix.malbolge"
    _ = path.write_bytes(source)
    command = [sys.executable, str(_ANALYZER)]
    if transition_limit is not None:
        command.extend(("--transition-limit", str(transition_limit)))
    command.append(str(path))
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
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


def _assert_second(
    observed: dict[str, object],
    expected: _ExpectedSecond,
) -> None:
    assert observed["status"] == expected.status
    assert observed["decoded_byte"] == expected.decoded
    assert observed["planned_data_write_address"] == expected.write_address
    assert observed["planned_data_write_value"] == expected.write_value
    assert observed["encryption_address"] == expected.encryption_address
    assert observed["encryption_input"] == expected.encryption_input
    assert observed["encryption_output"] == expected.encryption_output
    observed_alias = observed["data_write_aliases_encryption"]
    assert observed_alias == expected.aliases_encryption
    assert observed["input_dependent_accumulator"] == expected.input_dependent
    assert observed["result_accumulator"] == expected.accumulator
    assert observed["result_code_pointer"] == expected.code_pointer
    assert observed["result_data_pointer"] == expected.data_pointer
    assert observed["next_fetch_address"] == expected.next_fetch


_CASES: Final = tuple(
    (first, second)
    for first in _FIRST_INSTRUCTIONS
    for second in _SECOND_INSTRUCTIONS
)


@pytest.mark.parametrize(("first", "second"), _CASES)
def test_two_transition_cli_matches_independent_historical_model(
    tmp_path: Path,
    first: int,
    second: int,
) -> None:
    """Compare every second opcode after exact output/input entry semantics."""
    source_tuple = (_source_byte(first, 0), _source_byte(second, 1))
    source = bytes(source_tuple)
    expected = _expected_second(first, second, source_tuple)
    returncode, document = _report(tmp_path, source)
    observed = cast("dict[str, object]", document["second_transition"])
    _assert_second(observed, expected)
    _assert_third_prefix(document["third_transition"], source_tuple, expected)
    assert document["fourth_transition"] is None
    assert document["fifth_transition"] is None
    assert returncode == _expected_cli_code(expected)


_THIRD_REACHABLE_SECOND_INSTRUCTIONS: Final = tuple(b"j</o")
_THIRD_CASES: Final = tuple(
    (second, third)
    for second in _THIRD_REACHABLE_SECOND_INSTRUCTIONS
    for third in _SECOND_INSTRUCTIONS
)


@pytest.mark.parametrize(("second", "third"), _THIRD_CASES)
def test_three_transition_cli_matches_independent_historical_model(
    tmp_path: Path,
    second: int,
    third: int,
) -> None:
    """Compare every graphical third opcode across distinct carried states."""
    source_tuple = (
        _source_byte(ord("<"), 0),
        _source_byte(second, 1),
        _source_byte(third, 2),
    )
    first_expected = _expected_second(ord("<"), second, source_tuple)
    assert first_expected.status == _STATUS_CONTINUED
    assert first_expected.code_pointer is not None
    assert first_expected.data_pointer is not None
    expected, fetched, data = _expected_followup(
        _memory_after_second(source_tuple, first_expected),
        _ReferenceState(
            first_expected.code_pointer,
            first_expected.data_pointer,
            first_expected.accumulator,
        ),
    )
    assert expected.decoded == third
    returncode, document = _report(
        tmp_path, bytes(source_tuple), transition_limit=3
    )
    _assert_second(
        cast("dict[str, object]", document["second_transition"]), first_expected
    )
    observed = cast("dict[str, object]", document["third_transition"])
    assert observed["fetched_address"] == first_expected.code_pointer
    assert observed["fetched_value"] == fetched
    assert observed["data_address"] == first_expected.data_pointer
    assert observed["data_value"] == data
    assert observed["code_data_alias"] == (
        first_expected.code_pointer == first_expected.data_pointer
    )
    _assert_second(observed, expected)
    expected_success = expected.status in {_STATUS_CONTINUED, _STATUS_HALTED}
    assert returncode == (0 if expected_success else 1)


def _assert_fourth_reference_transition(
    document: dict[str, object],
    *,
    expected_fetch: int,
) -> None:
    assert document["status"] == _STATUS_STUCK
    assert document["fetched_address"] == _FOURTH_FETCH_ADDRESS
    assert document["fetched_value"] == expected_fetch
    assert document["decoded_byte"] is None
    assert document["data_address"] == _FOURTH_FINAL_DATA_ADDRESS
    assert document["data_value"] is None
    assert document["result_code_pointer"] == _FOURTH_FETCH_ADDRESS
    assert document["result_data_pointer"] == _FOURTH_FINAL_DATA_ADDRESS
    assert document["next_fetch_address"] == _FOURTH_FETCH_ADDRESS
    assert document["provable_cycle"] is True


def test_fourth_transition_matches_independent_recurrence_model(
    tmp_path: Path,
) -> None:
    """Compare one recurrence-backed fourth step to private 1998 semantics."""
    source = bytes(_FOURTH_SOURCE)
    returncode, report = _report(tmp_path, source)
    entry = cast("dict[str, object]", report["entry_transition"])
    second = cast("dict[str, object]", report["second_transition"])
    third = cast("dict[str, object]", report["third_transition"])
    fourth = cast("dict[str, object]", report["fourth_transition"])
    assert entry["decoded_byte"] == ord("j")
    assert entry["result_data_pointer"] == _FOURTH_SECOND_DATA_ADDRESS
    assert second["data_value"] == _initial_memory(
        _FOURTH_SOURCE, _FOURTH_SECOND_DATA_ADDRESS
    )
    assert second["encryption_output"] == _XLAT2[
        _FOURTH_SOURCE[1] - _GRAPHICAL_START
    ]
    assert third["data_address"] == _FOURTH_THIRD_DATA_ADDRESS
    assert third["data_value"] == _initial_memory(
        _FOURTH_SOURCE, _FOURTH_THIRD_DATA_ADDRESS
    )
    assert third["encryption_output"] == _XLAT2[
        _FOURTH_SOURCE[2] - _GRAPHICAL_START
    ]
    expected_fetch = _initial_memory(_FOURTH_SOURCE, _FOURTH_FETCH_ADDRESS)
    _assert_fourth_reference_transition(fourth, expected_fetch=expected_fetch)
    assert report["fifth_transition"] is None
    assert returncode == 1
