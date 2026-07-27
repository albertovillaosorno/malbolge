# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Hardware-neutral compact classic-step contract evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from accelerator.classic_step import ClassicStepRequest
from accelerator.classic_step import ClassicStepResult
from accelerator.classic_step import REQUEST_WORDS
from accelerator.classic_step import RESULT_WORDS
from accelerator.classic_step import StepError
from accelerator.classic_step import StepInputKind
from accelerator.classic_step import StepMemoryCell
from accelerator.classic_step import StepMemoryWrite
from accelerator.classic_step import StepStatus
from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError

DUPLICATE_MEMORY = "duplicate compact memory address"
MISSING_CODE_CELL = "missing its code-pointer cell"
INVALID_TERMINATION = "invalid compact termination"


def _invalid(action: Callable[[], object]) -> str:
    try:
        _ = action()
    except InvalidPrimitiveBatchError as error:
        return str(error)
    raise AssertionError


def test_compact_step_request_is_fixed_width_and_zero_padded() -> None:
    """Request encoding has a stable 20-word layout with four memory slots."""
    request = ClassicStepRequest(
        accumulator=7,
        code_pointer=0,
        data_pointer=1,
        input_byte=65,
        input_consumed=3,
        memory=(StepMemoryCell(0, 99), StepMemoryCell(1, 39)),
        output_len=5,
    )
    words = request.to_words()
    assert len(words) == REQUEST_WORDS
    assert words[:8] == (7, 0, 1, 3, 5, 0, 1, 65)
    assert words[8:14] == (1, 0, 99, 1, 1, 39)
    assert words[14:] == (0, 0, 0, 0, 0, 0)


def test_compact_step_request_rejects_invalid_termination_type() -> None:
    """Reject raw termination integers from dynamic callers."""
    request = ClassicStepRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=1,
        input_byte=None,
        input_consumed=0,
        memory=(StepMemoryCell(0, 39),),
        output_len=0,
        termination=3,
    )
    assert INVALID_TERMINATION in _invalid(request.validated)


def test_compact_step_request_rejects_hidden_or_duplicate_memory() -> None:
    """Live requests require `C` and reject ambiguous duplicate addresses."""
    missing = ClassicStepRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=1,
        input_byte=None,
        input_consumed=0,
        memory=(StepMemoryCell(1, 1),),
        output_len=0,
    )
    assert MISSING_CODE_CELL in _invalid(missing.validated)
    duplicate = ClassicStepRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=1,
        input_byte=None,
        input_consumed=0,
        memory=(StepMemoryCell(0, 39), StepMemoryCell(0, 40)),
        output_len=0,
    )
    assert DUPLICATE_MEMORY in _invalid(duplicate.validated)


def test_compact_step_result_roundtrip_preserves_trace_projection() -> None:
    """Preserve status, I/O, diagnostics, and both writes across encoding."""
    result = ClassicStepResult(
        accumulator=19_683,
        code_pointer=1,
        data_pointer=2,
        data_write=StepMemoryWrite(address=1, before=1, after=19_683),
        decoded=42,
        encryption_write=StepMemoryWrite(address=0, before=39, after=116),
        error=StepError.NONE,
        error_pointer=0,
        error_value=0,
        fetched=39,
        input_consumed=0,
        input_kind=StepInputKind.NONE,
        input_value=0,
        output_len=0,
        output_value=None,
        status=StepStatus.CONTINUED,
        termination=StepTermination.NONE,
    )
    words = result.to_words()
    assert len(words) == RESULT_WORDS
    assert ClassicStepResult.from_words(words) == result
