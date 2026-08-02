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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Resident CUDA classic sessions preserve segmented execution semantics.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Resident CUDA classic sessions preserve segmented execution semantics."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest import SkipTest

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_run import CudaClassicRunAdapter
from accelerator.cuda.classic_step import XLAT1
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError

NOOP_DECODED = ord("+")
SEGMENT_STEPS = 2
TOTAL_STEPS = 4
MAX_RUNS = 2
RUN_BUDGET_ERROR = "run budget exhausted"
MAX_RUNS_ERROR = "max runs must be positive"
OUTPUT_CAPACITY_ERROR = "output capacity exceeds unsigned 32-bit domain"
OUTPUT_BYTE = 65
OUTPUT_DECODED = ord("/")

if TYPE_CHECKING:
    from collections.abc import Callable


def _cuda() -> CudaClassicRunAdapter:
    try:
        return CudaClassicRunAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def test_resident_session_matches_one_equivalent_complete_run() -> None:
    """Two resident segments equal one ordinary run over the same four steps."""
    request = _request()
    with _cuda() as adapter:
        expected = adapter.evaluate((
            replace(request, step_budget=TOTAL_STEPS),
        ))[0]
        with adapter.open_session((request,), max_runs=MAX_RUNS) as session:
            session.advance()
            first = session.observe()[0]
            assert first.code_pointer == SEGMENT_STEPS
            assert first.steps == SEGMENT_STEPS
            assert first.status == RunStatus.BUDGET_EXHAUSTED
            session.advance()
            second = session.observe()[0]
            assert second.code_pointer == TOTAL_STEPS
            assert second.steps == SEGMENT_STEPS
            assert session.runs_executed == MAX_RUNS
            snapshot = session.snapshot()[0]
            error = _execution_error(session.advance)
            assert RUN_BUDGET_ERROR in error
    assert replace(snapshot, steps=TOTAL_STEPS) == expected


def test_resident_session_accumulates_output_across_launches() -> None:
    """Output capacity and cursor persist across resident launch boundaries."""
    request = replace(
        _request(),
        accumulator=OUTPUT_BYTE,
        memory=_instruction_memory(OUTPUT_DECODED, TOTAL_STEPS),
        step_budget=1,
    )
    with _cuda() as adapter:
        expected = adapter.evaluate((replace(request, step_budget=MAX_RUNS),))[
            0
        ]
        with adapter.open_session((request,), max_runs=MAX_RUNS) as session:
            session.advance()
            assert session.observe()[0].output_length == 1
            session.advance()
            assert session.observe()[0].output_length == MAX_RUNS
            snapshot = session.snapshot()[0]
    assert snapshot.output_bytes == expected.output_bytes
    assert snapshot.output_bytes == (OUTPUT_BYTE, OUTPUT_BYTE)


def test_resident_session_rejects_impossible_output_capacity() -> None:
    """Oversized output reservation fails before constructing host buffers."""
    request = replace(_request(), step_budget=(1 << 32) - 1)
    with _cuda() as adapter:
        error = _invalid_error(
            lambda: adapter.open_session((request,), max_runs=MAX_RUNS)
        )
    assert OUTPUT_CAPACITY_ERROR in error


def test_resident_session_rejects_nonpositive_launch_budget() -> None:
    """Session output capacity is never created for an invalid run count."""
    with _cuda() as adapter:
        error = _invalid_error(
            lambda: adapter.open_session((_request(),), max_runs=0)
        )
    assert MAX_RUNS_ERROR in error


def _request() -> ClassicRunRequest:
    return ClassicRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=_noop_memory(TOTAL_STEPS),
        output_bytes=(),
        step_budget=SEGMENT_STEPS,
        termination=StepTermination.NONE,
    ).validated()


def _noop_memory(steps: int) -> tuple[int, ...]:
    return _instruction_memory(NOOP_DECODED, steps)


def _instruction_memory(decoded: int, steps: int) -> tuple[int, ...]:
    target_index = XLAT1.index(decoded)
    words = [33] * MEMORY_WORDS
    for code_pointer in range(steps):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        words[code_pointer] = 33 + encoded_index
    return tuple(words)


def _execution_error(call: Callable[[], object]) -> str:
    try:
        _ = call()
    except AcceleratorExecutionError as error:
        return str(error)
    message = "expected AcceleratorExecutionError"
    raise AssertionError(message)


def _invalid_error(call: Callable[[], object]) -> str:
    try:
        _ = call()
    except InvalidPrimitiveBatchError as error:
        return str(error)
    message = "expected InvalidPrimitiveBatchError"
    raise AssertionError(message)
