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
#   - Independent two-transition differential evidence for the static analyzer.
# - Must-Not:
#   - Import verifier transition helpers or execute an unbounded guest loop.
# - Allows:
#   - Inputs: fixed admitted two-word sources and the analyzer CLI JSON report.
#   - Outputs: exact agreement with a test-local historical two-step model.
#   - Side effects: test-local source files and bounded subprocess execution.
# - Split-When:
#   - Third-step differential reachability needs a separately bounded model.
# - Merge-When:
#   - Another verifier differential owns the same two-step public surface.
# - Summary:
#   - Compares schema-v4 second transitions to independent 1998 semantics.
# - Description:
#   - Covers every admitted second opcode after exact output or input entry.
# - Usage:
#   - Collected by repository pytest validation.
# - Defaults:
#   - Unknown input followed by crazy remains explicitly unresolved.
#

"""Independent two-transition differential tests for emitted Malbolge."""

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
_FIRST_INSTRUCTIONS: Final = (ord("<"), ord("/"))
_SECOND_INSTRUCTIONS: Final = tuple(b"ji*p</vo")
_STATUS_CONTINUED: Final = "continued"
_STATUS_HALTED: Final = "halted"
_STATUS_REJECTED: Final = "rejected-invalid-self-encryption"
_STATUS_UNRESOLVED: Final = "unresolved-input-dependent-accumulator"
_ACCEPTED_STATUS: Final = frozenset({_STATUS_CONTINUED, _STATUS_HALTED})


@dataclass(frozen=True, slots=True)
class _PlanContext:
    data: int
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


def _initial_memory(source: tuple[int, int], address: int) -> int:
    memory = list(source)
    while len(memory) <= address:
        memory.append(_crazy(memory[-2], memory[-1]))
    return memory[address]


def _base_plan(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        1,
        1,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_data(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        1,
        context.data,
        input_dependent=context.accumulator is None,
    )


def _plan_jump_code(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        context.data,
        1,
        input_dependent=context.accumulator is None,
    )


def _plan_rotate(context: _PlanContext) -> _ReferencePlan:
    value = _rotate(context.data)
    return _ReferencePlan(value, 1, 1, 1, value)


def _plan_crazy(context: _PlanContext) -> _ReferencePlan:
    accumulator = context.accumulator
    if accumulator is None:
        return _ReferencePlan(
            None,
            1,
            1,
            input_dependent=True,
            unresolved=True,
        )
    value = _crazy(context.data, accumulator)
    return _ReferencePlan(value, 1, 1, 1, value)


def _plan_input(context: _PlanContext) -> _ReferencePlan:
    _ = context
    return _ReferencePlan(None, 1, 1, input_dependent=True)


def _plan_halt(context: _PlanContext) -> _ReferencePlan:
    return _ReferencePlan(
        context.accumulator,
        1,
        1,
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


def _plan_second(
    decoded: int,
    data: int,
    accumulator: int | None,
) -> _ReferencePlan:
    context = _PlanContext(data, accumulator)
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
        code_pointer=None if plan.unresolved else 1,
        data_pointer=None if plan.unresolved else 1,
        next_fetch=None,
    )


def _resolved_expected(
    source: tuple[int, int],
    decoded: int,
    plan: _ReferencePlan,
) -> _ExpectedSecond:
    aliases = plan.write_address == plan.code_pointer
    if aliases and plan.write_value is not None:
        encryption_input = plan.write_value
    else:
        encryption_input = _initial_memory(source, plan.code_pointer)
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
            code_pointer=1,
            data_pointer=1,
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
    source: tuple[int, int],
) -> _ExpectedSecond:
    accumulator = None if first == ord("/") else 0
    plan = _plan_second(second, source[1], accumulator)
    if plan.halted or plan.unresolved:
        return _terminal_expected(second, plan)
    return _resolved_expected(source, second, plan)


def _report(
    tmp_path: Path,
    source: bytes,
) -> tuple[int, dict[str, object]]:
    path = tmp_path / "prefix.malbolge"
    _ = path.write_bytes(source)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(path)],
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
    expected_code = 0 if expected.status in _ACCEPTED_STATUS else 1
    assert returncode == expected_code
