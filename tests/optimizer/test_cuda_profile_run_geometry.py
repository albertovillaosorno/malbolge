# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Live CUDA evidence that resident execution is not fixed to known profiles."""

from __future__ import annotations

from array import array
from typing import Final
from unittest import SkipTest

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest

SYNTHETIC_TRITS: Final = 5
SYNTHETIC_WORDS: Final = 243
INITIAL_ACCUMULATOR: Final = 7
EXPECTED_DATA_POINTER: Final = 2
NO_OP_CELL: Final = 33
ENCRYPTED_NO_OP_CELL: Final = 53
GEOMETRY = ProfileRunGeometry(
    eof_word=SYNTHETIC_WORDS - 1,
    memory_words=SYNTHETIC_WORDS,
    word_modulus=SYNTHETIC_WORDS,
    word_trits=SYNTHETIC_TRITS,
)


def _cuda() -> CudaProfileRunAdapter:
    try:
        return CudaProfileRunAdapter(GEOMETRY)
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def test_cuda_resident_kernel_executes_synthetic_five_trit_geometry() -> None:
    """Execute a valid NVRTC profile distinct from 10/14 trits."""
    memory = array("I", [0]) * SYNTHETIC_WORDS
    memory[0] = NO_OP_CELL
    request = ProfileRunRequest(
        accumulator=INITIAL_ACCUMULATOR,
        code_pointer=0,
        data_pointer=1,
        input_bytes=(),
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )

    with _cuda() as adapter:
        (result,) = adapter.evaluate((request,))

    assert result.accumulator == INITIAL_ACCUMULATOR
    assert result.code_pointer == 1
    assert result.data_pointer == EXPECTED_DATA_POINTER
    assert result.error is RunError.NONE
    assert result.input_consumed == 0
    assert result.memory[0] == ENCRYPTED_NO_OP_CELL
    assert result.memory[1:] == memory[1:]
    assert result.output_bytes == ()
    assert result.status is RunStatus.BUDGET_EXHAUSTED
    assert result.steps == 1
    assert result.termination is StepTermination.NONE
