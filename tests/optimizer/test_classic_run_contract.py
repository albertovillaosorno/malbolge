# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Contract tests for complete resident classic accelerator requests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError

if TYPE_CHECKING:
    from collections.abc import Callable

ZERO_MEMORY: tuple[int, ...] = (0,) * MEMORY_WORDS
INVALID_WORD = 59_049
INVALID_BYTE = 256
MEMORY_LENGTH_ERROR = "requires 59049 words"
MEMORY_WORD_ERROR = "memory value outside classic word domain"
INPUT_BYTE_ERROR = "input byte outside byte domain"
OUTPUT_BYTE_ERROR = "output byte outside byte domain"
INPUT_CURSOR_ERROR = "input consumed exceeds"
TERMINATION_ERROR = "invalid resident termination"


def test_resident_request_accepts_complete_resumable_state() -> None:
    """A full classic state with prior I/O can be resumed."""
    request = replace(
        _base_request(),
        accumulator=7,
        code_pointer=3,
        data_pointer=4,
        input_bytes=(65, 66),
        input_consumed=1,
        output_bytes=(90,),
        step_budget=8,
    )
    assert request.validated() is request


def test_resident_request_requires_exact_classic_memory() -> None:
    """Resident requests cannot omit any classic memory cell."""
    request = replace(_base_request(), memory=ZERO_MEMORY[:-1])
    assert MEMORY_LENGTH_ERROR in _invalid(request.validated)


def test_resident_request_rejects_out_of_domain_memory() -> None:
    """Every resident memory word is validated before CUDA execution."""
    memory: list[int] = list(ZERO_MEMORY)
    memory[-1] = INVALID_WORD
    request = replace(_base_request(), memory=tuple(memory))
    assert MEMORY_WORD_ERROR in _invalid(request.validated)


def test_resident_request_rejects_negative_memory() -> None:
    """Aggregate memory validation still rejects the lower domain edge."""
    memory: list[int] = list(ZERO_MEMORY)
    memory[0] = -1
    request = replace(_base_request(), memory=tuple(memory))
    assert MEMORY_WORD_ERROR in _invalid(request.validated)


def test_resident_request_rejects_invalid_io_and_cursor() -> None:
    """I/O bytes and the resumable input cursor remain bounded."""
    invalid_input = replace(_base_request(), input_bytes=(INVALID_BYTE,))
    assert INPUT_BYTE_ERROR in _invalid(invalid_input.validated)
    invalid_output = replace(_base_request(), output_bytes=(INVALID_BYTE,))
    assert OUTPUT_BYTE_ERROR in _invalid(invalid_output.validated)
    invalid_cursor = replace(
        _base_request(), input_bytes=(1,), input_consumed=2
    )
    assert INPUT_CURSOR_ERROR in _invalid(invalid_cursor.validated)


def test_resident_request_rejects_raw_termination_integer() -> None:
    """Dynamic callers cannot substitute an untyped termination integer."""
    request = replace(_base_request(), termination=1)
    assert TERMINATION_ERROR in _invalid(request.validated)


def _base_request() -> ClassicRunRequest:
    return ClassicRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=ZERO_MEMORY,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def _invalid(call: Callable[[], object]) -> str:
    try:
        _ = call()
    except InvalidPrimitiveBatchError as error:
        return str(error)
    message = "expected InvalidPrimitiveBatchError"
    raise AssertionError(message)
